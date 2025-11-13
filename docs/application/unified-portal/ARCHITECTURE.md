# 統合管理ポータル - アーキテクチャ設計

**関連Issue**: I001, I002, I003
**作成日**: 2025-11-13
**ステータス**: 設計中

---

## 📋 概要

Dell環境全体（Blog System + Mailserver）を統合管理するWebベースのポータルを構築します。

### 目標
- Blog System（16 WordPressサイト）とMailserverの一元管理
- モダンなUI/UX（ダークモード対応、レスポンシブ）
- リアルタイム監視とアラート
- セキュアな認証・権限管理

---

## 🏗️ アーキテクチャ

### 技術スタック

#### Backend
- **Framework**: FastAPI 0.109+
  - 高速・非同期処理
  - 自動API ドキュメント生成（OpenAPI/Swagger）
  - 型安全（Pydantic）
- **Database**: MariaDB（既存環境を共用）
- **Authentication**: JWT + OAuth2
- **WebSocket**: FastAPI native support（リアルタイム更新用）

#### Frontend
- **Framework**: React 18 + TypeScript
- **Build Tool**: Vite 5（高速ビルド）
- **UI Framework**: Tailwind CSS 3 + shadcn/ui
  - モダンなコンポーネントライブラリ
  - ダークモード対応
  - アクセシビリティ対応
- **State Management**:
  - TanStack Query（React Query）- サーバーステート管理
  - Zustand - クライアントステート管理
- **Router**: React Router v6

#### Infrastructure
- **Containerization**: Docker Compose
- **Reverse Proxy**: Nginx
- **SSL/TLS**: Cloudflare Tunnel
- **Monitoring**: Prometheus + Grafana（将来実装）

---

## 📂 ディレクトリ構造

```
services/unified-portal/
├── backend/                    # FastAPI Backend
│   ├── app/
│   │   ├── __init__.py
│   │   ├── main.py            # FastAPI application entry
│   │   ├── config.py          # Configuration management
│   │   ├── database.py        # Database connection
│   │   ├── dependencies.py    # FastAPI dependencies
│   │   ├── models/            # Pydantic models & SQLAlchemy models
│   │   │   ├── __init__.py
│   │   │   ├── user.py
│   │   │   ├── docker.py
│   │   │   └── backup.py
│   │   ├── routers/           # API routers
│   │   │   ├── __init__.py
│   │   │   ├── auth.py        # Authentication endpoints
│   │   │   ├── dashboard.py   # Dashboard data endpoints
│   │   │   ├── docker.py      # Docker management
│   │   │   ├── backup.py      # Backup management
│   │   │   └── websocket.py   # WebSocket endpoints
│   │   ├── services/          # Business logic
│   │   │   ├── __init__.py
│   │   │   ├── auth_service.py
│   │   │   ├── docker_service.py
│   │   │   └── backup_service.py
│   │   └── utils/             # Utilities
│   │       ├── __init__.py
│   │       ├── security.py
│   │       └── logger.py
│   ├── tests/                 # Backend tests
│   ├── requirements.txt
│   └── Dockerfile
│
├── frontend/                   # React Frontend
│   ├── src/
│   │   ├── main.tsx           # Application entry
│   │   ├── App.tsx            # Root component
│   │   ├── components/        # Reusable components
│   │   │   ├── ui/           # shadcn/ui components
│   │   │   ├── layout/       # Layout components
│   │   │   └── features/     # Feature-specific components
│   │   ├── pages/            # Page components
│   │   │   ├── Dashboard.tsx
│   │   │   ├── DockerManagement.tsx
│   │   │   ├── BackupManagement.tsx
│   │   │   └── Login.tsx
│   │   ├── hooks/            # Custom React hooks
│   │   ├── lib/              # Utilities
│   │   │   ├── api.ts        # API client
│   │   │   └── utils.ts
│   │   ├── stores/           # Zustand stores
│   │   └── types/            # TypeScript types
│   ├── public/
│   ├── package.json
│   ├── tsconfig.json
│   ├── vite.config.ts
│   ├── tailwind.config.js
│   └── Dockerfile
│
├── nginx/                      # Nginx configuration
│   └── unified-portal.conf
│
├── docker-compose.yml
└── README.md
```

---

## 🔌 API設計

### Base URL
```
http://172.20.0.90:8000/api/v1
```

### Endpoints

#### Authentication
- `POST /auth/login` - ログイン
- `POST /auth/logout` - ログアウト
- `POST /auth/refresh` - トークン更新
- `GET /auth/me` - 現在のユーザー情報

#### Dashboard
- `GET /dashboard/stats` - システム統計情報
- `GET /dashboard/services` - サービス稼働状態
- `GET /dashboard/alerts` - アラート一覧

#### Docker Management
- `GET /docker/containers` - コンテナ一覧
- `POST /docker/containers/{id}/start` - コンテナ起動
- `POST /docker/containers/{id}/stop` - コンテナ停止
- `POST /docker/containers/{id}/restart` - コンテナ再起動
- `GET /docker/containers/{id}/logs` - コンテナログ取得
- `GET /docker/images` - イメージ一覧
- `GET /docker/networks` - ネットワーク一覧

