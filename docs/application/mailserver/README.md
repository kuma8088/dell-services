# メールサーバー構築プロジェクト

**プロジェクト概要**: Xserver WEBメール機能相当のメールサーバーをDocker Compose環境で構築

**構築環境**: Dell RockyLinux 9.6

**構築方式**: Docker Compose

---

## 📚 ドキュメント一覧

### 1. [要件定義書 (01_requirements.md)](./01_requirements.md)
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

### 2. [設計書 (02_design.md)](./02_design.md)
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

### 3. [構築手順書 (03_installation.md)](./03_installation.md)
- 初級者向けステップバイステップ手順
- 環境構築からメールサーバー起動まで
- Docker Compose設定
- SSL証明書取得手順
- DKIM設定手順
- ユーザー作成手順

**構築所要時間**: 約2-3時間

### 4. [テスト手順書 (04_testing.md)](./04_testing.md)
- 機能テスト（15項目）
- セキュリティテスト（10項目）
- パフォーマンステスト（8項目）
- 運用テスト（5項目）
- テスト結果記録フォーム

**テスト所要時間**: 約2.5時間

### 5. Phase 10: ローカルバックアップシステム

#### [バックアップ実装ガイド (backup/03_implementation.md)](./backup/03_implementation.md)
- TDD開発手法による38テスト実装
- 日次/週次自動バックアップ（cron設定）
- コンポーネント別バックアップ（メール、MySQL、設定）
- リストア手順（完全復旧・部分復旧）
- バックアップ検証・モニタリング

**主要機能**:
- ✅ 日次自動バックアップ（AM 3:00）
- ✅ 週次自動バックアップ（日曜 AM 2:00）
- ✅ チェックサム検証
- ✅ コンポーネント別リストア
- ✅ ログ記録（~/.mailserver-backup.log）

**バックアップ先**: `/mnt/backup-hdd/mailserver/`

### 6. Phase 11-B: S3オフサイトバックアップシステム

#### [要件定義 (backup/05_s3backup_requirements.md)](./backup/05_s3backup_requirements.md)
- ランサムウェア対策（S3 Object Lock COMPLIANCE）
- コスト監視（2段階閾値: 10円WARNING / 100円CRITICAL）
- 自動マルウェアスキャン（ClamAV + rkhunter）
- IAM最小権限設計

#### [設計書 (backup/06_s3backup_design.md)](./backup/06_s3backup_design.md)
- S3バケット設計（Versioning + Object Lock）
- Terraform構成（S3, IAM, CloudWatch, SNS）
- マルウェアスキャン設計（3層防御）
- ライフサイクル管理（30d STANDARD → 60d GLACIER → 90d DELETE）

#### [実装ガイド (backup/07_s3backup_implementation.md)](./backup/07_s3backup_implementation.md)
- Terraform実装（S3インフラ構築）
- マルウェアスキャン環境構築
- バックアップスクリプト実装（4スクリプト）
- cron自動実行設定
- 動作確認・トラブルシューティング

**主要機能**:
- ✅ S3日次レプリケーション（AM 4:00）
- ✅ Object Lock（30日間削除不可）
- ✅ 日次マルウェアスキャン（AM 5:00）
- ✅ コスト監視アラート（CloudWatch + SNS）
- ✅ リストア前マルウェアスキャン

**実装所要時間**: 約3-4時間

#### [リカバリー手順書 (backup/08_recovery_procedures.md)](./backup/08_recovery_procedures.md)
- Githubからのインフラ復旧（IaC復旧）
- S3からのデータ復旧（メール・DB復旧）
- 完全障害からの復旧（Github + S3）
- 部分復旧（コンポーネント別）
- 検証手順・トラブルシューティング

**復旧シナリオ**:
- ✅ シナリオ1: Githubからのインフラ復旧（RTO: 2時間）
- ✅ シナリオ2: S3からのデータ復旧（RTO: 1時間、RPO: 24時間）
- ✅ シナリオ3: 完全障害からの復旧（RTO: 4時間、RPO: 24時間）
- ✅ シナリオ4: 部分復旧（RTO: 30分、RPO: 24時間）

