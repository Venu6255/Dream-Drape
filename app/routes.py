from flask import Blueprint, render_template, request, flash, redirect, url_for, jsonify, session, current_app
from flask_login import current_user, login_required
from flask_limiter import Limiter
from flask_limiter.util import get_remote_address
from app.models import Product, Category, CartItem, WishlistItem, Order, OrderItem, Review, Newsletter, ContactMessage, AuditLog
from app.forms import AddToCartForm, ReviewForm, NewsletterForm, ContactForm, SearchForm, CheckoutForm
from app.utils import generate_order_number, create_sample_data
from app.validators import sanitize_input, validate_file_upload
from app.payments import process_payment, PaymentError
from app.security import log_user_action
from app import db, cache, limiter
import json
from sqlalchemy import or_, and_
from datetime import datetime
import bleach

main = Blueprint('main', __name__)

@main.route('/')
@main.route('/index')
@cache.cached(timeout=300)  # Cache for 5 minutes
def index():
    """Homepage with featured products and categories"""
    # Get featured products
    featured_products = Product.query.filter_by(is_featured=True, is_active=True).limit(8).all()
    
    # Get new arrivals
    new_arrivals = Product.query.filter_by(is_new_arrival=True, is_active=True).limit(6).all()
    
    # Get best sellers
    best_sellers = Product.query.filter_by(is_best_seller=True, is_active=True).limit(6).all()
    
    # Get sale products
    sale_products = Product.query.filter_by(is_on_sale=True, is_active=True).limit(6).all()
    
    # Get categories
    categories = Category.query.filter_by(is_active=True).all()
    
    # Newsletter form
    newsletter_form = NewsletterForm()
    
    return render_template('index.html', 
                         featured_products=featured_products,
                         new_arrivals=new_arrivals,
                         best_sellers=best_sellers,
                         sale_products=sale_products,
                         categories=categories,
                         newsletter_form=newsletter_form)

@main.route('/products')
def products():
    """Product listing page with search and filter"""
    page = request.args.get('page', 1, type=int)
    category = sanitize_input(request.args.get('category', ''))
    search = sanitize_input(request.args.get('search', ''))
    sort_by = request.args.get('sort_by', 'newest')
    min_price = request.args.get('min_price', type=float)
    max_price = request.args.get('max_price', type=float)
    
    # Validate pagination
    if page < 1:
        page = 1
    
    query = Product.query.filter_by(is_active=True)
    
    # Apply filters with proper sanitization
    if category:
        query = query.join(Product.categories).filter(Category.name == category)
    
    if search:
        # Sanitize search input to prevent SQL injection
        clean_search = bleach.clean(search, strip=True)
        query = query.filter(or_(
            Product.name.contains(clean_search),
            Product.description.contains(clean_search)
        ))
    
    if min_price and min_price >= 0:
        query = query.filter(Product.price >= min_price)
    
    if max_price and max_price >= 0:
        query = query.filter(Product.price <= max_price)
    
    # Apply sorting with validation
    valid_sorts = ['name_asc', 'name_desc', 'price_asc', 'price_desc', 'newest']
    if sort_by not in valid_sorts:
        sort_by = 'newest'
    
    if sort_by == 'name_asc':
        query = query.order_by(Product.name.asc())
    elif sort_by == 'name_desc':
        query = query.order_by(Product.name.desc())
    elif sort_by == 'price_asc':
        query = query.order_by(Product.price.asc())
    elif sort_by == 'price_desc':
        query = query.order_by(Product.price.desc())
    elif sort_by == 'newest':
        query = query.order_by(Product.created_at.desc())
    
    try:
        products = query.paginate(
            page=page, per_page=12, error_out=False
        )
    except Exception as e:
        current_app.logger.error(f"Pagination error: {e}")
        flash('Error loading products. Please try again.', 'error')
        return redirect(url_for('main.index'))
    
    categories = Category.query.filter_by(is_active=True).all()
    
    return render_template('products.html', products=products, categories=categories,
                         current_category=category, current_search=search,
                         current_sort=sort_by, min_price=min_price, max_price=max_price)

