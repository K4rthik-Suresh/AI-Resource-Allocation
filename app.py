"""
================================================================================
AI-ENABLED MULTI-SYSTEM RESOURCE BOOKING SYSTEM
Main Flask Application File
================================================================================

DESCRIPTION:
    This is the main Flask application file that initializes and configures 
    the entire resource booking system with AI-powered natural language processing.

FEATURES:
    - Multi-facility/system support (Discovery-First Architecture)
    - AI-powered natural language booking search
    - User authentication with password hashing (bcrypt)
    - Security: CSRF protection, rate limiting, CSP, HTTPS headers
    - Session-based system context (one active facility per user)
    - Geolocation-based facility discovery
    - Complete booking management with conflict detection
    - Admin dashboard for facility management

KEY TECHNOLOGIES:
    - Flask: Web framework
    - SQLAlchemy: ORM for database operations
    - Flask-Login: User authentication and session management
    - Flask-Bcrypt: Password hashing for security
    - Flask-WTF: CSRF protection
    - Flask-Limiter: Rate limiting
    - Flask-Talisman: Security headers

DATABASE:
    - SQLite database: resource_booking.db
    - Tables: users, resource_systems, resources, bookings, user_resource_systems, etc.

ROUTES:
    - Blueprint auth_bp: Login/Register (/auth/*)
    - Blueprint resource_bp: Resource listing/details (/resources/*)
    - Blueprint booking_bp: Booking management (/bookings/*)
    - Blueprint admin_bp: Admin dashboard (/admin/*)
    - Blueprint ai_bp: NLP search (/ai/*)
    - Blueprint system_bp: Facility discovery (/system/*)

SECURITY FEATURES:
    - Password hashing with bcrypt (12+ chars, mixed case, numbers, symbols)
    - Session cookies: Secure, HttpOnly, SameSite
    - CSRF tokens for all forms
    - Rate limiting: 200/day, 50/hour per IP
    - Content Security Policy (CSP)
    - SQL injection prevention (SQLAlchemy parameterized queries)
    - XSS protection
    - HSTS (HTTP Strict Transport Security)

HOW TO RUN:
    1. pip install -r requirements.txt
    2. python init_system.py
    3. python create_users.py
    4. python app.py
    
    Then open: http://localhost:5000

LOGIN CREDENTIALS:
    Admin: admin / Admin@123456
    User: user1 / User@1234567

================================================================================
"""

from flask import Flask, render_template, redirect, url_for, request, jsonify, session
from database import db
from flask_sqlalchemy import SQLAlchemy
from flask_login import LoginManager, login_user, logout_user, login_required, current_user
from flask_bcrypt import Bcrypt
from datetime import datetime, timedelta
import os
from dotenv import load_dotenv
from flask_wtf.csrf import CSRFProtect
from flask_limiter import Limiter
from flask_limiter.util import get_remote_address
from flask_talisman import Talisman

# Load environment variables from .env file
load_dotenv()

app = Flask(__name__)

# Detect environment
IS_PRODUCTION = os.environ.get('FLASK_ENV', 'development') == 'production'

# Configuration
app.config['SECRET_KEY'] = os.environ.get('SECRET_KEY', os.urandom(32).hex())

# Database URL parsing (Neon provides postgres://, SQLAlchemy requires postgresql://)
database_url = os.environ.get('DATABASE_URL', 'sqlite:///resource_booking.db')
if database_url.startswith('postgres://'):
    database_url = database_url.replace('postgres://', 'postgresql://', 1)

app.config['SQLALCHEMY_DATABASE_URI'] = database_url
app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False
app.config['SESSION_COOKIE_SECURE'] = IS_PRODUCTION  # Only enforce HTTPS cookies in production
app.config['SESSION_COOKIE_HTTPONLY'] = True
app.config['SESSION_COOKIE_SAMESITE'] = 'Lax'
app.config['PERMANENT_SESSION_LIFETIME'] = timedelta(hours=2)
app.config['WTF_CSRF_TIME_LIMIT'] = None
app.config['WTF_CSRF_EXEMPT_LIST'] = ['/ai/nlp-booking']

db.init_app(app)
bcrypt = Bcrypt(app)

csrf = CSRFProtect(app)

limiter = Limiter(
    app=app,
    key_func=get_remote_address,
    default_limits=["200 per day", "50 per hour"],
    storage_uri="memory://"
)

csp = {
    'default-src': "'self'",
    'script-src': ["'self'", "'unsafe-inline'", "cdn.jsdelivr.net"],
    'style-src': ["'self'", "'unsafe-inline'", "cdn.jsdelivr.net"],
    'img-src': ["'self'", "data:", "https:"],
    'font-src': ["'self'", "cdn.jsdelivr.net"]
}
Talisman(app, 
         force_https=IS_PRODUCTION,  # Enable HTTPS redirect in production
         content_security_policy=csp,
         content_security_policy_nonce_in=['script-src'])

login_manager = LoginManager()
login_manager.init_app(app)
login_manager.login_view = 'auth.login'
login_manager.session_protection = 'strong'

@app.template_filter('format_12hr')
def format_12hr(time_str):
    """Convert 24-hour time format (HH:MM) to 12-hour format with AM/PM"""
    try:
        if isinstance(time_str, str):
            hour, minute = map(int, time_str.split(':'))
        else:
            # Handle time object
            hour = time_str.hour
            minute = time_str.minute
        
        meridiem = 'AM' if hour < 12 else 'PM'
        hour_12 = hour if hour <= 12 else hour - 12
        if hour == 0:
            hour_12 = 12
        
        return f"{hour_12:02d}:{minute:02d} {meridiem}"
    except:
        return time_str

