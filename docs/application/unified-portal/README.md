# 統合管理ポータル

ブログシステム + メールサーバー + Cloudflare DNSを一元管理するWebベースの統合管理ポータル

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
| **バックエンド** | FastAPI 0.109+, Python 3.9+ |
| **フロントエンド** | React 18, TypeScript 5.0+, Vite 5 |
| **UI** | Tailwind CSS 3, shadcn/ui |
| **状態管理** | TanStack Query, Zustand |
| **コンテナ** | Docker, Docker Compose |
| **プロキシ** | Nginx |
| **認証** | JWT (python-jose) |
| **DB** | MariaDB（既存環境共用） |

---

## プロジェクト概要

### 目的

**主目標**: ブログシステム + メールサーバー + Cloudflare DNSの一元管理

**技術目標**:
- ✅ モダンUI/UX（Xserver風インターフェース）
- ✅ Cloudflare DNS API統合
- ✅ Docker管理API実装
- ✅ WordPress管理API実装
- ✅ データベース管理API実装
- ✅ セキュリティ管理API実装
- ✅ バックアップ管理API実装
- ✅ メールサーバー管理API実装

---

## 現在の稼働状況

### 本番稼働中

| コンテナ | 状態 | 稼働期間 |
|---------|------|----------|
| backend (FastAPI) | ✅ Healthy | 2週間 |
| frontend (React) | ✅ Healthy | 2週間 |

### 管理機能（12ページ）

| ページ | 説明 | 状況 |
|--------|------|------|
| ダッシュボード | システム概要・リソース使用状況 | ✅ 実装済み |
| Docker管理 | コンテナ管理 | ✅ 実装済み |
| データベース管理 | MariaDB管理 | ✅ 実装済み |
| ドメイン管理 | Cloudflare DNS管理 | ✅ 実装済み |
| WordPress管理 | サイト管理 | ✅ 実装済み |
| バックアップ管理 | バックアップ操作 | ✅ 実装済み |
| セキュリティ管理 | セキュリティ設定 | ✅ 実装済み |
| PHP管理 | PHP設定 | ✅ 実装済み |
| メールサーバー管理 | メールユーザー管理 | ✅ 実装済み |
| ユーザー管理 | 管理者アカウント | ✅ 実装済み |
| マネージドサイト作成 | WordPress新規作成 | ✅ 実装済み |
| ログイン | 認証 | ✅ 実装済み |

---

## システムアーキテクチャ

### コンテナ構成

```
portal_network (Docker Bridge)
├── backend (FastAPI)
└── frontend (React/Nginx)
```

### バックエンドAPI構成

| ルーター | 機能 |
|---------|------|
| auth.py | 認証・JWT管理 |
| dashboard.py | システム統計 |
| docker.py | コンテナ操作 |
| database.py | DB管理 |
| domains.py | Cloudflare DNS |
| wordpress.py | WordPress管理 |
| backup.py | バックアップ操作 |
| security.py | セキュリティ設定 |
| php.py | PHP設定 |
| mailserver.py | メールユーザー管理 |

### ネットワークフロー

```
[ユーザー] → [Cloudflare Edge] → [Tunnel] → [nginx] → [Backend/Frontend]
              ↓                    ↓
           DDoS防御            アウトバウンド接続のみ
           SSL/TLS自動          （ポート開放不要）
```

---

## 実装フェーズ

### Phase 1: 基盤構築（✅ 完了）

- ✅ FastAPIバックエンド基盤
- ✅ Reactフロントエンド基盤
- ✅ Cloudflare DNS API統合
- ✅ 12ページのUI/API実装
- ✅ JWT認証システム
- ✅ Docker Compose本番設定

### Phase 2: 機能拡張（計画中）

- WebSocketリアルタイム更新
- 監視・アラート機能
- ログビューア機能強化

---

## ディレクトリ構成

```
services/unified-portal/
├── backend/                # FastAPIバックエンド
│   ├── app/
│   │   ├── main.py
│   │   ├── routers/       # 10個のAPIルーター
│   │   ├── models/
│   │   └── services/
│   └── requirements.txt
├── frontend/               # Reactフロントエンド
│   ├── src/
│   │   ├── components/
│   │   ├── pages/         # 12ページ
│   │   └── lib/
│   └── package.json
├── nginx/                  # Nginx設定
└── docker-compose.yml
```

---

## クイックスタート

### 開発環境

```bash
# バックエンド起動
cd services/unified-portal/backend
source venv/bin/activate
uvicorn app.main:app --reload

# フロントエンド起動
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
| フロントエンド | http://localhost:5173 |
| バックエンドAPI | http://localhost:8000 |
| APIドキュメント | http://localhost:8000/docs |

---

## 参考情報

### 公式ドキュメント

- [FastAPI](https://fastapi.tiangolo.com/)
- [React](https://react.dev/)
- [Vite](https://vitejs.dev/)
- [Tailwind CSS](https://tailwindcss.com/)
- [shadcn/ui](https://ui.shadcn.com/)
- [TanStack Query](https://tanstack.com/query/)

---

**Version**: 2.0
**現在のフェーズ**: Phase 1完了、本番稼働中
