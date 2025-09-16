import os
import secrets
from werkzeug.utils import secure_filename
from PIL import Image
from flask import current_app
import uuid
from datetime import datetime
import bleach
try:
    import magic
    MAGIC_AVAILABLE = True
except ImportError:
    MAGIC_AVAILABLE = False
    print("Warning: python-magic not available. File validation will be limited.")

def save_picture(form_picture, folder):
    """Save uploaded picture with enhanced security validation"""
    try:
        # Validate file type using python-magic
        if not validate_image_file(form_picture):
            raise ValueError("Invalid file type")
        
        # Generate secure filename
        random_hex = secrets.token_hex(8)
        _, f_ext = os.path.splitext(form_picture.filename)
        
        # Validate file extension
        allowed_extensions = {'.png', '.jpg', '.jpeg', '.gif'}
        if f_ext.lower() not in allowed_extensions:
            raise ValueError("File extension not allowed")
        
        picture_fn = random_hex + f_ext.lower()
        picture_path = os.path.join(current_app.root_path, 'static', folder, picture_fn)
        
        # Create directory if it doesn't exist
        os.makedirs(os.path.dirname(picture_path), exist_ok=True)
        
        # Open and validate image
        img = Image.open(form_picture)
        
        # Remove EXIF data for security
        if hasattr(img, 'getexif'):
            img = remove_exif(img)
        
        # Resize image to prevent large file attacks
        max_size = (1200, 1200)
        img.thumbnail(max_size, Image.Resampling.LANCZOS)
        
        # Convert to RGB if necessary
        if img.mode in ("RGBA", "P"):
            img = img.convert("RGB")
        
        # Save with optimization
        img.save(picture_path, optimize=True, quality=85)
        
        return picture_fn
        
    except Exception as e:
        current_app.logger.error(f"Image save error: {e}")
        raise ValueError("Failed to save image")

def validate_image_file(file_storage):
    """Validate image file using magic numbers"""
    if not MAGIC_AVAILABLE:
        # Fallback validation without magic
        filename = file_storage.filename.lower() if file_storage.filename else ""
        allowed_extensions = {'.jpg', '.jpeg', '.png', '.gif'}
        return any(filename.endswith(ext) for ext in allowed_extensions)
    
    try:
        # Read first 1024 bytes to check file signature
        file_storage.seek(0)
        header = file_storage.read(1024)
        file_storage.seek(0)
        
        # Use python-magic to detect actual file type
        file_type = magic.from_buffer(header, mime=True)
        
        allowed_types = {
            'image/jpeg',
            'image/png', 
            'image/gif',
            'image/webp'
        }
        
        return file_type in allowed_types
        
    except Exception:
        return False

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
    
    # Validate file content (simplified for Windows)
    if MAGIC_AVAILABLE:
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
            # Don't fail completely, just warn
            pass
    
    return True, "File is valid"

def remove_exif(image):
    """Remove EXIF data from image for security"""
    try:
        # Create a new image without EXIF data
        data = list(image.getdata())
        image_without_exif = Image.new(image.mode, image.size)
        image_without_exif.putdata(data)
        return image_without_exif
    except Exception:
        return image

def delete_picture(picture_fn, folder):
    """Safely delete picture from specified folder"""
    if picture_fn:
        try:
            picture_path = os.path.join(current_app.root_path, 'static', folder, picture_fn)
            if os.path.exists(picture_path):
                os.remove(picture_path)
                return True
        except Exception as e:
            current_app.logger.error(f"File deletion error: {e}")
    return False

def generate_order_number():
    """Generate cryptographically secure order number"""
    timestamp = datetime.now().strftime('%Y%m%d%H%M%S')
    random_part = secrets.token_hex(4).upper()
    return f"DD{timestamp}{random_part}"

def format_currency(amount):
    """Format amount as Indian currency with validation"""
    try:
        if amount is None:
            return "₹0.00"
        return f"₹{float(amount):,.2f}"
    except (ValueError, TypeError):
        return "₹0.00"

def calculate_discount_percentage(original_price, sale_price):
    """Calculate discount percentage with validation"""
    try:
        if not original_price or not sale_price or original_price <= 0 or sale_price < 0:
            return 0
        if original_price > sale_price:
            return round(((original_price - sale_price) / original_price) * 100)
        return 0
    except (ValueError, TypeError, ZeroDivisionError):
        return 0

