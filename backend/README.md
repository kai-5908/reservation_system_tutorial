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
