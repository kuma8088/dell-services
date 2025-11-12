# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

---

## ⚠️ このファイルの編集ルール（必読）

**目的**: 新しいClaude instancesが最初の5分で理解すべき最小限の情報を提供する

**編集方針**:
- ✅ **このファイルには詳細を書かない** - ドキュメントへのリンクのみ
- ✅ **コマンド例を書かない** - 各README.mdに記載
- ✅ **設定内容を書かない** - 各ドキュメントに記載
- ✅ **30000文字以内に収める** - Claude効率的動作のため
- ❌ **詳細情報の追加禁止** - 既存ドキュメントを参照させる

**編集が必要な場合**:
1. プロジェクト全体の方針変更
2. 新しい必読ドキュメントの追加
3. 致命的なルールの追加

**詳細情報の追加先**:
- **ドキュメント索引** → [docs/INDEX.md](docs/INDEX.md) ← AI用クイックリファレンス
- インフラ関連 → [docs/infra/README.md](docs/infra/README.md)
- Mailserver関連 → [docs/application/mailserver/README.md](docs/application/mailserver/README.md)
- Blog関連 → [docs/application/blog/README.md](docs/application/blog/README.md)
- トラブルシューティング → [services/mailserver/troubleshoot/README.md](services/mailserver/troubleshoot/README.md)
- 作業記録 → [docs/work-notes/README.md](docs/work-notes/README.md)

---

## 📋 プロジェクト概要

**リポジトリタイプ**: ドキュメント駆動型インフラリポジトリ

**目的**: Dell WorkStation (Rocky Linux 9.6) 上でDocker環境を構築し、Mailserver・Blog Systemを稼働

**特徴**:
- 実行可能な手順書を管理（アプリケーションコードは含まない）
- フェーズ別構築: Docker基盤 → サービスデプロイ
- 将来的なAWS移行を想定

**現在の構成**:
- ✅ Dell: Docker Compose環境
  - Mailserver（**9コンテナ**: Postfix, Dovecot, MariaDB, mailserver-api等）
  - Blog System（4コンテナ: WordPress, Nginx, MariaDB, Cloudflared - **16サイト**）
- ✅ Cloudflare: **Email Worker稼働中**（MX受信 → Dell mailserver-api (FastAPI) → LMTP、月額¥0）
- ❌ EC2 MX Gateway: **廃止済み**（2025-11-12にCloudflare Email Workerへ移行完了）
- ❌ Tailscale VPN: **不要に**（Cloudflare Tunnel経由で通信）
- 📝 KVM環境: 構築済みだが現在未使用（将来的な仮想化用）

**最新の統合・改善**（2025-11-12完了）:
- ✅ **Cloudflare Email Worker移行完了**（EC2 MX Gateway廃止、月額¥525→¥0削減）
- ✅ Phase A-2本番ドメイン移行完了（15サイト: blog.* → 本番ドメイン）
- ✅ demo1.kuma8088.com: WP Mail SMTP設定済み
- ✅ 残り15サイト: Phase A-2完了後にWP Mail SMTP設定予定
- ✅ Nginx HTTPS検出パラメータ追加（Elementor jQuery 404エラー解消）
- ✅ Nginx設定の自動生成化（247行→55行、78%削減）
- ✅ バックアップ/リストアスクリプトの堅牢性向上（preflight checks + dry-run）

**重要:**
- Dell側PostfixはDockerコンテナで稼働。systemd/journalctlではなく、`docker logs`/`docker exec`を使用。
- **MX受信フロー**: Internet → Cloudflare Email Routing → Email Worker (JS) → Cloudflare Tunnel → mailserver-api (FastAPI) → Dovecot LMTP
- **送信フロー**: Mail Client → Postfix (Dell) → SendGrid Relay → Internet
- EC2 MX Gateway、Tailscale VPNは廃止済み。

**ハードウェア制約**:
- CPU: 6コア/12スレッド、RAM: 32GB、Storage: 3.6TB HDD + 390GB SSD
- Docker環境: ホストリソースを直接使用

---

## 📊 プロジェクト進捗サマリー（AI用クイックリファレンス）

### ✅ 完了済みフェーズ

**インフラ基盤**:
- Phase 3: Docker環境構築 ✅ 完了
- KVM環境構築 ✅ 完了（現在未使用）

**Mailserver（9コンテナ稼働中）**:
- Phase 10: ローカルバックアップシステム ✅ 完了
  - 日次/週次自動バックアップ（cron設定済み）
  - 38テストケース実装（TDD開発）
  - リストア手順確立
