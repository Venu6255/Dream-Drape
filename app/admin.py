from flask import Blueprint, render_template, request, flash, redirect, url_for, jsonify
from flask_login import login_required, current_user
from functools import wraps
from app.models import Product, Category, User, Order, Review, Newsletter, ContactMessage
from app.forms import AdminProductForm, AdminCategoryForm, AdminOrderForm, AdminUserForm
from app.utils import save_picture, delete_picture
from app import db
import os

admin = Blueprint('admin', __name__)

def admin_required(f):
    """Decorator to require admin privileges"""
    @wraps(f)
    def decorated_function(*args, **kwargs):
        if not current_user.is_authenticated or not current_user.is_admin:
            flash('Access denied. Admin privileges required.', 'error')
            return redirect(url_for('main.index'))
        return f(*args, **kwargs)
    return decorated_function

@admin.route('/')
@login_required
@admin_required
def dashboard():
    """Admin dashboard with statistics"""
    # Get statistics
    total_products = Product.query.count()
    total_users = User.query.filter_by(is_admin=False).count()
    total_orders = Order.query.count()
    pending_orders = Order.query.filter_by(status='pending').count()
    
    # Recent orders
    recent_orders = Order.query.order_by(Order.created_at.desc()).limit(5).all()
    
    # Low stock products
    low_stock_products = Product.query.filter(Product.stock_quantity <= 5).all()
    
    # Pending reviews
    pending_reviews = Review.query.filter_by(is_approved=False).count()
    
    # Contact messages
    unread_messages = ContactMessage.query.filter_by(is_read=False).count()
    
    return render_template('admin/admin_dashboard.html',
                         total_products=total_products,
                         total_users=total_users,
                         total_orders=total_orders,
                         pending_orders=pending_orders,
                         recent_orders=recent_orders,
                         low_stock_products=low_stock_products,
                         pending_reviews=pending_reviews,
                         unread_messages=unread_messages)

# Product Management
@admin.route('/products')
@login_required
@admin_required
def manage_products():
    """Manage products page"""
    page = request.args.get('page', 1, type=int)
    search = request.args.get('search', '')
    category = request.args.get('category', '')
    
    query = Product.query
    
    if search:
        query = query.filter(Product.name.contains(search))
    
    if category:
        query = query.join(Product.categories).filter(Category.name == category)
    
    products = query.order_by(Product.created_at.desc()).paginate(
        page=page, per_page=20, error_out=False
    )
    
    categories = Category.query.all()
    
    return render_template('admin/manage_products.html', 
                         products=products, categories=categories,
                         search=search, current_category=category)

@admin.route('/product/add', methods=['GET', 'POST'])
@login_required
@admin_required
def add_product():
    """Add new product"""
    form = AdminProductForm()
    categories = Category.query.filter_by(is_active=True).all()
    
    if form.validate_on_submit():
        product = Product(
            name=form.name.data,
            description=form.description.data,
            price=form.price.data,
            original_price=form.original_price.data,
            sku=form.sku.data,
            stock_quantity=form.stock_quantity.data,
            sizes=form.sizes.data,
            colors=form.colors.data,
            material=form.material.data,
            care_instructions=form.care_instructions.data,
            is_featured=form.is_featured.data,
            is_new_arrival=form.is_new_arrival.data,
            is_best_seller=form.is_best_seller.data,
            is_on_sale=form.is_on_sale.data,
            is_active=form.is_active.data
        )
        
        # Handle image upload
        if form.image_file.data:
            picture_file = save_picture(form.image_file.data, 'images/products')
            product.image_url = picture_file
        
        db.session.add(product)
        db.session.commit()
        
        flash('Product added successfully!', 'success')
        return redirect(url_for('admin.manage_products'))
    
    return render_template('admin/add_edit_product.html', form=form, 
                         categories=categories, title='Add Product')

