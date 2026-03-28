

from flask import Blueprint, render_template, request, jsonify, redirect, url_for, flash, session
from flask_login import login_required, current_user
from models import db, Booking, Resource, BookingHistory, User, ResourceSystem, UserFavorite, SystemAnnouncement, ResourceReview
from datetime import datetime, date, time, timedelta, timezone
from decimal import Decimal
from ai.ai_module import AIModule
import logging

# IST timezone (UTC+5:30) - used for accurate time comparisons on deployed server
IST = timezone(timedelta(hours=5, minutes=30))

logger = logging.getLogger(__name__)

booking_bp = Blueprint('booking', __name__, url_prefix='/bookings')
ai_module = AIModule()

def calculate_cost(resource, booking_type, start_time, end_time, num_days=1):
    """Calculate booking cost"""
    if booking_type == 'hourly':
        hours = (datetime.combine(date.today(), end_time) - 
                datetime.combine(date.today(), start_time)).total_seconds() / 3600
        return resource.hourly_rate * hours
    elif booking_type == 'daily':
        return resource.daily_rate * num_days
    elif booking_type == 'monthly':
        return resource.monthly_rate
    return 0.0

def mark_expired_bookings_as_completed():
    """
    Auto-update any confirmed bookings that have passed their date/time to 'completed' status.
    Called before fetching bookings to ensure accurate status display.
    """
    now = datetime.now(IST)
    
    # Find all confirmed bookings where the end date+time has passed
    expired_bookings = Booking.query.filter(
        Booking.status == 'confirmed',
        Booking.booking_date < now.date()  # Entire day has passed
    ).all()
    
    # Also check bookings for today that have passed their end time
    expired_today = Booking.query.filter(
        Booking.status == 'confirmed',
        Booking.booking_date == now.date()
    ).all()
    
    # Use naive version of IST 'now' for comparisons with naive booking times
    now_naive = now.replace(tzinfo=None)
    
    for booking in expired_today:
        # Create end datetime from booking_date + end_time
        booking_end = datetime.combine(booking.booking_date, booking.end_time)
        if booking_end <= now_naive:
            expired_bookings.append(booking)
    
    # Update all expired bookings to 'completed'
    for booking in expired_bookings:
        if booking.status == 'confirmed':
            booking.status = 'completed'
            db.session.add(booking)
            print(f"[v0] Auto-marked booking {booking.id} as completed (was {booking.booking_date} {booking.end_time})")
    
    if expired_bookings:
        db.session.commit()
        print(f"[v0] Updated {len(expired_bookings)} expired bookings to 'completed' status")
    
    return len(expired_bookings)

def check_booking_conflict(resource_id, booking_date, start_time, end_time, duration_days):
    """
    Check if a resource is already booked during the requested time slot.
    Returns (has_conflict, conflicting_booking_info)
    """
    for day_offset in range(duration_days):
        check_date = booking_date + timedelta(days=day_offset)
        
        # Query for any confirmed bookings on this resource for this date
        conflicts = Booking.query.filter(
            Booking.resource_id == resource_id,
            Booking.booking_date == check_date,
            Booking.status == 'confirmed'
        ).all()
        
        for existing_booking in conflicts:
            # Check if times overlap
            if not (end_time <= existing_booking.start_time or start_time >= existing_booking.end_time):
                return True, existing_booking
    
    return False, None

def format_booking_time(booking):
    """Format booking info for display"""
    return f"{booking.booking_date} {booking.start_time} - {booking.end_time}"

