# メールサーバーバックアップシステム要件定義書

**作成日**: 2025-11-07
**バージョン**: 1.0
**対象システム**: Dell Mailserver (Docker Compose 環境)

---

## 📋 目次

1. [プロジェクト概要](#1-プロジェクト概要)
2. [背景と目的](#2-背景と目的)
3. [バックアップ対象](#3-バックアップ対象)
4. [機能要件](#4-機能要件)
5. [非機能要件](#5-非機能要件)
6. [リカバリー要件](#6-リカバリー要件)
7. [運用要件](#7-運用要件)
8. [セキュリティ要件](#8-セキュリティ要件)
9. [システム構成](#9-システム構成)
10. [リスク管理](#10-リスク管理)

---

## 1. プロジェクト概要

### 1.1 プロジェクト名
**Dell Mailserver バックアップ・リカバリーシステム**

### 1.2 目的
- 重要なメールデータとシステム設定の定期的なバックアップ
- 障害発生時の迅速なリカバリー
- データ損失リスクの最小化

### 1.3 スコープ
- Dell 環境の Mailserver データ全体
- Docker Compose 構成ファイル
- SSL証明書とDKIM鍵
- データベース（MySQL）
- メールボックス（Dovecot）
- システム設定ファイル

---

## 2. 背景と目的

### 2.1 背景
- 現在、バックアップの仕組みが未整備
- ハードウェア障害・誤操作によるデータ損失リスクが存在
- 外付けHDD（3.6TB）がバックアップ先として利用可能

### 2.2 ビジネス要件
| 要件 | 説明 |
|-----|------|
| **データ保護** | メールデータと設定の完全な保護 |
| **迅速なリカバリー** | 障害発生時に24時間以内に復旧 |
| **運用負荷削減** | 自動バックアップによる手動作業の削減 |
| **コンプライアンス** | メールデータの保持義務への対応 |

### 2.3 成功基準
- ✅ 日次バックアップが自動実行される
- ✅ バックアップからのリカバリーが30分以内に完了
- ✅ バックアップデータの整合性が100%保証される
- ✅ 過去30日分のバックアップが保持される

---

## 3. バックアップ対象

### 3.1 データ分類

| カテゴリ | 対象 | 優先度 | サイズ目安 |
|---------|------|--------|-----------|
| **メールデータ** | `/opt/onprem-infra-system/project-root-infra/services/mailserver/data/mail/` | 🔴 P0 | 可変（数GB～） |
| **データベース** | MySQL (usermgmt, roundcube) | 🔴 P0 | 数MB～数百MB |
| **SSL証明書** | Let's Encrypt証明書 + 秘密鍵 | 🟡 P1 | 数KB |
| **DKIM鍵** | OpenDKIM秘密鍵・公開鍵 | 🟡 P1 | 数KB |
| **設定ファイル** | Docker Compose, Postfix, Dovecot設定 | 🟡 P1 | 数MB |
| **ログファイル** | アプリケーションログ | 🟢 P2 | 可変（数GB） |
| **スクリプト** | 運用スクリプト | 🟢 P2 | 数KB～数MB |

### 3.2 詳細バックアップ対象

#### 3.2.1 メールデータ（P0）
```
/opt/onprem-infra-system/project-root-infra/services/mailserver/data/mail/
├── vmail/                    # 全ユーザーのメールボックス
│   ├── example.com/
│   │   ├── user1@example.com/
│   │   └── user2@example.com/
│   └── otherdomain.com/
└── sieve/                    # メールフィルタリングスクリプト
```

**バックアップ方法**: rsync による増分バックアップ

#### 3.2.2 データベース（P0）
```bash
# usermgmt データベース（ユーザー管理）
docker exec mailserver-mariadb mysqldump -u root -p usermgmt

# roundcubemail データベース（Webメール設定）
docker exec mailserver-mariadb mysqldump -u root -p roundcubemail
```

**バックアップ方法**: mysqldump による論理バックアップ（gzip圧縮）

#### 3.2.3 SSL証明書（P1）
```
/opt/onprem-infra-system/project-root-infra/services/mailserver/data/certbot/
├── live/
│   └── mail.example.com/
│       ├── fullchain.pem
│       ├── privkey.pem
│       └── chain.pem
└── renewal/
    └── mail.example.com.conf
```

#### 3.2.4 DKIM鍵（P1）
```
/opt/onprem-infra-system/project-root-infra/services/mailserver/config/opendkim/
├── keys/
│   └── mail.example.com/
│       ├── default.private
│       └── default.txt
└── KeyTable
```

#### 3.2.5 設定ファイル（P1）
```
/opt/onprem-infra-system/project-root-infra/services/mailserver/
├── docker-compose.yml
├── .env
├── config/
│   ├── postfix/
│   │   ├── main.cf
│   │   ├── master.cf
│   │   └── virtual_mailbox_maps
│   ├── dovecot/
│   │   ├── dovecot.conf
│   │   ├── dovecot-sql.conf.ext
│   │   └── users
│   ├── rspamd/
│   └── clamav/
└── scripts/
```

#### 3.2.6 ログファイル（P2）
```
/opt/onprem-infra-system/project-root-infra/services/mailserver/logs/
├── postfix/
├── dovecot/
├── rspamd/
└── mysql/
```

---

## 4. 機能要件

### 4.1 自動バックアップ

**FR-01: 日次バックアップの自動実行**
- バックアップスクリプトを cron で毎日午前3時に実行
- バックアップ処理中はメールサービスへの影響を最小化
- バックアップ完了後、成功/失敗を通知

**FR-02: 増分バックアップ**
- メールデータは rsync で増分バックアップ（差分のみコピー）
- データベースは完全バックアップ（mysqldump）
- 設定ファイルは完全バックアップ

**FR-03: バックアップ先**
- 外付けHDD: `/mnt/backup-hdd/mailserver/`
- バックアップ形式:
  ```
  /mnt/backup-hdd/mailserver/
  ├── daily/
  │   ├── 2025-11-07/
  │   │   ├── mail/
  │   │   ├── mysql/
  │   │   ├── config/
  │   │   ├── ssl/
  │   │   └── backup.log
  │   └── 2025-11-08/
  └── latest -> daily/2025-11-08/
  ```

### 4.2 保存期間とローテーション

**FR-04: バックアップ保存期間**
| データ種別 | 保存期間 | 理由 |
|-----------|---------|------|
| 日次バックアップ | 30日間 | 月次レベルの復旧に対応 |
| 週次バックアップ | 12週間（3ヶ月） | 四半期レベルの復旧に対応 |

**FR-05: 自動削除**
- 保存期間を超えたバックアップは自動削除
- 削除前にバックアップ整合性を検証

### 4.3 検証とモニタリング

**FR-06: バックアップ整合性検証**
- rsync: チェックサムによるファイル整合性確認
- MySQL: ダンプファイルの gzip 整合性確認
- バックアップ完了後、ファイルサイズと件数を記録

**FR-07: 監視とアラート**
- バックアップ失敗時、管理者にメール通知
- ディスク容量が80%を超えた場合、警告通知
- バックアップログを保持（30日間）

---

## 5. 非機能要件

### 5.1 パフォーマンス要件

**NFR-01: バックアップ時間**
- 通常のバックアップ: 30分以内に完了
- 初回フルバックアップ: 2時間以内

**NFR-02: システム影響**
- バックアップ中のCPU使用率: 30%以下
- バックアップ中のI/O負荷: nice値で優先度を下げる

### 5.2 信頼性要件

**NFR-03: バックアップ成功率**
- 目標成功率: 99%以上
- 失敗時は自動リトライ（最大3回）

**NFR-04: データ整合性**
- バックアップデータの整合性: 100%保証
- MySQL: トランザクション一貫性を維持（--single-transaction）

### 5.3 容量要件

**NFR-05: ストレージ容量**
- 外付けHDD: 3.6TB（現在使用率1%）
- 想定容量計画:
  - メールデータ: 最大500GB
  - データベース: 最大10GB
  - 設定・ログ: 最大50GB
  - 合計: 約560GB（30日分保持可能）

---

## 6. リカバリー要件

### 6.1 リカバリー目標

**RR-01: RTO（Recovery Time Objective）**
- 目標復旧時間: **24時間以内**
- 重要データ（メール・DB）: **4時間以内**

**RR-02: RPO（Recovery Point Objective）**
- 目標復旧時点: **24時間以内**（日次バックアップ）
- データ損失許容範囲: 最大1日分

### 6.2 リカバリーシナリオ

**RR-03: 完全リカバリー**
障害種別: ハードウェア故障、ディスク破損

手順:
1. 新しいハードウェアに Rocky Linux 9.6 をインストール
2. Docker と Docker Compose をインストール
3. バックアップから設定ファイルをリストア
4. バックアップからメールデータをリストア
5. バックアップからデータベースをリストア
6. Docker Compose でサービス起動
7. 動作確認

**RR-04: 部分リカバリー**
障害種別: 誤削除、データ破損

手順:
1. 影響範囲を特定
2. 該当データのみバックアップから復旧
3. サービス再起動
4. 動作確認

**RR-05: データベースリカバリー**
```bash
# MySQL リストア例
docker exec -i mailserver-mariadb mysql -u root -p usermgmt < /mnt/backup-hdd/mailserver/latest/mysql/usermgmt.sql
```

**RR-06: メールデータリカバリー**
```bash
# rsync によるリストア例
rsync -avz /mnt/backup-hdd/mailserver/latest/mail/ /opt/onprem-infra-system/project-root-infra/services/mailserver/data/mail/
```

---

## 7. 運用要件

### 7.1 バックアップスクリプト

**OR-01: バックアップスクリプトの配置**
```
/opt/onprem-infra-system/project-root-infra/services/mailserver/scripts/
└── backup-mailserver.sh
```

**OR-02: cron 設定**
```bash
# 毎日午前3時にバックアップ実行
0 3 * * * /opt/onprem-infra-system/project-root-infra/services/mailserver/scripts/backup-mailserver.sh >> ~/.mailserver-backup.log 2>&1
```

### 7.2 監視とログ

**OR-03: バックアップログ**
- ログ保存先: `~/.mailserver-backup.log`
- ログローテーション: 30日間保持
- ログ内容: 開始時刻、終了時刻、バックアップサイズ、エラー情報

**OR-04: 通知設定**
- 成功時: ログのみ記録
- 失敗時: 管理者にメール通知
- ディスク容量警告: 80%超過時にメール通知

### 7.3 テストとメンテナンス

**OR-05: リカバリーテスト**
- 頻度: 四半期ごと（3ヶ月に1回）
- 内容: 実際のバックアップからテスト環境へリストア
- 検証: メール送受信、Webメールアクセス、ユーザー管理機能

**OR-06: バックアップメンテナンス**
- 外付けHDDの健康状態チェック（月次）
- バックアップログの確認（週次）
- ディスク容量の確認（日次、自動）

---

## 8. セキュリティ要件

### 8.1 アクセス制御

**SR-01: バックアップデータのアクセス権限**
```bash
# バックアップディレクトリのパーミッション
chmod 700 /mnt/backup-hdd/mailserver/
chown system-admin:system-admin /mnt/backup-hdd/mailserver/
```

**SR-02: バックアップスクリプトの保護**
```bash
chmod 750 /opt/onprem-infra-system/project-root-infra/services/mailserver/scripts/backup-mailserver.sh
```

### 8.2 データ保護

**SR-03: バックアップデータの暗号化**
- フェーズ1（MVP）: ファイルシステムレベルの保護（パーミッション）
- フェーズ2（将来）: GPG暗号化の検討

**SR-04: MySQL認証情報の保護**
- `.my.cnf` によるパスワード管理
- バックアップスクリプト内に平文パスワードを記載しない

---

## 9. システム構成

### 9.1 外付けHDD構成

**ハードウェア情報**:
```bash
Filesystem      Size  Used Avail Use% Mounted on
/dev/sda1       3.6T   34G  3.4T   1% /mnt/backup-hdd
```

**マウント設定** (`/etc/fstab`):
```
UUID=xxxxxxxx-xxxx-xxxx-xxxx-xxxxxxxxxxxx  /mnt/backup-hdd  ext4  defaults,nofail  0  2
```

### 9.2 バックアップスケジュール

**日次バックアップ**:
- 実行時刻: 毎日午前3時
- 対象: 全データ（メール、DB、設定、SSL、DKIM）
- 保存期間: 30日間

**週次バックアップ**:
- 実行時刻: 毎週日曜日午前4時
- 対象: 全データ
- 保存期間: 12週間（3ヶ月）

### 9.3 必要なツール

```bash
# バックアップに必要なパッケージ
sudo dnf install -y rsync gzip coreutils findutils
```

---

## 10. リスク管理

### 10.1 リスク分析

| リスク | 影響度 | 発生確率 | 対策 |
|-------|--------|---------|------|
| **外付けHDD故障** | 🔴 高 | 🟡 中 | SMART監視、定期交換 |
| **バックアップ失敗** | 🔴 高 | 🟢 低 | 自動リトライ、アラート |
| **ディスク容量不足** | 🟡 中 | 🟢 低 | 監視、自動削除 |
| **バックアップデータ破損** | 🔴 高 | 🟢 低 | 整合性検証、チェックサム |
| **リカバリー手順の誤り** | 🟡 中 | 🟡 中 | 定期的なリカバリーテスト |

### 10.2 対策計画

**RM-01: 外付けHDD障害対策**
- SMART情報の定期チェック（月次）
- 異常検知時の早期交換
- 将来的なクラウドバックアップ（AWS S3）の検討

**RM-02: バックアップ失敗対策**
- 自動リトライ機能（最大3回）
- 失敗時の即座のアラート通知
- バックアップログの定期確認

**RM-03: リカバリーテスト**
- 四半期ごとにテスト環境でリカバリー実施
- リカバリー手順書の定期更新
- リカバリー所要時間の測定と記録

---

## 📝 付録

### A. 関連ドキュメント

- [Mailserver README](../README.md)
- [Mailserver Troubleshooting](../../../services/mailserver/troubleshoot/README.md)
- [Infrastructure Documentation](../../infra/README.md)

### B. 用語集

| 用語 | 説明 |
|-----|------|
| **RTO** | Recovery Time Objective - 目標復旧時間 |
| **RPO** | Recovery Point Objective - 目標復旧時点 |
| **rsync** | 増分バックアップツール |
| **mysqldump** | MySQL論理バックアップツール |
| **SMART** | ディスク健康状態監視技術 |

### C. 変更履歴

| バージョン | 日付 | 変更内容 | 作成者 |
|----------|------|---------|--------|
| 1.0 | 2025-11-07 | 初版作成 | system-admin |
| 1.1 | 2025-11-07 | コンテナ名修正 (mailserver-mysql → mailserver-mariadb) | system-admin |

---

**END OF DOCUMENT**
