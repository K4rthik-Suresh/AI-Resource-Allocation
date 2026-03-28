


from flask import Blueprint, render_template, request, jsonify, redirect, url_for, flash
from flask_login import login_required, current_user
from models import db, Resource, Booking
from datetime import datetime, date
from sqlalchemy import and_
from sqlalchemy.orm import joinedload

resource_bp = Blueprint('resource', __name__, url_prefix='/resources')

@resource_bp.route('/')
def list_resources():
    page = request.args.get('page', 1, type=int)
    search_query = request.args.get('search', '')
    capacity_range = request.args.get('capacity', '')
    price_range = request.args.get('price_range', '')
    sort_by = request.args.get('sort', '')
    
    # Simple query - get all available resources without system filtering
    query = Resource.query.filter_by(is_available=True)
    
    if search_query:
        query = query.filter(Resource.name.ilike(f'%{search_query}%'))
    
    if capacity_range:
        if capacity_range == '1-10':
            query = query.filter(Resource.capacity.between(1, 10))
        elif capacity_range == '11-25':
            query = query.filter(Resource.capacity.between(11, 25))
        elif capacity_range == '26-50':
            query = query.filter(Resource.capacity.between(26, 50))
        elif capacity_range == '51-100':
            query = query.filter(Resource.capacity.between(51, 100))
        elif capacity_range == '100+':
            query = query.filter(Resource.capacity >= 100)
    
    if price_range:
        if price_range == '0-50':
            query = query.filter(Resource.hourly_rate.between(0, 50))
        elif price_range == '51-100':
            query = query.filter(Resource.hourly_rate.between(51, 100))
        elif price_range == '101-200':
            query = query.filter(Resource.hourly_rate.between(101, 200))
        elif price_range == '200+':
            query = query.filter(Resource.hourly_rate >= 200)
    
    if sort_by == 'name':
        query = query.order_by(Resource.name.asc())
    elif sort_by == 'price_low':
        query = query.order_by(Resource.hourly_rate.asc())
    elif sort_by == 'price_high':
        query = query.order_by(Resource.hourly_rate.desc())
    elif sort_by == 'capacity':
        query = query.order_by(Resource.capacity.desc())
    else:
        query = query.order_by(Resource.name.asc())
    
    # Eager load the favorited_by relationship for all resources
    query = query.options(joinedload(Resource.favorited_by))
    
    resources = query.paginate(page=page, per_page=12)
    return render_template('resources/list.html', resources=resources)

@resource_bp.route('/<int:resource_id>')
def view_resource(resource_id):
    # Eager load the favorited_by relationship to get updated favorite status
    resource = Resource.query.options(
        joinedload(Resource.favorited_by)
    ).get_or_404(resource_id)
    
    # Get availability for next 30 days
    bookings = Booking.query.filter(
        Booking.resource_id == resource_id,
        Booking.status != 'cancelled'
    ).all()
    
    return render_template('resources/detail.html', resource=resource, bookings=bookings)

@resource_bp.route('/<int:resource_id>/availability')
def check_availability(resource_id):
    """AJAX endpoint to check resource availability"""
    resource = Resource.query.get_or_404(resource_id)
    booking_date = request.args.get('date', '')
    
    if not booking_date:
        return jsonify({'error': 'Date required'}), 400
    
    try:
        booking_date = datetime.strptime(booking_date, '%Y-%m-%d').date()
    except ValueError:
        return jsonify({'error': 'Invalid date format'}), 400
    
    # Get all bookings for this date
    bookings = Booking.query.filter(
        Booking.resource_id == resource_id,
        Booking.booking_date == booking_date,
        Booking.status != 'cancelled'
    ).all()
    
    booked_slots = [
        {
            'start': b.start_time.strftime('%H:%M'),
            'end': b.end_time.strftime('%H:%M')
        }
        for b in bookings
    ]
    
    return jsonify({
        'available': len(bookings) == 0,
        'booked_slots': booked_slots,
        'resource': {
            'id': resource.id,
            'name': resource.name,
            'availability_start': resource.availability_start.strftime('%H:%M'),
            'availability_end': resource.availability_end.strftime('%H:%M')
        }
    })

@resource_bp.route('/api/by-type/<resource_type>')
def get_resources_by_type(resource_type):
    """API endpoint to get resources by type"""
    resources = Resource.query.filter_by(
        resource_type=resource_type,
        is_available=True
    ).all()
    
    return jsonify([
        {
            'id': r.id,
            'name': r.name,
            'capacity': r.capacity,
            'location': r.location
        }
        for r in resources
    ])
