# 統合管理ポータル デプロイメント戦略

**作成者**: kuma8088（AWS認定ソリューションアーキテクト、ITストラテジスト）
**技術スタック**: Docker Compose, FastAPI, React, Nginx, Cloudflare Tunnel

---

## 1. デプロイメント方針

### 1.1 Infrastructure as Code（IaC）

| レイヤー | ツール | 管理対象 |
|---------|-------|---------|
| コンテナ定義 | Docker Compose | 3サービスコンテナ |
| 設定管理 | Git + 環境変数 | 設定ファイル、.env |
| エッジサービス | Cloudflare Dashboard | Tunnel, DNS |

**原則**:
- すべての設定変更はGitでバージョン管理
- 手動変更は禁止（緊急時を除く）
- 変更は必ずテスト後に適用

### 1.2 ディレクトリ構成

```
services/unified-portal/
├── docker-compose.yml      # コンテナ定義
├── .env                    # 環境変数（Git管理外）
├── .env.example            # 環境変数テンプレート
├── backend/                # FastAPI Backend
│   ├── app/
│   │   ├── main.py
│   │   ├── config.py
│   │   ├── database.py
│   │   ├── models/
│   │   ├── routers/
│   │   ├── services/
│   │   └── utils/
│   ├── tests/
│   ├── requirements.txt
│   ├── Dockerfile
│   └── .env                # Backend固有設定
├── frontend/               # React Frontend
│   ├── src/
│   │   ├── components/
│   │   ├── pages/
│   │   ├── hooks/
│   │   ├── lib/
│   │   ├── stores/
│   │   └── types/
│   ├── public/
│   ├── package.json
│   ├── vite.config.ts
│   ├── Dockerfile
│   └── .env.local          # Frontend固有設定
└── nginx/                  # Nginx設定
    └── unified-portal.conf
```

---

## 2. Docker Compose戦略

### 2.1 サービス構成（3コンテナ）

| サービス | イメージ | 役割 | リソース制限 |
|---------|---------|------|-------------|
| backend | python:3.9-slim | FastAPI APIサーバー | CPU: 1.0, MEM: 1G |
| frontend | node:20-alpine | React ビルド | CPU: 0.5, MEM: 512M |
| nginx | nginx:alpine | リバースプロキシ | CPU: 0.25, MEM: 128M |

### 2.2 Docker Compose構成

```yaml
version: '3.8'

services:
  backend:
    build:
      context: ./backend
      dockerfile: Dockerfile
    container_name: unified-portal-backend
    restart: always
    environment:
      - DATABASE_URL=${DATABASE_URL}
      - JWT_SECRET_KEY=${JWT_SECRET_KEY}
      - CLOUDFLARE_API_TOKEN=${CLOUDFLARE_API_TOKEN}
      - CLOUDFLARE_EMAIL=${CLOUDFLARE_EMAIL}
    volumes:
      - /var/run/docker.sock:/var/run/docker.sock:ro
    networks:
      portal_network:
        ipv4_address: 172.20.0.90
    healthcheck:
      test: ["CMD", "curl", "-f", "http://localhost:8000/api/health"]
      interval: 30s
      timeout: 10s
      retries: 3
      start_period: 30s

  frontend:
    build:
      context: ./frontend
      dockerfile: Dockerfile
    container_name: unified-portal-frontend
    restart: always
    environment:
      - VITE_API_BASE_URL=http://172.20.0.90:8000/api/v1
    networks:
      portal_network:
        ipv4_address: 172.20.0.91

  nginx:
    image: nginx:alpine
    container_name: unified-portal-nginx
    restart: always
    ports:
      - "8080:80"
    volumes:
      - ./nginx/unified-portal.conf:/etc/nginx/conf.d/default.conf:ro
      - ./frontend/dist:/usr/share/nginx/html:ro
    depends_on:
      - backend
      - frontend
    networks:
      portal_network:
        ipv4_address: 172.20.0.92
    healthcheck:
      test: ["CMD", "curl", "-f", "http://localhost/health"]
      interval: 30s
      timeout: 10s
      retries: 3

networks:
  portal_network:
    driver: bridge
    ipam:
      config:
        - subnet: 172.20.0.0/24
```

### 2.3 ネットワーク戦略

**設計意図**:
- Mailserver（172.20.0.0/24）と同一サブネット使用（DBアクセス用）
- 固定IPで設定管理を容易化
- 既存サービスとのリソース共有

### 2.4 ヘルスチェック設計

