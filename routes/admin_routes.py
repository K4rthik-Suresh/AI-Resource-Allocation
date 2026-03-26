from flask import Blueprint, render_template, request, redirect, url_for, flash, jsonify
from flask_login import login_required, current_user
from models import db, User, Resource, Booking, BookingHistory, ResourceSystem
from datetime import datetime, timedelta, date
from sqlalchemy import func
from werkzeug.security import generate_password_hash, check_password_hash
import logging

logger = logging.getLogger(__name__)

admin_bp = Blueprint('admin', __name__, url_prefix='/admin')

def admin_required(f):
    """Decorator to check if user is admin"""
    from functools import wraps
    @wraps(f)
    def decorated_function(*args, **kwargs):
        if not current_user.role == 'admin':
            flash("You don't have permission to access this page.", "error")
            return redirect(url_for('resource.list_resources'))
        return f(*args, **kwargs)
    return decorated_function

@admin_bp.route('/dashboard')
@login_required
@admin_required
def dashboard():
    """Admin dashboard with status filtering"""
    total_users = User.query.count()
    total_bookings = Booking.query.count()
    total_resources = Resource.query.count()
    
    total_revenue = db.session.query(func.sum(Booking.cost)).filter(
        Booking.status.in_(['confirmed', 'completed'])
    ).scalar()
    total_revenue = float(total_revenue) if total_revenue else 0.0
    
    # Get filter from query params
    booking_status = request.args.get('booking_status', '').strip()
    
    # Get recent bookings with optional status filter
    query = Booking.query.order_by(Booking.created_at.desc())
    if booking_status and booking_status in ['pending', 'confirmed', 'cancelled', 'completed']:
        query = query.filter(Booking.status == booking_status)
    
    recent_bookings = query.limit(5).all()
    
    return render_template('admin/dashboard.html',
                         total_users=total_users,
                         total_bookings=total_bookings,
                         total_resources=total_resources,
                         total_revenue=total_revenue,
                         recent_bookings=recent_bookings)

