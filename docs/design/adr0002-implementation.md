# 実装設計: ADR 0002（整合性と時刻）

## スコープ
- ADR0002 に沿ったバックエンド方針: キャンセルの楽観ロック（If-Match 優先の版数チェック + `cancel_pending` 遷移）、UTC 保存 + JST I/O、tz 付き入力の強制。
- 対象コード: `app/usecases/reservations.py`、`app/routers/reservations.py`、`app/utils/time.py`、`app/infrastructure/repositories.py`。
- スキーマは ADR0001 / migration-0001.sql で充足。追加マイグレーション不要。

## 現状とギャップ
- UTC 保存 + JST 返却はおおむね実装済み（`utc_naive_to_jst` と Pydantic encoder）。
- 予約作成はスロット行ロック + 残席計算 + 重複チェックを実施済み。
- 未対応/不足:
  - キャンセルで `version` を確認せず強制 `cancelled`。
  - `cancel_pending` ステップ未導入。
  - 入力 datetime の tz 未指定を 400 で弾くチェックが徹底されていない。

## 予約作成フロー（再確認）
1. トランザクション開始。
2. `slots` を `SELECT ... FOR UPDATE WHERE id=:slot_id` でロック。
3. 同一トランザクション内で集計:
   - `user_has_active`: `status != cancelled` のユーザー予約有無。
   - `sum_reserved`: `status != cancelled` の `party_size` 合計。
4. `SlotSnapshot` を組み立てて `validate_reservation`（status=open、重複なし、capacity、party_size>0）を実行。
5. `status=booked`、`version=1`、UTC naive の `created_at/updated_at` で挿入。

## キャンセルフロー（楽観ロック + `cancel_pending`）
1. トランザクション開始、予約+スロットを `FOR UPDATE` で取得。
2. 所有者チェック（user_id 一致）。
3. 版数チェック:
   - If-Match ヘッダがあれば優先、無ければ Body.version。
   - どちらも無ければ 400、不一致なら 409。
4. 冪等性: `cancelled` / `cancel_pending` はそのまま返す。
5. 遷移: `booked|request_pending|cancel_pending -> cancel_pending`（店舗承認フローを想定）。`cancelled` への遷移は承認処理側で別途行う想定。
6. `version += 1`、`updated_at = now_utc_naive()` で更新。

## 時刻の扱い
- 保存: ORM は `DateTime(timezone=False)` で UTC naive を保持。
- 入力: すべて tz 付き必須。naive は 400。
- 変換: DB 書き込み/検索前に `to_utc_naive`、レスポンスで `utc_naive_to_jst`。
- レスポンス: Pydantic encoder で ISO 8601 (+09:00) を返す。

## API 契約の調整
- `POST /me/reservations/{reservation_id}/cancel`
  - version 必須: If-Match を優先、無ければ Body.version。
  - version 不一致は 409、tz 無し/不正は 400、未発見/非所有は 404。
- （任意）監査が必要なら `created_at`/`updated_at`（JST）をレスポンスに追加可。

## テスト方針
- ドメイン/サービス: version 競合、冪等キャンセル、naive datetime 拒否。
- ユースケース: capacity 超過、重複予約、version 一致/不一致キャンセル、`cancel_pending` 遷移。
- （任意）DB/結合: 同時予約時のロック挙動で capacity が守られるか。

## インフラ前提
- MySQL InnoDB（REPEATABLE READ）を想定。スロット行ロックで予約競合を直列化。
- 既存インデックス（`idx_slots_shop`、`idx_slots_seat`、`idx_res_slot`、`idx_res_user`）で十分。