| サービス | チェック方法 |
|---------|------------|
| Backend | HTTP /api/health |
| Frontend | ビルド成功確認 |
| Nginx | HTTP /health |

---

## 3. デプロイメントワークフロー

### 3.1 初期デプロイ

```bash
# 1. プロジェクトディレクトリへ移動
cd /opt/onprem-infra-system/project-root-infra/services/unified-portal

# 2. 環境変数設定
cp .env.example .env
# .env を編集（DB接続情報、JWT秘密鍵等）

# 3. Backend .env設定
cp backend/.env.local-setup backend/.env
# backend/.env を編集

# 4. Frontend .env設定
cp frontend/.env.example frontend/.env.local
# frontend/.env.local を編集

# 5. 設定ファイル確認
docker compose config

# 6. ビルド・起動
docker compose build
docker compose up -d

# 7. 起動確認
docker compose ps
docker compose logs --tail=50
```

### 3.2 通常デプロイ（更新）

```bash
# 1. 変更確認
git pull origin main
docker compose config  # 設定検証

# 2. ビルド
docker compose build

# 3. 更新適用
docker compose up -d --remove-orphans

# 4. ヘルスチェック
docker compose ps
docker compose logs --tail=50
```

### 3.3 Frontend更新のみ

```bash
# 1. Frontend ビルド
cd frontend
npm install
npm run build

# 2. Nginx リロード（静的ファイル更新）
docker compose restart nginx

# 3. 確認
curl -I http://172.20.0.92/
```

### 3.4 Backend更新のみ

```bash
# 1. Backend リビルド
docker compose build backend

# 2. Backend再起動
docker compose up -d backend

# 3. ヘルスチェック
curl http://172.20.0.90:8000/api/health
```

### 3.5 デプロイ前チェックリスト

```
□ 設定ファイルの構文チェック（docker compose config）
□ 環境変数の確認（.env の必須項目）
□ ディスク空き容量の確認
□ 現在のサービス状態の記録（docker compose ps）
□ ロールバック手順の確認
```

---

## 4. ローカル開発環境

### 4.1 Backend開発

```bash
# 1. プロジェクトディレクトリへ移動
cd /opt/onprem-infra-system/project-root-infra/services/unified-portal/backend

# 2. Python仮想環境作成・有効化
python3 -m venv venv
source venv/bin/activate

# 3. 依存関係インストール
pip install --upgrade pip
pip install -r requirements.txt

# 4. 環境変数設定
cp .env.local-setup .env
# .env を編集

# 5. 開発サーバー起動（ホットリロード有効）
uvicorn app.main:app --host 0.0.0.0 --port 8000 --reload
```

### 4.2 Frontend開発

```bash
# 1. プロジェクトディレクトリへ移動
cd /opt/onprem-infra-system/project-root-infra/services/unified-portal/frontend

# 2. 依存関係インストール
npm install

# 3. 環境変数設定
cp .env.example .env.local
# .env.local を編集

# 4. 開発サーバー起動（ホットリロード有効）
npm run dev
```

### 4.3 アクセスURL（開発環境）

| サービス | URL |
|---------|-----|
| Frontend | http://localhost:5173 |
| Backend API | http://localhost:8000 |
| API Docs (Swagger) | http://localhost:8000/docs |
| API Docs (ReDoc) | http://localhost:8000/redoc |

---

## 5. Nginx設定

### 5.1 unified-portal.conf

```nginx
upstream backend {
    server 172.20.0.90:8000;
}

server {
    listen 80;
    server_name _;

    # Frontend (React SPA)
    location / {
        root /usr/share/nginx/html;
        index index.html;
        try_files $uri $uri/ /index.html;
    }

    # Backend API
    location /api/ {
        proxy_pass http://backend;
        proxy_http_version 1.1;
        proxy_set_header Host $host;
        proxy_set_header X-Real-IP $remote_addr;
        proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for;
        proxy_set_header X-Forwarded-Proto $scheme;
    }

    # WebSocket
    location /ws/ {
        proxy_pass http://backend;
        proxy_http_version 1.1;
        proxy_set_header Upgrade $http_upgrade;
        proxy_set_header Connection "upgrade";
        proxy_set_header Host $host;
    }

    # Health check
    location /health {
        return 200 'OK';
        add_header Content-Type text/plain;
    }

    # API Docs (開発時のみ)
    location /docs {
        proxy_pass http://backend/docs;
    }

    location /redoc {
        proxy_pass http://backend/redoc;
    }

    location /openapi.json {
        proxy_pass http://backend/openapi.json;
    }
}
```

