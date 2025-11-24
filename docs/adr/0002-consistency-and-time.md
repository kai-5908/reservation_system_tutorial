# ADR 0002: 整合性と時刻の扱い

- Status: Accepted (draft)
- Date: 2024-10-19

## 背景 / Context
- ADR 0001 で予約データモデルを定義した。実装では整合性（ダブルブッキング防止）と時刻の扱い方針を明確にする必要がある。
- UI は必ず JST 表記。DB は UTC 保存とし、API 層で JST 入出力に統一する。

## 決定 / Decision
### タイムゾーン・時刻
- DB への保存: UTC（`DATETIME` または `TIMESTAMP`）。
- API 入出力: JST (Asia/Tokyo) で返す/受け取る。フォーマットは ISO 8601 (+09:00) を推奨。
- 内部変換: サーバーサイドで UTC⇔JST を一元的に変換するユーティリティを持つ。

### 整合性・同時実行制御
- 予約作成時のトランザクション
  - `slots` 対象行を `SELECT ... FOR UPDATE` でロック。
  - `reservations` から同一 slot の `party_size` 合計を集計し、`capacity` を超えないことを確認。
  - 条件を満たす場合のみ `reservations` に挿入。
- 一意制約の活用
  - `slots` の (shop_id, seat_id, starts_at, ends_at) で枠の重複定義を防ぐ。
  - `reservations` の (user_id, slot_id) で同一ユーザーの同一枠重複を防ぐ（採用する場合）。
- 楽観ロック
  - `reservations.version` を更新時にインクリメントし、更新/キャンセル API で If-Match 的に検証できるようにする。

### ステータス遷移の最小ルール
- 予約: request_pending → booked → cancel_pending → cancelled（最小でも booked → cancelled は許可）。
- 枠: status が open のときのみ予約を許可。closed/blocked は予約不可。

## 根拠 / Rationale
- UTC 保存 + JST 入出力にすることで複数店舗や夏時間の影響を避けつつ、UI では一貫した JST を表示できる。
- 行ロック + 集計チェックにより同時アクセス時の二重予約を防止できる。ユニークキーで事前のデータ不整合も防ぐ。
- 楽観ロック version を持つことで、変更/キャンセル処理での競合検知が容易になる。

## 影響 / Consequences
- 実装タスク: 時刻変換ユーティリティ追加、予約作成処理をトランザクション化しロックを入れる、ユニーク制約に合わせたエラーハンドリングを実装。
- API 契約: 時刻は ISO 8601 +09:00 で返す/受け取る前提となる。
- 高負荷時: ロック待ちが発生する可能性があるため、将来的にキューイングやレートリミットを検討する余地あり。

## 未解決事項 / Open Questions
- party_size vs 席専有/結合の優先順位: 席が埋まっても人数が残っている場合の扱いをどうするか。
- 予約変更/キャンセルポリシー: 締切時間、ペナルティ、キャンセル申請フローの有無。
- 認証/認可: ユーザー/店舗の識別方法（メール+パスワード/OAuth 等）と API トークンの扱い。
