from flask import Blueprint, render_template, request, flash, redirect, url_for, jsonify, session
from flask_login import current_user, login_required
from app.models import Product, Category, CartItem, WishlistItem, Order, OrderItem, Review, Newsletter, ContactMessage
from app.forms import AddToCartForm, ReviewForm, NewsletterForm, ContactForm, SearchForm, CheckoutForm
from app.utils import generate_order_number, create_sample_data
from app import db
import json
from sqlalchemy import or_, and_

main = Blueprint('main', __name__)

@main.route('/')
@main.route('/index')
def index():
    """Homepage with featured products and categories"""
    # Get featured products
    featured_products = Product.query.filter_by(is_featured=True, is_active=True).limit(8).all()
    
    # Get new arrivals
    new_arrivals = Product.query.filter_by(is_new_arrival=True, is_active=True).limit(6).all()
    
    # Get best sellers
    best_sellers = Product.query.filter_by(is_best_seller=True, is_active=True).limit(6).all()
    
    # Get sale products
    sale_products = Product.query.filter_by(is_on_sale=True, is_active=True).limit(6).all()
    
    # Get categories
    categories = Category.query.filter_by(is_active=True).all()
    
    # Newsletter form
    newsletter_form = NewsletterForm()
    
    return render_template('index.html', 
                         featured_products=featured_products,
                         new_arrivals=new_arrivals,
                         best_sellers=best_sellers,
                         sale_products=sale_products,
                         categories=categories,
                         newsletter_form=newsletter_form)

@main.route('/products')
def products():
    """Product listing page with search and filter"""
    page = request.args.get('page', 1, type=int)
    category = request.args.get('category', '')
    search = request.args.get('search', '')
    sort_by = request.args.get('sort_by', 'newest')
    min_price = request.args.get('min_price', type=float)
    max_price = request.args.get('max_price', type=float)
    
    query = Product.query.filter_by(is_active=True)
    
    # Apply filters
    if category:
        query = query.join(Product.categories).filter(Category.name == category)
    
    if search:
        query = query.filter(or_(
            Product.name.contains(search),
            Product.description.contains(search)
        ))
    
    if min_price:
        query = query.filter(Product.price >= min_price)
    
    if max_price:
        query = query.filter(Product.price <= max_price)
    
    # Apply sorting
    if sort_by == 'name_asc':
        query = query.order_by(Product.name.asc())
    elif sort_by == 'name_desc':
        query = query.order_by(Product.name.desc())
    elif sort_by == 'price_asc':
        query = query.order_by(Product.price.asc())
    elif sort_by == 'price_desc':
        query = query.order_by(Product.price.desc())
    elif sort_by == 'newest':
        query = query.order_by(Product.created_at.desc())
    
    products = query.paginate(
        page=page, per_page=12, error_out=False
    )
    
    categories = Category.query.filter_by(is_active=True).all()
    
    return render_template('products.html', products=products, categories=categories,
                         current_category=category, current_search=search,
                         current_sort=sort_by, min_price=min_price, max_price=max_price)

@main.route('/product/<int:id>')
def product_detail(id):
    """Individual product page"""
    product = Product.query.get_or_404(id)
    
    # Get related products
    related_products = Product.query.filter(
        and_(Product.id != id, Product.is_active == True)
    ).join(Product.categories).filter(
        Category.id.in_([cat.id for cat in product.categories])
    ).limit(4).all()
    
    # Get reviews
    reviews = Review.query.filter_by(product_id=id, is_approved=True).all()
    
    # Forms
    add_to_cart_form = AddToCartForm()
    review_form = ReviewForm()
    
    # Populate size and color choices
    if product.sizes:
        add_to_cart_form.size.choices = [(size.strip(), size.strip()) for size in product.sizes.split(',')]
        add_to_cart_form.size.choices.insert(0, ('', 'Select Size'))
    
    if product.colors:
        add_to_cart_form.color.choices = [(color.strip(), color.strip()) for color in product.colors.split(',')]
        add_to_cart_form.color.choices.insert(0, ('', 'Select Color'))
    
    return render_template('product_detail.html', product=product, 
                         related_products=related_products, reviews=reviews,
                         add_to_cart_form=add_to_cart_form, review_form=review_form)

@main.route('/add_to_cart', methods=['POST'])
@login_required
def add_to_cart():
    """Add product to cart"""
    product_id = request.form.get('product_id', type=int)
    quantity = request.form.get('quantity', 1, type=int)
    size = request.form.get('size', '')
    color = request.form.get('color', '')
    
    product = Product.query.get_or_404(product_id)
    
    if not product.is_in_stock():
        flash('Sorry, this product is out of stock.', 'error')
        return redirect(url_for('main.product_detail', id=product_id))
    
    # Check if item already exists in cart
    cart_item = CartItem.query.filter_by(
        user_id=current_user.id, 
        product_id=product_id,
        size=size,
        color=color
    ).first()
    
    if cart_item:
        cart_item.quantity += quantity
    else:
        cart_item = CartItem(
            user_id=current_user.id,
            product_id=product_id,
            quantity=quantity,
            size=size,
            color=color
        )
        db.session.add(cart_item)
    
    db.session.commit()
    flash(f'{product.name} added to cart!', 'success')
    return redirect(url_for('main.product_detail', id=product_id))

