# Implementation Design: ADR 0001（予約モデル実装）

## スコープ
- ADR0001 のデータモデル実装のベース設計。
- マイグレーション（SQL 例）、制約/インデックス、アプリケーションの型/バリデーションの骨子。
- 時刻/整合性/ロックは ADR0002 を参照。

## マイグレーション例（MySQL / InnoDB）
```sql
CREATE TABLE shops (
  id BIGINT AUTO_INCREMENT PRIMARY KEY,
  name VARCHAR(255) NOT NULL,
  created_at DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP,
  updated_at DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP
) ENGINE=InnoDB;

CREATE TABLE slots (
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
) ENGINE=InnoDB;

CREATE TABLE reservations (
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
) ENGINE=InnoDB;

CREATE INDEX idx_slots_shop ON slots(shop_id);
CREATE INDEX idx_slots_seat ON slots(seat_id);
CREATE INDEX idx_res_slot ON reservations(slot_id);
CREATE INDEX idx_res_user ON reservations(user_id);
```

### 補足
- CHECK 制約は MySQL 8+ で有効（8未満ではアプリ側で補完が必要）。
- DATETIME は UTC で保存し、入出力は JST へ変換（ADR0002）。
- seat_id は NULL を許容し、店舗全体/座席単位の枠を混在可能。

## アプリ側の型・バリデーション（例）
- Slot
  - shop_id: bigint
  - seat_id: Optional[bigint]
  - starts_at/ends_at: datetime (UTC 保存)
  - capacity: int >= 1
  - status: Literal['open','closed','blocked']
- Reservation
  - slot_id: bigint
  - user_id: bigint
  - party_size: int >= 1
  - status: Literal['request_pending','booked','cancelled']
  - version: int（楽観ロック用、更新時に If-Match などで利用）

## 制約/整合性のポイント
- starts_at < ends_at をマイグレーションとアプリでチェック。
- capacity >= 1, party_size >= 1 は API 側でバリデーション。
- seat_id NULL とユニーク: MySQL では NULL はユニークキーで重複扱いにならないため、店舗全体枠と座席指定枠を混在可能。必要に応じてアプリ側で NULL を 1 店舗 1 件に制限するなど調整。
- status 値は固定リストで管理し、外部からの恣意的な値を防ぐ。

## 実装ステップ（例）
1) shops / users（ユーザーテーブルは本設計で別途定義）
2) slots
3) reservations
4) インデックス追加（必要に応じて再実行可）

## アプリ設計の骨子（例）
- リポジトリインターフェース: `SlotRepository`, `ReservationRepository` に CRUD/取得系を定義。
- DTO/Pydantic: SlotCreate/SlotRead, ReservationCreate/ReservationRead などを用意。
- ステータス遷移・ロック方針は ADR0002 に従う。

## TODO / Open
- seat_id NULL 枠を店舗あたり複数許容するか（現状は許容）。
- status 遷移の詳細（キャンセル締め切りなどは ADR0002 で定義）。
- users テーブルの詳細は別 ADR で定義。
