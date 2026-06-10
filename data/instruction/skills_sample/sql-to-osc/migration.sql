-- Flyway migration V2.3.1 - Add user activity tracking
-- Author: Backend Team
-- Date: 2026-04-01

ALTER TABLE users ADD COLUMN last_login_at TIMESTAMP NULL;
ALTER TABLE users ADD COLUMN login_count INT NOT NULL DEFAULT 0;
ALTER TABLE users ADD COLUMN account_status VARCHAR(20) NOT NULL DEFAULT 'active';

CREATE INDEX idx_users_account_status ON users(account_status);
CREATE INDEX idx_users_last_login ON users(last_login_at);

ALTER TABLE user_sessions ADD COLUMN ip_address VARCHAR(45) NULL;
ALTER TABLE user_sessions ADD COLUMN user_agent TEXT NULL;

CREATE INDEX idx_user_sessions_user_id_created ON user_sessions(user_id, created_at);