@booking_bp.route('/dashboard')
@login_required
def dashboard():
    # Auto-update expired bookings to 'completed' status
    mark_expired_bookings_as_completed()
    
    page = request.args.get('page', 1, type=int)
    status = request.args.get('status', 'all')
    
    # Get active system
    active_system_id = session.get('active_system_id')
    active_system = None
    
    if active_system_id:
        active_system = ResourceSystem.query.get(active_system_id)
    
    if not active_system:
        # Redirect to system discovery if no system selected
        return redirect(url_for('system.discover_systems'))
    
    # Filter bookings by active system and user
    query = Booking.query.filter_by(
        user_id=current_user.id,
        resource_system_id=active_system_id
    )
    
    if status != 'all':
        query = query.filter_by(status=status)
    
    bookings = query.order_by(Booking.booking_date.desc()).paginate(page=page, per_page=10)
    
    # Fetch which bookings the user has already rated
    rated_booking_ids = set()
    user_ratings = {}  # booking_id -> rating value
    if bookings.items:
        booking_ids = [b.id for b in bookings.items]
        reviews = ResourceReview.query.filter(
            ResourceReview.user_id == current_user.id,
            ResourceReview.booking_id.in_(booking_ids)
        ).all()
        for review in reviews:
            rated_booking_ids.add(review.booking_id)
            user_ratings[review.booking_id] = review.rating
    
    suggestions = ai_module.get_smart_suggestions(current_user.id, active_system_id)
    
    total_spent_raw = db.session.query(db.func.sum(Booking.cost)).filter(
        Booking.user_id == current_user.id,
        Booking.resource_system_id == active_system_id,
        Booking.status.in_(['confirmed', 'completed'])
    ).scalar() or 0
    
    stats = {
        'total_bookings': Booking.query.filter_by(
            user_id=current_user.id,
            resource_system_id=active_system_id
        ).count(),
        'confirmed': Booking.query.filter(
            Booking.user_id == current_user.id,
            Booking.resource_system_id == active_system_id,
            Booking.status.in_(['confirmed', 'completed'])
        ).count(),
        'pending': Booking.query.filter_by(
            user_id=current_user.id,
            resource_system_id=active_system_id,
            status='pending'
        ).count(),
        'total_spent': round(float(total_spent_raw), 3)
    }
    
    return render_template('bookings/dashboard.html', 
                         bookings=bookings, 
                         stats=stats, 
                         suggestions=suggestions,
                         active_system=active_system,
                         rated_booking_ids=rated_booking_ids,
                         user_ratings=user_ratings)

