-- Migration 0001: users, shops, slots, reservations (MySQL 8 / InnoDB / UTC保存)
-- Note: 時刻は UTC で保存し、API 入出力で JST(+09:00) に変換する。

CREATE TABLE IF NOT EXISTS users (
  id BIGINT AUTO_INCREMENT PRIMARY KEY,
  email VARCHAR(255) NOT NULL,
  name VARCHAR(255) NOT NULL,
  phone VARCHAR(50) NULL,
  email_verified_at DATETIME NULL,
  password_hash VARCHAR(255) NOT NULL,
  auth_provider VARCHAR(50) NOT NULL DEFAULT 'local',
  auth_provider_id VARCHAR(255) NULL,
  created_at DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP,
  updated_at DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,
  CONSTRAINT uq_users_email UNIQUE (email)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4;

CREATE TABLE IF NOT EXISTS shops (
  id BIGINT AUTO_INCREMENT PRIMARY KEY,
  name VARCHAR(255) NOT NULL,
  created_at DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP,
  updated_at DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4;

CREATE TABLE IF NOT EXISTS slots (
  id BIGINT AUTO_INCREMENT PRIMARY KEY,
  shop_id BIGINT NOT NULL,
  seat_id BIGINT NULL,
  starts_at DATETIME NOT NULL,
  ends_at DATETIME NOT NULL,
  capacity INT NOT NULL,
  status ENUM('open','closed','blocked') NOT NULL DEFAULT 'open',
  created_at DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP,
  updated_at DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,
  CONSTRAINT chk_slots_time CHECK (starts_at < ends_at),
  CONSTRAINT chk_slots_capacity CHECK (capacity >= 1),
  CONSTRAINT uq_slots UNIQUE (shop_id, seat_id, starts_at, ends_at),
  CONSTRAINT fk_slots_shop FOREIGN KEY (shop_id) REFERENCES shops(id)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4;

CREATE TABLE IF NOT EXISTS reservations (
  id BIGINT AUTO_INCREMENT PRIMARY KEY,
  slot_id BIGINT NOT NULL,
  user_id BIGINT NOT NULL,
  party_size INT NOT NULL,
  status ENUM('request_pending','booked','cancelled') NOT NULL DEFAULT 'request_pending',
  version INT NOT NULL DEFAULT 1,
  created_at DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP,
  updated_at DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,
  CONSTRAINT chk_res_party_size CHECK (party_size >= 1),
  CONSTRAINT uq_res_user_slot UNIQUE (user_id, slot_id),
  CONSTRAINT fk_res_slot FOREIGN KEY (slot_id) REFERENCES slots(id),
  CONSTRAINT fk_res_user FOREIGN KEY (user_id) REFERENCES users(id)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4;

-- Re-runnable index creation (drop first to avoid duplicate key errors)
SET @stmt = (SELECT IF(
    NOT EXISTS(SELECT 1 FROM information_schema.statistics WHERE table_schema = DATABASE() AND table_name = 'slots' AND index_name = 'idx_slots_shop'),
    'CREATE INDEX idx_slots_shop ON slots(shop_id)',
    'SELECT 1'));
PREPARE s1 FROM @stmt; EXECUTE s1; DEALLOCATE PREPARE s1;

SET @stmt = (SELECT IF(
    NOT EXISTS(SELECT 1 FROM information_schema.statistics WHERE table_schema = DATABASE() AND table_name = 'slots' AND index_name = 'idx_slots_seat'),
    'CREATE INDEX idx_slots_seat ON slots(seat_id)',
    'SELECT 1'));
PREPARE s2 FROM @stmt; EXECUTE s2; DEALLOCATE PREPARE s2;

SET @stmt = (SELECT IF(
    NOT EXISTS(SELECT 1 FROM information_schema.statistics WHERE table_schema = DATABASE() AND table_name = 'reservations' AND index_name = 'idx_res_slot'),
    'CREATE INDEX idx_res_slot ON reservations(slot_id)',
    'SELECT 1'));
PREPARE s3 FROM @stmt; EXECUTE s3; DEALLOCATE PREPARE s3;

SET @stmt = (SELECT IF(
    NOT EXISTS(SELECT 1 FROM information_schema.statistics WHERE table_schema = DATABASE() AND table_name = 'reservations' AND index_name = 'idx_res_user'),
    'CREATE INDEX idx_res_user ON reservations(user_id)',
    'SELECT 1'));
PREPARE s4 FROM @stmt; EXECUTE s4; DEALLOCATE PREPARE s4;
