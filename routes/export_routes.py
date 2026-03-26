"""
Phase 1: CSV Export Functionality
"""

from flask import Blueprint, send_file, request, jsonify, current_app
from flask_login import login_required, current_user
from models import db, Booking, Resource
from datetime import datetime
from io import StringIO, BytesIO
import csv
import logging

logger = logging.getLogger(__name__)

export_bp = Blueprint('export', __name__, url_prefix='/bookings/export')


@export_bp.route('/csv')
@login_required
def export_bookings_csv():
    """Export user's bookings to CSV with optional date range filter"""
    try:
        # Get filter parameters
        start_date = request.args.get('start_date')
        end_date = request.args.get('end_date')
        status_filter = request.args.get('status')
        
        # Start query
        query = Booking.query.filter_by(user_id=current_user.id)
        
        # Apply filters
        if start_date:
            query = query.filter(Booking.booking_date >= start_date)
        
        if end_date:
            query = query.filter(Booking.booking_date <= end_date)
        
        if status_filter and status_filter != 'all':
            query = query.filter_by(status=status_filter)
        
        # Limit to max 10000 rows
        bookings = query.order_by(Booking.booking_date.desc()).limit(10000).all()
        
        # Create CSV
        output = StringIO()
        writer = csv.writer(output)
        
        # Write headers
        writer.writerow([
            'Booking ID',
            'Resource Name',
            'Resource Type',
            'Booking Date',
            'Start Time',
            'End Time',
            'Duration (Days)',
            'Purpose',
            'Status',
            'Cost',
            'User Notes',
            'Created At',
            'Updated At'
        ])
        
        # Write data
        for booking in bookings:
            writer.writerow([
                booking.id,
                booking.resource.name if booking.resource else 'N/A',
                booking.resource.resource_type if booking.resource else 'N/A',
                booking.booking_date.strftime('%Y-%m-%d'),
                booking.start_time.strftime('%H:%M') if booking.start_time else '',
                booking.end_time.strftime('%H:%M') if booking.end_time else '',
                booking.duration_days,
                booking.purpose or '',
                booking.status,
                f"${booking.cost:.2f}",
                booking.user_notes or '',
                booking.created_at.strftime('%Y-%m-%d %H:%M:%S'),
                booking.updated_at.strftime('%Y-%m-%d %H:%M:%S')
            ])
        
        # Create file-like object
        output.seek(0)
        mem = BytesIO()
        mem.write(output.getvalue().encode('utf-8'))
        mem.seek(0)
        
        # Generate filename
        filename = f"bookings_{datetime.now().strftime('%Y%m%d_%H%M%S')}.csv"
        
        logger.info(f"User {current_user.id} exported {len(bookings)} bookings")
        
        return send_file(
            mem,
            mimetype='text/csv',
            as_attachment=True,
            download_name=filename
        )
    
    except Exception as e:
        logger.error(f"Error exporting CSV: {e}")
        return jsonify({'error': str(e)}), 500


@export_bp.route('/csv-admin')
@login_required
def export_all_bookings_csv():
    """Admin export - all bookings in system"""
    try:
        # Check if user is admin
        if current_user.role not in ['admin', 'staff']:
            return jsonify({'error': 'Unauthorized'}), 403
        
        # Get filter parameters
        start_date = request.args.get('start_date')
        end_date = request.args.get('end_date')
        resource_id = request.args.get('resource_id')
        status_filter = request.args.get('status')
        
        query = Booking.query
        
        if start_date:
            query = query.filter(Booking.booking_date >= start_date)
        if end_date:
            query = query.filter(Booking.booking_date <= end_date)
        if resource_id:
            query = query.filter_by(resource_id=resource_id)
        if status_filter and status_filter != 'all':
            query = query.filter_by(status=status_filter)
        
        bookings = query.order_by(Booking.booking_date.desc()).limit(10000).all()
        
        # Create CSV
        output = StringIO()
        writer = csv.writer(output)
        
        writer.writerow([
            'Booking ID',
            'User Name',
            'User Email',
            'Resource Name',
            'Resource Type',
            'Booking Date',
            'Start Time',
            'End Time',
            'Duration (Days)',
            'Purpose',
            'Status',
            'Cost',
            'User Notes',
            'Admin Notes',
            'Created At'
        ])
        
        for booking in bookings:
            writer.writerow([
                booking.id,
                booking.user.full_name or booking.user.username if booking.user else 'N/A',
                booking.user.email if booking.user else 'N/A',
                booking.resource.name if booking.resource else 'N/A',
                booking.resource.resource_type if booking.resource else 'N/A',
                booking.booking_date.strftime('%Y-%m-%d'),
                booking.start_time.strftime('%H:%M') if booking.start_time else '',
                booking.end_time.strftime('%H:%M') if booking.end_time else '',
                booking.duration_days,
                booking.purpose or '',
                booking.status,
                f"${booking.cost:.2f}",
                booking.user_notes or '',
                booking.admin_notes or '',
                booking.created_at.strftime('%Y-%m-%d %H:%M:%S')
            ])
        
        output.seek(0)
        mem = BytesIO()
        mem.write(output.getvalue().encode('utf-8'))
        mem.seek(0)
        
        filename = f"all_bookings_{datetime.now().strftime('%Y%m%d_%H%M%S')}.csv"
        
        logger.info(f"Admin {current_user.username} exported {len(bookings)} bookings")
        
        return send_file(
            mem,
            mimetype='text/csv',
            as_attachment=True,
            download_name=filename
        )
    
    except Exception as e:
        logger.error(f"Error exporting admin CSV: {e}")
        return jsonify({'error': str(e)}), 500
