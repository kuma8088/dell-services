# メールサーバー構築プロジェクト

**プロジェクト概要**: Xserver WEBメール機能相当のメールサーバーをDocker Compose環境で構築

**構築環境**: Rocky Linux 9.6

**構築方式**: Docker Compose

---

## 📚 ドキュメント一覧

### 1. 要件定義書
- プロジェクト概要と目的
- 機能要件・非機能要件
- システム制約とリスク管理
- 技術スタック概要

**主要要件**:
- ✅ SMTP/IMAP/POP3対応（SSL/TLS必須）
- ✅ WEBメール（Roundcube）
- ✅ 複数ドメイン対応
- ✅ SPF/DKIM/DMARC対応
- ✅ 自動SSL更新（Let's Encrypt）
- ✅ 初級管理者向け設計

### 2. 設計書
- システムアーキテクチャ図
- ネットワーク設計（Docker Bridge Network）
- コンポーネント詳細設計
- セキュリティ設計
- データフロー図
- バックアップ・リカバリ設計

**技術スタック**:
| コンポーネント | ソフトウェア | 役割 |
|----------------|--------------|------|
| MTA | Postfix 3.x | メール転送 |
| MDA | Dovecot 2.x | IMAP/POP3 |
| Webmail | Roundcube | WEBメール |
| Database | MariaDB 10.11 | Roundcube用DB |
| SSL/TLS | Let's Encrypt | 無料SSL証明書 |
| DKIM | OpenDKIM | DKIM署名 |
| Webserver | Nginx | リバースプロキシ |
| Anti-spam | Rspamd | スパムフィルタ |
| Anti-virus | ClamAV | ウイルススキャン |

### 3. 構築手順書
- 初級者向けステップバイステップ手順
- 環境構築からメールサーバー起動まで
- Docker Compose設定
- SSL証明書取得手順
- DKIM設定手順
- ユーザー作成手順

**構築所要時間**: 約2-3時間

### 4. テスト手順書
- 機能テスト（15項目）
- セキュリティテスト（10項目）
- パフォーマンステスト（8項目）
- 運用テスト（5項目）
- テスト結果記録フォーム

**テスト所要時間**: 約2.5時間

### 5. Phase 10: ローカルバックアップシステム

**主要機能**:
- ✅ 日次自動バックアップ
- ✅ 週次自動バックアップ
- ✅ チェックサム検証
- ✅ コンポーネント別リストア
- ✅ TDD開発手法による38テスト実装
- ✅ ログ記録とモニタリング

**バックアップ対象**:
- メールボックス（Maildir形式）
- データベース（MariaDB）
- 設定ファイル（Postfix, Dovecot, Nginx等）
- SSL証明書
- DKIM鍵

### 6. Phase 11-B: S3オフサイトバックアップシステム

**主要機能**:
- ✅ S3日次レプリケーション
- ✅ Object Lock（削除防止機能）
- ✅ 日次マルウェアスキャン（ClamAV + rkhunter）
- ✅ コスト監視アラート（CloudWatch + SNS）
- ✅ リストア前マルウェアスキャン

**セキュリティ対策**:
- ランサムウェア対策（S3 Object Lock COMPLIANCE）
- 3層防御（ファイルシステムスキャン + アーカイブスキャン + リストア前スキャン）
- IAM最小権限設計
- バージョニング有効化

**コスト管理**:
- 2段階閾値設定（WARNING / CRITICAL）
- ライフサイクル管理（STANDARD → GLACIER → DELETE）
- 定期的なコスト監視

**復旧シナリオ**:
- ✅ シナリオ1: インフラ復旧（IaCベース）
- ✅ シナリオ2: データ復旧（S3バックアップ）
- ✅ シナリオ3: 完全障害からの復旧
- ✅ シナリオ4: 部分復旧（コンポーネント別）

**復旧時間目標（RTO）**: 30分〜4時間（障害レベルによる）
**復旧ポイント目標（RPO）**: 24時間

### 7. Cloudflare Email Worker（MX受信システム）✅ 実装完了・稼働中

**実装完了日**: 2025-11-12
**ステータス**: ✅ 本番稼働中（安定）

