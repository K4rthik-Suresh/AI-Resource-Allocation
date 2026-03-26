-- Phase 1: Add booking notes and timezone fields
-- This migration adds new columns required for Phase 1 features

-- Add user_notes and admin_notes to bookings table
ALTER TABLE bookings ADD COLUMN user_notes TEXT;
ALTER TABLE bookings ADD COLUMN admin_notes TEXT;

-- Add timezone to users table
ALTER TABLE users ADD COLUMN timezone VARCHAR(50) DEFAULT 'UTC';

-- Create user_favorites table for Phase 1
CREATE TABLE IF NOT EXISTS user_favorites (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    user_id INTEGER NOT NULL,
    resource_id INTEGER NOT NULL,
    created_at DATETIME DEFAULT CURRENT_TIMESTAMP,
    FOREIGN KEY (user_id) REFERENCES users(id) ON DELETE CASCADE,
    FOREIGN KEY (resource_id) REFERENCES resources(id) ON DELETE CASCADE,
    UNIQUE(user_id, resource_id)
);

-- Create system_announcements table for Phase 1
CREATE TABLE IF NOT EXISTS system_announcements (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    title VARCHAR(200) NOT NULL,
    message TEXT NOT NULL,
    announcement_type VARCHAR(20) DEFAULT 'info',
    created_by INTEGER NOT NULL,
    start_date DATETIME DEFAULT CURRENT_TIMESTAMP,
    end_date DATETIME,
    is_active BOOLEAN DEFAULT 1,
    is_pinned BOOLEAN DEFAULT 0,
    created_at DATETIME DEFAULT CURRENT_TIMESTAMP,
    updated_at DATETIME DEFAULT CURRENT_TIMESTAMP,
    FOREIGN KEY (created_by) REFERENCES users(id)
);

-- Create indexes for better performance
CREATE INDEX IF NOT EXISTS idx_user_favorites_user_id ON user_favorites(user_id);
CREATE INDEX IF NOT EXISTS idx_user_favorites_resource_id ON user_favorites(resource_id);
CREATE INDEX IF NOT EXISTS idx_announcements_active ON system_announcements(is_active);
CREATE INDEX IF NOT EXISTS idx_announcements_created ON system_announcements(created_at);

-- Update booking status options by adding 'completed' status if not exists
-- Note: SQLite doesn't have ALTER COLUMN, so we just ensure the column supports these values