@main.route('/product/<int:id>')
def product_detail(id):
    """Individual product page"""
    product = Product.query.get_or_404(id)
    
    if not product.is_active:
        flash('Product not available.', 'error')
        return redirect(url_for('main.products'))
    
    # Get related products
    related_products = Product.query.filter(
        and_(Product.id != id, Product.is_active == True)
    ).join(Product.categories).filter(
        Category.id.in_([cat.id for cat in product.categories])
    ).limit(4).all()
    
    # Get approved reviews only
    reviews = Review.query.filter_by(product_id=id, is_approved=True).all()
    
    # Forms
    add_to_cart_form = AddToCartForm()
    review_form = ReviewForm()
    
    # Populate size and color choices securely
    if product.sizes:
        sizes = [size.strip() for size in product.sizes.split(',') if size.strip()]
        add_to_cart_form.size.choices = [(size, size) for size in sizes]
        add_to_cart_form.size.choices.insert(0, ('', 'Select Size'))
    
    if product.colors:
        colors = [color.strip() for color in product.colors.split(',') if color.strip()]
        add_to_cart_form.color.choices = [(color, color) for color in colors]
        add_to_cart_form.color.choices.insert(0, ('', 'Select Color'))
    
    return render_template('product_detail.html', product=product, 
                         related_products=related_products, reviews=reviews,
                         add_to_cart_form=add_to_cart_form, review_form=review_form)

@main.route('/add_to_cart', methods=['POST'])
@login_required
@limiter.limit("10 per minute")
def add_to_cart():
    """Add product to cart with security validation"""
    try:
        product_id = request.form.get('product_id', type=int)
        quantity = max(1, min(10, request.form.get('quantity', 1, type=int)))  # Limit quantity
        size = sanitize_input(request.form.get('size', ''))
        color = sanitize_input(request.form.get('color', ''))
        
        if not product_id:
            flash('Invalid product.', 'error')
            return redirect(url_for('main.products'))
        
        product = Product.query.get_or_404(product_id)
        
        if not product.is_active or not product.is_in_stock():
            flash('Sorry, this product is out of stock.', 'error')
            return redirect(url_for('main.product_detail', id=product_id))
        
        # Check stock availability
        if product.stock_quantity < quantity:
            flash(f'Only {product.stock_quantity} items available.', 'warning')
            quantity = product.stock_quantity
        
        # Check if item already exists in cart
        cart_item = CartItem.query.filter_by(
            user_id=current_user.id, 
            product_id=product_id,
            size=size,
            color=color
        ).first()
        
        if cart_item:
            new_quantity = cart_item.quantity + quantity
            if new_quantity <= product.stock_quantity:
                cart_item.quantity = new_quantity
            else:
                flash('Cannot add more items. Not enough stock.', 'warning')
                return redirect(url_for('main.product_detail', id=product_id))
        else:
            cart_item = CartItem(
                user_id=current_user.id,
                product_id=product_id,
                quantity=quantity,
                size=size,
                color=color
            )
            db.session.add(cart_item)
        
        db.session.commit()
        log_user_action(current_user.id, 'add_to_cart', 'product', product_id)
        flash(f'{product.name} added to cart!', 'success')
        
    except Exception as e:
        current_app.logger.error(f"Add to cart error: {e}")
        flash('Error adding item to cart. Please try again.', 'error')
    
    return redirect(url_for('main.product_detail', id=product_id))

@main.route('/cart')
@login_required
def cart():
    """Shopping cart page with total calculation"""
    cart_items = CartItem.query.filter_by(user_id=current_user.id).all()
    
    # Validate cart items and remove invalid ones
    valid_items = []
    for item in cart_items:
        if item.product and item.product.is_active:
            valid_items.append(item)
        else:
            db.session.delete(item)
    
    if len(valid_items) != len(cart_items):
        db.session.commit()
        flash('Some items were removed from your cart as they are no longer available.', 'info')
    
    total = sum(item.get_total() for item in valid_items)
    
    return render_template('cart.html', cart_items=valid_items, total=total)