---

## 6. 環境変数管理

### 6.1 Backend環境変数

```bash
# Database
DATABASE_URL=mysql+pymysql://user:password@host:port/dbname
MAILSERVER_DATABASE_URL=mysql+pymysql://user:password@host:port/mailserver_usermgmt

# JWT
JWT_SECRET_KEY=your-secret-key-change-in-production
JWT_ALGORITHM=HS256
JWT_ACCESS_TOKEN_EXPIRE_MINUTES=30

# Cloudflare API
CLOUDFLARE_API_TOKEN=your-api-token
CLOUDFLARE_EMAIL=your-email@example.com

# Docker
DOCKER_HOST=unix:///var/run/docker.sock

# CORS
CORS_ORIGINS=["http://172.20.0.91:5173","http://localhost:5173"]
```

### 6.2 Frontend環境変数

```bash
VITE_API_BASE_URL=http://172.20.0.90:8000/api/v1
VITE_WS_BASE_URL=ws://172.20.0.90:8000/ws
```

### 6.3 .gitignore

```
.env
.env.*
!.env.example
!.env.local-setup
backend/.env
frontend/.env.local
venv/
node_modules/
__pycache__/
*.pyc
dist/
build/
```

---

## 7. Cloudflare Tunnel設定

### 7.1 Tunnel統合（本番環境）

```yaml
# config.yml (Cloudflare Tunnel)
tunnel: <tunnel-id>
credentials-file: /etc/cloudflared/credentials.json

ingress:
  # Unified Portal
  - hostname: admin.kuma8088.com
    service: http://172.20.0.92:80
    originRequest:
      noTLSVerify: true

  # フォールバック
  - service: http_status:404
```

### 7.2 DNS設定

| タイプ | 名前 | 内容 | プロキシ |
|--------|------|------|---------|
| CNAME | admin | <tunnel-id>.cfargotunnel.com | ✅ |

---

## 8. ロールバック戦略

### 8.1 Dockerロールバック

```bash
# 直前のイメージに戻す
docker compose down
git checkout HEAD~1 -- docker-compose.yml
docker compose up -d

# 特定バージョンに戻す
docker compose down
# docker-compose.yml のイメージタグを変更
docker compose up -d
```

### 8.2 設定ロールバック

```bash
# Git から復元
git checkout HEAD~1 -- nginx/unified-portal.conf
docker compose restart nginx
```

### 8.3 Frontend ロールバック

```bash
# 前回ビルドに戻す（ビルドをGitにコミットしている場合）
git checkout HEAD~1 -- frontend/dist/
docker compose restart nginx
```

---

## 9. 既存サービス統合

### 9.1 Mailserver統合

| 項目 | 設定 |
|------|------|
| DB接続 | 同一MariaDBインスタンス（172.20.0.60） |
| ネットワーク | portal_network → mailserver_network ブリッジ |
| Flask usermgmt | REST API経由でデータ取得 |

### 9.2 Blog System統合

| 項目 | 設定 |
|------|------|
| WordPress API | REST API経由で管理 |
| Nginx設定 | 個別管理（blog側のNginx参照） |

### 9.3 Cloudflare統合（✅ 完了）

| 項目 | 設定 |
|------|------|
| API認証 | Bearer Token |
| 対応操作 | Zone一覧、DNSレコードCRUD |
| プロキシ設定 | サポート |

---

## 10. テスト

### 10.1 Backend テスト

```bash
cd /opt/onprem-infra-system/project-root-infra/services/unified-portal/backend
source venv/bin/activate

# 全テスト実行
pytest

# カバレッジ付きテスト
pytest --cov=app --cov-report=html

# 特定のテストのみ実行
pytest tests/test_auth.py -v
```

### 10.2 Frontend テスト

```bash
cd /opt/onprem-infra-system/project-root-infra/services/unified-portal/frontend

# Unit テスト（Vitest）
npm run test

# カバレッジ付きテスト
npm run test:coverage

# 型チェック
npm run type-check

# Lint
npm run lint
```

---

## 11. 関連ドキュメント

| ドキュメント | 内容 |
|------------|------|
| [requirements.md](requirements.md) | 要件定義・トレードオフ分析 |
| [architecture.md](architecture.md) | システムアーキテクチャ・コンポーネント設計 |
| [operations.md](operations.md) | 運用設計・開発ガイド |
