"""
================================================================================
AI ROUTES - NLP Booking Search Endpoints
================================================================================

DESCRIPTION:
    REST API endpoints for natural language booking search using AI module.

ROUTES:
    POST /ai/nlp-booking - Convert natural language to booking search
    GET /ai/features - AI features documentation page

NLP BOOKING SEARCH (/ai/nlp-booking):
    Input (JSON):
    {
        "query": "I need a conference room for 2 people from tomorrow 
                  for 5 days from 10am to 5pm"
    }
    
    Output (JSON):
    {
        "booking_params": {
            "resource_type": "room",
            "capacity": 2,
            "booking_date": "2026-02-23",
            "start_time": "10:00",
            "end_time": "17:00",
            "duration_days": 5,
            "purpose": "meeting"
        },
        "matching_resources": [
            {id, name, capacity, hourly_rate, available_slots, ...},
            ...
        ]
    }

================================================================================
"""

from flask import Blueprint, request, jsonify, session
from flask_login import login_required, current_user
from models import db, Resource
from ai.ai_module import AIModule
import logging
from datetime import datetime, timedelta

ai_bp = Blueprint('ai', __name__, url_prefix='/ai')
ai_module = AIModule()

logger = logging.getLogger(__name__)
logging.basicConfig(level=logging.INFO)

