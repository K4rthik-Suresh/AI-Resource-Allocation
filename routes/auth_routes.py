

from flask import Blueprint, render_template, request, redirect, url_for, flash, session
from flask_login import login_user, logout_user, current_user, login_required
from flask_bcrypt import Bcrypt
from werkzeug.security import generate_password_hash
from models import db, User, AuditLog
from datetime import datetime, timedelta
import re

auth_bp = Blueprint('auth', __name__)
bcrypt = Bcrypt()

login_attempts = {}
MAX_LOGIN_ATTEMPTS = 5
LOCKOUT_DURATION = timedelta(minutes=15)

def validate_email(email):
    pattern = r'^[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}$'
    return re.match(pattern, email) is not None

def validate_password(password):
    if len(password) < 12:
        return False, "Password must be at least 12 characters long"
    if not re.search(r'[A-Z]', password):
        return False, "Password must contain at least one uppercase letter"
    if not re.search(r'[a-z]', password):
        return False, "Password must contain at least one lowercase letter"
    if not re.search(r'\d', password):
        return False, "Password must contain at least one number"
    if not re.search(r'[!@#$%^&*(),.?":{}|<>]', password):
        return False, "Password must contain at least one special character"
    return True, "Password is strong"

def is_locked_out(ip_address):
    if ip_address in login_attempts:
        attempts, last_attempt = login_attempts[ip_address]
        if attempts >= MAX_LOGIN_ATTEMPTS:
            if datetime.now() - last_attempt < LOCKOUT_DURATION:
                return True
            else:
                del login_attempts[ip_address]
    return False

def record_failed_attempt(ip_address):
    if ip_address in login_attempts:
        attempts, _ = login_attempts[ip_address]
        login_attempts[ip_address] = (attempts + 1, datetime.now())
    else:
        login_attempts[ip_address] = (1, datetime.now())

def clear_login_attempts(ip_address):
    if ip_address in login_attempts:
        del login_attempts[ip_address]

def sanitize_input(text):
    if not text:
        return ""
    text = re.sub(r'<[^>]*>', '', str(text))
    text = text.strip()
    return text

@auth_bp.route('/register', methods=['GET', 'POST'])
def register():
    if current_user.is_authenticated:
        return redirect(url_for('booking.dashboard'))
    
    if request.method == 'POST':
        username = sanitize_input(request.form.get('username', ''))
        email = sanitize_input(request.form.get('email', ''))
        password = request.form.get('password', '')
        full_name = sanitize_input(request.form.get('full_name', ''))
        
        if not username or not email or not password:
            flash('All fields are required', 'error')
            AuditLog.log_action(
                user_id=None,
                action='register_failed',
                ip_address=request.remote_addr,
                user_agent=request.headers.get('User-Agent'),
                details='Missing required fields',
                status='failed'
            )
            return redirect(url_for('auth.register'))
        
        if len(username) < 3 or len(username) > 20:
            flash('Username must be between 3 and 20 characters', 'error')
            return redirect(url_for('auth.register'))
        
        if not re.match(r'^[a-zA-Z0-9_]+$', username):
            flash('Username can only contain letters, numbers, and underscores', 'error')
            return redirect(url_for('auth.register'))
        
        if not validate_email(email):
            flash('Invalid email format', 'error')
            return redirect(url_for('auth.register'))
        
        is_valid, message = validate_password(password)
        if not is_valid:
            flash(message, 'error')
            return redirect(url_for('auth.register'))
        
        if User.query.filter_by(username=username).first():
            flash('Username already exists', 'error')
            return redirect(url_for('auth.register'))
        
        if User.query.filter_by(email=email).first():
            flash('Email already registered', 'error')
            return redirect(url_for('auth.register'))
        
        hashed_password = generate_password_hash(password, method='pbkdf2:sha256')
        user = User(
            username=username,
            email=email,
            password_hash=hashed_password,
            full_name=full_name,
            role='user'
        )
        
        try:
            db.session.add(user)
            db.session.commit()
            AuditLog.log_action(
                user_id=user.id,
                action='register_success',
                ip_address=request.remote_addr,
                user_agent=request.headers.get('User-Agent'),
                details=f'New user registered: {username}',
                status='success'
            )
            flash('Registration successful! Please login.', 'success')
            return redirect(url_for('auth.login'))
        except Exception as e:
            db.session.rollback()
            flash('Registration failed. Please try again.', 'error')
            return redirect(url_for('auth.register'))
    
    return render_template('auth/register.html')

