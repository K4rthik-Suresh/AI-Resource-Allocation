

from flask import Blueprint, jsonify, request, redirect, url_for, flash
from flask_login import login_required, current_user
from models import db, ResourceReview, Booking, Resource
from datetime import datetime
import logging

logger = logging.getLogger(__name__)

rating_bp = Blueprint('rating', __name__, url_prefix='/ratings')


def _is_ajax():
    """Detect AJAX / fetch() requests."""
    return (
        request.headers.get('X-Requested-With') == 'XMLHttpRequest'
        or request.headers.get('Accept', '').startswith('application/json')
        or request.headers.get('Content-Type', '') == 'application/json'
    )


@rating_bp.route('/submit/<int:booking_id>', methods=['POST'])
@login_required
def submit_rating(booking_id):
    """Submit or update a star rating for a completed booking.
    
    Supports both:
    - AJAX (fetch): returns JSON { success, rating, comment, is_update }
    - HTML form POST: redirects with flash message (backward-compatible)
    """
    ajax = _is_ajax()

    # Determine redirect target for non-AJAX fallback
    redirect_url = request.form.get('next', '') or url_for('booking.dashboard')

    try:
        booking = Booking.query.get_or_404(booking_id)

        # Validate ownership
        if booking.user_id != current_user.id:
            msg = 'You can only rate your own bookings.'
            if ajax:
                return jsonify({'success': False, 'error': msg}), 403
            flash(msg, 'error')
            return redirect(redirect_url)

        # Validate status
        if booking.status != 'completed':
            msg = 'You can only rate completed bookings.'
            if ajax:
                return jsonify({'success': False, 'error': msg}), 400
            flash(msg, 'error')
            return redirect(redirect_url)

        # Parse values
        rating_value = request.form.get('rating', type=int)
        comment = request.form.get('comment', '').strip() or None

        if not rating_value or not (1 <= rating_value <= 5):
            msg = 'Please select a rating between 1 and 5 stars.'
            if ajax:
                return jsonify({'success': False, 'error': msg}), 400
            flash(msg, 'error')
            return redirect(redirect_url)

        # Upsert review
        existing = ResourceReview.query.filter_by(
            user_id=current_user.id,
            booking_id=booking_id
        ).first()

        if existing:
            existing.rating = rating_value
            existing.comment = comment
            is_update = True
        else:
            review = ResourceReview(
                user_id=current_user.id,
                resource_id=booking.resource_id,
                booking_id=booking.id,
                rating=rating_value,
                comment=comment
            )
            db.session.add(review)
            is_update = False

        db.session.commit()

        logger.info(
            f"User {current_user.id} {'updated' if is_update else 'submitted'} "
            f"rating {rating_value}★ for resource {booking.resource_id} "
            f"(booking {booking_id})"
        )

        if ajax:
            return jsonify({
                'success': True,
                'rating': rating_value,
                'comment': comment,
                'is_update': is_update,
                'resource_name': booking.resource.name
            })

        action = "updated" if is_update else "submitted"
        flash(
            f'Rating {action}! You rated {booking.resource.name} '
            f'{rating_value} star{"s" if rating_value != 1 else ""}.',
            'success'
        )
        return redirect(redirect_url)

    except Exception as e:
        logger.error(f"Error submitting rating for booking {booking_id}: {e}", exc_info=True)
        db.session.rollback()
        if ajax:
            return jsonify({'success': False, 'error': 'Failed to save rating. Please try again.'}), 500
        flash('Failed to submit rating. Please try again.', 'error')
        return redirect(redirect_url)


@rating_bp.route('/get/<int:booking_id>')
@login_required
def get_rating(booking_id):
    """Return the current user's existing rating for a booking (for pre-populating the edit modal)."""
    try:
        booking = Booking.query.get_or_404(booking_id)

        if booking.user_id != current_user.id:
            return jsonify({'error': 'Unauthorized'}), 403

        review = ResourceReview.query.filter_by(
            user_id=current_user.id,
            booking_id=booking_id
        ).first()

        if review:
            return jsonify({
                'is_rated': True,
                'rating': review.rating,
                'comment': review.comment or ''
            })

        return jsonify({'is_rated': False, 'rating': 0, 'comment': ''})

    except Exception as e:
        logger.error(f"Error fetching rating for booking {booking_id}: {e}")
        return jsonify({'is_rated': False, 'rating': 0, 'comment': ''}), 500


@rating_bp.route('/check/<int:booking_id>')
@login_required
def check_rating(booking_id):
    """Check if a booking has already been rated (legacy AJAX endpoint, kept for compatibility)."""
    try:
        review = ResourceReview.query.filter_by(
            user_id=current_user.id,
            booking_id=booking_id
        ).first()

        if review:
            return jsonify({'is_rated': True, 'rating': review.rating, 'comment': review.comment})
        return jsonify({'is_rated': False})

    except Exception as e:
        logger.error(f"Error checking rating: {e}")
        return jsonify({'is_rated': False}), 500


@rating_bp.route('/resource/<int:resource_id>')
def resource_ratings(resource_id):
    """Get average rating and reviews for a resource (public JSON endpoint)."""
    try:
        reviews = ResourceReview.query.filter_by(resource_id=resource_id).all()

        if not reviews:
            return jsonify({'average_rating': 0, 'total_reviews': 0, 'reviews': []})

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
