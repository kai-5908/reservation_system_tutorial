-- Development seed: users and shops (idempotent)
-- Note: Adjust ids/emails as needed for local testing.

INSERT INTO users (id, email, name, phone, email_verified_at, password_hash, auth_provider, auth_provider_id, created_at, updated_at)
VALUES (1, 'user1@example.com', 'User1', NULL, NULL, 'dummy', 'local', NULL, UTC_TIMESTAMP(), UTC_TIMESTAMP())
ON DUPLICATE KEY UPDATE id = id;

INSERT INTO shops (id, name, created_at, updated_at)
VALUES (1, 'Demo Shop', UTC_TIMESTAMP(), UTC_TIMESTAMP())
ON DUPLICATE KEY UPDATE id = id;
