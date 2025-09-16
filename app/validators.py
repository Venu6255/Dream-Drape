"""
Custom validators and input sanitization for Dream-Drape application
"""
import re
import bleach
from flask import current_app
from werkzeug.utils import secure_filename
import magic
import os

def sanitize_input(input_data, max_length=None):
    """Sanitize user input to prevent XSS and injection attacks"""
    if input_data is None:
        return None
    
    if not isinstance(input_data, str):
        input_data = str(input_data)
    
    # Remove null bytes and control characters
    sanitized = input_data.replace('\x00', '')
    sanitized = ''.join(char for char in sanitized 
                       if ord(char) >= 32 or char in '\n\t\r')
    
    # Clean HTML tags and malicious content
    sanitized = bleach.clean(sanitized, tags=[], attributes={}, strip=True)
    
    # Trim whitespace
    sanitized = sanitized.strip()
    
    # Enforce maximum length
    if max_length and len(sanitized) > max_length:
        sanitized = sanitized[:max_length]
    
    return sanitized

def validate_email(email):
    """Validate email address format"""
    if not email:
        return False, "Email is required"
    
    email = email.strip().lower()
    
    # Basic email regex pattern
    pattern = r'^[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}$'
    
    if not re.match(pattern, email):
        return False, "Invalid email format"
    
    # Check for suspicious patterns
    suspicious_patterns = [
        r'[<>"\']',  # HTML/SQL injection attempts
        r'javascript:',  # XSS attempts
        r'script',  # Script injection
    ]
    
    for pattern in suspicious_patterns:
        if re.search(pattern, email, re.IGNORECASE):
            return False, "Email contains invalid characters"
    
    if len(email) > 254:  # RFC 5321 limit
        return False, "Email address is too long"
    
    return True, "Valid email"

def validate_phone_number(phone):
    """Validate phone number format"""
    if not phone:
        return True, "Valid phone number"  # Optional field
    
    phone = re.sub(r'[\s\-\(\)]', '', phone.strip())
    
    # Allow international format
    pattern = r'^\+?[\d]{10,15}$'
    
    if not re.match(pattern, phone):
        return False, "Invalid phone number format"
    
    return True, "Valid phone number"

def validate_name(name, field_name="Name"):
    """Validate name fields (first name, last name, etc.)"""
    if not name:
        return False, f"{field_name} is required"
    
    name = name.strip()
    
    if len(name) < 2:
        return False, f"{field_name} must be at least 2 characters long"
    
    if len(name) > 50:
        return False, f"{field_name} must be less than 50 characters"
    
    # Allow letters, spaces, hyphens, and apostrophes
    pattern = r"^[a-zA-Z\s\-']+$"
    
    if not re.match(pattern, name):
        return False, f"{field_name} can only contain letters, spaces, hyphens, and apostrophes"
    
    # Check for suspicious patterns
    if re.search(r'[<>"\']', name):
        return False, f"{field_name} contains invalid characters"
    
    return True, f"Valid {field_name.lower()}"

def validate_username(username):
    """Validate username format"""
    if not username:
        return False, "Username is required"
    
    username = username.strip()
    
    if len(username) < 4:
        return False, "Username must be at least 4 characters long"
    
    if len(username) > 20:
        return False, "Username must be less than 20 characters"
    
    # Allow letters, numbers, and underscores only
    pattern = r'^[a-zA-Z0-9_]+$'
    
    if not re.match(pattern, username):
        return False, "Username can only contain letters, numbers, and underscores"
    
    # Username should not start with numbers
    if username[0].isdigit():
        return False, "Username cannot start with a number"
    
    # Check for reserved usernames
    reserved_usernames = [
        'admin', 'administrator', 'root', 'system', 'api', 'www',
        'ftp', 'mail', 'email', 'user', 'test', 'guest', 'public',
        'support', 'help', 'info', 'contact', 'sales', 'marketing'
    ]
    
    if username.lower() in reserved_usernames:
        return False, "This username is reserved and cannot be used"
    
    return True, "Valid username"

def validate_password(password):
    """Validate password strength"""
    if not password:
        return False, "Password is required"
    
    if len(password) < 8:
        return False, "Password must be at least 8 characters long"
    
    if len(password) > 128:
        return False, "Password is too long"
    
    # Check for required character types
    has_lower = bool(re.search(r'[a-z]', password))
    has_upper = bool(re.search(r'[A-Z]', password))
    has_digit = bool(re.search(r'[0-9]', password))
    has_special = bool(re.search(r'[!@#$%^&*(),.?":{}|<>]', password))
    
    missing = []
    if not has_lower:
        missing.append("lowercase letter")
    if not has_upper:
        missing.append("uppercase letter")
    if not has_digit:
        missing.append("number")
    if not has_special:
        missing.append("special character")
    
    if missing:
        return False, f"Password must contain at least one {', '.join(missing)}"
    
    # Check for common weak patterns
    weak_patterns = [
        r'(.)\1{3,}',  # Repeated characters (aaaa)
        r'(012|123|234|345|456|567|678|789)',  # Sequential numbers
        r'(abc|bcd|cde|def|efg|fgh|ghi|hij|ijk|jkl|klm|lmn|mno|nop|opq|pqr|qrs|rst|stu|tuv|uvw|vwx|wxy|xyz)',  # Sequential letters
        r'password',  # Contains "password"
        r'qwerty',    # QWERTY keyboard pattern
        r'12345',     # Simple numeric sequences
    ]
    
    for pattern in weak_patterns:
        if re.search(pattern, password.lower()):
            return False, "Password contains common patterns and is not secure enough"
    
    return True, "Password meets security requirements"