@main.route('/checkout', methods=['GET', 'POST'])
@login_required
@limiter.limit("5 per minute")
def checkout():
    """Secure checkout with complete payment integration"""
    cart_items = CartItem.query.filter_by(user_id=current_user.id).all()

    if not cart_items:
        flash('Your cart is empty!', 'warning')
        return redirect(url_for('main.cart'))

    # Validate all items are still available
    for item in cart_items:
        if not item.product.is_active or not item.product.is_in_stock():
            flash(f'{item.product.name} is no longer available and has been removed from your cart.', 'warning')
            db.session.delete(item)
            db.session.commit()
            return redirect(url_for('main.cart'))

    total = sum(item.get_total() for item in cart_items)
    form = CheckoutForm()

    # Pre-populate form with user data for GET requests
    if request.method == 'GET' and current_user:
        form.first_name.data = current_user.first_name
        form.last_name.data = current_user.last_name
        form.email.data = current_user.email
        form.phone.data = current_user.phone
        form.address.data = current_user.address
        form.city.data = current_user.city
        form.state.data = current_user.state
        form.pincode.data = current_user.pincode
        form.country.data = current_user.country or 'India'

    if form.validate_on_submit():
        try:
            # Server-side validation for payment details
            if form.payment_method.data == 'stripe':
                if not all([form.card_number.data, form.card_expiry.data, form.card_cvv.data]):
                    flash('Please enter all credit card details.', 'error')
                    return render_template('checkout.html', cart_items=cart_items, total=total, form=form)

            # Create order
            order = Order(
                user_id=current_user.id,
                total_amount=total,
                payment_method=form.payment_method.data,
                shipping_address=sanitize_input(form.address.data),
                shipping_city=sanitize_input(form.city.data),
                shipping_state=sanitize_input(form.state.data),
                shipping_pincode=sanitize_input(form.pincode.data),
                shipping_country=sanitize_input(form.country.data),
                shipping_phone=sanitize_input(form.phone.data),
                notes=sanitize_input(form.notes.data)
            )
            order.generate_order_number()
            db.session.add(order)
            db.session.flush()

            # Process payment if not COD
            if form.payment_method.data != 'cod':
                payment_data = {
                    'amount': total,
                    'currency': 'INR',
                    'order_id': order.order_number,
                    'payment_method': form.payment_method.data
                }
                
                if form.payment_method.data == 'stripe':
                    payment_data.update({
                        'card_number': form.card_number.data,
                        'card_expiry': form.card_expiry.data,
                        'card_cvv': form.card_cvv.data
                    })
                
                payment_result = process_payment(payment_data)
                
                if payment_result['success']:
                    order.payment_status = 'paid'
                    order.payment_id = payment_result.get('transaction_id')
                else:
                    flash(f'Payment failed: {payment_result.get("error", "Unknown error")}', 'error')
                    db.session.rollback()
                    return render_template('checkout.html', cart_items=cart_items, total=total, form=form)

            # Create order items
            for cart_item in cart_items:
                order_item = OrderItem(
                    order_id=order.id,
                    product_id=cart_item.product_id,
                    quantity=cart_item.quantity,
                    price=cart_item.product.price,
                    size=cart_item.size,
                    color=cart_item.color
                )
                db.session.add(order_item)
                
                # Update stock
                cart_item.product.stock_quantity -= cart_item.quantity

            # Clear cart
            for cart_item in cart_items:
                db.session.delete(cart_item)

            db.session.commit()
            log_user_action(current_user.id, 'place_order', 'order', order.id)
            
            flash(f'Order placed successfully! Order number: {order.order_number}', 'success')
            return redirect(url_for('main.order_confirmation', order_id=order.id))
            
        except PaymentError as e:
            flash(f'Payment error: {str(e)}', 'error')
            db.session.rollback()
        except Exception as e:
            current_app.logger.error(f"Checkout error: {e}")
            flash('Error processing order. Please try again.', 'error')
            db.session.rollback()

    return render_template('checkout.html', cart_items=cart_items, total=total, form=form)

@main.route('/order_confirmation/<int:order_id>')
@login_required
def order_confirmation(order_id):
    """Order confirmation page"""
    order = Order.query.filter_by(id=order_id, user_id=current_user.id).first_or_404()
    return render_template('order_confirmation.html', order=order)

