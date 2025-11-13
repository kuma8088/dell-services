# 統合管理ポータル - ローカル開発・検証ガイド

**対象**: AI開発者、人間開発者
**作成日**: 2025-11-13
**前提**: Docker、Node.js、Python 3.11+ がインストール済み

---

## 📋 このドキュメントの目的

Claude Codeが実装した統合ポータルを、ローカル環境で検証するための手順を提供します。

---

## 🚀 クイックスタート（5分）

### 1. 前提条件確認

```bash
# Dockerが稼働していることを確認
docker --version
docker compose version

# Node.jsバージョン確認（18.x以上推奨）
node --version

# Python バージョン確認（3.11以上推奨）
python3 --version
```

### 2. 統合ポータルの起動

```bash
# プロジェクトルートへ移動
cd /opt/onprem-infra-system/project-root-infra/services/unified-portal

# Docker Composeで全サービス起動
docker compose up -d

# ログ確認
docker compose logs -f
```

### 3. アクセス確認

- **Frontend**: http://172.20.0.91:5173
- **Backend API**: http://172.20.0.90:8000
- **API Docs**: http://172.20.0.90:8000/docs（Swagger UI）
- **Nginx Proxy**: http://172.20.0.92:80

### 4. 動作確認

```bash
# Backend ヘルスチェック
curl http://172.20.0.90:8000/health

# 期待される出力
# {"status":"healthy","service":"unified-portal-backend","version":"0.1.0"}

# Frontend アクセス確認
curl -I http://172.20.0.91:5173

# 期待される出力
# HTTP/1.1 200 OK
```

---

## 🛠️ ローカル開発環境のセットアップ

### Backend（FastAPI）

#### 1. 仮想環境作成

```bash
cd /opt/onprem-infra-system/project-root-infra/services/unified-portal/backend

# Python仮想環境作成
python3 -m venv venv

# 仮想環境有効化
source venv/bin/activate

# 依存関係インストール
pip install -r requirements.txt
```

#### 2. 環境変数設定

```bash
# .envファイル作成
cat > .env << 'EOF'
# Database
DATABASE_URL=mysql+pymysql://usermgmt:YOUR_PASSWORD@172.20.0.60:3306/unified_portal

# JWT
JWT_SECRET_KEY=your-secret-key-change-in-production
JWT_ALGORITHM=HS256
JWT_ACCESS_TOKEN_EXPIRE_MINUTES=30

# CORS
CORS_ORIGINS=["http://172.20.0.91:5173","http://localhost:5173"]

# Docker
DOCKER_HOST=unix:///var/run/docker.sock
EOF
```

#### 3. データベース初期化

```bash
# Alembic マイグレーション実行（将来実装）
# alembic upgrade head

# または、直接SQLで初期化
docker compose exec mariadb mysql -u usermgmt -p -e "CREATE DATABASE IF NOT EXISTS unified_portal;"
```

#### 4. 開発サーバー起動

```bash
# ホットリロード有効で起動
uvicorn app.main:app --host 0.0.0.0 --port 8000 --reload
```

#### 5. 動作確認

```bash
# 別ターミナルで
curl http://localhost:8000/health

# API ドキュメント確認
open http://localhost:8000/docs
```

---

### Frontend（React + Vite）

#### 1. 依存関係インストール

```bash
cd /opt/onprem-infra-system/project-root-infra/services/unified-portal/frontend

# npm インストール
npm install
```

#### 2. 環境変数設定

```bash
# .env.local ファイル作成
cat > .env.local << 'EOF'
VITE_API_BASE_URL=http://172.20.0.90:8000/api/v1
VITE_WS_BASE_URL=ws://172.20.0.90:8000/ws
EOF
```

#### 3. 開発サーバー起動

```bash
# Vite 開発サーバー起動（ホットリロード有効）
npm run dev
```

#### 4. 動作確認

```bash
# ブラウザでアクセス
open http://localhost:5173
```

---

## 🧪 テスト実行

### Backend テスト

```bash
cd /opt/onprem-infra-system/project-root-infra/services/unified-portal/backend

# 全テスト実行
pytest

# カバレッジ付きテスト
pytest --cov=app --cov-report=html

# 特定のテストのみ実行
pytest tests/test_auth.py -v

# カバレッジレポート確認
open htmlcov/index.html
```

### Frontend テスト

```bash
cd /opt/onprem-infra-system/project-root-infra/services/unified-portal/frontend

# Unit テスト（Vitest）
npm run test

# カバレッジ付きテスト
npm run test:coverage

# E2E テスト（Playwright）
npm run test:e2e
```

---

## 🔍 デバッグ方法

### Backend デバッグ

#### 1. ログレベル変更

```bash
# app/config.py で LOG_LEVEL を DEBUG に変更
LOG_LEVEL=DEBUG uvicorn app.main:app --reload
```

#### 2. SQLクエリログ確認

```python
# app/database.py で SQLALCHEMY_ECHO を True に
SQLALCHEMY_ECHO = True
```

#### 3. VSCode デバッガー設定

`.vscode/launch.json`:

```json
{
  "version": "0.2.0",
  "configurations": [
    {
      "name": "Python: FastAPI",
      "type": "python",
      "request": "launch",
      "module": "uvicorn",
      "args": [
        "app.main:app",
        "--reload"
      ],
      "jinja": true
    }
  ]
}
```

### Frontend デバッグ

#### 1. React Developer Tools

