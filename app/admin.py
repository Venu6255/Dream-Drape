from flask import Blueprint, render_template, request, flash, redirect, url_for, jsonify, current_app
from flask_login import login_required, current_user
from functools import wraps
from app.models import Product, Category, User, Order, Review, Newsletter, ContactMessage, AuditLog
from app.forms import AdminProductForm, AdminCategoryForm, AdminOrderForm, AdminUserForm
from app.utils import save_picture, delete_picture
from app.validators import sanitize_input, validate_file_upload
from app.security import log_user_action
from app import db, limiter, cache
from sqlalchemy import func, extract
from datetime import datetime, timedelta
import os
import bleach

admin = Blueprint('admin', __name__)

def admin_required(f):
    """Decorator to require admin privileges with logging"""
    @wraps(f)
    def decorated_function(*args, **kwargs):
        if not current_user.is_authenticated or not current_user.is_admin:
            log_user_action(current_user.id if current_user.is_authenticated else None, 
                          'unauthorized_admin_access', 'admin', None)
            flash('Access denied. Admin privileges required.', 'error')
            return redirect(url_for('main.index'))
        return f(*args, **kwargs)
    return decorated_function

@admin.route('/')
@login_required
@admin_required
@cache.cached(timeout=60)  # Cache dashboard for 1 minute
def dashboard():
    """Admin dashboard with statistics and security monitoring"""
    try:
        # Get statistics
        total_products = Product.query.count()
        total_users = User.query.filter_by(is_admin=False).count()
        total_orders = Order.query.count()
        pending_orders = Order.query.filter_by(status='pending').count()
        
        # Recent orders
        recent_orders = Order.query.order_by(Order.created_at.desc()).limit(5).all()
        
        # Low stock products (critical inventory)
        low_stock_products = Product.query.filter(Product.stock_quantity <= 5, Product.is_active == True).all()
        
        # Pending reviews
        pending_reviews = Review.query.filter_by(is_approved=False).count()
        
        # Contact messages
        unread_messages = ContactMessage.query.filter_by(is_read=False).count()
        
        # Security metrics
        recent_failed_logins = AuditLog.query.filter_by(action='failed_login').filter(
            AuditLog.created_at >= datetime.utcnow() - timedelta(hours=24)
        ).count()
        
        return render_template('admin/admin_dashboard.html',
                             total_products=total_products,
                             total_users=total_users,
                             total_orders=total_orders,
                             pending_orders=pending_orders,
                             recent_orders=recent_orders,
                             low_stock_products=low_stock_products,
                             pending_reviews=pending_reviews,
                             unread_messages=unread_messages,
                             recent_failed_logins=recent_failed_logins)
    
    except Exception as e:
        current_app.logger.error(f"Admin dashboard error: {e}")
        flash('Error loading dashboard data.', 'error')
        return render_template('admin/admin_dashboard.html')

# Product Management with Enhanced Security
@admin.route('/products')
@login_required
@admin_required
def manage_products():
    """Manage products page with search and pagination"""
    page = request.args.get('page', 1, type=int)
    search = sanitize_input(request.args.get('search', ''))
    category = sanitize_input(request.args.get('category', ''))
    
    try:
        query = Product.query
        
        if search:
            clean_search = bleach.clean(search, strip=True)
            query = query.filter(Product.name.contains(clean_search))
        
        if category:
            query = query.join(Product.categories).filter(Category.name == category)
        
        products = query.order_by(Product.created_at.desc()).paginate(
            page=page, per_page=20, error_out=False
        )
        
        categories = Category.query.all()
        
        return render_template('admin/manage_products.html', 
                             products=products, categories=categories,
                             search=search, current_category=category)
    except Exception as e:
        current_app.logger.error(f"Manage products error: {e}")
        flash('Error loading products.', 'error')
        return redirect(url_for('admin.dashboard'))

