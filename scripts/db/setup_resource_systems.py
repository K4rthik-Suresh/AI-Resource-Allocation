#!/usr/bin/env python3
"""
Migration script to set up ResourceSystem table and migrate existing resources.
This script:
1. Creates ResourceSystem table if it doesn't exist
2. Creates a default "Main Facility" system
3. Migrates all existing resources to this system
4. Sets up admin assignments for existing admin users
"""

import sys
import os
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from app import app, db
from models import ResourceSystem, UserResourceSystem, Resource, User

def setup_resource_systems():
    """Setup resource systems and migrate existing data"""
    with app.app_context():
        try:
            # Create tables if they don't exist
            db.create_all()
            print("[v0] Database tables created successfully")
            
            # Check if default system already exists
            default_system = ResourceSystem.query.filter_by(name='Main Facility').first()
            
            if not default_system:
                # Create default ResourceSystem
                default_system = ResourceSystem(
                    name='Main Facility',
                    description='Default resource facility for all existing resources',
                    address='Default Address',
                    city='Default City',
                    latitude=None,
                    longitude=None,
                    is_public=True,
                    is_active=True
                )
                db.session.add(default_system)
                db.session.commit()
                print(f"[v0] Created default ResourceSystem: 'Main Facility' (ID: {default_system.id})")
            else:
                print(f"[v0] Default ResourceSystem already exists: 'Main Facility' (ID: {default_system.id})")
            
            # Migrate existing resources without system assignment
            unassigned_resources = Resource.query.filter_by(resource_system_id=None).all()
            
            if unassigned_resources:
                for resource in unassigned_resources:
                    resource.resource_system_id = default_system.id
                db.session.commit()
                print(f"[v0] Migrated {len(unassigned_resources)} existing resources to 'Main Facility'")
            else:
                print("[v0] All resources already assigned to a system")
            
            # Assign existing admin users to the default system
            admin_users = User.query.filter_by(role='admin').all()
            
            for admin_user in admin_users:
                # Check if assignment already exists
                existing_assignment = UserResourceSystem.query.filter_by(
                    user_id=admin_user.id,
                    resource_system_id=default_system.id
                ).first()
                
                if not existing_assignment:
                    assignment = UserResourceSystem(
                        user_id=admin_user.id,
                        resource_system_id=default_system.id,
                        role='admin'
                    )
                    db.session.add(assignment)
            
            db.session.commit()
            print(f"[v0] Assigned {len(admin_users)} admin users to 'Main Facility'")
            
            print("\n[v0] ✓ Resource system setup completed successfully!")
            print(f"[v0] Default System ID: {default_system.id}")
            print(f"[v0] Resources migrated: {len(unassigned_resources)}")
            print(f"[v0] Admins assigned: {len(admin_users)}")
            
        except Exception as e:
            print(f"[v0] Error during setup: {str(e)}")
            db.session.rollback()
            sys.exit(1)

if __name__ == '__main__':
    setup_resource_systems()