- Phase 11: User Management System ✅ 完了
  - Flask + MariaDB実装
  - REST API提供
  - Web UI完備
- Phase 11-A: Admin管理機能 ✅ 完了
  - 管理者権限分離
  - 単一管理者制約
- Phase 11-B: S3オフサイトバックアップ ✅ 完了
  - Terraform IaC（S3 + IAM + CloudWatch + SNS）
  - Object Lock COMPLIANCE（ランサムウェア対策）
  - ClamAV + rkhunter マルウェアスキャン
  - コスト監視（10円/100円閾値）

**Blog System（16サイト・4コンテナ稼働中）**:
- Phase A-1: 一括マイグレーション ✅ 完了（2025-11-09）
  - 16 WordPress サイト移植（Xserver → Dell、95GB）
  - Docker Compose環境構築
  - Cloudflare Tunnel設定（14 Public Hostnames）
- Phase A-2: 本番ドメイン移行 ✅ 完了（2025-11-12）
  - 15サイト: blog.* → 本番ドメイン
  - 全サイトサブドメイン化（保守性向上）
  - 301リダイレクト設定
  - WP Mail SMTP設定（16サイト）
- **P011: サブディレクトリ表示問題** ✅ 解決（2025-11-11）
  - Nginx HTTPS検出パラメータ追加
  - Elementor jQuery 404エラー解消

**Blog System自動化**:
- ✅ 新規サイト作成ウィザード（`create-new-wp-site.sh`）
- ✅ WP Mail SMTP一括設定（`setup-wp-mail-smtp.sh`）
- ✅ Nginx設定自動生成（247行→55行、78%削減）

### 📝 計画中・未着手フェーズ

**Blog System**:
- Phase B: Production Hardening（計画中）
  - CDNキャッシュ最適化
  - 監視・アラート整備
  - ディザスタリカバリ手順確立
- Phase C: Feature Enhancement（計画中）
  - 管理ポータル統合（Mailserver連携）
  - SSO実装
  - マルチサイト管理UI
  - 自動デプロイパイプライン

**共通インフラ**:
- AWS移行（Phase 12以降）
  - 段階的移行: 開発(Dell) → ステージング(AWS) → 本番(Multi-AZ)

### 🎯 Active Issues（優先度順）

**Blog System**:
- **P010**: HTTPS混在コンテンツエラー（Medium）
- **I004**: バックアップ不具合修正（Critical） - Phase B-1で対応予定
- **I005**: バックアップ改善（Medium）
- **I001-I003**: 管理ポータル統合・UI刷新（Low）
- **I006**: キャッシュシステム（Low）
- **I007**: Email Routing移行（Low）

**Mailserver**:
- 現在アクティブな問題なし（安定稼働中）

### 📌 現在の稼働状況

**Dell WorkStation**:
- Mailserver: **9コンテナ稼働**（安定）- mailserver-api追加
- Blog System: 4コンテナ + 16サイト稼働（本番運用中）
- リソース使用: RAM 15GB/32GB、SSD余裕あり、HDD 95.4GB/3.4TB

**Cloudflare**:
- Email Routing + Email Worker: MX受信処理（サーバーレス、月額¥0）
- Cloudflare Tunnel: Blog + Mail API公開（セキュア、月額¥0）

**AWS**:
- S3 Backup: オフサイトバックアップ（Object Lock COMPLIANCE）
- CloudWatch + SNS: コスト監視

**自動化運用**:
- 日次バックアップ（AM 3:00）: Mailserver + Blog
- 週次バックアップ（日曜 AM 2:00）
- S3レプリケーション（AM 4:00）
- マルウェアスキャン（AM 5:00）

---

## 🚨 絶対にやってはいけないこと

### 1. インフラ変更前の公式ドキュメント確認（必須）

**CRITICAL**: Docker/ネットワーク/ストレージ構成変更時は必ず公式ドキュメント確認

**理由**: 誤設定は本番障害に直結。ポート番号・ネットワークレンジ・サービス動作を仮定しない。

**公式ドキュメント**:
- Docker: https://docs.docker.com/
- Docker Compose: https://docs.docker.com/compose/
- Rocky Linux: https://docs.rockylinux.org/

**確認手順**:
1. WebFetchで公式ドキュメント取得
2. 現在の設定確認: `docker compose config`
3. テスト環境で検証 → 本番適用

### 2. SSH セキュリティ設定