@main.route('/cart')
@login_required
def cart():
    """Shopping cart page"""
    cart_items = CartItem.query.filter_by(user_id=current_user.id).all()
    total = sum(item.get_total() for item in cart_items)
    
    return render_template('cart.html', cart_items=cart_items, total=total)

@main.route('/update_cart', methods=['POST'])
@login_required
def update_cart():
    """Update cart item quantity"""
    item_id = request.form.get('item_id', type=int)
    quantity = request.form.get('quantity', type=int)
    
    cart_item = CartItem.query.filter_by(id=item_id, user_id=current_user.id).first_or_404()
    
    if quantity > 0:
        cart_item.quantity = quantity
        db.session.commit()
        flash('Cart updated successfully!', 'success')
    else:
        db.session.delete(cart_item)
        db.session.commit()
        flash('Item removed from cart!', 'info')
    
    return redirect(url_for('main.cart'))

@main.route('/remove_from_cart/<int:item_id>')
@login_required
def remove_from_cart(item_id):
    """Remove item from cart"""
    cart_item = CartItem.query.filter_by(id=item_id, user_id=current_user.id).first_or_404()
    db.session.delete(cart_item)
    db.session.commit()
    flash('Item removed from cart!', 'info')
    return redirect(url_for('main.cart'))

from flask import request

@main.route('/checkout', methods=['GET', 'POST'])
@login_required
def checkout():
    """Checkout page"""
    cart_items = CartItem.query.filter_by(user_id=current_user.id).all()

    if not cart_items:
        flash('Your cart is empty!', 'warning')
        return redirect(url_for('main.cart'))

    total = sum(item.get_total() for item in cart_items)
    form = CheckoutForm()

    # Pre-populate form with user data for GET requests
    if request.method == 'GET' and current_user:
        form.first_name.data = current_user.first_name
        form.last_name.data = current_user.last_name
        form.email.data = current_user.email
        form.phone.data = current_user.phone
        form.address.data = current_user.address
        form.city.data = current_user.city
        form.state.data = current_user.state
        form.pincode.data = current_user.pincode
        form.country.data = current_user.country or 'India'

    if form.validate_on_submit():
        # Server-side validation for online payment details (e.g., Stripe)
        if form.payment_method.data == 'stripe':
            if not form.card_number.data or not form.card_expiry.data or not form.card_cvv.data:
                flash('Please enter all credit card details.', 'error')
                return render_template('checkout.html', cart_items=cart_items, total=total, form=form)

        # Place order logic begins here (example)
        # Create order record, order items, clear cart, etc.
        # This is placeholder for your existing processing code.
        # Return redirect to order confirmation after successful placement.

        flash('Order placed successfully!', 'success')
        return redirect(url_for('main.order_confirmation'))

    return render_template('checkout.html', cart_items=cart_items, total=total, form=form)

@main.route('/place_order', methods=['POST'])
@login_required
def place_order():
    """Process order placement"""
    form = CheckoutForm()
    
    if form.validate_on_submit():
        cart_items = CartItem.query.filter_by(user_id=current_user.id).all()
        
        if not cart_items:
            flash('Your cart is empty!', 'warning')
            return redirect(url_for('main.cart'))
        
        total = sum(item.get_total() for item in cart_items)
        
        # Create order
        order = Order(
            user_id=current_user.id,
            total_amount=total,
            payment_method=form.payment_method.data,
            shipping_address=form.address.data,
            shipping_city=form.city.data,
            shipping_state=form.state.data,
            shipping_pincode=form.pincode.data,
            shipping_country=form.country.data,
            shipping_phone=form.phone.data,
            notes=form.notes.data
        )
        order.generate_order_number()
        db.session.add(order)
        db.session.flush()  # To get the order ID
        
        # Create order items
        for cart_item in cart_items:
            order_item = OrderItem(
                order_id=order.id,
                product_id=cart_item.product_id,
                quantity=cart_item.quantity,
                price=cart_item.product.price,
                size=cart_item.size,
                color=cart_item.color
            )
            db.session.add(order_item)
        
        # Clear cart
        for cart_item in cart_items:
            db.session.delete(cart_item)
        
        db.session.commit()
        
        flash(f'Order placed successfully! Order number: {order.order_number}', 'success')
        return redirect(url_for('main.order_confirmation', order_id=order.id))
    
    # If form validation fails
    cart_items = CartItem.query.filter_by(user_id=current_user.id).all()
    total = sum(item.get_total() for item in cart_items)
    return render_template('checkout.html', cart_items=cart_items, total=total, form=form)

