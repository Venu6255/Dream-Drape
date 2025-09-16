from datetime import datetime
from flask_sqlalchemy import SQLAlchemy
from flask_login import UserMixin
from werkzeug.security import generate_password_hash, check_password_hash
from sqlalchemy import Index
import re
from app import db

# Association table for many-to-many relationship between products and categories
product_categories = db.Table('product_categories',
    db.Column('product_id', db.Integer, db.ForeignKey('product.id'), primary_key=True),
    db.Column('category_id', db.Integer, db.ForeignKey('category.id'), primary_key=True)
)

class User(UserMixin, db.Model):
    id = db.Column(db.Integer, primary_key=True)
    username = db.Column(db.String(80), unique=True, nullable=False, index=True)
    email = db.Column(db.String(120), unique=True, nullable=False, index=True)
    password_hash = db.Column(db.String(255), nullable=False)
    first_name = db.Column(db.String(50), nullable=False)
    last_name = db.Column(db.String(50), nullable=False)
    phone = db.Column(db.String(15))
    address = db.Column(db.Text)
    city = db.Column(db.String(50))
    state = db.Column(db.String(50))
    pincode = db.Column(db.String(10))
    country = db.Column(db.String(50), default='India')
    is_admin = db.Column(db.Boolean, default=False, index=True)
    is_active = db.Column(db.Boolean, default=True, index=True)
    created_at = db.Column(db.DateTime, default=datetime.utcnow, index=True)
    last_login = db.Column(db.DateTime)
    failed_login_attempts = db.Column(db.Integer, default=0)
    locked_until = db.Column(db.DateTime)
    
    # Relationships
    orders = db.relationship('Order', backref='user', lazy=True)
    cart_items = db.relationship('CartItem', backref='user', lazy=True)
    wishlist_items = db.relationship('WishlistItem', backref='user', lazy=True)
    reviews = db.relationship('Review', backref='user', lazy=True)
    
    def set_password(self, password):
        if not self.validate_password_strength(password):
            raise ValueError("Password does not meet security requirements")
        self.password_hash = generate_password_hash(password)
        
    def check_password(self, password):
        return check_password_hash(self.password_hash, password)
    
    @staticmethod
    def validate_password_strength(password):
        """Validate password meets security requirements"""
        if len(password) < 8:
            return False
        if not re.search(r'[A-Z]', password):
            return False
        if not re.search(r'[a-z]', password):
            return False
        if not re.search(r'[0-9]', password):
            return False
        return True
    
    def get_full_name(self):
        return f"{self.first_name} {self.last_name}"
    
    def get_cart_total(self):
        return sum(item.get_total() for item in self.cart_items)
    
    def get_cart_count(self):
        return sum(item.quantity for item in self.cart_items)
    
    def is_account_locked(self):
        return self.locked_until and self.locked_until > datetime.utcnow()

class Category(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(100), unique=True, nullable=False, index=True)
    description = db.Column(db.Text)
    image_url = db.Column(db.String(255))
    is_active = db.Column(db.Boolean, default=True, index=True)
    created_at = db.Column(db.DateTime, default=datetime.utcnow, index=True)
    
    def __repr__(self):
        return f'<Category {self.name}>'