**必須設定**:
- パスワード認証無効（`PasswordAuthentication no`）
- 公開鍵認証のみ使用
- root直接ログイン禁止

**現在の構成**:
- Dell/EC2ともに公開鍵認証のみ有効
- Defense in Depth（多層防御）により保護
- KVM仮想ネットワーク用ポート範囲2201-2280は現在未使用

### 3. 認証情報の混同注意（Mailserver）

**重要**: `.env` の `MYSQL_PASSWORD` と `USERMGMT_DB_PASSWORD` は**異なる**

- ❌ Dovecot SQL認証で `MYSQL_PASSWORD` を使用（間違い）
- ✅ Dovecot SQL認証は `usermgmt` ユーザー + `USERMGMT_DB_PASSWORD` を使用

詳細: [docs/application/mailserver/usermgmt/guides/DEVELOPMENT.md](docs/application/mailserver/usermgmt/guides/DEVELOPMENT.md)

### 4. 手順書実行の原則

- **実行前**: 前提条件・期待出力・ロールバック手順を確認
- **実行中**: 結果を記録、期待値と異なる場合は停止
- **実行後**: バリデーション実施、Git コミット

### 5. コマンド提示のルール（コピペエラー防止）

**問題**: 会話内のコマンド提示で意味のないインデントを入れると、コピペ時にエラーが発生

**必須ルール - 会話内でのコマンド提示**:
- ✅ **コードブロック内は必ず左詰め** (インデント・空白を入れない)
- ✅ **長い複数行コマンドは `.md` ファイル化** (コピペミス防止)
- ❌ **見た目のためのインデント禁止** (コマンドの一部として認識されエラー)

**良い例（会話内）**:
```bash
cd /opt/project
docker compose up -d
```

**悪い例（会話内）**:
```bash
    cd /opt/project
    docker compose up -d
```
↑ コピペ時に先頭の空白がコマンドの一部として認識されエラー

**長いコマンドの場合**:
- `/tmp/script.sh` または `docs/work-notes/command.md` にファイル化
- ファイルを Read ツールで読んでもらう、またはそのまま実行

**理由**: ユーザーがコピペで即座に実行でき、余計な編集作業が不要

---

## 📚 必読ドキュメント（最初に読むべきもの）

### 0. ドキュメント索引（AI用）

**[docs/INDEX.md](docs/INDEX.md)** - AI開発用クイックリファレンス

**内容**:
- カテゴリ別ドキュメント一覧
- 各システムの主要ドキュメントへの直リンク
- クイック検索ガイド（問題解決、設定変更、スクリプト実行、IaC操作）
- ドキュメント統計情報

### 1. インフラドキュメント

**[docs/infra/README.md](docs/infra/README.md)** - 必ず最初に読む

**内容**:
- Docker環境構築手順書（Phase 3）
- ストレージ構成（SSD/HDD分離）
- よく使うコマンド
- よくある問題と対処
- KVM環境手順書（構築済み、現在未使用）

### 2. Mailserverドキュメント

**[docs/application/mailserver/README.md](docs/application/mailserver/README.md)** - Mailserver作業時に必読

**内容**:
- アーキテクチャ（EC2 MX + Dell LMTP + SendGrid）
- サービス構成（Docker Compose）
- Phase 11/11-A: User Management System
- EC2操作ガイド
- Terraform運用

### 3. バックアップシステム（Phase 10 + 11-B）

**Phase 10 - ローカルバックアップ**:
- **[docs/application/mailserver/backup/03_implementation.md](docs/application/mailserver/backup/03_implementation.md)**
- TDD開発バックアップシステム（38テスト）
- 日次/週次自動バックアップ（cron設定済み）
- リストア手順（コンポーネント別復旧）
- ログ: `~/.mailserver-backup.log`

**Phase 11-B - S3オフサイトバックアップ** ✅ 完了:
- **[docs/application/mailserver/backup/07_s3backup_implementation.md](docs/application/mailserver/backup/07_s3backup_implementation.md)**
- Terraform IaC (S3 + IAM + CloudWatch + SNS)
- Object Lock COMPLIANCE（ランサムウェア対策）
- ClamAV + rkhunter マルウェアスキャン（3層防御）
- コスト監視（10円/100円閾値）
- ログ: `~/.s3-backup-cron.log`, `~/.scan-cron.log`

### 4. Blog Systemドキュメント

**[docs/application/blog/README.md](docs/application/blog/README.md)** - Blog作業時に必読