@admin.route('/product/add', methods=['GET', 'POST'])
@login_required
@admin_required
@limiter.limit("10 per hour")
def add_product():
    """Add new product with enhanced validation"""
    form = AdminProductForm()
    categories = Category.query.filter_by(is_active=True).all()
    
    if form.validate_on_submit():
        try:
            product = Product(
                name=sanitize_input(form.name.data),
                description=bleach.clean(form.description.data) if form.description.data else None,
                price=form.price.data,
                original_price=form.original_price.data,
                sku=sanitize_input(form.sku.data) if form.sku.data else None,
                stock_quantity=max(0, form.stock_quantity.data),
                sizes=sanitize_input(form.sizes.data) if form.sizes.data else None,
                colors=sanitize_input(form.colors.data) if form.colors.data else None,
                material=sanitize_input(form.material.data) if form.material.data else None,
                care_instructions=bleach.clean(form.care_instructions.data) if form.care_instructions.data else None,
                is_featured=form.is_featured.data,
                is_new_arrival=form.is_new_arrival.data,
                is_best_seller=form.is_best_seller.data,
                is_on_sale=form.is_on_sale.data,
                is_active=form.is_active.data
            )
            
            # Handle secure image upload
            if form.image_file.data:
                if validate_file_upload(form.image_file.data):
                    picture_file = save_picture(form.image_file.data, 'images/products')
                    product.image_url = picture_file
                else:
                    flash('Invalid file type. Only JPG, PNG, and JPEG files are allowed.', 'error')
                    return render_template('admin/add_edit_product.html', form=form, 
                                         categories=categories, title='Add Product')
            
            db.session.add(product)
            db.session.commit()
            
            log_user_action(current_user.id, 'create_product', 'product', product.id)
            flash('Product added successfully!', 'success')
            return redirect(url_for('admin.manage_products'))
            
        except Exception as e:
            current_app.logger.error(f"Add product error: {e}")
            flash('Error adding product. Please try again.', 'error')
    
    return render_template('admin/add_edit_product.html', form=form, 
                         categories=categories, title='Add Product')

@admin.route('/product/edit/<int:id>', methods=['GET', 'POST'])
@login_required
@admin_required
@limiter.limit("20 per hour")
def edit_product(id):
    """Edit existing product with security validation"""
    product = Product.query.get_or_404(id)
    form = AdminProductForm(obj=product)
    categories = Category.query.filter_by(is_active=True).all()
    
    if form.validate_on_submit():
        try:
            # Store old values for audit
            old_values = {
                'name': product.name,
                'price': product.price,
                'stock_quantity': product.stock_quantity
            }
            
            product.name = sanitize_input(form.name.data)
            product.description = bleach.clean(form.description.data) if form.description.data else None
            product.price = form.price.data
            product.original_price = form.original_price.data
            product.sku = sanitize_input(form.sku.data) if form.sku.data else None
            product.stock_quantity = max(0, form.stock_quantity.data)
            product.sizes = sanitize_input(form.sizes.data) if form.sizes.data else None
            product.colors = sanitize_input(form.colors.data) if form.colors.data else None
            product.material = sanitize_input(form.material.data) if form.material.data else None
            product.care_instructions = bleach.clean(form.care_instructions.data) if form.care_instructions.data else None
            product.is_featured = form.is_featured.data
            product.is_new_arrival = form.is_new_arrival.data
            product.is_best_seller = form.is_best_seller.data
            product.is_on_sale = form.is_on_sale.data
            product.is_active = form.is_active.data
            
            # Handle secure image upload
            if form.image_file.data:
                if validate_file_upload(form.image_file.data):
                    # Delete old image
                    if product.image_url:
                        delete_picture(product.image_url, 'images/products')
                    
                    picture_file = save_picture(form.image_file.data, 'images/products')
                    product.image_url = picture_file
                else:
                    flash('Invalid file type. Only JPG, PNG, and JPEG files are allowed.', 'error')
                    return render_template('admin/add_edit_product.html', form=form, 
                                         categories=categories, product=product, title='Edit Product')
            
            db.session.commit()
            
            # Log the change with details
            changes = []
            for key, old_val in old_values.items():
                new_val = getattr(product, key)
                if old_val != new_val:
                    changes.append(f"{key}: {old_val} -> {new_val}")
            
            log_user_action(current_user.id, 'update_product', 'product', product.id, 
                          details='; '.join(changes))
            
            flash('Product updated successfully!', 'success')
            return redirect(url_for('admin.manage_products'))
            
        except Exception as e:
            current_app.logger.error(f"Edit product error: {e}")
            flash('Error updating product. Please try again.', 'error')
    
    return render_template('admin/add_edit_product.html', form=form, 
                         categories=categories, product=product, title='Edit Product')

@admin.route('/product/delete/<int:id>')
@login_required
@admin_required
@limiter.limit("5 per hour")
def delete_product(id):
    """Delete product with security logging"""
    try:
        product = Product.query.get_or_404(id)
        product_name = product.name
        
        # Delete product image
        if product.image_url:
            delete_picture(product.image_url, 'images/products')
        
        db.session.delete(product)
        db.session.commit()
        
        log_user_action(current_user.id, 'delete_product', 'product', id, 
                      details=f"Deleted product: {product_name}")
        
        flash('Product deleted successfully!', 'info')
    except Exception as e:
        current_app.logger.error(f"Delete product error: {e}")
        flash('Error deleting product. Please try again.', 'error')
    
    return redirect(url_for('admin.manage_products'))

