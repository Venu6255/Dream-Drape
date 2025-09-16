"""
Payment processing module for Dream-Drape application
Handles Stripe and Razorpay payment integration
"""
import stripe
import razorpay
from flask import current_app
from app.security import log_security_event, mask_sensitive_data
import logging
import json
from decimal import Decimal

class PaymentError(Exception):
    """Custom exception for payment processing errors"""
    pass

class PaymentProcessor:
    """Base payment processor class"""
    
    def __init__(self):
        self.logger = logging.getLogger('payments')
    
    def process_payment(self, payment_data):
        """Process payment - to be implemented by subclasses"""
        raise NotImplementedError
    
    def verify_payment(self, payment_id):
        """Verify payment status - to be implemented by subclasses"""
        raise NotImplementedError
    
    def refund_payment(self, payment_id, amount=None):
        """Refund payment - to be implemented by subclasses"""
        raise NotImplementedError

class StripeProcessor(PaymentProcessor):
    """Stripe payment processor"""
    
    def __init__(self):
        super().__init__()
        stripe.api_key = current_app.config.get('STRIPE_SECRET_KEY')
        
        if not stripe.api_key:
            raise PaymentError("Stripe secret key not configured")
    
    def process_payment(self, payment_data):
        """Process Stripe payment"""
        try:
            # Validate required fields
            required_fields = ['amount', 'currency', 'card_number', 'card_expiry', 'card_cvv']
            for field in required_fields:
                if field not in payment_data:
                    raise PaymentError(f"Missing required field: {field}")
            
            # Convert amount to cents
            amount_cents = int(Decimal(str(payment_data['amount'])) * 100)
            
            if amount_cents <= 0:
                raise PaymentError("Invalid payment amount")
            
            # Parse card expiry
            expiry_parts = payment_data['card_expiry'].split('/')
            if len(expiry_parts) != 2:
                raise PaymentError("Invalid card expiry format")
            
            exp_month = int(expiry_parts[0])
            exp_year = int('20' + expiry_parts[1])
            
            # Create payment method
            payment_method = stripe.PaymentMethod.create(
                type="card",
                card={
                    "number": payment_data['card_number'],
                    "exp_month": exp_month,
                    "exp_year": exp_year,
                    "cvc": payment_data['card_cvv'],
                }
            )
            
            # Create payment intent
            intent = stripe.PaymentIntent.create(
                amount=amount_cents,
                currency=payment_data.get('currency', 'inr').lower(),
                payment_method=payment_method.id,
                confirmation_method='manual',
                confirm=True,
                return_url=current_app.config.get('STRIPE_RETURN_URL', 'https://dreamdrape.com/payment/return'),
                metadata={
                    'order_id': payment_data.get('order_id', ''),
                    'customer_email': payment_data.get('customer_email', '')
                }
            )
            
            if intent.status == 'succeeded':
                self.logger.info(f"Stripe payment successful: {intent.id}")
                log_security_event('PAYMENT_SUCCESS', 
                                 f'Stripe payment successful for amount: {payment_data["amount"]}')
                
                return {
                    'success': True,
                    'transaction_id': intent.id,
                    'amount': payment_data['amount'],
                    'currency': payment_data['currency'],
                    'status': 'completed'
                }
            
            elif intent.status == 'requires_action':
                return {
                    'success': False,
                    'requires_action': True,
                    'client_secret': intent.client_secret,
                    'error': 'Additional authentication required'
                }
            
            else:
                raise PaymentError(f"Payment failed with status: {intent.status}")
                
        except stripe.error.CardError as e:
            error_msg = f"Card error: {e.user_message}"
            self.logger.error(f"Stripe card error: {e}")
            log_security_event('PAYMENT_CARD_ERROR', error_msg, severity='WARNING')
            raise PaymentError(error_msg)
            
        except stripe.error.RateLimitError as e:
            error_msg = "Rate limit error"
            self.logger.error(f"Stripe rate limit error: {e}")
            raise PaymentError(error_msg)
            
        except stripe.error.InvalidRequestError as e:
            error_msg = f"Invalid request: {e.user_message}"
            self.logger.error(f"Stripe invalid request error: {e}")
            raise PaymentError(error_msg)
            
        except stripe.error.AuthenticationError as e:
            error_msg = "Authentication error"
            self.logger.error(f"Stripe authentication error: {e}")
            log_security_event('PAYMENT_AUTH_ERROR', 'Stripe authentication failed', 
                             severity='ERROR')
            raise PaymentError(error_msg)
            
        except stripe.error.APIConnectionError as e:
            error_msg = "Network error"
            self.logger.error(f"Stripe API connection error: {e}")
            raise PaymentError(error_msg)
            
        except stripe.error.StripeError as e:
            error_msg = "Payment processing error"
            self.logger.error(f"Stripe error: {e}")
            raise PaymentError(error_msg)
            
        except Exception as e:
            error_msg = f"Unexpected payment error: {str(e)}"
            self.logger.error(error_msg)
            raise PaymentError("Payment processing failed")
    
    def verify_payment(self, payment_id):
        """Verify Stripe payment"""
        try:
            intent = stripe.PaymentIntent.retrieve(payment_id)
            
            return {
                'success': True,
                'status': intent.status,
                'amount': intent.amount / 100,  # Convert from cents
                'currency': intent.currency.upper(),
                'verified': intent.status == 'succeeded'
            }
            
        except Exception as e:
            self.logger.error(f"Stripe verification error: {e}")
            return {'success': False, 'error': str(e)}
    
    def refund_payment(self, payment_id, amount=None):
        """Refund Stripe payment"""
        try:
            refund_data = {'payment_intent': payment_id}
            
            if amount:
                # Convert to cents
                refund_data['amount'] = int(Decimal(str(amount)) * 100)
            
            refund = stripe.Refund.create(**refund_data)
            
            self.logger.info(f"Stripe refund successful: {refund.id}")
            log_security_event('PAYMENT_REFUND', f'Stripe refund processed: {refund.id}')
            
            return {
                'success': True,
                'refund_id': refund.id,
                'status': refund.status,
                'amount': refund.amount / 100 if refund.amount else None
            }
            
        except Exception as e:
            self.logger.error(f"Stripe refund error: {e}")
            return {'success': False, 'error': str(e)}

