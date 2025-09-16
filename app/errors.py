"""
Error handlers for Dream-Drape application
"""
from flask import Blueprint, render_template, request, current_app, jsonify
from app.security import log_security_event, get_client_ip
import traceback

errors = Blueprint('errors', __name__)

@errors.app_errorhandler(400)
def bad_request_error(error):
    """Handle 400 Bad Request errors"""
    current_app.logger.warning(f"Bad request from {get_client_ip()}: {request.url}")
    
    if request.is_json:
        return jsonify({
            'error': 'Bad Request',
            'message': 'The request could not be understood by the server.'
        }), 400
    
    return render_template('errors/400.html'), 400

@errors.app_errorhandler(401)
def unauthorized_error(error):
    """Handle 401 Unauthorized errors"""
    log_security_event('UNAUTHORIZED_ACCESS', 
                      f'Unauthorized access attempt to {request.url}', 
                      severity='WARNING')
    
    if request.is_json:
        return jsonify({
            'error': 'Unauthorized',
            'message': 'Authentication is required to access this resource.'
        }), 401
    
    return render_template('errors/401.html'), 401

@errors.app_errorhandler(403)
def forbidden_error(error):
    """Handle 403 Forbidden errors"""
    log_security_event('FORBIDDEN_ACCESS', 
                      f'Forbidden access attempt to {request.url}', 
                      severity='WARNING')
    
    if request.is_json:
        return jsonify({
            'error': 'Forbidden',
            'message': 'You do not have permission to access this resource.'
        }), 403
    
    return render_template('errors/403.html'), 403

@errors.app_errorhandler(404)
def not_found_error(error):
    """Handle 404 Not Found errors"""
    current_app.logger.info(f"404 error from {get_client_ip()}: {request.url}")
    
    if request.is_json:
        return jsonify({
            'error': 'Not Found',
            'message': 'The requested resource could not be found.'
        }), 404
    
    return render_template('errors/404.html'), 404

@errors.app_errorhandler(413)
def request_entity_too_large_error(error):
    """Handle 413 Request Entity Too Large errors"""
    current_app.logger.warning(f"File too large from {get_client_ip()}: {request.url}")
    
    if request.is_json:
        return jsonify({
            'error': 'File Too Large',
            'message': 'The uploaded file is too large.'
        }), 413
    
    return render_template('errors/413.html'), 413

@errors.app_errorhandler(429)
def rate_limit_error(error):
    """Handle 429 Rate Limit Exceeded errors"""
    log_security_event('RATE_LIMIT_EXCEEDED', 
                      f'Rate limit exceeded from {get_client_ip()}', 
                      severity='WARNING')
    
    if request.is_json:
        return jsonify({
            'error': 'Rate Limit Exceeded',
            'message': 'Too many requests. Please try again later.'
        }), 429
    
    return render_template('errors/429.html'), 429

@errors.app_errorhandler(500)
def internal_error(error):
    """Handle 500 Internal Server errors"""
    current_app.logger.error(f"Internal server error: {error}")
    current_app.logger.error(f"Traceback: {traceback.format_exc()}")
    
    # Roll back any pending database transactions
    from app import db
    db.session.rollback()
    
    if request.is_json:
        return jsonify({
            'error': 'Internal Server Error',
            'message': 'An internal server error occurred.'
        }), 500
    
    return render_template('errors/500.html'), 500

@errors.app_errorhandler(502)
def bad_gateway_error(error):
    """Handle 502 Bad Gateway errors"""
    current_app.logger.error(f"Bad gateway error: {error}")
    
    if request.is_json:
        return jsonify({
            'error': 'Bad Gateway',
            'message': 'Bad gateway error occurred.'
        }), 502
    
    return render_template('errors/502.html'), 502

@errors.app_errorhandler(503)
def service_unavailable_error(error):
    """Handle 503 Service Unavailable errors"""
    current_app.logger.error(f"Service unavailable error: {error}")
    
    if request.is_json:
        return jsonify({
            'error': 'Service Unavailable',
            'message': 'The service is temporarily unavailable.'
        }), 503
    
    return render_template('errors/503.html'), 503

# Custom error handlers
class CustomError(Exception):
    """Base class for custom application errors"""
    status_code = 500
    message = "An error occurred"
    
    def __init__(self, message=None, status_code=None):
        if message:
            self.message = message
        if status_code:
            self.status_code = status_code
        super().__init__(self.message)

class ValidationError(CustomError):
    """Validation error"""
    status_code = 400

class AuthenticationError(CustomError):
    """Authentication error"""
    status_code = 401

class AuthorizationError(CustomError):
    """Authorization error"""
    status_code = 403

class PaymentError(CustomError):
    """Payment processing error"""
    status_code = 402

@errors.app_errorhandler(CustomError)
def handle_custom_error(error):
    """Handle custom application errors"""
    current_app.logger.error(f"Custom error: {error.message}")
    
    if request.is_json:
        return jsonify({
            'error': error.__class__.__name__,
            'message': error.message
        }), error.status_code
    
    return render_template('errors/custom.html', error=error), error.status_code

# Security-related error handlers
@errors.app_errorhandler(Exception)
def handle_unexpected_error(error):
    """Handle unexpected errors with security logging"""
    error_id = current_app.logger.error(f"Unexpected error: {error}")
    current_app.logger.error(f"Traceback: {traceback.format_exc()}")
    
    log_security_event('UNEXPECTED_ERROR', 
                      f'Unexpected error occurred: {str(error)}', 
                      severity='ERROR')
    
    # Roll back any pending database transactions
    from app import db
    db.session.rollback()
    
    if current_app.debug:
        # In debug mode, let Flask handle the error
        raise error
    
    if request.is_json:
        return jsonify({
            'error': 'Internal Server Error',
            'message': 'An unexpected error occurred.',
            'error_id': error_id
        }), 500
    
    return render_template('errors/500.html', error_id=error_id), 500
