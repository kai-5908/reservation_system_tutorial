# ユーザー予約一覧 API に status フィルタを追加する

Status: Accepted

Relevant PR:

# Context

- API スキーマ（docs/design/api-schema.md）では `GET /me/reservations` に `status` クエリフィルタが定義されているが、実装は常に全ステータスを返しており契約と乖離している。
- フロントエンドで不要データを受信しクライアント側で絞り込む必要があり、ネットワーク負荷とロジック重複が発生する。
- 予約一覧はユーザー自身の予約のみ返すため、`user_id` に加え `status` で絞り込むことによるインデックス影響は限定的（現状 `idx_res_user` がある）。

## References

- docs/design/api-schema.md — `GET /me/reservations` に `status` フィルタの仕様が記載。
- docs/implementation_plan.md — 予約確認機能の要件。

# Decision

`GET /me/reservations` にクエリパラメータ `status`（ReservationStatus の単一値）を受け付け、指定時はそのステータスのみを返す。未指定時は従来どおり全ステータスを返す。

## Reason

- API 契約との整合性を取り、クライアント側のフィルタ実装と不要データ受信を解消するため。
- 既存のユースケースやリポジトリに optional フィルタを渡す変更で完結し、影響範囲が小さい。
- 別案（クライアント側フィルタ継続、もしくは個別ステータスごとエンドポイント追加）は冗長で利点が少ない。

# Consequences

- ルーターで `status` クエリを受け取り、usecase/repository で `WHERE status = :status` を追加する分岐を実装する。
- レスポンス形は変更なし。クエリミスマッチ時は FastAPI/Pydantic がバリデーションエラー（400）を返す。
- パフォーマンス上の追加コストは軽微。必要に応じて将来的に `(user_id, status)` 複合インデックスを検討できるが現時点では不要と判断。
