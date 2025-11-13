# Documentation Index (AI Quick Reference)

このドキュメントはAI開発を効率化するためのクイックリファレンスです。

## 🎯 Start Here

**最初に読むべきドキュメント:**
- [CLAUDE.md](/CLAUDE.md) - AI開発ガイドライン（必読）
- [README.md](/README.md) - プロジェクト全体概要

## 📚 Category Index

### Infrastructure

**[インフラ構築](/docs/infra/README.md)** - 182行
- Docker環境: [procedures/3-docker/](/docs/infra/procedures/3-docker/)
  - 3.1: Docker環境セットアップ
  - 3.2: ストレージ・バックアップセットアップ
  - 3.3: 監視・セキュリティセットアップ
  - 3.4: インフラバリデーション
- KVM環境: [procedures/2-kvm/](/docs/infra/procedures/2-kvm/) (構築済み、現在未使用)
- Staging環境: [staging/](/docs/infra/staging/)

### Applications

#### Mailserver

**[Mailserver概要](/docs/application/mailserver/README.md)** - 347行

**主要ドキュメント:**
- **バックアップシステム:**
  - Phase 10 (ローカル): [backup/03_implementation.md](/docs/application/mailserver/backup/03_implementation.md)
  - Phase 11-B (S3): [backup/07_s3backup_implementation.md](/docs/application/mailserver/backup/07_s3backup_implementation.md)
- **User Management System:**
  - 概要: [usermgmt/README.md](/docs/application/mailserver/usermgmt/README.md)
  - 開発ガイド: [usermgmt/guides/DEVELOPMENT.md](/docs/application/mailserver/usermgmt/guides/DEVELOPMENT.md)
  - ユーザーガイド: [usermgmt/guides/USER_GUIDE.md](/docs/application/mailserver/usermgmt/guides/USER_GUIDE.md)
  - API仕様: [usermgmt/guides/API.md](/docs/application/mailserver/usermgmt/guides/API.md)
  - 設計: [usermgmt/design/](/docs/application/mailserver/usermgmt/design/)
  - フェーズ記録: [usermgmt/phases/](/docs/application/mailserver/usermgmt/phases/)
- **Cloudflare Email Worker（MX受信システム）:**
  - 実装手順書: [migration/cloudflare-email-worker-implementation.md](/docs/application/mailserver/migration/cloudflare-email-worker-implementation.md) ✅ **運用中** (2025-11-12)
  - Workerコード: [migration/worker.js](/docs/application/mailserver/migration/worker.js)
  - **EC2 MX Gateway**: ❌ **廃止済み**（月額¥525→¥0削減、Tailscale VPNも不要に）
  - **新しいフロー**: Internet → Cloudflare Email Routing → Email Worker → Cloudflare Tunnel → mailserver-api (FastAPI) → Dovecot LMTP
  - 移行オプション比較（参考資料）: [migration/cloudflare-email-relay-migration.md](/docs/application/mailserver/migration/cloudflare-email-relay-migration.md)
- **トラブルシューティング:** [/services/mailserver/troubleshoot/README.md](/services/mailserver/troubleshoot/README.md)
- **Device Access:** [device/README.md](/docs/application/mailserver/device/README.md)

#### Blog System

**[Blog System概要](/docs/application/blog/README.md)** - 492行

**主要ドキュメント:**
- **Phase進捗:** [phases/](/docs/application/blog/phases/)
  - Phase A-1: 一括マイグレーション ✅ 完了 (2025-11-09)
  - Phase A-2: 本番ドメイン移行 ✅ 完了 (2025-11-12)
  - Phase B: Production Hardening 📋 計画中
- **Issue管理:** [issue/README.md](/docs/application/blog/issue/README.md)
  - Active Issues: [issue/active/](/docs/application/blog/issue/active/)
    - P010: HTTPS混在コンテンツエラー
    - I001-I009: 改善提案
  - Completed: [issue/completed/](/docs/application/blog/issue/completed/)
    - P011: サブディレクトリ表示問題 ✅ 解決 (2025-11-11)
    - C001: Xserver移行問題対応
- **構築手順:**
  - 01: 要件定義
  - 02: 設計
  - 03: インストール
  - 04: マイグレーション
  - 05: テスト
- **Cloudflare Tunnel:** [cloudflare-tunnel-hostnames.md](/docs/application/blog/cloudflare-tunnel-hostnames.md)
- **WP Mail SMTP自動設定:**
  - セットアップガイド: [guides/WP-MAIL-SMTP-SETUP.md](/docs/application/blog/guides/WP-MAIL-SMTP-SETUP.md)
  - 新規サイト作成: [/services/blog/scripts/create-new-wp-site.sh](/services/blog/scripts/create-new-wp-site.sh)
  - ポータル統合設計: [design/portal-integration-design.md](/docs/application/blog/design/portal-integration-design.md)

#### Unified Portal

**[統合ポータル概要](/docs/application/unified-portal/README.md)** - NEW 🎉

**主要ドキュメント:**
- **アーキテクチャ:** [ARCHITECTURE.md](/docs/application/unified-portal/ARCHITECTURE.md)
  - FastAPI + React + TypeScript
  - Xserver風UI/UX
  - 実装ロードマップ（Phase 1-4）
- **開発環境:** [LOCAL_DEVELOPMENT.md](/docs/application/unified-portal/LOCAL_DEVELOPMENT.md)
  - セットアップ手順
  - テスト・デバッグ方法
  - トラブルシューティング
- **Cloudflare統合:** [CLOUDFLARE-API-INTEGRATION.md](/docs/application/unified-portal/CLOUDFLARE-API-INTEGRATION.md) ✅ **実装済み** (2025-11-13)
  - DNS管理API完全実装
  - ゾーン一覧・DNSレコードCRUD
  - API トークン作成ガイド
  - BIND vs Cloudflare 比較
