# API Schema (初期案) — 予約枠/予約
対象: ADR 0001 (モデル) + ADR 0002 (整合性/時刻)
時刻フォーマット: ISO 8601 `YYYY-MM-DDTHH:MM:SS+09:00`（JST）。DB では UTC 保存。

## 共通
- 認証: Bearer トークン想定（ユーザー本人を特定）。店舗向け管理APIは別途。
- エラー: 400(バリデーション), 401(認証), 403(権限), 404(未発見), 409(競合: capacity/重複) を使用。

---
## 予約枠検索（空き枠）
GET /shops/{shop_id}/slots/availability?start=2024-10-20T00:00:00+09:00&end=2024-10-21T00:00:00+09:00&seat_id=123
- 目的: ユーザー向け空き枠一覧。
- クエリ: start/end は必須。seat_id は任意。
- レスポンス 200:
```json
{
  "items": [
    {
      "slot_id": 1,
      "shop_id": 10,
      "seat_id": null,
      "starts_at": "2024-10-20T18:00:00+09:00",
      "ends_at": "2024-10-20T19:00:00+09:00",
      "capacity": 4,
      "status": "open",
      "remaining": 2
    }
  ]
}
```
- 備考: remaining は reservations の party_size 合計から算出。

---
## 予約作成
POST /reservations
- ボディ:
```json
{
  "slot_id": 1,
  "party_size": 2
}
```
- ルール: slots.status=open かつ capacity を超えない場合のみ作成。user_id は認証から取得。
- レスポンス 201:
```json
{
  "reservation_id": 100,
  "slot_id": 1,
  "user_id": 55,
  "party_size": 2,
  "status": "booked",
  "version": 1,
  "created_at": "2024-10-20T12:00:00+09:00"
}
```
- エラー例:
  - 404: slot が存在しない/予約不可（status!=open）
  - 409: capacity exceeded / duplicate reservation (user_id, slot_id)

---
## 予約確認（ユーザー自身）
GET /me/reservations
- クエリ: status 任意フィルタ（例: booked）。
- レスポンス 200:
```json
{
  "items": [
    {
      "reservation_id": 100,
      "slot_id": 1,
      "shop_id": 10,
      "seat_id": null,
      "starts_at": "2024-10-20T18:00:00+09:00",
      "ends_at": "2024-10-20T19:00:00+09:00",
      "party_size": 2,
      "status": "booked",
      "version": 1
    }
  ]
}
```

GET /me/reservations/{reservation_id}
- レスポンス 200: 上記の1件版。
- 404: 他人の予約 or 不在。

---
## 予約キャンセル（ユーザー）
POST /me/reservations/{reservation_id}/cancel
- ボディ: `{ "version": 1 }`（楽観ロック用、任意で If-Match ヘッダでも可）
- 遷移: booked → cancel_pending → cancelled（最小運用なら booked → cancelled を即時でも可）
- レスポンス 200:
```json
{
  "reservation_id": 100,
  "status": "cancelled",
  "version": 2
}
```
- エラー:
  - 404: 他人の予約 or 不在。
  - 409: version 不一致（同時更新）

---
## 予約枠作成（店舗向け、管理API想定）
POST /shops/{shop_id}/slots
- ボディ:
```json
{
  "seat_id": null,
  "starts_at": "2024-10-20T18:00:00+09:00",
  "ends_at": "2024-10-20T19:00:00+09:00",
  "capacity": 4,
  "status": "open"
}
```
- レスポンス 201: 作成済み slot 情報。
- エラー 409: 同一 (shop_id, seat_id, starts_at, ends_at) が既に存在。

---
## エラーレスポンス例
```json
{
  "error": {
    "code": "capacity_exceeded",
    "message": "No remaining capacity for this slot"
  }
}
```

## 実装メモ
- 時刻は入出力とも JST(+09:00)。DB には UTC で保存（内部で変換）。
- capacity チェックとロックは ADR 0002 のポリシーに従う。
- version はレスポンスに常に含め、更新系でクライアントが送る（If-Match or body）。