@booking_bp.route('/create', methods=['GET', 'POST'])
@login_required
def create_booking():
    if request.method == 'POST':
        resource_id = request.form.get('resource_id', type=int)
        booking_date_str = request.form.get('booking_date', '')
        duration_days = request.form.get('duration_days', 1, type=int)
        start_time_str = request.form.get('start_time', '')
        end_time_str = request.form.get('end_time', '')
        purpose = request.form.get('purpose', '')
        
        if not resource_id or not booking_date_str or not start_time_str or not end_time_str:
            flash('Please fill in all required fields', 'error')
            return redirect(url_for('booking.create_booking'))
        
        resource = Resource.query.get_or_404(resource_id)
        
        try:
            booking_date = datetime.strptime(booking_date_str, '%Y-%m-%d').date()
            start_time = datetime.strptime(start_time_str, '%H:%M').time()
            end_time = datetime.strptime(end_time_str, '%H:%M').time()
        except ValueError:
            flash('Invalid date or time format', 'error')
            return redirect(url_for('booking.create_booking'))
        
        if booking_date < date.today():
            flash('Cannot book in the past', 'error')
            return redirect(url_for('booking.create_booking'))
        
        if start_time >= end_time:
            flash('End time must be after start time', 'error')
            return redirect(url_for('booking.create_booking'))
        
        if duration_days < 1 or duration_days > 365:
            flash('Duration must be between 1 and 365 days', 'error')
            return redirect(url_for('booking.create_booking'))
        
        # Calculate cost based on hours per day × number of days
        hours_per_day = (datetime.combine(date.today(), end_time) - 
                        datetime.combine(date.today(), start_time)).total_seconds() / 3600
        total_hours = hours_per_day * duration_days
        cost = resource.hourly_rate * total_hours
        
        # Get active system
        active_system_id = session.get('active_system_id')
        if not active_system_id:
            flash('No resource system selected', 'error')
            return redirect(url_for('system.discover_systems'))
        
        # Verify resource belongs to active system
        if resource.resource_system_id != active_system_id:
            flash('Resource does not belong to selected system', 'error')
            return redirect(url_for('booking.create_booking'))
        
        # Check for booking conflicts
        has_conflict, conflicting_booking = check_booking_conflict(
            resource_id, booking_date, start_time, end_time, duration_days
        )
        
        if has_conflict:
            conflict_info = format_booking_time(conflicting_booking)
            flash(f'This resource is already booked during the requested time: {conflict_info}', 'error')
            return redirect(url_for('booking.create_booking'))
        
        # Create booking with auto-approval (status = 'confirmed' instead of 'pending')
        booking = Booking(
            user_id=current_user.id,
            resource_system_id=active_system_id,
            resource_id=resource_id,
            booking_date=booking_date,
            start_time=start_time,
            end_time=end_time,
            duration_days=duration_days,
            purpose=purpose,
            booking_type='hourly',
            cost=cost,
            status='confirmed'  # AUTO-APPROVED
        )
        
        try:
            db.session.add(booking)
            db.session.commit()
            
            history = BookingHistory(
                user_id=current_user.id,
                resource_id=resource_id,
                booking_date=booking_date,
                start_time=start_time,
                end_time=end_time,
                action='created'
            )
            db.session.add(history)
            db.session.commit()
            
            flash(f'Booking confirmed successfully for {duration_days} day(s)!', 'success')
            return redirect(url_for('booking.dashboard'))
        except Exception as e:
            db.session.rollback()
            flash(f'Booking creation failed: {str(e)}', 'error')
            return redirect(url_for('booking.create_booking'))
    
    resource_id = request.args.get('resource_id', type=int)
    selected_resource = None
    if resource_id:
        selected_resource = Resource.query.get(resource_id)
    
    nlp_date = request.args.get('date', '')
    nlp_start_time = request.args.get('start_time', '')
    nlp_end_time = request.args.get('end_time', '')
    nlp_duration_days = request.args.get('duration_days', type=int)
    nlp_purpose = request.args.get('purpose', '')
    
    if not nlp_duration_days:
        nlp_duration_days = 1
    
    # Prepare pre-filled values
    prefill_data = {
        'date': nlp_date if nlp_date else '',
        'start_time': nlp_start_time if nlp_start_time else '',
        'end_time': nlp_end_time if nlp_end_time else '',
        'duration_days': nlp_duration_days,
        'purpose': nlp_purpose if nlp_purpose else ''
    }
    
    resources = Resource.query.filter_by(is_available=True).all()
    return render_template('bookings/create.html', 
                         resources=resources,
                         selected_resource=selected_resource,
                         prefill=prefill_data)

@booking_bp.route('/<int:booking_id>/cancel', methods=['POST'])
@login_required
def cancel_booking(booking_id):
    booking = Booking.query.get_or_404(booking_id)
    
    if booking.user_id != current_user.id and current_user.role != 'admin':
        flash('Unauthorized', 'error')
        return redirect(url_for('booking.dashboard'))
    
    if booking.status == 'cancelled':
        flash('Booking already cancelled', 'warning')
        return redirect(url_for('booking.dashboard'))
    
    if booking.status == 'confirmed' and current_user.role != 'admin':
        # User is requesting cancellation for a confirmed booking
        if booking.cancellation_requested:
            flash('Cancellation request already submitted. Waiting for admin approval.', 'info')
            return redirect(url_for('booking.dashboard'))
        
        booking.cancellation_requested = True
        booking.cancellation_reason = request.form.get('reason', 'User requested cancellation')
        booking.cancellation_requested_at = datetime.utcnow()
        
        try:
            db.session.commit()
            flash('Cancellation request submitted successfully. An admin will review it shortly.', 'success')
        except Exception as e:
            db.session.rollback()
            flash('Failed to submit cancellation request', 'error')
        
        return redirect(url_for('booking.dashboard'))
    
    booking.status = 'cancelled'
    db.session.commit()
    
    # Add to history
    history = BookingHistory(
        user_id=current_user.id,
        resource_id=booking.resource_id,
        booking_date=booking.booking_date,
        start_time=booking.start_time,
        end_time=booking.end_time,
        action='cancelled'
    )
    db.session.add(history)
    db.session.commit()
    
    flash('Booking cancelled successfully', 'success')
    return redirect(url_for('booking.dashboard'))

