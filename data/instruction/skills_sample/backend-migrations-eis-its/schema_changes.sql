-- Planned schema changes for v2.3.0 release

-- 1. Add user_preferences table
CREATE TABLE user_preferences (
    id BIGSERIAL PRIMARY KEY,
    user_id BIGINT NOT NULL REFERENCES users(id),
    theme VARCHAR(20) DEFAULT 'light',
    language VARCHAR(10) DEFAULT 'en',
    notifications_enabled BOOLEAN DEFAULT TRUE,
    created_at TIMESTAMP DEFAULT NOW(),
    updated_at TIMESTAMP DEFAULT NOW()
);

-- 2. Add index on users.email for faster lookup
CREATE INDEX idx_users_email ON users(email);

-- 3. Add soft delete to orders table
ALTER TABLE orders ADD COLUMN deleted_at TIMESTAMP NULL;