def allowed_file(filename, allowed_extensions=None):
    """Check if file extension is allowed with enhanced validation"""
    if allowed_extensions is None:
        allowed_extensions = {'png', 'jpg', 'jpeg', 'gif'}
    
    if not filename or '.' not in filename:
        return False
    
    extension = filename.rsplit('.', 1)[1].lower()
    return extension in allowed_extensions

def sanitize_filename(filename):
    """Sanitize filename for secure storage"""
    if not filename:
        return 'unnamed'
    
    # Remove path separators and dangerous characters
    filename = os.path.basename(filename)
    filename = "".join(c for c in filename if c.isalnum() or c in (' ', '-', '_', '.'))
    filename = filename.strip()
    
    # Limit length
    if len(filename) > 100:
        name, ext = os.path.splitext(filename)
        filename = name[:90] + ext
    
    return filename or 'unnamed'

def get_cart_total(cart_items):
    """Calculate total amount for cart items with validation"""
    try:
        return sum(item.get_total() for item in cart_items if item and item.get_total())
    except Exception:
        return 0.0

def get_cart_count(cart_items):
    """Get total number of items in cart with validation"""
    try:
        return sum(item.quantity for item in cart_items if item and item.quantity)
    except Exception:
        return 0

def send_email(to, subject, template, **kwargs):
    """Send email using Flask-Mail with enhanced error handling"""
    from flask_mail import Message
    from app import mail
    
    try:
        if not to or not subject:
            return False
        
        msg = Message(
            subject=f'Dream & Drape - {subject}',
            sender=current_app.config['MAIL_USERNAME'],
            recipients=[to] if isinstance(to, str) else to
        )
        msg.html = template
        mail.send(msg)
        return True
    except Exception as e:
        current_app.logger.error(f"Email send error: {e}")
        return False

def create_sample_data():
    """Create sample products and categories for testing with enhanced validation"""
    from app.models import Category, Product, User
    from app import db
    
    try:
        # Create categories with validation
        categories_data = [
            {'name': 'New Arrivals', 'description': 'Latest fashion trends'},
            {'name': 'Anarkali Suits', 'description': 'Elegant Anarkali collection'},
            {'name': 'Sarees', 'description': 'Traditional and modern sarees'},
            {'name': 'Kurtis', 'description': 'Comfortable and stylish kurtis'},
            {'name': 'Lehenga', 'description': 'Bridal and party lehengas'},
            {'name': 'Best Sellers', 'description': 'Most popular items'},
            {'name': 'Sale', 'description': 'Discounted products'}
        ]
        
        for cat_data in categories_data:
            if not Category.query.filter_by(name=cat_data['name']).first():
                category = Category(**cat_data)
                db.session.add(category)
        
        db.session.commit()
        
        # Create sample products with enhanced validation
        products_data = [
            {
                'name': 'Cotton Print Kurti',
                'description': 'Comfortable cotton kurti perfect for daily wear. Features beautiful prints and breathable fabric for all-day comfort.',
                'price': 899.0,
                'original_price': 1299.0,
                'stock_quantity': 25,
                'sizes': 'S, M, L, XL, XXL',
                'colors': 'White, Blue, Pink, Yellow',
                'material': 'Pure Cotton',
                'care_instructions': 'Machine wash cold, tumble dry low',
                'is_new_arrival': True,
                'is_featured': True,
                'is_on_sale': True
            },
            {
                'name': 'Designer Silk Saree',
                'description': 'Premium silk saree with intricate border work. Perfect for weddings and special occasions.',
                'price': 5999.0,
                'original_price': 7999.0,
                'stock_quantity': 8,
                'sizes': 'One Size',
                'colors': 'Red, Maroon, Navy Blue, Golden',
                'material': 'Pure Silk',
                'care_instructions': 'Dry clean only',
                'is_featured': True,
                'is_best_seller': True,
                'is_on_sale': True
            },
            {
                'name': 'Elegant Pink Anarkali',
                'description': 'Beautiful pink anarkali with gold work and embellishments. Stunning outfit for festive occasions.',
                'price': 2999.0,
                'original_price': 3499.0,
                'stock_quantity': 12,
                'sizes': 'S, M, L, XL',
                'colors': 'Pink, Rose Gold, Peach',
                'material': 'Georgette with Embroidery',
                'care_instructions': 'Dry clean recommended',
                'is_new_arrival': True,
                'is_featured': True,
                'is_best_seller': True
            },
            {
                'name': 'Floral Print Anarkali',
                'description': 'Light and comfortable floral anarkali perfect for casual and semi-formal occasions.',
                'price': 1999.0,
                'original_price': 2499.0,
                'stock_quantity': 18,
                'sizes': 'S, M, L, XL',
                'colors': 'White, Pink, Green, Blue',
                'material': 'Cotton Blend',
                'care_instructions': 'Machine wash gentle cycle',
                'is_new_arrival': True,
                'is_on_sale': True
            },
            {
                'name': 'Royal Blue Lehenga',
                'description': 'Stunning royal blue lehenga with gold work. Perfect for weddings, receptions, and grand celebrations.',
                'price': 8999.0,
                'original_price': 12999.0,
                'stock_quantity': 6,
                'sizes': 'S, M, L, XL',
                'colors': 'Royal Blue, Navy Blue, Midnight Blue',
                'material': 'Silk with Heavy Embroidery',
                'care_instructions': 'Dry clean only, store in garment bag',
                'is_featured': True,
                'is_best_seller': True,
                'is_on_sale': True
            }
        ]
        
        # Get categories for assignment
        categories = {cat.name: cat for cat in Category.query.all()}
        
        for prod_data in products_data:
            if not Product.query.filter_by(name=prod_data['name']).first():
                product = Product(**prod_data)
                product.sku = f"DD{secrets.token_hex(4).upper()}"
                db.session.add(product)
                db.session.flush()  # Get the product ID
                
                # Assign categories based on product type
                if 'Anarkali' in product.name:
                    if 'Anarkali Suits' in categories:
                        product.categories.append(categories['Anarkali Suits'])
                elif 'Saree' in product.name:
                    if 'Sarees' in categories:
                        product.categories.append(categories['Sarees'])
                elif 'Kurti' in product.name:
                    if 'Kurtis' in categories:
                        product.categories.append(categories['Kurtis'])
                elif 'Lehenga' in product.name:
                    if 'Lehenga' in categories:
                        product.categories.append(categories['Lehenga'])
                
                # Assign additional categories based on flags
                if product.is_new_arrival and 'New Arrivals' in categories:
                    product.categories.append(categories['New Arrivals'])
                if product.is_best_seller and 'Best Sellers' in categories:
                    product.categories.append(categories['Best Sellers'])
                if product.is_on_sale and 'Sale' in categories:
                    product.categories.append(categories['Sale'])
        
        db.session.commit()
        current_app.logger.info("Sample data created successfully!")
        return True
        
    except Exception as e:
        current_app.logger.error(f"Sample data creation error: {e}")
        db.session.rollback()
        return False