@admin.route('/product/edit/<int:id>', methods=['GET', 'POST'])
@login_required
@admin_required
def edit_product(id):
    """Edit existing product"""
    product = Product.query.get_or_404(id)
    form = AdminProductForm(obj=product)
    categories = Category.query.filter_by(is_active=True).all()
    
    if form.validate_on_submit():
        product.name = form.name.data
        product.description = form.description.data
        product.price = form.price.data
        product.original_price = form.original_price.data
        product.sku = form.sku.data
        product.stock_quantity = form.stock_quantity.data
        product.sizes = form.sizes.data
        product.colors = form.colors.data
        product.material = form.material.data
        product.care_instructions = form.care_instructions.data
        product.is_featured = form.is_featured.data
        product.is_new_arrival = form.is_new_arrival.data
        product.is_best_seller = form.is_best_seller.data
        product.is_on_sale = form.is_on_sale.data
        product.is_active = form.is_active.data
        
        # Handle image upload
        if form.image_file.data:
            # Delete old image
            if product.image_url:
                delete_picture(product.image_url, 'images/products')
            
            picture_file = save_picture(form.image_file.data, 'images/products')
            product.image_url = picture_file
        
        db.session.commit()
        flash('Product updated successfully!', 'success')
        return redirect(url_for('admin.manage_products'))
    
    return render_template('admin/add_edit_product.html', form=form, 
                         categories=categories, product=product, title='Edit Product')

@admin.route('/product/delete/<int:id>')
@login_required
@admin_required
def delete_product(id):
    """Delete product"""
    product = Product.query.get_or_404(id)
    
    # Delete product image
    if product.image_url:
        delete_picture(product.image_url, 'images/products')
    
    db.session.delete(product)
    db.session.commit()
    
    flash('Product deleted successfully!', 'info')
    return redirect(url_for('admin.manage_products'))

# Category Management
@admin.route('/categories')
@login_required
@admin_required
def manage_categories():
    """Manage categories page"""
    categories = Category.query.order_by(Category.name).all()
    return render_template('admin/manage_categories.html', categories=categories)

@admin.route('/category/add', methods=['GET', 'POST'])
@login_required
@admin_required
def add_category():
    """Add new category"""
    form = AdminCategoryForm()
    
    if form.validate_on_submit():
        category = Category(
            name=form.name.data,
            description=form.description.data,
            is_active=form.is_active.data
        )
        
        # Handle image upload
        if form.image_file.data:
            picture_file = save_picture(form.image_file.data, 'images/categories')
            category.image_url = picture_file
        
        db.session.add(category)
        db.session.commit()
        
        flash('Category added successfully!', 'success')
        return redirect(url_for('admin.manage_categories'))
    
    return render_template('admin/add_edit_category.html', form=form, title='Add Category')

@admin.route('/category/edit/<int:id>', methods=['GET', 'POST'])
@login_required
@admin_required
def edit_category(id):
    """Edit existing category"""
    category = Category.query.get_or_404(id)
    form = AdminCategoryForm(obj=category)
    
    if form.validate_on_submit():
        category.name = form.name.data
        category.description = form.description.data
        category.is_active = form.is_active.data
        
        # Handle image upload
        if form.image_file.data:
            # Delete old image
            if category.image_url:
                delete_picture(category.image_url, 'images/categories')
            
            picture_file = save_picture(form.image_file.data, 'images/categories')
            category.image_url = picture_file
        
        db.session.commit()
        flash('Category updated successfully!', 'success')
        return redirect(url_for('admin.manage_categories'))
    
    return render_template('admin/add_edit_category.html', form=form, 
                         category=category, title='Edit Category')

@admin.route('/category/delete/<int:id>')
@login_required
@admin_required
def delete_category(id):
    """Delete category"""
    category = Category.query.get_or_404(id)
    
    # Delete category image
    if category.image_url:
        delete_picture(category.image_url, 'images/categories')
    
    db.session.delete(category)
    db.session.commit()
    
    flash('Category deleted successfully!', 'info')
    return redirect(url_for('admin.manage_categories'))

# Order Management
@admin.route('/orders')
@login_required
@admin_required
def manage_orders():
    """Manage orders page"""
    page = request.args.get('page', 1, type=int)
    status = request.args.get('status', '')
    
    query = Order.query
    
    if status:
        query = query.filter_by(status=status)
    
    orders = query.order_by(Order.created_at.desc()).paginate(
        page=page, per_page=20, error_out=False
    )
    
    return render_template('admin/manage_orders.html', orders=orders, current_status=status)

