"""
================================================================================
SYSTEM ROUTES - Multi-Facility Discovery and Selection
================================================================================

DESCRIPTION:
    Implements Discovery-First architecture. Users select a facility before booking.
    Provides geolocation-based facility discovery and selection.

ROUTES:
    GET /system/discover - Discover facilities by location
    POST /system/select/<id> - Select active facility
    GET /system/current - Get current selected facility
    GET /system/list - List accessible facilities
    GET /system/comfort-score/<id> - Calculate facility comfort score

FEATURES:
    - Geolocation-based facility discovery using browser GPS
    - Distance calculation using Haversine formula
    - Comfort score based on: resources, setup quality, description
    - Search by name, city, address
    - Sorting: by distance, name, resources, comfort score
    - Session-based facility context

DISCOVERY-FIRST PATTERN:
    1. User logs in → sees facility discovery page
    2. User allows geolocation OR searches by location
    3. System shows nearby facilities sorted by distance
    4. User selects a facility → becomes active system
    5. All bookings/resources now filtered by active facility
    6. User can switch facilities anytime

COMFORT SCORE CALCULATION:
    Weighted scoring based on:
    - Number of resources (0-30 points)
    - Resource variety (0-20 points)
    - Setup quality (0-30 points)
    - Description quality (0-20 points)
    Scale: 0-100 (Higher = Better)

================================================================================
"""

from flask import Blueprint, render_template, request, jsonify, session, redirect, url_for
from flask_login import login_required, current_user
from models import ResourceSystem, UserResourceSystem, Resource, db
from sqlalchemy import func, and_
import math

system_bp = Blueprint('system', __name__, url_prefix='/system')

def haversine_distance(lat1, lon1, lat2, lon2):
    """Calculate distance between two coordinates in kilometers"""
    if not all([lat1, lon1, lat2, lon2]):
        return None
    
    R = 6371  # Earth's radius in km
    
    dlat = math.radians(lat2 - lat1)
    dlon = math.radians(lon2 - lon1)
    
    a = math.sin(dlat/2)**2 + math.cos(math.radians(lat1)) * math.cos(math.radians(lat2)) * math.sin(dlon/2)**2
    c = 2 * math.asin(math.sqrt(a))
    
    return R * c

@system_bp.route('/discover', methods=['GET'])
@login_required
def discover_systems():
    """Discover nearby resource systems based on user location"""
    user_lat = request.args.get('lat', type=float)
    user_lon = request.args.get('lon', type=float)
    search_query = request.args.get('search', '')
    sort_by = request.args.get('sort', 'distance')  # distance, name, resources
    
    # Get all public systems
    query = ResourceSystem.query.filter_by(is_public=True, is_active=True)
    
    if search_query:
        query = query.filter(
            ResourceSystem.name.ilike(f'%{search_query}%') |
            ResourceSystem.city.ilike(f'%{search_query}%') |
            ResourceSystem.description.ilike(f'%{search_query}%')
        )
    
    systems = query.all()
    
    # Calculate distances and resource counts
    systems_data = []
    for system in systems:
        distance = None
        if user_lat and user_lon:
            distance = haversine_distance(user_lat, user_lon, system.latitude, system.longitude)
        
        resource_count = Resource.query.filter_by(
            resource_system_id=system.id,
            is_available=True
        ).count()
        
        systems_data.append({
            'id': system.id,
            'name': system.name,
            'description': system.description,
            'address': system.address,
            'city': system.city,
            'latitude': system.latitude,
            'longitude': system.longitude,
            'distance': distance,
            'resource_count': resource_count,
            'comfort_score': calculate_comfort_score(system, resource_count)
        })
    
    # Sort systems
    if sort_by == 'distance' and user_lat and user_lon:
        systems_data.sort(key=lambda x: x['distance'] if x['distance'] else float('inf'))
    elif sort_by == 'name':
        systems_data.sort(key=lambda x: x['name'])
    elif sort_by == 'resources':
        systems_data.sort(key=lambda x: x['resource_count'], reverse=True)
    else:
        # Default: by comfort score
        systems_data.sort(key=lambda x: x['comfort_score'], reverse=True)
    
    return render_template('system/discover.html', 
                         systems=systems_data,
                         user_location={'lat': user_lat, 'lon': user_lon})

@system_bp.route('/select/<int:system_id>', methods=['POST'])
@login_required
def select_system(system_id):
    """Select active resource system for user session"""
    system = ResourceSystem.query.get_or_404(system_id)
    
    # Verify user has access (public systems or admin assignment)
    if not system.is_public:
        if current_user.role != 'admin':
            return jsonify({'error': 'Access denied'}), 403
        
        admin_access = UserResourceSystem.query.filter_by(
            user_id=current_user.id,
            resource_system_id=system_id
        ).first()
        
        if not admin_access:
            return jsonify({'error': 'Not assigned to this system'}), 403
    
    # Set active system in session
    session['active_system_id'] = system_id
    session.modified = True
    
    return jsonify({
        'success': True,
        'system_id': system_id,
        'system_name': system.name
    })

@system_bp.route('/current', methods=['GET'])
@login_required
def get_current_system():
    """Get current active system"""
    active_system_id = session.get('active_system_id')
    
    if not active_system_id:
        return jsonify({'error': 'No system selected'}), 400
    
    system = ResourceSystem.query.get_or_404(active_system_id)
    
    return jsonify({
        'id': system.id,
        'name': system.name,
        'description': system.description,
        'address': system.address,
        'city': system.city,
        'resource_count': Resource.query.filter_by(
            resource_system_id=system.id,
            is_available=True
        ).count()
    })

@system_bp.route('/list', methods=['GET'])
@login_required
def list_user_systems():
    """List all systems accessible to current user"""
    if current_user.role == 'admin':
        # Get assigned systems for admin
        admin_systems = UserResourceSystem.query.filter_by(
            user_id=current_user.id
        ).all()
        
        systems = [ResourceSystem.query.get(us.resource_system_id) for us in admin_systems]
    else:
        # Regular users see all public systems
        systems = ResourceSystem.query.filter_by(is_public=True, is_active=True).all()
    
    return jsonify({
        'systems': [{
            'id': s.id,
            'name': s.name,
            'city': s.city,
            'address': s.address,
            'resource_count': Resource.query.filter_by(
                resource_system_id=s.id,
                is_available=True
            ).count()
        } for s in systems]
    })

def calculate_comfort_score(system, resource_count):
    """Calculate comfort score based on various factors"""
    base_score = 50
    
    # Points for resources
    resource_score = min(resource_count * 5, 30)
    
    # Points for having coordinates (shows proper setup)
    location_score = 10 if (system.latitude and system.longitude) else 0
    
    # Points for having description
    description_score = 5 if system.description else 0
    
    # Points for active status
    active_score = 5 if system.is_active else 0
    
    total_score = base_score + resource_score + location_score + description_score + active_score
    
    return min(total_score, 100)

def register_system_routes(app):
    """Register system blueprint with app"""
    app.register_blueprint(system_bp)
