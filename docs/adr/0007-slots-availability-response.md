# 空き枠一覧 API のレスポンスを items ラップに統一する

Status: Accepted

Relevant PR:

# Context

- API スキーマ（docs/design/api-schema.md）では `GET /shops/{shop_id}/slots/availability` のレスポンスは `items` キーにスロット配列をラップする形で定義されている。
- 現実装は配列をそのまま返しており、スキーマと乖離があるためクライアント実装でのハードコードや互換レイヤが必要になっている。
- 既に利用中のクライアントがある場合は互換性に注意が必要だが、設計ドキュメントに合わせて揃える方針。

## References

- docs/design/api-schema.md — 空き枠 API のレスポンス例に `items` ラップが明記されている。
- docs/implementation_plan.md — 空き枠検索機能のスコープ。

# Decision

`GET /shops/{shop_id}/slots/availability` のレスポンスを `{ "items": [...] }` の形に変更し、スロット配列を `items` に格納する。スキーマと実装を一致させる。

## Reason

- クライアント実装を設計どおりに簡素化し、契約の一貫性を確保するため。
- 差分はレスポンスラップのみで、既存ロジックやドメインへの影響が軽微。
- 別案（スキーマを配列返却に変更する）は API 文書を後追いで変えることになり、他クライアントとの整合性を損ねる。

# Consequences

- ルーターで返却形を `{"items": list}` に変更し、Pydantic スキーマが必要なら項目を追加する。
- 既存クライアントは `items` ラップに対応するよう修正が必要（ドキュメントと一致する形）。
- 後方互換が懸念される場合は一時的に両対応（フラグなど）を検討できるが、基本は文書化された形に統一する。