ブラウザ拡張機能をインストール:
- [React Developer Tools](https://react.dev/learn/react-developer-tools)

#### 2. ネットワークリクエスト確認

```tsx
// src/lib/api.ts でログ追加
axios.interceptors.request.use((config) => {
  console.log('Request:', config);
  return config;
});

axios.interceptors.response.use((response) => {
  console.log('Response:', response);
  return response;
});
```

#### 3. VSCode デバッガー設定

`.vscode/launch.json`:

```json
{
  "version": "0.2.0",
  "configurations": [
    {
      "name": "Chrome: Frontend",
      "type": "chrome",
      "request": "launch",
      "url": "http://localhost:5173",
      "webRoot": "${workspaceFolder}/frontend/src"
    }
  ]
}
```

---

## 🐛 トラブルシューティング

### Backend

#### 問題: `ModuleNotFoundError: No module named 'app'`

**解決策**:
```bash
# PYTHONPATH を設定
export PYTHONPATH=/opt/onprem-infra-system/project-root-infra/services/unified-portal/backend:$PYTHONPATH
```

#### 問題: データベース接続エラー

**解決策**:
```bash
# MariaDBコンテナが起動しているか確認
docker compose -f /opt/onprem-infra-system/project-root-infra/services/mailserver/docker-compose.yml ps mariadb

# 接続テスト
docker exec -it mailserver-mariadb mysql -u usermgmt -p
```

#### 問題: Docker APIアクセスエラー

**解決策**:
```bash
# Dockerソケットのパーミッション確認
ls -la /var/run/docker.sock

# ユーザーをdockerグループに追加
sudo usermod -aG docker $USER
```

### Frontend

#### 問題: `ECONNREFUSED` エラー

**解決策**:
```bash
# Backend が起動しているか確認
curl http://172.20.0.90:8000/health

# VITE_API_BASE_URL が正しいか確認
cat frontend/.env.local
```

#### 問題: `Module not found` エラー

**解決策**:
```bash
# node_modules 再インストール
rm -rf node_modules package-lock.json
npm install
```

#### 問題: ビルドエラー

**解決策**:
```bash
# TypeScript型チェック
npm run type-check

# Lintエラー確認
npm run lint
```

---

## 📊 検証チェックリスト

### 基本機能

- [ ] Backend起動確認（`/health` エンドポイント）
- [ ] Frontend起動確認（トップページ表示）
- [ ] API ドキュメント表示（`/docs`）
- [ ] CORS設定動作確認
- [ ] データベース接続確認

### 認証機能

- [ ] ログイン成功
- [ ] ログイン失敗（エラーメッセージ表示）
- [ ] JWT トークン発行
- [ ] トークン更新
- [ ] ログアウト

### ダッシュボード

- [ ] 統計情報取得
- [ ] サービス稼働状態表示
- [ ] リソース使用率グラフ表示
- [ ] アラート一覧表示

### Docker管理

- [ ] コンテナ一覧取得
- [ ] コンテナ起動
- [ ] コンテナ停止
- [ ] コンテナ再起動
- [ ] ログ表示（モーダル）

### バックアップ管理

- [ ] バックアップジョブ一覧取得
- [ ] バックアップ実行
- [ ] バックアップ履歴表示
- [ ] リストア実行

### UI/UX

- [ ] レスポンシブデザイン（モバイル・タブレット）
- [ ] ダークモード切替
- [ ] ローディング表示
- [ ] エラー表示
- [ ] 成功メッセージ表示

---

## 🔧 開発ツール

### 推奨VSCode拡張機能

```json
{
  "recommendations": [
    "ms-python.python",
    "ms-python.vscode-pylance",
    "esbenp.prettier-vscode",
    "dbaeumer.vscode-eslint",
    "bradlc.vscode-tailwindcss",
    "ms-vscode.vscode-typescript-next"
  ]
}
```

### 推奨ブラウザ拡張機能

- React Developer Tools
- Redux DevTools（状態管理確認用）
- JSON Viewer

---

## 📚 参考リソース

### Backend
- [FastAPI Documentation](https://fastapi.tiangolo.com/)
- [SQLAlchemy Documentation](https://docs.sqlalchemy.org/)
- [Pydantic Documentation](https://docs.pydantic.dev/)

### Frontend
- [React Documentation](https://react.dev/)
- [Vite Documentation](https://vitejs.dev/)
- [Tailwind CSS Documentation](https://tailwindcss.com/)
- [shadcn/ui Documentation](https://ui.shadcn.com/)
- [TanStack Query Documentation](https://tanstack.com/query/)

### Tools
- [Docker Documentation](https://docs.docker.com/)
- [Nginx Documentation](https://nginx.org/en/docs/)

---

## 📝 よくある質問（FAQ）

### Q1: ポートが既に使用されている場合は？

**A**: `docker-compose.yml` でポート番号を変更してください。

```yaml
services:
  backend:
    ports:
      - "8001:8000"  # 8000 → 8001 に変更
```

### Q2: データベースをリセットしたい

**A**: 以下のコマンドでデータベースを再初期化できます。

```bash
docker compose down -v
docker compose up -d
```

### Q3: Frontend のビルドが遅い

**A**: Vite のキャッシュをクリアしてください。

```bash
rm -rf node_modules/.vite
npm run dev
```

### Q4: Hot Reload が動作しない

**A**: WSL2を使用している場合、ファイル監視設定を変更してください。

```bash
# vite.config.ts
export default defineConfig({
  server: {
    watch: {
      usePolling: true
    }
  }
})
```

---

## 📅 更新履歴

- 2025-11-13: 初版作成（ローカル開発・検証ガイド）