@admin_bp.route('/analytics')
@login_required
@admin_required
def analytics():
    """Advanced Analytics dashboard with comprehensive booking data"""
    
    # Get pagination
    page = request.args.get('page', 1, type=int)
    
    # Get all resources paginated
    resources_paginated = Resource.query.paginate(page=page, per_page=20)
    
    # Date ranges
    today = datetime.utcnow().date()
    start_date_30 = today - timedelta(days=30)
    start_date_year = today - timedelta(days=365)
    
    # 1. BASIC KPIs - Last 30 days
    total_bookings_30 = Booking.query.filter(
        Booking.created_at >= start_date_30,
        Booking.status != 'cancelled'
    ).count()
    
    total_revenue_30 = db.session.query(func.sum(Booking.cost)).filter(
        Booking.created_at >= start_date_30,
        Booking.status != 'cancelled'
    ).scalar() or 0.0
    
    bookings_today = Booking.query.filter(
        Booking.created_at >= today,
        Booking.status != 'cancelled'
    ).count()
    
    # 2. MOST BOOKED RESOURCES (Last 30 days)
    most_booked = db.session.query(
        Resource.id,
        Resource.name,
        func.count(Booking.id).label('booking_count')
    ).join(Booking).filter(
        Booking.created_at >= start_date_30,
        Booking.status != 'cancelled'
    ).group_by(Resource.id, Resource.name).order_by(func.count(Booking.id).desc()).limit(5).all()
    
    most_booked_rooms = [{'name': r[1], 'bookings': r[2]} for r in most_booked]
    
    # 3. LEAST BOOKED RESOURCES (that have at least one booking)
    least_booked = db.session.query(
        Resource.id,
        Resource.name,
        func.count(Booking.id).label('booking_count')
    ).outerjoin(Booking, (Booking.resource_id == Resource.id) & 
        (Booking.created_at >= start_date_30) & 
        (Booking.status != 'cancelled')).group_by(Resource.id, Resource.name).order_by(func.count(Booking.id)).limit(5).all()
    
    least_booked_rooms = [{'name': r[1], 'bookings': r[2] or 0} for r in least_booked]
    
    # 4. MOST SEARCHED RESOURCE TYPE
    most_searched_type = db.session.query(
        Resource.resource_type,
        func.count(Booking.id).label('booking_count')
    ).join(Booking).filter(
        Booking.created_at >= start_date_30,
        Booking.status != 'cancelled'
    ).group_by(Resource.resource_type).order_by(func.count(Booking.id).desc()).limit(5).all()
    
    resource_types_data = [{'type': r[0], 'count': r[1]} for r in most_searched_type]
    
    # 5. MOST SEARCHED CAPACITY
    most_searched_capacity = db.session.query(
        Resource.capacity,
        func.count(Booking.id).label('booking_count')
    ).join(Booking).filter(
        Booking.created_at >= start_date_30,
        Booking.status != 'cancelled'
    ).group_by(Resource.capacity).order_by(func.count(Booking.id).desc()).limit(5).all()
    
    capacity_data = [{'capacity': r[0], 'count': r[1]} for r in most_searched_capacity]
    
    # 6. MOST SEARCHED TIME SLOTS
    most_searched_times = db.session.query(
        Booking.start_time,
        func.count(Booking.id).label('booking_count')
    ).filter(
        Booking.created_at >= start_date_30,
        Booking.status != 'cancelled'
    ).group_by(Booking.start_time).order_by(func.count(Booking.id).desc()).limit(5).all()
    
    time_slots_data = [{'time': r[0].strftime('%H:%M') if r[0] else 'N/A', 'count': r[1]} for r in most_searched_times]
    
    # 7. MONTHLY BOOKINGS (Last 12 months) - For Chart
    monthly_bookings = []
    from dateutil.relativedelta import relativedelta
    
    for i in range(12, -1, -1):
        month_date = today - relativedelta(months=i)
        month_start = month_date.replace(day=1)
        
        # Get next month start date for end boundary
        if month_date.month == 12:
            month_end = month_date.replace(year=month_date.year + 1, month=1, day=1)
        else:
            month_end = month_date.replace(month=month_date.month + 1, day=1)
        
        try:
            month_count = Booking.query.filter(
                Booking.created_at >= month_start,
                Booking.created_at < month_end,
                Booking.status != 'cancelled'
            ).count()
        except Exception as e:
            logger.error(f"Error counting monthly bookings: {e}")
            month_count = 0
        
        monthly_bookings.append({
            'month': month_start.strftime('%b %Y'),
            'bookings': month_count
        })
    
    # 8. DAILY BOOKINGS (Last 30 days) - For Table
    daily_bookings = []
    try:
        daily_result = db.session.query(
            Booking.booking_date,
            func.count(Booking.id)
        ).filter(
            Booking.booking_date >= start_date_30,
            Booking.status != 'cancelled'
        ).group_by(Booking.booking_date).order_by(Booking.booking_date.desc()).all()
        
        for booking_date, count in daily_result:
            daily_bookings.append({'date': str(booking_date), 'bookings': int(count)})
    except Exception as e:
        logger.error(f"Error getting daily bookings: {e}")
        pass
    
    # 9. RESOURCE STATS
    resource_stats = []
    for resource in resources_paginated.items:
        res_count = Booking.query.filter(
            Booking.resource_id == resource.id,
            Booking.created_at >= start_date_30,
            Booking.status != 'cancelled'
        ).count()
        
        resource_stats.append({
            'id': resource.id,
            'name': resource.name,
            'resource_type': resource.resource_type,
            'capacity': resource.capacity,
            'hourly_rate': resource.hourly_rate,
            'bookings': res_count
        })
    
    # 10. KPIs
    active_bookings = Booking.query.filter(
        Booking.status == 'confirmed',
        Booking.booking_date >= today
    ).count()

    kpis = {
        'total_bookings': total_bookings_30,
        'total_revenue': total_revenue_30,
        'bookings_today': bookings_today,
        'active_bookings': active_bookings
    }
    
    return render_template('admin/analytics.html', 
                         resource_stats=resource_stats,
                         resources_paginated=resources_paginated,
                         kpis=kpis,
                         daily_bookings=daily_bookings,
                         most_booked_rooms=most_booked_rooms,
                         least_booked_rooms=least_booked_rooms,
                         resource_types_data=resource_types_data,
                         capacity_data=capacity_data,
                         time_slots_data=time_slots_data,
                         monthly_bookings=monthly_bookings)

