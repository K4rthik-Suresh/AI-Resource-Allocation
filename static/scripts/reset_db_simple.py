#!/usr/bin/env python3
"""Simple database reset for multi-system architecture"""
import sys
sys.path.insert(0, '/app')

from app import app, db
from models import User, Resource, ResourceSystem, Booking, UserResourceSystem, BookingHistory, AuditLog
from flask_bcrypt import Bcrypt

bcrypt = Bcrypt()

print("[v0] Starting database reset...")

with app.app_context():
    try:
        # Drop all tables
        print("[v0] Dropping all existing tables...")
        db.drop_all()
        
        # Create all tables
        print("[v0] Creating new tables with multi-system schema...")
        db.create_all()
        
        # Create default system
        print("[v0] Creating Main Facility...")
        default_system = ResourceSystem(
            name='Main Facility',
            description='Default resource facility',
            address='123 Main Street',
            city='Main City',
            latitude=40.7128,
            longitude=-74.0060,
            is_public=True,
            is_active=True
        )
        db.session.add(default_system)
        db.session.commit()
        print(f"[v0] Main Facility created with ID: {default_system.id}")
        
        # Create admin user
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
        print(f"[v0] Admin user created")
        
        # Assign admin to system
        print("[v0] Assigning admin to Main Facility...")
        assignment = UserResourceSystem(
            user_id=admin.id,
            resource_system_id=default_system.id,
            role='admin'
        )
        db.session.add(assignment)
        db.session.commit()
        
        # Create sample resources
        print("[v0] Creating sample resources...")
        resources = [
            Resource(
                resource_system_id=default_system.id,
                name='Conference Room A',
                description='Large conference room',
                resource_type='room',
                capacity=20,
                location='Building 1, Floor 3',
                features='["projector", "whiteboard"]',
                square_feet=500,
                hourly_rate=50.0,
                daily_rate=300.0,
                monthly_rate=3000.0,
                is_available=True
            ),
            Resource(
                resource_system_id=default_system.id,
                name='Laboratory 1',
                description='Science laboratory',
                resource_type='lab',
                capacity=15,
                location='Building 2, Floor 1',
                features='["microscopes", "fume hood"]',
                square_feet=600,
                hourly_rate=75.0,
                daily_rate=450.0,
                monthly_rate=4500.0,
                is_available=True
            ),
        ]
        
        for resource in resources:
            db.session.add(resource)
        
        db.session.commit()
        print(f"[v0] Created {len(resources)} sample resources")
        
        print("\n" + "="*60)
        print("✅ DATABASE RESET SUCCESSFUL!")
        print("="*60)
        print("\n📝 Login Credentials:")
        print("   Username: admin")
        print("   Password: Admin@12345")
        print("\n⚠️  Change password after first login!")
        print("="*60 + "\n")
        
    except Exception as e:
        print(f"\n❌ ERROR: {str(e)}")
        import traceback
        traceback.print_exc()
        sys.exit(1)
