#!/usr/bin/env python3
"""
Minimal database initialization using direct SQLite without external dependencies
"""
import sqlite3
import hashlib
import os

DB_PATH = 'resource_booking.db'

def hash_password(password):
    """Simple password hashing"""
    return hashlib.sha256(password.encode()).hexdigest()

def init_database():
    """Initialize database with minimal schema"""
    
    # Remove old database if exists
    if os.path.exists(DB_PATH):
        os.remove(DB_PATH)
        print("[v0] Removed old database")
    
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()
    
    print("[v0] Creating database tables...")
    
    # Users table
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
    print("[v0] Created users table")
    
    # Resource Systems table
    cursor.execute('''
        CREATE TABLE resource_systems (
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
    print("[v0] Created resource_systems table")
    
    # User Resource Systems table
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
    print("[v0] Created user_resource_systems table")
    
    # Resources table
    cursor.execute('''
        CREATE TABLE resources (
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
    print("[v0] Created resources table")
    
    # Bookings table
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
            booking_type VARCHAR(20) DEFAULT 'hourly',
            cost FLOAT DEFAULT 0.0,
            cancellation_requested BOOLEAN DEFAULT 0,
            cancellation_reason TEXT,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            FOREIGN KEY(user_id) REFERENCES users(id),
            FOREIGN KEY(resource_system_id) REFERENCES resource_systems(id),
            FOREIGN KEY(resource_id) REFERENCES resources(id)
        )
    ''')
    print("[v0] Created bookings table")
    
    # Booking History table
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
    print("[v0] Created booking_history table")
    
    # Audit Logs table
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
    print("[v0] Created audit_logs table")
    
    # Create indexes
    cursor.execute('CREATE INDEX idx_users_username ON users(username)')
    cursor.execute('CREATE INDEX idx_users_email ON users(email)')
    cursor.execute('CREATE INDEX idx_resources_system ON resources(resource_system_id)')
    cursor.execute('CREATE INDEX idx_bookings_user ON bookings(user_id)')
    cursor.execute('CREATE INDEX idx_bookings_resource ON bookings(resource_id)')
    cursor.execute('CREATE INDEX idx_bookings_system ON bookings(resource_system_id)')
    cursor.execute('CREATE INDEX idx_audit_user ON audit_logs(user_id)')
    print("[v0] Created indexes")
    
    # Insert default resource system
    cursor.execute('''
        INSERT INTO resource_systems (name, description, address, city, is_public, is_active)
        VALUES (?, ?, ?, ?, ?, ?)
    ''', ('Main Facility', 'Default resource facility', 'Default Address', 'Default City', 1, 1))
    
    system_id = cursor.lastrowid
    print(f"[v0] Created Main Facility with ID: {system_id}")
    
    # Create admin user
    admin_password_hash = hash_password('Admin@12345')
    cursor.execute('''
        INSERT INTO users (username, email, password_hash, full_name, role, is_active)
        VALUES (?, ?, ?, ?, ?, ?)
    ''', ('admin', 'admin@example.com', admin_password_hash, 'System Admin', 'admin', 1))
    
    admin_id = cursor.lastrowid
    print(f"[v0] Created admin user with ID: {admin_id}")
    
    # Assign admin to main facility
    cursor.execute('''
        INSERT INTO user_resource_systems (user_id, resource_system_id, role)
        VALUES (?, ?, ?)
    ''', (admin_id, system_id, 'admin'))
    print(f"[v0] Assigned admin to Main Facility")
    
    # Create sample resources
    sample_resources = [
        ('Conference Room A', 'Large conference room with AV setup', 'room', 20, 'Building 1, Floor 2', '500 sq ft', 50.0, 300.0, 1000.0, '09:00:00', '18:00:00'),
        ('Meeting Room B', 'Small meeting room', 'room', 8, 'Building 1, Floor 1', '200 sq ft', 25.0, 150.0, 500.0, '09:00:00', '18:00:00'),
        ('Lab 101', 'Research laboratory', 'lab', 15, 'Building 2, Floor 1', '1000 sq ft', 75.0, 400.0, 1500.0, '08:00:00', '20:00:00'),
        ('Auditorium', 'Large presentation hall', 'auditorium', 100, 'Building 3, Ground', '5000 sq ft', 100.0, 600.0, 2000.0, '09:00:00', '21:00:00'),
        ('Study Area', 'Quiet study space', 'room', 10, 'Building 1, Floor 3', '300 sq ft', 0.0, 50.0, 200.0, '07:00:00', '23:00:00'),
    ]
    
    for resource in sample_resources:
        cursor.execute('''
            INSERT INTO resources 
            (resource_system_id, name, description, resource_type, capacity, location, square_feet, 
             hourly_rate, daily_rate, monthly_rate, availability_start, availability_end, is_available)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
        ''', (system_id,) + resource + (1,))
    
    print(f"[v0] Created {len(sample_resources)} sample resources")
    
    conn.commit()
    conn.close()
    
    print("\n" + "="*60)
    print("[v0] DATABASE INITIALIZATION COMPLETE!")
    print("="*60)
    print(f"Database: {DB_PATH}")
    print(f"Admin Credentials:")
    print(f"  Username: admin")
    print(f"  Password: Admin@12345")
    print(f"\nMain Facility ID: {system_id}")
    print(f"Admin User ID: {admin_id}")
    print("="*60)

if __name__ == '__main__':
    try:
        init_database()
        print("[v0] Database initialization successful!")
    except Exception as e:
        print(f"[v0] Error during initialization: {str(e)}")
        import traceback
        traceback.print_exc()