@admin.route('/order/<int:id>')
@login_required
@admin_required
def view_order(id):
    """View order details"""
    order = Order.query.get_or_404(id)
    return render_template('admin/view_order.html', order=order)

@admin.route('/order/edit/<int:id>', methods=['GET', 'POST'])
@login_required
@admin_required
def edit_order(id):
    """Edit order status"""
    order = Order.query.get_or_404(id)
    
    # Handle status change via query parameter (e.g., cancel order)
    new_status = request.args.get('status')
    if new_status:
        order.status = new_status
        db.session.commit()
        flash(f'Order status updated to {new_status.title()}!', 'success')
        return redirect(url_for('admin.view_order', id=id))
    
    form = AdminOrderForm(obj=order)
    
    if form.validate_on_submit():
        order.status = form.status.data
        order.tracking_number = form.tracking_number.data
        order.notes = form.notes.data
        
        db.session.commit()
        flash('Order updated successfully!', 'success')
        return redirect(url_for('admin.view_order', id=id))
    
    return render_template('admin/edit_order.html', form=form, order=order)

# User Management
@admin.route('/users')
@login_required
@admin_required
def manage_users():
    """Manage users page"""
    page = request.args.get('page', 1, type=int)
    search = request.args.get('search', '')
    
    query = User.query
    
    if search:
        query = query.filter(
            (User.username.contains(search)) | 
            (User.email.contains(search)) |
            (User.first_name.contains(search)) |
            (User.last_name.contains(search))
        )
    
    users = query.order_by(User.created_at.desc()).paginate(
        page=page, per_page=20, error_out=False
    )
    
    return render_template('admin/manage_users.html', users=users, search=search)

@admin.route('/user/<int:id>')
@login_required
@admin_required
def view_user(id):
    """View user details"""
    user = User.query.get_or_404(id)
    user_orders = Order.query.filter_by(user_id=id).order_by(Order.created_at.desc()).limit(10).all()
    return render_template('admin/view_user.html', user=user, orders=user_orders)

@admin.route('/user/edit/<int:id>', methods=['GET', 'POST'])
@login_required
@admin_required
def edit_user(id):
    """Edit user details"""
    user = User.query.get_or_404(id)
    form = AdminUserForm(obj=user)
    
    if form.validate_on_submit():
        user.username = form.username.data
        user.email = form.email.data
        user.first_name = form.first_name.data
        user.last_name = form.last_name.data
        user.is_admin = form.is_admin.data
        user.is_active = form.is_active.data
        
        db.session.commit()
        flash('User updated successfully!', 'success')
        return redirect(url_for('admin.view_user', id=id))
    
    return render_template('admin/edit_user.html', form=form, user=user)

# Review Management
@admin.route('/reviews')
@login_required
@admin_required
def manage_reviews():
    """Manage reviews page"""
    page = request.args.get('page', 1, type=int)
    status = request.args.get('status', 'pending')
    
    query = Review.query
    
    if status == 'pending':
        query = query.filter_by(is_approved=False)
    elif status == 'approved':
        query = query.filter_by(is_approved=True)
    
    reviews = query.order_by(Review.created_at.desc()).paginate(
        page=page, per_page=20, error_out=False
    )
    
    return render_template('admin/manage_reviews.html', reviews=reviews, current_status=status)

@admin.route('/review/approve/<int:id>')
@login_required
@admin_required
def approve_review(id):
    """Approve review"""
    review = Review.query.get_or_404(id)
    review.is_approved = True
    db.session.commit()
    flash('Review approved successfully!', 'success')
    return redirect(url_for('admin.manage_reviews'))

@admin.route('/review/delete/<int:id>')
@login_required
@admin_required
def delete_review(id):
    """Delete review"""
    review = Review.query.get_or_404(id)
    db.session.delete(review)
    db.session.commit()
    flash('Review deleted successfully!', 'info')
    return redirect(url_for('admin.manage_reviews'))

