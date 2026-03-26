#!/bin/bash
# ============================================
# Render Startup Script
# Initializes DB on first deploy, then starts server
# ============================================

set -e

echo "============================================"
echo " Resource Allocation System - Starting..."
echo "============================================"

# Initialize database if it doesn't exist
if [ ! -f /data/resource_booking.db ]; then
    echo "[DEPLOY] First deployment detected - initializing database..."
    cd /app/scripts && python init_system.py
    
    # Move the database to the persistent disk
    if [ -f /app/scripts/resource_booking.db ]; then
        mv /app/scripts/resource_booking.db /data/resource_booking.db
        echo "[DEPLOY] Database moved to persistent disk at /data/resource_booking.db"
    fi
    
    cd /app
    echo "[DEPLOY] Database initialization complete!"
else
    echo "[DEPLOY] Existing database found at /data/resource_booking.db"
fi

echo "[DEPLOY] Starting Gunicorn server..."
exec gunicorn app:app -c gunicorn.conf.py