class RazorpayProcessor(PaymentProcessor):
    """Razorpay payment processor"""
    
    def __init__(self):
        super().__init__()
        key_id = current_app.config.get('RAZORPAY_KEY_ID')
        key_secret = current_app.config.get('RAZORPAY_KEY_SECRET')
        
        if not key_id or not key_secret:
            raise PaymentError("Razorpay credentials not configured")
        
        self.client = razorpay.Client(auth=(key_id, key_secret))
    
    def process_payment(self, payment_data):
        """Process Razorpay payment"""
        try:
            # Validate required fields
            required_fields = ['amount', 'currency', 'order_id']
            for field in required_fields:
                if field not in payment_data:
                    raise PaymentError(f"Missing required field: {field}")
            
            # Convert amount to paisa (smallest currency unit)
            amount_paisa = int(Decimal(str(payment_data['amount'])) * 100)
            
            if amount_paisa <= 0:
                raise PaymentError("Invalid payment amount")
            
            # Create order
            order_data = {
                'amount': amount_paisa,
                'currency': payment_data.get('currency', 'INR').upper(),
                'receipt': payment_data['order_id'],
                'payment_capture': 1,  # Auto capture
                'notes': {
                    'order_id': payment_data.get('order_id', ''),
                    'customer_email': payment_data.get('customer_email', '')
                }
            }
            
            order = self.client.order.create(data=order_data)
            
            self.logger.info(f"Razorpay order created: {order['id']}")
            
            return {
                'success': True,
                'order_id': order['id'],
                'amount': payment_data['amount'],
                'currency': payment_data['currency'],
                'key_id': current_app.config.get('RAZORPAY_KEY_ID'),
                'status': 'created'
            }
            
        except Exception as e:
            error_msg = f"Razorpay order creation failed: {str(e)}"
            self.logger.error(error_msg)
            raise PaymentError(error_msg)
    
    def verify_payment(self, payment_id, order_id=None, signature=None):
        """Verify Razorpay payment"""
        try:
            # Fetch payment details
            payment = self.client.payment.fetch(payment_id)
            
            # Verify signature if provided
            if order_id and signature:
                params_dict = {
                    'razorpay_order_id': order_id,
                    'razorpay_payment_id': payment_id,
                    'razorpay_signature': signature
                }
                
                # This will raise an exception if signature is invalid
                self.client.utility.verify_payment_signature(params_dict)
            
            self.logger.info(f"Razorpay payment verified: {payment_id}")
            
            return {
                'success': True,
                'status': payment['status'],
                'amount': payment['amount'] / 100,  # Convert from paisa
                'currency': payment['currency'],
                'verified': payment['status'] == 'captured'
            }
            
        except Exception as e:
            self.logger.error(f"Razorpay verification error: {e}")
            return {'success': False, 'error': str(e)}
    
    def refund_payment(self, payment_id, amount=None):
        """Refund Razorpay payment"""
        try:
            refund_data = {'payment_id': payment_id}
            
            if amount:
                # Convert to paisa
                refund_data['amount'] = int(Decimal(str(amount)) * 100)
            
            refund = self.client.payment.refund(payment_id, refund_data)
            
            self.logger.info(f"Razorpay refund successful: {refund['id']}")
            log_security_event('PAYMENT_REFUND', f'Razorpay refund processed: {refund["id"]}')
            
            return {
                'success': True,
                'refund_id': refund['id'],
                'status': refund['status'],
                'amount': refund['amount'] / 100 if refund['amount'] else None
            }
            
        except Exception as e:
            self.logger.error(f"Razorpay refund error: {e}")
            return {'success': False, 'error': str(e)}

