# Infrastructure Documentation

Dockerコンテナ基盤の構築ドキュメント

**現在の構成**: ワークステーション上でDocker Composeを直接実行

---

## 📋 ドキュメント構成

このディレクトリには以下のドキュメントが含まれています:

- 要件定義書
- システム設計書
- インストール手順書
- テスト計画書

---

## 🌐 Docker Compose サービス構成

### Mailserver（9コンテナ）

| サービス | 役割 |
|---------|------|
| postfix | SMTP送信（SendGrid経由） |
| dovecot | IMAP/POP3受信・LMTP |
| mariadb | データベース |
| clamav | ウイルススキャン |
| rspamd | スパムフィルタ |
| roundcube | Webメール |
| mailserver-api | メール受信API（Cloudflare Worker連携） |
| usermgmt | ユーザー管理（Flask） |
| cloudflared | Cloudflare Tunnel |

**ネットワーク構成**:
- メール受信: Cloudflare Email Worker → Tunnel → mailserver-api → Dovecot LMTP
- メール送信: Postfix → SendGrid Relay
- クライアントアクセス: VPN経由のみ

### Blog System（5コンテナ）

| サービス | 役割 |
|---------|------|
| nginx | リバースプロキシ |
| wordpress | WordPress + PHP-FPM（複数サイト） |
| mariadb | データベース |
| redis | Object Cache |
| cloudflared | Cloudflare Tunnel |

---

## 💾 ストレージ構成

| マウントポイント | 用途 |
|---------------|------|
| SSD | OS、Docker システム、データベース |
| HDD | メールデータ、WordPress、バックアップ |

---

## 🚨 重要な作業ルール

### 1. インフラ変更前の必須確認

**CRITICAL**: Docker/ネットワーク/ストレージ設定変更時は必ず公式ドキュメント確認

```bash
# 推奨確認手順
1. 公式ドキュメントで仕様確認
2. 現在の設定確認: docker compose config
3. テスト環境で検証後、本番適用
```

**参照ドキュメント**:
- Docker: https://docs.docker.com/
- Docker Compose: https://docs.docker.com/compose/
- Rocky Linux: https://docs.rockylinux.org/

### 2. セキュリティ設定

- SSH: 公開鍵認証のみ、パスワード認証無効
- ポート: 必要最小限のみ開放（Cloudflare Tunnel活用）
- アクセス制御: VPNで内部サービス保護

### 3. 手順書実行の原則

- **実行前**: 前提条件・期待出力・ロールバック手順を確認
- **実行中**: 結果を記録、期待値と異なる場合は停止して調査
- **実行後**: バリデーション実施、Git コミット

---

## 🔧 よく使うコマンド

### Docker操作

```bash
# Mailserver
cd services/mailserver
docker compose ps
docker compose logs -f <service-name>
docker compose restart <service-name>

# Blog
cd services/blog
docker compose ps
docker compose logs -f <service-name>

# システム情報
docker system df
docker volume ls
```

---

## ⚠️ よくある問題と対処

| 問題 | 原因 | 対処 |
|-----|------|-----|
| コンテナ起動失敗 | ストレージ/パーミッション | daemon.json検証、SELinuxコンテキスト確認 |
| ネットワーク接続失敗 | Dockerネットワーク設定 | docker network inspect確認 |
| ディスク容量不足 | ボリューム/イメージ肥大化 | docker system prune実行 |
| リソース枯渇 | メモリ/CPU/ディスク不足 | docker stats確認、不要コンテナ停止 |

---

## 🌩️ 将来のAWS移行

- **段階的移行**: 開発(オンプレ) → ステージング(AWS) → 本番(AWS Multi-AZ)
- **IaC**: Terraform による Infrastructure as Code
- **移行ツール**: AWS Application Migration Service

---

**Repository Type**: ドキュメント駆動型インフラリポジトリ
