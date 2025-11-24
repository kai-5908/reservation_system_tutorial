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