@main.route('/order_confirmation/<int:order_id>')
@login_required
def order_confirmation(order_id):
    """Order confirmation page"""
    order = Order.query.filter_by(id=order_id, user_id=current_user.id).first_or_404()
    return render_template('order_confirmation.html', order=order)

@main.route('/wishlist')
@login_required
def wishlist():
    """User wishlist page"""
    wishlist_items = WishlistItem.query.filter_by(user_id=current_user.id).all()
    return render_template('wishlist.html', wishlist_items=wishlist_items)

@main.route('/add_to_wishlist/<int:product_id>')
@login_required
def add_to_wishlist(product_id):
    """Add product to wishlist"""
    product = Product.query.get_or_404(product_id)
    
    existing_item = WishlistItem.query.filter_by(
        user_id=current_user.id, 
        product_id=product_id
    ).first()
    
    if not existing_item:
        wishlist_item = WishlistItem(user_id=current_user.id, product_id=product_id)
        db.session.add(wishlist_item)
        db.session.commit()
        flash(f'{product.name} added to wishlist!', 'success')
    else:
        flash(f'{product.name} is already in your wishlist!', 'info')
    
    return redirect(url_for('main.product_detail', id=product_id))

@main.route('/remove_from_wishlist/<int:product_id>')
@login_required
def remove_from_wishlist(product_id):
    """Remove product from wishlist"""
    wishlist_item = WishlistItem.query.filter_by(
        user_id=current_user.id, 
        product_id=product_id
    ).first_or_404()
    
    db.session.delete(wishlist_item)
    db.session.commit()
    flash('Item removed from wishlist!', 'info')
    return redirect(url_for('main.wishlist'))

@main.route('/add_review/<int:product_id>', methods=['POST'])
@login_required
def add_review(product_id):
    """Add product review"""
    form = ReviewForm()
    product = Product.query.get_or_404(product_id)
    
    if form.validate_on_submit():
        # Check if user already reviewed this product
        existing_review = Review.query.filter_by(
            user_id=current_user.id, 
            product_id=product_id
        ).first()
        
        if existing_review:
            flash('You have already reviewed this product!', 'warning')
        else:
            review = Review(
                user_id=current_user.id,
                product_id=product_id,
                rating=form.rating.data,
                comment=form.comment.data
            )
            db.session.add(review)
            db.session.commit()
            flash('Review added successfully! It will be published after approval.', 'success')
    
    return redirect(url_for('main.product_detail', id=product_id))

@main.route('/newsletter_signup', methods=['POST'])
def newsletter_signup():
    """Newsletter subscription"""
    form = NewsletterForm()
    
    if form.validate_on_submit():
        existing_subscriber = Newsletter.query.filter_by(email=form.email.data).first()
        
        if not existing_subscriber:
            newsletter = Newsletter(email=form.email.data)
            db.session.add(newsletter)
            db.session.commit()
            flash('Thank you for subscribing to our newsletter!', 'success')
        else:
            flash('Email already subscribed!', 'info')
    
    return redirect(url_for('main.index'))

@main.route('/contact', methods=['GET', 'POST'])
def contact():
    """Contact page"""
    form = ContactForm()
    
    if form.validate_on_submit():
        contact_msg = ContactMessage(
            name=form.name.data,
            email=form.email.data,
            phone=form.phone.data,
            subject=form.subject.data,
            message=form.message.data
        )
        db.session.add(contact_msg)
        db.session.commit()
        flash('Thank you for your message! We will get back to you soon.', 'success')
        return redirect(url_for('main.contact'))
    
    return render_template('contact.html', form=form)

@main.route('/about')
def about():
    """About page"""
    return render_template('about.html')

@main.route('/privacy')
def privacy():
    """Privacy policy page"""
    return render_template('privacy.html')

@main.route('/terms')
def terms():
    """Terms and conditions page"""
    return render_template('terms.html')

@main.route('/init_sample_data')
def init_sample_data():
    """Initialize sample data (for development)"""
    create_sample_data()
    flash('Sample data created successfully!', 'success')
    return redirect(url_for('main.index'))

# AJAX routes
@main.route('/api/cart_count')
def api_cart_count():
    """Get current user's cart count"""
    if current_user.is_authenticated:
        count = current_user.get_cart_count()
        return jsonify({'count': count})
    return jsonify({'count': 0})

@main.route('/api/search_suggestions')
def api_search_suggestions():
    """Get search suggestions"""
    query = request.args.get('q', '')
    if len(query) >= 2:
        products = Product.query.filter(
            Product.name.contains(query)
        ).filter_by(is_active=True).limit(5).all()
        
        suggestions = [{'id': p.id, 'name': p.name, 'price': p.price} for p in products]
        return jsonify(suggestions)
    return jsonify([])