# Messages and Newsletter
@admin.route('/messages')
@login_required
@admin_required
def manage_messages():
    """Manage contact messages"""
    page = request.args.get('page', 1, type=int)
    messages = ContactMessage.query.order_by(ContactMessage.created_at.desc()).paginate(
        page=page, per_page=20, error_out=False
    )
    return render_template('admin/manage_messages.html', messages=messages)

@admin.route('/message/<int:id>')
@login_required
@admin_required
def view_message(id):
    """View contact message"""
    message = ContactMessage.query.get_or_404(id)
    message.is_read = True
    db.session.commit()
    return render_template('admin/view_message.html', message=message)

@admin.route('/newsletter')
@login_required
@admin_required
def manage_newsletter():
    """Manage newsletter subscribers"""
    page = request.args.get('page', 1, type=int)
    subscribers = Newsletter.query.order_by(Newsletter.subscribed_at.desc()).paginate(
        page=page, per_page=20, error_out=False
    )
    return render_template('admin/manage_newsletter.html', subscribers=subscribers)

# API Routes for AJAX
@admin.route('/api/stats')
@login_required
@admin_required
def api_stats():
    """Get dashboard statistics"""
    stats = {
        'total_products': Product.query.count(),
        'total_users': User.query.filter_by(is_admin=False).count(),
        'total_orders': Order.query.count(),
        'pending_orders': Order.query.filter_by(status='pending').count(),
        'pending_reviews': Review.query.filter_by(is_approved=False).count(),
        'unread_messages': ContactMessage.query.filter_by(is_read=False).count()
    }
    return jsonify(stats)
@admin.route('/api/order_status')
@login_required
@admin_required
def api_order_status():
    data = {
        'pending': Order.query.filter_by(status='pending').count(),
        'confirmed': Order.query.filter_by(status='confirmed').count(),
        'shipped': Order.query.filter_by(status='shipped').count(),
        'delivered': Order.query.filter_by(status='delivered').count(),
        'cancelled': Order.query.filter_by(status='cancelled').count(),
    }
    return jsonify(data)

from sqlalchemy import func, extract
from datetime import datetime, timedelta

@admin.route('/api/sales_overview')
@login_required
@admin_required
def api_sales_overview():
    today = datetime.utcnow().date()
    start_date = today - timedelta(days=29)  # last 30 days including today

    sales_data = (
        db.session.query(
            func.date(Order.created_at).label('date'),
            func.sum(Order.total_amount).label('total')
        )
        .filter(Order.created_at >= start_date)
        .group_by(func.date(Order.created_at))
        .all()
    )
    # Format data for chart.js
    dates = [(start_date + timedelta(days=i)) for i in range(30)]
    totals_dict = {record.date.strftime('%Y-%m-%d'): float(record.total) for record in sales_data}
    totals = [totals_dict.get(d.strftime('%Y-%m-%d'), 0) for d in dates]
    labels = [d.strftime('%b %d') for d in dates]

    return jsonify({'labels': labels, 'totals': totals})

@admin.route('/api/product_categories')
@login_required
@admin_required
def api_product_categories():
    results = (
        db.session.query(Category.name, func.count(Product.id))
        .join(Product.categories)
        .group_by(Category.id)
        .all()
    )
    labels = [r[0] for r in results]
    counts = [r[1] for r in results]
    return jsonify({'labels': labels, 'counts': counts})

@admin.route('/api/weekly_revenue')
@login_required
@admin_required
def api_weekly_revenue():
    today = datetime.utcnow().date()
    start_date = today - timedelta(days=6)  # last 7 days including today

    revenue_data = (
        db.session.query(
            func.date(Order.created_at).label('date'),
            func.sum(Order.total_amount).label('total')
        )
        .filter(Order.created_at >= start_date)
        .group_by(func.date(Order.created_at))
        .all()
    )
    dates = [(start_date + timedelta(days=i)) for i in range(7)]
    totals_dict = {record.date.strftime('%Y-%m-%d'): float(record.total) for record in revenue_data}
    totals = [totals_dict.get(d.strftime('%Y-%m-%d'), 0) for d in dates]
    labels = [d.strftime('%a') for d in dates]  # Mon, Tue etc.

    return jsonify({'labels': labels, 'totals': totals})