**システム構成:**
```
9コンテナ稼働中:
1. Postfix (送信専用、外部Relay経由)
2. Dovecot (IMAP/POP3/LMTP)
3. MariaDB (Roundcube/usermgmt)
4. Roundcube (Webmail)
5. Rspamd (スパムフィルタ)
6. ClamAV (ウイルススキャン)
7. Nginx (リバースプロキシ)
8. usermgmt (ユーザー管理)
9. mailserver-api (メール受信API)
```

**達成された効果:**
- ✅ **サーバーレス化**: MXレコード受信をCloudflare Email Workerで処理
- ✅ **高速化**: エッジ実行、コールドスタートなし
- ✅ **高可用性**: Cloudflare SLA 99.99%
- ✅ **コスト削減**: 専用MXサーバー不要
- ✅ **セキュリティ向上**: セキュアトンネル経由通信

**メールフロー（現在）:**

受信フロー:
```
Internet (MX)
  ↓
Cloudflare Email Routing
  ↓
Cloudflare Email Worker (JavaScript)
  ↓ HTTPS POST (via Secure Tunnel)
mailserver-api (FastAPI)
  ↓ LMTP
Dovecot (メールボックス保存)
```

送信フロー:
```
Mail Client (SMTP)
  ↓
Postfix
  ↓ Relay
External SMTP Relay Service
  ↓
Internet
```

---

## 🚀 クイックスタート

### 前提条件
- Rocky Linux 9.6がインストールされている
- root権限またはsudo権限がある
- ドメイン名を取得済み
- DNSレコード設定が可能

### 構築手順概要

1. **ドキュメント確認**
   - 要件定義書で要件確認
   - 設計書でアーキテクチャ確認

2. **環境準備**
   - Docker, Docker Composeインストール
   - 必要なディレクトリ作成
   - 環境変数設定

3. **コンテナ起動**
   - Docker Compose設定ファイル作成
   - コンテナ起動・確認

4. **テスト実施**
   - 機能テスト
   - セキュリティテスト
   - パフォーマンステスト

---

## 📊 プロジェクト構成

```
mailserver/
├── README.md                    # 本ファイル
├── docker-compose.yml           # コンテナ定義
├── .env                         # 環境変数
├── config/                      # 設定ファイル
│   ├── postfix/
│   ├── dovecot/
│   ├── nginx/
│   ├── roundcube/
│   └── opendkim/
├── data/                        # データ保存先
│   ├── mailboxes/
│   ├── mysql/
│   └── ssl/
├── logs/                        # ログファイル
├── scripts/                     # 管理スクリプト
└── backups/                     # バックアップ先
```

---

## 🎯 主要機能

### メール送受信
- **SMTP**: Port 25 (受信), 465 (SMTPS), 587 (Submission)
- **IMAP**: Port 993 (IMAPS)
- **POP3**: Port 995 (POP3S)
- **WEBメール**: Port 443 (HTTPS)

### セキュリティ
- SSL/TLS暗号化（全プロトコル）
- SPF/DKIM/DMARC対応
- Let's Encrypt自動更新
- SMTP認証必須
- スパムフィルタリング（Rspamd）
- ウイルススキャン（ClamAV）

### 運用
- Docker Composeによる一元管理
- 自動バックアップ（日次/週次）
- S3オフサイトバックアップ
- マルウェアスキャン
- ログローテーション
- ユーザー管理Web UI

---

## ⚙️ システム要件

### ハードウェア
- **CPU**: 2コア以上推奨
- **メモリ**: 4GB以上推奨（ClamAV使用時は8GB推奨）
- **ディスク**: 20GB以上推奨（ユーザー数・メール量により増減）

### ソフトウェア
- **OS**: Rocky Linux 9.6
- **Docker**: 24.0.x以上
- **Docker Compose**: 2.x以上

### ネットワーク
- **グローバルIP**: 固定IPアドレス推奨
- **ポート転送**: 25, 80, 443, 465, 587, 993, 995
- **DNS管理**: A/MX/TXT/PTR/DMARCレコード設定可能

---

## 📈 性能仕様

| 項目 | 初期値 | 拡張目標 |
|------|--------|----------|
| **ユーザー数** | 5名 | 50名 |
| **ドメイン数** | 1-3個 | 10個 |
| **メール処理量** | 100通/日 | 1,000通/日 |
| **メールボックス容量** | 2GB/ユーザー | 10GB/ユーザー |
| **添付ファイル** | 25MB/メール | 25MB/メール（大容量は外部共有推奨） |