#### Backup Management
- `GET /backup/jobs` - バックアップジョブ一覧
- `POST /backup/jobs` - バックアップ実行
- `GET /backup/jobs/{id}` - バックアップ詳細
- `POST /backup/restore` - リストア実行
- `GET /backup/history` - バックアップ履歴

#### System Monitoring
- `GET /system/resources` - システムリソース（CPU, Memory, Disk）
- `GET /system/logs` - システムログ
- `GET /system/alerts` - アラート設定

#### WebSocket
- `WS /ws/logs` - リアルタイムログストリーム
- `WS /ws/stats` - リアルタイム統計情報

---

## 🎨 UI/UX設計

### デザインシステム

#### カラーパレット
- **Primary**: Blue-600 (`#2563eb`)
- **Secondary**: Slate-700 (`#334155`)
- **Accent**: Green-500 (`#22c55e`)
- **Error**: Red-500 (`#ef4444`)
- **Warning**: Yellow-500 (`#eab308`)
- **Background (Light)**: White (`#ffffff`)
- **Background (Dark)**: Slate-950 (`#020617`)

#### タイポグラフィ
- **Font Family**: Inter, system-ui, sans-serif
- **Headings**: Font-weight 600-700
- **Body**: Font-weight 400

#### レイアウト
- **サイドバーナビゲーション**（左側固定）
- **トップバー**（ユーザー情報、通知、設定）
- **メインコンテンツエリア**（グリッド/カードレイアウト）

### ページ構成

1. **ダッシュボード** (`/`)
   - システム統計カード
   - サービス稼働状態
   - 最近のアラート
   - リソース使用率グラフ

2. **Docker管理** (`/docker`)
   - コンテナ一覧テーブル
   - 操作ボタン（起動/停止/再起動）
   - ログビューア（モーダル）

3. **バックアップ管理** (`/backup`)
   - バックアップジョブ一覧
   - バックアップ実行フォーム
   - バックアップ履歴
   - リストア機能

4. **ログビューア** (`/logs`)
   - リアルタイムログストリーム
   - フィルタリング・検索機能
   - ログダウンロード

5. **設定** (`/settings`)
   - アラート設定
   - ユーザー管理
   - システム設定

---

## 🔐 セキュリティ

### 認証・認可
- **JWT Token-based authentication**
- **Role-based access control (RBAC)**
  - `admin`: 全権限
  - `operator`: 読み取り + 基本操作
  - `viewer`: 読み取りのみ

### セキュリティ対策
- HTTPS必須（Cloudflare Tunnel）
- CSRF保護
- Rate limiting
- Input validation（Pydantic）
- SQL Injection対策（SQLAlchemy ORM）
- XSS対策（React自動エスケープ）

---

## 🚀 デプロイメント

### Docker Compose構成

```yaml
version: '3.8'

services:
  backend:
    build: ./backend
    container_name: unified-portal-backend
    restart: always
    environment:
      - DATABASE_URL=mysql+pymysql://...
      - JWT_SECRET_KEY=...
    networks:
      portal_network:
        ipv4_address: 172.20.0.90

  frontend:
    build: ./frontend
    container_name: unified-portal-frontend
    restart: always
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
      - ./nginx/unified-portal.conf:/etc/nginx/conf.d/default.conf
    networks:
      portal_network:
        ipv4_address: 172.20.0.92

networks:
  portal_network:
    driver: bridge
    ipam:
      config:
        - subnet: 172.20.0.0/24
```

---

## 📊 監視・ログ

### ログ管理
- **Backend**: Structured logging (JSON format)
- **Frontend**: Console logging + Error boundary
- **Log aggregation**: 将来的にELK stack導入検討

### メトリクス
- API レスポンスタイム
- エラーレート
- リクエスト数
- システムリソース使用率

---

## 🛣️ 実装ロードマップ

### Phase 1: MVP（2週間）
- [ ] Backend基礎実装（FastAPI + 認証）
- [ ] Frontend基礎実装（React + Vite + Tailwind）
- [ ] ダッシュボードページ（統計表示のみ）
- [ ] Docker管理（読み取りのみ）

### Phase 2: Core Features（2週間）
- [ ] Docker管理（操作機能）
- [ ] バックアップ管理（実行・履歴）
- [ ] ログビューア（リアルタイム）
- [ ] WebSocket統合

### Phase 3: Advanced Features（2週間）
- [ ] アラート機能
- [ ] レポート生成
- [ ] ユーザー管理
- [ ] 設定画面

### Phase 4: Production Hardening（1週間）
- [ ] テスト（Unit + Integration + E2E）
- [ ] パフォーマンス最適化
- [ ] セキュリティ監査
- [ ] ドキュメント整備

---

## 📚 関連ドキュメント

- [ローカル開発・検証ガイド](./LOCAL_DEVELOPMENT.md)
- [API仕様書](./API_SPECIFICATION.md)（自動生成）
- [デプロイメントガイド](./DEPLOYMENT.md)
- I001: 管理ポータル統合
- I002: デザイン刷新
- I003: 機能拡張

---

## 📅 更新履歴

- 2025-11-13: 初版作成（アーキテクチャ設計）
