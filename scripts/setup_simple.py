"""
Simplified Resource Setup - Just 25 core resources
"""

import sys
import os
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from app import app, db
from models import Resource, ResourceSystem
from datetime import time

def setup_simple_resources():
    with app.app_context():
        # Get or create main facility
        facility = ResourceSystem.query.filter_by(name='Main Facility').first()
        if not facility:
            facility = ResourceSystem(
                name='Main Facility',
                description='Central booking facility',
                location='Building A',
                latitude=40.7128,
                longitude=-74.0060
            )
            db.session.add(facility)
            db.session.commit()
        
        # Delete old resources
        Resource.query.delete()
        db.session.commit()
        
        resources_data = [
            # Conference Rooms
            ('Conference Room A', 'room', 15, 75.00, 'Executive boardroom with video conferencing'),
            ('Conference Room B', 'room', 20, 85.00, 'Medium meeting room'),
            ('Conference Room C', 'room', 30, 95.00, 'Large conference hall'),
            ('Executive Suite', 'room', 8, 120.00, 'Private executive meeting room'),
            
            # Meeting Rooms
            ('Meeting Room 1', 'room', 6, 45.00, 'Small intimate meeting space'),
            ('Meeting Room 2', 'room', 10, 55.00, 'Standard meeting room'),
            ('Meeting Room 3', 'room', 12, 65.00, 'Medium meeting room'),
            ('Collaboration Space', 'room', 8, 50.00, 'Open collaboration area'),
            
            # Training Rooms
            ('Training Room A', 'room', 25, 70.00, 'Training with presentation setup'),
            ('Training Room B', 'room', 35, 85.00, 'Large training facility'),
            ('Workshop Space', 'room', 20, 80.00, 'Hands-on workshop area'),
            
            # Research Labs
            ('Lab 1 - Chemistry', 'lab', 12, 150.00, 'Chemistry research laboratory'),
            ('Lab 2 - Biology', 'lab', 12, 150.00, 'Biology research laboratory'),
            ('Lab 3 - Physics', 'lab', 10, 180.00, 'Physics research laboratory'),
            ('Lab 4 - Shared', 'lab', 15, 100.00, 'Shared research lab'),
            
            # Computer Labs
            ('Computer Lab A', 'lab', 30, 90.00, '30 workstations with dual monitors'),
            ('Computer Lab B', 'lab', 25, 85.00, '25 powerful workstations'),
            ('Dev Studio', 'lab', 12, 110.00, 'Development and coding studio'),
            
            # Auditoriums
            ('Main Auditorium', 'auditorium', 200, 250.00, 'Large presentation hall with stage'),
            ('Small Auditorium', 'auditorium', 80, 150.00, 'Intimate auditorium'),
            
            # Specialty Spaces
            ('Recording Studio', 'studio', 5, 120.00, 'Professional audio/video recording'),
            ('Design Studio', 'studio', 10, 85.00, 'Creative design workspace'),
            ('Break Room', 'room', 20, 30.00, 'Casual break and relaxation area'),
            ('Game Room', 'entertainment', 12, 40.00, 'Recreation and gaming space'),
            ('Library Study Area', 'room', 30, 35.00, 'Quiet study space with books'),
            ('Outdoor Terrace', 'outdoor', 50, 50.00, 'Beautiful outdoor event space'),
        ]
        
        for name, res_type, capacity, rate, description in resources_data:
            resource = Resource(
                name=name,
                description=description,
                resource_type=res_type,
                capacity=capacity,
                hourly_rate=rate,
                location='Building A',
                availability_start=time(8, 0),
                availability_end=time(22, 0),
                resource_system_id=facility.id,
                is_available=True,
                features=f'{name} - {capacity} people'
            )
            db.session.add(resource)
        
        db.session.commit()
        
        print("=" * 70)
        print("[v0] SUCCESS! Simplified resource setup complete!")
        print("=" * 70)
        print(f"\n[v0] Added {len(resources_data)} resources to database")
        print(f"[v0] All resources linked to: Main Facility\n")
        print("[v0] Resources created:")
        for name, res_type, capacity, rate, _ in resources_data:
            print(f"    - {name} ({res_type}) | Capacity: {capacity} | Rate: ${rate}/hr")
        print("\n" + "=" * 70)
        print("[v0] Now run: python app.py")
        print("[v0] Then go to: http://localhost:5000")
        print("[v0] Click 'Resources' to see all resources!")
        print("=" * 70)

if __name__ == '__main__':
    setup_simple_resources()
