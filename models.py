"""
================================================================================
DATABASE MODELS - SQLAlchemy ORM Models
================================================================================

DESCRIPTION:
    Defines all database tables and their relationships for the resource booking system.

TABLES:
    1. User - User accounts with authentication info
    2. ResourceSystem - Facilities/buildings/campuses  
    3. UserResourceSystem - Admin assignments to specific facilities
    4. Resource - Rooms, labs, equipment within a facility
    5. Booking - Reservations made by users
    6. BookingHistory - Audit log of all booking changes
    7. AuditLog - System-wide activity tracking

RELATIONSHIPS:
    - User (1) --> (Many) Booking
    - User (1) --> (Many) UserResourceSystem
    - ResourceSystem (1) --> (Many) Resource
    - ResourceSystem (1) --> (Many) Booking
    - Resource (1) --> (Many) Booking

SECURITY:
    - Passwords stored as bcrypt hashes (never plain text)
    - Email validation for user accounts
    - Role-based access control (admin/user)

================================================================================
"""

from database import db
from flask_login import UserMixin
from datetime import datetime, time
import enum

class UserRole(enum.Enum):
    ADMIN = 'admin'
    USER = 'user'

class User(UserMixin, db.Model):
    __tablename__ = 'users'
    
    id = db.Column(db.Integer, primary_key=True)
    username = db.Column(db.String(80), unique=True, nullable=False, index=True)
    email = db.Column(db.String(120), unique=True, nullable=False, index=True)
    password_hash = db.Column(db.String(255), nullable=False)
    full_name = db.Column(db.String(120), nullable=True)
    role = db.Column(db.String(20), default='user', nullable=False)
    is_active = db.Column(db.Boolean, default=True)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    updated_at = db.Column(db.DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    last_login = db.Column(db.DateTime, nullable=True)
    last_login_ip = db.Column(db.String(45), nullable=True)
    timezone = db.Column(db.String(50), default='UTC', nullable=False)  # Phase 1: Timezone support
    
    bookings = db.relationship('Booking', backref='user', lazy=True, cascade='all, delete-orphan')
    booking_history = db.relationship('BookingHistory', backref='user', lazy=True)
    audit_logs = db.relationship('AuditLog', backref='user', lazy=True)
    favorites = db.relationship('UserFavorite', backref='user', lazy=True, cascade='all, delete-orphan')  # Phase 1: Favorites
    reviews = db.relationship('ResourceReview', backref='user', lazy=True, cascade='all, delete-orphan')  # Phase 1: Reviews

class ResourceSystem(db.Model):
    __tablename__ = 'resource_systems'
    
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(120), nullable=False, index=True)  # "Building A", "Campus X"
    description = db.Column(db.Text, nullable=True)
    address = db.Column(db.String(255), nullable=False)
    city = db.Column(db.String(120), nullable=False, index=True)
    latitude = db.Column(db.Float, nullable=True)
    longitude = db.Column(db.Float, nullable=True)
    is_public = db.Column(db.Boolean, default=True)  # Visible in discovery
    is_active = db.Column(db.Boolean, default=True)  # Can be deactivated
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    updated_at = db.Column(db.DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    
    resources = db.relationship('Resource', backref='system', lazy=True, cascade='all, delete-orphan')
    user_admins = db.relationship('UserResourceSystem', backref='system', lazy=True, cascade='all, delete-orphan')

class UserResourceSystem(db.Model):
    __tablename__ = 'user_resource_systems'
    
    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey('users.id'), nullable=False, index=True)
    resource_system_id = db.Column(db.Integer, db.ForeignKey('resource_systems.id'), nullable=False, index=True)
    role = db.Column(db.String(20), default='admin')  # admin, viewer
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    
    # Composite unique constraint - one user can be admin of system only once
    __table_args__ = (db.UniqueConstraint('user_id', 'resource_system_id', name='uq_user_system'),)