# Main payment processing function
def process_payment(payment_data):
    """Main function to process payments based on payment method"""
    try:
        payment_method = payment_data.get('payment_method', '').lower()
        
        if payment_method == 'stripe':
            processor = StripeProcessor()
        elif payment_method == 'razorpay':
            processor = RazorpayProcessor()
        else:
            raise PaymentError(f"Unsupported payment method: {payment_method}")
        
        # Log payment attempt (with masked sensitive data)
        masked_data = {k: mask_sensitive_data(str(v)) if 'card' in k else v 
                      for k, v in payment_data.items()}
        
        current_app.logger.info(f"Processing {payment_method} payment: {json.dumps(masked_data)}")
        
        result = processor.process_payment(payment_data)
        
        if result.get('success'):
            log_security_event('PAYMENT_PROCESSED', 
                             f'Payment processed successfully: {payment_method}')
        
        return result
        
    except PaymentError:
        raise
    except Exception as e:
        error_msg = f"Payment processing failed: {str(e)}"
        current_app.logger.error(error_msg)
        log_security_event('PAYMENT_ERROR', error_msg, severity='ERROR')
        raise PaymentError("Payment processing failed")

def verify_payment(payment_id, payment_method, **kwargs):
    """Verify payment status"""
    try:
        if payment_method.lower() == 'stripe':
            processor = StripeProcessor()
        elif payment_method.lower() == 'razorpay':
            processor = RazorpayProcessor()
        else:
            raise PaymentError(f"Unsupported payment method: {payment_method}")
        
        return processor.verify_payment(payment_id, **kwargs)
        
    except Exception as e:
        current_app.logger.error(f"Payment verification failed: {e}")
        return {'success': False, 'error': str(e)}

def refund_payment(payment_id, payment_method, amount=None):
    """Refund a payment"""
    try:
        if payment_method.lower() == 'stripe':
            processor = StripeProcessor()
        elif payment_method.lower() == 'razorpay':
            processor = RazorpayProcessor()
        else:
            raise PaymentError(f"Unsupported payment method: {payment_method}")
        
        return processor.refund_payment(payment_id, amount)
        
    except Exception as e:
        current_app.logger.error(f"Payment refund failed: {e}")
        return {'success': False, 'error': str(e)}

# Webhook handlers
def handle_stripe_webhook(payload, sig_header):
    """Handle Stripe webhook events"""
    try:
        endpoint_secret = current_app.config.get('STRIPE_WEBHOOK_SECRET')
        
        if endpoint_secret:
            event = stripe.Webhook.construct_event(
                payload, sig_header, endpoint_secret
            )
        else:
            event = json.loads(payload)
        
        # Handle different event types
        if event['type'] == 'payment_intent.succeeded':
            payment_intent = event['data']['object']
            current_app.logger.info(f"Stripe payment succeeded: {payment_intent['id']}")
            log_security_event('WEBHOOK_PAYMENT_SUCCESS', 
                             f'Stripe webhook payment success: {payment_intent["id"]}')
            
        elif event['type'] == 'payment_intent.payment_failed':
            payment_intent = event['data']['object']
            current_app.logger.warning(f"Stripe payment failed: {payment_intent['id']}")
            log_security_event('WEBHOOK_PAYMENT_FAILED', 
                             f'Stripe webhook payment failed: {payment_intent["id"]}',
                             severity='WARNING')
        
        return {'success': True}
        
    except Exception as e:
        current_app.logger.error(f"Stripe webhook error: {e}")
        return {'success': False, 'error': str(e)}

def handle_razorpay_webhook(payload, signature):
    """Handle Razorpay webhook events"""
    try:
        webhook_secret = current_app.config.get('RAZORPAY_WEBHOOK_SECRET')
        
        if webhook_secret:
            # Verify webhook signature
            # Implementation depends on Razorpay's webhook verification method
            pass
        
        event = json.loads(payload)
        
        # Handle different event types
        if event['event'] == 'payment.captured':
            payment = event['payload']['payment']['entity']
            current_app.logger.info(f"Razorpay payment captured: {payment['id']}")
            log_security_event('WEBHOOK_PAYMENT_SUCCESS', 
                             f'Razorpay webhook payment captured: {payment["id"]}')
            
        elif event['event'] == 'payment.failed':
            payment = event['payload']['payment']['entity']
            current_app.logger.warning(f"Razorpay payment failed: {payment['id']}")
            log_security_event('WEBHOOK_PAYMENT_FAILED', 
                             f'Razorpay webhook payment failed: {payment["id"]}',
                             severity='WARNING')
        
        return {'success': True}
        
    except Exception as e:
        current_app.logger.error(f"Razorpay webhook error: {e}")
        return {'success': False, 'error': str(e)}
