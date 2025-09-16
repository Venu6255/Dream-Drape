"""
Flask CLI commands for Dream-Drape application
"""
import click
from flask.cli import with_appcontext
from datetime import datetime, timedelta
import secrets

@click.command()
@with_appcontext
def init_db():
    """Initialize the database."""
    from app import db
    db.create_all()
    click.echo('Initialized the database.')

@click.command()
@with_appcontext
def create_admin():
    """Create an admin user."""
    from app import db
    from app.models import User
    
    email = click.prompt('Admin email')
    password = click.prompt('Admin password', hide_input=True)
    first_name = click.prompt('First name')
    last_name = click.prompt('Last name')
    
    # Check if admin already exists
    if User.query.filter_by(email=email).first():
        click.echo('Admin user already exists.')
        return
    
    admin = User(
        username='admin',
        email=email,
        first_name=first_name,
        last_name=last_name,
        is_admin=True,
        is_active=True
    )
    admin.set_password(password)
    
    db.session.add(admin)
    db.session.commit()
    
    click.echo(f'Admin user created: {email}')

@click.command()
@with_appcontext
def create_sample():
    """Create sample data for testing."""
    from app.utils import create_sample_data
    
    if create_sample_data():
        click.echo('Sample data created successfully.')
    else:
        click.echo('Error creating sample data.')

@click.command()
@click.option('--days', default=30, help='Number of days to keep logs')
@with_appcontext
def cleanup_logs(days):
    """Clean up old audit logs."""
    from app import db
    from app.models import AuditLog
    
    cutoff_date = datetime.utcnow() - timedelta(days=int(days))
    
    deleted = AuditLog.query.filter(AuditLog.created_at < cutoff_date).delete()
    db.session.commit()
    
    click.echo(f'Deleted {deleted} old audit log entries.')

@click.command()
@with_appcontext
def generate_secret_key():
    """Generate a secure secret key."""
    key = secrets.token_hex(32)
    click.echo(f'Generated secret key: {key}')
    click.echo('Add this to your .env file as SECRET_KEY')

def register_commands(app):
    """Register CLI commands with Flask app."""
    app.cli.add_command(init_db)
    app.cli.add_command(create_admin)
    app.cli.add_command(create_sample)
    app.cli.add_command(cleanup_logs)
    app.cli.add_command(generate_secret_key)