@ai_bp.route('/nlp-booking', methods=['POST', 'OPTIONS'])
@login_required
def nlp_booking():
    """Advanced NLP search endpoint"""
    if request.method == 'OPTIONS':
        response = jsonify({'status': 'ok'})
        response.headers.add('Access-Control-Allow-Origin', '*')
        response.headers.add('Access-Control-Allow-Headers', 'Content-Type')
        response.headers.add('Access-Control-Allow-Methods', 'POST')
        return response
    
    try:
        print("[v0] === NLP SEARCH STARTED ===")
        logger.info("[v0] NLP Search Request Received")
        
        if request.is_json:
            data = request.get_json()
            user_input = data.get('input', '').strip()
        else:
            user_input = request.form.get('input', '').strip()
        
        print(f"[v0] User Query: '{user_input}'")
        logger.info(f"[v0] Query: '{user_input}'")
        
        if not user_input:
            print("[v0] Empty query received")
            return jsonify({
                'success': False,
                'error': 'Please enter a search query',
                'matched_resources': []
            }), 200
        
        # Parse user input with AI
        print("[v0] Parsing query with AI...")
        booking_params = ai_module.parse_nlp_booking(user_input)
        print(f"[v0] Parsed Parameters: {booking_params}")
        logger.info(f"[v0] Parsed: {booking_params}")
        
        # Validate parsed parameters
        if not booking_params:
            booking_params = {}
        
        # Build query
        print("[v0] Building database query...")
        query = Resource.query.filter_by(is_available=True)
        
        # Safely get resource_type
        resource_type = booking_params.get('resource_type') if booking_params else None
        if resource_type:
            print(f"[v0] Filtering by type: {resource_type}")
            query = query.filter(
                Resource.resource_type.ilike(f"%{resource_type}%")
            )
        
        # Safely get participants
        participants = booking_params.get('participants') if booking_params else None
        if participants:
            print(f"[v0] Filtering by capacity >= {participants}")
            # Add reasonable upper limit - don't show resources more than 3x the requested capacity
            # This prevents showing 200+ seat halls for 25 person requests
            max_reasonable_capacity = participants * 3.5
            print(f"[v0] Capacity range: {participants} to {max_reasonable_capacity}")
            query = query.filter(
                Resource.capacity >= participants,
                Resource.capacity <= max_reasonable_capacity
            )
        
        resources = query.all()
        print(f"[v0] Found {len(resources)} matching resources")
        logger.info(f"[v0] Found {len(resources)} resources")
        
        # Fallback: if no results and both type + capacity were specified, retry without type filter
        fallback_active = False
        if not resources and resource_type and participants:
            print(f"[v0] No '{resource_type}' resources for {participants} people — falling back to capacity-only search")
            fallback_query = Resource.query.filter_by(is_available=True)
            max_reasonable_capacity = participants * 3.5
            fallback_query = fallback_query.filter(
                Resource.capacity >= participants,
                Resource.capacity <= max_reasonable_capacity
            )
            resources = fallback_query.all()
            if resources:
                fallback_active = True
                print(f"[v0] Fallback found {len(resources)} alternative resources")
        
        print("[v0] Scoring results...")
        results = []
        for resource in resources:
            score = ai_module.calculate_relevance_score(resource, booking_params, [])
            match_reasons = ai_module.explain_match(resource, booking_params)
            is_perfect = ai_module.is_perfect_match(resource, booking_params)
            
            # Add fallback reason if applicable
            if fallback_active:
                match_reasons.append(f"Different type ({resource.resource_type}), but fits your capacity needs")
            
            results.append({
                'resource': resource,
                'score': score,
                'match_reasons': match_reasons,
                'is_perfect': is_perfect
            })
        
        # Sort by: Perfect matches first (by score), then all others (by score)
        perfect_results = [r for r in results if r['is_perfect']]
        other_results = [r for r in results if not r['is_perfect']]
        perfect_results.sort(key=lambda x: x['score'], reverse=True)
        other_results.sort(key=lambda x: x['score'], reverse=True)
        results = perfect_results + other_results
        
        print(f"[v0] Found {len(perfect_results)} PERFECT matches and {len(other_results)} other matches")
        print(f"[v0] Top score: {results[0]['score'] if results else 0}")
        
        # Also show debug info about top 3
        print("[v0] Top 3 results:")
        for idx, item in enumerate(results[:3]):
            match_type = "PERFECT" if item['is_perfect'] else "RELEVANT"
            print(f"  {idx+1}. {item['resource'].name} ({match_type} - capacity: {item['resource'].capacity}, score: {item['score']:.1f})")
        
        # Format response
        print("[v0] Formatting response...")
        formatted = []
        for idx, item in enumerate(results):
            r = item['resource']
            formatted.append({
                'id': r.id,
                'name': r.name,
                'type': r.resource_type,
                'capacity': r.capacity,
                'location': r.location or 'Not specified',
                'hourly_rate': float(r.hourly_rate),
                'features': r.features or '',
                'match_reasons': item['match_reasons'],
                'is_best_match': item['is_perfect'],  # Now based on perfect match, not just rank
                'relevance_score': round(item['score'], 2),
                'match_type': 'BEST RESULT' if item['is_perfect'] else 'MOST RELEVANT'
            })
        
        response_data = {
            'success': True,
            'query': user_input,
            'booking_params': booking_params,
            'matched_resources': formatted,
            'total_matches': len(formatted),
            'fallback_active': fallback_active,
            'fallback_message': f"No \"{resource_type}\" resources available for {participants} people. Showing other resource types that can accommodate your group." if fallback_active else None
        }
        
        print(f"[v0] Returning {len(formatted)} results (fallback: {fallback_active})")
        print("[v0] === NLP SEARCH COMPLETE ===")
        logger.info(f"[v0] Success: {len(formatted)} results")
        
        return jsonify(response_data), 200
        
    except Exception as e:
        print(f"[v0] ERROR: {str(e)}")
        logger.error(f"[v0] Error: {str(e)}", exc_info=True)
        return jsonify({
            'success': False,
            'error': f'Search error: {str(e)}',
            'matched_resources': []
        }), 200

@ai_bp.route('/smart-suggestions', methods=['GET'])
@login_required
def smart_suggestions():
    """Get AI-powered resource suggestions based on user history"""
    try:
        # Get active system from session
        from flask import session
        active_system_id = session.get('active_system_id', 1)
        
        suggestions = ai_module.get_smart_suggestions(
            user_id=current_user.id,
            system_id=active_system_id
        )
        
        return jsonify({
            'success': True,
            'suggestions': suggestions
        }), 200
    except Exception as e:
        logger.error(f"[v0] Smart Suggestions Error: {str(e)}", exc_info=True)
        return jsonify({
            'success': False,
            'error': str(e),
            'suggestions': {
                'recent_resources': [],
                'popular_resources': [],
                'suggested_times': ['09:00', '14:00', '17:00'],
                'next_available_date': (datetime.now() + timedelta(days=1)).strftime('%Y-%m-%d')
            }
        }), 200

@ai_bp.route('/test', methods=['GET'])
def test():
    """Test endpoint to verify AI routes are accessible"""
    return jsonify({
        'status': 'ok',
        'message': 'AI routes are working',
        'endpoint': '/ai/test'
    }), 200
