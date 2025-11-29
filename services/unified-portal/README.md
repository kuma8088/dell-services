# 統合管理ポータル（Unified Portal）

WordPress サイトと Mailserver を一元管理する Web ポータルです。

## 概要

複数の WordPress サイト（17サイト）の管理、Docker コンテナの監視、バックアップ操作、Cloudflare DNS 設定などを単一の管理画面から行えます。

**技術スタック**:
- Backend: FastAPI (Python 3.11)
- Frontend: React 18 + TypeScript + Tailwind CSS
- Database: MariaDB（Mailserver と共用）
- Deploy: Docker Compose + Cloudflare Tunnel

## できること

| 機能 | 説明 |
|------|------|
| WordPress 管理 | サイト一覧（ドメイン別グループ化）、新規作成、削除、キャッシュクリア |
| Docker 管理 | コンテナ一覧、起動/停止/再起動操作 |
| データベース管理 | DB一覧表示、WordPress以外のDB削除防止 |
| ドメイン管理 | Cloudflare DNS レコードの CRUD 操作 |
| バックアップ | 履歴表示、手動実行 |

## クイックスタート

### 前提条件

- Docker & Docker Compose
- Mailserver の `mailserver_mailserver_network` (172.20.0.0/24) が存在
- MariaDB コンテナ (172.20.0.60) が稼働中

### 起動

```bash
cd /opt/onprem-infra-system/project-root-infra/services/unified-portal

# 初回のみ: .env ファイルを作成
# 必要な環境変数:
#   USERMGMT_DB_PASSWORD - MariaDB接続パスワード
#   JWT_SECRET_KEY - 認証用シークレット（32バイト以上）
#   ADMIN_PASSWORD - 管理者パスワード
#   CLOUDFLARE_API_TOKEN - Cloudflare API トークン（任意）

docker compose up -d
```

### アクセス

- 本番: https://admin.kuma8088.com
- ローカル: http://172.20.0.91
- API ドキュメント: https://admin.kuma8088.com/docs

### ログイン

- ユーザー名: `admin`
- パスワード: `.env` の `ADMIN_PASSWORD`

## 開発

### Backend

```bash
cd backend
python3 -m venv venv
source venv/bin/activate
pip install -r requirements.txt
uvicorn app.main:app --host 0.0.0.0 --port 8000 --reload
```

### Frontend

```bash
cd frontend
npm install
npm run dev      # 開発サーバー
npm run build    # 本番ビルド
```

### テスト

```bash
# Backend
cd backend && pytest

# Frontend
cd frontend && npm run test
```

## デプロイ

コード変更後の本番反映手順:

```bash
cd /opt/onprem-infra-system/project-root-infra/services/unified-portal

# Frontend のビルド
cd frontend && npm run build && cd ..

# コンテナ再ビルド & 起動
docker compose build frontend
docker compose up -d frontend
```

## トラブルシューティング

**DB接続エラー**:
```bash
docker exec -it mailserver-mariadb mysql -u usermgmt -p
```

**Frontend ビルドエラー**:
```bash
cd frontend
rm -rf node_modules package-lock.json
npm install
```

**キャッシュが効いて変更が反映されない**:
ブラウザのキャッシュをクリアするか、シークレットウィンドウで確認。

## ファイル構成

```
unified-portal/
├── backend/
│   ├── app/
│   │   ├── main.py           # FastAPI エントリポイント
│   │   ├── auth.py           # JWT 認証
│   │   ├── routers/          # API エンドポイント
│   │   └── services/         # ビジネスロジック
│   └── requirements.txt
├── frontend/
│   ├── src/
│   │   ├── pages/            # 各管理画面
│   │   ├── components/       # 共通コンポーネント
│   │   └── lib/api.ts        # API クライアント
│   └── package.json
├── docker-compose.yml
└── .env                      # 環境変数（Git管理外）
```

## 関連ドキュメント

- [アーキテクチャ設計](../../docs/application/unified-portal/ARCHITECTURE.md)
- [ローカル開発ガイド](../../docs/application/unified-portal/LOCAL_DEVELOPMENT.md)