# Enhanced Order Management
@admin.route('/orders')
@login_required
@admin_required
def manage_orders():
    """Manage orders page with filtering and search"""
    page = request.args.get('page', 1, type=int)
    status = sanitize_input(request.args.get('status', ''))
    
    try:
        query = Order.query
        
        if status:
            query = query.filter_by(status=status)
        
        orders = query.order_by(Order.created_at.desc()).paginate(
            page=page, per_page=20, error_out=False
        )
        
        return render_template('admin/manage_orders.html', orders=orders, current_status=status)
    except Exception as e:
        current_app.logger.error(f"Manage orders error: {e}")
        flash('Error loading orders.', 'error')
        return redirect(url_for('admin.dashboard'))

@admin.route('/order/<int:id>')
@login_required
@admin_required
def view_order(id):
    """View order details with security check"""
    try:
        order = Order.query.get_or_404(id)
        return render_template('admin/view_order.html', order=order)
    except Exception as e:
        current_app.logger.error(f"View order error: {e}")
        flash('Error loading order details.', 'error')
        return redirect(url_for('admin.manage_orders'))

@admin.route('/order/edit/<int:id>', methods=['GET', 'POST'])
@login_required
@admin_required
@limiter.limit("20 per hour")
def edit_order(id):
    """Edit order status with validation and logging"""
    order = Order.query.get_or_404(id)
    
    # Handle quick status change via query parameter
    new_status = sanitize_input(request.args.get('status', ''))
    valid_statuses = ['pending', 'confirmed', 'shipped', 'delivered', 'cancelled']
    
    if new_status and new_status in valid_statuses:
        try:
            old_status = order.status
            order.status = new_status
            db.session.commit()
            
            log_user_action(current_user.id, 'update_order_status', 'order', id,
                          details=f"Status changed from {old_status} to {new_status}")
            
            flash(f'Order status updated to {new_status.title()}!', 'success')
            return redirect(url_for('admin.view_order', id=id))
        except Exception as e:
            current_app.logger.error(f"Quick status change error: {e}")
            flash('Error updating order status.', 'error')
    
    form = AdminOrderForm(obj=order)
    
    if form.validate_on_submit():
        try:
            old_status = order.status
            order.status = form.status.data
            order.tracking_number = sanitize_input(form.tracking_number.data) if form.tracking_number.data else None
            order.notes = bleach.clean(form.notes.data) if form.notes.data else None
            
            db.session.commit()
            
            log_user_action(current_user.id, 'update_order', 'order', id,
                          details=f"Status: {old_status} -> {order.status}")
            
            flash('Order updated successfully!', 'success')
            return redirect(url_for('admin.view_order', id=id))
        except Exception as e:
            current_app.logger.error(f"Edit order error: {e}")
            flash('Error updating order. Please try again.', 'error')
    
    return render_template('admin/edit_order.html', form=form, order=order)

# User Management with Security
@admin.route('/users')
@login_required
@admin_required
def manage_users():
    """Manage users page with search and filtering"""
    page = request.args.get('page', 1, type=int)
    search = sanitize_input(request.args.get('search', ''))
    
    try:
        query = User.query
        
        if search:
            clean_search = bleach.clean(search, strip=True)
            query = query.filter(
                (User.username.contains(clean_search)) | 
                (User.email.contains(clean_search)) |
                (User.first_name.contains(clean_search)) |
                (User.last_name.contains(clean_search))
            )
        
        users = query.order_by(User.created_at.desc()).paginate(
            page=page, per_page=20, error_out=False
        )
        
        return render_template('admin/manage_users.html', users=users, search=search)
    except Exception as e:
        current_app.logger.error(f"Manage users error: {e}")
        flash('Error loading users.', 'error')
        return redirect(url_for('admin.dashboard'))

@admin.route('/user/<int:id>')
@login_required
@admin_required
def view_user(id):
    """View user details with order history"""
    try:
        user = User.query.get_or_404(id)
        user_orders = Order.query.filter_by(user_id=id).order_by(Order.created_at.desc()).limit(10).all()
        
        # Get user activity from audit log
        recent_activity = AuditLog.query.filter_by(user_id=id).order_by(
            AuditLog.created_at.desc()
        ).limit(10).all()
        
        return render_template('admin/view_user.html', user=user, orders=user_orders, 
                             recent_activity=recent_activity)
    except Exception as e:
        current_app.logger.error(f"View user error: {e}")
        flash('Error loading user details.', 'error')
        return redirect(url_for('admin.manage_users'))

