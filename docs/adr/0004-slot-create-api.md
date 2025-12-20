# ADR 0004: 予約枠作成API実装方針

Status: Accepted

Relevant PR: （未作成）

# Context

- 予約システムにおいて、店舗側が予約枠を作成する API が未実装（docs/design/api-schema.md に定義済み）。
- 既存コードは予約作成/キャンセル/リスケをユースケース経由で実装済み。空き枠検索もユースケース層を通す構成。
- ドメイン・インフラ責務を分離した構造を維持しつつ、(shop_id, seat_id, starts_at, ends_at) の一意制約や時刻変換、ステータス/容量バリデーションを正しく扱う必要がある。

## References

- docs/design/api-schema.md（予約枠作成エンドポイント仕様）
- docs/design/reservation-model-impl.md（モデル実装と制約）
- ADR 0001/0002（モデルと整合性/時刻方針）

# Decision

- 予約枠作成 API をユースケース層経由で実装する。
  - ルータは FastAPI からユースケースを呼ぶ薄いレイヤに留める。
  - `usecases/slots.py` に `create_slot` を追加し、バリデーションとリポジトリ呼び出しを集約。
  - `SlotRepository` に `create` を追加し、`infrastructure/repositories.py` で SQLAlchemy INSERT を実装。
  - スキーマ: `SlotCreate`（JST入力、ge=1、status enum）、`SlotRead`（JST出力）を `schemas.py` に追加。
  - 時刻: 入力は JST (+09:00) 必須。`to_utc_naive` で保存用に変換。`starts_at < ends_at` を Pydantic + DB CHECK で二重防御。
  - ステータス: `open/closed/blocked` を受け付け、デフォルト `open`。
  - エラー: 重複 (unique violation) は 409、バリデーションエラーは 400、tz 無し入力も 400。shop 存在チェックはリポジトリが持っていないため今回は省略（将来導入可）。

## Reason

- 既存のレイヤード構造（ユースケース経由）と整合し、再利用性とテスト容易性を確保したいため。
- ルータ直書きは短期で速いが、バリデーションが分散し後続の管理 UI/API 拡張で重複/齟齬が起きやすい。
- ドメインサービス拡張は純度は高いが、現状の規模に対して過剰で初期コストが高い。ユースケース内に整理する A 案で十分。

# Consequences

- 新規エンドポイント `POST /shops/{shop_id}/slots` が追加され、予約枠を登録できる。
- スキーマ/ユースケース/リポジトリが拡張され、後続の枠更新/削除APIも同レイヤ構造で実装しやすくなる。
- テスト追加（ユースケース・ルータ）により、重複・時刻バリデーション・tz 必須・容量>=1 などが保証される。
- shop の存在確認は未実装のため、必要になれば `ShopRepository` を追加して 404 を返すよう拡張する。
