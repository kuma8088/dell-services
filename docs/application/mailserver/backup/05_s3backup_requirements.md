# S3バックアップシステム要件定義書（Phase 11-B）

**作成日**: 2025-11-07
**バージョン**: 1.0
**対象システム**: Dell Mailserver → AWS S3 Replication
**前提ドキュメント**: [01_requirements.md](./01_requirements.md), [03_implementation.md](./03_implementation.md)

---

## 📋 目次

1. [プロジェクト概要](#1-プロジェクト概要)
2. [背景と目的](#2-背景と目的)
3. [脅威モデル](#3-脅威モデル)
4. [バックアップ対象分類](#4-バックアップ対象分類)
5. [機能要件](#5-機能要件)
6. [非機能要件](#6-非機能要件)
7. [リカバリー要件](#7-リカバリー要件)
8. [運用要件](#8-運用要件)
9. [セキュリティ要件](#9-セキュリティ要件)
10. [コスト試算](#10-コスト試算)

---

## 1. プロジェクト概要

### 1.1 プロジェクト名
**Dell Mailserver S3バックアップシステム（ランサムウェア対策）**

### 1.2 目的
- **PRIMARY**: ランサムウェア攻撃からのデータ保護
- **SECONDARY**: 外部からアクセス可能な環境（EC2, Dell）のデータ保全
- **TERTIARY**: 災害復旧時のデータソース多重化

### 1.3 スコープ
- **IN SCOPE**:
  - 状態データ（State）: Mail, MySQL DB, DKIM keys, Dovecot users, .env
  - 日次バックアップのS3レプリケーション（30日間保持）
  - S3 Object Lock（WORM）による改ざん防止
  - リストア後のマルウェアスキャン（ClamAV + rkhunter）

- **OUT OF SCOPE**:
  - Infrastructure as Code（IaC）: GitHubで管理（Terraform, docker-compose.yml）
  - EC2環境のバックアップ（State Dataを保持しないため）
  - 暗号化バックアップ（Phase 2検討事項）

### 1.3.1 EC2環境について

**EC2は本バックアップの対象外**:

理由:
1. **State Dataを保持しない**: メール転送専用、データ保存なし
2. **完全なIaC管理**: 全設定がTerraformテンプレート化
3. **復旧方法**: `terraform apply` で数分で再構築可能
4. **ログデータ**: CloudWatch Logsに送信（オプション）

EC2のランサムウェア対策:
- インフラコード: GitHubでバージョン管理済み
- 設定ファイル: Terraformテンプレート（Git管理）
- 復旧手順: `terraform destroy && terraform apply`

脅威モデルでの位置づけ:
- ✅ 攻撃侵入経路として脅威分析に含める
- ❌ バックアップ対象としては不要

### 1.4 前提条件
- Phase 10（ローカルバックアップシステム）が実装済み
- 外付けHDDに日次バックアップが正常に実行されている
- AWS環境（IAM, S3）へのアクセス権限が付与されている

---

## 2. 背景と目的

### 2.1 背景

**現在のリスク状況**:
```
Dell Mailserver (外部公開)
├─ 外部からSSH/SMTP/IMAPアクセス可能
├─ 巧妙なランサムウェア攻撃のリスク
└─ バックアップデータが同一サーバー内に存在（外付けHDD）

EC2 MX Gateway (外部公開)
├─ MXレコード公開（25/tcp）
├─ ランサムウェア侵入経路の可能性
└─ Dell環境へのトンネル経由攻撃リスク
```

**問題点**:
- **単一障害点**: 外付けHDDがDellサーバーに接続されている
- **同時被害リスク**: ランサムウェアがDell環境に侵入した場合、バックアップも暗号化される可能性
- **オフサイトバックアップ不在**: 物理的に分離されたバックアップが存在しない

### 2.2 ビジネス要件

| 要件 | 説明 |
|-----|------|
| **データ保全** | ランサムウェア攻撃から業務データを保護 |
| **復旧保証** | 最悪の場合でもGit（IaC） + S3（State）から完全復旧可能 |
| **コスト最適化** | 費用対効果の高いバックアップ戦略（日次30日のみS3） |
| **運用負荷削減** | 自動化による手動作業の排除 |
| **早期検知** | 定期マルウェアスキャンによる侵入の早期発見 |

### 2.3 成功基準
- ✅ 日次バックアップがS3に自動レプリケーションされる（毎日04:00）
- ✅ S3 Object Lock により改ざん・削除が30日間不可能
- ✅ ランサムウェア攻撃発生時、S3からデータ復旧可能（RPO: 24時間）
- ✅ 定期マルウェアスキャンで侵入を早期検知（日次・週次）
- ✅ 現行データ量での月次コストが10円以内（異常検知閾値: 100円）

---

## 3. 脅威モデル

### 3.1 ランサムウェア攻撃シナリオ

**シナリオ1: Dell直接侵入**
```
攻撃者 → SSH/SMTPポート → Dell Mailserver
       ↓
1. 脆弱性エクスプロイト or 認証情報漏洩
2. 権限昇格（root/system-admin）
3. メールデータ暗号化
4. 外付けHDDバックアップ暗号化
5. .env / DKIM keys 削除
```

**シナリオ2: EC2経由侵入**
```
攻撃者 → MXポート → EC2 Postfix
       ↓
1. コンテナ脱出 or EC2侵害
2. Tailscale VPN経由でDell環境アクセス
3. メールデータ暗号化
4. バックアップデータ暗号化
```

**シナリオ3: ゼロデイ攻撃**
```
攻撃者 → 未知の脆弱性 → Dell/EC2
       ↓
1. システム全体の侵害
2. バックアップスクリプト改ざん
3. バックアップデータ破壊
```

### 3.2 攻撃対象分類

| 資産 | 攻撃リスク | S3保護必要性 | 理由 |
|-----|-----------|------------|------|
| **メールデータ** | 🔴 HIGH | ✅ 必須 | 業務継続に必須、再生成不可 |
| **MySQL DB** | 🔴 HIGH | ✅ 必須 | ユーザー情報・設定、再生成困難 |
| **DKIM keys** | 🟡 MEDIUM | ✅ 必須 | 再発行可能だがDNS再設定が必要 |
| **Dovecot users** | 🟡 MEDIUM | ✅ 必須 | 再生成可能だが設定情報含む |
| **.env** | 🟡 MEDIUM | ✅ 必須 | 機密情報、再生成可能だが手間 |
| **SSL証明書** | 🟢 LOW | ❌ 不要 | Let's Encrypt自動再取得可能 |
| **Terraform** | 🟢 LOW | ❌ 不要 | GitHubで管理、バージョン管理済み |
| **docker-compose.yml** | 🟢 LOW | ❌ 不要 | GitHubで管理、バージョン管理済み |

---

## 4. バックアップ対象分類

### 4.1 データとコードの分類

**RED（State Data）: S3バックアップ必須**
```
/mnt/backup-hdd/mailserver/weekly/YYYY-week-WW/
├── mail/                       # メールデータ（最重要）
│   └── vmail/                  # 全ドメイン・全ユーザー
├── mysql/                      # データベース
│   ├── usermgmt.sql.gz         # ユーザー管理DB
│   └── roundcubemail.sql.gz    # Webメール設定
├── dkim/                       # DKIM秘密鍵
│   └── opendkim-keys.tar.gz    # 各ドメインの秘密鍵
├── config/                     # 設定ファイル（一部）
│   ├── .env                    # 環境変数（機密情報）
│   └── dovecot/users           # Dovecotユーザー設定
└── checksums.sha256            # 整合性検証
```

**GREEN（Infrastructure as Code）: GitHubで管理、S3不要**
```
GitHub: anthropics/onprem-infra-system
├── services/mailserver/
│   ├── docker-compose.yml      # コンテナ定義
│   ├── config/postfix/         # テンプレート設定
│   ├── config/dovecot/         # テンプレート設定
│   └── terraform/              # EC2インフラ定義
└── docs/                       # ドキュメント
```

### 4.2 S3バックアップ対象

**日次バックアップディレクトリ全体**:
```bash
SOURCE: /mnt/backup-hdd/mailserver/daily/YYYY-MM-DD/
DESTINATION: s3://mailserver-backup-ACCOUNT-ID/daily/YYYY-MM-DD/
```

**サイズ試算**（現行環境）:
- メールデータ: 3.9M（成長予測: 10MB/月）
- MySQL: 10KB（成長予測: 100KB/月）
- DKIM: 8KB（固定）
- Config: 100KB（成長予測: 10KB/月）
- **合計**: 約4MB/日（月次: 120MB、年次: ~1.4GB）

---

## 5. 機能要件

### 5.1 自動レプリケーション

**FR-01: 日次S3レプリケーション**
- トリガー: ローカル日次バックアップ完了後（毎日 03:00実行後）
- タイミング: 毎日 04:00（ローカルバックアップ完了1時間後）
- 対象: `/mnt/backup-hdd/mailserver/daily/YYYY-MM-DD/` 全体
- 方式: AWS CLI `aws s3 sync` または `aws s3 cp --recursive`

**FR-02: バックアップ検証**
- ローカルチェックサム検証（`checksums.sha256`）
- S3アップロード後のETag検証
- アップロード完了後の整合性確認

**FR-03: 保存期間とライフサイクル**
```yaml
S3ライフサイクルポリシー:
  STANDARD:
    retention: 30日間
    object_lock: COMPLIANCE mode

  GLACIER:
    transition_after: 30日
    retention: 60日間（追加）

  DELETE:
    after: 90日間
```

**保存期間の設計根拠**:
- **30日間（STANDARD）**: ランサムウェア即座発動ケースに対応
- **潜伏型攻撃への対処**: リストア後のマルウェアスキャンで対応
- **実用性重視**: 30日以上前のメールデータは業務継続に使えない

### 5.2 リカバリー機能

**FR-04: S3からのダウンロード**
```bash
# 最新日次バックアップ取得
aws s3 sync s3://mailserver-backup-ACCOUNT-ID/daily/latest/ /tmp/s3-restore/

# 特定時点のバックアップ取得
aws s3 sync s3://mailserver-backup-ACCOUNT-ID/daily/2025-11-06/ /tmp/s3-restore/
```

**FR-05: リストアスクリプト統合**
```bash
# 既存の restore-mailserver.sh を使用
./restore-mailserver.sh --from /tmp/s3-restore/ --component all
```

**FR-06: マルウェアスキャン（重要）**

ランサムウェア予防・検知のため、2つのスキャンモードを実装:

**A. 定期スキャン（予防的監視）**

Dell環境全体を定期的にスキャン（侵入検知・早期発見）:

```bash
# 日次スキャン（毎日05:00、S3アップロード後）
# スクリプト: scan-mailserver.sh --daily

# 対象:
# 1. メールデータ（増分スキャン）
docker exec mailserver-clamav clamscan -r /var/mail/vmail/ \
  --infected --move=/var/quarantine/ --log=/var/log/clamav/daily-scan.log

# 2. ホストOS側のメールデータディレクトリ
clamscan -r /opt/onprem-infra-system/project-root-infra/services/mailserver/data/mail/ \
  --infected --log=/var/log/clamav/host-daily-scan.log

# 週次スキャン（毎週日曜06:00）
# スクリプト: scan-mailserver.sh --weekly

# 追加対象:
# 3. バックアップデータ
clamscan -r /mnt/backup-hdd/mailserver/ \
  --infected --log=/var/log/clamav/backup-scan.log

# 4. システム全体のルートキット検査
rkhunter --check --skip-keypress --report-warnings-only \
  --log=/var/log/rkhunter/weekly-scan.log
```

**B. リストア後スキャン（復旧時検証）**

リストア完了後の包括的スキャン:

```bash
# スクリプト: scan-restored-data.sh

# 1. S3ダウンロードファイルのスキャン
clamscan -r /tmp/s3-restore/ --infected --remove \
  --log=/var/log/clamav/restore-scan.log

# 2. リストア後のメールデータスキャン
docker exec mailserver-clamav clamscan -r /var/mail/vmail/ \
  --infected --move=/var/quarantine/ --log=/var/log/clamav/post-restore-scan.log

# 3. システム全体のルートキット検査
rkhunter --check --skip-keypress --report-warnings-only
```

**スキャン実装要件**:
- 自動実行スクリプト:
  - `scan-mailserver.sh` (定期スキャン)
  - `scan-restored-data.sh` (リストア後)
- cron設定:
  - 日次: 毎日05:00（S3アップロード後）
  - 週次: 日曜06:00
- 検出時の処理:
  - 自動隔離（`/var/quarantine/`）
  - 管理者アラート（メール通知）
  - 詳細ログ記録
- スキャンログ保存: 90日間

### 5.3 監視とアラート

**FR-07: アップロード監視**
- S3アップロード成功/失敗のログ記録
- 失敗時の管理者メール通知
- CloudWatch Logs へのログ送信（オプション）

**FR-08: コスト監視（2段階閾値）**
- AWS Cost Explorer でS3コスト追跡
- **WARNING**: 月次コスト10円超過時のアラート（現行データ量での想定値超過）
- **CRITICAL**: 月次コスト100円超過時のアラート（異常な増加、調査必要）
- CloudWatch Alarms + SNS によるメール通知

---

## 6. 非機能要件

### 6.1 パフォーマンス要件

**NFR-01: アップロード時間**
- 4MB日次バックアップ: 5分以内に完了
- 100MB想定（将来）: 30分以内に完了
- ネットワーク帯域: 最低1Mbps以上

**NFR-02: システム影響**
- アップロード中のCPU使用率: 10%以下
- アップロード中のネットワーク帯域: 最大50%使用

### 6.2 信頼性要件

**NFR-03: アップロード成功率**
- 目標成功率: 99%以上
- 失敗時の自動リトライ: 最大3回（指数バックオフ）

**NFR-04: データ整合性**
- S3 Object Lock により改ざん不可能
- バージョニング有効化（誤削除対策）
- チェックサム検証（SHA256）

### 6.3 セキュリティ要件

**NFR-05: IAM権限分離**
```yaml
IAM Role: mailserver-backup-uploader
  - s3:PutObject（日次バックアップバケットのみ）
  - s3:PutObjectRetention（Object Lock設定）
  - s3:GetObject（検証用）

IAM Role: mailserver-backup-admin
  - s3:GetObject（全バックアップ）
  - s3:ListBucket（バックアップ一覧）
  - s3:GetObjectVersion（バージョン管理）
  - 注: s3:DeleteObject 権限なし（削除は制御不可）

IAM Role: disaster-recovery
  - s3:GetObject（緊急時のみ）
  - MFA必須（AWS CLI --profile dr-mfa）
```

**NFR-06: 暗号化**
- S3サーバーサイド暗号化: AES-256（SSE-S3）
- 転送時暗号化: TLS 1.2以上（AWS CLI自動）

---

## 7. リカバリー要件

### 7.1 リカバリー目標

**RR-01: RTO（Recovery Time Objective）**
- S3からのダウンロード: **1時間以内**
- マルウェアスキャン: **2時間以内**
- データリストア: **1時間以内**
- 合計復旧時間: **4時間以内**

**RR-02: RPO（Recovery Point Objective）**
- 日次バックアップ: **最大24時間分のデータ損失**
- 許容範囲: 1日分のメールデータ損失を許容

### 7.2 リカバリーシナリオ

**シナリオ1: ランサムウェア被害後の完全復旧**
```bash
# Step 1: Git からインフラコード取得
git clone https://github.com/anthropics/onprem-infra-system.git
cd onprem-infra-system/project-root-infra

# Step 2: Terraform でEC2インフラ再構築
cd services/mailserver/terraform/ec2
terraform init
terraform apply -auto-approve

# Step 3: Dell環境にDocker Compose セットアップ
cd ../../
docker compose up -d

# Step 4: S3から最新日次バックアップをダウンロード＋リストア
# restore-from-s3.sh が以下を自動実行:
# - S3ダウンロード
# - チェックサム検証
# - マルウェアスキャン
# - データリストア
./scripts/restore-from-s3.sh --date latest --component all
# → マルウェア検出時: 自動で前日バックアップにフォールバック

# Step 5: リストア後マルウェアスキャン
./scripts/scan-restored-data.sh --source /opt/onprem-infra-system/project-root-infra/services/mailserver/data/mail/

# Step 6: 動作確認
docker compose ps
docker logs mailserver-postfix
./scripts/test-mailserver.sh
```

**シナリオ2: 特定時点へのロールバック**
```bash
# 3日前のバックアップから復旧
./scripts/restore-from-s3.sh --date 2025-11-04 --component mysql

# restore-from-s3.sh が以下を自動実行:
# 1. S3から2025-11-04のバックアップをダウンロード
# 2. チェックサム検証
# 3. マルウェアスキャン
# 4. MySQLのみリストア
```

**シナリオ3: 手動リストア（デバッグ用）**
```bash
# S3から手動ダウンロード
aws s3 sync s3://mailserver-backup-ACCOUNT-ID/daily/2025-11-07/ /tmp/s3-restore/

# マルウェアスキャン実施
./scripts/scan-restored-data.sh --source /tmp/s3-restore/

# 既存スクリプトで個別リストア
./scripts/restore-mailserver.sh --from /tmp/s3-restore/ --component config
```

---

## 8. 運用要件

### 8.1 スクリプト配置

**OR-01: スクリプト一覧**
```
/opt/onprem-infra-system/project-root-infra/services/mailserver/scripts/
├── backup-mailserver.sh        # Phase 10: ローカルバックアップ
├── restore-mailserver.sh       # Phase 10: ローカルリストア
├── backup-to-s3.sh             # Phase 11-B: S3レプリケーション
├── restore-from-s3.sh          # Phase 11-B: S3ダウンロード＋リストア（ラッパー）
├── scan-mailserver.sh          # Phase 11-B: 定期マルウェアスキャン
└── scan-restored-data.sh       # Phase 11-B: リストア後スキャン
```

**スクリプト詳細**:

| スクリプト名 | 役割 | 使用例 |
|------------|------|--------|
| `backup-mailserver.sh` | ローカルバックアップ実行 | `./backup-mailserver.sh --daily` |
| `restore-mailserver.sh` | ローカルディレクトリからリストア | `./restore-mailserver.sh --from /mnt/backup-hdd/mailserver/latest/` |
| `backup-to-s3.sh` | ローカルバックアップをS3にアップロード | `./backup-to-s3.sh` (cron実行) |
| `restore-from-s3.sh` | S3ダウンロード → restore-mailserver.sh 呼び出し | `./restore-from-s3.sh --date 2025-11-07 --component all` |
| `scan-mailserver.sh` | 定期スキャン（日次/週次） | `./scan-mailserver.sh --daily` |
| `scan-restored-data.sh` | リストア後のマルウェアスキャン | `./scan-restored-data.sh --source /tmp/s3-restore/` |

**restore-from-s3.sh の内部動作**:
```bash
# 1. S3からダウンロード
aws s3 sync s3://mailserver-backup-ACCOUNT-ID/daily/${DATE}/ /tmp/s3-restore/

# 2. チェックサム検証
cd /tmp/s3-restore/
sha256sum -c checksums.sha256

# 3. 既存スクリプトを呼び出し
/path/to/restore-mailserver.sh --from /tmp/s3-restore/ --component ${COMPONENT}

# 4. クリーンアップ
rm -rf /tmp/s3-restore/
```

### 8.2 cron設定

**OR-02: 自動実行スケジュール**
```bash
# 毎日 03:00 - ローカル日次バックアップ（Phase 10）
0 3 * * * /opt/onprem-infra-system/project-root-infra/services/mailserver/scripts/backup-mailserver.sh --daily >> ~/.mailserver-backup.log 2>&1

# 毎日 04:00 - S3レプリケーション（Phase 11-B）
0 4 * * * /opt/onprem-infra-system/project-root-infra/services/mailserver/scripts/backup-to-s3.sh >> ~/.mailserver-s3backup.log 2>&1

# 毎日 05:00 - 日次マルウェアスキャン（Phase 11-B）
0 5 * * * /opt/onprem-infra-system/project-root-infra/services/mailserver/scripts/scan-mailserver.sh --daily >> ~/.mailserver-scan.log 2>&1

# 毎週日曜 06:00 - 週次マルウェアスキャン（Phase 11-B）
0 6 * * 0 /opt/onprem-infra-system/project-root-infra/services/mailserver/scripts/scan-mailserver.sh --weekly >> ~/.mailserver-scan.log 2>&1
```

### 8.3 監視とログ

**OR-03: ログ管理**

ログファイル:
- S3バックアップ: `~/.mailserver-s3backup.log`
- マルウェアスキャン: `~/.mailserver-scan.log`
- ClamAV詳細ログ: `/var/log/clamav/`
- rkhunter詳細ログ: `/var/log/rkhunter/`

ログローテーション: 90日間保持

ログ内容:
- タイムスタンプ
- 処理結果（成功/失敗）
- データサイズ
- 検出されたマルウェア（該当時）
- エラー情報

**OR-04: CloudWatch統合（オプション）**
```bash
# AWS CloudWatch Logs にログ送信
aws logs put-log-events \
  --log-group-name /mailserver/s3-backup \
  --log-stream-name dell-daily \
  --log-events timestamp=$(date +%s000),message="$(tail -n 1 ~/.mailserver-s3backup.log)"
```

### 8.4 テストとメンテナンス

**OR-05: S3リストアテスト**
- 頻度: 四半期ごと（3ヶ月に1回）
- 内容: S3からテスト環境へのリストア実施
- 検証:
  - データ整合性
  - マルウェアスキャン動作
  - リストア所要時間
  - 手順書の有効性

**OR-06: マルウェアスキャンレビュー**
- 頻度: 月次
- 確認項目:
  - スキャンログ確認
  - 隔離ファイル確認（`/var/quarantine/`）
  - ClamAV/rkhunter定義ファイル更新状況
- アクション: 検出があった場合の詳細調査

**OR-07: コストレビュー**
- 頻度: 月次
- 確認項目: S3ストレージコスト、データ転送コスト、リクエストコスト
- アクション: コスト異常時のアラート、保存期間の見直し

---

## 9. セキュリティ要件

### 9.1 S3バケット設定

**SR-01: バケットポリシー**
```json
{
  "Version": "2012-10-17",
  "Statement": [
    {
      "Sid": "DenyInsecureTransport",
      "Effect": "Deny",
      "Principal": "*",
      "Action": "s3:*",
      "Resource": [
        "arn:aws:s3:::mailserver-backup-ACCOUNT-ID",
        "arn:aws:s3:::mailserver-backup-ACCOUNT-ID/*"
      ],
      "Condition": {
        "Bool": {
          "aws:SecureTransport": "false"
        }
      }
    },
    {
      "Sid": "DenyUnencryptedObjectUploads",
      "Effect": "Deny",
      "Principal": "*",
      "Action": "s3:PutObject",
      "Resource": "arn:aws:s3:::mailserver-backup-ACCOUNT-ID/*",
      "Condition": {
        "StringNotEquals": {
          "s3:x-amz-server-side-encryption": "AES256"
        }
      }
    }
  ]
}
```

**SR-02: Object Lock設定**
```yaml
Object Lock Configuration:
  Mode: COMPLIANCE
  Retention:
    Days: 90
    Mode: COMPLIANCE

  # COMPLIANCE モード = 誰も削除不可能（rootユーザーでも）
  # GOVERNANCE モード = 特定権限で削除可能（使用しない）
```

**SR-03: バージョニング**
- バージョニング: 有効化（必須、Object Lock前提条件）
- 誤削除保護: 削除マーカー作成、実データは保持
- バージョン保存期間: 90日間（Object Lock期間と一致）

### 9.2 IAM認証情報管理

**SR-04: AWS認証情報の保管**
```bash
# Dell環境での AWS CLI 設定
aws configure --profile mailserver-backup
# Access Key: AKIA... （uploader role）
# Secret Key: （KeePass等で管理）
# Region: ap-northeast-1

# 認証情報ファイル
~/.aws/credentials
chmod 600 ~/.aws/credentials
```

**SR-05: IAM Access Key ローテーション**
- 頻度: 90日ごと
- 手順: 新規Access Key作成 → スクリプト更新 → 旧Key無効化
- 記録: Key作成日をドキュメント化

---

## 10. コスト試算

### 10.1 現行データ量でのコスト

**前提条件**:
- リージョン: ap-northeast-1（東京）
- データ量: 4MB/日（日次バックアップ）
- 保存期間: 30日間（STANDARD）+ 60日間（GLACIER）
- 為替レート: 1 USD = 150 JPY

**S3ストレージコスト**:
```yaml
STANDARD（30日間）:
  データ量: 4MB × 30日 = 120MB
  単価: $0.025/GB/月
  コスト: 120MB × $0.025 / 1024 = $0.0029/月 ≈ 0.44円/月

GLACIER（60日間追加）:
  データ量: 4MB × 60日 = 240MB
  単価: $0.005/GB/月
  コスト: 240MB × $0.005 / 1024 = $0.0012/月 ≈ 0.18円/月

合計ストレージコスト: 0.62円/月 ≈ 7.4円/年
```

**データ転送コスト**:
```yaml
アップロード（PUT）:
  頻度: 日次（365回/年）
  データ量: 4MB/日
  単価: $0 （インターネットからS3へのPUTは無料）
  コスト: 0円

リクエストコスト（PUT）:
  リクエスト数: 約100ファイル/日（mail, mysql, config, checksumなど）
  単価: $0.0047/1000 PUT requests
  コスト: 100 × 365 × $0.0047 / 1000 = $0.17/年 ≈ 25.5円/年

ダウンロード（GET）:
  頻度: 四半期テスト（年4回）+ 緊急時
  データ量: 4MB × 4回 = 16MB/年
  単価: $0.114/GB（ap-northeast-1から外部）
  コスト: 16MB × $0.114 / 1024 = $0.0018/年 ≈ 0.27円/年

合計: 7.4 + 25.5 + 0.27 = 33.2円/年 ≈ 2.8円/月
```

### 10.2 将来予測（データ成長シナリオ）

**シナリオ1: 中成長（100MB/日）**
```yaml
想定: メールデータ成長（ユーザー増加、添付ファイル増加）

ストレージコスト:
  STANDARD: 100MB × 30日 × $0.025 / 1024 = $0.073/月 ≈ 11円/月
  GLACIER: 100MB × 60日 × $0.005 / 1024 = $0.029/月 ≈ 4.4円/月

リクエストコスト: 約25.5円/年（ファイル数は変わらない）

合計: 約15.4円/月 ≈ 185円/年
```

**シナリオ2: 高成長（1GB/日）**
```yaml
想定: 大量ユーザー、大容量添付ファイル

ストレージコスト:
  STANDARD: 1GB × 30日 × $0.025 = $0.75/月 ≈ 113円/月
  GLACIER: 1GB × 60日 × $0.005 = $0.3/月 ≈ 45円/月

合計: 約158円/月 ≈ 1896円/年
```

### 10.3 コスト最適化戦略

**CO-01: Daily 30日のみS3保存（Weekly削除）**
- 理由: ランサムウェア対策は30日で十分（潜伏型はマルウェアスキャンで対応）
- 効果: Weekly削除により、コストを抑制

**CO-02: ライフサイクルポリシーの最適化**
- STANDARD 30日 → 即座アクセス期間（ランサムウェア対策）
- GLACIER 60日 → 低頻度アクセス期間（保険）
- DELETE 90日 → 総保存期間3ヶ月

**CO-03: 圧縮効率の向上（オプション）**
- 現状: gzip圧縮（MySQL）、rsync増分（mail）
- 検討: tar.gz全体を再圧縮（重複排除）
- 効果: 10-20%のサイズ削減
- 注意: 圧縮処理時間とCPU負荷のトレードオフ

**CO-04: マルウェアスキャンのコスト**
- ClamAV/rkhunter: オープンソース（無料）
- 追加コスト: ホストOS側のClamAVインストールのみ（dnfパッケージ）
- 運用コスト: CPU使用率増加（週次スキャン時のみ）

---

## 📝 付録

### A. 関連ドキュメント

- [01_requirements.md](./01_requirements.md) - ローカルバックアップ要件
- [03_implementation.md](./03_implementation.md) - ローカルバックアップ実装
- [04_recovery.md](./04_recovery.md) - リカバリー手順
- [Mailserver README](../README.md) - Mailserver全体ドキュメント

### B. 用語集

| 用語 | 説明 |
|-----|------|
| **WORM** | Write Once Read Many - 一度書き込んだら読み取り専用 |
| **Object Lock** | S3のWORM機能、指定期間削除・上書き不可 |
| **COMPLIANCE Mode** | rootユーザーでも削除不可能な厳格モード |
| **GOVERNANCE Mode** | 特定権限で削除可能なモード（今回不使用） |
| **Versioning** | S3のバージョン管理機能、削除マーカー作成 |
| **Lifecycle Policy** | S3のストレージクラス自動移行ルール |

### C. 変更履歴

| バージョン | 日付 | 変更内容 | 作成者 |
|----------|------|---------|--------|
| 1.0 | 2025-11-07 | 初版作成（Phase 11-B要件定義） | system-admin |
| 1.1 | 2025-11-07 | Weekly→Daily変更、マルウェアスキャン追加、EC2不要理由明記 | system-admin |
| 1.2 | 2025-11-07 | レビュー反映: ビジネス要件・NFR修正、スクリプト役割明確化 | system-admin |
| 1.3 | 2025-11-07 | FR-08コスト監視を2段階閾値に修正（10円WARNING + 100円CRITICAL） | system-admin |

---

**END OF DOCUMENT**
