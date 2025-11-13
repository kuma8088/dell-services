# 統合管理ポータル（Unified Portal）

Blog System と Mailserver を統合管理する Web ベースのポータルシステムです。

## 📋 概要

- **Backend**: FastAPI（Python 3.11+）
- **Frontend**: React 18 + Vite + TypeScript + Tailwind CSS + shadcn/ui
- **Database**: MariaDB（既存Mailserver環境を共用）
- **Deployment**: Docker Compose

## 🚀 クイックスタート

### 前提条件

- Docker & Docker Compose がインストールされていること
- Mailserverの `mailserver_mailserver_network` (172.20.0.0/24) が存在すること
- MariaDB コンテナ (172.20.0.60) が稼働していること

### 起動方法

```bash
# プロジェクトディレクトリへ移動
cd /opt/onprem-infra-system/project-root-infra/services/unified-portal

# 環境変数設定（初回のみ）
# .env ファイルを作成し、以下の変数を設定:
# USERMGMT_DB_PASSWORD: MariaDB接続パスワード
# JWT_SECRET_KEY: 32-byte hex (セキュアな乱数)
# ADMIN_PASSWORD: 管理者パスワード (セキュアな乱数)
# CLOUDFLARE_API_TOKEN: Cloudflare API トークン（オプション）

# コンテナビルド & 起動
docker compose up -d

# ログ確認
docker compose logs -f
```

### アクセス

**ローカル環境**:
- **Frontend**: http://172.20.0.91 (Nginx経由)
- **Backend API**: http://172.20.0.92:8000
- **API Docs**: http://172.20.0.92:8000/docs

**本番環境** (Cloudflare Tunnel):
- **Portal**: https://admin.kuma8088.com
- **API Docs**: https://admin.kuma8088.com/docs

### 認証情報

- **Username**: admin
- **Password**: (`.env` ファイルの `ADMIN_PASSWORD`)

⚠️ **セキュリティ**: 本番環境では必ず `.env` ファイルで強力なパスワードを設定してください。

## 📚 ドキュメント

- [アーキテクチャ設計](../../docs/application/unified-portal/ARCHITECTURE.md)
- [ローカル開発・検証ガイド](../../docs/application/unified-portal/LOCAL_DEVELOPMENT.md)

## 🛠️ 開発

### Backend（FastAPI）

```bash
cd backend

# 仮想環境作成
python3 -m venv venv
source venv/bin/activate

# 依存関係インストール
pip install -r requirements.txt

# 開発サーバー起動
uvicorn app.main:app --host 0.0.0.0 --port 8000 --reload
```

### Frontend（React + Vite）

```bash
cd frontend

# 依存関係インストール
npm install

# 開発サーバー起動
npm run dev

# ビルド
npm run build
```

## 🧪 テスト

### Backend

```bash
cd backend
pytest
pytest --cov=app
```

### Frontend

```bash
cd frontend
npm run test
npm run test:coverage
```

## 📋 主な機能

### Phase 1 (MVP) - 完了

**認証システム**:
- ✅ JWT認証実装 (HS256, 30分有効期限)
- ✅ Login API (/api/v1/auth/login)
- ✅ ユーザー確認 API (/api/v1/auth/me)
- ✅ AuthContext (グローバル認証状態管理)
- ✅ ProtectedRoute (認証ガード)
- ✅ Login ページ (実 API 統合)

**管理機能**:
- ✅ ダッシュボードページ（統計表示）
- ✅ Docker管理（コンテナ一覧・操作）
- ✅ バックアップ管理（履歴表示・実行）
- ✅ Database管理（UI層）
- ✅ PHP管理（UI層）
- ✅ Security管理（UI層）
- ✅ WordPress管理（UI層）
- ✅ Domain管理（Cloudflare DNS API統合）

**インフラ**:
- ✅ Docker Compose 環境構築
- ✅ Nginx リバースプロキシ設定
- ✅ Cloudflare Tunnel 対応 (admin.kuma8088.com)

### Phase 2 - 予定

- [ ] Docker管理（ログビューア・WebSocket）
- [ ] バックアップ管理（リストア機能）
- [ ] システム監視（CPU/メモリ/ディスク）
- [ ] アラート機能

### Phase 3 - 予定

- [ ] ユーザー管理
- [ ] レポート生成
- [ ] 設定画面
- [ ] Mailserver連携

## 🔧 トラブルシューティング

### Backend起動エラー

```bash
# データベース接続確認
docker exec -it mailserver-mariadb mysql -u usermgmt -p

# Dockerソケット権限確認
ls -la /var/run/docker.sock
```

### Frontend ビルドエラー

```bash
# node_modules 再インストール
rm -rf node_modules package-lock.json
npm install
```

## 🌐 Cloudflare Tunnel デプロイ

### 設定手順

1. **Cloudflare Zero Trust Dashboard** にアクセス:
   - https://one.dash.cloudflare.com/
   - Networks → Tunnels → blog-tunnel → Public Hostnames

2. **Public Hostname を追加**:
   - Hostname: `admin.kuma8088.com`
   - Service Type: `HTTP`
   - Service URL: `http://172.20.0.91:80`
   - HTTP Settings:
     - HTTP Host Header: `admin.kuma8088.com`

3. **動作確認**:
   - https://admin.kuma8088.com にアクセス
   - Login 画面が表示される
   - 認証情報でログイン成功

詳細: [docs/cloudflare-tunnel-setup.md](docs/cloudflare-tunnel-setup.md)

## 📝 関連ドキュメント

- [Cloudflare Tunnel 設定ガイド](docs/cloudflare-tunnel-setup.md)
- [I001: 管理ポータル統合](../../docs/application/blog/issue/active/I001_management-portal-integration.md)
- [I002: デザイン刷新](../../docs/application/blog/issue/active/I002_portal-design-modernization.md)
- [I003: 機能拡張](../../docs/application/blog/issue/active/I003_portal-feature-enhancement.md)
- [I006: Redis Object Cache](../../docs/application/blog/issue/completed/I006_redis-object-cache.md)

## 📅 更新履歴

- 2025-11-13:
  - プロジェクト初期化、MVP実装完了
  - JWT認証システム実装完了
  - Docker環境構築完了（env_file対応、IP競合解決）
  - Cloudflare Tunnel対応（admin.kuma8088.com）
  - Cloudflare DNS API統合完了
