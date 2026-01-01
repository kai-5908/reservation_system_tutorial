# 予約イベントの構造化監査ログを追加する

Status: Accepted

Relevant PR:

# Context

- 予約作成/キャンセル/リスケ（および自動キャンセル、店舗側キャンセル）の操作を追跡できるようにしたい。
- API 実装は存在するが、現在は監査向けログがなく、後追い調査やインシデント対応の手掛かりが不足している。
- ストレージはアプリ外（例: AWS S3 など）で行う前提のため、アプリ側では構造化ログを stdout に出力する方針とする。
- ログ欠落はリスクが高いと判断し、ログ出力に失敗した場合は本処理も失敗（500）とする。
- PII は user_id のみに留め、メール・氏名などは記録しない。
- リクエスト相関のため `request_id`（例: `X-Request-ID` を受け取り、なければ生成）をログに含める。

## References

- docs/implementation_plan.md — 監査/ログが最後のスコープとして記載。
- これまでの ADR (0006, 0007) — API 整合性の対応が完了しており、次の優先が監査/ログ。

# Decision

- 構造化 JSON ログを stdout に出力し、後段で収集/保管する。
- 対象イベント: 予約作成、キャンセル、リスケ、自動キャンセル、店舗側キャンセル（実装時に該当経路があれば同様に記録）。
- ログフィールド（案を採用）:
  - `timestamp` (UTC ISO 8601), `level` (info/error), `action` (`reservation.created`, `reservation.cancelled`, `reservation.rescheduled`, `reservation.autocancelled`, `reservation.shop_cancelled`),
  - `initiator` (`user` / `system` / `shop`), `request_id`, `reservation_id`, `slot_id`, `shop_id`, `user_id`, `party_size`, `status_from`, `status_to`, `version`, `message`(任意)
- ログ出力に失敗した場合、本処理も失敗させ 500 を返す。
- PII は user_id のみに限定する。

## Reason

- 監査証跡を残し、インシデント調査や不正検知の土台を作るため。
- 構造化 JSON により後段のログ基盤（S3 など）で集約・検索しやすくするため。
- ログ欠落を重大と見なし、失敗時に処理も失敗させることで確実な記録を担保するため。
- リクエスト相関 ID を入れることで、複数サービス間のトレースや同一リクエスト起因のログ束ねを容易にするため。

# Consequences

- 予約系のユースケース/ルーターにロガーを追加し、上記フィールドを含む JSON を出力する実装が必要。
- `request_id` 受け入れ/生成の共通処理を追加し、各ハンドラで参照する。
- ログ出力失敗時に 500 を返すため、運用上はログ基盤の安定性が求められる。
- PII を抑制するため、メールや氏名はログに出さない運用が前提となる。

## Examples

予約作成（ユーザー操作）

```json
{
  "timestamp": "2024-10-20T09:00:00Z",
  "level": "info",
  "action": "reservation.created",
  "initiator": "user",
  "request_id": "req-12345",
  "reservation_id": 501,
  "slot_id": 321,
  "shop_id": 10,
  "user_id": 55,
  "party_size": 2,
  "status_from": null,
  "status_to": "booked",
  "version": 1
}
```

ユーザーキャンセル（If-Match 成功）

```json
{
  "timestamp": "2024-10-20T12:00:00Z",
  "level": "info",
  "action": "reservation.cancelled",
  "initiator": "user",
  "request_id": "req-67890",
  "reservation_id": 501,
  "slot_id": 321,
  "shop_id": 10,
  "user_id": 55,
  "party_size": 2,
  "status_from": "booked",
  "status_to": "cancelled",
  "version": 2
}
```

自動キャンセル（システムによるタイムアウト）

```json
{
  "timestamp": "2024-10-21T00:00:00Z",
  "level": "info",
  "action": "reservation.autocancelled",
  "initiator": "system",
  "request_id": null,
  "reservation_id": 502,
  "slot_id": 322,
  "shop_id": 10,
  "user_id": 56,
  "party_size": 4,
  "status_from": "booked",
  "status_to": "cancelled",
  "version": 3,
  "message": "Expired payment window"
}
```
