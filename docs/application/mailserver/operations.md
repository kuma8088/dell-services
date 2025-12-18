# メールサーバー運用設計

**作成者**: kuma8088（AWS認定ソリューションアーキテクト、ITストラテジスト）
**技術スタック**: Docker Compose, AWS S3, ClamAV

---

## 1. 運用方針

### 1.1 運用原則

| 原則 | 内容 |
|------|------|
| 自動化優先 | 定型作業はスクリプト化・cron化 |
| 監視と通知 | 異常検知→即時通知→対応 |
| ドキュメント化 | 手順書整備、変更履歴記録 |
| 最小権限 | 運用に必要な権限のみ付与 |

### 1.2 運用担当範囲

| カテゴリ | 担当 | 頻度 |
|---------|------|------|
| 日常監視 | 自動（cron） | 毎日 |
| バックアップ | 自動（cron） | 毎日 |
| セキュリティ更新 | 手動 | 月次 |
| 障害対応 | 手動 | 随時 |

---

## 2. 監視設計

### 2.1 監視項目

| カテゴリ | 監視項目 | 閾値 | 通知 |
|---------|---------|------|------|
| リソース | CPU使用率 | 80%以上 | 警告 |
| リソース | メモリ使用率 | 80%以上 | 警告 |
| リソース | ディスク使用率 | 70%以上 | 警告 |
| サービス | コンテナ状態 | unhealthy | 緊急 |
| サービス | メール送受信 | 失敗 | 緊急 |
| セキュリティ | マルウェア検出 | 1件以上 | 緊急 |
| コスト | S3料金 | $5以上 | 警告 |

### 2.2 ヘルスチェック

```bash
# コンテナ状態確認
docker compose ps

# サービス別確認
docker compose exec postfix postconf -n | grep -E "^myhostname|^mydomain"
docker compose exec dovecot doveadm log find
docker compose exec mariadb mysqladmin -u root ping
```

### 2.3 ログ監視

| ログ | パス | 確認ポイント |
|------|------|-------------|
| Postfix | docker logs mailserver-postfix | 送信エラー、認証失敗 |
| Dovecot | docker logs mailserver-dovecot | 認証エラー、LMTP失敗 |
| mailserver-api | docker logs mailserver-api | 受信エラー |
| バックアップ | ~/.mailserver-backup.log | バックアップ成否 |
| S3同期 | ~/.s3-backup-cron.log | 同期成否 |

---

## 3. バックアップ運用

### 3.1 自動バックアップスケジュール

| 種別 | cron設定 | 実行時間 |
|------|---------|----------|
| 日次バックアップ | `0 3 * * *` | AM 3:00 |
| 週次バックアップ | `0 2 * * 0` | 日曜 AM 2:00 |
| S3同期 | `0 4 * * *` | AM 4:00 |
| マルウェアスキャン | `0 5 * * *` | AM 5:00 |

### 3.2 バックアップ確認

```bash
# 日次バックアップ確認
ls -lah /mnt/backup-hdd/mailserver/daily/
tail -50 ~/.mailserver-backup.log

# S3同期確認
tail -50 ~/.s3-backup-cron.log
aws s3 ls s3://bucket-name/mailserver/ --profile mailserver-backup

# スキャン結果確認
tail -50 ~/.scan-cron.log
```

### 3.3 手動バックアップ

```bash
cd /opt/onprem-infra-system/project-root-infra/services/mailserver

# 全コンポーネントバックアップ
./scripts/backup-mailserver.sh

# 特定コンポーネントのみ
./scripts/backup-mailserver.sh --component mysql
./scripts/backup-mailserver.sh --component mailboxes
```

### 3.4 バックアップ検証（月次）

```bash
# Dry-runでリストア検証
./scripts/restore-mailserver.sh \
  --from /mnt/backup-hdd/mailserver/daily/$(date +%Y-%m-%d) \
  --dry-run

# チェックサム検証
cd /mnt/backup-hdd/mailserver/daily/$(date +%Y-%m-%d)
sha256sum -c checksums.sha256
```

---

## 4. リストア手順

### 4.1 リストア前チェック

```bash
# 1. バックアップの存在確認
ls -la /mnt/backup-hdd/mailserver/daily/

# 2. チェックサム検証
cd /mnt/backup-hdd/mailserver/daily/YYYY-MM-DD
sha256sum -c checksums.sha256

# 3. マルウェアスキャン
./scripts/scan-before-restore.sh /mnt/backup-hdd/mailserver/daily/YYYY-MM-DD
```

