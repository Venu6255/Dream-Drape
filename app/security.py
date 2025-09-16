"""
Security utilities, validators, and decorators for Dream-Drape application
"""
from flask import request, current_app
from flask_login import current_user
from app.models import AuditLog
from app import db
from datetime import datetime
from urllib.parse import urlparse, urljoin
import logging
import ipaddress

def log_user_action(user_id, action, resource_type=None, resource_id=None, details=None):
    """Log user actions for security auditing"""
    try:
        audit_log = AuditLog(
            user_id=user_id,
            action=action,
            resource_type=resource_type,
            resource_id=resource_id,
            details=details,
            ip_address=get_client_ip(),
            user_agent=request.headers.get('User-Agent', '')[:255]
        )
        db.session.add(audit_log)
        db.session.commit()
    except Exception as e:
        current_app.logger.error(f"Failed to log user action: {e}")

def get_client_ip():
    """Get client IP address with proxy support"""
    if request.environ.get('HTTP_X_FORWARDED_FOR') is None:
        return request.environ.get('REMOTE_ADDR', 'unknown')
    else:
        # Get the first IP in case of multiple proxies
        return request.environ['HTTP_X_FORWARDED_FOR'].split(',')[0].strip()

def is_safe_url(target):
    """Check if a redirect URL is safe"""
    if not target:
        return False
    
    ref_url = urlparse(request.host_url)
    test_url = urlparse(urljoin(request.host_url, target))
    
    return (test_url.scheme in ('http', 'https') and 
            ref_url.netloc == test_url.netloc)

def validate_ip_address(ip_str):
    """Validate IP address format"""
    try:
        ipaddress.ip_address(ip_str)
        return True
    except ValueError:
        return False

def check_rate_limit_exceeded(user_id=None, ip_address=None, action=None, time_window=3600, max_attempts=10):
    """Check if rate limit is exceeded for specific action"""
    try:
        from datetime import timedelta
        
        time_threshold = datetime.utcnow() - timedelta(seconds=time_window)
        
        query = AuditLog.query.filter(AuditLog.created_at >= time_threshold)
        
        if user_id:
            query = query.filter(AuditLog.user_id == user_id)
        elif ip_address:
            query = query.filter(AuditLog.ip_address == ip_address)
        
        if action:
            query = query.filter(AuditLog.action == action)
        
        attempt_count = query.count()
        return attempt_count >= max_attempts
        
    except Exception as e:
        current_app.logger.error(f"Rate limit check error: {e}")
        return False

def log_security_event(event_type, details, severity='INFO'):
    """Log security-related events"""
    security_logger = logging.getLogger('security')
    
    log_data = {
        'event_type': event_type,
        'details': details,
        'ip_address': get_client_ip(),
        'user_agent': request.headers.get('User-Agent', ''),
        'user_id': current_user.id if current_user.is_authenticated else None,
        'timestamp': datetime.utcnow().isoformat()
    }
    
    log_message = f"Security Event: {event_type} - {details}"
    
    if severity == 'CRITICAL':
        security_logger.critical(log_message, extra=log_data)
    elif severity == 'ERROR':
        security_logger.error(log_message, extra=log_data)
    elif severity == 'WARNING':
        security_logger.warning(log_message, extra=log_data)
    else:
        security_logger.info(log_message, extra=log_data)

def sanitize_user_input(input_string, max_length=None):
    """Sanitize user input to prevent injection attacks"""
    if not input_string:
        return ""
    
    # Remove null bytes
    cleaned = input_string.replace('\x00', '')
    
    # Remove control characters except newlines and tabs
    cleaned = ''.join(char for char in cleaned if ord(char) >= 32 or char in '\n\t')
    
    # Trim whitespace
    cleaned = cleaned.strip()
    
    # Enforce maximum length
    if max_length and len(cleaned) > max_length:
        cleaned = cleaned[:max_length]
    
    return cleaned

def validate_csrf_token():
    """Validate CSRF token for form submissions"""
    from flask_wtf.csrf import validate_csrf
    from wtforms.validators import ValidationError
    
    try:
        validate_csrf(request.form.get('csrf_token'))
        return True
    except ValidationError:
        log_security_event('CSRF_TOKEN_INVALID', 
                         f'Invalid CSRF token from IP: {get_client_ip()}', 
                         severity='WARNING')
        return False

