# フロントエンド概要

このプロジェクトは Create React App（React 18）で構成されています。状態管理や UI ライブラリは特に導入していないシンプルな構成です。

## 開発コマンド

- 開発サーバー起動: `npm start` （http://localhost:3000）
- テスト実行: `npm test`
- 本番ビルド: `npm run build`
- 依存インストール: `npm install`

## 技術スタック

- React (CRA)
- 状態管理: なし（必要に応じて React Hooks で実装）
- UI ライブラリ: なし（必要に応じて後付け）

## 補足

- API コントラクト変更（空き枠レスポンスの `items` ラップ、予約一覧の `status` フィルタ）に追随する想定です。
- 認証トークンは Bearer でヘッダ送信してください。