@booking_bp.route('/<int:booking_id>')
@login_required
def view_booking(booking_id):
    booking = Booking.query.get_or_404(booking_id)
    
    if booking.user_id != current_user.id and current_user.role != 'admin':
        flash('Unauthorized', 'error')
        return redirect(url_for('booking.dashboard'))
    
    # Check for existing review on this booking
    existing_review = None
    if booking.status == 'completed':
        existing_review = ResourceReview.query.filter_by(
            user_id=current_user.id,
            booking_id=booking_id
        ).first()
    
    return render_template('bookings/detail.html', booking=booking, existing_review=existing_review)

@booking_bp.route('/search', methods=['GET', 'POST'])
@login_required
def search():
    """Handle natural language search with traditional form submission"""
    if request.method == 'POST':
        search_query = request.form.get('search_query', '').strip()
        
        if not search_query:
            flash('Please enter a search query', 'warning')
            return redirect(url_for('booking.dashboard'))
        
        try:
            print(f"\n[v0] ===== NLP SEARCH DEBUG =====")
            print(f"[v0] Original query: {search_query}")
            
            # Safely parse with error handling
            try:
                booking_params = ai_module.parse_nlp_booking(search_query)
            except Exception as e:
                print(f"[v0] Error parsing: {e}")
                booking_params = {}
            
            # Ensure booking_params is a dict
            if not booking_params or not isinstance(booking_params, dict):
                booking_params = {}
            
            print(f"[v0] Extracted parameters:")
            print(f"  - Date: {booking_params.get('date')}")
            print(f"  - Time: {booking_params.get('start_time')}")
            print(f"  - Duration: {booking_params.get('duration')}")
            print(f"  - Participants: {booking_params.get('participants')}")
            print(f"  - Resource Type: {booking_params.get('resource_type')}")
            print(f"[v0] =============================\n")
            
            all_resources = Resource.query.filter_by(is_available=True).all()
            
            if not all_resources:
                flash('No available resources at the moment', 'warning')
                return redirect(url_for('booking.dashboard'))
            
            def score_resources(resources_list, booking_params, enforce_type=True):
                """Score resources based on booking params. If enforce_type is False, skip type filtering."""
                scored = []
                resource_type = booking_params.get('resource_type')
                participants = booking_params.get('participants')
                
                # Pre-fetch average ratings for all resources in one query
                from sqlalchemy import func
                rating_data = db.session.query(
                    ResourceReview.resource_id,
                    func.avg(ResourceReview.rating).label('avg_rating'),
                    func.count(ResourceReview.id).label('review_count')
                ).group_by(ResourceReview.resource_id).all()
                rating_map = {r.resource_id: {'avg': float(r.avg_rating), 'count': r.review_count} for r in rating_data}
                
                for resource in resources_list:
                    is_suitable = True
                    match_reasons = []
                    match_score = 0.0
                    is_perfect_match = False
                    
                    # Check participants/capacity - out of 80 points
                    if participants:
                        required_capacity = int(participants)
                        if resource.capacity >= required_capacity:
                            capacity_ratio = resource.capacity / required_capacity
                            
                            if 1.0 <= capacity_ratio <= 1.1:
                                match_score += 80
                                match_reasons.append(f"Perfect capacity match: {resource.capacity} people")
                                is_perfect_match = True
                            elif capacity_ratio <= 1.5:
                                match_score += 55
                                match_reasons.append(f"Excellent fit: {resource.capacity} people")
                            elif capacity_ratio <= 3.5:
                                match_score += 30
                                match_reasons.append(f"Can accommodate: {resource.capacity} people")
                            else:
                                match_score += 8
                                match_reasons.append(f"Has capacity: {resource.capacity} people")
                        else:
                            is_suitable = False
                    else:
                        match_score += 25
                    
                    # Check resource type - out of 40 points
                    if resource_type and is_suitable:
                        resource_type_lower = resource_type.lower().strip()
                        resource_actual_type = resource.resource_type.lower().strip() if resource.resource_type else ""
                        
                        if resource_type_lower == resource_actual_type or resource_type_lower in resource_actual_type or resource_actual_type in resource_type_lower:
                            match_score += 40
                            match_reasons.append(f"Matches type: {resource_type}")
                        else:
                            if enforce_type:
                                is_suitable = False
                                match_score = 0
                            else:
                                # Fallback mode: don't exclude, but give lower type score
                                match_score += 8
                                match_reasons.append(f"Different type ({resource.resource_type}), but fits your capacity needs")
                    else:
                        match_score += 20
                    
                    # Price competitiveness - out of 25 points
                    if is_suitable:
                        if resource.hourly_rate:
                            price_normalized = min(resource.hourly_rate / 300.0, 1.0)
                            price_score = 25 * (1.0 - price_normalized)
                            match_score += price_score
                        else:
                            match_score += 12
                        
                        # Availability bonus - out of 25 points
                        if resource.is_available:
                            match_score += 25
                        else:
                            match_score += 5
                    
                    # User rating bonus - out of 30 points
                    resource_rating = rating_map.get(resource.id)
                    avg_rating = 0
                    review_count = 0
                    if is_suitable:
                        if resource_rating:
                            avg_rating = resource_rating['avg']
                            review_count = resource_rating['count']
                            rating_score = (avg_rating / 5.0) * 30
                            match_score += rating_score
                            match_reasons.append(f"User rating: {avg_rating:.1f}/5 ({review_count} review{'s' if review_count != 1 else ''})")
                        else:
                            # Unrated resources get a neutral score
                            match_score += 15
                            avg_rating = 0
                            review_count = 0
                    
                    match_score = max(0, min(200, match_score))
                    
                    if is_suitable and match_score > 0:
                        scored.append({
                            'resource': resource,
                            'relevance_score': match_score,
                            'match_reasons': match_reasons,
                            'is_best_match': is_perfect_match,
                            'match_type': 'BEST RESULT' if is_perfect_match else 'MOST RELEVANT',
                            'avg_rating': round(avg_rating, 1),
                            'review_count': review_count
                        })
                
                return scored
            
            # First pass: search with type enforcement
            suitable_resources = score_resources(all_resources, booking_params, enforce_type=True)
            fallback_active = False
            
            # Fallback: if no results and a resource_type was requested, retry without type filter
            resource_type = booking_params.get('resource_type')
            participants = booking_params.get('participants')
            if not suitable_resources and resource_type and participants:
                print(f"[v0] No '{resource_type}' resources found for {participants} people — falling back to capacity-only search")
                suitable_resources = score_resources(all_resources, booking_params, enforce_type=False)
                if suitable_resources:
                    fallback_active = True
                    print(f"[v0] Fallback found {len(suitable_resources)} alternative resources")
            
            # Sort by: Perfect matches first (by score), then all others (by score)
            perfect_results = [r for r in suitable_resources if r['is_best_match']]
            other_results = [r for r in suitable_resources if not r['is_best_match']]
            perfect_results.sort(key=lambda x: x['relevance_score'], reverse=True)
            other_results.sort(key=lambda x: x['relevance_score'], reverse=True)
            
            # Cap best results at 5
            perfect_results = perfect_results[:5]
            
            suitable_resources = perfect_results + other_results
            
            print(f"[v0] Found {len(perfect_results)} BEST matches (capped at 5) and {len(other_results)} MOST RELEVANT matches")
            
            return render_template(
                'bookings/search_results.html',
                resources=suitable_resources[:20],
                search_query=search_query,
                booking_params=booking_params,
                fallback_active=fallback_active
            )
            
        except Exception as e:
            print(f"[v0] Search error: {str(e)}")
            flash(f'Search error: {str(e)}', 'error')
            return redirect(url_for('booking.dashboard'))
    
    return redirect(url_for('booking.dashboard'))