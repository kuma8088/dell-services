# 統合管理ポータル アーキテクチャ設計

**技術スタック**: FastAPI, React, TypeScript, Tailwind CSS, Docker Compose

---

## 1. システム概要

### 1.1 アーキテクチャ方針

| 方針 | 内容 |
|------|------|
| SPA + API | React SPA + FastAPI RESTful API |
| コンテナ化 | Docker Composeによる一元管理 |
| ゼロトラスト | Cloudflare Tunnel経由、内部ネットワーク限定 |
| リアルタイム | WebSocketによるリアルタイム更新 |

### 1.2 全体構成図

```
                    Internet
                        │
                        ▼
              ┌─────────────────┐
              │   Cloudflare    │
              │   (Tunnel/CDN)  │
              └────────┬────────┘
                       │
        ┌──────────────┴──────────────┐
        │     Docker Network          │
        │                             │
        │  ┌─────────────────────┐    │
        │  │      Nginx          │    │
        │  │  (リバースプロキシ)  │    │
        │  └──────────┬──────────┘    │
        │        ┌────┴────┐          │
        │        ▼         ▼          │
        │  ┌──────────┐ ┌──────────┐  │
        │  │ Frontend │ │ Backend  │  │
        │  │  React   │ │ FastAPI  │  │
        │  └──────────┘ └────┬─────┘  │
        │                    │        │
        │                    ▼        │
        │              ┌──────────┐   │
        │              │ MariaDB  │   │
        │              │  (共用)   │   │
        │              └──────────┘   │
        └─────────────────────────────┘
                       │
        ┌──────────────┴──────────────┐
        │     External Services       │
        │  ┌─────────┐ ┌───────────┐  │
        │  │ Docker  │ │Cloudflare │  │
        │  │ Socket  │ │   API     │  │
        │  └─────────┘ └───────────┘  │
        └─────────────────────────────┘
```

---

## 2. コンポーネント構成

### 2.1 コンテナ一覧

| コンテナ | イメージ | 役割 | ポート |
|---------|---------|------|--------|
| backend | python:3.9-slim | FastAPI APIサーバー | 8000 |
| frontend | node:20-alpine | React SPA（ビルド） | - |
| nginx | nginx:alpine | リバースプロキシ、静的ファイル配信 | 8080 |

### 2.2 ネットワーク設計

```yaml
networks:
  portal_network:
    driver: bridge
```

| コンテナ | 役割 |
|---------|------|
| backend | APIサーバー |
| frontend | SPAビルド |
| nginx | リバースプロキシ |

---

## 3. Backend設計（FastAPI）

### 3.1 ディレクトリ構造

```
backend/
├── app/
│   ├── __init__.py
│   ├── main.py              # FastAPIエントリポイント
│   ├── config.py            # 設定管理
│   ├── database.py          # DB接続
│   ├── dependencies.py      # 依存性注入
│   ├── models/              # Pydantic / SQLAlchemy モデル
│   │   ├── user.py
│   │   ├── docker.py
│   │   ├── domain.py        # Cloudflare DNS
│   │   └── backup.py
│   ├── routers/             # APIルーター
│   │   ├── auth.py
│   │   ├── dashboard.py
│   │   ├── docker.py
│   │   ├── domains.py       # DNS管理
│   │   ├── backup.py
│   │   └── websocket.py
│   ├── services/            # ビジネスロジック
│   │   ├── auth_service.py
│   │   ├── docker_service.py
│   │   ├── cloudflare_service.py
│   │   └── backup_service.py
│   └── utils/
│       ├── security.py
│       └── logger.py
├── tests/
├── requirements.txt
└── Dockerfile
```

### 3.2 API設計

**Base URL**: `http://localhost:8000/api/v1`

#### 認証 (Auth)
| Method | Endpoint | 説明 |
|--------|----------|------|
| POST | /auth/login | ログイン |
| POST | /auth/logout | ログアウト |
| POST | /auth/refresh | トークン更新 |
| GET | /auth/me | 現在のユーザー情報 |

#### ダッシュボード (Dashboard)
| Method | Endpoint | 説明 |
|--------|----------|------|
| GET | /dashboard/stats | システム統計情報 |
| GET | /dashboard/services | サービス稼働状態 |
| GET | /dashboard/alerts | アラート一覧 |

