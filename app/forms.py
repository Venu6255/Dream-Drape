from flask_wtf import FlaskForm
from flask_wtf.file import FileField, FileAllowed
from wtforms import StringField, TextAreaField, PasswordField, SubmitField, BooleanField, SelectField, IntegerField, FloatField, HiddenField
from wtforms.validators import DataRequired, Email, EqualTo, Length, NumberRange, Optional, ValidationError, Regexp
from wtforms.widgets import TextArea
import re

# Custom Validators
def strong_password(form, field):
    """Validate password strength"""
    password = field.data
    if len(password) < 8:
        raise ValidationError('Password must be at least 8 characters long.')
    if not re.search(r'[A-Z]', password):
        raise ValidationError('Password must contain at least one uppercase letter.')
    if not re.search(r'[a-z]', password):
        raise ValidationError('Password must contain at least one lowercase letter.')
    if not re.search(r'[0-9]', password):
        raise ValidationError('Password must contain at least one number.')
    if not re.search(r'[!@#$%^&*(),.?":{}|<>]', password):
        raise ValidationError('Password must contain at least one special character.')

def no_html_tags(form, field):
    """Prevent HTML tags in input"""
    if field.data and re.search(r'<[^>]*>', field.data):
        raise ValidationError('HTML tags are not allowed.')

def safe_filename_chars(form, field):
    """Validate filename contains only safe characters"""
    if field.data and not re.match(r'^[a-zA-Z0-9._-]+$', field.data):
        raise ValidationError('Only letters, numbers, dots, hyphens, and underscores are allowed.')

class LoginForm(FlaskForm):
    email = StringField('Email', validators=[
        DataRequired(message='Email is required.'), 
        Email(message='Please enter a valid email address.'),
        Length(max=120, message='Email must be less than 120 characters.')
    ])
    password = PasswordField('Password', validators=[
        DataRequired(message='Password is required.'),
        Length(min=1, max=255, message='Password length is invalid.')
    ])
    remember_me = BooleanField('Remember Me')
    submit = SubmitField('Sign In')

class RegistrationForm(FlaskForm):
    username = StringField('Username', validators=[
        DataRequired(message='Username is required.'), 
        Length(min=4, max=20, message='Username must be between 4 and 20 characters.'),
        Regexp(r'^[a-zA-Z0-9_]+$', message='Username can only contain letters, numbers, and underscores.'),
        no_html_tags
    ])
    email = StringField('Email', validators=[
        DataRequired(message='Email is required.'), 
        Email(message='Please enter a valid email address.'),
        Length(max=120, message='Email must be less than 120 characters.')
    ])
    first_name = StringField('First Name', validators=[
        DataRequired(message='First name is required.'), 
        Length(min=1, max=50, message='First name must be less than 50 characters.'),
        Regexp(r'^[a-zA-Z\s]+$', message='First name can only contain letters and spaces.'),
        no_html_tags
    ])
    last_name = StringField('Last Name', validators=[
        DataRequired(message='Last name is required.'), 
        Length(min=1, max=50, message='Last name must be less than 50 characters.'),
        Regexp(r'^[a-zA-Z\s]+$', message='Last name can only contain letters and spaces.'),
        no_html_tags
    ])
    phone = StringField('Phone Number', validators=[
        Optional(), 
        Length(max=15, message='Phone number must be less than 15 characters.'),
        Regexp(r'^\+?[\d\s\-\(\)]+$', message='Please enter a valid phone number.')
    ])
    password = PasswordField('Password', validators=[
        DataRequired(message='Password is required.'),
        strong_password
    ])
    password2 = PasswordField('Confirm Password', validators=[
        DataRequired(message='Please confirm your password.'),
        EqualTo('password', message='Passwords must match.')
    ])
    submit = SubmitField('Register')

