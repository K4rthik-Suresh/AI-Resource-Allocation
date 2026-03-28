

from flask import Blueprint, jsonify, render_template, redirect, url_for, flash, request
from flask_login import login_required, current_user
from models import db, UserFavorite, Resource
import logging

logger = logging.getLogger(__name__)

# Create favorites blueprint (can be registered in main app)
favorites_bp = Blueprint('favorites', __name__, url_prefix='/bookings/favorites')


@favorites_bp.route('/toggle/<int:resource_id>', methods=['POST'])
@login_required
def toggle_favorite(resource_id):
    """Add or remove resource from user's favorites"""
    try:
        resource = Resource.query.get(resource_id)
        if not resource:
            # Check if this is an AJAX request
            if request.headers.get('X-Requested-With') == 'XMLHttpRequest':
                return jsonify({'success': False, 'error': 'Resource not found'}), 404
            flash("Resource not found", "error")
            return redirect(url_for('booking.dashboard'))
        
        # Check if already favorited
        existing = UserFavorite.query.filter_by(
            user_id=current_user.id,
            resource_id=resource_id
        ).first()
        
        if existing:
            # Remove from favorites
            db.session.delete(existing)
            is_favorite = False
            message = f"Removed {resource.name} from favorites"
        else:
            # Add to favorites
            new_favorite = UserFavorite(
                user_id=current_user.id,
                resource_id=resource_id
            )
            db.session.add(new_favorite)
            is_favorite = True
            message = f"Added {resource.name} to favorites"
        
        db.session.commit()
        logger.info(f"User {current_user.id} {'favorited' if is_favorite else 'unfavorited'} resource {resource_id}")
        
        # Check if this is an AJAX request - if so, return JSON
        if request.headers.get('X-Requested-With') == 'XMLHttpRequest':
            return jsonify({
                'success': True,
                'is_favorite': is_favorite,
                'message': message
            })
        
        # Otherwise redirect for regular form submission
        flash(message, 'success')
        referer = request.referrer or url_for('resource.detail_resource', resource_id=resource_id)
        return redirect(referer)
    
    except Exception as e:
        logger.error(f"Error toggling favorite: {e}")
        db.session.rollback()
        if request.headers.get('X-Requested-With') == 'XMLHttpRequest':
            return jsonify({'success': False, 'error': str(e)}), 500
        flash(f"Error updating favorite: {str(e)}", "error")
        return redirect(request.referrer or url_for('booking.dashboard'))


@favorites_bp.route('')
@login_required
def view_favorites():
    """View user's favorite resources"""
    try:
        favorites = UserFavorite.query.filter_by(
            user_id=current_user.id
        ).order_by(UserFavorite.created_at.desc()).all()
        
        favorite_resources = [fav.resource for fav in favorites if fav.resource]
        
        return render_template(
            'bookings/favorites.html',
            favorite_resources=favorite_resources,
            count=len(favorite_resources)
        )
    
    except Exception as e:
        logger.error(f"Error viewing favorites: {e}")
        flash("Error loading favorites", "error")
        return redirect(url_for('booking.dashboard'))


@favorites_bp.route('/is-favorite/<int:resource_id>')
@login_required
def is_favorite(resource_id):
    """Check if resource is favorited (AJAX endpoint)"""
    try:
        favorite = UserFavorite.query.filter_by(
            user_id=current_user.id,
            resource_id=resource_id
        ).first()
        
        return jsonify({'is_favorite': favorite is not None})
    
    except Exception as e:
        logger.error(f"Error checking favorite status: {e}")
        return jsonify({'is_favorite': False}), 500


@favorites_bp.route('/count')
@login_required
def favorite_count():
    """Get count of user's favorites"""
    try:
        count = UserFavorite.query.filter_by(user_id=current_user.id).count()
        return jsonify({'count': count})
    
    except Exception as e:
        logger.error(f"Error getting favorite count: {e}")
        return jsonify({'count': 0}), 500