class Resource(db.Model):
    __tablename__ = 'resources'
    
    id = db.Column(db.Integer, primary_key=True)
    resource_system_id = db.Column(db.Integer, db.ForeignKey('resource_systems.id'), nullable=False, index=True)
    name = db.Column(db.String(120), nullable=False, index=True)
    description = db.Column(db.Text, nullable=True)
    resource_type = db.Column(db.String(50), nullable=False)  # room, hall, lab, equipment
    capacity = db.Column(db.Integer, nullable=True)
    location = db.Column(db.String(255), nullable=True)
    features = db.Column(db.Text, nullable=True)  # JSON string of features
    square_feet = db.Column(db.Float, nullable=True)  # Space in square feet
    hourly_rate = db.Column(db.Float, default=0.0)
    daily_rate = db.Column(db.Float, default=0.0)
    monthly_rate = db.Column(db.Float, default=0.0)
    availability_start = db.Column(db.Time, default=time(9, 0))
    availability_end = db.Column(db.Time, default=time(18, 0))
    is_available = db.Column(db.Boolean, default=True)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    updated_at = db.Column(db.DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    
    bookings = db.relationship('Booking', backref='resource', lazy=True, cascade='all, delete-orphan')

class Booking(db.Model):
    __tablename__ = 'bookings'
    
    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey('users.id'), nullable=False, index=True)
    resource_system_id = db.Column(db.Integer, db.ForeignKey('resource_systems.id'), nullable=False, index=True)
    resource_id = db.Column(db.Integer, db.ForeignKey('resources.id'), nullable=False, index=True)
    booking_date = db.Column(db.Date, nullable=False, index=True)
    start_time = db.Column(db.Time, nullable=False)
    end_time = db.Column(db.Time, nullable=False)
    duration_days = db.Column(db.Integer, default=1, nullable=False)
    purpose = db.Column(db.Text, nullable=True)
    user_notes = db.Column(db.Text, nullable=True)  # Phase 1: User booking notes
    admin_notes = db.Column(db.Text, nullable=True)  # Phase 1: Admin-only notes
    status = db.Column(db.String(20), default='pending')  # pending, confirmed, cancelled, completed
    cancellation_requested = db.Column(db.Boolean, default=False)
    cancellation_reason = db.Column(db.Text, nullable=True)
    cancellation_requested_at = db.Column(db.DateTime, nullable=True)
    booking_type = db.Column(db.String(20), default='hourly')  # hourly, daily, monthly
    cost = db.Column(db.Float, default=0.0)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    updated_at = db.Column(db.DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    
    resource_system = db.relationship('ResourceSystem', foreign_keys=[resource_system_id])
    
    def is_conflict(self):
        """Check if this booking conflicts with existing bookings"""
        existing = Booking.query.filter(
            Booking.resource_id == self.resource_id,
            Booking.booking_date == self.booking_date,
            Booking.status != 'cancelled',
            Booking.id != self.id
        ).all()
        
        for booking in existing:
            if not (self.end_time <= booking.start_time or self.start_time >= booking.end_time):
                return True
        return False

class BookingHistory(db.Model):
    __tablename__ = 'booking_history'
    
    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey('users.id'), nullable=False)
    resource_id = db.Column(db.Integer, db.ForeignKey('resources.id'), nullable=False)
    booking_date = db.Column(db.Date, nullable=False)
    start_time = db.Column(db.Time, nullable=False)
    end_time = db.Column(db.Time, nullable=False)
    action = db.Column(db.String(50), nullable=False)  # created, cancelled, modified
    created_at = db.Column(db.DateTime, default=datetime.utcnow)

