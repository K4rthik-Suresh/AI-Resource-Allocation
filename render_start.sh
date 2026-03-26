#!/bin/bash
# ============================================
# Render Startup Script
# Initializes DB safely on startup and seeds data
# ============================================

set -e

echo "============================================"
echo " Resource Allocation System - Starting..."
echo "============================================"

# We rely on app.py's `db.create_all()` context to safely create tables in Postgres
# without wiping existing data.

# We will run the seeding scripts. Since the scripts check if resources/facilities
# exist before creating them (or safely delete and recreate specific chunks), 
# running them on startup is safe and idempotent.

echo "[DEPLOY] Seeding default facilities and base resources..."
cd /app/scripts
python setup_simple.py

echo "[DEPLOY] Seeding extended resources and future bookings..."
python add_500_resources_and_bookings.py

cd /app
echo "[DEPLOY] Starting Gunicorn server..."
exec gunicorn app:app -c gunicorn.conf.py
