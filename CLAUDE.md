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
  - Mailserver（8コンテナ: Postfix, Dovecot, MariaDB等）
  - Blog System（4コンテナ: WordPress, Nginx, MariaDB, Cloudflared - **16サイト**）
- ✅ EC2: **PostfixがDockerコンテナで稼働**（MX Gateway）
- 📝 KVM環境: 構築済みだが現在未使用（将来的な仮想化用）

**最新の統合**（2025-11-10完了）:
- ✅ WordPress → Mailserver SMTP連携（全16サイト）
- ✅ SPF/DKIM認証によるメール配信改善

**重要:** Dell側・EC2側ともにPostfixはDockerコンテナで稼働しています。systemd/journalctlベースのコマンドではなく、`docker logs`/`docker exec`を使用してください。

**ハードウェア制約**:
- CPU: 6コア/12スレッド、RAM: 32GB、Storage: 3.6TB HDD + 390GB SSD
- Docker環境: ホストリソースを直接使用

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
- 16 WordPress サイト構成（Phase A-1完了）
- Cloudflare Tunnel設定（5 Public Hostnames - 16 WordPress installations）
- Docker Compose環境（4コンテナ）
- WordPress → Mailserver SMTP連携（Phase A-1完了）
- 既知の問題（Phase 011: サブディレクトリ表示問題、Elementor、PHP互換性）
- wp-cli操作、URL置換手順

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
- `services/blog/` - Blog System実装（config, docker-compose）
  - `config/nginx/conf.d/` - 5つの仮想ホスト設定（kuma8088.conf他）
  - `config/mariadb/init/` - 16データベース初期化
  - `config/wordpress/` - PHP設定、WP Mail SMTP設定
  - `config/cloudflared/` - Cloudflare Tunnel設定

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

### バックアップ確認
```bash
tail -f ~/.mailserver-backup.log
tail -f ~/.s3-backup-cron.log
tail -f ~/.scan-cron.log
ls -lah /mnt/backup-hdd/mailserver/daily/
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
- **P011: kuma8088.com表示問題** ⚠️ 起票済み:
  - **症状**: blog.kuma8088.com配下10サイトでElementorプレビュー/静的ファイル404
  - **根本原因**: Cloudflare HTTPS検出が**欠落**（他ドメインには存在）
  - **影響**: WordPress HTTP判定 → Elementor HTTP URL生成 → 混在コンテンツエラー
  - **解決策**: kuma8088.confに `fastcgi_param HTTPS on;` 追加（8箇所）
  - 詳細: [docs/application/blog/issue/active/P011-subdirectory-display-issue.md](docs/application/blog/issue/active/P011-subdirectory-display-issue.md)
- **P010: HTTPS混在コンテンツエラー**
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
