#!/usr/bin/env python3
"""
Standalone database initialization script.
This script resets the database and creates all tables with the new multi-system architecture.
Run this to fix login issues.
"""

import sys
import os
import sqlite3
from pathlib import Path
from werkzeug.security import generate_password_hash
from datetime import datetime

# Get the project root directory
project_root = Path(__file__).parent.parent
db_path = project_root / 'resource_booking.db'

print("[v0] Database Initialization Script")
print(f"[v0] Project Root: {project_root}")
print(f"[v0] Database Path: {db_path}")

# Step 1: Delete existing database
if db_path.exists():
    print(f"[v0] Removing existing database: {db_path}")
    db_path.unlink()
    print("[v0] Database deleted")

# Step 2: Create new database and tables
print("[v0] Creating new database with schema...")

conn = sqlite3.connect(str(db_path))
cursor = conn.cursor()

# Create Users table
cursor.execute('''
    CREATE TABLE IF NOT EXISTS users (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        username VARCHAR(80) NOT NULL UNIQUE,
        email VARCHAR(120) NOT NULL UNIQUE,
        password_hash VARCHAR(255) NOT NULL,
        full_name VARCHAR(120),
        role VARCHAR(20) DEFAULT 'user',
        is_active BOOLEAN DEFAULT 1,
        created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
        updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
        last_login TIMESTAMP,
        last_login_ip VARCHAR(45)
    )
''')

# Create ResourceSystem table (NEW)
cursor.execute('''
    CREATE TABLE IF NOT EXISTS resource_systems (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        name VARCHAR(120) NOT NULL,
        description TEXT,
        address VARCHAR(255) NOT NULL,
        city VARCHAR(120) NOT NULL,
        latitude FLOAT,
        longitude FLOAT,
        is_public BOOLEAN DEFAULT 1,
        is_active BOOLEAN DEFAULT 1,
        created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
        updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
    )
''')

# Create UserResourceSystem table (NEW)
cursor.execute('''
    CREATE TABLE IF NOT EXISTS user_resource_systems (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        user_id INTEGER NOT NULL,
        resource_system_id INTEGER NOT NULL,
        role VARCHAR(20) DEFAULT 'admin',
        created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
        FOREIGN KEY(user_id) REFERENCES users(id),
        FOREIGN KEY(resource_system_id) REFERENCES resource_systems(id),
        UNIQUE(user_id, resource_system_id)
    )
''')

# Create Resources table
cursor.execute('''
    CREATE TABLE IF NOT EXISTS resources (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        resource_system_id INTEGER NOT NULL,
        name VARCHAR(120) NOT NULL,
        description TEXT,
        resource_type VARCHAR(50) NOT NULL,
        capacity INTEGER,
        location VARCHAR(255),
        features TEXT,
        square_feet FLOAT,
        hourly_rate FLOAT DEFAULT 0.0,
        daily_rate FLOAT DEFAULT 0.0,
        monthly_rate FLOAT DEFAULT 0.0,
        availability_start TIME DEFAULT '09:00:00',
        availability_end TIME DEFAULT '18:00:00',
        is_available BOOLEAN DEFAULT 1,
        created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
        updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
        FOREIGN KEY(resource_system_id) REFERENCES resource_systems(id)
    )
''')

# Create Bookings table
cursor.execute('''
    CREATE TABLE IF NOT EXISTS bookings (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        user_id INTEGER NOT NULL,
        resource_system_id INTEGER NOT NULL,
        resource_id INTEGER NOT NULL,
        booking_date DATE NOT NULL,
        start_time TIME NOT NULL,
        end_time TIME NOT NULL,
        duration_days INTEGER,
        purpose TEXT,
        status VARCHAR(20) DEFAULT 'pending',
        cost FLOAT,
        booking_type VARCHAR(20),
        cancellation_requested BOOLEAN DEFAULT 0,
        cancellation_reason TEXT,
        created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
        updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
        FOREIGN KEY(user_id) REFERENCES users(id),
        FOREIGN KEY(resource_system_id) REFERENCES resource_systems(id),
        FOREIGN KEY(resource_id) REFERENCES resources(id)
    )
''')

