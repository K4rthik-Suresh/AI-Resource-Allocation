"""
Add 500+ More Resources and 20+ Future Bookings
Includes halls, auditoriums, and other venue types
"""

import sys
import os
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from app import app, db
from models import Resource, ResourceSystem, Booking, User
from datetime import datetime, timedelta, time
import random

def add_bulk_resources_and_bookings():
    with app.app_context():
        # Get or create main facility
        facility = ResourceSystem.query.filter_by(name="Main Facility").first()
        if not facility:
            facility = ResourceSystem(
                name="Main Facility",
                description="Main Facility",
                location="Building A",
                capacity=10000,
                created_at=datetime.now()
            )
            db.session.add(facility)
            db.session.commit()
            print(f"[v0] Created facility with ID: {facility.id}")

        # Extended resources data - 500+ items with HALLS
        resources_data = [
            # HALLS (NEW - 50 resources)
            *[{
                "name": f"Grand Hall {i + 1}",
                "category": "Grand Halls",
                "resource_type": "hall",
                "capacity": 150 + (i % 8) * 50,
                "rate": 200 + (i % 6) * 50
            } for i in range(25)],
            
            *[{
                "name": f"Event Hall {i + 1}",
                "category": "Event Halls",
                "resource_type": "hall",
                "capacity": 100 + (i % 6) * 30,
                "rate": 150 + (i % 5) * 40
            } for i in range(25)],
            
            # Conference Rooms (80 resources)
            *[{
                "name": f"Conference Room {chr(65 + (i % 26))}-{i // 26 + 1}",
                "category": "Conference Rooms",
                "resource_type": "room",
                "capacity": 10 + (i % 8) * 5,
                "rate": 50 + (i % 7) * 15
            } for i in range(80)],
            
            # Meeting Rooms (60 resources)
            *[{
                "name": f"Meeting Room {i + 1}",
                "category": "Meeting Rooms",
                "resource_type": "room",
                "capacity": 6 + (i % 6) * 3,
                "rate": 40 + (i % 5) * 10
            } for i in range(60)],
            
            # Training Rooms (50 resources)
            *[{
                "name": f"Training Room {i + 1}",
                "category": "Training Rooms",
                "resource_type": "room",
                "capacity": 15 + (i % 7) * 5,
                "rate": 60 + (i % 6) * 15
            } for i in range(50)],
            
            # Research Labs (40 resources)
            *[{
                "name": f"Research Lab {i + 1}",
                "category": "Research Labs",
                "resource_type": "lab",
                "capacity": 8 + (i % 5) * 3,
                "rate": 100 + (i % 6) * 25
            } for i in range(40)],
            
            # Computer Labs (50 resources)
            *[{
                "name": f"Computer Lab {i + 1}",
                "category": "Computer Labs",
                "resource_type": "lab",
                "capacity": 20 + (i % 8) * 5,
                "rate": 80 + (i % 7) * 20
            } for i in range(50)],
            
            # Auditoriums (30 resources)
            *[{
                "name": f"Auditorium {i + 1}",
                "category": "Auditoriums",
                "resource_type": "auditorium",
                "capacity": 100 + (i % 7) * 60,
                "rate": 150 + (i % 6) * 40
            } for i in range(30)],
            
            # Executive Offices (40 resources)
            *[{
                "name": f"Executive Office {i + 1}",
                "category": "Executive Offices",
                "resource_type": "room",
                "capacity": 2 + (i % 4),
                "rate": 70 + (i % 5) * 20
            } for i in range(40)],
            
            # Open Workspaces (35 resources)
            *[{
                "name": f"Open Workspace {i + 1}",
                "category": "Open Workspaces",
                "resource_type": "room",
                "capacity": 30 + (i % 8) * 15,
                "rate": 50 + (i % 6) * 15
            } for i in range(35)],
            
            # Study Rooms (25 resources)
            *[{
                "name": f"Study Room {i + 1}",
                "category": "Study Rooms",
                "resource_type": "room",
                "capacity": 4 + (i % 4) * 2,
                "rate": 25 + (i % 4) * 8
            } for i in range(25)],
            
            # Video Conference Rooms (30 resources)
            *[{
                "name": f"Video Conference Room {i + 1}",
                "category": "Video Conference Rooms",
                "resource_type": "room",
                "capacity": 6 + (i % 5) * 3,
                "rate": 75 + (i % 5) * 20
            } for i in range(30)],
            
            # Specialized Equipment Rooms (25 resources)
            *[{
                "name": f"Equipment Room {i + 1}",
                "category": "Specialized Equipment",
                "resource_type": "equipment",
                "capacity": 10 + (i % 4) * 5,
                "rate": 120 + (i % 5) * 30
            } for i in range(25)],
            
            # Event Spaces (30 resources)
            *[{
                "name": f"Event Space {i + 1}",
                "category": "Event Spaces",
                "resource_type": "hall",
                "capacity": 50 + (i % 8) * 40,
                "rate": 100 + (i % 7) * 30
            } for i in range(30)],
            
            # Recreation Areas (20 resources)
            *[{
                "name": f"Recreation Area {i + 1}",
                "category": "Recreation Areas",
                "resource_type": "room",
                "capacity": 20 + (i % 5) * 12,
                "rate": 40 + (i % 4) * 12
            } for i in range(20)],
            
            # Testing Centers (25 resources)
            *[{
                "name": f"Testing Center {i + 1}",
                "category": "Testing Centers",
                "resource_type": "lab",
                "capacity": 25 + (i % 5) * 8,
                "rate": 90 + (i % 5) * 20
            } for i in range(25)],
            
            # Breakout Rooms (35 resources)
            *[{
                "name": f"Breakout Room {i + 1}",
                "category": "Breakout Rooms",
                "resource_type": "room",
                "capacity": 8 + (i % 5) * 4,
                "rate": 35 + (i % 5) * 10
            } for i in range(35)],
            
            # Studio Spaces (20 resources)
            *[{
                "name": f"Studio {i + 1}",
                "category": "Studio Spaces",
                "resource_type": "room",
                "capacity": 12 + (i % 5) * 6,
                "rate": 110 + (i % 5) * 25
            } for i in range(20)],
        ]

        print(f"[v0] Adding {len(resources_data)} resources to database...")
        
        # Add resources in batches
        added_count = 0
        for idx, resource_info in enumerate(resources_data):
            # Check if resource already exists
            existing = Resource.query.filter_by(name=resource_info["name"]).first()
            if not existing:
                resource = Resource(
                    name=resource_info["name"],
                    description=f"{resource_info['category']} - {resource_info['name']}",
                    resource_type=resource_info["resource_type"],
                    capacity=resource_info["capacity"],
                    hourly_rate=resource_info["rate"],
                    resource_system_id=facility.id,
                    location=f"Building A - {resource_info['category']}",
                    is_available=True,
                    created_at=datetime.now()
                )
                db.session.add(resource)
                added_count += 1
            
            # Commit in batches of 50
            if (idx + 1) % 50 == 0:
                db.session.commit()
                print(f"[v0] Inserted {idx + 1} resources ({added_count} new)...")
        
        db.session.commit()
        print(f"[v0] Total resources added: {added_count}")
        
        # Now add 20+ future bookings
        print(f"\n[v0] Adding 20+ future bookings...")
        
        # Get admin user or create one
        admin_user = User.query.filter_by(username='admin').first()
        if not admin_user:
            print("[v0] Warning: No admin user found, skipping bookings")
            return
        
        # Get some resources for booking
        all_resources = Resource.query.filter_by(resource_system_id=facility.id).limit(100).all()
        
        if not all_resources:
            print("[v0] Warning: No resources found to create bookings")
            return
        
        # Create bookings for future dates (next 7-30 days)
        base_date = datetime.now().date() + timedelta(days=1)
        
        booking_entries = []
        for i in range(25):
            # Pick random resource
            resource = random.choice(all_resources)
            
            # Random date within next 30 days
            booking_date = base_date + timedelta(days=random.randint(0, 29))
            
            # Random times
            start_hour = random.randint(8, 16)
            end_hour = min(start_hour + random.randint(1, 4), 18)
            
            start_time = time(start_hour, 0, 0)
            end_time = time(end_hour, 0, 0)
            
            # Check for conflicts
            conflict = Booking.query.filter(
                Booking.resource_id == resource.id,
                Booking.booking_date == booking_date,
                Booking.status != 'cancelled'
            ).first()
            
            if not conflict:
                booking = Booking(
                    user_id=admin_user.id,
                    resource_id=resource.id,
                    resource_system_id=facility.id,
                    booking_date=booking_date,
                    start_time=start_time,
                    end_time=end_time,
                    status='confirmed',
                    cost=resource.hourly_rate * (end_hour - start_hour),
                    created_at=datetime.now()
                )
                db.session.add(booking)
                booking_entries.append((resource.name, booking_date, start_time, end_time))
                
                # Commit every 5 bookings
                if (i + 1) % 5 == 0:
                    db.session.commit()
                    print(f"[v0] Added {i + 1} bookings...")
        
        db.session.commit()
        print(f"[v0] Total bookings added: {len(booking_entries)}")
        
        # Display summary
        print("\n[v0] ===== BOOKING SUMMARY =====")
        for resource_name, date, start, end in booking_entries[:10]:  # Show first 10
            print(f"  {resource_name} - {date} {start.strftime('%H:%M')} to {end.strftime('%H:%M')}")
        if len(booking_entries) > 10:
            print(f"  ... and {len(booking_entries) - 10} more bookings")
        
        print(f"\n[v0] ===== COMPLETION =====")
        print(f"[v0] Resources: {added_count} added")
        print(f"[v0] Bookings: {len(booking_entries)} added")
        print(f"[v0] Halls: Added 50 hall resources (Grand Halls + Event Halls)")

if __name__ == '__main__':
    add_bulk_resources_and_bookings()
    print("\n[v0] Data seeding complete!")
