# ADR 0001: 予約データモデル

- Status: Accepted (draft)
- Date: 2024-10-19

## 背景 / Context
- 予約枠を事前に定義し、その枠からユーザーが予約する機能を実装する。
- ダブルブッキング防止と整合性確保を優先し、UI よりも正しさを重視する。
- 将来的にキャンセル/変更、店舗側の予約操作、認証/権限を拡張する前提。
- DB は MySQL (InnoDB) を想定する（ロック/外部キーが使える）。
- タイムゾーンやロック戦略などの整合性・時刻方針は ADR 0002 で扱う。

## 決定 / Decision
### テーブル（最小構成）
- users: id (PK) — 本 ADR では詳細スキーマは省略（別 ADR で定義）
- shops: id (PK), name (必須)
- slots: id (PK), shop_id (FK), seat_id (FK, NULL許容), starts_at (DATETIME), ends_at (DATETIME), capacity INT (>=1), status ENUM('open','closed','blocked'), created_at, updated_at
  - 制約: starts_at < ends_at, capacity >= 1
  - 一意制約: (shop_id, seat_id, starts_at, ends_at)
    - seat_id を NULL 許容とし、席を結合/専有する将来拡張に対応
  - インデックス: shop_id, seat_id
- reservations: id (PK), slot_id (FK), user_id (FK), party_size INT (>=1), status ENUM('request_pending','booked','cancelled'), created_at, updated_at, version INT (楽観ロック用)
  - 制約: party_size >= 1
  - 一意制約（候補）: (user_id, slot_id) — 同一ユーザーの同一枠重複を防ぐ
  - インデックス: slot_id, user_id

### ステータス（予約/枠）
- slots.status: 'open' のみ予約を許可。'closed' は店舗都合クローズ、'blocked' はシステム保守などで予約不可。
- reservations.status: 'request_pending'（受付中） / 'booked'（確定） / 'cancelled'（キャンセル確定）。

## 根拠 / Rationale
- seat_id を NULL 許容で持つことで、席専有/席結合と店舗全体の枠を両立しやすい。一意制約を seat_id 含みで設計しておけば拡張時に大きな変更が不要。
- 予約ステータスを細分化することで、受付中/確定/キャンセル申請中の違いを後続の業務処理で扱いやすくする。
- 楽観ロック用の version カラムを先に入れておくと、変更/キャンセル API での整合性チェックに流用できる。

## 影響 / Consequences
- 実装タスク: マイグレーション作成、枠/予約テーブルの CRUD、ステータス値のバリデーション。
- 一意制約・FK によりデータ投入時のエラーが早期に表面化する。
- 同時実行制御・タイムゾーンの扱いは ADR 0002 に委ねる。

## 未解決事項 / Open Questions
- party_size と席管理: 人数単位での運用と席専有/結合の優先順位をどうするか。
- 予約変更/キャンセルポリシー: 締切時間やペナルティ、キャンセル申請中→確定のフローをどうするか。
- 認証方式: ユーザー/店舗の認証手段（メール+パスワード/OAuth等）。