#### Docker管理
| Method | Endpoint | 説明 |
|--------|----------|------|
| GET | /docker/containers | コンテナ一覧 |
| POST | /docker/containers/{id}/start | コンテナ起動 |
| POST | /docker/containers/{id}/stop | コンテナ停止 |
| POST | /docker/containers/{id}/restart | コンテナ再起動 |
| GET | /docker/containers/{id}/logs | コンテナログ取得 |
| GET | /docker/images | イメージ一覧 |

#### ドメイン管理（Cloudflare DNS）
| Method | Endpoint | 説明 |
|--------|----------|------|
| GET | /domains/zones | ゾーン一覧 |
| GET | /domains/zones/{id}/records | DNSレコード一覧 |
| POST | /domains/zones/{id}/records | DNSレコード作成 |
| PUT | /domains/records/{id} | DNSレコード更新 |
| DELETE | /domains/records/{id} | DNSレコード削除 |

#### バックアップ管理
| Method | Endpoint | 説明 |
|--------|----------|------|
| GET | /backup/jobs | バックアップジョブ一覧 |
| POST | /backup/jobs | バックアップ実行 |
| GET | /backup/jobs/{id} | バックアップ詳細 |
| POST | /backup/restore | リストア実行 |
| GET | /backup/history | バックアップ履歴 |

#### WebSocket
| Endpoint | 説明 |
|----------|------|
| WS /ws/logs | リアルタイムログストリーム |
| WS /ws/stats | リアルタイム統計情報 |

---

## 4. Frontend設計（React）

### 4.1 ディレクトリ構造

```
frontend/
├── src/
│   ├── main.tsx              # エントリポイント
│   ├── App.tsx               # ルートコンポーネント
│   ├── components/
│   │   ├── ui/               # shadcn/ui コンポーネント
│   │   │   ├── button.tsx
│   │   │   ├── card.tsx
│   │   │   ├── dialog.tsx
│   │   │   └── ...
│   │   ├── layout/           # レイアウト
│   │   │   ├── Sidebar.tsx
│   │   │   ├── Header.tsx
│   │   │   └── Layout.tsx
│   │   └── features/         # 機能別コンポーネント
│   │       ├── docker/
│   │       ├── domains/
│   │       └── backup/
│   ├── pages/                # ページコンポーネント
│   │   ├── Dashboard.tsx
│   │   ├── DockerManagement.tsx
│   │   ├── DatabaseManagement.tsx
│   │   ├── DomainManagement.tsx
│   │   ├── WordPressManagement.tsx
│   │   ├── BackupManagement.tsx
│   │   └── Login.tsx
│   ├── hooks/                # カスタムフック
│   │   ├── useAuth.ts
│   │   ├── useDocker.ts
│   │   └── useDomains.ts
│   ├── lib/
│   │   ├── api.ts            # APIクライアント
│   │   └── utils.ts
│   ├── stores/               # Zustand ストア
│   │   ├── authStore.ts
│   │   └── uiStore.ts
│   └── types/                # TypeScript型定義
│       ├── api.ts
│       └── domain.ts
├── public/
├── package.json
├── tsconfig.json
├── vite.config.ts
└── tailwind.config.js
```

### 4.2 ページ構成

| ルート | ページ | 説明 |
|--------|--------|------|
| / | Dashboard | システム概要、リソース使用状況 |
| /docker | DockerManagement | コンテナ管理 |
| /databases | DatabaseManagement | データベース管理 |
| /domains | DomainManagement | Cloudflare DNS管理 |
| /wordpress | WordPressManagement | WordPress サイト管理 |
| /backup | BackupManagement | バックアップ管理 |
| /security | SecurityManagement | セキュリティ設定 |
| /settings | Settings | システム設定 |

### 4.3 状態管理

| 種別 | ライブラリ | 用途 |
|------|----------|------|
| サーバーステート | TanStack Query | API データキャッシュ、同期 |
| クライアントステート | Zustand | UI状態、認証状態 |

---

## 5. UI/UX設計

### 5.1 デザインシステム

#### カラーパレット

| 用途 | カラー | コード |
|------|--------|--------|
| Primary | Blue-600 | #2563eb |
| Secondary | Slate-700 | #334155 |
| Accent | Green-500 | #22c55e |
| Error | Red-500 | #ef4444 |
| Warning | Yellow-500 | #eab308 |
| Background (Light) | White | #ffffff |
| Background (Dark) | Slate-950 | #020617 |

#### タイポグラフィ

