#!/usr/bin/env python3
"""
NLP Testing Script - Verify the NLP pipeline works correctly
"""

from app import app, db
from models import Resource, ResourceSystem
from ai_module import AIModule

# Initialize app context
with app.app_context():
    ai = AIModule()
    
    print("\n" + "="*70)
    print("NLP PIPELINE TEST")
    print("="*70)
    
    # Test cases
    test_queries = [
        "I need a conference room for 10 people tomorrow from 10am to 5pm",
        "Book a lab for 3 people next Friday afternoon",
        "Meeting room for 5 people, 2 days, starting today at 2pm",
        "auditorium for 100 people this weekend",
        "sports court tomorrow morning for 2 hours",
    ]
    
    for query in test_queries:
        print(f"\n[TEST] Query: '{query}'")
        print("-" * 70)
        
        try:
            result = ai.parse_nlp_booking(query)
            print(f"[OK] Parsed successfully")
            print(f"    - Resource type: {result.get('resource_type')}")
            print(f"    - Participants: {result.get('participants')}")
            print(f"    - Date: {result.get('date')}")
            print(f"    - Start time: {result.get('start_time')}")
            print(f"    - Duration days: {result.get('duration_days')}")
            print(f"    - Urgency: {result.get('urgency')}")
        except Exception as e:
            print(f"[ERROR] Failed to parse: {str(e)}")
            import traceback
            traceback.print_exc()
    
    print("\n" + "="*70)
    print("TESTING RESOURCE MATCHING")
    print("="*70)
    
    # Test resource matching
    resources = Resource.query.filter_by(is_available=True).limit(5).all()
    print(f"\n[INFO] Found {len(resources)} resources to test")
    
    for resource in resources:
        print(f"\n[TEST] Resource: {resource.name}")
        print("-" * 70)
        
        test_params = {
            'resource_type': 'room',
            'participants': 5,
            'date': None,
            'start_time': None,
        }
        
        try:
            score = ai.calculate_relevance_score(resource, test_params, [])
            reasons = ai.explain_match(resource, test_params)
            print(f"[OK] Relevance score: {score}")
            print(f"    - Match reasons: {', '.join(reasons)}")
        except Exception as e:
            print(f"[ERROR] Failed to score: {str(e)}")
    
    print("\n" + "="*70)
    print("NLP TESTS COMPLETE")
    print("="*70 + "\n")