def validate_price(price):
    """Validate price input"""
    try:
        price = float(price)
        return price >= 0
    except (ValueError, TypeError):
        return False

def validate_quantity(quantity):
    """Validate quantity input"""
    try:
        quantity = int(quantity)
        return 0 <= quantity <= 10000
    except (ValueError, TypeError):
        return False

def clean_html(text):
    """Clean HTML content using bleach"""
    if not text:
        return ""
    
    allowed_tags = ['p', 'br', 'strong', 'em', 'u', 'ol', 'ul', 'li']
    allowed_attributes = {}
    
    return bleach.clean(text, tags=allowed_tags, attributes=allowed_attributes, strip=True)

def init_payment_gateways():
    """Initialize payment gateway configurations with validation"""
    try:
        payment_config = {
            'razorpay': {
                'key_id': current_app.config.get('RAZORPAY_KEY_ID'),
                'key_secret': current_app.config.get('RAZORPAY_KEY_SECRET')
            },
            'stripe': {
                'public_key': current_app.config.get('STRIPE_PUBLIC_KEY'),
                'secret_key': current_app.config.get('STRIPE_SECRET_KEY')
            }
        }
        
        # Validate configuration
        for gateway, config in payment_config.items():
            if not all(config.values()):
                current_app.logger.warning(f"{gateway} configuration incomplete")
        
        return payment_config
    except Exception as e:
        current_app.logger.error(f"Payment gateway initialization error: {e}")
        return {}

def generate_secure_token():
    """Generate cryptographically secure token"""
    return secrets.token_urlsafe(32)

def mask_sensitive_data(data, mask_char='*'):
    """Mask sensitive data for logging"""
    if not data or len(data) <= 4:
        return mask_char * len(data) if data else ""
    
    return data[:2] + mask_char * (len(data) - 4) + data[-2:]