@main.route('/update_cart', methods=['POST'])
@login_required
@limiter.limit("20 per minute")
def update_cart():
    """Update cart item quantity with validation"""
    try:
        item_id = request.form.get('item_id', type=int)
        quantity = request.form.get('quantity', type=int)
        
        if not item_id or quantity is None:
            flash('Invalid request.', 'error')
            return redirect(url_for('main.cart'))
        
        cart_item = CartItem.query.filter_by(id=item_id, user_id=current_user.id).first_or_404()
        
        if quantity > 0:
            # Validate stock
            if quantity <= cart_item.product.stock_quantity:
                cart_item.quantity = min(quantity, 10)  # Max 10 per item
                db.session.commit()
                flash('Cart updated successfully!', 'success')
            else:
                flash(f'Only {cart_item.product.stock_quantity} items available.', 'warning')
        else:
            db.session.delete(cart_item)
            db.session.commit()
            flash('Item removed from cart!', 'info')
            
    except Exception as e:
        current_app.logger.error(f"Update cart error: {e}")
        flash('Error updating cart. Please try again.', 'error')
    
    return redirect(url_for('main.cart'))

@main.route('/remove_from_cart/<int:item_id>')
@login_required
def remove_from_cart(item_id):
    """Remove item from cart"""
    try:
        cart_item = CartItem.query.filter_by(id=item_id, user_id=current_user.id).first_or_404()
        db.session.delete(cart_item)
        db.session.commit()
        flash('Item removed from cart!', 'info')
    except Exception as e:
        current_app.logger.error(f"Remove from cart error: {e}")
        flash('Error removing item. Please try again.', 'error')
    
    return redirect(url_for('main.cart'))

@main.route('/wishlist')
@login_required
def wishlist():
    """User wishlist page"""
    wishlist_items = WishlistItem.query.filter_by(user_id=current_user.id).all()
    return render_template('wishlist.html', wishlist_items=wishlist_items)

@main.route('/add_to_wishlist/<int:product_id>')
@login_required
@limiter.limit("10 per minute")
def add_to_wishlist(product_id):
    """Add product to wishlist"""
    try:
        product = Product.query.get_or_404(product_id)
        
        existing_item = WishlistItem.query.filter_by(
            user_id=current_user.id, 
            product_id=product_id
        ).first()
        
        if not existing_item:
            wishlist_item = WishlistItem(user_id=current_user.id, product_id=product_id)
            db.session.add(wishlist_item)
            db.session.commit()
            log_user_action(current_user.id, 'add_to_wishlist', 'product', product_id)
            flash(f'{product.name} added to wishlist!', 'success')
        else:
            flash(f'{product.name} is already in your wishlist!', 'info')
    
    except Exception as e:
        current_app.logger.error(f"Add to wishlist error: {e}")
        flash('Error adding to wishlist. Please try again.', 'error')
    
    return redirect(url_for('main.product_detail', id=product_id))

@main.route('/remove_from_wishlist/<int:product_id>')
@login_required
def remove_from_wishlist(product_id):
    """Remove product from wishlist"""
    try:
        wishlist_item = WishlistItem.query.filter_by(
            user_id=current_user.id, 
            product_id=product_id
        ).first_or_404()
        
        db.session.delete(wishlist_item)
        db.session.commit()
        flash('Item removed from wishlist!', 'info')
    except Exception as e:
        current_app.logger.error(f"Remove from wishlist error: {e}")
        flash('Error removing from wishlist. Please try again.', 'error')
    
    return redirect(url_for('main.wishlist'))