class AuditLog(db.Model):
    __tablename__ = 'audit_logs'
    
    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey('users.id'), nullable=True, index=True)
    action = db.Column(db.String(100), nullable=False)  # login, logout, create_booking, etc.
    resource_type = db.Column(db.String(50), nullable=True)  # user, booking, resource
    resource_id = db.Column(db.Integer, nullable=True)
    ip_address = db.Column(db.String(45), nullable=True)
    user_agent = db.Column(db.String(255), nullable=True)
    details = db.Column(db.Text, nullable=True)  # JSON string with additional details
    status = db.Column(db.String(20), default='success')  # success, failed, blocked
    created_at = db.Column(db.DateTime, default=datetime.utcnow, index=True)
    
    @staticmethod
    def log_action(user_id, action, resource_type=None, resource_id=None, 
                   ip_address=None, user_agent=None, details=None, status='success'):
        """Helper method to create audit log entries"""
        log = AuditLog(
            user_id=user_id,
            action=action,
            resource_type=resource_type,
            resource_id=resource_id,
            ip_address=ip_address,
            user_agent=user_agent,
            details=details,
            status=status
        )
        db.session.add(log)
        db.session.commit()
        return log


# ============ PHASE 1: NEW MODELS ============

class UserFavorite(db.Model):
    """User's favorite resources for quick access"""
    __tablename__ = 'user_favorites'
    
    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey('users.id'), nullable=False, index=True)
    resource_id = db.Column(db.Integer, db.ForeignKey('resources.id'), nullable=False, index=True)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    
    resource = db.relationship('Resource', backref='favorited_by')
    
    __table_args__ = (db.UniqueConstraint('user_id', 'resource_id', name='uq_user_favorite'),)


class ResourceReview(db.Model):
    """User reviews and ratings for resources"""
    __tablename__ = 'resource_reviews'
    
    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey('users.id'), nullable=False, index=True)
    resource_id = db.Column(db.Integer, db.ForeignKey('resources.id'), nullable=False, index=True)
    booking_id = db.Column(db.Integer, db.ForeignKey('bookings.id'), nullable=True)  # Link to completed booking
    rating = db.Column(db.Integer, nullable=False)  # 1-5 stars
    comment = db.Column(db.Text, nullable=True)
    created_at = db.Column(db.DateTime, default=datetime.utcnow, index=True)
    updated_at = db.Column(db.DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    
    resource = db.relationship('Resource', backref='reviews')
    booking = db.relationship('Booking', foreign_keys=[booking_id])


class SystemAnnouncement(db.Model):
    """System-wide announcements and notifications"""
    __tablename__ = 'system_announcements'
    
    id = db.Column(db.Integer, primary_key=True)
    title = db.Column(db.String(200), nullable=False)
    message = db.Column(db.Text, nullable=False)
    announcement_type = db.Column(db.String(20), default='info')  # info, warning, maintenance, alert
    created_by = db.Column(db.Integer, db.ForeignKey('users.id'), nullable=False)  # Admin user
    start_date = db.Column(db.DateTime, default=datetime.utcnow)
    end_date = db.Column(db.DateTime, nullable=True)  # Expiry date
    is_active = db.Column(db.Boolean, default=True)
    is_pinned = db.Column(db.Boolean, default=False)  # Pinned to top
    created_at = db.Column(db.DateTime, default=datetime.utcnow, index=True)
    updated_at = db.Column(db.DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    
    creator = db.relationship('User', foreign_keys=[created_by])
    
    def is_expired(self):
        """Check if announcement is expired"""
        if self.end_date:
            return datetime.utcnow() > self.end_date
        return False
    
    @staticmethod
    def get_active_announcements():
        """Get all active non-expired announcements"""
        return SystemAnnouncement.query.filter(
            SystemAnnouncement.is_active == True,
            SystemAnnouncement.start_date <= datetime.utcnow(),
            db.or_(
                SystemAnnouncement.end_date == None,
                SystemAnnouncement.end_date >= datetime.utcnow()
            )
        ).order_by(
            SystemAnnouncement.is_pinned.desc(),
            SystemAnnouncement.created_at.desc()
        ).all()
