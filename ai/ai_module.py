"""
================================================================================
AI MODULE - Groq-Powered Natural Language Processing for Booking
================================================================================

DESCRIPTION:
    Converts natural language text into structured booking requirements using 
    Groq's advanced LLM for intelligent understanding of booking requests.

KEY FEATURES:
    - Intelligent date extraction: "tomorrow", "next Monday", "8th February"
    - Smart time extraction: "10am", "2:30pm", "10:00 - 17:00", "morning"
    - Duration parsing: "5 days", "2 hours", "full day"
    - Resource type detection: "conference room", "lab", "auditorium"
    - Capacity extraction: "2 people", "10 seats"
    - Natural conversation understanding with Groq LLM
    - Context-aware booking interpretation

================================================================================
"""

import os
import re
import json
import logging
from datetime import datetime, timedelta
from models import Booking, Resource, db, BookingHistory
from sqlalchemy import func

logger = logging.getLogger(__name__)

# Try to import Groq, fall back gracefully if not available
try:
    from groq import Groq
    GROQ_AVAILABLE = True
except ImportError:
    GROQ_AVAILABLE = False
    logger.warning("[v0] Groq not installed. Install with: pip install groq")

class AIModule:
    """AI module using Groq LLM for advanced natural language processing"""
    
    _cached_valid_types_str = None
    
    @classmethod
    def invalidate_type_cache(cls, mapper=None, connection=None, target=None):
        """Invalidate the cached resource types string when resources change."""
        logger.info("[v0] Invalidating AI valid resource types cache")
        cls._cached_valid_types_str = None
        
    def __init__(self):
        """Initialize AI module with Groq client"""
        if GROQ_AVAILABLE:
            api_key = os.getenv('GROQ_API_KEY')
            if api_key:
                self.client = Groq(api_key=api_key)
                logger.info("[v0] Groq AI module initialized successfully")
            else:
                logger.warning("[v0] GROQ_API_KEY not set. Set environment variable to enable Groq NLP.")
                self.client = None
        else:
            self.client = None
        
        # Fallback patterns for when Groq is unavailable
        self.weekday_patterns = {
            'monday': 0, 'mon': 0,
            'tuesday': 1, 'tue': 1, 'tues': 1,
            'wednesday': 2, 'wed': 2,
            'thursday': 3, 'thu': 3, 'thur': 3, 'thurs': 3,
            'friday': 4, 'fri': 4,
            'saturday': 5, 'sat': 5,
            'sunday': 6, 'sun': 6,
        }
        
        self.date_expressions = {
            'today': 0, 'tonight': 0, 'tomorrow': 1, 'tommorow': 1,
            'tommorrow': 1, 'next day': 1, 'day after tomorrow': 2,
            'this week': 0, 'next week': 7,
        }
        
        self.time_expressions = {
            'morning': '09:00', 'noon': '12:00', 'afternoon': '14:00',
            'evening': '18:00', 'night': '19:00',
        }
    
    def parse_nlp_booking(self, user_input):
        """Parse booking request using Groq LLM or fallback to pattern matching"""
        if not user_input or not user_input.strip():
            logger.warning("[v0] Empty user input received")
            return {}
        
        if self.client:
            result = self._parse_with_groq(user_input)
        else:
            result = self._parse_with_patterns(user_input)
        
        # Ensure result is always a dict with required keys
        if not isinstance(result, dict):
            result = {}
        
        # Set defaults for missing keys
        # If start_date was extracted but date is missing, map it
        extracted_date = result.get('start_date') or result.get('date')
        if extracted_date:
            result['date'] = extracted_date
        else:
            result.setdefault('date', datetime.now().strftime('%Y-%m-%d'))  # Default to today
            
        result.setdefault('end_date', None)
        result.setdefault('start_time', None)
        result.setdefault('end_time', None)
        result.setdefault('resource_type', None)
        result.setdefault('duration', None)
        result.setdefault('duration_days', 1)
        result.setdefault('hours_per_day', None)
        result.setdefault('total_hours', None)
        result.setdefault('participants', None)
        result.setdefault('intent', None)
        result.setdefault('activity', None)
        result.setdefault('urgency', 'flexible')
        result.setdefault('preferences', None)
        result.setdefault('context', user_input)
        
        return result
    
    def parse_booking_query(self, user_input):
        """Main parser - delegates to Groq or pattern matching"""
        return self.parse_nlp_booking(user_input)
    
    def _parse_with_groq(self, user_input):
        """Parse booking request using Groq LLM"""
        try:
            # Fetch valid resource types from the database or cache
            try:
                if AIModule._cached_valid_types_str is None:
                    # Query distinct resource types to pass into prompt
                    type_records = Resource.query.with_entities(Resource.resource_type).distinct().all()
                    valid_types = [r[0] for r in type_records if r[0]]
                    AIModule._cached_valid_types_str = "/".join(valid_types) if valid_types else "room/lab/auditorium/studio/entertainment/outdoor"
                    logger.info(f"[v0] Initialized AI resource type cache: {AIModule._cached_valid_types_str}")
                
                valid_types_str = AIModule._cached_valid_types_str
            except Exception as e:
                logger.warning(f"[v0] Could not fetch resource types for prompt: {e}")
                valid_types_str = "room/lab/auditorium/studio/entertainment/outdoor"

            # Create structured prompt for Groq
            prompt = f"""Extract booking details from this request and return ONLY a valid JSON object (no markdown, no code blocks):

User Request: "{user_input}"

Today's date is: {datetime.now().strftime('%Y-%m-%d')}

Extract and return as JSON:
{{
    "start_date": "YYYY-MM-DD or null",
    "end_date": "YYYY-MM-DD or null",
    "start_time": "HH:MM or null",
    "end_time": "HH:MM or null",
    "duration_hours": number or null,
    "duration_days": number or null,
    "resource_type": "One of: {valid_types_str} or null",
    "participants": number or null,
    "purpose": "meeting/training/research/presentation or null",
    "urgency": "immediate/soon/flexible or null"
}}

Rules:
- Be conservative - return null if you cannot determine with confidence
- "Tomorrow" means {(datetime.now() + timedelta(days=1)).strftime('%Y-%m-%d')}
- Recognize dates in ANY of these formats and always convert to YYYY-MM-DD:
  * Formal American: "March 15, 2026"
  * Formal British: "15 March 2026"
  * Ordinal: "15th March 2026" or "March 15th, 2026"
  * Numerical DMY (British): "15/03/2026", "15.03.26", "15-03-2026"
  * ISO 8601: "2026-03-15"
  * Relative: "tomorrow", "next Monday", "in 3 days"
- For 2-digit years, assume 2000s (e.g., 26 = 2026)
- Time ranges like "10am to 5pm" should set both start_time and end_time
- Infer duration from time range if provided
- Duration in hours should be decimal (e.g., 1.5, 2.5)
- For multi-day bookings, set duration_days
- Group size/people helps determine resource type and capacity
- IMPORTANT: Classify the requested space exactly into ONE of the provided available resource types. For example, map synonyms like 'hall' or 'theater' directly to 'auditorium' (or whatever is applicable in {valid_types_str}), and 'workspace' or 'boardroom' to 'room'.

Return ONLY the JSON object, nothing else."""

            message = self.client.chat.completions.create(
                model="llama-3.3-70b-versatile",
                messages=[
                    {
                        "role": "user",
                        "content": prompt
                    }
                ],
                temperature=0.3,
                max_tokens=500
            )
            
            # Parse Groq response
            response_text = message.choices[0].message.content.strip()
            logger.info(f"[v0] Groq raw response: {response_text}")
            
            # Remove markdown code blocks if present
            if response_text.startswith('```'):
                response_text = re.sub(r'```json?\n?', '', response_text)
                response_text = re.sub(r'\n?```', '', response_text)
            
            response_text = response_text.strip()
            
            # Parse JSON response
            parsed = json.loads(response_text)
            
            # Convert to booking params format
            booking_params = {
                'start_date': parsed.get('start_date'),
                'end_date': parsed.get('end_date'),
                'start_time': parsed.get('start_time'),
                'end_time': parsed.get('end_time'),
                'resource_type': parsed.get('resource_type'),
                'duration': parsed.get('duration_hours'),
                'duration_days': parsed.get('duration_days') or 1,
                'participants': parsed.get('participants'),
                'intent': parsed.get('purpose'),
                'activity': parsed.get('purpose'),
                'urgency': parsed.get('urgency') or 'flexible',
                'preferences': None,
                'context': user_input
            }
            
            logger.info(f"[v0] Groq parsed booking: {booking_params}")
            return booking_params
            
        except json.JSONDecodeError as e:
            logger.error(f"[v0] JSON parsing error from Groq: {e}. Response was: {response_text}")
            return self._parse_with_patterns(user_input)
        except Exception as e:
            logger.error(f"[v0] Groq parsing error: {e}. Falling back to pattern matching.")
            return self._parse_with_patterns(user_input)
    
    def _parse_with_patterns(self, user_input):
        """Fallback pattern-based parsing"""
        text_lower = user_input.lower()
        
        # Extract time range first (e.g., "10am to 5pm")
        time_range = self._extract_time_range(text_lower)
        
        # Extract date range (start and end dates)
        date_range = self._extract_date_range(text_lower)
        
        # Extract start date - if not found, default to TODAY
        start_date = date_range['start'] if date_range else self._extract_date_pattern(text_lower)
        if not start_date:
            start_date = datetime.now().strftime('%Y-%m-%d')
            print(f"[v0] No start date found, defaulting to today: {start_date}")
        
        # Calculate duration in hours per day from time range
        hours_per_day = None
        if time_range and time_range.get('start') and time_range.get('end'):
            start_time_obj = datetime.strptime(time_range['start'], '%H:%M')
            end_time_obj = datetime.strptime(time_range['end'], '%H:%M')
            hours_per_day = (end_time_obj - start_time_obj).total_seconds() / 3600
            print(f"[v0] Calculated hours per day: {hours_per_day}")
        
        # Calculate total duration in days
        duration_days = 1
        end_date = None
        
        if date_range:
            duration_days = date_range['days']
            end_date = date_range['end']
            print(f"[v0] Date range found: {duration_days} days from {start_date} to {end_date}")
        elif self._extract_duration_days(text_lower):
            duration_days = self._extract_duration_days(text_lower)
            print(f"[v0] Duration days extracted: {duration_days}")
        
        # Calculate total hours
        total_hours = (hours_per_day or 1) * duration_days if hours_per_day else None
        
        booking_params = {
            'start_date': start_date,
            'end_date': end_date,
            'start_time': time_range['start'] if time_range else self._extract_time_pattern(text_lower),
            'end_time': time_range['end'] if time_range else None,
            'resource_type': self._extract_resource_type(text_lower),
            'duration': self._extract_duration_pattern(text_lower),
            'duration_days': duration_days,
            'hours_per_day': hours_per_day,
            'total_hours': total_hours,
            'participants': self._extract_participants(text_lower),
            'intent': None,
            'activity': None,
            'urgency': 'flexible',
            'preferences': None,
            'context': user_input
        }
        
        logger.info(f"[v0] Pattern-based parsed booking: date={start_date}, end_date={end_date}, duration_days={duration_days}, hours_per_day={hours_per_day}")
        return booking_params
    
    def _extract_date_pattern(self, text):
        """Pattern-based date extraction - supports ISO 8601, numerical DMY, formal, ordinal, relative dates, and weekday names"""
        # First check relative date expressions
        for expression, days_offset in self.date_expressions.items():
            if expression in text:
                target_date = datetime.now() + timedelta(days=days_offset)
                return target_date.strftime('%Y-%m-%d')
        
        # === Weekday name patterns: "next monday", "this friday", "on wednesday", bare "monday" ===
        # Pattern: "next monday", "next friday", etc. — always jumps to the NEXT occurrence (1-7 days ahead)
        next_weekday_match = re.search(r'next\s+(monday|tuesday|wednesday|thursday|friday|saturday|sunday|mon|tue|tues|wed|thu|thur|thurs|fri|sat|sun)\b', text, re.IGNORECASE)
        if next_weekday_match:
            weekday_str = next_weekday_match.group(1).lower()
            if weekday_str in self.weekday_patterns:
                target_weekday = self.weekday_patterns[weekday_str]
                today = datetime.now()
                days_ahead = target_weekday - today.weekday()
                if days_ahead <= 0:
                    days_ahead += 7  # Always go to NEXT week's occurrence
                target_date = today + timedelta(days=days_ahead)
                print(f"[v0] Extracted 'next {weekday_str}' date: {target_date.strftime('%Y-%m-%d')}")
                return target_date.strftime('%Y-%m-%d')
        
        # Pattern: "this monday", "this friday", "on monday", or bare "monday" — picks the upcoming occurrence
        this_weekday_match = re.search(r'(?:this|on|for)\s+(monday|tuesday|wednesday|thursday|friday|saturday|sunday|mon|tue|tues|wed|thu|thur|thurs|fri|sat|sun)\b', text, re.IGNORECASE)
        if this_weekday_match:
            weekday_str = this_weekday_match.group(1).lower()
            if weekday_str in self.weekday_patterns:
                target_weekday = self.weekday_patterns[weekday_str]
                today = datetime.now()
                days_ahead = target_weekday - today.weekday()
                if days_ahead < 0:
                    days_ahead += 7  # Go to next week if the day already passed
                target_date = today + timedelta(days=days_ahead)
                print(f"[v0] Extracted 'this/on {weekday_str}' date: {target_date.strftime('%Y-%m-%d')}")
                return target_date.strftime('%Y-%m-%d')
        
        # Pattern: bare weekday name "monday", "friday" (without next/this/on prefix)
        # Only match if it's a standalone weekday reference, not part of another matched pattern
        bare_weekday_match = re.search(r'\b(monday|tuesday|wednesday|thursday|friday|saturday|sunday)\b', text, re.IGNORECASE)
        if bare_weekday_match:
            weekday_str = bare_weekday_match.group(1).lower()
            if weekday_str in self.weekday_patterns:
                target_weekday = self.weekday_patterns[weekday_str]
                today = datetime.now()
                days_ahead = target_weekday - today.weekday()
                if days_ahead <= 0:
                    days_ahead += 7  # Go to next occurrence
                target_date = today + timedelta(days=days_ahead)
                print(f"[v0] Extracted bare weekday '{weekday_str}' date: {target_date.strftime('%Y-%m-%d')}")
                return target_date.strftime('%Y-%m-%d')
        
        # "in 3 days" pattern
        match = re.search(r'in\s+(\d+)\s+days?', text)
        if match:
            days = int(match.group(1))
            target_date = datetime.now() + timedelta(days=days)
            return target_date.strftime('%Y-%m-%d')
        
        # --- ISO 8601: "2026-03-15" (Year-Month-Day) ---
        match = re.search(r'(\d{4})-(\d{2})-(\d{2})', text)
        if match:
            try:
                year, month, day = int(match.group(1)), int(match.group(2)), int(match.group(3))
                parsed = datetime(year, month, day).strftime('%Y-%m-%d')
                print(f"[v0] Extracted ISO 8601 date: {parsed}")
                return parsed
            except ValueError:
                pass
        
        # --- Ordinal with year: "15th March 2026" or "March 15th, 2026" ---
        # Day-first ordinal with year: "15th March 2026"
        match = re.search(r'(\d{1,2})(?:st|nd|rd|th)\s+([a-z]+)\s+(\d{4})', text, re.IGNORECASE)
        if match:
            try:
                day, month_str, year = int(match.group(1)), match.group(2), int(match.group(3))
                parsed = self._parse_month_day(month_str, day, year)
                if parsed:
                    print(f"[v0] Extracted ordinal+year date: {parsed}")
                    return parsed
            except (ValueError, IndexError):
                pass
        
        # Month-first ordinal with year: "March 15th, 2026"
        match = re.search(r'([a-z]+)\s+(\d{1,2})(?:st|nd|rd|th),?\s+(\d{4})', text, re.IGNORECASE)
        if match:
            try:
                month_str, day, year = match.group(1), int(match.group(2)), int(match.group(3))
                parsed = self._parse_month_day(month_str, day, year)
                if parsed:
                    print(f"[v0] Extracted month-ordinal+year date: {parsed}")
                    return parsed
            except (ValueError, IndexError):
                pass
        
        # --- Formal with year (American): "March 15, 2026" ---
        match = re.search(r'([a-z]+)\s+(\d{1,2}),?\s+(\d{4})', text, re.IGNORECASE)
        if match:
            try:
                month_str, day, year = match.group(1), int(match.group(2)), int(match.group(3))
                parsed = self._parse_month_day(month_str, day, year)
                if parsed:
                    print(f"[v0] Extracted formal American date: {parsed}")
                    return parsed
            except (ValueError, IndexError):
                pass
        
        # --- Formal with year (British): "15 March 2026" ---
        match = re.search(r'(\d{1,2})\s+([a-z]+)\s+(\d{4})', text, re.IGNORECASE)
        if match:
            try:
                day, month_str, year = int(match.group(1)), match.group(2), int(match.group(3))
                parsed = self._parse_month_day(month_str, day, year)
                if parsed:
                    print(f"[v0] Extracted formal British date: {parsed}")
                    return parsed
            except (ValueError, IndexError):
                pass
        
        # --- Numerical DMY with slash: "15/03/2026" or "15/03/26" ---
        match = re.search(r'(\d{1,2})/(\d{1,2})/(\d{2,4})', text)
        if match:
            try:
                day, month, year = int(match.group(1)), int(match.group(2)), int(match.group(3))
                if year < 100:
                    year += 2000  # Convert 2-digit year: 26 -> 2026
                parsed = datetime(year, month, day).strftime('%Y-%m-%d')
                print(f"[v0] Extracted numerical slash date: {parsed}")
                return parsed
            except ValueError:
                pass
        
        # --- Numerical DMY with dot: "15.03.2026" or "15.03.26" ---
        match = re.search(r'(\d{1,2})\.(\d{1,2})\.(\d{2,4})', text)
        if match:
            try:
                day, month, year = int(match.group(1)), int(match.group(2)), int(match.group(3))
                if year < 100:
                    year += 2000
                parsed = datetime(year, month, day).strftime('%Y-%m-%d')
                print(f"[v0] Extracted numerical dot date: {parsed}")
                return parsed
            except ValueError:
                pass
        
        # --- Numerical DMY with dash: "15-03-2026" ---
        # (Only match DD-MM-YYYY, not YYYY-MM-DD which is handled above as ISO)
        match = re.search(r'(\d{1,2})-(\d{1,2})-(\d{4})', text)
        if match:
            try:
                day, month, year = int(match.group(1)), int(match.group(2)), int(match.group(3))
                if day <= 31 and month <= 12:  # Validate it's DMY not YMD
                    parsed = datetime(year, month, day).strftime('%Y-%m-%d')
                    print(f"[v0] Extracted numerical dash date: {parsed}")
                    return parsed
            except ValueError:
                pass
        
        # --- Ordinal dates without year (existing): "15th march", "march 15th" ---
        ordinal_patterns = [
            # "15th march" - day with ordinal, then month
            r'(\d{1,2})(?:st|nd|rd|th)\s+([a-z]+)',
            # "march 15th" - month then day with ordinal
            r'([a-z]+)\s+(\d{1,2})(?:st|nd|rd|th)',
            # "15 march" - day without ordinal, then month
            r'(\d{1,2})\s+([a-z]+)(?:\s|$)',
            # "march 15" - month then day without ordinal
            r'([a-z]+)\s+(\d{1,2})(?:\s|$)',
        ]
        
        for pattern_idx, pattern in enumerate(ordinal_patterns):
            match = re.search(pattern, text, re.IGNORECASE)
            if match:
                try:
                    groups = match.groups()
                    
                    if pattern_idx in (0, 2):  # day first, then month
                        day = int(groups[0])
                        month_str = groups[1]
                    else:  # month first, then day
                        month_str = groups[0]
                        day = int(groups[1])
                    
                    current_year = datetime.now().year
                    parsed_date = self._parse_month_day(month_str, day, current_year)
                    if parsed_date:
                        print(f"[v0] Extracted ordinal date: {parsed_date} from pattern: {pattern}")
                        return parsed_date
                except (ValueError, IndexError):
                    continue
        
        return None
    
    def _extract_date_range(self, text):
        """Extract date range for multi-day bookings - handles 'from', 'till', 'until', 'through', 'to' patterns"""
        print(f"[v0] Extracting date range from: {text}")
        
        # === ISO 8601 range: "from 2026-03-15 to 2026-03-20" ===
        iso_range_pattern = r'(?:from\s+)?(\d{4})-(\d{2})-(\d{2})\s+(?:to|till|until|through)\s+(\d{4})-(\d{2})-(\d{2})'
        match = re.search(iso_range_pattern, text, re.IGNORECASE)
        if match:
            try:
                start_date = datetime(int(match.group(1)), int(match.group(2)), int(match.group(3))).strftime('%Y-%m-%d')
                end_date = datetime(int(match.group(4)), int(match.group(5)), int(match.group(6))).strftime('%Y-%m-%d')
                days_diff = (datetime.strptime(end_date, '%Y-%m-%d') - datetime.strptime(start_date, '%Y-%m-%d')).days + 1
                print(f"[v0] Matched ISO 8601 date range: {start_date} to {end_date}")
                return {'start': start_date, 'end': end_date, 'days': max(1, days_diff)}
            except ValueError as e:
                print(f"[v0] Error parsing ISO range: {e}")
        
        # === Numerical DMY range with slash: "from 15/03/2026 to 20/03/2026" ===
        num_slash_range = r'(?:from\s+)?(\d{1,2})/(\d{1,2})/(\d{2,4})\s+(?:to|till|until|through)\s+(\d{1,2})/(\d{1,2})/(\d{2,4})'
        match = re.search(num_slash_range, text, re.IGNORECASE)
        if match:
            try:
                sd, sm, sy = int(match.group(1)), int(match.group(2)), int(match.group(3))
                ed, em, ey = int(match.group(4)), int(match.group(5)), int(match.group(6))
                if sy < 100: sy += 2000
                if ey < 100: ey += 2000
                start_date = datetime(sy, sm, sd).strftime('%Y-%m-%d')
                end_date = datetime(ey, em, ed).strftime('%Y-%m-%d')
                days_diff = (datetime.strptime(end_date, '%Y-%m-%d') - datetime.strptime(start_date, '%Y-%m-%d')).days + 1
                print(f"[v0] Matched numerical slash date range: {start_date} to {end_date}")
                return {'start': start_date, 'end': end_date, 'days': max(1, days_diff)}
            except ValueError as e:
                print(f"[v0] Error parsing numerical slash range: {e}")
        
        # === Numerical DMY range with dot: "from 15.03.2026 to 20.03.2026" ===
        num_dot_range = r'(?:from\s+)?(\d{1,2})\.(\d{1,2})\.(\d{2,4})\s+(?:to|till|until|through)\s+(\d{1,2})\.(\d{1,2})\.(\d{2,4})'
        match = re.search(num_dot_range, text, re.IGNORECASE)
        if match:
            try:
                sd, sm, sy = int(match.group(1)), int(match.group(2)), int(match.group(3))
                ed, em, ey = int(match.group(4)), int(match.group(5)), int(match.group(6))
                if sy < 100: sy += 2000
                if ey < 100: ey += 2000
                start_date = datetime(sy, sm, sd).strftime('%Y-%m-%d')
                end_date = datetime(ey, em, ed).strftime('%Y-%m-%d')
                days_diff = (datetime.strptime(end_date, '%Y-%m-%d') - datetime.strptime(start_date, '%Y-%m-%d')).days + 1
                print(f"[v0] Matched numerical dot date range: {start_date} to {end_date}")
                return {'start': start_date, 'end': end_date, 'days': max(1, days_diff)}
            except ValueError as e:
                print(f"[v0] Error parsing numerical dot range: {e}")
        
        # === Ordinal/named month range: "from 15th march to 20th march" ===
        from_to_pattern = r'from\s+(\d{1,2})(?:st|nd|rd|th)?\s+([a-z]+)\s+(?:to|till|until|through)\s+(\d{1,2})(?:st|nd|rd|th)?\s+([a-z]+)'
        match = re.search(from_to_pattern, text, re.IGNORECASE)
        
        if match:
            try:
                start_day = int(match.group(1))
                start_month = match.group(2)
                end_day = int(match.group(3))
                end_month = match.group(4)
                current_year = datetime.now().year
                
                start_date = self._parse_month_day(start_month, start_day, current_year)
                end_date = self._parse_month_day(end_month, end_day, current_year)
                
                if start_date and end_date:
                    print(f"[v0] Matched 'from...to' date range: {start_date} to {end_date}")
                    start_dt = datetime.strptime(start_date, '%Y-%m-%d')
                    end_dt = datetime.strptime(end_date, '%Y-%m-%d')
                    days_diff = (end_dt - start_dt).days + 1  # +1 to include both start and end dates
                    
                    return {
                        'start': start_date,
                        'end': end_date,
                        'days': max(1, days_diff)
                    }
            except Exception as e:
                print(f"[v0] Error parsing 'from...to' date range: {e}")
        
        # First extract start date using existing method, default to today if not found
        start_date = self._extract_date_pattern(text)
        if not start_date:
            start_date = datetime.now().strftime('%Y-%m-%d')
            print(f"[v0] No explicit start date found, defaulting to today: {start_date}")
        
        # Now look for end date indicators
        # Patterns to match end dates: "till DATE", "until DATE", "through DATE", "to DATE", "till the DATE"
        end_patterns = [
            # "till 20th march" - ordinal day followed by month name (with ordinal suffix)
            r'(?:till|until|through|to)\s+(?:the\s+)?(\d{1,2})(?:st|nd|rd|th)\s+([a-z]+)',
            # "till 20 march" - day followed by month (without ordinal suffix)
            r'(?:till|until|through|to)\s+(?:the\s+)?(\d{1,2})\s+([a-z]+)',
            # "till march 20th" - month followed by ordinal day
            r'(?:till|until|through|to)\s+(?:the\s+)?([a-z]+)\s+(\d{1,2})(?:st|nd|rd|th)',
            # "till march 20" - month followed by day (without ordinal)
            r'(?:till|until|through|to)\s+(?:the\s+)?([a-z]+)\s+(\d{1,2})',
            # "till 2026-02-28" (ISO)
            r'(?:till|until|through|to)\s+(\d{4})-(\d{2})-(\d{2})',
            # "till 28/02/2026" (numerical slash)
            r'(?:till|until|through|to)\s+(\d{1,2})/(\d{1,2})/(\d{2,4})',
            # "till 28.02.2026" (numerical dot)
            r'(?:till|until|through|to)\s+(\d{1,2})\.(\d{1,2})\.(\d{2,4})',
            # "till next friday", "till next monday"
            r'(?:till|until|through|to)\s+(?:next|this)\s+([a-z]+)',
            # "till in 5 days", "till in 2 weeks"
            r'(?:till|until|through|to)\s+in\s+(\d+)\s+(?:days|weeks)',
        ]
        
        end_date = None
        
        for i, pattern in enumerate(end_patterns):
            match = re.search(pattern, text, re.IGNORECASE)
            if match:
                print(f"[v0] Matched end date pattern {i}: {pattern}")
                print(f"[v0] Match groups: {match.groups()}")
                
                try:
                    groups = match.groups()
                    
                    # Pattern 0: "till 20th march" - day with ordinal, then month
                    if i == 0:
                        day = int(groups[0])
                        month_str = groups[1]
                        current_year = datetime.now().year
                        end_date = self._parse_month_day(month_str, day, current_year)
                    
                    # Pattern 1: "till 20 march" - day without ordinal, then month
                    elif i == 1:
                        day = int(groups[0])
                        month_str = groups[1]
                        current_year = datetime.now().year
                        end_date = self._parse_month_day(month_str, day, current_year)
                    
                    # Pattern 2: "till march 20th" - month then day with ordinal
                    elif i == 2:
                        month_str = groups[0]
                        day = int(groups[1])
                        current_year = datetime.now().year
                        end_date = self._parse_month_day(month_str, day, current_year)
                    
                    # Pattern 3: "till march 20" - month then day without ordinal
                    elif i == 3:
                        month_str = groups[0]
                        day = int(groups[1])
                        current_year = datetime.now().year
                        end_date = self._parse_month_day(month_str, day, current_year)
                    
                    # Pattern 4: "till 2026-02-28" (ISO)
                    elif i == 4:
                        year = int(groups[0])
                        month = int(groups[1])
                        day = int(groups[2])
                        end_date = datetime(year, month, day).strftime('%Y-%m-%d')
                    
                    # Pattern 5: "till 28/02/2026" (numerical slash)
                    elif i == 5:
                        day = int(groups[0])
                        month = int(groups[1])
                        year = int(groups[2])
                        if year < 100:
                            year += 2000
                        end_date = datetime(year, month, day).strftime('%Y-%m-%d')
                    
                    # Pattern 6: "till 28.02.2026" (numerical dot)
                    elif i == 6:
                        day = int(groups[0])
                        month = int(groups[1])
                        year = int(groups[2])
                        if year < 100:
                            year += 2000
                        end_date = datetime(year, month, day).strftime('%Y-%m-%d')
                    
                    # Pattern 7: "till next friday"
                    elif i == 7:
                        weekday_str = groups[0].lower()
                        if weekday_str in self.weekday_patterns:
                            weekday = self.weekday_patterns[weekday_str]
                            today = datetime.now()
                            days_ahead = weekday - today.weekday()
                            if days_ahead <= 0:
                                days_ahead += 7
                            end_date = (today + timedelta(days=days_ahead)).strftime('%Y-%m-%d')
                    
                    # Pattern 8: "till in 5 days/weeks"
                    elif i == 8:
                        amount = int(groups[0])
                        if 'week' in text[match.start():match.end()]:
                            days = amount * 7
                        else:
                            days = amount
                        end_date = (datetime.now() + timedelta(days=days)).strftime('%Y-%m-%d')
                    
                    if end_date:
                        print(f"[v0] Extracted end date: {end_date}")
                        # Calculate days between start and end
                        start_dt = datetime.strptime(start_date, '%Y-%m-%d')
                        end_dt = datetime.strptime(end_date, '%Y-%m-%d')
                        days_diff = (end_dt - start_dt).days + 1  # +1 to include both start and end dates
                        
                        print(f"[v0] Date range calculated: {start_date} to {end_date}, {days_diff} days")
                        
                        return {
                            'start': start_date,
                            'end': end_date,
                            'days': max(1, days_diff)
                        }
                
                except Exception as e:
                    print(f"[v0] Error parsing end date: {e}")
                    import traceback
                    traceback.print_exc()
                    continue
        
        print(f"[v0] No end date found, using start date only")
        return None
    
    def _parse_month_day(self, month_str, day, year):
        """Parse month string and day to date"""
        month_map = {
            'january': 1, 'february': 2, 'march': 3, 'april': 4,
            'may': 5, 'june': 6, 'july': 7, 'august': 8,
            'september': 9, 'october': 10, 'november': 11, 'december': 12,
            'jan': 1, 'feb': 2, 'mar': 3, 'apr': 4, 'may': 5, 'jun': 6,
            'jul': 7, 'aug': 8, 'sep': 9, 'oct': 10, 'nov': 11, 'dec': 12
        }
        
        month_lower = month_str.lower()
        if month_lower in month_map:
            month = month_map[month_lower]
            try:
                date_obj = datetime(year, month, day)
                return date_obj.strftime('%Y-%m-%d')
            except ValueError:
                print(f"[v0] Invalid date: {year}-{month}-{day}")
                return None
        
        return None
    
    def _extract_time_pattern(self, text):
        """Pattern-based time extraction - handles 10am, 2:30pm, 10 am, etc."""
        # First check time expressions (morning, afternoon, etc.)
        for expression, time_value in self.time_expressions.items():
            if expression in text:
                print(f"[v0] Found time expression: {expression} -> {time_value}")
                return time_value
        
        # Handle time formats: "10am", "10:30pm", "10 am", "2:30 pm", etc.
        # Match: 1-2 digits, optional colon+minutes, optional spaces, optional am/pm
        patterns = [
            # "10am" or "10AM"
            r'(\d{1,2})\s*(?::(\d{2}))?\s*(am|pm)',
            # "10 am" with space
            r'(\d{1,2})\s+(?::(\d{2}))?\s*(am|pm)',
            # "10:30" in 24-hour format (no am/pm)
            r'(\d{1,2}):(\d{2})(?:\s+(am|pm))?',
        ]
        
        for pattern in patterns:
            match = re.search(pattern, text, re.IGNORECASE)
            if match:
                hour = int(match.group(1))
                minute = int(match.group(2)) if match.group(2) else 0
                meridiem = match.group(3).lower() if match.group(3) else None
                
                print(f"[v0] Matched time: hour={hour}, minute={minute}, meridiem={meridiem}")
                
                # Validate hour is reasonable (1-12 for 12-hour, 0-23 for 24-hour)
                if meridiem:
                    if not (1 <= hour <= 12):
                        continue  # Invalid 12-hour format
                    
                    if meridiem == 'pm' and hour != 12:
                        hour += 12
                    elif meridiem == 'am' and hour == 12:
                        hour = 0
                else:
                    # Assume 24-hour format if no meridiem
                    if not (0 <= hour <= 23):
                        continue  # Invalid 24-hour format
                
                result = f"{hour:02d}:{minute:02d}"
                print(f"[v0] Extracted time: {result}")
                return result
        
        print(f"[v0] No time pattern matched in: {text}")
        return None
    
    def _extract_time_range(self, text):
        """Extract time range like '10am to 5pm' or '10:00 - 17:00'"""
        # Pattern: "10am to 5pm" or "10am - 5pm"
        range_pattern = r'(\d{1,2}):?(\d{2})?\s*(am|pm)?\s*(?:to|-)\s*(\d{1,2}):?(\d{2})?\s*(am|pm)?'
        match = re.search(range_pattern, text, re.IGNORECASE)
        
        if match:
            print(f"[v0] Found time range pattern")
            
            start_hour = int(match.group(1))
            start_minute = int(match.group(2)) if match.group(2) else 0
            start_meridiem = match.group(3).lower() if match.group(3) else None
            
            end_hour = int(match.group(4))
            end_minute = int(match.group(5)) if match.group(5) else 0
            end_meridiem = match.group(6).lower() if match.group(6) else None
            
            # Handle start time
            if start_meridiem:
                if start_meridiem == 'pm' and start_hour != 12:
                    start_hour += 12
                elif start_meridiem == 'am' and start_hour == 12:
                    start_hour = 0
            
            # Handle end time
            if end_meridiem:
                if end_meridiem == 'pm' and end_hour != 12:
                    end_hour += 12
                elif end_meridiem == 'am' and end_hour == 12:
                    end_hour = 0
            else:
                # If end time has no meridiem but start does, assume same meridiem
                if start_meridiem and start_meridiem == 'pm' and end_hour < 12:
                    end_hour += 12
            
            start_time = f"{start_hour:02d}:{start_minute:02d}"
            end_time = f"{end_hour:02d}:{end_minute:02d}"
            
            print(f"[v0] Extracted time range: {start_time} to {end_time}")
            return {'start': start_time, 'end': end_time}
        
        return None
    
    def _extract_duration_pattern(self, text):
        """Pattern-based duration extraction in hours"""
        # "2 hours" pattern
        match = re.search(r'(\d+)\s*hours?', text)
        if match:
            return int(match.group(1))
        
        # "30 minutes" pattern
        match = re.search(r'(\d+)\s*minutes?', text)
        if match:
            return int(match.group(1)) / 60
        
        # "full day" = 8 hours
        if 'full day' in text or 'whole day' in text:
            return 8
        
        # Default 1 hour
        return 1
    
    def _extract_duration_days(self, text):
        """Extract duration in days"""
        # "5 days" pattern
        match = re.search(r'(\d+)\s*days?', text)
        if match:
            return int(match.group(1))
        
        if 'full day' in text or 'whole day' in text:
            return 1
        
        return None
    
    def _extract_resource_type(self, text):
        """Extract resource type - recognizes hall, room, lab, sports, equipment"""
        text_lower = text.lower()
        
        # Check for hall first (before general conference/meeting terms)
        if any(word in text_lower for word in ['hall', 'ballroom', 'banquet', 'grand hall', 'event hall']):
            return 'hall'
        
        # Conference/meeting rooms
        if any(word in text_lower for word in ['conference', 'meeting', 'board', 'boardroom']):
            return 'room'
        
        # Labs and research spaces
        if any(word in text_lower for word in ['lab', 'laboratory', 'research']):
            return 'lab'
        
        # Auditoriums and theaters
        if any(word in text_lower for word in ['auditorium', 'theater', 'theatre', 'lecture hall']):
            return 'auditorium'
        
        # Sports facilities
        if any(word in text_lower for word in ['court', 'sports', 'field', 'badminton', 'tennis', 'gym']):
            return 'sports'
        
        # Equipment and tools
        if any(word in text_lower for word in ['equipment', 'device', 'tool', 'device']):
            return 'equipment'
        
        return 'room'  # Default to room
    
    def _extract_participants(self, text):
        """Extract number of participants - handles natural expressions like 'for 25', '25 people', 'group of 20', etc."""
        text_lower = text.lower()
        
        # Common patterns: "for 25 people", "25 people", "for 25 persons"
        match = re.search(r'(?:for\s+)?(\d+)\s*(?:people|person|participants?|attendees?|persons?)', text)
        if match:
            return int(match.group(1))
        
        # "group of N" pattern
        match = re.search(r'group\s+of\s+(\d+)', text)
        if match:
            return int(match.group(1))
        
        # "for N" pattern (without 'people' specified)
        match = re.search(r'for\s+(\d+)(?:\s|$)', text)
        if match:
            return int(match.group(1))
        
        # "N seats/capacity" pattern
        match = re.search(r'(\d+)\s*(?:seats?|capacity)', text)
        if match:
            return int(match.group(1))
        
        # "accommodate/seat N" pattern
        match = re.search(r'(?:accommodate|seat)\s+(?:up\s+to\s+)?(\d+)', text)
        if match:
            return int(match.group(1))
        
        return None
    
    def get_smart_suggestions(self, user_id, system_id):
        """Get smart booking suggestions - random by default, optimized if bookings exist"""
        try:
            import random
            
            # Get user's recent bookings to find similar resources
            recent_bookings = Booking.query.filter_by(
                user_id=user_id,
                resource_system_id=system_id
            ).order_by(Booking.created_at.desc()).limit(10).all()
            
            # If user has bookings, recommend similar resources
            if recent_bookings:
                print(f"[v0] User has {len(recent_bookings)} bookings, finding similar resources...")
                
                # Get types and features from recent bookings
                booked_types = set()
                booked_ids = set()
                
                for booking in recent_bookings:
                    if booking.resource:
                        booked_types.add(booking.resource.resource_type)
                        booked_ids.add(booking.resource.id)
                
                # Query for similar resources (same type but not already booked)
                similar_resources = Resource.query.filter(
                    Resource.resource_system_id == system_id,
                    Resource.resource_type.in_(list(booked_types)) if booked_types else True,
                    Resource.is_available == True,
                    ~Resource.id.in_(booked_ids) if booked_ids else True
                ).limit(9).all()
                
                # If we found similar resources, add reason
                if similar_resources:
                    suggestions = []
                    for resource in similar_resources:
                        resource.reason = f"Similar to your recent bookings"
                        suggestions.append(resource)
                    
                    print(f"[v0] Recommending {len(suggestions)} similar resources")
                    return suggestions
            
            # Default: Show random available resources if no bookings or no similar found
            print("[v0] No bookings found or no similar resources, showing random resources...")
            
            all_resources = Resource.query.filter_by(
                resource_system_id=system_id,
                is_available=True
            ).all()
            
            if not all_resources:
                return []
            
            # Shuffle and take up to 9 random resources
            random_suggestions = random.sample(all_resources, min(9, len(all_resources)))
            
            for resource in random_suggestions:
                resource.reason = "Popular choice"
            
            print(f"[v0] Returning {len(random_suggestions)} random resources")
            return random_suggestions
            
        except Exception as e:
            logger.error(f"[v0] Error generating suggestions: {e}")
            import traceback
            traceback.print_exc()
            
            try:
                # Fallback: just return any available resources
                import random
                fallback_resources = Resource.query.filter_by(
                    resource_system_id=system_id,
                    is_available=True
                ).limit(9).all()
                
                for resource in fallback_resources:
                    resource.reason = "Available resource"
                
                return fallback_resources
            except:
                return []
    
    def calculate_relevance_score(self, resource, booking_params, existing_bookings):
        """Calculate how well a resource matches the booking parameters with adaptive, granular scoring"""
        score = 0.0
        requested_capacity = booking_params.get('participants')
        
        # CAPACITY MATCH (0-100 points) - Most important factor, uses continuous scoring
        if requested_capacity:
            capacity_ratio = resource.capacity / requested_capacity if requested_capacity > 0 else 1
            
            # Use gaussian-like curve centered at perfect fit
            # Perfect fit (1.0) = 100 points, degrades smoothly
            # Formula: 100 * exp(-(ratio-1)^2 / 0.05) gives smooth penalty for size mismatch
            import math
            capacity_score = 100 * math.exp(-((capacity_ratio - 1.0) ** 2) / 0.05)
            score += capacity_score
            print(f"[v0] {resource.name}: capacity_ratio={capacity_ratio:.2f}, capacity_score={capacity_score:.1f}")
        else:
            score += 50
        
        # RESOURCE TYPE MATCH (0-30 points)
        if booking_params.get('resource_type'):
            if resource.resource_type and booking_params['resource_type'].lower() in resource.resource_type.lower():
                score += 30  # Perfect type match
            else:
                score += 0   # Type mismatch (already filtered, shouldn't happen)
        else:
            score += 15
        
        # PRICE COMPETITIVENESS (0-50 points) - Significantly increased to differentiate same-capacity resources
        # Prefer cheaper options - this is key for distinguishing between resources
        if resource.hourly_rate:
            # Calculate price percentile - lower prices get higher scores
            # Use $300/hr as the upper reasonable limit
            price_normalized = min(resource.hourly_rate / 300.0, 1.0)
            # Inverse: expensive = low score, cheap = high score
            # $50/hr → score 40 pts, $100/hr → score 33 pts, $150/hr → score 25 pts, $300/hr → score 0 pts
            price_score = 50 * (1.0 - price_normalized)
            score += price_score
            print(f"[v0]   hourly_rate=${resource.hourly_rate}, price_normalized={price_normalized:.2f}, price_score={price_score:.1f}")
        else:
            score += 25
        
        # AVAILABILITY (0-20 points)
        if resource.is_available:
            score += 20
        else:
            score += 5
        
        # Ensure score is between 0 and 200
        score = max(0, min(200, score))
        
        return score
    
    def is_perfect_match(self, resource, booking_params):
        """Determine if a resource is a BEST RESULT (perfect match for all requirements)"""
        requested_capacity = booking_params.get('participants')
        
        # Check capacity perfection: within 90-110% of requested
        if requested_capacity:
            capacity_ratio = resource.capacity / requested_capacity if requested_capacity > 0 else 1
            if not (0.9 <= capacity_ratio <= 1.1):
                return False
        
        # Check type perfection: must match exactly
        if booking_params.get('resource_type'):
            if not resource.resource_type or booking_params['resource_type'].lower() not in resource.resource_type.lower():
                return False
        
        # Check availability perfection: must be available
        if not resource.is_available:
            return False
        
        return True
    
    def explain_match(self, resource, booking_params):
        """Generate human-readable explanation of why this resource matches"""
        reasons = []
        requested_capacity = booking_params.get('participants')
        
        if requested_capacity and resource.capacity:
            capacity_ratio = resource.capacity / requested_capacity if requested_capacity > 0 else 1
            
            # Perfect fit
            if 0.9 <= capacity_ratio <= 1.1:
                reasons.append(f"Perfect size for {requested_capacity} people ({resource.capacity} capacity)")
            # Good fit
            elif 1.1 < capacity_ratio <= 1.5:
                reasons.append(f"Excellent fit for {requested_capacity} people ({resource.capacity} capacity)")
            # Acceptable
            elif 1.5 < capacity_ratio <= 2.5:
                reasons.append(f"Accommodates {requested_capacity} people (has {resource.capacity} capacity)")
            # Oversized
            else:
                reasons.append(f"Can accommodate {requested_capacity} people (has {resource.capacity} capacity)")
        
        if booking_params.get('resource_type'):
            if resource.resource_type and booking_params['resource_type'].lower() in resource.resource_type.lower():
                reasons.append(f"Type: {resource.resource_type}")
        
        if resource.is_available:
            reasons.append("Currently available")
        
        if not reasons:
            reasons.append("Matches your search criteria")
        
        return reasons

from sqlalchemy import event

# Register SQLAlchemy events to auto-invalidate cache
try:
    event.listen(Resource, 'after_insert', AIModule.invalidate_type_cache)
    event.listen(Resource, 'after_update', AIModule.invalidate_type_cache)
    event.listen(Resource, 'after_delete', AIModule.invalidate_type_cache)
except Exception as e:
    logger.warning(f"[v0] Could not register SQLAlchemy events for cache invalidation: {e}")
