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
- Mailserverの `mailserver_network` (172.20.0.0/24) が存在すること
- MariaDB コンテナ (172.20.0.60) が稼働していること

### 起動方法

```bash
# プロジェクトディレクトリへ移動
cd /opt/onprem-infra-system/project-root-infra/services/unified-portal

# 環境変数設定（初回のみ）
cat > .env << 'EOF'
USERMGMT_DB_PASSWORD=your-password-here
JWT_SECRET_KEY=your-secret-key-here
EOF

# コンテナビルド & 起動
docker compose up -d

# ログ確認
docker compose logs -f
```

### アクセス

- **Frontend**: http://172.20.0.91 (Nginx経由)
- **Backend API**: http://172.20.0.90:8000
- **API Docs**: http://172.20.0.90:8000/docs

### デフォルトログイン

- **Username**: admin
- **Password**: admin

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

- ✅ Backend基礎実装（FastAPI + 認証）
- ✅ Frontend基礎実装（React + Vite + Tailwind）
- ✅ ダッシュボードページ（統計表示）
- ✅ Docker管理（コンテナ一覧・操作）
- ✅ バックアップ管理（履歴表示・実行）

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

## 📝 関連ドキュメント

- [I001: 管理ポータル統合](../../docs/application/blog/issue/active/I001_management-portal-integration.md)
- [I002: デザイン刷新](../../docs/application/blog/issue/active/I002_portal-design-modernization.md)
- [I003: 機能拡張](../../docs/application/blog/issue/active/I003_portal-feature-enhancement.md)

## 📅 更新履歴

- 2025-11-13: プロジェクト初期化、MVP実装完了
