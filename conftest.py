"""
Test configuration for Dream-Drape application
"""
import pytest
import tempfile
import os
from app import create_app, db
from app.models import User, Product, Category
from config import TestingConfig

@pytest.fixture(scope='session')
def app():
    """Create application for testing."""
    db_fd, db_path = tempfile.mkstemp()
    
    app = create_app(TestingConfig)
    app.config['DATABASE_URL'] = f'sqlite:///{db_path}'
    app.config['TESTING'] = True
    app.config['WTF_CSRF_ENABLED'] = False
    
    with app.app_context():
        db.create_all()
        yield app
        
    os.close(db_fd)
    os.unlink(db_path)

@pytest.fixture(scope='function')
def client(app):
    """Create test client."""
    return app.test_client()

@pytest.fixture(scope='function')
def db_session(app):
    """Create database session for testing."""
    with app.app_context():
        db.drop_all()
        db.create_all()
        yield db.session
        db.session.rollback()

@pytest.fixture
def user(db_session):
    """Create test user."""
    user = User(
        username='testuser',
        email='test@example.com',
        first_name='Test',
        last_name='User'
    )
    user.set_password('TestPassword123!')
    db_session.add(user)
    db_session.commit()
    return user

@pytest.fixture
def admin_user(db_session):
    """Create admin user."""
    admin = User(
        username='admin',
        email='admin@example.com',
        first_name='Admin',
        last_name='User',
        is_admin=True
    )
    admin.set_password('AdminPassword123!')
    db_session.add(admin)
    db_session.commit()
    return admin

@pytest.fixture
def category(db_session):
    """Create test category."""
    category = Category(
        name='Test Category',
        description='Test category description'
    )
    db_session.add(category)
    db_session.commit()
    return category

@pytest.fixture
def product(db_session, category):
    """Create test product."""
    product = Product(
        name='Test Product',
        description='Test product description',
        price=99.99,
        stock_quantity=10,
        is_active=True
    )
    product.categories.append(category)
    db_session.add(product)
    db_session.commit()
    return product