@admin_bp.route('/manage-bookings')
@login_required
@admin_required
def manage_bookings():
    """Manage all bookings with status filtering"""
    # Auto-update expired bookings to 'completed' status
    from routes.booking_routes import mark_expired_bookings_as_completed
    mark_expired_bookings_as_completed()
    
    page = request.args.get('page', 1, type=int)
    status = request.args.get('status', 'all').strip().lower()
    
    query = Booking.query.order_by(Booking.created_at.desc())
    
    # Apply status filter
    if status == 'pending':
        query = query.filter(Booking.status == 'pending')
    elif status == 'confirmed':
        query = query.filter(Booking.status == 'confirmed')
    elif status == 'cancelled':
        query = query.filter(Booking.status == 'cancelled')
    elif status == 'completed':
        query = query.filter(Booking.status == 'completed')
    elif status == 'cancellation_requests':
        query = query.filter(Booking.cancellation_requested == True)
    # else: 'all' - no filter, show all
    
    bookings = query.paginate(page=page, per_page=20)
    return render_template('admin/bookings.html', bookings=bookings, status=status)

@admin_bp.route('/manage-resources')
@login_required
@admin_required
def manage_resources():
    """List and manage resources"""
    page = request.args.get('page', 1, type=int)
    resources = Resource.query.paginate(page=page, per_page=20)
    return render_template('admin/resources.html', resources=resources)

@admin_bp.route('/resource/<int:resource_id>/edit', methods=['GET', 'POST'])
@login_required
@admin_required
def edit_resource(resource_id):
    """Edit a resource"""
    resource = Resource.query.get_or_404(resource_id)
    
    if request.method == 'POST':
        try:
            resource.name = request.form.get('name', '').strip() or resource.name
            resource.description = request.form.get('description', '').strip() or resource.description
            resource.resource_type = request.form.get('resource_type', '').strip() or resource.resource_type
            capacity = request.form.get('capacity', type=int)
            if capacity:
                resource.capacity = capacity
            hourly_rate = request.form.get('hourly_rate', type=float)
            if hourly_rate is not None:
                resource.hourly_rate = hourly_rate
            resource.location = request.form.get('location', '').strip() or resource.location
            
            db.session.commit()
            flash(f"Resource '{resource.name}' updated successfully!", "success")
            return redirect(url_for('admin.manage_resources'))
        except Exception as e:
            db.session.rollback()
            logger.error(f"Error editing resource: {e}", exc_info=True)
            flash(f"Error updating resource: {str(e)}", "error")
    
    return render_template('admin/edit_resource.html', resource=resource)

@admin_bp.route('/resource/<int:resource_id>/delete', methods=['POST'])
@login_required
@admin_required
def delete_resource(resource_id):
    """Delete a resource"""
    resource = Resource.query.get_or_404(resource_id)
    
    try:
        resource_name = resource.name
        db.session.delete(resource)
        db.session.commit()
        flash(f"Resource '{resource_name}' deleted successfully!", "success")
    except Exception as e:
        db.session.rollback()
        logger.error(f"Error deleting resource: {e}", exc_info=True)
        flash(f"Error deleting resource: {str(e)}", "error")
    
    return redirect(url_for('admin.manage_resources'))

@admin_bp.route('/resource/<int:resource_id>/toggle-availability', methods=['POST'])
@login_required
@admin_required
def toggle_availability(resource_id):
    """Toggle resource availability"""
    resource = Resource.query.get_or_404(resource_id)
    
    try:
        resource.is_available = not resource.is_available
        db.session.commit()
        status = "available" if resource.is_available else "unavailable"
        flash(f"Resource '{resource.name}' is now {status}.", "success")
    except Exception as e:
        db.session.rollback()
        logger.error(f"Error toggling availability: {e}", exc_info=True)
        flash(f"Error updating availability: {str(e)}", "error")
    
    return redirect(url_for('admin.manage_resources'))

