#!/usr/bin/env python
"""
Standalone database initialization script for Resource Booking System
Creates all tables, initializes data, and creates test accounts
"""

import sqlite3
import hashlib
import os
from datetime import datetime, date, time

DB_PATH = 'resource_booking.db'

def hash_password(password):
    """Hash password using SHA256"""
    return hashlib.sha256(password.encode()).hexdigest()

def init_database():
    """Initialize database with all tables"""
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()
    
    print("[v0] Creating database tables...")
    
    # Drop existing tables if they exist (fresh start)
    tables_to_drop = [
        'booking_history', 'audit_logs', 'bookings', 'user_resource_systems',
        'resources', 'resource_systems', 'users'
    ]
    
    for table in tables_to_drop:
        cursor.execute(f'DROP TABLE IF EXISTS {table}')
    
    # Create users table
    cursor.execute('''
        CREATE TABLE users (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            username VARCHAR(80) UNIQUE NOT NULL,
            email VARCHAR(120) UNIQUE NOT NULL,
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
    print("  ✓ Created users table")
    
    # Create resource_systems table
    cursor.execute('''
        CREATE TABLE resource_systems (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            name VARCHAR(120) UNIQUE NOT NULL,
            description TEXT,
            address VARCHAR(255) NOT NULL,
            city VARCHAR(120),
            latitude REAL,
            longitude REAL,
            is_public BOOLEAN DEFAULT 1,
            is_active BOOLEAN DEFAULT 1,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        )
    ''')
    print("  ✓ Created resource_systems table")
    
    # Create user_resource_systems table
    cursor.execute('''
        CREATE TABLE user_resource_systems (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            user_id INTEGER NOT NULL,
            resource_system_id INTEGER NOT NULL,
            role VARCHAR(20) DEFAULT 'admin',
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            UNIQUE(user_id, resource_system_id),
            FOREIGN KEY(user_id) REFERENCES users(id),
            FOREIGN KEY(resource_system_id) REFERENCES resource_systems(id)
        )
    ''')
    print("  ✓ Created user_resource_systems table")
    
    # Create resources table
    cursor.execute('''
        CREATE TABLE resources (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            resource_system_id INTEGER NOT NULL,
            name VARCHAR(120) NOT NULL,
            description TEXT,
            resource_type VARCHAR(50),
            capacity INTEGER,
            location VARCHAR(255),
            features TEXT,
            square_feet REAL,
            hourly_rate REAL DEFAULT 0.0,
            daily_rate REAL DEFAULT 0.0,
            monthly_rate REAL DEFAULT 0.0,
            availability_start TIME DEFAULT '09:00:00',
            availability_end TIME DEFAULT '18:00:00',
            is_available BOOLEAN DEFAULT 1,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            FOREIGN KEY(resource_system_id) REFERENCES resource_systems(id)
        )
    ''')
    print("  ✓ Created resources table")
    
    # Create bookings table
    cursor.execute('''
        CREATE TABLE bookings (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            user_id INTEGER NOT NULL,
            resource_system_id INTEGER NOT NULL,
            resource_id INTEGER NOT NULL,
            booking_date DATE NOT NULL,
            start_time TIME NOT NULL,
            end_time TIME NOT NULL,
            duration_days INTEGER DEFAULT 1,
            purpose TEXT,
            status VARCHAR(20) DEFAULT 'pending',
            cancellation_requested BOOLEAN DEFAULT 0,
            cancellation_reason TEXT,
            cancellation_requested_at TIMESTAMP,
            booking_type VARCHAR(20) DEFAULT 'hourly',
            cost REAL DEFAULT 0.0,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            FOREIGN KEY(user_id) REFERENCES users(id),
            FOREIGN KEY(resource_system_id) REFERENCES resource_systems(id),
            FOREIGN KEY(resource_id) REFERENCES resources(id)
        )
    ''')
    print("  ✓ Created bookings table")
    
    # Create booking_history table
    cursor.execute('''
        CREATE TABLE booking_history (
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
    print("  ✓ Created booking_history table")
    
    # Create audit_logs table
    cursor.execute('''
        CREATE TABLE audit_logs (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            user_id INTEGER,
            action VARCHAR(100),
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
    print("  ✓ Created audit_logs table")
    
    conn.commit()
    return conn, cursor

def create_users(cursor, conn):
    """Create admin and user accounts"""
    print("\n[v0] Creating user accounts...")
    
    # Admin user
    admin_password = hash_password('Admin@12345')
    cursor.execute('''
        INSERT INTO users (username, email, password_hash, full_name, role, is_active)
        VALUES (?, ?, ?, ?, ?, ?)
    ''', ('admin', 'admin@system.com', admin_password, 'System Administrator', 'admin', 1))
    admin_id = cursor.lastrowid
    print(f"  ✓ Created admin user (ID: {admin_id})")
    
    # Regular user
    user_password = hash_password('User@12345')
    cursor.execute('''
        INSERT INTO users (username, email, password_hash, full_name, role, is_active)
        VALUES (?, ?, ?, ?, ?, ?)
    ''', ('user1', 'user1@example.com', user_password, 'John Doe', 'user', 1))
    user_id = cursor.lastrowid
    print(f"  ✓ Created regular user (ID: {user_id})")
    
    conn.commit()
    return admin_id, user_id

def create_facility(cursor, conn):
    """Create the default facility"""
    print("\n[v0] Creating facility...")
    
    cursor.execute('''
        INSERT INTO resource_systems (name, description, address, city, is_public, is_active)
        VALUES (?, ?, ?, ?, ?, ?)
    ''', ('Main Facility', 'Default resource facility for all users', 
          '123 Main Street', 'Downtown', 1, 1))
    facility_id = cursor.lastrowid
    print(f"  ✓ Created Main Facility (ID: {facility_id})")
    
    conn.commit()
    return facility_id

def assign_admin_to_facility(cursor, conn, admin_id, facility_id):
    """Assign admin user to facility"""
    print("\n[v0] Assigning admin to facility...")
    
    cursor.execute('''
        INSERT INTO user_resource_systems (user_id, resource_system_id, role)
        VALUES (?, ?, ?)
    ''', (admin_id, facility_id, 'admin'))
    
    conn.commit()
    print(f"  ✓ Admin assigned to Main Facility")

def create_resources(cursor, conn, facility_id):
    """Create sample resources"""
    print("\n[v0] Creating sample resources...")
    
    resources = [
        {
            'name': 'Conference Room A',
            'type': 'room',
            'capacity': 10,
            'location': 'Floor 1',
            'square_feet': 400,
            'hourly_rate': 50,
            'daily_rate': 300,
            'features': '["Projector", "Whiteboard", "Conference Phone"]'
        },
        {
            'name': 'Meeting Room B',
            'type': 'room',
            'capacity': 6,
            'location': 'Floor 1',
            'square_feet': 250,
            'hourly_rate': 30,
            'daily_rate': 200,
            'features': '["TV Screen", "Whiteboard"]'
        },
        {
            'name': 'Lab 1',
            'type': 'lab',
            'capacity': 20,
            'location': 'Floor 2',
            'square_feet': 800,
            'hourly_rate': 100,
            'daily_rate': 600,
            'features': '["Equipment", "Workstations", "Safety Gear"]'
        },
        {
            'name': 'Auditorium',
            'type': 'auditorium',
            'capacity': 100,
            'location': 'Ground Floor',
            'square_feet': 2000,
            'hourly_rate': 200,
            'daily_rate': 1000,
            'features': '["Projector", "Sound System", "Stage"]'
        },
        {
            'name': 'Training Room',
            'type': 'room',
            'capacity': 30,
            'location': 'Floor 3',
            'square_feet': 600,
            'hourly_rate': 75,
            'daily_rate': 400,
            'features': '["Projector", "Laptops", "Network"]'
        }
    ]
    
    for resource in resources:
        cursor.execute('''
            INSERT INTO resources 
            (resource_system_id, name, description, resource_type, capacity, location, 
             square_feet, hourly_rate, daily_rate, monthly_rate, features, is_available)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
        ''', (facility_id, resource['name'], f"{resource['name']} - Description", 
              resource['type'], resource['capacity'], resource['location'],
              resource['square_feet'], resource['hourly_rate'], resource['daily_rate'],
              resource['daily_rate'] * 20, resource['features'], 1))
        
        resource_id = cursor.lastrowid
        print(f"  ✓ Created {resource['name']} (ID: {resource_id})")
    
    conn.commit()

def main():
    """Run complete database initialization"""
    print("="*60)
    print("Resource Booking System - Database Initialization")
    print("="*60)
    
    # Check if database exists
    if os.path.exists(DB_PATH):
        print(f"\n[v0] Found existing database at {DB_PATH}")
        print("[v0] Backing up old database...")
        os.rename(DB_PATH, f'{DB_PATH}.backup')
        print("[v0] Old database backed up to resource_booking.db.backup")
    
    # Initialize database
    conn, cursor = init_database()
    
    # Create users
    admin_id, user_id = create_users(cursor, conn)
    
    # Create facility
    facility_id = create_facility(cursor, conn)
    
    # Assign admin to facility
    assign_admin_to_facility(cursor, conn, admin_id, facility_id)
    
    # Create resources
    create_resources(cursor, conn, facility_id)
    
    # Close connection
    conn.close()
    
    print("\n" + "="*60)
    print("DATABASE SETUP COMPLETE!")
    print("="*60)
    print("\nLOGIN CREDENTIALS:")
    print("-" * 60)
    print("\nADMIN USER:")
    print("  Username: admin")
    print("  Password: Admin@12345")
    print("  Role: Administrator")
    print("\nREGULAR USER:")
    print("  Username: user1")
    print("  Password: User@12345")
    print("  Role: User")
    print("-" * 60)
    print("\nDatabase file: resource_booking.db")
    print("Tables created: 7")
    print("Resources created: 5")
    print("\nYou can now start the application!")
    print("="*60)

if __name__ == '__main__':
    main()
