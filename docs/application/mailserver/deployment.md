# メールサーバーデプロイメント戦略

**技術スタック**: Docker Compose, Terraform, Cloudflare

---

## 1. デプロイメント方針

### 1.1 Infrastructure as Code（IaC）

| レイヤー | ツール | 管理対象 |
|---------|-------|---------|
| クラウドリソース | Terraform | S3, IAM, CloudWatch, SNS |
| コンテナ定義 | Docker Compose | 9サービスコンテナ |
| 設定管理 | Git + 環境変数 | 設定ファイル、.env |
| エッジサービス | Cloudflare Dashboard | Tunnel, Email Routing, DNS |

**原則**:
- すべてのインフラ変更はコードとしてバージョン管理
- 手動変更は禁止（緊急時を除く）
- 変更は必ずレビュー後に適用

### 1.2 ディレクトリ構成

```
services/mailserver/
├── docker-compose.yml      # コンテナ定義
├── .env                    # 環境変数（Git管理外）
├── .env.example            # 環境変数テンプレート
├── config/                 # 設定ファイル
│   ├── postfix/
│   ├── dovecot/
│   ├── nginx/
│   ├── roundcube/
│   ├── rspamd/
│   └── clamav/
├── scripts/                # 運用スクリプト
│   ├── backup-mailserver.sh
│   ├── restore-mailserver.sh
│   ├── sync-to-s3.sh
│   └── scan-before-restore.sh
├── terraform/              # IaC
│   └── s3-backup/
├── usermgmt/               # ユーザー管理アプリ
└── mailserver-api/         # メール受信API
```

---

## 2. Docker Compose 戦略

### 2.1 サービス構成（9コンテナ）

| サービス | イメージ | 役割 | リソース制限 |
|---------|---------|------|-------------|
| postfix | boky/postfix:latest | SMTP送信 | CPU: 1.0, MEM: 512M |
| dovecot | dovecot/dovecot:2.3.21 | IMAP/LMTP | CPU: 1.0, MEM: 1G |
| mariadb | mariadb:10.11.7 | データベース | CPU: 1.0, MEM: 1G |
| rspamd | rspamd/rspamd:3.8 | スパムフィルタ | CPU: 1.0, MEM: 1G |
| clamav | clamav/clamav:1.3 | ウイルススキャン | CPU: 1.0, MEM: 2G |
| roundcube | roundcube/roundcubemail:1.6.7 | Webメール | CPU: 0.5, MEM: 512M |
| mailserver-api | カスタムビルド | メール受信API | CPU: 0.5, MEM: 256M |
| usermgmt | カスタムビルド | ユーザー管理 | CPU: 0.5, MEM: 512M |
| nginx | nginx:1.26-alpine | リバースプロキシ | CPU: 0.5, MEM: 256M |

### 2.2 ボリューム戦略

```yaml
volumes:
  # パフォーマンス重視: SSD
  db_data:
    driver: local
    driver_opts:
      type: none
      o: bind
      device: /path/to/ssd/mariadb

  # 容量重視: HDD
  mail_data:
    driver: local
    driver_opts:
      type: none
      o: bind
      device: /mnt/backup-hdd/mailserver/mailboxes
```

**設計意図**:
- **SSD**: データベース、ログ（頻繁なI/O）
- **HDD**: メールボックス、バックアップ（大容量）

### 2.3 ネットワーク戦略

```yaml
networks:
  mailserver_network:
    driver: bridge
```

**設計意図**:
- 独立したネットワークセグメント
- 他サービス（Blog等）との分離
- コンテナ間通信の制御

### 2.4 ヘルスチェック設計

```yaml
healthcheck:
  test: ["CMD", "curl", "-f", "http://localhost/health"]
  interval: 30s      # 30秒ごとにチェック
  timeout: 10s       # 10秒でタイムアウト
  retries: 3         # 3回失敗で unhealthy
  start_period: 40s  # 起動後40秒は猶予
```

**サービス別ヘルスチェック**:

