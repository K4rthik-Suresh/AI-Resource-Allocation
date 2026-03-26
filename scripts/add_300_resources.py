from app import app, db
from models import Resource, ResourceSystem
from datetime import datetime

def add_300_resources():
    with app.app_context():
        # Get or create main facility
        facility = ResourceSystem.query.filter_by(name="Main Facility").first()
        if not facility:
            facility = ResourceSystem(
                name="Main Facility",
                description="Main Facility",
                location="Building A",
                capacity=5000,
                created_at=datetime.now()
            )
            db.session.add(facility)
            db.session.commit()
            print(f"[v0] Created facility with ID: {facility.id}")

        # Resource data with 300 items across 15 categories
        resources_data = [
            # Conference Rooms (50 resources)
            *[{"name": f"Conference Room {chr(65 + i % 26)}-{i // 26 + 1}", "category": "Conference Rooms", "capacity": 10 + (i % 5) * 5, "rate": 50 + (i % 5) * 10} for i in range(50)],
            
            # Meeting Rooms (40 resources)
            *[{"name": f"Meeting Room {i + 1}", "category": "Meeting Rooms", "capacity": 6 + (i % 4) * 3, "rate": 40 + (i % 4) * 8} for i in range(40)],
            
            # Training Rooms (35 resources)
            *[{"name": f"Training Room {i + 1}", "category": "Training Rooms", "capacity": 15 + (i % 5) * 5, "rate": 60 + (i % 5) * 10} for i in range(35)],
            
            # Research Labs (25 resources)
            *[{"name": f"Research Lab {i + 1}", "category": "Research Labs", "capacity": 8 + (i % 4) * 2, "rate": 100 + (i % 5) * 20} for i in range(25)],
            
            # Computer Labs (30 resources)
            *[{"name": f"Computer Lab {i + 1}", "category": "Computer Labs", "capacity": 20 + (i % 5) * 5, "rate": 80 + (i % 5) * 15} for i in range(30)],
            
            # Auditoriums (15 resources)
            *[{"name": f"Auditorium {i + 1}", "category": "Auditoriums", "capacity": 100 + (i % 5) * 50, "rate": 150 + (i % 5) * 30} for i in range(15)],
            
            # Executive Offices (25 resources)
            *[{"name": f"Executive Office {i + 1}", "category": "Executive Offices", "capacity": 2 + (i % 3), "rate": 70 + (i % 4) * 15} for i in range(25)],
            
            # Open Workspaces (20 resources)
            *[{"name": f"Open Workspace {i + 1}", "category": "Open Workspaces", "capacity": 30 + (i % 5) * 10, "rate": 50 + (i % 4) * 10} for i in range(20)],
            
            # Study Rooms (15 resources)
            *[{"name": f"Study Room {i + 1}", "category": "Study Rooms", "capacity": 4 + (i % 3) * 2, "rate": 25 + (i % 4) * 5} for i in range(15)],
            
            # Break Rooms (10 resources)
            *[{"name": f"Break Room {i + 1}", "category": "Break Rooms", "capacity": 8 + (i % 3) * 2, "rate": 20 + (i % 3) * 5} for i in range(10)],
            
            # Video Conference Rooms (20 resources)
            *[{"name": f"Video Conference Room {i + 1}", "category": "Video Conference Rooms", "capacity": 6 + (i % 4) * 3, "rate": 75 + (i % 4) * 15} for i in range(20)],
            
            # Specialized Equipment Rooms (15 resources)
            *[{"name": f"Equipment Room {i + 1}", "category": "Specialized Equipment", "capacity": 10 + (i % 3) * 5, "rate": 120 + (i % 4) * 20} for i in range(15)],
            
            # Storage Areas (10 resources)
            *[{"name": f"Storage Area {i + 1}", "category": "Storage", "capacity": 50, "rate": 30 + (i % 3) * 5} for i in range(10)],
            
            # Event Spaces (15 resources)
            *[{"name": f"Event Space {i + 1}", "category": "Event Spaces", "capacity": 50 + (i % 5) * 30, "rate": 100 + (i % 5) * 25} for i in range(15)],
            
            # Recreation Areas (10 resources)
            *[{"name": f"Recreation Area {i + 1}", "category": "Recreation Areas", "capacity": 20 + (i % 4) * 10, "rate": 40 + (i % 3) * 10} for i in range(10)],
            
            # Testing Centers (15 resources)
            *[{"name": f"Testing Center {i + 1}", "category": "Testing Centers", "capacity": 25 + (i % 4) * 5, "rate": 90 + (i % 4) * 15} for i in range(15)],
        ]

        print(f"[v0] Adding {len(resources_data)} resources to database...")
        
        # Check for existing resources
        existing_count = Resource.query.count()
        print(f"[v0] Existing resources: {existing_count}")
        
        # Add resources in batches
        for idx, resource_info in enumerate(resources_data):
            # Check if resource already exists
            existing = Resource.query.filter_by(name=resource_info["name"]).first()
            if not existing:
                resource = Resource(
                    name=resource_info["name"],
                    description=f"{resource_info['category']} - {resource_info['name']}",
                    resource_type=resource_info["category"].lower().replace(" ", "_"),
                    capacity=resource_info["capacity"],
                    hourly_rate=resource_info["rate"],
                    resource_system_id=facility.id,
                    location=f"Building A - {resource_info['category']}",
                    is_available=True,
                    created_at=datetime.now()
                )
                db.session.add(resource)
            
            # Commit in batches of 50
            if (idx + 1) % 50 == 0:
                db.session.commit()
                print(f"[v0] Inserted {idx + 1} resources...")

        # Final commit
        db.session.commit()
        
        # Print final count
        final_count = Resource.query.count()
        print(f"\n======================================================================")
        print(f"[v0] SUCCESS! Resources added to database!")
        print(f"======================================================================")
        print(f"\nTotal resources in system: {final_count}")
        print(f"Resources added in this session: {len(resources_data)}")
        
        # Count by category
        categories = {}
        for resource in Resource.query.all():
            cat = resource.resource_type or "Uncategorized"
            categories[cat] = categories.get(cat, 0) + 1
        
        print(f"\nResources by category:")
        for cat in sorted(categories.keys()):
            print(f"  - {cat}: {categories[cat]}")
        
        print(f"\n======================================================================")
        print(f"Now run: python app.py")
        print(f"Then go to: http://localhost:5000")
        print(f"Click 'Resources' to see all {final_count} resources!")
        print(f"======================================================================\n")

if __name__ == "__main__":
    add_300_resources()