# Create BookingHistory table
cursor.execute('''
    CREATE TABLE IF NOT EXISTS booking_history (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        user_id INTEGER NOT NULL,
        resource_id INTEGER NOT NULL,
        booking_date DATE,
        start_time TIME,
        end_time TIME,
        action VARCHAR(50),
        created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
        FOREIGN KEY(user_id) REFERENCES users(id),
        FOREIGN KEY(resource_id) REFERENCES resources(id)
    )
''')

# Create AuditLog table
cursor.execute('''
    CREATE TABLE IF NOT EXISTS audit_logs (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        user_id INTEGER,
        action VARCHAR(50),
        resource_type VARCHAR(50),
        resource_id INTEGER,
        ip_address VARCHAR(45),
        user_agent TEXT,
        details TEXT,
        status VARCHAR(20),
        created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
        FOREIGN KEY(user_id) REFERENCES users(id)
    )
''')

# Create indexes
cursor.execute('CREATE INDEX IF NOT EXISTS idx_users_username ON users(username)')
cursor.execute('CREATE INDEX IF NOT EXISTS idx_users_email ON users(email)')
cursor.execute('CREATE INDEX IF NOT EXISTS idx_resources_system ON resources(resource_system_id)')
cursor.execute('CREATE INDEX IF NOT EXISTS idx_bookings_user ON bookings(user_id)')
cursor.execute('CREATE INDEX IF NOT EXISTS idx_bookings_resource ON bookings(resource_id)')
cursor.execute('CREATE INDEX IF NOT EXISTS idx_bookings_system ON bookings(resource_system_id)')
cursor.execute('CREATE INDEX IF NOT EXISTS idx_resource_systems_city ON resource_systems(city)')

print("[v0] Tables created successfully")

# Step 3: Insert default data
print("[v0] Inserting default data...")

# Create admin user with password "Admin@12345"
admin_password_hash = generate_password_hash('Admin@12345')
cursor.execute('''
    INSERT INTO users (username, email, password_hash, full_name, role, is_active)
    VALUES (?, ?, ?, ?, ?, ?)
''', ('admin', 'admin@resourcebooking.com', admin_password_hash, 'System Administrator', 'admin', 1))

admin_id = cursor.lastrowid
print(f"[v0] Created admin user with ID: {admin_id}")

# Create default resource system
cursor.execute('''
    INSERT INTO resource_systems (name, description, address, city, is_public, is_active)
    VALUES (?, ?, ?, ?, ?, ?)
''', ('Main Facility', 'Default resource facility for all resources', 'Default Address', 'Default City', 1, 1))

system_id = cursor.lastrowid
print(f"[v0] Created Main Facility with ID: {system_id}")

# Assign admin to system
cursor.execute('''
    INSERT INTO user_resource_systems (user_id, resource_system_id, role)
    VALUES (?, ?, ?)
''', (admin_id, system_id, 'admin'))

print("[v0] Assigned admin to Main Facility")

# Create sample resources
sample_resources = [
    ('Conference Room A', 'Professional conference room for meetings', 'room', 20, 'Building A - 2nd Floor', 'Projector, Whiteboard, Video Conference', 400, 50, 150, 500),
    ('Meeting Room B', 'Small meeting room for team discussions', 'room', 8, 'Building A - 1st Floor', 'Whiteboard, TV Display', 150, 25, 75, 225),
    ('Training Lab', 'Computer lab for training sessions', 'lab', 30, 'Building B - 3rd Floor', 'Computers, Projector, WiFi', 800, 75, 225, 750),
]

for name, desc, rtype, capacity, location, features, sqft, hourly, daily, monthly in sample_resources:
    cursor.execute('''
        INSERT INTO resources 
        (resource_system_id, name, description, resource_type, capacity, location, features, square_feet, hourly_rate, daily_rate, monthly_rate)
        VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
    ''', (system_id, name, desc, rtype, capacity, location, features, sqft, hourly, daily, monthly))

print("[v0] Created 3 sample resources")

# Commit all changes
conn.commit()
conn.close()

print("\n" + "="*60)
print("[v0] DATABASE INITIALIZATION COMPLETE")
print("="*60)
print("\nYou can now login with:")
print("  Username: admin")
print("  Password: Admin@12345")
print("\nDatabase Location:", db_path)
print("="*60)
