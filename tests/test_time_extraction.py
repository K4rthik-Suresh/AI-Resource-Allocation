#!/usr/bin/env python
"""Test NLP time extraction, date extraction, and date range parsing"""
import sys
import os

# Add project root to path
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..'))

from ai.ai_module import AIModule

ai = AIModule()

# =========================================================================
# 1. TIME EXTRACTION TESTS
# =========================================================================
time_queries = [
    "conference room for 10 people tomorrow from 10am to 5pm",
    "meeting room tomorrow at 2:30pm",
    "lab booking for 3 days starting tomorrow 9 am",
    "book a room from 10:30 to 17:00",
    "I need a space this afternoon from 2pm - 6pm",
    "tomorrow morning from 9am for 2 hours",
]

print("\n[v0] ===== NLP TIME EXTRACTION TEST =====\n")
for query in time_queries:
    result = ai.parse_nlp_booking(query)
    print(f"Query: {query}")
    print(f"  Start Time: {result.get('start_time')}")
    print(f"  End Time: {result.get('end_time')}")
    print()

# =========================================================================
# 2. DATE FORMAT TESTS (all new formats)
# =========================================================================
date_format_queries = [
    # Relative dates (existing)
    ("tomorrow", "Relative"),
    ("day after tomorrow", "Relative"),
    ("in 3 days", "Relative"),

    # Ordinal without year (existing)
    ("15th march", "Ordinal (no year)"),
    ("march 15th", "Ordinal (no year)"),

    # ISO 8601
    ("book a room on 2026-03-15", "ISO 8601"),
    ("need lab 2026-04-01", "ISO 8601"),

    # Formal American: "March 15, 2026"
    ("meeting on March 15, 2026", "Formal American"),
    ("book room April 1, 2026", "Formal American"),

    # Formal British: "15 March 2026"
    ("reserve on 15 March 2026", "Formal British"),
    ("need space 1 April 2026", "Formal British"),

    # Ordinal with year: "15th March 2026" / "March 15th, 2026"
    ("book on 15th March 2026", "Ordinal+Year (British)"),
    ("meeting March 15th, 2026", "Ordinal+Year (American)"),
    ("event on 1st April 2026", "Ordinal+Year"),
    ("conference April 2nd, 2026", "Ordinal+Year"),

    # Numerical DMY slash: "15/03/2026" or "15/03/26"
    ("book room on 15/03/2026", "Numerical Slash"),
    ("need lab 01/04/26", "Numerical Slash (2-digit year)"),

    # Numerical DMY dot: "15.03.2026" or "15.03.26"
    ("meeting on 15.03.2026", "Numerical Dot"),
    ("reserve 01.04.26", "Numerical Dot (2-digit year)"),

    # Numerical DMY dash: "15-03-2026"
    ("book on 15-03-2026", "Numerical Dash"),
]

print("\n[v0] ===== DATE FORMAT EXTRACTION TEST =====\n")
print(f"{'Format':<30} {'Query':<40} {'Extracted Date':<15} {'Status'}")
print("-" * 100)

for query, fmt in date_format_queries:
    extracted = ai._extract_date_pattern(query.lower())
    status = "✓" if extracted else "✗ FAILED"
    print(f"{fmt:<30} {query:<40} {str(extracted):<15} {status}")

# =========================================================================
# 3. DATE RANGE TESTS (including new formats)
# =========================================================================
range_queries = [
    # Ordinal ranges (existing)
    "I need a room from 15th march to 20th march",
    "book conference room from 1st april to 5th april",
    "need a lab from march 15th to march 20th",
    "from 15th march till 20th march",
    "need space from 10th may till 15th may for 20 people",

    # ISO 8601 ranges (new)
    "book room from 2026-03-15 to 2026-03-20",
    "need lab 2026-04-01 to 2026-04-05",

    # Numerical slash ranges (new)
    "reserve from 15/03/2026 to 20/03/2026",
    "need room 01/04/26 to 05/04/26",

    # Numerical dot ranges (new)
    "book from 15.03.2026 to 20.03.2026",

    # End date with "till" using ISO/numerical (new)
    "need room from 15th march till 2026-03-20",
    "book from 15th march till 20/03/2026",
]

print("\n\n[v0] ===== DATE RANGE EXTRACTION TEST =====\n")
for query in range_queries:
    result = ai.parse_nlp_booking(query)
    print(f"Query: {query}")
    print(f"  Date: {result.get('date')}")
    print(f"  End Date: {result.get('end_date')}")
    print(f"  Duration Days: {result.get('duration_days')}")
    print()

print("[v0] ===== ALL TESTS COMPLETE =====\n")
