"""
Phase 1: System Announcements Routes
"""

from flask import Blueprint, render_template, request, jsonify, redirect, url_for, flash
from flask_login import login_required, current_user
from models import db, SystemAnnouncement, User
from datetime import datetime, timedelta
import logging

logger = logging.getLogger(__name__)

announcements_bp = Blueprint('announcements', __name__, url_prefix='/announcements')


@announcements_bp.route('/')
def get_announcements():
    """Get active announcements (AJAX endpoint)"""
    try:
        announcements = SystemAnnouncement.get_active_announcements()
        
        data = []
        for ann in announcements:
            data.append({
                'id': ann.id,
                'title': ann.title,
                'message': ann.message,
                'type': ann.announcement_type,
                'is_pinned': ann.is_pinned,
                'created_at': ann.created_at.strftime('%Y-%m-%d %H:%M'),
                'expires_at': ann.end_date.strftime('%Y-%m-%d') if ann.end_date else None
            })
        
        return jsonify({'announcements': data})
    
    except Exception as e:
        logger.error(f"Error fetching announcements: {e}")
        return jsonify({'announcements': []}), 500


@announcements_bp.route('/admin/create', methods=['GET', 'POST'])
@login_required
def create_announcement():
    """Admin: Create new announcement"""
    try:
        if current_user.role not in ['admin']:
            flash("You don't have permission to create announcements", "error")
            return redirect(url_for('booking.dashboard'))
        
        if request.method == 'POST':
            title = request.form.get('title')
            message = request.form.get('message')
            ann_type = request.form.get('type', 'info')
            is_pinned = request.form.get('is_pinned') == 'on'
            expire_days = int(request.form.get('expire_days', 7))
            
            if not title or not message:
                flash("Title and message are required", "error")
                return redirect(url_for('announcements.create_announcement'))
            
            end_date = None
            if expire_days > 0:
                end_date = datetime.utcnow() + timedelta(days=expire_days)
            
            announcement = SystemAnnouncement(
                title=title,
                message=message,
                announcement_type=ann_type,
                created_by=current_user.id,
                is_pinned=is_pinned,
                end_date=end_date,
                is_active=True
            )
            
            db.session.add(announcement)
            db.session.commit()
            
            logger.info(f"Admin {current_user.username} created announcement: {title}")
            flash(f"Announcement '{title}' created successfully!", "success")
            return redirect(url_for('announcements.manage_announcements'))
        
        return render_template('announcements/create.html')
    
    except Exception as e:
        logger.error(f"Error creating announcement: {e}")
        flash(f"Error creating announcement: {str(e)}", "error")
        return redirect(url_for('announcements.manage_announcements'))


@announcements_bp.route('/admin/manage')
@login_required
def manage_announcements():
    """Admin: Manage announcements"""
    try:
        if current_user.role not in ['admin']:
            flash("You don't have permission to access this page", "error")
            return redirect(url_for('booking.dashboard'))
        
        # Get all announcements (including expired)
        announcements = SystemAnnouncement.query.order_by(
            SystemAnnouncement.is_pinned.desc(),
            SystemAnnouncement.created_at.desc()
        ).all()
        
        return render_template('announcements/manage.html', announcements=announcements)
    
    except Exception as e:
        logger.error(f"Error managing announcements: {e}")
        flash(f"Error loading announcements: {str(e)}", "error")
        return redirect(url_for('booking.dashboard'))


@announcements_bp.route('/admin/edit/<int:announcement_id>', methods=['GET', 'POST'])
@login_required
def edit_announcement(announcement_id):
    """Admin: Edit announcement"""
    try:
        if current_user.role not in ['admin']:
            flash("You don't have permission to edit announcements", "error")
            return redirect(url_for('booking.dashboard'))
        
        announcement = SystemAnnouncement.query.get(announcement_id)
        if not announcement:
            flash("Announcement not found", "error")
            return redirect(url_for('announcements.manage_announcements'))
        
        if request.method == 'POST':
            announcement.title = request.form.get('title')
            announcement.message = request.form.get('message')
            announcement.announcement_type = request.form.get('type', 'info')
            announcement.is_pinned = request.form.get('is_pinned') == 'on'
            announcement.is_active = request.form.get('is_active') == 'on'
            
            expire_days = int(request.form.get('expire_days', 7))
            if expire_days > 0:
                announcement.end_date = datetime.utcnow() + timedelta(days=expire_days)
            else:
                announcement.end_date = None
            
            announcement.updated_at = datetime.utcnow()
            
            db.session.commit()
            
            logger.info(f"Admin {current_user.username} updated announcement: {announcement.title}")
            flash(f"Announcement '{announcement.title}' updated successfully!", "success")
            return redirect(url_for('announcements.manage_announcements'))
        
        return render_template('announcements/edit.html', announcement=announcement)
    
    except Exception as e:
        logger.error(f"Error editing announcement: {e}")
        flash(f"Error updating announcement: {str(e)}", "error")
        return redirect(url_for('announcements.manage_announcements'))


@announcements_bp.route('/admin/delete/<int:announcement_id>', methods=['POST'])
@login_required
def delete_announcement(announcement_id):
    """Admin: Delete announcement"""
    try:
        if current_user.role not in ['admin']:
            return jsonify({'success': False, 'error': 'Unauthorized'}), 403
        
        announcement = SystemAnnouncement.query.get(announcement_id)
        if not announcement:
            return jsonify({'success': False, 'error': 'Announcement not found'}), 404
        
        title = announcement.title
        db.session.delete(announcement)
        db.session.commit()
        
        logger.info(f"Admin {current_user.username} deleted announcement: {title}")
        return jsonify({'success': True, 'message': f"Announcement '{title}' deleted"})
    
    except Exception as e:
        logger.error(f"Error deleting announcement: {e}")
        return jsonify({'success': False, 'error': str(e)}), 500


@announcements_bp.route('/admin/cleanup', methods=['POST'])
@login_required
def cleanup_expired_announcements():
    """Admin: Delete expired announcements"""
    try:
        if current_user.role not in ['admin']:
            return jsonify({'success': False, 'error': 'Unauthorized'}), 403
        
        deleted = SystemAnnouncement.query.filter(
            SystemAnnouncement.end_date < datetime.utcnow(),
            SystemAnnouncement.end_date != None
        ).delete()
        
        db.session.commit()
        
        logger.info(f"Admin {current_user.username} cleaned up {deleted} expired announcements")
        return jsonify({'success': True, 'message': f"Deleted {deleted} expired announcements"})
    
    except Exception as e:
        logger.error(f"Error cleaning up announcements: {e}")
        return jsonify({'success': False, 'error': str(e)}), 500
