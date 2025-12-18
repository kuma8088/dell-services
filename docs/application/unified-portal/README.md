# 統合管理ポータル

**作成者**: kuma8088（AWS認定ソリューションアーキテクト、ITストラテジスト）

Dell WorkStation環境のBlog System + Mailserver + Cloudflare DNSを一元管理するWebベースの統合管理ポータル

---

## ドキュメント構成

| ドキュメント | 内容 |
|------------|------|
| [requirements.md](requirements.md) | 要件定義・トレードオフ分析 |
| [architecture.md](architecture.md) | システム設計・アーキテクチャ図 |
| [deployment.md](deployment.md) | デプロイ戦略・Docker Compose設定 |
| [operations.md](operations.md) | 運用設計・開発ガイド |

---

## 技術スタック

| カテゴリ | 技術 |
|---------|------|
| **Backend** | FastAPI 0.109+, Python 3.9+ |
| **Frontend** | React 18, TypeScript 5.0+, Vite 5 |
| **UI** | Tailwind CSS 3, shadcn/ui |
| **状態管理** | TanStack Query, Zustand |
| **コンテナ** | Docker, Docker Compose |
| **プロキシ** | Nginx |
| **認証** | JWT (python-jose) |
| **DB** | MariaDB（既存環境共用） |

---

## Project Overview

### Objectives

**Primary Goal**: Blog System + Mailserver + Cloudflare DNSの一元管理

**Technical Goals**:
- ✅ モダンUI/UX（Xserver風インターフェース）
- ✅ Cloudflare DNS API統合
- 🔄 Docker管理統合（実装中）
- 📝 WordPress管理統合（計画中）
- 📝 リアルタイム監視（計画中）

### 管理機能（8ページ）

| ページ | 説明 | 状況 |
|--------|------|------|
| Dashboard | システム概要・リソース使用状況 | UI完成 |
| Docker Management | コンテナ管理 | UI完成・API待ち |
| Database Management | データベース管理 | UI完成・API待ち |
| Domain Management | Cloudflare DNS管理 | ✅ 完了 |
| WordPress Management | WordPressサイト管理 | UI完成・API待ち |
| Backup Management | バックアップ管理 | UI完成・API待ち |
| Security Management | セキュリティ設定 | UI完成・API待ち |
| Settings | システム設定 | UI完成 |

---

## System Architecture

### Container Composition

```
portal_network (Docker Bridge)
├── backend (FastAPI) - 172.20.0.90
├── frontend (React) - 172.20.0.91
└── nginx (Reverse Proxy) - 172.20.0.92
```

### Network Flow

```
[User] → [Cloudflare Edge] → [Tunnel] → [nginx] → [Backend/Frontend]
          ↓                    ↓
       DDoS protection    outbound-only connection
       SSL/TLS auto       (no port forwarding required)
```

---

## Current Status

### ✅ Completed

1. **UI実装（Phase 1）**
   - 8つの管理ページUI
   - shadcn/ui コンポーネント統合
   - レスポンシブデザイン
   - ダークモード対応

2. **Cloudflare DNS API統合**
   - ゾーン一覧取得
   - DNSレコードCRUD操作
   - プロキシ設定対応
   - TTL設定対応

### 🔄 In Progress

- Docker管理API統合
- WordPress REST API統合
- リアルタイムログ表示

### 📝 Planned

- JWT認証システム
- WebSocketリアルタイム更新
- Mailserverユーザー管理統合
- バックアップAPI統合

---

## Quick Start

### 開発環境

```bash
# Backend起動
cd services/unified-portal/backend
source venv/bin/activate
uvicorn app.main:app --reload

# Frontend起動
cd services/unified-portal/frontend
npm install
npm run dev
```

### Docker Compose

```bash
cd services/unified-portal
docker compose up -d
```

### アクセスURL

| サービス | URL |
|---------|-----|
| Frontend | http://localhost:5173 |
| Backend API | http://localhost:8000 |
| API Docs | http://localhost:8000/docs |

---

## Directory Structure

```
services/unified-portal/
├── backend/                # FastAPI Backend
│   ├── app/
│   │   ├── main.py
│   │   ├── models/
│   │   ├── routers/
│   │   └── services/
│   └── requirements.txt
├── frontend/               # React Frontend
│   ├── src/
│   │   ├── components/
│   │   ├── pages/
│   │   └── lib/
│   └── package.json
├── nginx/                  # Nginx設定
└── docker-compose.yml
```

---

## Implementation Phases

### Phase 1: 基盤構築（✅ 完了）

- FastAPI バックエンド基盤
- React フロントエンド基盤
- Cloudflare DNS API統合
- 8つの管理ページUI実装

### Phase 2: API統合（計画中）

- Docker API統合
- WordPress REST API統合
- MariaDB管理API
- バックアップAPI

### Phase 3: 高度な機能（計画中）

- JWT認証システム
- WebSocketリアルタイム更新
- Mailserverユーザー管理統合
- 監視・アラート機能

### Phase 4: 本番デプロイ（計画中）

- Docker Compose本番設定
- Cloudflare Tunnel統合
- セキュリティ監査
- 本番環境デプロイ

---

## Reference Information

### Official Documentation

- [FastAPI](https://fastapi.tiangolo.com/)
- [React](https://react.dev/)
- [Vite](https://vitejs.dev/)
- [Tailwind CSS](https://tailwindcss.com/)
- [shadcn/ui](https://ui.shadcn.com/)
- [TanStack Query](https://tanstack.com/query/)

### Project Documentation

- [docs/application/unified-portal/](.)

---

**Version**: 1.0
**Current Phase**: Phase 1 完了、Phase 2 計画中
