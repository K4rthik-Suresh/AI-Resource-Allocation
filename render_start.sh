#!/bin/bash
# ============================================
# Render Startup Script
# Initializes DB on each start, then starts server
# ============================================

set -e

echo "============================================"
echo " Resource Allocation System - Starting..."
echo "============================================"

# Initialize database (re-creates fresh on each restart with sample data)
echo "[DEPLOY] Initializing database with sample data..."
cd /app/scripts && python init_system.py

# Move the database to app root where Flask expects it
if [ -f /app/scripts/resource_booking.db ]; then
    mv /app/scripts/resource_booking.db /app/instance/resource_booking.db
    echo "[DEPLOY] Database ready at /app/instance/resource_booking.db"
fi

cd /app
echo "[DEPLOY] Starting Gunicorn server..."
exec gunicorn app:app -c gunicorn.conf.py