| 要素 | フォント | ウェイト |
|------|---------|---------|
| Font Family | Inter, system-ui | - |
| Headings | - | 600-700 |
| Body | - | 400 |

### 5.2 レイアウト構成

```
┌──────────────────────────────────────────────────┐
│                    Header                         │
│  [Logo]            [Notifications] [User Menu]    │
├──────────┬───────────────────────────────────────┤
│          │                                        │
│ Sidebar  │          Main Content Area            │
│          │                                        │
│ - Dashboard                                       │
│ - Docker    ┌─────────┐ ┌─────────┐              │
│ - Database  │  Card   │ │  Card   │              │
│ - Domains   └─────────┘ └─────────┘              │
│ - WordPress                                       │
│ - Backup    ┌──────────────────────┐             │
│ - Security  │     Data Table       │             │
│ - Settings  └──────────────────────┘             │
│          │                                        │
└──────────┴───────────────────────────────────────┘
```

---

## 6. セキュリティ設計

### 6.1 認証・認可

```
┌─────────────────────────────────────────────────┐
│                Authentication Flow               │
│                                                  │
│  User → Login Form → Backend Auth               │
│              ↓                                   │
│         JWT Token (HS256)                       │
│              ↓                                   │
│     Access Token (15分) + Refresh Token          │
│              ↓                                   │
│     httpOnly Cookie / localStorage               │
└─────────────────────────────────────────────────┘
```

### 6.2 Role-Based Access Control (RBAC)

| ロール | 権限 |
|--------|------|
| super_admin | 全権限 + ユーザー管理 |
| admin | 読み取り + 全操作 |
| editor | 読み取り + 基本操作 |
| viewer | 読み取りのみ |

### 6.3 セキュリティ対策

| 対策 | 実装 |
|------|------|
| HTTPS | Cloudflare Tunnel経由 |
| CSRF保護 | CSRFトークン |
| Rate Limiting | FastAPI Middleware |
| Input Validation | Pydantic |
| SQL Injection | SQLAlchemy ORM |
| XSS | React自動エスケープ |

---

## 7. 外部サービス統合

### 7.1 統合対象

| サービス | 統合方法 | 用途 |
|---------|---------|------|
| Docker Engine | Unix Socket | コンテナ管理 |
| Cloudflare | REST API | DNS管理 |
| MariaDB | SQLAlchemy | データ永続化 |
| WordPress | REST API | サイト管理 |
| Flask usermgmt | REST API | メールユーザー管理 |

### 7.2 Cloudflare API統合（✅ 完了）

```
Portal Backend → Cloudflare API → DNS Zone/Records
                     ↓
              Authentication: Bearer Token
              Endpoints:
              - /zones
              - /zones/{zone_id}/dns_records
```

---

## 8. 通信フロー

### 8.1 Web閲覧フロー

```
User Browser
    │
    ▼ HTTPS
Cloudflare Tunnel
    │
    ▼ HTTP
Nginx
    │
    ├──▶ /api/* → Backend
    │                │
    │                ├──▶ MariaDB
    │                └──▶ External APIs
    │
    └──▶ /* → Frontend (静的ファイル)
```

### 8.2 API呼び出しフロー

```
React Component
    │
    ▼
TanStack Query (キャッシュ確認)
    │
    ▼
API Client (axios/fetch)
    │
    ▼ HTTP + JWT
FastAPI Router
    │
    ▼
Service Layer (ビジネスロジック)
    │
    ├──▶ Database (SQLAlchemy)
    └──▶ External Service (Docker/Cloudflare)
```

---

## 9. 監視・ログ設計

### 9.1 ログ管理

| レイヤー | 形式 | 出力先 |
|---------|------|--------|
| Backend | JSON Structured | stdout / file |
| Frontend | Console | Browser DevTools |
| Nginx | Combined | Docker logs |

### 9.2 メトリクス

| メトリクス | 説明 |
|-----------|------|
| API レスポンスタイム | 平均/95パーセンタイル |
| エラーレート | 4xx/5xx 比率 |
| リクエスト数 | 時間あたりリクエスト |
| システムリソース | CPU/Memory/Disk |

---

## 10. 関連ドキュメント

| ドキュメント | 内容 |
|------------|------|
| [requirements.md](requirements.md) | 要件定義・トレードオフ分析 |
| [deployment.md](deployment.md) | デプロイ戦略・Docker Compose設定 |
| [operations.md](operations.md) | 運用設計・開発ガイド |