class Product(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(200), nullable=False, index=True)
    description = db.Column(db.Text)
    price = db.Column(db.Float, nullable=False, index=True)
    original_price = db.Column(db.Float)
    sku = db.Column(db.String(50), unique=True, index=True)
    stock_quantity = db.Column(db.Integer, default=0, index=True)
    image_url = db.Column(db.String(255))
    additional_images = db.Column(db.Text)  # JSON string of image URLs
    sizes = db.Column(db.String(200))  # Comma-separated sizes
    colors = db.Column(db.String(200))  # Comma-separated colors
    material = db.Column(db.String(100))
    care_instructions = db.Column(db.Text)
    is_featured = db.Column(db.Boolean, default=False, index=True)
    is_new_arrival = db.Column(db.Boolean, default=False, index=True)
    is_best_seller = db.Column(db.Boolean, default=False, index=True)
    is_on_sale = db.Column(db.Boolean, default=False, index=True)
    is_active = db.Column(db.Boolean, default=True, index=True)
    created_at = db.Column(db.DateTime, default=datetime.utcnow, index=True)
    updated_at = db.Column(db.DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    
    # Relationships
    categories = db.relationship('Category', secondary=product_categories, backref='products')
    cart_items = db.relationship('CartItem', backref='product', lazy=True)
    order_items = db.relationship('OrderItem', backref='product', lazy=True)
    wishlist_items = db.relationship('WishlistItem', backref='product', lazy=True)
    reviews = db.relationship('Review', backref='product', lazy=True)
    
    def get_discount_percentage(self):
        if self.original_price and self.original_price > self.price:
            return round(((self.original_price - self.price) / self.original_price) * 100)
        return 0
    
    def get_average_rating(self):
        if self.reviews:
            return sum(review.rating for review in self.reviews) / len(self.reviews)
        return 0
    
    def get_size_list(self):
        return [size.strip() for size in self.sizes.split(',')] if self.sizes else []
    
    def get_color_list(self):
        return [color.strip() for color in self.colors.split(',')] if self.colors else []
    
    def is_in_stock(self):
        return self.stock_quantity > 0

class CartItem(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey('user.id'), nullable=False, index=True)
    product_id = db.Column(db.Integer, db.ForeignKey('product.id'), nullable=False, index=True)
    quantity = db.Column(db.Integer, default=1)
    size = db.Column(db.String(10))
    color = db.Column(db.String(50))
    added_at = db.Column(db.DateTime, default=datetime.utcnow, index=True)
    
    def get_total(self):
        return self.product.price * self.quantity

class WishlistItem(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey('user.id'), nullable=False, index=True)
    product_id = db.Column(db.Integer, db.ForeignKey('product.id'), nullable=False, index=True)
    added_at = db.Column(db.DateTime, default=datetime.utcnow, index=True)

class Order(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey('user.id'), nullable=False, index=True)
    order_number = db.Column(db.String(50), unique=True, nullable=False, index=True)
    total_amount = db.Column(db.Float, nullable=False, index=True)
    status = db.Column(db.String(50), default='pending', index=True)  # pending, confirmed, shipped, delivered, cancelled
    payment_status = db.Column(db.String(50), default='pending', index=True)  # pending, paid, failed, refunded
    payment_method = db.Column(db.String(50))
    payment_id = db.Column(db.String(100))
    
    # Shipping details
    shipping_address = db.Column(db.Text, nullable=False)
    shipping_city = db.Column(db.String(50), nullable=False)
    shipping_state = db.Column(db.String(50), nullable=False)
    shipping_pincode = db.Column(db.String(10), nullable=False)
    shipping_country = db.Column(db.String(50), default='India')
    shipping_phone = db.Column(db.String(15))
    
    tracking_number = db.Column(db.String(100))
    notes = db.Column(db.Text)
    
    created_at = db.Column(db.DateTime, default=datetime.utcnow, index=True)
    updated_at = db.Column(db.DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    
    # Relationships
    order_items = db.relationship('OrderItem', backref='order', lazy=True, cascade='all, delete-orphan')
    
    def generate_order_number(self):
        import uuid
        self.order_number = f"DD{datetime.now().strftime('%Y%m%d')}{str(uuid.uuid4())[:8].upper()}"

class OrderItem(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    order_id = db.Column(db.Integer, db.ForeignKey('order.id'), nullable=False, index=True)
    product_id = db.Column(db.Integer, db.ForeignKey('product.id'), nullable=False, index=True)
    quantity = db.Column(db.Integer, nullable=False)
    price = db.Column(db.Float, nullable=False)  # Price at time of order
    size = db.Column(db.String(10))
    color = db.Column(db.String(50))
    
    def get_total(self):
        return self.price * self.quantity

class Review(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey('user.id'), nullable=False, index=True)
    product_id = db.Column(db.Integer, db.ForeignKey('product.id'), nullable=False, index=True)
    rating = db.Column(db.Integer, nullable=False, index=True)  # 1-5 stars
    comment = db.Column(db.Text)
    is_approved = db.Column(db.Boolean, default=False, index=True)
    created_at = db.Column(db.DateTime, default=datetime.utcnow, index=True)
    
    def __repr__(self):
        return f'<Review {self.rating} stars for {self.product.name}>'

class Newsletter(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    email = db.Column(db.String(120), unique=True, nullable=False, index=True)
    is_active = db.Column(db.Boolean, default=True, index=True)
    subscribed_at = db.Column(db.DateTime, default=datetime.utcnow, index=True)

class ContactMessage(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(100), nullable=False)
    email = db.Column(db.String(120), nullable=False, index=True)
    phone = db.Column(db.String(15))
    subject = db.Column(db.String(200))
    message = db.Column(db.Text, nullable=False)
    is_read = db.Column(db.Boolean, default=False, index=True)
    created_at = db.Column(db.DateTime, default=datetime.utcnow, index=True)

# Audit Log Model
class AuditLog(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey('user.id'), index=True)
    action = db.Column(db.String(100), nullable=False, index=True)
    resource_type = db.Column(db.String(50), index=True)
    resource_id = db.Column(db.Integer, index=True)
    details = db.Column(db.Text)
    ip_address = db.Column(db.String(45))
    user_agent = db.Column(db.String(255))
    created_at = db.Column(db.DateTime, default=datetime.utcnow, index=True)

# Create additional indexes
Index('idx_user_email_active', User.email, User.is_active)
Index('idx_product_active_featured', Product.is_active, Product.is_featured)
Index('idx_order_user_created', Order.user_id, Order.created_at)