@admin_bp.route('/booking/<int:booking_id>/confirm', methods=['POST'])
@login_required
@admin_required
def confirm_booking(booking_id):
    """Confirm a pending booking"""
    booking = Booking.query.get_or_404(booking_id)
    
    try:
        booking.status = 'confirmed'
        db.session.commit()
        flash(f"Booking #{booking.id} confirmed successfully!", "success")
    except Exception as e:
        db.session.rollback()
        logger.error(f"Error confirming booking: {e}", exc_info=True)
        flash(f"Error confirming booking: {str(e)}", "error")
    
    return redirect(url_for('admin.manage_bookings'))

@admin_bp.route('/booking/<int:booking_id>/reject', methods=['POST'])
@login_required
@admin_required
def reject_booking(booking_id):
    """Reject a pending booking"""
    booking = Booking.query.get_or_404(booking_id)
    
    try:
        booking.status = 'cancelled'
        db.session.commit()
        flash(f"Booking #{booking.id} rejected successfully!", "success")
    except Exception as e:
        db.session.rollback()
        logger.error(f"Error rejecting booking: {e}", exc_info=True)
        flash(f"Error rejecting booking: {str(e)}", "error")
    
    return redirect(url_for('admin.manage_bookings'))

@admin_bp.route('/booking/<int:booking_id>/approve-cancellation', methods=['POST'])
@login_required
@admin_required
def approve_cancellation(booking_id):
    """Approve a cancellation request"""
    booking = Booking.query.get_or_404(booking_id)
    
    try:
        booking.status = 'cancelled'
        booking.cancellation_requested = False
        db.session.commit()
        flash(f"Cancellation request for booking #{booking.id} approved!", "success")
    except Exception as e:
        db.session.rollback()
        logger.error(f"Error approving cancellation: {e}", exc_info=True)
        flash(f"Error approving cancellation: {str(e)}", "error")
    
    return redirect(url_for('admin.manage_bookings', status='cancellation_requests'))

@admin_bp.route('/booking/<int:booking_id>/reject-cancellation', methods=['POST'])
@login_required
@admin_required
def reject_cancellation(booking_id):
    """Reject a cancellation request"""
    booking = Booking.query.get_or_404(booking_id)
    
    try:
        booking.cancellation_requested = False
        db.session.commit()
        flash(f"Cancellation request for booking #{booking.id} rejected!", "success")
    except Exception as e:
        db.session.rollback()
        logger.error(f"Error rejecting cancellation: {e}", exc_info=True)
        flash(f"Error rejecting cancellation: {str(e)}", "error")
    
    return redirect(url_for('admin.manage_bookings', status='cancellation_requests'))

@admin_bp.route('/create-resource', methods=['GET', 'POST'])
@login_required
@admin_required
def create_resource():
    """Create a new resource"""
    if request.method == 'POST':
        try:
            name = request.form.get('name', '').strip()
            description = request.form.get('description', '').strip()
            resource_type = request.form.get('resource_type', '').strip()
            capacity = request.form.get('capacity', type=int)
            hourly_rate = request.form.get('hourly_rate', type=float)
            location = request.form.get('location', '').strip()
            
            if not all([name, resource_type, capacity, hourly_rate]):
                flash("Please fill in all required fields.", "error")
                return render_template('admin/create_resource.html')
            
            # Get the first resource system (default)
            system = ResourceSystem.query.first()
            if not system:
                flash("No resource system found. Please contact administrator.", "error")
                return render_template('admin/create_resource.html')
            
            resource = Resource(
                resource_system_id=system.id,
                name=name,
                description=description,
                resource_type=resource_type,
                capacity=capacity,
                hourly_rate=hourly_rate,
                location=location
            )
            db.session.add(resource)
            db.session.commit()
            
            flash(f"Resource '{name}' created successfully!", "success")
            return redirect(url_for('admin.manage_resources'))
        except Exception as e:
            logger.error(f"Error creating resource: {e}", exc_info=True)
            flash(f"Error creating resource: {str(e)}", "error")
            return render_template('admin/create_resource.html')
    
    return render_template('admin/create_resource.html')

