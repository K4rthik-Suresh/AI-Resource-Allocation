#!/usr/bin/env python
"""Phase 1 Database Migration - Add new columns and tables"""
import os
import sys
from datetime import datetime

# Add parent directory (project root) to path
script_dir = os.path.dirname(os.path.abspath(__file__))
parent_dir = os.path.dirname(script_dir)
sys.path.insert(0, parent_dir)

from app import app, db
from models import Booking, User, UserFavorite, SystemAnnouncement
from sqlalchemy import text, inspect

def migrate_phase1():
    """Execute Phase 1 database migration"""
    print("[v0] Starting Phase 1 Database Migration...")
    
    with app.app_context():
        try:
            # Get inspector to check existing columns
            inspector = inspect(db.engine)
            bookings_columns = [col['name'] for col in inspector.get_columns('bookings')]
            users_columns = [col['name'] for col in inspector.get_columns('users')]
            
            print(f"[v0] Current bookings columns: {bookings_columns}")
            print(f"[v0] Current users columns: {users_columns}")
            
            # Add user_notes column if it doesn't exist
            if 'user_notes' not in bookings_columns:
                print("[v0] Adding user_notes column to bookings table...")
                with db.engine.connect() as conn:
                    conn.execute(text('ALTER TABLE bookings ADD COLUMN user_notes TEXT'))
                    conn.commit()
                print("[v0] Successfully added user_notes column")
            else:
                print("[v0] user_notes column already exists")
            
            # Add admin_notes column if it doesn't exist
            if 'admin_notes' not in bookings_columns:
                print("[v0] Adding admin_notes column to bookings table...")
                with db.engine.connect() as conn:
                    conn.execute(text('ALTER TABLE bookings ADD COLUMN admin_notes TEXT'))
                    conn.commit()
                print("[v0] Successfully added admin_notes column")
            else:
                print("[v0] admin_notes column already exists")
            
            # Add timezone column to users if it doesn't exist
            if 'timezone' not in users_columns:
                print("[v0] Adding timezone column to users table...")
                with db.engine.connect() as conn:
                    conn.execute(text("ALTER TABLE users ADD COLUMN timezone VARCHAR(50) DEFAULT 'UTC'"))
                    conn.commit()
                print("[v0] Successfully added timezone column")
            else:
                print("[v0] timezone column already exists")
            
            # Check if user_favorites table exists, if not create it
            existing_tables = inspector.get_table_names()
            
            if 'user_favorites' not in existing_tables:
                print("[v0] Creating user_favorites table...")
                db.create_all()
                print("[v0] Successfully created user_favorites table")
            else:
                print("[v0] user_favorites table already exists")
            
            if 'system_announcements' not in existing_tables:
                print("[v0] Creating system_announcements table...")
                db.create_all()
                print("[v0] Successfully created system_announcements table")
            else:
                print("[v0] system_announcements table already exists")
            
            print("[v0] Phase 1 Migration completed successfully!")
            return True
            
        except Exception as e:
            print(f"[v0] ERROR during migration: {e}")
            import traceback
            traceback.print_exc()
            return False

if __name__ == '__main__':
    success = migrate_phase1()
    sys.exit(0 if success else 1)