@app.template_filter('format_time_range')
def format_time_range(start_time, end_time):
    """Format a time range in 12-hour format"""
    try:
        def convert_to_12hr(time_val):
            if isinstance(time_val, str):
                hour, minute = map(int, time_val.split(':'))
            else:
                hour = time_val.hour
                minute = time_val.minute
            
            meridiem = 'AM' if hour < 12 else 'PM'
            hour_12 = hour if hour <= 12 else hour - 12
            if hour == 0:
                hour_12 = 12
            
            return f"{hour_12:02d}:{minute:02d} {meridiem}"
        
        return f"{convert_to_12hr(start_time)} - {convert_to_12hr(end_time)}"
    except:
        return f"{start_time} - {end_time}"

# Import models and routes after app initialization
from models import User, Resource, Booking, BookingHistory
from routes.auth_routes import auth_bp
from routes.resource_routes import resource_bp
from routes.booking_routes import booking_bp
from routes.admin_routes import admin_bp
from routes.ai_routes import ai_bp
from routes.system_routes import system_bp
from routes.favorites_routes import favorites_bp  # Phase 1: Favorites
from routes.export_routes import export_bp  # Phase 1: CSV Export
from routes.announcements_routes import announcements_bp  # Phase 1: Announcements

# Register blueprints
app.register_blueprint(auth_bp)
app.register_blueprint(resource_bp)
app.register_blueprint(booking_bp)
app.register_blueprint(admin_bp)
app.register_blueprint(ai_bp)
app.register_blueprint(system_bp)
app.register_blueprint(favorites_bp)  # Phase 1: Favorites
app.register_blueprint(export_bp)  # Phase 1: CSV Export
app.register_blueprint(announcements_bp)  # Phase 1: Announcements

@login_manager.user_loader
def load_user(user_id):
    return User.query.get(int(user_id))

@app.route('/')
def index():
    if current_user.is_authenticated:
        return redirect(url_for('booking.dashboard'))
    return redirect(url_for('auth.login'))

@app.route('/health')
def health():
    return jsonify({'status': 'healthy'}), 200

@app.route('/ai')
@login_required
def ai_features():
    return render_template('ai/features.html')

@app.errorhandler(404)
def not_found_error(error):
    return render_template('errors/404.html'), 404

@app.errorhandler(500)
def internal_error(error):
    db.session.rollback()
    return render_template('errors/500.html'), 500

@app.errorhandler(403)
def forbidden_error(error):
    return render_template('errors/403.html'), 403

@app.after_request
def set_security_headers(response):
    response.headers['X-Content-Type-Options'] = 'nosniff'
    response.headers['X-Frame-Options'] = 'SAMEORIGIN'
    response.headers['X-XSS-Protection'] = '1; mode=block'
    response.headers['Strict-Transport-Security'] = 'max-age=31536000; includeSubDomains'
    return response

def initialize_resource_systems():
    """Initialize resource systems on app startup"""
    from models import ResourceSystem, UserResourceSystem, Resource, User, Booking
    
    # Check if default system exists
    default_system = ResourceSystem.query.filter_by(name='Main Facility').first()
    
    if not default_system:
        default_system = ResourceSystem(
            name='Main Facility',
            description='Default resource facility',
            address='Default Address',
            city='Default City',
            latitude=None,
            longitude=None,
            is_public=True,
            is_active=True
        )
        db.session.add(default_system)
        db.session.commit()
        print("[v0] Created default ResourceSystem: 'Main Facility'")
    
    # Migrate resources without system assignment
    unassigned_resources = Resource.query.filter_by(resource_system_id=None).all()
    if unassigned_resources:
        for resource in unassigned_resources:
            resource.resource_system_id = default_system.id
        db.session.commit()
        print(f"[v0] Migrated {len(unassigned_resources)} resources to Main Facility")
    
    # Migrate bookings without system assignment
    unassigned_bookings = Booking.query.filter_by(resource_system_id=None).all()
    if unassigned_bookings:
        for booking in unassigned_bookings:
            booking.resource_system_id = default_system.id
        db.session.commit()
        print(f"[v0] Migrated {len(unassigned_bookings)} bookings to Main Facility")
    
    # Assign admin users to default system
    admin_users = User.query.filter_by(role='admin').all()
    for admin_user in admin_users:
        existing = UserResourceSystem.query.filter_by(
            user_id=admin_user.id,
            resource_system_id=default_system.id
        ).first()
        if not existing:
            assignment = UserResourceSystem(
                user_id=admin_user.id,
                resource_system_id=default_system.id,
                role='admin'
            )
            db.session.add(assignment)
    
    db.session.commit()
    print(f"[v0] Assigned {len(admin_users)} admin users to Main Facility")

@app.before_request
def set_active_system():
    """Set the active resource system in session"""
    from models import ResourceSystem
    
    if current_user.is_authenticated:
        # Get or set active system from session
        if 'active_system_id' not in session:
            # Get user's first accessible system
            if current_user.role == 'admin':
                # Admin gets their assigned systems
                from models import UserResourceSystem
                admin_system = UserResourceSystem.query.filter_by(
                    user_id=current_user.id
                ).first()
                if admin_system:
                    session['active_system_id'] = admin_system.resource_system_id
                else:
                    # Fallback to default
                    default = ResourceSystem.query.filter_by(name='Main Facility').first()
                    if default:
                        session['active_system_id'] = default.id
            else:
                # Regular user - set to default
                default = ResourceSystem.query.filter_by(name='Main Facility').first()
                if default:
                    session['active_system_id'] = default.id
            
            if 'active_system_id' in session:
                session.modified = True

# Create tables when imported by gunicorn (production)
with app.app_context():
    db.create_all()
    initialize_resource_systems()

if __name__ == '__main__':
    app.run(debug=not IS_PRODUCTION, port=int(os.environ.get('PORT', 5000)))
