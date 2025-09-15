from flask import Flask
from flask_sqlalchemy import SQLAlchemy
from flask_login import LoginManager
from flask_mail import Mail
from config import Config

db = SQLAlchemy()
login = LoginManager()
login.login_view = 'auth.login'
login.login_message = 'Please log in to access this page.'
mail = Mail()

def create_app(config_class=Config):
    app = Flask(__name__)
    app.config.from_object(config_class)
    
    db.init_app(app)
    login.init_app(app)
    mail.init_app(app)
    
    # Register blueprints
    from app.routes import main
    from app.auth import auth
    from app.admin import admin
    
    app.register_blueprint(main)
    app.register_blueprint(auth, url_prefix='/auth')
    app.register_blueprint(admin, url_prefix='/admin')
    
    # Create database tables
    with app.app_context():
        db.create_all()
        
        # Create admin user if it doesn't exist
        from app.models import User
        admin_user = User.query.filter_by(email=app.config['ADMIN_EMAIL']).first()
        if not admin_user:
            admin_user = User(
                username='admin',
                email=app.config['ADMIN_EMAIL'],
                first_name='Admin',
                last_name='User',
                is_admin=True
            )
            admin_user.set_password(app.config['ADMIN_PASSWORD'])
            db.session.add(admin_user)
            db.session.commit()
    
    return app