#!/usr/bin/env python
"""Quick test to verify all date format extractions work correctly"""
import sys, os, logging
logging.disable(logging.CRITICAL)
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..'))
from ai.ai_module import AIModule

ai = AIModule()
passed = 0
failed = 0

tests = [
    # (input_text, expected_date, format_name)
    ("2026-03-15", "2026-03-15", "ISO 8601"),
    ("book on 2026-04-01", "2026-04-01", "ISO 8601 in sentence"),
    ("15/03/2026", "2026-03-15", "Numerical Slash DMY"),
    ("01/04/26", "2026-04-01", "Numerical Slash 2-digit year"),
    ("15.03.2026", "2026-03-15", "Numerical Dot DMY"),
    ("15.03.26", "2026-03-15", "Numerical Dot 2-digit year"),
    ("15-03-2026", "2026-03-15", "Numerical Dash DMY"),
    ("march 15, 2026", "2026-03-15", "Formal American"),
    ("april 1, 2026", "2026-04-01", "Formal American (no leading zero)"),
    ("15 march 2026", "2026-03-15", "Formal British"),
    ("1 april 2026", "2026-04-01", "Formal British (no leading zero)"),
    ("15th march 2026", "2026-03-15", "Ordinal+Year British"),
    ("march 15th, 2026", "2026-03-15", "Ordinal+Year American"),
    ("1st april 2026", "2026-04-01", "Ordinal 1st + Year"),
    ("2nd april 2026", "2026-04-02", "Ordinal 2nd + Year"),
    ("3rd april 2026", "2026-04-03", "Ordinal 3rd + Year"),
    ("15th march", "2026-03-15", "Ordinal no year (existing)"),
    ("march 15th", "2026-03-15", "Ordinal no year reversed (existing)"),
]

print("\n===== DATE FORMAT EXTRACTION TEST =====\n")

for query, expected, name in tests:
    result = ai._extract_date_pattern(query.lower())
    ok = result == expected
    if ok:
        passed += 1
        print(f"  PASS  {name:40s}  {query:30s} -> {result}")
    else:
        failed += 1
        print(f"  FAIL  {name:40s}  {query:30s} -> {result} (expected {expected})")

print(f"\n===== RESULTS: {passed} passed, {failed} failed =====\n")

if failed > 0:
    sys.exit(1)
