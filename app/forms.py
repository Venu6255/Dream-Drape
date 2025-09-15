from flask_wtf import FlaskForm
from flask_wtf.file import FileField, FileAllowed
from wtforms import StringField, TextAreaField, PasswordField, SubmitField, BooleanField, SelectField, IntegerField, FloatField, HiddenField
from wtforms.validators import DataRequired, Email, EqualTo, Length, NumberRange, Optional
from wtforms.widgets import TextArea

class LoginForm(FlaskForm):
    email = StringField('Email', validators=[DataRequired(), Email()])
    password = PasswordField('Password', validators=[DataRequired()])
    remember_me = BooleanField('Remember Me')
    submit = SubmitField('Sign In')

class RegistrationForm(FlaskForm):
    username = StringField('Username', validators=[DataRequired(), Length(min=4, max=20)])
    email = StringField('Email', validators=[DataRequired(), Email()])
    first_name = StringField('First Name', validators=[DataRequired(), Length(max=50)])
    last_name = StringField('Last Name', validators=[DataRequired(), Length(max=50)])
    phone = StringField('Phone Number', validators=[Optional(), Length(max=15)])
    password = PasswordField('Password', validators=[DataRequired(), Length(min=6)])
    password2 = PasswordField('Confirm Password', 
                             validators=[DataRequired(), EqualTo('password')])
    submit = SubmitField('Register')

class ProfileForm(FlaskForm):
    username = StringField('Username', validators=[DataRequired(), Length(min=4, max=20)])
    email = StringField('Email', validators=[DataRequired(), Email()])
    first_name = StringField('First Name', validators=[DataRequired(), Length(max=50)])
    last_name = StringField('Last Name', validators=[DataRequired(), Length(max=50)])
    phone = StringField('Phone Number', validators=[Optional(), Length(max=15)])
    address = TextAreaField('Address', validators=[Optional()])
    city = StringField('City', validators=[Optional(), Length(max=50)])
    state = StringField('State', validators=[Optional(), Length(max=50)])
    pincode = StringField('Pincode', validators=[Optional(), Length(max=10)])
    country = StringField('Country', validators=[Optional(), Length(max=50)])
    submit = SubmitField('Update Profile')

class ChangePasswordForm(FlaskForm):
    current_password = PasswordField('Current Password', validators=[DataRequired()])
    new_password = PasswordField('New Password', validators=[DataRequired(), Length(min=6)])
    confirm_password = PasswordField('Confirm New Password', 
                                   validators=[DataRequired(), EqualTo('new_password')])
    submit = SubmitField('Change Password')

class CheckoutForm(FlaskForm):
    # Shipping information
    first_name = StringField('First Name', validators=[DataRequired(), Length(max=50)])
    last_name = StringField('Last Name', validators=[DataRequired(), Length(max=50)])
    email = StringField('Email', validators=[DataRequired(), Email()])
    phone = StringField('Phone Number', validators=[DataRequired(), Length(max=15)])
    address = TextAreaField('Address', validators=[DataRequired()])
    city = StringField('City', validators=[DataRequired(), Length(max=50)])
    state = StringField('State', validators=[DataRequired(), Length(max=50)])
    pincode = StringField('Pincode', validators=[DataRequired(), Length(max=10)])
    country = StringField('Country', default='India')
    
    # Payment information
    payment_method = SelectField('Payment Method', 
                               choices=[('cod', 'Cash on Delivery'), 
                                      ('razorpay', 'Razorpay'), 
                                      ('stripe', 'Credit Card')],
                               validators=[DataRequired()])
    
    card_number = StringField('Card Number', validators=[Optional(), Length(min=13, max=19)])  # Optional unless credit selected
    card_expiry = StringField('Expiry Date (MM/YY)', validators=[Optional(), Length(min=5, max=5)])
    card_cvv = StringField('CVV', validators=[Optional(), Length(min=3, max=4)])
    
    notes = TextAreaField('Order Notes (Optional)')
    submit = SubmitField('Place Order')

class AddToCartForm(FlaskForm):
    product_id = HiddenField('Product ID', validators=[DataRequired()])
    quantity = IntegerField('Quantity', default=1, validators=[DataRequired(), NumberRange(min=1, max=10)])
    size = SelectField('Size', choices=[], validators=[Optional()])
    color = SelectField('Color', choices=[], validators=[Optional()])
    submit = SubmitField('Add to Cart')

