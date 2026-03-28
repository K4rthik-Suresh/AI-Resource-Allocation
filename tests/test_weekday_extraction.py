#!/usr/bin/env python
"""Test to verify weekday name date extraction works correctly"""
import sys, os, logging
logging.disable(logging.CRITICAL)
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..'))
from ai.ai_module import AIModule
from datetime import datetime, timedelta

ai = AIModule()
passed = 0
failed = 0
today = datetime.now()

def next_weekday(weekday_num):
    """Calculate the next occurrence of a weekday (1-7 days ahead)"""
    days_ahead = weekday_num - today.weekday()
    if days_ahead <= 0:
        days_ahead += 7
    return (today + timedelta(days=days_ahead)).strftime('%Y-%m-%d')

def this_weekday(weekday_num):
    """Calculate this/upcoming occurrence of a weekday (0-6 days ahead)"""
    days_ahead = weekday_num - today.weekday()
    if days_ahead < 0:
        days_ahead += 7
    return (today + timedelta(days=days_ahead)).strftime('%Y-%m-%d')

# Weekday numbers: Mon=0, Tue=1, Wed=2, Thu=3, Fri=4, Sat=5, Sun=6
tests = [
    # "next <weekday>" tests
    ("i need a room for next monday", next_weekday(0), "next monday"),
    ("book a lab next tuesday", next_weekday(1), "next tuesday"),
    ("need a room next wednesday", next_weekday(2), "next wednesday"),
    ("reserve for next thursday", next_weekday(3), "next thursday"),
    ("i need a room for next friday", next_weekday(4), "next friday"),
    ("book next saturday", next_weekday(5), "next saturday"),
    ("meeting next sunday", next_weekday(6), "next sunday"),
    
    # "this <weekday>" tests
    ("i need a room this monday", this_weekday(0), "this monday"),
    ("book for this friday", this_weekday(4), "this friday"),
    
    # "on <weekday>" tests
    ("book a room on monday", this_weekday(0), "on monday"),
    ("meeting on friday", this_weekday(4), "on friday"),
    
    # bare weekday name tests
    ("i need a room monday", next_weekday(0), "bare monday"),
    ("book a lab friday afternoon", next_weekday(4), "bare friday"),
    
    # abbreviated weekday names
    ("next mon", next_weekday(0), "next mon (abbreviated)"),
    ("next fri", next_weekday(4), "next fri (abbreviated)"),
    
    # generic "weekday" literal tests
    ("on coming weekday", (today + timedelta(days=3 if today.weekday() == 4 else 2 if today.weekday() == 5 else 1)).strftime('%Y-%m-%d'), "coming weekday"),
    ("on next weekday", (today + timedelta(days=3 if today.weekday() == 4 else 2 if today.weekday() == 5 else 1)).strftime('%Y-%m-%d'), "next weekday"),
    ("on weekday", (today + timedelta(days=3 if today.weekday() == 4 else 2 if today.weekday() == 5 else 1)).strftime('%Y-%m-%d'), "on weekday"),
    ("this weekday", (today + timedelta(days=3 if today.weekday() == 4 else 2 if today.weekday() == 5 else 1)).strftime('%Y-%m-%d'), "this weekday"),
]

print(f"\n===== WEEKDAY DATE EXTRACTION TEST =====")
print(f"Today is: {today.strftime('%A %Y-%m-%d')} (weekday={today.weekday()})\n")

for query, expected, name in tests:
    result = ai._extract_date_pattern(query.lower())
    ok = result == expected
    if ok:
        passed += 1
        print(f"  PASS  {name:30s}  {query:45s} -> {result}")
    else:
        failed += 1
        print(f"  FAIL  {name:30s}  {query:45s} -> {result} (expected {expected})")

print(f"\n===== RESULTS: {passed} passed, {failed} failed =====\n")

if failed > 0:
    sys.exit(1)
