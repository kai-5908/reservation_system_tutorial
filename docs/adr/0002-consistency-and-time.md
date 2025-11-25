# ADR 0002: 整合性と時刻の扱い

- Status: Accepted (draft)
- Date: 2024-10-19

## 背景 / Context
- ADR 0001 でモデルを定義済み。本稿では同時実行制御と時刻の扱いを明確化する。
- UI は JST を表示、DB は UTC 保存、API I/O は JST (+09:00)。

## 決定 / Decision
### タイムゾーンと保存形式
- DB への保存: UTC（`DATETIME` もしくは `TIMESTAMP`）。
- API 入出力: JST (Asia/Tokyo) を ISO 8601 (+09:00) で返す/受ける。
- 変換: サーバー側で UTC↔JST を一貫して行う。全入力 datetime は tz 付き必須（naive は 400）。

### 同時実行・整合性
- 予約作成トランザクション
  - `slots` を `SELECT ... FOR UPDATE` でロック。
  - `reservations` の `party_size` 合計（`status != cancelled`）で残席を確認。
  - `reservations` の active 予約重複を確認。
  - OK なら予約を挿入（`booked`、`version=1`）。
- 一意制約
  - `slots`: (shop_id, seat_id, starts_at, ends_at)
  - `reservations`: (user_id, slot_id)
- 楽観ロック
  - `reservations.version` を更新ごとにインクリメント。
  - キャンセル API は If-Match ヘッダを優先し、無ければ Body.version を使う。どちらも無ければ 400。版数不一致は 409。

### ステータス遷移の最小ルール
- 予約: `request_pending` → `booked` → `cancelled`（ユーザーは開始 2 日前より前なら即 `cancelled`、2 日前以降は不可。店舗はいつでも `cancelled` へ遷移可）。`cancelled` への再リクエストは冪等に扱う。
- スロット: `open` のみ予約可。`closed`/`blocked` は予約不可。

## 根拠 / Rationale
- UTC 保存 + JST I/O で UI 表示を簡潔にしつつ時差問題を回避。
- スロット行ロック + キャパシティ集計で過剰予約を防ぎ、`version` を用いた楽観ロックで更新競合を安全に検知。
- If-Match 優先にすることで HTTP 標準の条件付き更新に合わせつつ、ボディ版数もフォールバックで許容。

## 影響 / Consequences
- 実装: 時刻変換と tz バリデーションの追加、キャンセル API に版数必須、キャンセル猶予ルール（開始 2 日前で締め切り）。
- API: バージョン不一致は 409、tz 無し入力は 400、キャンセル期限超過は 403。予約レスポンスは JST で返す。
- 運用: 必要に応じて `created_at`/`updated_at` をレスポンスへ追加可能。

## オープン事項 / Open Questions
- party_size と「席の占有単位」の整合（人数以外の課金単位が必要か）。
- 認証・権限の詳細（現状は簡易な user_id 取得に留める）。
- ロギング/監査項目（必要なら予約レスポンスに created_at/updated_at を含める）。
