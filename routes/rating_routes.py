

from flask import Blueprint, jsonify, request, redirect, url_for, flash
from flask_login import login_required, current_user
from models import db, ResourceReview, Booking, Resource
from datetime import datetime
import logging

logger = logging.getLogger(__name__)

rating_bp = Blueprint('rating', __name__, url_prefix='/ratings')


@rating_bp.route('/submit/<int:booking_id>', methods=['POST'])
@login_required
def submit_rating(booking_id):
    """Submit a one-time rating (1-5 stars) for a completed booking"""
    # Determine redirect target (supports admin bookings page via 'next' field)
    redirect_url = request.form.get('next', '')
    if not redirect_url:
        redirect_url = url_for('booking.dashboard')
        
    is_ajax = request.headers.get('X-Requested-With') == 'XMLHttpRequest' or 'application/json' in request.headers.get('Accept', '')

    try:
        booking = Booking.query.get_or_404(booking_id)

        # Validate ownership
        if booking.user_id != current_user.id:
            if is_ajax:
                return jsonify({'success': False, 'message': 'You can only rate your own bookings.'}), 403
            flash('You can only rate your own bookings.', 'error')
            return redirect(redirect_url)

        # Validate status
        if booking.status != 'completed':
            if is_ajax:
                return jsonify({'success': False, 'message': 'You can only rate completed bookings.'}), 400
            flash('You can only rate completed bookings.', 'error')
            return redirect(redirect_url)

        # Parse rating value
        rating_value = request.form.get('rating', type=int)
        comment = request.form.get('comment', '').strip()

        if not rating_value or rating_value < 1 or rating_value > 5:
            if is_ajax:
                return jsonify({'success': False, 'message': 'Please select a rating between 1 and 5 stars.'}), 400
            flash('Please select a rating between 1 and 5 stars.', 'error')
            return redirect(url_for('booking.view_booking', booking_id=booking_id))

        # Check if already rated — if so, update instead of creating new
        existing_review = ResourceReview.query.filter_by(
            user_id=current_user.id,
            booking_id=booking_id
        ).first()

        if existing_review:
            # Update existing review
            existing_review.rating = rating_value
            existing_review.comment = comment if comment else None
            review = existing_review
            is_update = True
        else:
            # Create new review
            review = ResourceReview(
                user_id=current_user.id,
                resource_id=booking.resource_id,
                booking_id=booking.id,
                rating=rating_value,
                comment=comment if comment else None
            )
            db.session.add(review)
            is_update = False

        db.session.commit()

        action = "updated" if is_update else "rated"
        logger.info(f"User {current_user.id} {action} resource {booking.resource_id} "
                     f"({rating_value} stars) via booking {booking_id}")

        msg = 'Thank you, your rating has been successfully updated.' if is_update else 'Thank you, your rating has been successfully submitted.'
        
        if is_ajax:
            return jsonify({
                'success': True,
                'message': msg,
                'rating': rating_value,
                'is_update': is_update,
                'booking_id': booking_id
            })

        flash(msg, 'success')
        return redirect(redirect_url)

    except Exception as e:
        logger.error(f"Error submitting rating: {e}")
        db.session.rollback()
        if is_ajax:
            return jsonify({'success': False, 'message': 'Failed to submit rating. Please try again.'}), 500
        flash('Failed to submit rating. Please try again.', 'error')
        return redirect(redirect_url)


@rating_bp.route('/check/<int:booking_id>')
@login_required
def check_rating(booking_id):
    """Check if a booking has already been rated (AJAX endpoint)"""
    try:
        review = ResourceReview.query.filter_by(
            user_id=current_user.id,
            booking_id=booking_id
        ).first()

        if review:
            return jsonify({
                'is_rated': True,
                'rating': review.rating,
                'comment': review.comment
            })

        return jsonify({'is_rated': False})

    except Exception as e:
        logger.error(f"Error checking rating: {e}")
        return jsonify({'is_rated': False}), 500


@rating_bp.route('/resource/<int:resource_id>')
def resource_ratings(resource_id):
    """Get average rating and reviews for a resource (public JSON endpoint)"""
    try:
        reviews = ResourceReview.query.filter_by(resource_id=resource_id).all()

        if not reviews:
            return jsonify({
                'average_rating': 0,
                'total_reviews': 0,
                'reviews': []
            })

        avg_rating = sum(r.rating for r in reviews) / len(reviews)

        review_list = [{
            'rating': r.rating,
            'comment': r.comment,
            'created_at': r.created_at.strftime('%Y-%m-%d %H:%M') if r.created_at else None
        } for r in reviews]

        return jsonify({
            'average_rating': round(avg_rating, 1),
            'total_reviews': len(reviews),
            'reviews': review_list
        })

    except Exception as e:
        logger.error(f"Error fetching resource ratings: {e}")
        return jsonify({'average_rating': 0, 'total_reviews': 0, 'reviews': []}), 500