class ProfileForm(FlaskForm):
    username = StringField('Username', validators=[
        DataRequired(message='Username is required.'), 
        Length(min=4, max=20, message='Username must be between 4 and 20 characters.'),
        Regexp(r'^[a-zA-Z0-9_]+$', message='Username can only contain letters, numbers, and underscores.'),
        no_html_tags
    ])
    email = StringField('Email', validators=[
        DataRequired(message='Email is required.'), 
        Email(message='Please enter a valid email address.'),
        Length(max=120, message='Email must be less than 120 characters.')
    ])
    first_name = StringField('First Name', validators=[
        DataRequired(message='First name is required.'), 
        Length(min=1, max=50, message='First name must be less than 50 characters.'),
        Regexp(r'^[a-zA-Z\s]+$', message='First name can only contain letters and spaces.'),
        no_html_tags
    ])
    last_name = StringField('Last Name', validators=[
        DataRequired(message='Last name is required.'), 
        Length(min=1, max=50, message='Last name must be less than 50 characters.'),
        Regexp(r'^[a-zA-Z\s]+$', message='Last name can only contain letters and spaces.'),
        no_html_tags
    ])
    phone = StringField('Phone Number', validators=[
        Optional(), 
        Length(max=15, message='Phone number must be less than 15 characters.'),
        Regexp(r'^\+?[\d\s\-\(\)]+$', message='Please enter a valid phone number.')
    ])
    address = TextAreaField('Address', validators=[
        Optional(), 
        Length(max=500, message='Address must be less than 500 characters.'),
        no_html_tags
    ])
    city = StringField('City', validators=[
        Optional(), 
        Length(max=50, message='City must be less than 50 characters.'),
        Regexp(r'^[a-zA-Z\s]+$', message='City can only contain letters and spaces.'),
        no_html_tags
    ])
    state = StringField('State', validators=[
        Optional(), 
        Length(max=50, message='State must be less than 50 characters.'),
        Regexp(r'^[a-zA-Z\s]+$', message='State can only contain letters and spaces.'),
        no_html_tags
    ])
    pincode = StringField('Pincode', validators=[
        Optional(), 
        Length(max=10, message='Pincode must be less than 10 characters.'),
        Regexp(r'^\d{5,6}$', message='Please enter a valid pincode.')
    ])
    country = StringField('Country', validators=[
        Optional(), 
        Length(max=50, message='Country must be less than 50 characters.'),
        Regexp(r'^[a-zA-Z\s]+$', message='Country can only contain letters and spaces.'),
        no_html_tags
    ])
    submit = SubmitField('Update Profile')

class ChangePasswordForm(FlaskForm):
    current_password = PasswordField('Current Password', validators=[
        DataRequired(message='Current password is required.')
    ])
    new_password = PasswordField('New Password', validators=[
        DataRequired(message='New password is required.'),
        strong_password
    ])
    confirm_password = PasswordField('Confirm New Password', validators=[
        DataRequired(message='Please confirm your new password.'),
        EqualTo('new_password', message='Passwords must match.')
    ])
    submit = SubmitField('Change Password')