@auth_bp.route('/login', methods=['GET', 'POST'])
def login():
    if current_user.is_authenticated:
        return redirect(url_for('booking.dashboard'))
    
    if request.method == 'POST':
        ip_address = request.remote_addr
        
        if is_locked_out(ip_address):
            AuditLog.log_action(
                user_id=None,
                action='login_blocked',
                ip_address=ip_address,
                user_agent=request.headers.get('User-Agent'),
                details='Account locked due to too many failed attempts',
                status='blocked'
            )
            flash('Too many failed login attempts. Please try again in 15 minutes.', 'error')
            return redirect(url_for('auth.login'))
        
        username = sanitize_input(request.form.get('username', ''))
        password = request.form.get('password', '')
        
        if not username or not password:
            flash('Username and password required', 'error')
            return redirect(url_for('auth.login'))
        
        user = User.query.filter_by(username=username).first()
        
        password_valid = False
        if user:
            try:
                # Use flask_bcrypt's check_password_hash which handles the exact hash format we stored
                password_valid = bcrypt.check_password_hash(user.password_hash, password)
            except Exception:
                try:
                    # Fallback for old werkzeug pbkdf2 hashes in case some exist
                    from werkzeug.security import check_password_hash
                    password_valid = check_password_hash(user.password_hash, password)
                except:
                    password_valid = False
        
        if user and password_valid:
            if not user.is_active:
                AuditLog.log_action(
                    user_id=user.id,
                    action='login_failed',
                    ip_address=ip_address,
                    user_agent=request.headers.get('User-Agent'),
                    details='Account is inactive',
                    status='failed'
                )
                flash('Account is inactive. Contact administrator.', 'error')
                return redirect(url_for('auth.login'))
            
            clear_login_attempts(ip_address)
            
            user.last_login = datetime.utcnow()
            user.last_login_ip = ip_address
            db.session.commit()
            
            login_user(user)
            session.permanent = True
            
            AuditLog.log_action(
                user_id=user.id,
                action='login_success',
                ip_address=ip_address,
                user_agent=request.headers.get('User-Agent'),
                details=f'User {username} logged in successfully',
                status='success'
            )
            
            flash(f'Welcome back, {user.full_name or user.username}!', 'success')
            
            next_page = request.args.get('next')
            if next_page and next_page.startswith('/'):
                return redirect(next_page)
            return redirect(url_for('booking.dashboard'))
        else:
            record_failed_attempt(ip_address)
            attempts_left = MAX_LOGIN_ATTEMPTS - login_attempts.get(ip_address, (0, None))[0]
            
            AuditLog.log_action(
                user_id=user.id if user else None,
                action='login_failed',
                ip_address=ip_address,
                user_agent=request.headers.get('User-Agent'),
                details=f'Failed login attempt for username: {username}',
                status='failed'
            )
            
            if attempts_left > 0:
                flash(f'Invalid username or password. {attempts_left} attempts remaining.', 'error')
            else:
                flash('Account locked due to too many failed attempts. Try again in 15 minutes.', 'error')
            
            return redirect(url_for('auth.login'))
    
    return render_template('auth/login.html')

@auth_bp.route('/logout')
@login_required
def logout():
    AuditLog.log_action(
        user_id=current_user.id,
        action='logout',
        ip_address=request.remote_addr,
        user_agent=request.headers.get('User-Agent'),
        details=f'User {current_user.username} logged out',
        status='success'
    )
    
    session.clear()
    logout_user()
    flash('You have been logged out.', 'success')
    return redirect(url_for('auth.login'))