### 4.2 リストア実行

```bash
cd /opt/onprem-infra-system/project-root-infra/services/mailserver

# Dry-run（事前確認）
./scripts/restore-mailserver.sh \
  --from /mnt/backup-hdd/mailserver/daily/YYYY-MM-DD \
  --dry-run

# 全コンポーネントリストア
./scripts/restore-mailserver.sh \
  --from /mnt/backup-hdd/mailserver/daily/YYYY-MM-DD \
  --component all

# 特定コンポーネントのみ
./scripts/restore-mailserver.sh \
  --from /mnt/backup-hdd/mailserver/daily/YYYY-MM-DD \
  --component mysql
```

### 4.3 S3からのリストア

```bash
# S3からダウンロード
aws s3 sync s3://bucket-name/mailserver/daily/YYYY-MM-DD \
  /tmp/restore-from-s3/ \
  --profile mailserver-backup

# マルウェアスキャン
./scripts/scan-before-restore.sh /tmp/restore-from-s3/

# リストア実行
./scripts/restore-mailserver.sh \
  --from /tmp/restore-from-s3 \
  --component all
```

### 4.4 リストア後確認

```bash
# サービス起動確認
docker compose ps
docker compose logs --tail=50

# メール送受信テスト
# 1. Webメールにログイン
# 2. テストメール送信
# 3. 受信確認
```

---

## 5. 障害対応

### 5.1 障害レベル定義

| レベル | 定義 | 目標復旧時間 | 例 |
|--------|------|-------------|-----|
| Critical | サービス完全停止 | 1時間 | 全コンテナ停止 |
| High | 主要機能停止 | 2時間 | メール送受信不可 |
| Medium | 一部機能停止 | 4時間 | Webメールのみ不可 |
| Low | 軽微な問題 | 24時間 | ログエラー |

### 5.2 障害対応フロー

```
障害検知
    │
    ▼
┌─────────────────────┐
│ 1. 影響範囲確認     │
│    docker compose ps │
└─────────────────────┘
    │
    ▼
┌─────────────────────┐
│ 2. ログ確認         │
│    docker logs ...  │
└─────────────────────┘
    │
    ▼
┌─────────────────────┐
│ 3. 原因特定         │
│    設定/リソース/外部│
└─────────────────────┘
    │
    ├── 設定問題 → 設定修正 → 再起動
    ├── リソース問題 → リソース解放
    └── 外部問題 → 連携先確認
    │
    ▼
┌─────────────────────┐
│ 4. 復旧確認         │
│    動作テスト       │
└─────────────────────┘
    │
    ▼
┌─────────────────────┐
│ 5. 事後対応         │
│    原因分析/再発防止│
└─────────────────────┘
```

### 5.3 よくある障害と対処

#### メール受信できない
```bash
# 1. mailserver-api確認
docker compose logs -f mailserver-api

# 2. Dovecot LMTP確認
docker compose exec dovecot doveadm log find

# 3. Cloudflare Email Worker確認
# Cloudflare Dashboard → Email → Email Routing → Logs
```

#### メール送信できない
```bash
# 1. Postfixログ確認
docker compose logs -f postfix

# 2. SendGrid接続確認
docker compose exec postfix postconf -n | grep relayhost

# 3. SendGrid Dashboard確認
# Activity → 送信履歴
```

#### 認証失敗
```bash
# 1. Dovecotログ確認
docker compose logs dovecot | grep -i auth

# 2. ユーザー存在確認
docker compose exec mariadb mysql -u root -p \
  -e "SELECT email FROM usermgmt.users;"

# 3. パスワードリセット
# usermgmt Web UI → ユーザー編集
```

#### コンテナ起動失敗
```bash
# 1. 状態確認
docker compose ps

# 2. エラーログ確認
docker compose logs <service-name>

# 3. 設定検証
docker compose config

# 4. 再起動
docker compose down
docker compose up -d
```

---

## 6. ユーザー管理

### 6.1 Web UI操作

| 操作 | URL | 手順 |
|------|-----|------|
| ログイン | http://localhost:5000 | usermgmt UIにアクセス |
| ユーザー追加 | /users/new | フォーム入力→保存 |
| パスワード変更 | /users/{id}/edit | 編集画面→パスワード更新 |
| ユーザー削除 | /users/{id}/delete | 削除確認→実行 |

### 6.2 REST API操作