@main.route('/add_review/<int:product_id>', methods=['POST'])
@login_required
@limiter.limit("3 per hour")
def add_review(product_id):
    """Add product review with security validation"""
    form = ReviewForm()
    
    if form.validate_on_submit():
        try:
            # Check if user already reviewed this product
            existing_review = Review.query.filter_by(
                user_id=current_user.id, 
                product_id=product_id
            ).first()
            
            if existing_review:
                flash('You have already reviewed this product!', 'warning')
            else:
                review = Review(
                    user_id=current_user.id,
                    product_id=product_id,
                    rating=form.rating.data,
                    comment=bleach.clean(form.comment.data, strip=True)  # Sanitize comment
                )
                db.session.add(review)
                db.session.commit()
                log_user_action(current_user.id, 'add_review', 'product', product_id)
                flash('Review added successfully! It will be published after approval.', 'success')
        except Exception as e:
            current_app.logger.error(f"Add review error: {e}")
            flash('Error adding review. Please try again.', 'error')
    
    return redirect(url_for('main.product_detail', id=product_id))

@main.route('/newsletter_signup', methods=['POST'])
@limiter.limit("5 per hour")
def newsletter_signup():
    """Newsletter subscription with validation"""
    form = NewsletterForm()
    
    if form.validate_on_submit():
        try:
            email = form.email.data.lower().strip()
            existing_subscriber = Newsletter.query.filter_by(email=email).first()
            
            if not existing_subscriber:
                newsletter = Newsletter(email=email)
                db.session.add(newsletter)
                db.session.commit()
                flash('Thank you for subscribing to our newsletter!', 'success')
            else:
                flash('Email already subscribed!', 'info')
        except Exception as e:
            current_app.logger.error(f"Newsletter signup error: {e}")
            flash('Error subscribing to newsletter. Please try again.', 'error')
    else:
        flash('Please enter a valid email address.', 'error')
    
    return redirect(url_for('main.index'))

@main.route('/contact', methods=['GET', 'POST'])
@limiter.limit("5 per hour")
def contact():
    """Contact page with form validation"""
    form = ContactForm()
    
    if form.validate_on_submit():
        try:
            contact_msg = ContactMessage(
                name=sanitize_input(form.name.data),
                email=form.email.data.lower().strip(),
                phone=sanitize_input(form.phone.data),
                subject=sanitize_input(form.subject.data),
                message=bleach.clean(form.message.data, strip=True)
            )
            db.session.add(contact_msg)
            db.session.commit()
            flash('Thank you for your message! We will get back to you soon.', 'success')
            return redirect(url_for('main.contact'))
        except Exception as e:
            current_app.logger.error(f"Contact form error: {e}")
            flash('Error sending message. Please try again.', 'error')
    
    return render_template('contact.html', form=form)

@main.route('/about')
def about():
    """About page"""
    return render_template('about.html')

@main.route('/privacy')
def privacy():
    """Privacy policy page"""
    return render_template('privacy.html')

@main.route('/terms')
def terms():
    """Terms and conditions page"""
    return render_template('terms.html')

# AJAX routes with security
@main.route('/api/cart_count')
@limiter.limit("30 per minute")
def api_cart_count():
    """Get current user's cart count"""
    if current_user.is_authenticated:
        count = current_user.get_cart_count()
        return jsonify({'count': count})
    return jsonify({'count': 0})

@main.route('/api/search_suggestions')
@limiter.limit("30 per minute")
def api_search_suggestions():
    """Get search suggestions with validation"""
    query = sanitize_input(request.args.get('q', ''))
    
    if len(query) >= 2:
        try:
            products = Product.query.filter(
                Product.name.contains(query)
            ).filter_by(is_active=True).limit(5).all()
            
            suggestions = [{'id': p.id, 'name': p.name, 'price': p.price} for p in products]
            return jsonify(suggestions)
        except Exception as e:
            current_app.logger.error(f"Search suggestions error: {e}")
            return jsonify([])
    
    return jsonify([])

# Development route (remove in production)
@main.route('/init_sample_data')
@limiter.limit("1 per hour")
def init_sample_data():
    """Initialize sample data (for development only)"""
    if current_app.config.get('DEVELOPMENT'):
        try:
            create_sample_data()
            flash('Sample data created successfully!', 'success')
        except Exception as e:
            current_app.logger.error(f"Sample data creation error: {e}")
            flash('Error creating sample data.', 'error')
    else:
        flash('This feature is not available in production.', 'error')
    
    return redirect(url_for('main.index'))