def validate_file_upload(file_storage):
    """Validate uploaded file for security"""
    if not file_storage:
        return False, "No file provided"
    
    if not file_storage.filename:
        return False, "No filename provided"
    
    # Check file size (5MB limit)
    file_storage.seek(0, os.SEEK_END)
    file_size = file_storage.tell()
    file_storage.seek(0)
    
    max_size = 5 * 1024 * 1024  # 5MB
    if file_size > max_size:
        return False, f"File size exceeds {max_size / (1024*1024):.1f}MB limit"
    
    if file_size == 0:
        return False, "File is empty"
    
    # Validate filename
    filename = secure_filename(file_storage.filename)
    if not filename:
        return False, "Invalid filename"
    
    # Check file extension
    allowed_extensions = {'jpg', 'jpeg', 'png', 'gif'}
    if '.' not in filename:
        return False, "File must have an extension"
    
    extension = filename.rsplit('.', 1)[1].lower()
    if extension not in allowed_extensions:
        return False, f"File type not allowed. Allowed types: {', '.join(allowed_extensions)}"
    
    # Validate file content using magic numbers
    try:
        file_storage.seek(0)
        header = file_storage.read(1024)
        file_storage.seek(0)
        
        file_type = magic.from_buffer(header, mime=True)
        allowed_mime_types = {
            'image/jpeg',
            'image/png', 
            'image/gif'
        }
        
        if file_type not in allowed_mime_types:
            return False, f"File content doesn't match extension. Detected: {file_type}"
            
    except Exception as e:
        current_app.logger.error(f"File validation error: {e}")
        return False, "Unable to validate file content"
    
    return True, "File is valid"

def validate_address(address):
    """Validate address format"""
    if not address:
        return False, "Address is required"
    
    address = address.strip()
    
    if len(address) < 10:
        return False, "Address must be at least 10 characters long"
    
    if len(address) > 500:
        return False, "Address must be less than 500 characters"
    
    # Check for suspicious patterns
    suspicious_patterns = [
        r'[<>"]',  # HTML tags
        r'javascript:',  # XSS attempts
        r'script',  # Script injection
    ]
    
    for pattern in suspicious_patterns:
        if re.search(pattern, address, re.IGNORECASE):
            return False, "Address contains invalid characters"
    
    return True, "Valid address"

def validate_pincode(pincode):
    """Validate Indian pincode format"""
    if not pincode:
        return False, "Pincode is required"
    
    pincode = pincode.strip()
    
    # Indian pincode format: 6 digits
    pattern = r'^\d{6}$'
    
    if not re.match(pattern, pincode):
        return False, "Pincode must be exactly 6 digits"
    
    # First digit should not be 0
    if pincode[0] == '0':
        return False, "Invalid pincode format"
    
    return True, "Valid pincode"

def validate_price(price):
    """Validate price value"""
    try:
        price = float(price)
        
        if price < 0:
            return False, "Price cannot be negative"
        
        if price > 999999.99:
            return False, "Price is too high"
        
        # Check for reasonable decimal places
        if len(str(price).split('.')[-1]) > 2:
            return False, "Price can have at most 2 decimal places"
        
        return True, "Valid price"
        
    except (ValueError, TypeError):
        return False, "Price must be a valid number"

def validate_quantity(quantity):
    """Validate quantity value"""
    try:
        quantity = int(quantity)
        
        if quantity < 0:
            return False, "Quantity cannot be negative"
        
        if quantity > 99999:
            return False, "Quantity is too high"
        
        return True, "Valid quantity"
        
    except (ValueError, TypeError):
        return False, "Quantity must be a valid number"

def validate_search_query(query):
    """Validate search query"""
    if not query:
        return False, "Search query is required"
    
    query = query.strip()
    
    if len(query) < 1:
        return False, "Search query cannot be empty"
    
    if len(query) > 100:
        return False, "Search query is too long"
    
    # Check for suspicious patterns
    suspicious_patterns = [
        r'[<>"\']',  # HTML/SQL injection
        r'javascript:',  # XSS
        r'union\s+select',  # SQL injection
        r'script',  # Script injection
    ]
    
    for pattern in suspicious_patterns:
        if re.search(pattern, query, re.IGNORECASE):
            return False, "Search query contains invalid characters"
    
    return True, "Valid search query"

def validate_order_notes(notes):
    """Validate order notes"""
    if not notes:
        return True, "Valid notes"  # Optional field
    
    notes = notes.strip()
    
    if len(notes) > 1000:
        return False, "Notes must be less than 1000 characters"
    
    # Check for suspicious patterns
    suspicious_patterns = [
        r'[<>"]',  # HTML tags
        r'javascript:',  # XSS attempts
        r'script',  # Script injection
    ]
    
    for pattern in suspicious_patterns:
        if re.search(pattern, notes, re.IGNORECASE):
            return False, "Notes contain invalid characters"
    
    return True, "Valid notes"

def validate_sku(sku):
    """Validate SKU format"""
    if not sku:
        return True, "Valid SKU"  # Optional field
    
    sku = sku.strip().upper()
    
    if len(sku) > 50:
        return False, "SKU must be less than 50 characters"
    
    # Allow letters, numbers, hyphens, and underscores
    pattern = r'^[A-Z0-9_-]+$'
    
    if not re.match(pattern, sku):
        return False, "SKU can only contain letters, numbers, hyphens, and underscores"
    
    return True, "Valid SKU"

def clean_and_validate_input(input_data, field_name, validation_func=None, max_length=None):
    """Clean and validate input data"""
    # Sanitize input
    cleaned_data = sanitize_input(input_data, max_length)
    
    # Apply specific validation if provided
    if validation_func:
        is_valid, message = validation_func(cleaned_data)
        if not is_valid:
            return False, cleaned_data, message
    
    return True, cleaned_data, f"Valid {field_name}"