# Enhanced API Routes with Security
@admin.route('/api/stats')
@login_required
@admin_required
@cache.cached(timeout=300)  # Cache for 5 minutes
def api_stats():
    """Get dashboard statistics with caching"""
    try:
        stats = {
            'total_products': Product.query.count(),
            'active_products': Product.query.filter_by(is_active=True).count(),
            'total_users': User.query.filter_by(is_admin=False).count(),
            'total_orders': Order.query.count(),
            'pending_orders': Order.query.filter_by(status='pending').count(),
            'pending_reviews': Review.query.filter_by(is_approved=False).count(),
            'unread_messages': ContactMessage.query.filter_by(is_read=False).count(),
            'low_stock_items': Product.query.filter(Product.stock_quantity <= 5, Product.is_active == True).count()
        }
        return jsonify(stats)
    except Exception as e:
        current_app.logger.error(f"API stats error: {e}")
        return jsonify({'error': 'Unable to load statistics'}), 500

@admin.route('/api/sales_overview')
@login_required
@admin_required
@cache.cached(timeout=600)  # Cache for 10 minutes
def api_sales_overview():
    """Get sales data for charts with enhanced error handling"""
    try:
        today = datetime.utcnow().date()
        start_date = today - timedelta(days=29)  # last 30 days including today

        sales_data = (
            db.session.query(
                func.date(Order.created_at).label('date'),
                func.sum(Order.total_amount).label('total')
            )
            .filter(Order.created_at >= start_date)
            .filter(Order.payment_status == 'paid')  # Only paid orders
            .group_by(func.date(Order.created_at))
            .all()
        )
        
        # Format data for chart.js
        dates = [(start_date + timedelta(days=i)) for i in range(30)]
        totals_dict = {record.date.strftime('%Y-%m-%d'): float(record.total or 0) for record in sales_data}
        totals = [totals_dict.get(d.strftime('%Y-%m-%d'), 0) for d in dates]
        labels = [d.strftime('%b %d') for d in dates]

        return jsonify({'labels': labels, 'totals': totals})
    except Exception as e:
        current_app.logger.error(f"API sales overview error: {e}")
        return jsonify({'error': 'Unable to load sales data'}), 500

# Security and Audit Routes
@admin.route('/security')
@login_required
@admin_required
def security_dashboard():
    """Security monitoring dashboard"""
    try:
        # Recent security events
        recent_failed_logins = AuditLog.query.filter_by(action='failed_login').filter(
            AuditLog.created_at >= datetime.utcnow() - timedelta(days=7)
        ).order_by(AuditLog.created_at.desc()).limit(50).all()
        
        # Locked accounts
        locked_users = User.query.filter(User.locked_until > datetime.utcnow()).all()
        
        # Recent admin actions
        admin_actions = AuditLog.query.filter(
            AuditLog.action.in_(['create_product', 'update_product', 'delete_product', 
                               'update_order', 'update_user'])
        ).filter(
            AuditLog.created_at >= datetime.utcnow() - timedelta(days=7)
        ).order_by(AuditLog.created_at.desc()).limit(50).all()
        
        return render_template('admin/security_dashboard.html', 
                             failed_logins=recent_failed_logins,
                             locked_users=locked_users,
                             admin_actions=admin_actions)
    except Exception as e:
        current_app.logger.error(f"Security dashboard error: {e}")
        flash('Error loading security dashboard.', 'error')
        return redirect(url_for('admin.dashboard'))

@admin.route('/unlock_user/<int:user_id>')
@login_required
@admin_required
@limiter.limit("10 per hour")
def unlock_user(user_id):
    """Unlock a locked user account"""
    try:
        user = User.query.get_or_404(user_id)
        user.failed_login_attempts = 0
        user.locked_until = None
        db.session.commit()
        
        log_user_action(current_user.id, 'unlock_user', 'user', user_id,
                      details=f"Unlocked user account: {user.email}")
        
        flash(f'User account {user.email} has been unlocked.', 'success')
    except Exception as e:
        current_app.logger.error(f"Unlock user error: {e}")
        flash('Error unlocking user account.', 'error')
    
    return redirect(url_for('admin.security_dashboard'))
