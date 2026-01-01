# フロントエンド共通APIクライアント（Next.js）設計

Status: Accepted

Relevant PR:

# Context

- React/Next フロントで、各API呼び出しごとに繰り返し書く処理（Bearerトークン付与、X-Request-ID付与、JSON文字列化、401時のログインリダイレクト）を共通化したい。
- バックエンドは Bearer JWT + Request-ID による相関ログを前提としている。
- APIはJSON入出力が基本で、If-Matchなど個別ヘッダは呼び出し側で付与する方針。

## References

- docs/openapi.yaml — バックエンドAPI仕様（最新の items ラップ/ status フィルタ対応）。
- docs/design/frontend-mvp-plan.md — MVP方針（トークンはローカルストレージ保持、Request-ID自動付与）。

# Decision

- `src/api/client.ts` に薄い fetch ラッパー `apiFetch` を実装し、共通処理を集約する。
- 機能:
  - Authorization: localStorage のトークンを Bearer ヘッダに自動付与。
  - Request-ID: UUIDで生成し `X-Request-ID` に自動付与（未指定時）。
  - JSON送信: `jsonBody` を自動 stringfy、またはプレーンオブジェクトを body に渡した場合も stringify。
  - 401応答: `/login` にリダイレクトし、呼び出し側にエラーを返す。
  - 戻り値: `{ data, error }` のユニオン型 (`ApiResponse<T>`) でラップ。
- トークン保存ヘルパー `setToken` を提供（localStorage に保存/削除）。
- 呼び出し側が If-Match 等の個別ヘッダやクエリパラメータを付ける前提とし、メソッドは必ず明示して使う（デフォルトは GET）。
- Jest + ts-jest + jsdom でユニットテストを追加し、上記の基本挙動を検証。

## Reason

- 毎回の重複記述（Authorization、Request-ID、JSON stringify、401ハンドリング）を避け、ミスを減らすため。
- Request-ID をフロントから送ることで監査ログの相関を取りやすくするため（バックエンドでも生成されるが、整合性を高める）。
- シンプルな戻り値構造で呼び出し側のエラーハンドリングを容易にするため。
- 未認証時はフロント側で早期にログイン誘導を行うほうがUXが明確になるため。

# Consequences

- POST/PUT/PATCH 時は `method` を明示し忘れると GET になるため、呼び出し側が注意するか薄いラッパー追加を検討。
- If-Match 等の個別ヘッダは自動付与しないため、各API呼び出しで指定する必要がある。
- 401で自動リダイレクトする挙動が不要な画面がある場合は、ラッパーを分ける/オプション化を検討する余地あり。
- テスト実行には `jest-environment-jsdom` や `@testing-library/jest-dom` などの開発依存が必要。***