class CheckoutForm(FlaskForm):
    # Shipping information
    first_name = StringField('First Name', validators=[
        DataRequired(message='First name is required.'), 
        Length(min=1, max=50, message='First name must be less than 50 characters.'),
        Regexp(r'^[a-zA-Z\s]+$', message='First name can only contain letters and spaces.'),
        no_html_tags
    ])
    last_name = StringField('Last Name', validators=[
        DataRequired(message='Last name is required.'), 
        Length(min=1, max=50, message='Last name must be less than 50 characters.'),
        Regexp(r'^[a-zA-Z\s]+$', message='Last name can only contain letters and spaces.'),
        no_html_tags
    ])
    email = StringField('Email', validators=[
        DataRequired(message='Email is required.'), 
        Email(message='Please enter a valid email address.'),
        Length(max=120, message='Email must be less than 120 characters.')
    ])
    phone = StringField('Phone Number', validators=[
        DataRequired(message='Phone number is required.'), 
        Length(max=15, message='Phone number must be less than 15 characters.'),
        Regexp(r'^\+?[\d\s\-\(\)]+$', message='Please enter a valid phone number.')
    ])
    address = TextAreaField('Address', validators=[
        DataRequired(message='Address is required.'),
        Length(min=10, max=500, message='Address must be between 10 and 500 characters.'),
        no_html_tags
    ])
    city = StringField('City', validators=[
        DataRequired(message='City is required.'), 
        Length(min=1, max=50, message='City must be less than 50 characters.'),
        Regexp(r'^[a-zA-Z\s]+$', message='City can only contain letters and spaces.'),
        no_html_tags
    ])
    state = StringField('State', validators=[
        DataRequired(message='State is required.'), 
        Length(min=1, max=50, message='State must be less than 50 characters.'),
        Regexp(r'^[a-zA-Z\s]+$', message='State can only contain letters and spaces.'),
        no_html_tags
    ])
    pincode = StringField('Pincode', validators=[
        DataRequired(message='Pincode is required.'), 
        Length(min=5, max=10, message='Pincode must be between 5 and 10 characters.'),
        Regexp(r'^\d{5,6}$', message='Please enter a valid pincode.')
    ])
    country = StringField('Country', default='India', validators=[
        DataRequired(message='Country is required.'),
        Length(max=50, message='Country must be less than 50 characters.'),
        no_html_tags
    ])
    
    # Payment information
    payment_method = SelectField('Payment Method', 
                               choices=[('cod', 'Cash on Delivery'), 
                                      ('razorpay', 'Razorpay'), 
                                      ('stripe', 'Credit Card')],
                               validators=[DataRequired(message='Please select a payment method.')])
    
    card_number = StringField('Card Number', validators=[
        Optional(), 
        Length(min=13, max=19, message='Card number must be between 13 and 19 digits.'),
        Regexp(r'^\d+$', message='Card number can only contain digits.')
    ])
    card_expiry = StringField('Expiry Date (MM/YY)', validators=[
        Optional(), 
        Length(min=5, max=5, message='Expiry date must be in MM/YY format.'),
        Regexp(r'^\d{2}/\d{2}$', message='Expiry date must be in MM/YY format.')
    ])
    card_cvv = StringField('CVV', validators=[
        Optional(), 
        Length(min=3, max=4, message='CVV must be 3 or 4 digits.'),
        Regexp(r'^\d{3,4}$', message='CVV can only contain digits.')
    ])
    
    notes = TextAreaField('Order Notes (Optional)', validators=[
        Optional(),
        Length(max=1000, message='Notes must be less than 1000 characters.'),
        no_html_tags
    ])
    submit = SubmitField('Place Order')

class AddToCartForm(FlaskForm):
    product_id = HiddenField('Product ID', validators=[
        DataRequired(message='Product ID is required.')
    ])
    quantity = IntegerField('Quantity', default=1, validators=[
        DataRequired(message='Quantity is required.'),
        NumberRange(min=1, max=10, message='Quantity must be between 1 and 10.')
    ])
    size = SelectField('Size', choices=[], validators=[Optional()])
    color = SelectField('Color', choices=[], validators=[Optional()])
    submit = SubmitField('Add to Cart')

class ReviewForm(FlaskForm):
    rating = SelectField('Rating', 
                        choices=[(5, '5 Stars'), (4, '4 Stars'), (3, '3 Stars'), 
                               (2, '2 Stars'), (1, '1 Star')],
                        coerce=int, validators=[
                            DataRequired(message='Please select a rating.')
                        ])
    comment = TextAreaField('Review', validators=[
        DataRequired(message='Review comment is required.'), 
        Length(min=10, max=500, message='Review must be between 10 and 500 characters.'),
        no_html_tags
    ])
    submit = SubmitField('Submit Review')