**内容**:
- 16 WordPress サイト構成（Phase A-1完了、Phase A-2実施済み）
- Cloudflare Tunnel設定（5 Public Hostnames - 16 WordPress installations）
- Docker Compose環境（4コンテナ）
- 本番ドメイン移行: 15サイト完了（blog.* → 本番ドメイン）
- WP Mail SMTP: demo1.kuma8088.com設定済み、残り15サイトは要設定
- wp-cli操作、URL置換手順

**新規サイト作成自動化** ✨ NEW (2025-11-11):
- **[guides/WP-MAIL-SMTP-SETUP.md](docs/application/blog/guides/WP-MAIL-SMTP-SETUP.md)** - WP Mail SMTP一括設定ガイド
- **[services/blog/scripts/create-new-wp-site.sh](services/blog/scripts/create-new-wp-site.sh)** - 新規サイト作成ウィザード（対話式）
  - データベース作成
  - WordPress自動インストール
  - WP Mail SMTP自動設定
  - Nginx/Cloudflare設定ガイダンス
- **[services/blog/scripts/QUICKSTART.md](services/blog/scripts/QUICKSTART.md)** - 5分クイックスタート
- **[design/portal-integration-design.md](docs/application/blog/design/portal-integration-design.md)** - 将来の管理ポータル統合設計

### 5. トラブルシューティング

**[services/mailserver/troubleshoot/README.md](services/mailserver/troubleshoot/README.md)** - 問題発生時に必読

**内容**:
- 問題別クイックリファレンス
- 認証失敗対処（Dovecot SQL）
- メール受信失敗対処（relay_domains）
- 緊急対応フロー
- 診断コマンド一覧

---

## 📂 重要ディレクトリ

- `docs/INDEX.md` - AI用クイックリファレンス **← まずここから**
- `docs/infra/` - インフラ構築ドキュメント
- `docs/application/mailserver/` - Mailserver仕様・設計
  - `usermgmt/` - User Management System ドキュメント
    - `guides/` - 開発ガイド、ユーザーガイド、API仕様
    - `design/` - 設計ドキュメント
    - `phases/` - Phase 11/11-A完了報告
- `docs/application/blog/` - Blog System仕様・設計
  - `phases/` - Phase A-1等の進捗記録
  - `issue/` - Issue管理
    - `active/` - アクティブなIssue（I=Improvement, P=Problem）
    - `completed/` - 完了したIssue
- `docs/work-notes/` - Claude作業成果物（分析レポート、設定記録）
  - `mailserver/` - Mailserver関連作業記録
  - `blog/` - Blog System関連作業記録
- `services/mailserver/` - Mailserver実装（config, scripts, terraform）
  - `config/` - 各サービス設定（postfix, dovecot, nginx等）
  - `scripts/` - 運用スクリプト（backup, restore, scan）
  - `terraform/` - EC2 MX Gateway (IaC)
  - `terraform/s3-backup/` - S3 Backup Infrastructure (IaC)
  - `usermgmt/` - Flask User Management App
  - `troubleshoot/` - トラブルシューティング
- `services/blog/` - Blog System実装（config, docker-compose, scripts）
  - `config/nginx/conf.d/` - 5つの仮想ホスト設定（kuma8088.conf他）
  - `config/mariadb/init/` - 16データベース初期化
  - `config/wordpress/` - PHP設定、WP Mail SMTP設定
  - `config/cloudflared/` - Cloudflare Tunnel設定
  - `scripts/` - 運用スクリプト ✨ NEW
    - `create-new-wp-site.sh` - 新規サイト作成ウィザード（自動化）
    - `setup-wp-mail-smtp.sh` - WP Mail SMTP一括設定
    - `check-wp-mail-smtp.sh` - SMTP設定確認
    - `generate-nginx-subdirectories.sh` - Nginx設定生成

## 🔧 よく使うコマンド

### Docker操作（Mailserver）
```bash
cd /opt/onprem-infra-system/project-root-infra/services/mailserver
docker compose ps
docker compose logs -f postfix
docker compose restart <service>
docker compose exec postfix bash
```

### Docker操作（Blog）
```bash
cd /opt/onprem-infra-system/project-root-infra/services/blog
docker compose ps
docker compose logs -f wordpress
docker compose restart <service>
docker compose exec wordpress bash
```