---

## 🔒 セキュリティ対策

- ✅ SSL/TLS必須（平文プロトコル無効化）
- ✅ SMTP認証必須
- ✅ SPF/DKIM/DMARCによる送信ドメイン認証
- ✅ ファイアウォール設定
- ✅ 不正中継（Open Relay）防止
- ✅ スパムフィルタリング（Rspamd）
- ✅ ウイルススキャン（ClamAV）
- ✅ 定期的なセキュリティ更新
- ✅ バックアップ暗号化
- ✅ IAM最小権限設計

---

## 🛠️ 管理スクリプト

構築後、以下の管理スクリプトが利用可能：

```bash
# ユーザー追加
./scripts/add-user.sh user@example.com password

# ドメイン追加
./scripts/add-domain.sh newdomain.com

# DKIM鍵生成
./scripts/generate-dkim.sh example.com

# バックアップ実行
./scripts/backup-mailserver.sh

# リストア実行
./scripts/restore-mailserver.sh --from <backup-path> --component all

# S3バックアップ
./scripts/sync-to-s3.sh

# マルウェアスキャン
./scripts/scan-before-restore.sh
```

---

## 📝 運用タスク

### 日次
- [ ] メール送受信動作確認
- [ ] 自動バックアップ確認
- [ ] ログ確認（エラー検出）

### 週次
- [ ] 週次バックアップ確認
- [ ] ディスク容量確認
- [ ] セキュリティログ確認

### 月次
- [ ] バックアップリストアテスト
- [ ] セキュリティ更新確認
- [ ] DNS設定確認
- [ ] SSL証明書有効期限確認
- [ ] S3バックアップコスト確認

---

## 🆘 トラブルシューティング

### よくある問題

#### メール送信できない
```bash
# Postfixログ確認
docker compose logs postfix | tail -50

# ポート確認
netstat -tuln | grep -E '25|465|587'

# SMTP認証確認
docker compose exec postfix postconf -n | grep smtpd_sasl
```

#### メール受信できない
```bash
# Dovecotログ確認
docker compose logs dovecot | tail -50

# LMTP動作確認
docker compose exec dovecot doveadm log find

# メールボックス確認
docker compose exec dovecot doveadm mailbox list -u user@example.com
```

#### WEBメールアクセスできない
```bash
# Nginxログ確認
docker compose logs nginx | tail -50

# SSL証明書確認
openssl s_client -connect mail.example.com:443

# Roundcube設定確認
docker compose exec roundcube cat /etc/roundcube/config.inc.php
```

#### コンテナが起動しない
```bash
# コンテナ状態確認
docker compose ps

# 全ログ確認
docker compose logs

# 全コンテナ再起動
docker compose down
docker compose up -d

# 個別コンテナ再起動
docker compose restart <service-name>
```

#### バックアップ失敗
```bash
# バックアップログ確認
tail -f ~/.mailserver-backup.log

# ディスク容量確認
df -h

# 権限確認
ls -la <backup-directory>
```

#### S3同期失敗
```bash
# S3バックアップログ確認
tail -f ~/.s3-backup-cron.log

# AWS認証確認
aws s3 ls --profile mailserver-backup

# IAM権限確認
aws iam get-user --profile mailserver-backup
```

---

## 📞 サポート

### 参考リンク
- [Postfix公式ドキュメント](http://www.postfix.org/documentation.html)
- [Dovecot公式ドキュメント](https://doc.dovecot.org/)
- [Roundcube公式ドキュメント](https://github.com/roundcube/roundcubemail/wiki)
- [Let's Encrypt公式サイト](https://letsencrypt.org/)
- [Docker公式ドキュメント](https://docs.docker.com/)
- [Rspamd公式ドキュメント](https://rspamd.com/doc/)
- [ClamAV公式ドキュメント](https://docs.clamav.net/)

---

## 📜 ライセンス

本プロジェクトで使用する各ソフトウェアは、それぞれのライセンスに従います。

---

**作成日**: 2025-10-31
**最終更新**: 2025-11-12
**バージョン**: 2.0