class NewsletterForm(FlaskForm):
    email = StringField('Email', validators=[
        DataRequired(message='Email is required.'), 
        Email(message='Please enter a valid email address.'),
        Length(max=120, message='Email must be less than 120 characters.')
    ])
    submit = SubmitField('Subscribe')

class ContactForm(FlaskForm):
    name = StringField('Name', validators=[
        DataRequired(message='Name is required.'), 
        Length(min=2, max=100, message='Name must be between 2 and 100 characters.'),
        Regexp(r'^[a-zA-Z\s]+$', message='Name can only contain letters and spaces.'),
        no_html_tags
    ])
    email = StringField('Email', validators=[
        DataRequired(message='Email is required.'), 
        Email(message='Please enter a valid email address.'),
        Length(max=120, message='Email must be less than 120 characters.')
    ])
    phone = StringField('Phone', validators=[
        Optional(), 
        Length(max=15, message='Phone number must be less than 15 characters.'),
        Regexp(r'^\+?[\d\s\-\(\)]+$', message='Please enter a valid phone number.')
    ])
    subject = StringField('Subject', validators=[
        Optional(), 
        Length(max=200, message='Subject must be less than 200 characters.'),
        no_html_tags
    ])
    message = TextAreaField('Message', validators=[
        DataRequired(message='Message is required.'), 
        Length(min=10, max=1000, message='Message must be between 10 and 1000 characters.'),
        no_html_tags
    ])
    submit = SubmitField('Send Message')

class SearchForm(FlaskForm):
    query = StringField('Search', validators=[
        DataRequired(message='Search query is required.'),
        Length(min=1, max=100, message='Search query must be less than 100 characters.'),
        no_html_tags
    ])
    category = SelectField('Category', choices=[('', 'All Categories')], validators=[Optional()])
    min_price = FloatField('Min Price', validators=[
        Optional(), 
        NumberRange(min=0, max=999999, message='Price must be between 0 and 999999.')
    ])
    max_price = FloatField('Max Price', validators=[
        Optional(), 
        NumberRange(min=0, max=999999, message='Price must be between 0 and 999999.')
    ])
    sort_by = SelectField('Sort By', 
                         choices=[('name_asc', 'Name A-Z'), ('name_desc', 'Name Z-A'),
                                ('price_asc', 'Price Low to High'), ('price_desc', 'Price High to Low'),
                                ('newest', 'Newest First'), ('rating', 'Highest Rated')],
                         default='newest')
    submit = SubmitField('Search')

# Admin Forms with Enhanced Security
class AdminProductForm(FlaskForm):
    name = StringField('Product Name', validators=[
        DataRequired(message='Product name is required.'), 
        Length(min=2, max=200, message='Product name must be between 2 and 200 characters.'),
        no_html_tags
    ])
    description = TextAreaField('Description', validators=[
        Optional(),
        Length(max=5000, message='Description must be less than 5000 characters.')
    ])
    price = FloatField('Price', validators=[
        DataRequired(message='Price is required.'),
        NumberRange(min=0.01, max=999999.99, message='Price must be between 0.01 and 999999.99.')
    ])
    original_price = FloatField('Original Price', validators=[
        Optional(),
        NumberRange(min=0.01, max=999999.99, message='Original price must be between 0.01 and 999999.99.')
    ])
    sku = StringField('SKU', validators=[
        Optional(), 
        Length(max=50, message='SKU must be less than 50 characters.'),
        Regexp(r'^[a-zA-Z0-9_-]*$', message='SKU can only contain letters, numbers, hyphens, and underscores.')
    ])
    stock_quantity = IntegerField('Stock Quantity', default=0, validators=[
        NumberRange(min=0, max=99999, message='Stock quantity must be between 0 and 99999.')
    ])
    image_file = FileField('Product Image', validators=[
        FileAllowed(['jpg', 'png', 'jpeg'], message='Only JPG, PNG, and JPEG files are allowed.')
    ])
    sizes = StringField('Sizes (comma-separated)', validators=[
        Optional(),
        Length(max=200, message='Sizes must be less than 200 characters.'),
        no_html_tags
    ])
    colors = StringField('Colors (comma-separated)', validators=[
        Optional(),
        Length(max=200, message='Colors must be less than 200 characters.'),
        no_html_tags
    ])
    material = StringField('Material', validators=[
        Optional(), 
        Length(max=100, message='Material must be less than 100 characters.'),
        no_html_tags
    ])
    care_instructions = TextAreaField('Care Instructions', validators=[
        Optional(),
        Length(max=1000, message='Care instructions must be less than 1000 characters.')
    ])
    is_featured = BooleanField('Featured Product')
    is_new_arrival = BooleanField('New Arrival')
    is_best_seller = BooleanField('Best Seller')
    is_on_sale = BooleanField('On Sale')
    is_active = BooleanField('Active', default=True)
    submit = SubmitField('Save Product')