### 新規サイト作成（Blog）✨ NEW
```bash
cd /opt/onprem-infra-system/project-root-infra/services/blog

# 対話式ウィザードで新規サイト作成（推奨）
./scripts/create-new-wp-site.sh

# WordPress自動インストール + WP Mail SMTP自動設定 + ガイダンス表示
# 実行後: Nginx設定追加 → Cloudflare Tunnel設定更新
```

### WP Mail SMTP設定（Blog）
```bash
cd /opt/onprem-infra-system/project-root-infra/services/blog

# 全16サイトの設定状況確認
./scripts/check-wp-mail-smtp.sh

# 全サイト一括設定（初回のみ）
./scripts/setup-wp-mail-smtp.sh --dry-run  # プレビュー
./scripts/setup-wp-mail-smtp.sh             # 実行

# 単一サイト設定（新規サイト追加時）
./scripts/setup-wp-mail-smtp.sh --site kuma8088-new-site blog.kuma8088.com/new-site noreply@kuma8088.com

# テストメール送信
./scripts/setup-wp-mail-smtp.sh --test-email your-email@example.com
```

### Nginx設定生成（Blog）
```bash
# サブディレクトリサイトの設定を自動生成
cd /opt/onprem-infra-system/project-root-infra/services/blog
./scripts/generate-nginx-subdirectories.sh > config/nginx/conf.d/kuma8088-subdirs-generated.inc
docker compose exec nginx nginx -t
docker compose exec nginx nginx -s reload
```

### バックアップ確認
```bash
tail -f ~/.mailserver-backup.log
tail -f ~/.s3-backup-cron.log
tail -f ~/.scan-cron.log
ls -lah /mnt/backup-hdd/mailserver/daily/
```

### リストア操作（Mailserver）
```bash
cd /opt/onprem-infra-system/project-root-infra/services/mailserver

# Dry-runで事前確認（実際には実行しない）
./scripts/restore-mailserver.sh --from /mnt/backup-hdd/mailserver/daily/YYYY-MM-DD --dry-run

# 特定コンポーネントのリストア
./scripts/restore-mailserver.sh --from /mnt/backup-hdd/mailserver/daily/YYYY-MM-DD --component mysql

# 全コンポーネントのリストア
./scripts/restore-mailserver.sh --from /mnt/backup-hdd/mailserver/daily/YYYY-MM-DD --component all

# リストアログ確認
tail -f ~/.mailserver-restore.log
```

### Terraform操作（S3 Backup）
```bash
cd services/mailserver/terraform/s3-backup
terraform plan
terraform apply
terraform output
```

---

## ⚠️ よくある落とし穴

### Mailserver
- **認証失敗**: MYSQL_PASSWORD と USERMGMT_DB_PASSWORD の混同
- **メール受信失敗**: EC2の relay_domains未登録
- **コンテナ起動失敗**: ストレージ/パーミッション問題

詳細: [services/mailserver/troubleshoot/README.md](services/mailserver/troubleshoot/README.md)

### Blog System
- **P011: kuma8088.com表示問題** ✅ **解決済み**（2025-11-11）:
  - **症状**: blog.kuma8088.com配下10サイトでElementorプレビュー/静的ファイル404
  - **根本原因**: Nginx HTTPS検出パラメータ欠落
  - **解決策**: kuma8088.confに `fastcgi_param HTTPS on;` と `HTTP_X_FORWARDED_PROTO https;` を8箇所追加
  - 詳細: [docs/application/blog/issue/completed/P011-subdirectory-display-issue.md](docs/application/blog/issue/completed/P011-subdirectory-display-issue.md)
- **P010: HTTPS混在コンテンツエラー** ⚠️ 起票済み:
  - 詳細: [docs/application/blog/issue/active/P010_https-mixed-content-error.md](docs/application/blog/issue/active/P010_https-mixed-content-error.md)
- **Nginxサブディレクトリ404**: alias設定とSCRIPT_FILENAMEの誤設定
- **wp-config.php編集失敗**: 所有者82:82 (www-data) への変更必要
- **画像表示問題**: Elementorキャッシュクリアが必要
- **PHP非互換**: create_function()等の非推奨関数がPHP 8.xでエラー

詳細: [docs/application/blog/README.md](docs/application/blog/README.md) | Issue一覧: [docs/application/blog/issue/README.md](docs/application/blog/issue/README.md)

---

## 🌩️ 将来のAWS移行

- 段階的移行: 開発(Dell) → ステージング(AWS) → 本番(Multi-AZ)
- 詳細: [docs/infra/README.md](docs/infra/README.md)
