# Project Title

Reservation System Tutorial

# Project Schedule

https://github.com/users/kai-5908/projects/1

タスク管理は以下の方法に従う

https://dev.classmethod.jp/articles/scrum-backlog-github-projects/

## Description

予約システムを開発するチュートリアルをするためのリポジトリ

## Getting Started

### Dependencies

* Describe any prerequisites, libraries, OS version, etc., needed before installing program.
* ex. Windows 10

### 環境構築

VSCodeのdevcontainerでメインコンテナとdbコンテナが起動する

#### Frontendの環境構築

```
cd frontend
npm install
```

#### Frontendサーバの起動

```
cd frontend
yarn start
```

#### Backendの環境構築

```
cd backend
poetry install
```

#### Backendサーバの起動

```
cd backend
uvicorn app.main:app --host 0.0.0.0 --port 8000 --reload
```

#### DBサーバへのアクセス

```
mysql -u user -p -h db --port 3306
```

### 監査ログとリクエストID

- 予約関連のイベント（作成/キャンセル/リスケなど）は構造化JSONで stdout に出力されます。`X-Request-ID` ヘッダーを付けるとログに含まれ、相関が取りやすくなります（未指定時はサーバ側で生成されレスポンスにも付与されます）。