class AdminCategoryForm(FlaskForm):
    name = StringField('Category Name', validators=[
        DataRequired(message='Category name is required.'), 
        Length(min=2, max=100, message='Category name must be between 2 and 100 characters.'),
        no_html_tags
    ])
    description = TextAreaField('Description', validators=[
        Optional(),
        Length(max=1000, message='Description must be less than 1000 characters.')
    ])
    image_file = FileField('Category Image', validators=[
        FileAllowed(['jpg', 'png', 'jpeg'], message='Only JPG, PNG, and JPEG files are allowed.')
    ])
    is_active = BooleanField('Active', default=True)
    submit = SubmitField('Save Category')

class AdminOrderForm(FlaskForm):
    status = SelectField('Order Status', 
                        choices=[('pending', 'Pending'), ('confirmed', 'Confirmed'), 
                               ('shipped', 'Shipped'), ('delivered', 'Delivered'), 
                               ('cancelled', 'Cancelled')],
                        validators=[DataRequired(message='Order status is required.')])
    tracking_number = StringField('Tracking Number', validators=[
        Optional(),
        Length(max=100, message='Tracking number must be less than 100 characters.'),
        Regexp(r'^[a-zA-Z0-9_-]*$', message='Tracking number can only contain letters, numbers, hyphens, and underscores.')
    ])
    notes = TextAreaField('Notes', validators=[
        Optional(),
        Length(max=1000, message='Notes must be less than 1000 characters.'),
        no_html_tags
    ])
    submit = SubmitField('Update Order')

class AdminUserForm(FlaskForm):
    username = StringField('Username', validators=[
        DataRequired(message='Username is required.'), 
        Length(min=4, max=20, message='Username must be between 4 and 20 characters.'),
        Regexp(r'^[a-zA-Z0-9_]+$', message='Username can only contain letters, numbers, and underscores.'),
        no_html_tags
    ])
    email = StringField('Email', validators=[
        DataRequired(message='Email is required.'), 
        Email(message='Please enter a valid email address.'),
        Length(max=120, message='Email must be less than 120 characters.')
    ])
    first_name = StringField('First Name', validators=[
        DataRequired(message='First name is required.'), 
        Length(min=1, max=50, message='First name must be less than 50 characters.'),
        Regexp(r'^[a-zA-Z\s]+$', message='First name can only contain letters and spaces.'),
        no_html_tags
    ])
    last_name = StringField('Last Name', validators=[
        DataRequired(message='Last name is required.'), 
        Length(min=1, max=50, message='Last name must be less than 50 characters.'),
        Regexp(r'^[a-zA-Z\s]+$', message='Last name can only contain letters and spaces.'),
        no_html_tags
    ])
    is_admin = BooleanField('Admin User')
    is_active = BooleanField('Active User', default=True)
    submit = SubmitField('Save User')
