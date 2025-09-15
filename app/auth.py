from flask import Blueprint, render_template, redirect, url_for, flash, request
from flask_login import login_user, logout_user, current_user, login_required
from app.models import User, Order
from app.forms import LoginForm, RegistrationForm, ProfileForm, ChangePasswordForm
from app import db

auth = Blueprint('auth', __name__)

@auth.route('/login', methods=['GET', 'POST'])
def login():
    """User login page"""
    if current_user.is_authenticated:
        return redirect(url_for('main.index'))
    
    form = LoginForm()
    
    if form.validate_on_submit():
        user = User.query.filter_by(email=form.email.data).first()
        
        if user and user.check_password(form.password.data) and user.is_active:
            login_user(user, remember=form.remember_me.data)
            
            # Redirect to next page if specified
            next_page = request.args.get('next')
            if next_page:
                return redirect(next_page)
            
            flash(f'Welcome back, {user.first_name}!', 'success')
            return redirect(url_for('main.index'))
        else:
            flash('Invalid email or password. Please try again.', 'error')
    
    return render_template('login.html', form=form, title='Login')

@auth.route('/register', methods=['GET', 'POST'])
def register():
    """User registration page"""
    if current_user.is_authenticated:
        return redirect(url_for('main.index'))
    
    form = RegistrationForm()
    
    if form.validate_on_submit():
        # Check if username or email already exists
        existing_user = User.query.filter(
            (User.username == form.username.data) | 
            (User.email == form.email.data)
        ).first()
        
        if existing_user:
            if existing_user.username == form.username.data:
                flash('Username already exists. Please choose a different one.', 'error')
            else:
                flash('Email already registered. Please use a different email.', 'error')
        else:
            # Create new user
            user = User(
                username=form.username.data,
                email=form.email.data,
                first_name=form.first_name.data,
                last_name=form.last_name.data,
                phone=form.phone.data
            )
            user.set_password(form.password.data)
            
            db.session.add(user)
            db.session.commit()
            
            flash('Registration successful! You can now log in.', 'success')
            return redirect(url_for('auth.login'))
    
    return render_template('register.html', form=form, title='Register')

@auth.route('/logout')
@login_required
def logout():
    """User logout"""
    logout_user()
    flash('You have been logged out successfully.', 'info')
    return redirect(url_for('main.index'))

@auth.route('/profile')
@login_required
def profile():
    """User profile page"""
    # Get user's recent orders
    recent_orders = Order.query.filter_by(user_id=current_user.id).order_by(
        Order.created_at.desc()
    ).limit(5).all()
    
    return render_template('profile.html', user=current_user, orders=recent_orders)

@auth.route('/edit_profile', methods=['GET', 'POST'])
@login_required
def edit_profile():
    """Edit user profile"""
    form = ProfileForm()
    
    if form.validate_on_submit():
        # Check if username or email is being changed to an existing one
        if form.username.data != current_user.username:
            existing_user = User.query.filter_by(username=form.username.data).first()
            if existing_user:
                flash('Username already exists. Please choose a different one.', 'error')
                return render_template('edit_profile.html', form=form)
        
        if form.email.data != current_user.email:
            existing_user = User.query.filter_by(email=form.email.data).first()
            if existing_user:
                flash('Email already registered. Please use a different email.', 'error')
                return render_template('edit_profile.html', form=form)
        
        # Update user information
        current_user.username = form.username.data
        current_user.email = form.email.data
        current_user.first_name = form.first_name.data
        current_user.last_name = form.last_name.data
        current_user.phone = form.phone.data
        current_user.address = form.address.data
        current_user.city = form.city.data
        current_user.state = form.state.data
        current_user.pincode = form.pincode.data
        current_user.country = form.country.data
        
        db.session.commit()
        flash('Profile updated successfully!', 'success')
        return redirect(url_for('auth.profile'))
    
    # Pre-populate form with current user data
    elif request.method == 'GET':
        form.username.data = current_user.username
        form.email.data = current_user.email
        form.first_name.data = current_user.first_name
        form.last_name.data = current_user.last_name
        form.phone.data = current_user.phone
        form.address.data = current_user.address
        form.city.data = current_user.city
        form.state.data = current_user.state
        form.pincode.data = current_user.pincode
        form.country.data = current_user.country
    
    return render_template('edit_profile.html', form=form)

@auth.route('/change_password', methods=['GET', 'POST'])
@login_required
def change_password():
    """Change user password"""
    form = ChangePasswordForm()
    
    if form.validate_on_submit():
        if current_user.check_password(form.current_password.data):
            current_user.set_password(form.new_password.data)
            db.session.commit()
            flash('Password changed successfully!', 'success')
            return redirect(url_for('auth.profile'))
        else:
            flash('Current password is incorrect.', 'error')
    
    return render_template('change_password.html', form=form)

@auth.route('/orders')
@login_required
def my_orders():
    """User orders history"""
    page = request.args.get('page', 1, type=int)
    orders = Order.query.filter_by(user_id=current_user.id).order_by(
        Order.created_at.desc()
    ).paginate(page=page, per_page=10, error_out=False)
    
    return render_template('my_orders.html', orders=orders)

@auth.route('/order/<int:order_id>')
@login_required
def order_detail(order_id):
    """Individual order details"""
    order = Order.query.filter_by(
        id=order_id, 
        user_id=current_user.id
    ).first_or_404()
    
    return render_template('order_detail.html', order=order)

@auth.route('/cancel_order/<int:order_id>')
@login_required
def cancel_order(order_id):
    """Cancel an order"""
    order = Order.query.filter_by(
        id=order_id, 
        user_id=current_user.id
    ).first_or_404()
    
    # Only allow cancellation if order is pending or confirmed
    if order.status in ['pending', 'confirmed']:
        order.status = 'cancelled'
        db.session.commit()
        flash('Order cancelled successfully.', 'info')
    else:
        flash('This order cannot be cancelled.', 'error')
    
    return redirect(url_for('auth.order_detail', order_id=order_id))

@auth.route('/reorder/<int:order_id>')
@login_required
def reorder(order_id):
    """Add all items from previous order to cart"""
    from app.models import CartItem
    
    order = Order.query.filter_by(
        id=order_id, 
        user_id=current_user.id
    ).first_or_404()
    
    items_added = 0
    for order_item in order.order_items:
        # Check if product is still active and in stock
        if order_item.product.is_active and order_item.product.is_in_stock():
            # Check if item already exists in cart
            existing_cart_item = CartItem.query.filter_by(
                user_id=current_user.id,
                product_id=order_item.product_id,
                size=order_item.size,
                color=order_item.color
            ).first()
            
            if existing_cart_item:
                existing_cart_item.quantity += order_item.quantity
            else:
                cart_item = CartItem(
                    user_id=current_user.id,
                    product_id=order_item.product_id,
                    quantity=order_item.quantity,
                    size=order_item.size,
                    color=order_item.color
                )
                db.session.add(cart_item)
            
            items_added += 1
    
    if items_added > 0:
        db.session.commit()
        flash(f'{items_added} items added to cart from your previous order.', 'success')
    else:
        flash('No items could be added to cart. Products may be out of stock.', 'warning')
    
    return redirect(url_for('main.cart'))

# User loader function for Flask-Login
from app import login

@login.user_loader
def load_user(user_id):
    """Load user for Flask-Login"""
    return User.query.get(int(user_id))