- **実装状況:** 📋 Phase 1実装中（I001/I002/I003/I006対応）
  - ✅ プロジェクト構造作成
  - ✅ バックエンド基盤（FastAPI + SQLAlchemy）
  - ✅ フロントエンド基盤（React + Vite + Tailwind + shadcn/ui）
  - ✅ Cloudflare DNS API統合
  - ✅ Redis Object Cache統合（WordPress高速化）
  - 🔄 管理ページ実装中（Dashboard, Docker, Database, PHP, Security, WordPress, Domain, Backup）

## 🛠️ Implementation

### Mailserver実装
**場所:** [/services/mailserver/](/services/mailserver/)

**構成:**
- `docker-compose.yml` - 8コンテナ構成
- `config/` - サービス設定ファイル
  - postfix/, dovecot/, nginx/, roundcube/, rspamd/, clamav/, mariadb/
- `config-staging/` - ステージング環境設定
- `scripts/` - 運用スクリプト
  - backup-mailserver.sh, restore-mailserver.sh
  - backup-to-s3.sh, restore-from-s3.sh
  - scan-mailserver.sh
  - add-user.sh
- `terraform/` - EC2 MX Gateway (IaC) ❌ 廃止済み
- `terraform/s3-backup/` - S3 Backup Infrastructure (IaC)
- `usermgmt/` - Flask User Management App
- `tests/` - バックアップシステムテスト (38テスト)
- `troubleshoot/` - トラブルシューティング記録

### Blog実装
**場所:** [/services/blog/](/services/blog/)

**構成:**
- `docker-compose.yml` - 4コンテナ構成（+ Redis）
- `config/` - サービス設定ファイル
  - nginx/conf.d/ - 5仮想ホスト設定
  - mariadb/init/ - 16データベース初期化
  - wordpress/ - PHP設定、WP Mail SMTP設定
  - cloudflared/ - Cloudflare Tunnel設定
- `scripts/` - 運用スクリプト
  - create-new-wp-site.sh - 新規サイト作成自動化 ✨
  - setup-wp-mail-smtp.sh - WP Mail SMTP一括設定
  - check-wp-mail-smtp.sh - SMTP設定確認
  - generate-nginx-subdirectories.sh - Nginx設定生成
  - setup-redis-object-cache.sh - Redis Object Cache設定
  - test-redis-performance.sh - Redis性能テスト
- `servers/` - サーバー別設定

### Unified Portal実装
**場所:** [/services/unified-portal/](/services/unified-portal/)

**構成:**
- `backend/` - FastAPI バックエンド
  - `app/` - アプリケーションコード
    - `routers/` - API エンドポイント
      - domains.py - Cloudflare DNS API統合 ✅
    - config.py, database.py, main.py
  - `requirements.txt` - Python依存関係
  - `.env.example` - 環境変数テンプレート
- `frontend/` - React フロントエンド
  - `src/` - ソースコード
    - `components/` - UIコンポーネント（shadcn/ui）
    - `pages/` - ページコンポーネント（8ページ）
    - `lib/` - API クライアント、ユーティリティ
      - api.ts - ベースAPIクライアント
      - domains-api.ts - ドメインAPI ✅
  - `package.json` - npm依存関係
  - `.env.example` - 環境変数テンプレート
- `docker-compose.yml` - 開発環境構成

## 📝 Work Notes

**[作業記録](/docs/work-notes/)** - Claude Code作業成果物

**内容:**
- `mailserver/` - Mailserver関連作業記録
  - WordPress SMTP連携設定記録
- `blog/` - Blog System関連作業記録
  - Xserverマイグレーション調査
  - データベースエクスポート状況
  - サイトチェックリスト

## 🔍 Quick Search

**問題が発生したら:**
1. まず [/services/mailserver/troubleshoot/README.md](/services/mailserver/troubleshoot/README.md) を確認
2. 該当する問題別ドキュメントを参照
3. 診断コマンドを実行

**設定変更が必要なら:**
- Mailserver: `/services/mailserver/config/`
- Blog: `/services/blog/config/`
- 変更後は必ず `docker compose restart <service>` を実行

**スクリプト実行:**
- **Mailserver:**
  - バックアップ: `/services/mailserver/scripts/backup-*.sh`
  - S3同期: `/services/mailserver/scripts/backup-to-s3.sh`
  - マルウェアスキャン: `/services/mailserver/scripts/scan-mailserver.sh`
- **Blog:**
  - 新規サイト作成: `/services/blog/scripts/create-new-wp-site.sh` ✨
  - WP Mail SMTP設定: `/services/blog/scripts/setup-wp-mail-smtp.sh`
  - SMTP設定確認: `/services/blog/scripts/check-wp-mail-smtp.sh`

**IaC操作:**
- S3 Backup: `/services/mailserver/terraform/s3-backup/`
- EC2 MX Gateway: `/services/mailserver/terraform/` ❌ **廃止済み** (2025-11-12)

## 🏷️ ドキュメント命名規則

- **Phase文書:** `PHASE{番号}_{タイトル}.md` (例: PHASE11_COMPLETION.md)
- **Issue文書:**
  - Improvement: `I{3桁番号}_{タイトル}.md`
  - Problem: `P{3桁番号}_{タイトル}.md`
  - Completed: `C{3桁番号}_{タイトル}.md`
- **手順書:** `{番号}_{タイトル}.md` (例: 01_requirements.md)

## 📊 ドキュメント統計

- **総Markdownファイル数:** 92ファイル
- **主要README行数:**
  - プロジェクトルート: 712行
  - CLAUDE.md: 287行
  - docs/infra: 182行
  - Mailserver: 347行
  - Blog: 492行
