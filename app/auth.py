from flask import Blueprint, render_template, redirect, url_for, flash, request, current_app
from flask_login import login_user, logout_user, current_user, login_required
from app.models import User, Order, AuditLog
from app.forms import LoginForm, RegistrationForm, ProfileForm, ChangePasswordForm
from app.validators import sanitize_input
from app.security import log_user_action, is_safe_url
from app import db, limiter
from datetime import datetime, timedelta
import bleach

auth = Blueprint('auth', __name__)

@auth.route('/login', methods=['GET', 'POST'])
@limiter.limit("10 per 15 minutes")
def login():
    """User login page with security enhancements"""
    if current_user.is_authenticated:
        return redirect(url_for('main.index'))
    
    form = LoginForm()
    
    if form.validate_on_submit():
        try:
            email = form.email.data.lower().strip()
            user = User.query.filter_by(email=email).first()
            
            # Check if user exists and account is not locked
            if user and user.is_account_locked():
                flash('Account temporarily locked due to too many failed login attempts. Please try again later.', 'error')
                return render_template('login.html', form=form, title='Login')
            
            if user and user.check_password(form.password.data) and user.is_active:
                # Reset failed login attempts on successful login
                user.failed_login_attempts = 0
                user.locked_until = None
                user.last_login = datetime.utcnow()
                db.session.commit()
                
                login_user(user, remember=form.remember_me.data)
                log_user_action(user.id, 'login', 'user', user.id)
                
                # Redirect to next page if specified and safe
                next_page = request.args.get('next')
                if next_page and is_safe_url(next_page):
                    return redirect(next_page)
                
                flash(f'Welcome back, {user.first_name}!', 'success')
                return redirect(url_for('main.index'))
            else:
                # Handle failed login attempt
                if user:
                    user.failed_login_attempts += 1
                    if user.failed_login_attempts >= 5:
                        user.locked_until = datetime.utcnow() + timedelta(minutes=30)
                    db.session.commit()
                
                # Log failed login attempt
                log_user_action(None, 'failed_login', 'user', None, 
                              details=f"Failed login attempt for email: {email}")
                
                flash('Invalid email or password. Please try again.', 'error')
                
        except Exception as e:
            current_app.logger.error(f"Login error: {e}")
            flash('Login error. Please try again.', 'error')
    
    return render_template('login.html', form=form, title='Login')

@auth.route('/register', methods=['GET', 'POST'])
@limiter.limit("5 per hour")
def register():
    """User registration page with enhanced validation"""
    if current_user.is_authenticated:
        return redirect(url_for('main.index'))
    
    form = RegistrationForm()
    
    if form.validate_on_submit():
        try:
            # Sanitize inputs
            username = sanitize_input(form.username.data)
            email = form.email.data.lower().strip()
            first_name = sanitize_input(form.first_name.data)
            last_name = sanitize_input(form.last_name.data)
            phone = sanitize_input(form.phone.data) if form.phone.data else None
            
            # Check if username or email already exists
            existing_user = User.query.filter(
                (User.username == username) | 
                (User.email == email)
            ).first()
            
            if existing_user:
                if existing_user.username == username:
                    flash('Username already exists. Please choose a different one.', 'error')
                else:
                    flash('Email already registered. Please use a different email.', 'error')
            else:
                # Create new user with password validation
                user = User(
                    username=username,
                    email=email,
                    first_name=first_name,
                    last_name=last_name,
                    phone=phone
                )
                
                # This will validate password strength
                user.set_password(form.password.data)
                
                db.session.add(user)
                db.session.commit()
                
                log_user_action(user.id, 'register', 'user', user.id)
                
                flash('Registration successful! You can now log in.', 'success')
                return redirect(url_for('auth.login'))
                
        except ValueError as e:
            flash(str(e), 'error')
        except Exception as e:
            current_app.logger.error(f"Registration error: {e}")
            flash('Registration error. Please try again.', 'error')
    
    return render_template('register.html', form=form, title='Register')

@auth.route('/logout')
@login_required
def logout():
    """User logout with logging"""
    if current_user.is_authenticated:
        log_user_action(current_user.id, 'logout', 'user', current_user.id)
    
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
@limiter.limit("10 per hour")
def edit_profile():
    """Edit user profile with validation"""
    form = ProfileForm()
    
    if form.validate_on_submit():
        try:
            # Sanitize inputs
            username = sanitize_input(form.username.data)
            email = form.email.data.lower().strip()
            
            # Check if username or email is being changed to an existing one
            if username != current_user.username:
                existing_user = User.query.filter_by(username=username).first()
                if existing_user:
                    flash('Username already exists. Please choose a different one.', 'error')
                    return render_template('edit_profile.html', form=form)
            
            if email != current_user.email:
                existing_user = User.query.filter_by(email=email).first()
                if existing_user:
                    flash('Email already registered. Please use a different email.', 'error')
                    return render_template('edit_profile.html', form=form)
            
            # Update user information
            current_user.username = username
            current_user.email = email
            current_user.first_name = sanitize_input(form.first_name.data)
            current_user.last_name = sanitize_input(form.last_name.data)
            current_user.phone = sanitize_input(form.phone.data) if form.phone.data else None
            current_user.address = sanitize_input(form.address.data) if form.address.data else None
            current_user.city = sanitize_input(form.city.data) if form.city.data else None
            current_user.state = sanitize_input(form.state.data) if form.state.data else None
            current_user.pincode = sanitize_input(form.pincode.data) if form.pincode.data else None
            current_user.country = sanitize_input(form.country.data) if form.country.data else None
            
            db.session.commit()
            log_user_action(current_user.id, 'update_profile', 'user', current_user.id)
            flash('Profile updated successfully!', 'success')
            return redirect(url_for('auth.profile'))
            
        except Exception as e:
            current_app.logger.error(f"Profile update error: {e}")
            flash('Error updating profile. Please try again.', 'error')
    
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
@limiter.limit("5 per hour")
def change_password():
    """Change user password with enhanced security"""
    form = ChangePasswordForm()
    
    if form.validate_on_submit():
        try:
            if current_user.check_password(form.current_password.data):
                # Validate new password strength
                current_user.set_password(form.new_password.data)
                db.session.commit()
                log_user_action(current_user.id, 'change_password', 'user', current_user.id)
                flash('Password changed successfully!', 'success')
                return redirect(url_for('auth.profile'))
            else:
                flash('Current password is incorrect.', 'error')
        except ValueError as e:
            flash(str(e), 'error')
        except Exception as e:
            current_app.logger.error(f"Password change error: {e}")
            flash('Error changing password. Please try again.', 'error')
    
    return render_template('change_password.html', form=form)

