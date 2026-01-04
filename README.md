# Reservation System Tutorial

FastAPI（Python 3.11）+ Next.js（TypeScript）で予約システムを作るチュートリアル用リポジトリです。DB は MySQL 8 を前提に UTC で時刻を保存します。

- プロジェクトボード: https://github.com/users/kai-5908/projects/1

## リポジトリ構成
- `backend/`: FastAPI アプリ（uv 使用、`uv.lock` で固定）。`app/` 配下にドメイン/ユースケース/ルータ実装、`migrations/` に初期スキーマと開発用シード。
- `frontend/`: Next.js 16（React 19）アプリ。API 先は `NEXT_PUBLIC_API_BASE`（未指定時は http://localhost:8000）。
- `docs/`: 要件/設計資料（ER 図、OpenAPI、マイグレーション SQL など）。
- ルート `Makefile`: Docker Compose を使った DB/バックエンド/フロントエンドの起動・マイグレーション・シード。

## 事前準備
- Docker / Docker Compose, make
- ホストで動かす場合: Python 3.11 + [uv](https://github.com/astral-sh/uv)、Node.js 20 系 + npm、MySQL 8

## 起動方法（Docker Compose 推奨）
1. コンテナ起動  
   ```
   make dev-up     # backend + db
   # または frontend もまとめて
   make dev-all    # backend + db + frontend（http://localhost:3001）
   ```
2. スキーマ適用 & 開発シード投入（idempotent）  
   ```
   make db-migrate        # docs/design/migration-0001.sql を適用
   make seed-dev          # backend/migrations/seed_dev.sql を適用
   ```
3. バックエンド API を起動（backend コンテナのデフォルト CMD は sleep のため手動実行）  
   ```
   docker compose exec backend uv run uvicorn app.main:app --reload --host 0.0.0.0 --port 8000
   ```
4. フロントエンド  
   - frontend コンテナを使う場合は初回に依存を入れ（`docker compose exec frontend npm install`）、`PORT=3001` で Next.js を起動してください（`docker compose exec frontend sh -lc 'PORT=3001 npm run dev -- --hostname 0.0.0.0 --port 3001'` など）。ポートマッピングは `3001:3001` です。
   - ホストで動かす場合は後述のローカル手順を参照（3000/3001 どちらも CORS 許可済み）。

## ローカルでの動かし方（Docker を使わない場合）
### Backend
```
cd backend
uv venv .venv
source .venv/bin/activate   # Windows: .venv\Scripts\Activate.ps1
uv sync --frozen --dev      # uv.lock から依存をインストール

# 必須環境変数
export AUTH_SECRET=devsecret                           # Bearer 検証用シークレット（必須）
export DATABASE_URL="mysql+aiomysql://app:app_password@127.0.0.1:3306/reservation"  # 任意（未指定ならデフォルト）
export ECHO_SQL=0                                      # 任意。1 で SQL ログ出力

uv run uvicorn app.main:app --reload --host 0.0.0.0 --port 8000
```

### Frontend
```
cd frontend
npm install
# 3000 で動かす場合
NEXT_PUBLIC_API_BASE=http://localhost:8000 PORT=3000 npm run dev -- --hostname 0.0.0.0 --port 3000
# 3001 で分けたい場合（CORS 許可済み）
# NEXT_PUBLIC_API_BASE=http://localhost:8000 PORT=3001 npm run dev -- --hostname 0.0.0.0 --port 3001
```

## 開発者向け動作確認フロー（API 手動確認）
1. DB とバックエンドを起動  
   - Docker Compose 利用時: `make dev-up` → `make db-migrate` → `make seed-dev` → `docker compose exec backend uv run uvicorn ...`  
   - ローカル DB の場合も同様にスキーマとシードを適用。
2. アクセストークンを発行（HS256 / `AUTH_SECRET` と合わせる）  
   ```bash
   cd backend
   export AUTH_SECRET=devsecret
   uv run python - <<'PY'
   from datetime import timedelta
   import os
   from app.utils.auth import create_access_token
   print(create_access_token(user_id=1, secret=os.environ["AUTH_SECRET"], expires_delta=timedelta(hours=1)))
   PY
   ```
3. 空き枠を作成（例: JST で 2024-12-01 18:00-19:00, shop_id=1）  
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
4. 空き枠検索（remaining を確認）  
   ```bash
   curl "http://localhost:8000/shops/1/slots/availability?start=2024-12-01T00:00:00+09:00&end=2024-12-02T00:00:00+09:00" \
     -H "Authorization: Bearer <token>"
   ```
5. 予約作成  
   ```bash
   curl -X POST http://localhost:8000/reservations \
     -H "Authorization: Bearer <token>" \
     -H "Content-Type: application/json" \
     -d '{"slot_id": <slot_id>, "party_size": 2}'
   ```
6. 予約取得・キャンセル・リスケ（If-Match でバージョン指定）  
   - 一覧/詳細: `GET /me/reservations`, `GET /me/reservations/{id}`  
   - キャンセル: `POST /me/reservations/<id>/cancel` + `If-Match: "<version>"`  
   - リスケ: `POST /me/reservations/<id>/reschedule` + `If-Match` + JSON で `slot_id`
7. 監査ログ / Request ID  
   - バックエンドの stdout に `reservation.created/cancelled/rescheduled` が構造化 JSON で出力されます。  
   - `X-Request-ID` ヘッダーを付けるとログにも同じ ID が入り、レスポンスヘッダーにも返されます（未指定ならサーバ側で生成）。  
   - Docker 利用時は `docker compose logs -f backend` で確認。

## テスト・Lint
- Backend: `cd backend && uv run pytest`、`uv run ruff check .`、`uv run mypy .`（`backend/Makefile` に lint/format/test ターゲットあり）
- Frontend: `cd frontend && npm test`、`npm run lint`
