-- ============================================================================
-- PHASE 1 DATABASE MIGRATION SCRIPT
-- Adds support for: Favorites, Reviews, Announcements, Notes, Timezone
-- ============================================================================

-- 1. Alter Users table - Add timezone and new relationships
ALTER TABLE users ADD COLUMN timezone VARCHAR(50) DEFAULT 'UTC' NOT NULL;

-- 2. Alter Bookings table - Add notes and update status values
ALTER TABLE bookings ADD COLUMN user_notes TEXT;
ALTER TABLE bookings ADD COLUMN admin_notes TEXT;
-- Update status enum to include 'completed'
UPDATE bookings SET status = CASE 
    WHEN status = 'pending' THEN 'pending'
    WHEN status = 'confirmed' THEN 'confirmed'
    WHEN status = 'cancelled' THEN 'cancelled'
    ELSE 'pending'
END;

-- 3. Create user_favorites table
CREATE TABLE IF NOT EXISTS user_favorites (
    id INTEGER PRIMARY KEY AUTO_INCREMENT,
    user_id INTEGER NOT NULL,
    resource_id INTEGER NOT NULL,
    created_at DATETIME DEFAULT CURRENT_TIMESTAMP,
    
    FOREIGN KEY (user_id) REFERENCES users(id) ON DELETE CASCADE,
    FOREIGN KEY (resource_id) REFERENCES resources(id) ON DELETE CASCADE,
    UNIQUE KEY uq_user_favorite (user_id, resource_id),
    INDEX idx_user_id (user_id),
    INDEX idx_resource_id (resource_id)
);

-- 4. Create resource_reviews table
CREATE TABLE IF NOT EXISTS resource_reviews (
    id INTEGER PRIMARY KEY AUTO_INCREMENT,
    user_id INTEGER NOT NULL,
    resource_id INTEGER NOT NULL,
    booking_id INTEGER,
    rating INTEGER NOT NULL CHECK (rating >= 1 AND rating <= 5),
    comment TEXT,
    created_at DATETIME DEFAULT CURRENT_TIMESTAMP,
    updated_at DATETIME DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,
    
    FOREIGN KEY (user_id) REFERENCES users(id) ON DELETE CASCADE,
    FOREIGN KEY (resource_id) REFERENCES resources(id) ON DELETE CASCADE,
    FOREIGN KEY (booking_id) REFERENCES bookings(id) ON DELETE SET NULL,
    INDEX idx_user_id (user_id),
    INDEX idx_resource_id (resource_id),
    INDEX idx_booking_id (booking_id),
    INDEX idx_created_at (created_at)
);

-- 5. Create system_announcements table
CREATE TABLE IF NOT EXISTS system_announcements (
    id INTEGER PRIMARY KEY AUTO_INCREMENT,
    title VARCHAR(200) NOT NULL,
    message LONGTEXT NOT NULL,
    announcement_type VARCHAR(20) DEFAULT 'info',
    created_by INTEGER NOT NULL,
    start_date DATETIME DEFAULT CURRENT_TIMESTAMP,
    end_date DATETIME,
    is_active BOOLEAN DEFAULT TRUE,
    is_pinned BOOLEAN DEFAULT FALSE,
    created_at DATETIME DEFAULT CURRENT_TIMESTAMP,
    updated_at DATETIME DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,
    
    FOREIGN KEY (created_by) REFERENCES users(id) ON DELETE SET NULL,
    INDEX idx_is_active (is_active),
    INDEX idx_created_at (created_at),
    INDEX idx_start_date (start_date),
    INDEX idx_end_date (end_date)
);

-- Add indexes for performance
CREATE INDEX IF NOT EXISTS idx_user_created_at ON bookings(user_id, created_at);
CREATE INDEX IF NOT EXISTS idx_status ON bookings(status);
CREATE INDEX IF NOT EXISTS idx_resource_system ON resources(resource_system_id);

COMMIT;
