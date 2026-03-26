#!/usr/bin/env python3
"""
Database Migration Script for Multi-System Architecture
Handles schema changes and data migration
"""
import sys
import os
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from app import app, db
from models import User, Resource, ResourceSystem, Booking, UserResourceSystem, BookingHistory, AuditLog
from flask_bcrypt import Bcrypt
from datetime import datetime

bcrypt = Bcrypt()

def reset_database():
    """Drop all tables and recreate schema"""
    with app.app_context():
        print("[v0] Dropping all tables...")
        db.drop_all()
        print("[v0] Creating all tables with new schema...")
        db.create_all()
        print("[v0] Database schema created successfully!")

def create_default_system():
    """Create default resource system"""
    with app.app_context():
        default_system = ResourceSystem.query.filter_by(name='Main Facility').first()
        
        if not default_system:
            print("[v0] Creating default ResourceSystem...")
            default_system = ResourceSystem(
                name='Main Facility',
                description='Default resource facility for all resources',
                address='123 Main Street',
                city='Main City',
                latitude=40.7128,
                longitude=-74.0060,
                is_public=True,
                is_active=True
            )
            db.session.add(default_system)
            db.session.commit()
            print(f"[v0] Default system created with ID: {default_system.id}")
        
        return default_system

def create_admin_user(system_id):
    """Create admin user and assign to system"""
    with app.app_context():
        admin = User.query.filter_by(username='admin').first()
        
        if not admin:
            print("[v0] Creating admin user...")
            admin = User(
                username='admin',
                email='admin@example.com',
                password_hash=bcrypt.generate_password_hash('Admin@12345').decode('utf-8'),
                full_name='Administrator',
                role='admin',
                is_active=True
            )
            db.session.add(admin)
            db.session.commit()
            print(f"[v0] Admin user created. Username: admin, Password: Admin@12345")
        
        # Assign admin to system
        assignment = UserResourceSystem.query.filter_by(
            user_id=admin.id,
            resource_system_id=system_id
        ).first()
        
        if not assignment:
            print("[v0] Assigning admin to Main Facility...")
            assignment = UserResourceSystem(
                user_id=admin.id,
                resource_system_id=system_id,
                role='admin'
            )
            db.session.add(assignment)
            db.session.commit()
            print("[v0] Admin assigned to Main Facility")
        
        return admin

def create_sample_resources(system_id):
    """Create sample resources in the default system"""
    with app.app_context():
        sample_resources = [
            {
                'name': 'Conference Room A',
                'description': 'Large conference room with projector and whiteboard',
                'resource_type': 'room',
                'capacity': 20,
                'location': 'Building 1, Floor 3',
                'features': '["projector", "whiteboard", "video conferencing"]',
                'square_feet': 500,
                'hourly_rate': 50.0,
                'daily_rate': 300.0,
                'monthly_rate': 3000.0,
            },
            {
                'name': 'Conference Room B',
                'description': 'Medium conference room',
                'resource_type': 'room',
                'capacity': 12,
                'location': 'Building 1, Floor 2',
                'features': '["projector", "whiteboard"]',
                'square_feet': 350,
                'hourly_rate': 40.0,
                'daily_rate': 250.0,
                'monthly_rate': 2500.0,
            },
            {
                'name': 'Laboratory 1',
                'description': 'Science laboratory with equipment',
                'resource_type': 'lab',
                'capacity': 15,
                'location': 'Building 2, Floor 1',
                'features': '["microscopes", "fume hood", "centrifuge"]',
                'square_feet': 600,
                'hourly_rate': 75.0,
                'daily_rate': 450.0,
                'monthly_rate': 4500.0,
            },
            {
                'name': 'Meeting Hall',
                'description': 'Spacious hall for events and meetings',
                'resource_type': 'hall',
                'capacity': 100,
                'location': 'Building 1, Ground Floor',
                'features': '["stage", "audio system", "lighting"]',
                'square_feet': 2000,
                'hourly_rate': 150.0,
                'daily_rate': 800.0,
                'monthly_rate': 8000.0,
            },
        ]
        
        created_count = 0
        for resource_data in sample_resources:
            existing = Resource.query.filter_by(name=resource_data['name']).first()
            if not existing:
                resource = Resource(
                    resource_system_id=system_id,
                    **resource_data,
                    is_available=True
                )
                db.session.add(resource)
                created_count += 1
        
        db.session.commit()
        print(f"[v0] Created {created_count} sample resources")

def migrate():
    """Run complete migration"""
    print("\n" + "="*60)
    print("DATABASE MIGRATION - Multi-System Architecture")
    print("="*60 + "\n")
    
    try:
        # Step 1: Reset database
        reset_database()
        
        # Step 2: Create default system
        system = create_default_system()
        
        # Step 3: Create admin user
        create_admin_user(system.id)
        
        # Step 4: Create sample resources
        create_sample_resources(system.id)
        
        print("\n" + "="*60)
        print("✅ MIGRATION COMPLETED SUCCESSFULLY!")
        print("="*60)
        print("\n📝 Login Credentials:")
        print("   Username: admin")
        print("   Password: Admin@12345")
        print("\n⚠️  IMPORTANT: Change the admin password after first login!")
        print("="*60 + "\n")
        
    except Exception as e:
        print(f"\n❌ MIGRATION FAILED: {str(e)}")
        print(f"Error details: {type(e).__name__}")
        import traceback
        traceback.print_exc()
        sys.exit(1)

if __name__ == '__main__':
    migrate()