def check_password_complexity(password):
    """Check password complexity requirements"""
    import re
    
    if len(password) < 8:
        return False, "Password must be at least 8 characters long"
    
    if not re.search(r'[A-Z]', password):
        return False, "Password must contain at least one uppercase letter"
    
    if not re.search(r'[a-z]', password):
        return False, "Password must contain at least one lowercase letter"
    
    if not re.search(r'[0-9]', password):
        return False, "Password must contain at least one number"
    
    if not re.search(r'[!@#$%^&*(),.?":{}|<>]', password):
        return False, "Password must contain at least one special character"
    
    # Check for common patterns
    common_patterns = [
        r'(.)\1{2,}',  # Repeated characters
        r'(012|123|234|345|456|567|678|789|890)',  # Sequential numbers
        r'(abc|bcd|cde|def|efg|fgh|ghi|hij|ijk|jkl|klm|lmn|mno|nop|opq|pqr|qrs|rst|stu|tuv|uvw|vwx|wxy|xyz)'  # Sequential letters
    ]
    
    for pattern in common_patterns:
        if re.search(pattern, password.lower()):
            return False, "Password contains common patterns and is not secure"
    
    return True, "Password meets complexity requirements"

def generate_secure_session_token():
    """Generate cryptographically secure session token"""
    import secrets
    return secrets.token_urlsafe(32)

def hash_sensitive_data(data):
    """Hash sensitive data for storage"""
    import hashlib
    import secrets
    
    salt = secrets.token_bytes(32)
    pwdhash = hashlib.pbkdf2_hmac('sha256', data.encode('utf-8'), salt, 100000)
    return salt + pwdhash

def verify_sensitive_data(stored_data, provided_data):
    """Verify hashed sensitive data"""
    import hashlib
    
    salt = stored_data[:32]
    stored_hash = stored_data[32:]
    pwdhash = hashlib.pbkdf2_hmac('sha256', provided_data.encode('utf-8'), salt, 100000)
    return pwdhash == stored_hash

class SecurityDecorator:
    """Security decorators for enhanced protection"""
    
    @staticmethod
    def require_fresh_login(f):
        """Require fresh login for sensitive operations"""
        from functools import wraps
        from flask import session, redirect, url_for, flash
        
        @wraps(f)
        def decorated_function(*args, **kwargs):
            if not current_user.is_authenticated:
                return redirect(url_for('auth.login'))
            
            # Check if login is fresh (within last 30 minutes)
            if 'login_time' not in session:
                flash('Please log in again to perform this action.', 'warning')
                return redirect(url_for('auth.login'))
            
            login_time = datetime.fromisoformat(session['login_time'])
            if (datetime.utcnow() - login_time).seconds > 1800:  # 30 minutes
                flash('Please log in again to perform this action.', 'warning')
                return redirect(url_for('auth.login'))
            
            return f(*args, **kwargs)
        return decorated_function
    
    @staticmethod
    def log_access(resource_type):
        """Log access to sensitive resources"""
        def decorator(f):
            from functools import wraps
            
            @wraps(f)
            def decorated_function(*args, **kwargs):
                log_user_action(
                    current_user.id if current_user.is_authenticated else None,
                    f'access_{resource_type}',
                    resource_type,
                    kwargs.get('id'),
                    f'Accessed {resource_type} endpoint'
                )
                return f(*args, **kwargs)
            return decorated_function
        return decorator

def check_suspicious_activity(user_id=None, ip_address=None):
    """Check for suspicious activity patterns"""
    try:
        from datetime import timedelta
        
        # Check for rapid successive logins
        if user_id:
            recent_logins = AuditLog.query.filter(
                AuditLog.user_id == user_id,
                AuditLog.action == 'login',
                AuditLog.created_at >= datetime.utcnow() - timedelta(minutes=5)
            ).count()
            
            if recent_logins > 3:
                return True, "Multiple rapid login attempts detected"
        
        # Check for multiple failed attempts from same IP
        if ip_address:
            failed_attempts = AuditLog.query.filter(
                AuditLog.ip_address == ip_address,
                AuditLog.action == 'failed_login',
                AuditLog.created_at >= datetime.utcnow() - timedelta(hours=1)
            ).count()
            
            if failed_attempts > 5:
                return True, "Multiple failed login attempts from same IP"
        
        return False, "No suspicious activity detected"
        
    except Exception as e:
        current_app.logger.error(f"Suspicious activity check error: {e}")
        return False, "Unable to check for suspicious activity"