| サービス | チェック方法 | 理由 |
|---------|------------|------|
| Postfix | SMTP接続確認 | ポート応答確認 |
| Dovecot | サービスステータス確認 | プロセス状態確認 |
| MariaDB | `mysqladmin ping` | DB接続確認 |
| Nginx | HTTP応答確認 | Web応答確認 |
| ClamAV | スキャン実行テスト | スキャン機能確認 |

---

## 3. Terraform 戦略（S3バックアップ）

### 3.1 モジュール構成

```
terraform/s3-backup/
├── main.tf           # メインリソース定義
├── variables.tf      # 変数定義
├── outputs.tf        # 出力定義
├── terraform.tfvars  # 変数値（Git管理外）
└── provider.tf       # AWS プロバイダー設定
```

### 3.2 リソース構成

| リソース | 用途 |
|---------|------|
| S3 Bucket | バックアップ保存 |
| S3 Object Lock | COMPLIANCE モード（削除不可） |
| IAM User | バックアップ専用ユーザー |
| IAM Policy | 最小権限（PutObject, GetObject） |
| CloudWatch Alarm | コスト監視 |
| SNS Topic | アラート通知 |

### 3.3 State管理

```hcl
terraform {
  backend "s3" {
    bucket         = "terraform-state-bucket"
    key            = "mailserver/s3-backup/terraform.tfstate"
    region         = "ap-northeast-1"
    encrypt        = true
    dynamodb_table = "terraform-state-lock"
  }
}
```

### 3.4 タグ戦略

```hcl
locals {
  common_tags = {
    Project     = "mailserver-backup"
    Environment = var.environment
    ManagedBy   = "terraform"
    Owner       = "admin"
  }
}
```

---

## 4. デプロイメントワークフロー

### 4.1 初期デプロイ

```bash
# 1. 環境変数設定
cp .env.example .env
# .env を編集（パスワード、APIキー等）

# 2. ディレクトリ準備
mkdir -p /path/to/ssd/mariadb
mkdir -p /mnt/backup-hdd/mailserver/{mailboxes,daily,weekly}

# 3. 設定ファイル確認
docker compose config

# 4. イメージ取得・起動
docker compose pull
docker compose up -d

# 5. 起動確認
docker compose ps
docker compose logs --tail=50
```

### 4.2 通常デプロイ（更新）

```bash
# 1. 変更確認
git pull origin main
docker compose config  # 設定検証

# 2. イメージ更新
docker compose pull

# 3. ローリングアップデート
docker compose up -d --remove-orphans

# 4. ヘルスチェック
docker compose ps
docker compose logs --tail=50
```

### 4.3 設定変更デプロイ

```bash
# 1. 設定ファイル編集
vim config/postfix/main.cf

# 2. 設定検証
docker compose exec postfix postconf -n

# 3. サービス再起動
docker compose restart postfix

# 4. 動作確認
docker compose logs -f postfix
```

### 4.4 Terraformデプロイ

```bash
cd terraform/s3-backup

# 1. 計画確認
terraform plan -out=tfplan

# 2. レビュー
# ... 変更内容確認 ...

# 3. 適用
terraform apply tfplan

# 4. 出力確認
terraform output
```

### 4.5 デプロイ前チェックリスト

```
□ 設定ファイルの構文チェック（docker compose config）
□ 環境変数の確認（.env の必須項目）
□ ディスク空き容量の確認
□ 現在のサービス状態の記録（docker compose ps）
□ バックアップの確認（直近のバックアップが成功しているか）
□ ロールバック手順の確認
```

---

## 5. イメージ管理

### 5.1 バージョン固定

```yaml
# Good: バージョン固定
image: mariadb:10.11.7
image: nginx:1.26-alpine
image: dovecot/dovecot:2.3.21

# Bad: latest（本番では避ける）
image: nginx:latest
```

**理由**:
- 再現性確保
- 予期しないアップデート防止
- ロールバック容易化

### 5.2 カスタムイメージ

| イメージ | ベース | カスタマイズ内容 |
|---------|--------|-----------------|
| mailserver-api | python:3.11-slim | FastAPI、メール受信API |
| usermgmt | python:3.11-slim | Flask、ユーザー管理UI |

**ビルドポリシー**:
- ベースイメージは公式を使用
- カスタマイズは最小限
- セキュリティパッチ適用のため定期リビルド（月次）
- マルチステージビルドで最終イメージを軽量化

