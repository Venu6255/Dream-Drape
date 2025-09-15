import os
import secrets
from PIL import Image
from flask import current_app
import uuid
from datetime import datetime

def save_picture(form_picture, folder):
    """Save uploaded picture to specified folder"""
    random_hex = secrets.token_hex(8)
    _, f_ext = os.path.splitext(form_picture.filename)
    picture_fn = random_hex + f_ext
    picture_path = os.path.join(current_app.root_path, 'static', folder, picture_fn)
    
    # Create directory if it doesn't exist
    os.makedirs(os.path.dirname(picture_path), exist_ok=True)
    
    # Resize image
    output_size = (800, 800)
    img = Image.open(form_picture)
    img.thumbnail(output_size)
    img.save(picture_path)
    
    return picture_fn

def delete_picture(picture_fn, folder):
    """Delete picture from specified folder"""
    if picture_fn:
        picture_path = os.path.join(current_app.root_path, 'static', folder, picture_fn)
        if os.path.exists(picture_path):
            os.remove(picture_path)

def generate_order_number():
    """Generate unique order number"""
    timestamp = datetime.now().strftime('%Y%m%d%H%M%S')
    random_part = str(uuid.uuid4())[:8].upper()
    return f"DD{timestamp}{random_part}"

def format_currency(amount):
    """Format amount as Indian currency"""
    return f"₹{amount:,.2f}"

def calculate_discount_percentage(original_price, sale_price):
    """Calculate discount percentage"""
    if original_price and original_price > sale_price:
        return round(((original_price - sale_price) / original_price) * 100)
    return 0

def allowed_file(filename, allowed_extensions={'png', 'jpg', 'jpeg', 'gif'}):
    """Check if file extension is allowed"""
    return '.' in filename and \
           filename.rsplit('.', 1)[1].lower() in allowed_extensions

def get_cart_total(cart_items):
    """Calculate total amount for cart items"""
    return sum(item.get_total() for item in cart_items)

def get_cart_count(cart_items):
    """Get total number of items in cart"""
    return sum(item.quantity for item in cart_items)

def send_email(to, subject, template, **kwargs):
    """Send email using Flask-Mail"""
    from flask_mail import Message
    from app import mail
    
    msg = Message(
        subject=f'Dream & Drape - {subject}',
        sender=current_app.config['MAIL_USERNAME'],
        recipients=[to]
    )
    msg.html = template
    try:
        mail.send(msg)
        return True
    except Exception as e:
        print(f"Failed to send email: {e}")
        return False

def create_sample_data():
    """Create sample products and categories for testing"""
    from app.models import Category, Product, User
    from app import db
    
    # Create categories
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
        category = Category.query.filter_by(name=cat_data['name']).first()
        if not category:
            category = Category(**cat_data)
            db.session.add(category)
    
    db.session.commit()
    
    # Create your 5 specific products with images
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
            'image_url': 'cotton_print_kurti.jpg',
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
            'image_url': 'designer_silk_saree.jpg',
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
            'image_url': 'elegant_pink_anarkali.jpg',
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
            'image_url': 'floral_print_anarkali.jpg',
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
            'image_url': 'royal_blue_lehenga.jpg',
            'is_featured': True,
            'is_best_seller': True,
            'is_on_sale': True
        }
    ]
    
    # Get categories for assignment
    anarkali_category = Category.query.filter_by(name='Anarkali Suits').first()
    saree_category = Category.query.filter_by(name='Sarees').first()
    kurti_category = Category.query.filter_by(name='Kurtis').first()
    lehenga_category = Category.query.filter_by(name='Lehenga').first()
    new_arrivals_category = Category.query.filter_by(name='New Arrivals').first()
    best_sellers_category = Category.query.filter_by(name='Best Sellers').first()
    sale_category = Category.query.filter_by(name='Sale').first()
    
    for prod_data in products_data:
        product = Product.query.filter_by(name=prod_data['name']).first()
        if not product:
            product = Product(**prod_data)
            product.sku = f"DD{secrets.token_hex(4).upper()}"
            db.session.add(product)
            db.session.flush()  # Get the product ID
            
            # Assign categories based on product type
            if 'Anarkali' in product.name:
                if anarkali_category:
                    product.categories.append(anarkali_category)
            elif 'Saree' in product.name:
                if saree_category:
                    product.categories.append(saree_category)
            elif 'Kurti' in product.name:
                if kurti_category:
                    product.categories.append(kurti_category)
            elif 'Lehenga' in product.name:
                if lehenga_category:
                    product.categories.append(lehenga_category)
            
            # Assign additional categories based on flags
            if product.is_new_arrival and new_arrivals_category:
                product.categories.append(new_arrivals_category)
            if product.is_best_seller and best_sellers_category:
                product.categories.append(best_sellers_category)
            if product.is_on_sale and sale_category:
                product.categories.append(sale_category)
    
    db.session.commit()
    print("Your 5 Dream & Drape products created successfully!")

def init_payment_gateways():
    """Initialize payment gateway configurations"""
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
    return payment_config