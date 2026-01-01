# Backend Setup (uv)

## 前提
- Python 3.11 系
- uv がインストール済み（例: `pipx install uv` または `curl -LsSf https://astral.sh/uv/install.sh | sh`）

## セットアップ（ホストで動かす場合）
```
cd backend
uv venv .venv
# Linux/WSL/macOS
source .venv/bin/activate
# Windows PowerShell
# .venv\Scripts\Activate.ps1

# 依存インストール（開発用）
uv pip install -r requirements-dev.txt
```

## 起動
```
uv run uvicorn app.main:app --reload --host 0.0.0.0 --port 8000
```

## 認証要件
- すべての API は `Authorization: Bearer <token>` が必須です（空き枠検索 `/shops/{id}/slots/availability` も含む）。
- トークンは HS256 署名のアクセストークンを前提としています。

### 環境変数（認証）
- `AUTH_SECRET`: 必須。Bearer トークン検証用のシークレット（HS256 想定）。未設定の場合は起動エラーになります。
- `AUTH_ALGORITHM`: 署名アルゴリズム（デフォルト: `HS256`）

## マイグレーション
- MySQL にテーブルを作成する場合は `backend/migrations/` の SQL を適用してください（例: `mysql -u user -p -h db reservation < backend/migrations/0001_users.sql`）。
- docs/design/migration-0001.sql にも全テーブル定義があります。

## テスト
```
uv run pytest
```

## セットアップ（docker compose の backend コンテナで動かす場合）
- すでに uv + 依存入りの /opt/venv を持ったイメージをビルドします。
- ソースコード（tests を含む）はホストから `/app` にバインドマウントされ、変更が即時反映されます。

```
# プロジェクトルートで
docker compose build backend
docker compose up -d backend db
# コンテナに入る
docker compose exec backend bash
# venv は /opt/venv にあり PATH 済み
uv run uvicorn app.main:app --reload --host 0.0.0.0 --port 8000
```

## 補足
- 依存を追加する場合は `requirements.txt` / `requirements-dev.txt` を更新してください。
- pyproject.toml はそのまま残していますが、インストールは uv の requirements ファイル経由で行います。

## 動作確認フロー（手動）
1. コンテナ/DB 起動: `make db-up`（または `docker compose up -d backend db`）
2. スキーマ適用: `make db-migrate`（必要に応じて `MIGRATION_SQL` を切り替え）
3. 開発用シード投入: `make seed-dev`（user id=1, shop id=1 を投入）
4. トークン発行（例: user_id=1, AUTH_SECRET を環境と合わせる）
   ```bash
   cd backend
   export AUTH_SECRET=devsecret
   python - <<'PY'
   from datetime import timedelta
   import os
   from app.utils.auth import create_access_token
   print(create_access_token(user_id=1, secret=os.environ["AUTH_SECRET"], expires_delta=timedelta(hours=1)))
   PY
   ```
5. 空き枠作成（JST指定、shop_id=1）
   ```bash
   curl -X POST http://localhost:8000/shops/1/slots \
     -H "Authorization: Bearer <token>" \
     -H "Content-Type: application/json" \
     -d '{
       "seat_id": null,
       "starts_at": "2024-12-01T18:00:00+09:00",
       "ends_at": "2024-12-01T19:00:00+09:00",
       "capacity": 4,
       "status": "open"
     }'
   ```
6. 空き枠検索（remaining を確認）
   ```bash
   curl "http://localhost:8000/shops/1/slots/availability?start=2024-12-01T00:00:00+09:00&end=2024-12-02T00:00:00+09:00" \
     -H "Authorization: Bearer <token>"
   ```
7. 予約作成
   ```bash
   curl -X POST http://localhost:8000/reservations \
     -H "Authorization: Bearer <token>" \
     -H "Content-Type: application/json" \
     -d '{"slot_id": <slot_id>, "party_size": 2}'
   ```
8. 予約一覧/詳細確認: `GET /me/reservations` / `GET /me/reservations/{id}`
9. キャンセル（開始2日前より前のみ可、If-Match で version 指定）
   ```bash
   curl -X POST http://localhost:8000/me/reservations/<id>/cancel \
     -H "Authorization: Bearer <token>" \
     -H 'If-Match: "1"'
   ```
10. リスケ（同一ショップ、空き枠に移動）
    ```bash
    curl -X POST http://localhost:8000/me/reservations/<id>/reschedule \
      -H "Authorization: Bearer <token>" \
      -H 'If-Match: "<current_version>"' \
      -H "Content-Type: application/json" \
      -d '{"slot_id": <new_slot_id>}'
    ```
11. 監査ログ: サーバ stdout に JSON で `reservation.created/cancelled/rescheduled` が出力され、`X-Request-ID` が含まれることを確認。

## アーキテクチャ方針（オンニオン化）
- プレゼンテーション層: `app/routers`（FastAPI ルータ、極力薄くユースケース呼び出しのみ）
- ユースケース層: `app/usecases`（予約作成/キャンセル/取得、空き枠検索などのアプリケーションサービス）
- ドメイン層: `app/domain`（ドメインサービス `services.py`、ドメイン例外 `errors.py`、リポジトリインターフェース `repositories.py`）
- インフラ層: `app/infrastructure`（SQLAlchemy 実装のリポジトリなど、外部I/O依存）
- 共通設定: `app/config.py`、DB接続: `app/database.py`
- スキーマ/I/O: `app/schemas.py`
- 依存解決: `app/deps.py`

## ディレクトリ構造（抜粋）
```
backend/
  app/
    config.py          # 設定読み込み
    database.py        # DB接続 (SQLAlchemy async engine/session)
    deps.py            # FastAPI Depends 用のDI
    main.py            # FastAPI エントリ、ルータ登録
    models.py          # ORMモデル (slots/reservations/shops/users)
    schemas.py         # Pydantic I/O
    utils/time.py      # 時刻変換 (UTC<->JST)
    domain/
      errors.py        # ドメイン例外
      services.py      # ドメインサービス（純粋ロジック）
      repositories.py  # リポジトリインターフェース
    usecases/
      slots.py         # 空き枠検索ユースケース
      reservations.py  # 予約作成/キャンセル/取得ユースケース
    infrastructure/
      repositories.py  # SQLAlchemy リポジトリ実装
    routers/
      slots.py         # /shops/{id}/slots/availability
      reservations.py  # /reservations, /me/reservations, cancel 等
  tests/
    domain/            # ドメインサービスのユニットテスト
    usecases/          # ユースケースのユニットテスト
    test_sample.py     # サンプル/スモーク
  Makefile             # uv + ruff + mypy + pytest 用ターゲット
  pyproject.toml       # 依存とツール設定 (uv/ruff/mypy/pytest など)
```