### 5.3 コンテナ起動順序

```
MariaDB → Dovecot → Postfix → Rspamd → ClamAV → Roundcube → mailserver-api → usermgmt → Nginx
```

**依存関係管理**:
- `depends_on` + `healthcheck` で起動順序を制御
- DBが ready になるまでアプリケーション起動を待機

---

## 6. 秘密情報管理

### 6.1 環境変数

```bash
# .env（本番）- Git管理外
MYSQL_ROOT_PASSWORD=<secure-password>
MYSQL_PASSWORD=<secure-password>
USERMGMT_DB_PASSWORD=<secure-password>
SENDGRID_API_KEY=<api-key>
MAILSERVER_API_TOKEN=<token>
```

### 6.2 .gitignore

```
.env
.env.*
!.env.example
*.key
*.pem
secrets/
terraform.tfvars
```

### 6.3 シークレットローテーション

| シークレット | ローテーション頻度 | 方法 |
|-------------|------------------|------|
| DBパスワード | 90日 | 手動更新 |
| APIキー（SendGrid） | 365日 | サービス側で再生成 |
| Mailserver API Token | 90日 | 手動更新 |
| AWS認証情報 | 90日 | IAM Access Key再生成 |

---

## 7. ロールバック戦略

### 7.1 Dockerロールバック

```bash
# 直前のイメージに戻す
docker compose down
git checkout HEAD~1 -- docker-compose.yml
docker compose up -d

# 特定バージョンに戻す
docker compose down
docker compose pull  # 指定バージョンのイメージ
docker compose up -d
```

### 7.2 設定ロールバック

```bash
# Git から復元
git checkout HEAD~1 -- config/postfix/main.cf
docker compose restart postfix
```

### 7.3 Terraformロールバック

```bash
# 直前のStateに戻す
terraform plan -target=<resource> -destroy
terraform apply

# または
git revert <commit>
terraform apply
```

### 7.4 データロールバック

```bash
# バックアップからリストア
./scripts/restore-mailserver.sh \
  --from /mnt/backup-hdd/mailserver/daily/YYYY-MM-DD \
  --component all
```

---

## 8. Cloudflare設定

### 8.1 Email Routing設定

| 設定項目 | 値 |
|---------|-----|
| MXレコード | route1.mx.cloudflare.net（優先度10） |
| Catch-all | Email Worker転送 |
| SPF | `v=spf1 include:_spf.mx.cloudflare.net ~all` |

### 8.2 Tunnel設定

| ホスト名 | サービス | 用途 |
|---------|---------|------|
| mail.example.com | http://nginx:80 | Webメール |
| mail-api.example.com | http://mailserver-api:8000 | メール受信API |

### 8.3 DNS設定

| タイプ | 名前 | 値 | 用途 |
|--------|------|-----|------|
| MX | @ | route1.mx.cloudflare.net | メール受信 |
| TXT | @ | v=spf1 ... | SPF |
| TXT | _dmarc | v=DMARC1; ... | DMARC |
| TXT | selector._domainkey | v=DKIM1; ... | DKIM |
| CNAME | mail | tunnel-id.cfargotunnel.com | Webメール |

---

## 9. 継続的改善

### 9.1 イメージ更新チェック

```bash
# 月次: セキュリティアップデート確認
docker images --format "{{.Repository}}:{{.Tag}}" | while read img; do
  docker pull $img
done

# 変更があれば再起動
docker compose up -d
```

### 9.2 依存関係監査

- **Dockerfile**: ベースイメージの脆弱性スキャン
- **Terraform**: プロバイダーバージョン確認
- **Python依存**: pip-audit による脆弱性チェック
- **設定ファイル**: ベストプラクティス準拠確認

---

## 10. 関連ドキュメント

| ドキュメント | 内容 |
|------------|------|
| [requirements.md](requirements.md) | 要件定義・トレードオフ分析 |
| [architecture.md](architecture.md) | システムアーキテクチャ・コンポーネント設計 |
| [operations.md](operations.md) | 運用設計・監視・バックアップ運用 |