class ReviewForm(FlaskForm):
    rating = SelectField('Rating', 
                        choices=[(5, '5 Stars'), (4, '4 Stars'), (3, '3 Stars'), 
                               (2, '2 Stars'), (1, '1 Star')],
                        coerce=int, validators=[DataRequired()])
    comment = TextAreaField('Review', validators=[DataRequired(), Length(max=500)])
    submit = SubmitField('Submit Review')

class NewsletterForm(FlaskForm):
    email = StringField('Email', validators=[DataRequired(), Email()])
    submit = SubmitField('Subscribe')

class ContactForm(FlaskForm):
    name = StringField('Name', validators=[DataRequired(), Length(max=100)])
    email = StringField('Email', validators=[DataRequired(), Email()])
    phone = StringField('Phone', validators=[Optional(), Length(max=15)])
    subject = StringField('Subject', validators=[Optional(), Length(max=200)])
    message = TextAreaField('Message', validators=[DataRequired(), Length(max=1000)])
    submit = SubmitField('Send Message')

class SearchForm(FlaskForm):
    query = StringField('Search', validators=[DataRequired()])
    category = SelectField('Category', choices=[('', 'All Categories')], validators=[Optional()])
    min_price = FloatField('Min Price', validators=[Optional(), NumberRange(min=0)])
    max_price = FloatField('Max Price', validators=[Optional(), NumberRange(min=0)])
    sort_by = SelectField('Sort By', 
                         choices=[('name_asc', 'Name A-Z'), ('name_desc', 'Name Z-A'),
                                ('price_asc', 'Price Low to High'), ('price_desc', 'Price High to Low'),
                                ('newest', 'Newest First'), ('rating', 'Highest Rated')],
                         default='newest')
    submit = SubmitField('Search')

# Admin Forms
class AdminProductForm(FlaskForm):
    name = StringField('Product Name', validators=[DataRequired(), Length(max=200)])
    description = TextAreaField('Description')
    price = FloatField('Price', validators=[DataRequired(), NumberRange(min=0)])
    original_price = FloatField('Original Price', validators=[Optional(), NumberRange(min=0)])
    sku = StringField('SKU', validators=[Optional(), Length(max=50)])
    stock_quantity = IntegerField('Stock Quantity', default=0, validators=[NumberRange(min=0)])
    image_file = FileField('Product Image', validators=[FileAllowed(['jpg', 'png', 'jpeg'])])
    sizes = StringField('Sizes (comma-separated)', validators=[Optional()])
    colors = StringField('Colors (comma-separated)', validators=[Optional()])
    material = StringField('Material', validators=[Optional(), Length(max=100)])
    care_instructions = TextAreaField('Care Instructions')
    is_featured = BooleanField('Featured Product')
    is_new_arrival = BooleanField('New Arrival')
    is_best_seller = BooleanField('Best Seller')
    is_on_sale = BooleanField('On Sale')
    is_active = BooleanField('Active', default=True)
    submit = SubmitField('Save Product')

class AdminCategoryForm(FlaskForm):
    name = StringField('Category Name', validators=[DataRequired(), Length(max=100)])
    description = TextAreaField('Description')
    image_file = FileField('Category Image', validators=[FileAllowed(['jpg', 'png', 'jpeg'])])
    is_active = BooleanField('Active', default=True)
    submit = SubmitField('Save Category')

class AdminOrderForm(FlaskForm):
    status = SelectField('Order Status', 
                        choices=[('pending', 'Pending'), ('confirmed', 'Confirmed'), 
                               ('shipped', 'Shipped'), ('delivered', 'Delivered'), 
                               ('cancelled', 'Cancelled')],
                        validators=[DataRequired()])
    tracking_number = StringField('Tracking Number', validators=[Optional()])
    notes = TextAreaField('Notes')
    submit = SubmitField('Update Order')

class AdminUserForm(FlaskForm):
    username = StringField('Username', validators=[DataRequired(), Length(min=4, max=20)])
    email = StringField('Email', validators=[DataRequired(), Email()])
    first_name = StringField('First Name', validators=[DataRequired(), Length(max=50)])
    last_name = StringField('Last Name', validators=[DataRequired(), Length(max=50)])
    is_admin = BooleanField('Admin User')
    is_active = BooleanField('Active User', default=True)
    submit = SubmitField('Save User')