```bash
# ユーザー一覧取得
curl http://localhost:5000/api/users

# ユーザー追加
curl -X POST http://localhost:5000/api/users \
  -H "Content-Type: application/json" \
  -d '{"email": "user@example.com", "password": "secure-password"}'

# ユーザー削除
curl -X DELETE http://localhost:5000/api/users/{id}
```

### 6.3 ドメイン管理

```bash
# ドメイン一覧
curl http://localhost:5000/api/domains

# ドメイン追加
curl -X POST http://localhost:5000/api/domains \
  -H "Content-Type: application/json" \
  -d '{"name": "newdomain.com"}'
```

---

## 7. 定期メンテナンス

### 7.1 日次タスク

| タスク | 確認方法 |
|--------|---------|
| バックアップ成功確認 | `tail ~/.mailserver-backup.log` |
| S3同期確認 | `tail ~/.s3-backup-cron.log` |
| スキャン結果確認 | `tail ~/.scan-cron.log` |
| コンテナ状態確認 | `docker compose ps` |

### 7.2 週次タスク

| タスク | 確認方法 |
|--------|---------|
| 週次バックアップ確認 | `ls /mnt/backup-hdd/mailserver/weekly/` |
| ディスク使用量確認 | `df -h` |
| ログローテーション確認 | ログファイルサイズ確認 |

### 7.3 月次タスク

| タスク | 手順 |
|--------|------|
| バックアップリストアテスト | Dry-runでリストア検証 |
| セキュリティ更新 | Dockerイメージ更新 |
| SSL証明書確認 | 有効期限確認（Cloudflare自動更新） |
| コスト確認 | AWS Cost Explorer確認 |

### 7.4 年次タスク

| タスク | 手順 |
|--------|------|
| DR訓練 | 完全リストア訓練 |
| セキュリティ監査 | 設定・権限見直し |
| キャパシティ計画 | ストレージ・リソース見直し |

---

## 8. セキュリティ運用

### 8.1 マルウェアスキャン

```bash
# 手動スキャン
./scripts/scan-before-restore.sh /path/to/scan

# スキャン結果確認
tail -50 ~/.scan-cron.log

# ClamAV定義更新確認
docker compose exec clamav freshclam --version
```

### 8.2 認証情報ローテーション

| 対象 | 頻度 | 手順 |
|------|------|------|
| DBパスワード | 90日 | .env更新→コンテナ再起動 |
| APIトークン | 90日 | .env更新→コンテナ再起動 |
| AWS認証情報 | 90日 | IAM Access Key再生成 |

### 8.3 アクセスログ確認

```bash
# Nginx アクセスログ
docker compose logs nginx | grep -E "POST|DELETE"

# 認証失敗ログ
docker compose logs dovecot | grep -i "auth failed"

# 不審なアクセス確認
docker compose logs nginx | grep -E "4[0-9]{2}|5[0-9]{2}"
```

---

## 9. 運用スクリプト一覧

| スクリプト | 用途 | 実行例 |
|-----------|------|--------|
| backup-mailserver.sh | バックアップ実行 | `./scripts/backup-mailserver.sh` |
| restore-mailserver.sh | リストア実行 | `./scripts/restore-mailserver.sh --from ... --component all` |
| sync-to-s3.sh | S3同期 | `./scripts/sync-to-s3.sh` |
| scan-before-restore.sh | マルウェアスキャン | `./scripts/scan-before-restore.sh /path` |

---

## 10. 運用チェックリスト

### 10.1 障害発生時

```
□ 影響範囲の確認
□ ログの確認
□ 原因の特定
□ 対処の実施
□ 復旧の確認
□ 関係者への報告
□ 事後分析・再発防止策
```

### 10.2 デプロイ時

```
□ バックアップの確認
□ 変更内容のレビュー
□ ロールバック手順の確認
□ デプロイの実行
□ 動作確認
□ ログ確認
```

### 10.3 月次メンテナンス

```
□ バックアップリストアテスト
□ セキュリティ更新確認
□ ディスク使用量確認
□ S3コスト確認
□ ログ・アラート確認
□ ドキュメント更新
```

---

## 11. 関連ドキュメント

| ドキュメント | 内容 |
|------------|------|
| [requirements.md](requirements.md) | 要件定義・トレードオフ分析 |
| [architecture.md](architecture.md) | システムアーキテクチャ・コンポーネント設計 |
| [deployment.md](deployment.md) | デプロイ戦略・Docker Compose設定 |