@auth.route('/orders')
@login_required
def my_orders():
    """User orders history with pagination"""
    page = request.args.get('page', 1, type=int)
    
    try:
        orders = Order.query.filter_by(user_id=current_user.id).order_by(
            Order.created_at.desc()
        ).paginate(page=page, per_page=10, error_out=False)
    except Exception as e:
        current_app.logger.error(f"Orders page error: {e}")
        flash('Error loading orders. Please try again.', 'error')
        orders = None
    
    return render_template('my_orders.html', orders=orders)

@auth.route('/order/<int:order_id>')
@login_required
def order_detail(order_id):
    """Individual order details with security check"""
    try:
        order = Order.query.filter_by(
            id=order_id, 
            user_id=current_user.id
        ).first_or_404()
        
        return render_template('order_detail.html', order=order)
    except Exception as e:
        current_app.logger.error(f"Order detail error: {e}")
        flash('Error loading order details.', 'error')
        return redirect(url_for('auth.my_orders'))

@auth.route('/cancel_order/<int:order_id>')
@login_required
@limiter.limit("5 per hour")
def cancel_order(order_id):
    """Cancel an order with validation"""
    try:
        order = Order.query.filter_by(
            id=order_id, 
            user_id=current_user.id
        ).first_or_404()
        
        # Only allow cancellation if order is pending or confirmed
        if order.status in ['pending', 'confirmed']:
            order.status = 'cancelled'
            
            # Restore stock
            for item in order.order_items:
                if item.product:
                    item.product.stock_quantity += item.quantity
            
            db.session.commit()
            log_user_action(current_user.id, 'cancel_order', 'order', order_id)
            flash('Order cancelled successfully.', 'info')
        else:
            flash('This order cannot be cancelled.', 'error')
    except Exception as e:
        current_app.logger.error(f"Cancel order error: {e}")
        flash('Error cancelling order. Please try again.', 'error')
    
    return redirect(url_for('auth.order_detail', order_id=order_id))

@auth.route('/reorder/<int:order_id>')
@login_required
@limiter.limit("5 per hour")
def reorder(order_id):
    """Add all items from previous order to cart with validation"""
    from app.models import CartItem
    
    try:
        order = Order.query.filter_by(
            id=order_id, 
            user_id=current_user.id
        ).first_or_404()
        
        items_added = 0
        for order_item in order.order_items:
            # Check if product is still active and in stock
            if order_item.product and order_item.product.is_active and order_item.product.is_in_stock():
                # Check if item already exists in cart
                existing_cart_item = CartItem.query.filter_by(
                    user_id=current_user.id,
                    product_id=order_item.product_id,
                    size=order_item.size,
                    color=order_item.color
                ).first()
                
                quantity_to_add = min(order_item.quantity, order_item.product.stock_quantity)
                
                if existing_cart_item:
                    new_quantity = existing_cart_item.quantity + quantity_to_add
                    if new_quantity <= order_item.product.stock_quantity:
                        existing_cart_item.quantity = new_quantity
                    else:
                        existing_cart_item.quantity = order_item.product.stock_quantity
                else:
                    cart_item = CartItem(
                        user_id=current_user.id,
                        product_id=order_item.product_id,
                        quantity=quantity_to_add,
                        size=order_item.size,
                        color=order_item.color
                    )
                    db.session.add(cart_item)
                
                items_added += 1
        
        if items_added > 0:
            db.session.commit()
            log_user_action(current_user.id, 'reorder', 'order', order_id)
            flash(f'{items_added} items added to cart from your previous order.', 'success')
        else:
            flash('No items could be added to cart. Products may be out of stock.', 'warning')
            
    except Exception as e:
        current_app.logger.error(f"Reorder error: {e}")
        flash('Error processing reorder. Please try again.', 'error')
    
    return redirect(url_for('main.cart'))

# User loader function for Flask-Login
from app import login

@login.user_loader
def load_user(user_id):
    """Load user for Flask-Login with error handling"""
    try:
        return User.query.get(int(user_id))
    except Exception as e:
        current_app.logger.error(f"User loader error: {e}")
        return None