@admin_bp.route('/add-resource')
@login_required
@admin_required
def add_resource():
    """Redirect to create resource form"""
    return redirect(url_for('admin.create_resource'))

@admin_bp.route('/manage-users')
@login_required
@admin_required
def manage_users():
    """List and manage users"""
    page = request.args.get('page', 1, type=int)
    users = User.query.paginate(page=page, per_page=20)
    return render_template('admin/users.html', users=users)

@admin_bp.route('/user/create', methods=['GET', 'POST'])
@login_required
@admin_required
def create_user():
    """Create a new user"""
    if request.method == 'POST':
        username = request.form.get('username', '').strip()
        password = request.form.get('password', '').strip()
        password_confirm = request.form.get('password_confirm', '').strip()
        
        # Validation
        if not username or len(username) < 3:
            flash("Username must be at least 3 characters long.", "error")
            return redirect(url_for('admin.create_user'))
        
        if not password or len(password) < 6:
            flash("Password must be at least 6 characters long.", "error")
            return redirect(url_for('admin.create_user'))
        
        if password != password_confirm:
            flash("Passwords do not match.", "error")
            return redirect(url_for('admin.create_user'))
        
        # Check if username exists
        if User.query.filter_by(username=username).first():
            flash(f"Username '{username}' already exists.", "error")
            return redirect(url_for('admin.create_user'))
        
        try:
            # Create new user with default email format
            new_user = User(
                username=username,
                email=f"{username}@resourcebooking.com",
                password_hash=generate_password_hash(password, method='pbkdf2:sha256'),
                role='user',
                is_active=True
            )
            
            db.session.add(new_user)
            db.session.commit()
            
            flash(f"User '{username}' created successfully!", "success")
            return redirect(url_for('admin.manage_users'))
        except Exception as e:
            db.session.rollback()
            logger.error(f"Error creating user: {e}", exc_info=True)
            flash(f"Error creating user: {str(e)}", "error")
            return redirect(url_for('admin.create_user'))
    
    return render_template('admin/create_user.html')

@admin_bp.route('/user/<int:user_id>/edit', methods=['GET', 'POST'])
@login_required
@admin_required
def edit_user(user_id):
    """Edit user credentials"""
    user = User.query.get_or_404(user_id)
    
    if request.method == 'POST':
        username = request.form.get('username', '').strip()
        password = request.form.get('password', '').strip()
        password_confirm = request.form.get('password_confirm', '').strip()
        
        try:
            # Update username if changed
            if username and username != user.username:
                if len(username) < 3:
                    flash("Username must be at least 3 characters long.", "error")
                    return redirect(url_for('admin.edit_user', user_id=user_id))
                
                if User.query.filter_by(username=username).first():
                    flash(f"Username '{username}' is already taken.", "error")
                    return redirect(url_for('admin.edit_user', user_id=user_id))
                
                user.username = username
            
            # Update password if provided
            if password:
                if len(password) < 6:
                    flash("Password must be at least 6 characters long.", "error")
                    return redirect(url_for('admin.edit_user', user_id=user_id))
                
                if password != password_confirm:
                    flash("Passwords do not match.", "error")
                    return redirect(url_for('admin.edit_user', user_id=user_id))
                
                user.password_hash = generate_password_hash(password, method='pbkdf2:sha256')
            
            db.session.commit()
            flash(f"User '{user.username}' updated successfully!", "success")
            return redirect(url_for('admin.manage_users'))
        except Exception as e:
            db.session.rollback()
            logger.error(f"Error editing user: {e}", exc_info=True)
            flash(f"Error updating user: {str(e)}", "error")
    
    return render_template('admin/edit_user.html', user=user)
