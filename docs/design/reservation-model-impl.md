# Implementation Design: ADR 0001 (予約データモデル)

## スコープ
- ADR 0001 のデータモデルを実装するための具体設計。
- マイグレーション方針（SQL 例）、制約/インデックス、アプリ側の型・バリデーションの要点を示す。
- 整合性/ロック/時刻方針は ADR 0002 参照。

## マイグレーション（例: MySQL / InnoDB）
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
  status ENUM('request_pending','booked','cancel_pending','cancelled') NOT NULL DEFAULT 'request_pending',
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

### 備考
- CHECK 制約は MySQL 8+ で有効（8未満ではアプリ側で検証が必要）。
- DATETIME に UTC を保存し、入出力時に JST へ変換（ADR 0002）。
- seat_id は NULL 許容。席結合/専有の運用ルールはアプリ層/運用ルールで定義。

## アプリ層の型・バリデーション（例）
- Slot
  - shop_id: bigint
  - seat_id: Optional[bigint]
  - starts_at/ends_at: datetime (UTC 保持)
  - capacity: int >= 1
  - status: Literal['open','closed','blocked']
- Reservation
  - slot_id: bigint
  - user_id: bigint
  - party_size: int >= 1
  - status: Literal['request_pending','booked','cancel_pending','cancelled']
  - version: int (レスポンスに含め、更新/キャンセル時に If-Match 用に利用可)

## バリデーション/制約の実装ポイント
- starts_at < ends_at をアプリ層でもチェック（DB CHECK への依存を避けるため）。
- capacity >= 1, party_size >= 1 を API バリデーションで必須。
- seat_id の NULL とユニークキーの相性: MySQL では NULL はユニークを許容するため、(shop_id, seat_id, starts_at, ends_at) で seat_id が NULL の行は複数作れる。必要ならアプリ側で「seat_id NULL の枠は店舗単位で同時間帯に1件まで」など運用ルールで抑制する。
- status 値は列挙でバリデーションし、想定外文字列を禁止。

## マイグレーション順序の例
1) shops / users（既存ならスキップ）
2) slots
3) reservations
4) インデックス追加（必要に応じて同時）

## アプリ実装の入口（例）
- リポジトリ層: `SlotRepository`, `ReservationRepository` を定義し、作成/更新/取得を実装。
- DTO/Pydantic モデル: SlotCreate/SlotRead, ReservationCreate/ReservationRead などを定義。
- ステータスの遷移ルールとロック戦略は ADR 0002 に従う。

## TODO / Open
- seat_id NULL の枠をどこまで許容するか（店舗全体枠を複数作るか否か）。
- status 遷移に伴うイベント/通知の要否。
- users テーブルの詳細スキーマ（別 ADR で定義）。
