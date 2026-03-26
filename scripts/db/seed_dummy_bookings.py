"""
Script to add dummy booking data for analytics testing.
This will create bookings spread across the last 12 months with varying counts.
"""

import sys
import os
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from datetime import datetime, timedelta, date, time
import random
from app import app, db
from models import User, Resource, ResourceSystem, Booking

def seed_dummy_bookings():
    with app.app_context():
        # Get existing users and resources
        users = User.query.all()
        resources = Resource.query.all()
        resource_systems = ResourceSystem.query.all()
        
        if not users:
            print("No users found. Please create users first.")
            return
        
        if not resources:
            print("No resources found. Please create resources first.")
            return
        
        if not resource_systems:
            print("No resource systems found.")
            return
        
        print(f"Found {len(users)} users, {len(resources)} resources, {len(resource_systems)} systems")
        
        # Define booking patterns for each month (more realistic distribution)
        # Key: months ago, Value: number of bookings
        monthly_booking_counts = {
            0: 5,   # Current month
            1: 8,   # Last month
            2: 12,  # 2 months ago
            3: 15,  # 3 months ago
            4: 10,  # 4 months ago
            5: 18,  # 5 months ago
            6: 22,  # 6 months ago (peak)
            7: 20,  # 7 months ago
            8: 14,  # 8 months ago
            9: 11,  # 9 months ago
            10: 8,  # 10 months ago
            11: 6,  # 11 months ago
        }
        
        # Time slots for bookings
        time_slots = [
            (time(8, 0), time(10, 0)),
            (time(10, 0), time(12, 0)),
            (time(12, 0), time(14, 0)),
            (time(14, 0), time(16, 0)),
            (time(16, 0), time(18, 0)),
            (time(18, 0), time(20, 0)),
        ]
        
        # Purposes
        purposes = [
            "Team Meeting",
            "Client Presentation",
            "Training Session",
            "Workshop",
            "Board Meeting",
            "Interview",
            "Project Review",
            "Strategy Planning",
            "Department Sync",
            "Product Demo"
        ]
        
        statuses = ['confirmed', 'completed', 'confirmed', 'completed', 'completed']  # Mostly completed/confirmed
        
        today = date.today()
        bookings_created = 0
        
        for months_ago, count in monthly_booking_counts.items():
            # Calculate the target month
            target_date = today - timedelta(days=months_ago * 30)
            year = target_date.year
            month = target_date.month
            
            # Get the first and last day of that month
            first_day = date(year, month, 1)
            if month == 12:
                last_day = date(year + 1, 1, 1) - timedelta(days=1)
            else:
                last_day = date(year, month + 1, 1) - timedelta(days=1)
            
            print(f"Creating {count} bookings for {first_day.strftime('%B %Y')}...")
            
            for _ in range(count):
                # Random day in the month (avoid weekends for more realism)
                day_offset = random.randint(0, (last_day - first_day).days)
                booking_date = first_day + timedelta(days=day_offset)
                
                # Skip weekends
                while booking_date.weekday() >= 5:
                    day_offset = random.randint(0, (last_day - first_day).days)
                    booking_date = first_day + timedelta(days=day_offset)
                
                # Random resource, user, time slot
                resource = random.choice(resources)
                user = random.choice(users)
                start_time, end_time = random.choice(time_slots)
                purpose = random.choice(purposes)
                status = random.choice(statuses)
                
                # Calculate cost
                hours = (datetime.combine(date.today(), end_time) - datetime.combine(date.today(), start_time)).seconds / 3600
                cost = hours * float(resource.hourly_rate)
                
                # Check for conflicts
                existing = Booking.query.filter(
                    Booking.resource_id == resource.id,
                    Booking.booking_date == booking_date,
                    Booking.start_time == start_time
                ).first()
                
                if existing:
                    continue  # Skip if conflict
                
                # Create the booking
                booking = Booking(
                    user_id=user.id,
                    resource_id=resource.id,
                    resource_system_id=resource.resource_system_id,
                    booking_date=booking_date,
                    start_time=start_time,
                    end_time=end_time,
                    purpose=purpose,
                    status=status,
                    cost=cost,
                    booking_type='hourly',
                    created_at=datetime.combine(booking_date, time(9, 0))
                )
                
                db.session.add(booking)
                bookings_created += 1
        
        db.session.commit()
        print(f"\nSuccessfully created {bookings_created} dummy bookings!")
        print("Analytics should now show more interesting data.")

if __name__ == '__main__':
    seed_dummy_bookings()
