"""
Add additional relevant resources to the existing ones.
"""

import sys
import os
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from app import app, db
from models import Resource, ResourceSystem
from datetime import time

def setup_more_resources():
    with app.app_context():
        # Get main facility
        facility = ResourceSystem.query.filter_by(name='Main Facility').first()
        if not facility:
            print("Error: Main Facility not found. Please run setup_simple.py first.")
            return
        
        resources_data = [
            # Focus Spaces
            ('Focus Booth 1', 'desk', 1, 15.00, 'Soundproof booth for deep work or calls'),
            ('Focus Booth 2', 'desk', 1, 15.00, 'Soundproof booth for deep work or calls'),
            ('Focus Room Alpha', 'room', 2, 25.00, 'Small private space for 1-2 people'),
            ('Focus Room Beta', 'room', 2, 25.00, 'Small private space for 1-2 people'),
            
            # Wellness & Family
            ('Wellness Room A', 'wellness', 1, 0.00, 'Private space for meditation or relaxation'),
            ('Wellness Room B', 'wellness', 1, 0.00, 'Private space for meditation or relaxation'),
            ('Mother\'s Room', 'wellness', 1, 0.00, 'Comfortable, private nursing room'),
            
            # Digital & Content Creation
            ('Podcast Studio A', 'studio', 4, 90.00, 'Fully equipped audio podcasting suite'),
            ('Podcast Studio B', 'studio', 4, 90.00, 'Fully equipped audio podcasting suite'),
            ('Photography Studio', 'studio', 6, 110.00, 'Studio with lighting and backdrop setups'),
            ('VR/AR Lab', 'lab', 8, 150.00, 'Virtual and Augmented Reality testing environment'),
            
            # Maker & Creative Spaces
            ('Maker Space', 'lab', 15, 80.00, 'Workspace with 3D printers and crafting tools'),
            ('Ideation Room', 'room', 12, 60.00, 'Room with full 360-degree whiteboard walls and sticky notes'),
            ('Prototyping Lab', 'lab', 10, 100.00, 'Hardware prototyping and electronics bench'),
            
            # Event & Gathering Spaces
            ('Cafe Area', 'entertainment', 40, 0.00, 'Open cafe seating for casual meetings'),
            ('Rooftop Garden', 'outdoor', 60, 100.00, 'Scenic rooftop area for gatherings'),
            ('Exhibition Hall', 'auditorium', 150, 200.00, 'Open hall for exhibitions and large events'),
            
            # Specialty
            ('Data Center Access', 'specialty', 5, 300.00, 'Secure, limited access to server room'),
            ('Archive Room', 'specialty', 4, 20.00, 'Secure document review and storage access')
        ]
        
        added_count = 0
        for name, res_type, capacity, rate, description in resources_data:
            # Check if resource already exists
            existing = Resource.query.filter_by(name=name, resource_system_id=facility.id).first()
            if not existing:
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
                added_count += 1
            else:
                print(f"Skipping {name}: already exists.")
        
        db.session.commit()
        
        print("=" * 70)
        print(f"SUCCESS! Added {added_count} new resources!")
        print("=" * 70)
        print("\nNew resources added:")
        for name, res_type, capacity, rate, _ in resources_data:
            print(f"    - {name} ({res_type}) | Capacity: {capacity} | Rate: ${rate}/hr")
        print("\n" + "=" * 70)

if __name__ == '__main__':
    setup_more_resources()
