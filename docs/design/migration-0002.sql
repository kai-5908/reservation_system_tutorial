-- Migration 0002: remove cancel_pending from reservations.status ENUM
-- Assumes MySQL 8 / InnoDB / UTC storage

-- 1) Normalize legacy cancel_pending rows (choose target state; here we mark them cancelled)
UPDATE reservations SET status = 'cancelled' WHERE status = 'cancel_pending';

-- 2) Alter ENUM to remove cancel_pending
ALTER TABLE reservations
  MODIFY status ENUM('request_pending','booked','cancelled') NOT NULL DEFAULT 'request_pending';

-- 3) Recreate index (noop if already present)
SET @stmt = (SELECT IF(
    NOT EXISTS(SELECT 1 FROM information_schema.statistics WHERE table_schema = DATABASE() AND table_name = 'reservations' AND index_name = 'idx_res_slot'),
    'CREATE INDEX idx_res_slot ON reservations(slot_id)',
    'SELECT 1'));
PREPARE s1 FROM @stmt; EXECUTE s1; DEALLOCATE PREPARE s1;

SET @stmt = (SELECT IF(
    NOT EXISTS(SELECT 1 FROM information_schema.statistics WHERE table_schema = DATABASE() AND table_name = 'reservations' AND index_name = 'idx_res_user'),
    'CREATE INDEX idx_res_user ON reservations(user_id)',
    'SELECT 1'));
PREPARE s2 FROM @stmt; EXECUTE s2; DEALLOCATE PREPARE s2;