**復旧所要時間**: 30分〜4時間（障害レベルによる）

---

## 🚀 クイックスタート

### 前提条件
- Rocky Linux 9.6がインストールされている
- root権限またはsudo権限がある
- ドメイン名を取得済み
- DNSレコード設定が可能

### 構築手順概要

1. **ドキュメント確認**
   ```bash
   cd /Docs/application/mailserver/
   cat 01_requirements.md  # 要件確認
   cat 02_design.md        # 設計確認
   ```

2. **構築実施**
   ```bash
   # 構築手順書に従って実施
   cat 03_installation.md
   ```

3. **テスト実施**
   ```bash
   # テスト手順書に従って実施
   cat 04_testing.md
   ```

---

## 📊 プロジェクト構成

```
/Docs/application/mailserver/
├── README.md                    # 本ファイル
├── 01_requirements.md           # 要件定義書
├── 02_design.md                 # 設計書
├── 03_installation.md           # 構築手順書
├── 04_testing.md                # テスト手順書
└── xserver-mail-function        # 参照: Xserver機能仕様
```

**実際の構築先**:
```
/opt/mailserver/
├── docker-compose.yml
├── .env
├── config/
├── data/
├── logs/
├── scripts/
└── backups/
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

### 運用
- Docker Composeによる一元管理
- 自動バックアップ（日次）
- ログローテーション
- ユーザー管理スクリプト

---

## ⚙️ システム要件

### ハードウェア
- **CPU**: 2コア以上推奨
- **メモリ**: 4GB以上推奨
- **ディスク**: 20GB以上推奨

### ソフトウェア
- **OS**: Rocky Linux 9.6
- **Docker**: 24.0.x以上
- **Docker Compose**: 2.x以上

### ネットワーク
- **グローバルIP**: 固定IPアドレス
- **ポート転送**: 25, 80, 443, 465, 587, 993, 995
- **DNS管理**: Route53またはCloudflareでA/MX/TXT/PTR/DMARCレコード設定可能

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
- ✅ 定期的なセキュリティ更新

---

## 🛠️ 管理スクリプト

構築後、以下のスクリプトが利用可能：

```bash
# ユーザー追加
/opt/mailserver/scripts/add-user.sh user@example.com password

# ドメイン追加
/opt/mailserver/scripts/add-domain.sh newdomain.com

# DKIM鍵生成
/opt/mailserver/scripts/generate-dkim.sh example.com

# バックアップ実行
/opt/mailserver/scripts/backup.sh
```

---

## 📝 運用タスク

### 日次
- [ ] メール送受信動作確認

### 週次
- [ ] ログ確認
- [ ] ディスク容量確認

### 月次
- [ ] バックアップテスト
- [ ] セキュリティ更新確認
- [ ] DNS設定確認

---

## 🆘 トラブルシューティング

### よくある問題

#### メール送信できない
```bash
# Postfixログ確認
docker compose logs postfix | tail -50

# ポート確認
netstat -tuln | grep -E '25|465|587'
```

#### WEBメールアクセスできない
```bash
# Nginxログ確認
docker compose logs nginx | tail -50

# SSL証明書確認
openssl s_client -connect mail.example.com:443
```

#### コンテナが起動しない
```bash
# コンテナ状態確認
docker compose ps

# 全コンテナ再起動
docker compose down
docker compose up -d
```

詳細は `03_installation.md` の「12. トラブルシューティング」を参照

---

## 📞 サポート

### ドキュメント
- 要件定義: `01_requirements.md`
- 設計詳細: `02_design.md`
- 構築手順: `03_installation.md`
- テスト手順: `04_testing.md`

### 参考リンク
- [Postfix公式ドキュメント](http://www.postfix.org/documentation.html)
- [Dovecot公式ドキュメント](https://doc.dovecot.org/)
- [Roundcube公式ドキュメント](https://github.com/roundcube/roundcubemail/wiki)
- [Let's Encrypt公式サイト](https://letsencrypt.org/)

---

## 📜 ライセンス

本プロジェクトで使用する各ソフトウェアは、それぞれのライセンスに従います。

---

**作成日**: 2025-10-31
**バージョン**: 1.0
**作成者**: Claude
