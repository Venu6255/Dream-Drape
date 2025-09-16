"""
Flask CLI commands for Dream-Drape application
"""
import click
from flask.cli import with_appcontext
from app import db
from app.models import User, Product, Category, AuditLog
from app.utils import create_sample_data
from datetime import datetime, timedelta
import secrets

@click.command()
@with_appcontext
def init_db():
    """Initialize the database."""
    db.create_all()
    click.echo('Initialized the database.')

@click.command()
@with_appcontext
def create_admin():
    """Create an admin user."""
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
    if create_sample_data():
        click.echo('Sample data created successfully.')
    else:
        click.echo('Error creating sample data.')

@click.command()
@click.option('--days', default=30, help='Number of days to keep logs')
@with_appcontext
def cleanup_logs(days):
    """Clean up old audit logs."""
    cutoff_date = datetime.utcnow() - timedelta(days=int(days))
    
    deleted = AuditLog.query.filter(AuditLog.created_at < cutoff_date).delete()
    db.session.commit()
    
    click.echo(f'Deleted {deleted} old audit log entries.')

@click.command()
@with_appcontext
def reset_failed_logins():
    """Reset failed login attempts for all users."""
    users = User.query.filter(User.failed_login_attempts > 0).all()
    
    for user in users:
        user.failed_login_attempts = 0
        user.locked_until = None
    
    db.session.commit()
    
    click.echo(f'Reset failed login attempts for {len(users)} users.')

@click.command()
@with_appcontext
def generate_secret_key():
    """Generate a secure secret key."""
    key = secrets.token_hex(32)
    click.echo(f'Generated secret key: {key}')
    click.echo('Add this to your .env file as SECRET_KEY')

@click.command()
@with_appcontext
def backup_db():
    """Create a database backup."""
    import subprocess
    import os
    
    timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
    backup_file = f'backup_dreamdrape_{timestamp}.sql'
    
    try:
        # This is for PostgreSQL - adjust for your database
        subprocess.run([
            'pg_dump', 
            os.environ.get('DATABASE_URL', 'postgresql://localhost/dreamdrape'),
            '-f', backup_file
        ], check=True)
        
        click.echo(f'Database backup created: {backup_file}')
    except subprocess.CalledProcessError as e:
        click.echo(f'Backup failed: {e}')

@click.command()
@with_appcontext
def check_security():
    """Run security checks."""
    issues = []
    
    # Check for default admin password
    admin = User.query.filter_by(email='admin@dreamdrape.com').first()
    if admin and admin.check_password('admin123'):
        issues.append('Default admin password is still in use')
    
    # Check for users with weak passwords (this would need password history)
    locked_users = User.query.filter(User.locked_until > datetime.utcnow()).count()
    if locked_users > 0:
        issues.append(f'{locked_users} user accounts are currently locked')
    
    # Check recent failed logins
    recent_failures = AuditLog.query.filter(
        AuditLog.action == 'failed_login',
        AuditLog.created_at >= datetime.utcnow() - timedelta(hours=24)
    ).count()
    
    if recent_failures > 100:
        issues.append(f'{recent_failures} failed login attempts in last 24 hours')
    
    if issues:
        click.echo('Security Issues Found:')
        for issue in issues:
            click.echo(f'  - {issue}')
    else:
        click.echo('No security issues found.')

# Register commands
def register_commands(app):
    """Register CLI commands with Flask app."""
    app.cli.add_command(init_db)
    app.cli.add_command(create_admin)
    app.cli.add_command(create_sample)
    app.cli.add_command(cleanup_logs)
    app.cli.add_command(reset_failed_logins)
    app.cli.add_command(generate_secret_key)
    app.cli.add_command(backup_db)
    app.cli.add_command(check_security)
