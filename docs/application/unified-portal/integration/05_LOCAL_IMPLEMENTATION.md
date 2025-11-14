# ローカル側実装ガイド

**プロジェクト**: Unified Portal - Mailserver統合 + DNS管理強化

**対象環境**: Dell WorkStation (Rocky Linux 9.6)

**前提**: Web側実装（04_WEB_IMPLEMENTATION.md）が完了していること

**作成日**: 2025-11-14

---

## 📋 概要

このガイドでは、Claude Code on the webで生成したコードをローカル環境（Dell WorkStation）で動作させるための手順を説明します。

**実行時間**: 約4-6時間

**実行場所**: `/opt/onprem-infra-system/project-root-infra/services/unified-portal`

---

## ⚠️ 重要な注意事項

### 既存システムへの影響
- Flask usermgmt（`services/mailserver/usermgmt`）は一切変更しません
- 並行稼働可能な設計のため、問題があればすぐにFlask usermgmtに戻せます
- データベースは共有しますが、テーブル構造は変更しません

### バックアップ必須
作業開始前に必ずバックアップを取得してください：

```bash
# データベースバックアップ
docker exec mailserver-mariadb-1 mysqldump \
  -u usermgmt -p<password> mailserver_usermgmt > \
  /mnt/backup-hdd/mailserver_usermgmt_pre-unified-portal_$(date +%Y%m%d_%H%M%S).sql

# 設定ファイルバックアップ
tar -czf /mnt/backup-hdd/unified-portal-backup_$(date +%Y%m%d_%H%M%S).tar.gz \
  /opt/onprem-infra-system/project-root-infra/services/unified-portal
```

---

## 🚀 Phase 1: 環境構築（所要時間: 約45分）

### Step 1: リポジトリ最新化（5分）

```bash
cd /opt/onprem-infra-system/project-root-infra

# 最新コードを取得（Web側で生成したコード）
git fetch origin
git pull origin claude/unified-portal-update-013A39eBWkgFoYTVLvM3V19t

# 確認
git log --oneline -5
git status
```

**検証**:
- `services/unified-portal/backend/app/models/mail_user.py` が存在
- `services/unified-portal/frontend/src/pages/MailUserManagement.tsx` が存在

---

### Step 2: バックエンド環境設定（15分）

#### 2.1 仮想環境確認
```bash
cd /opt/onprem-infra-system/project-root-infra/services/unified-portal/backend

# 仮想環境が存在するか確認
if [ -d "venv" ]; then
    echo "仮想環境が存在します"
else
    echo "仮想環境を作成します"
    python3 -m venv venv
fi

# 仮想環境アクティベート
source venv/bin/activate

# Python バージョン確認
python --version  # 3.9以上であること
```

#### 2.2 依存関係インストール
```bash
pip install --upgrade pip
pip install -r requirements.txt

# インストール確認
pip list | grep -E "fastapi|pymysql|passlib|sqlalchemy"
```

**期待出力**:
```
fastapi       0.104.1
pymysql       1.1.0
passlib       1.7.4
SQLAlchemy    2.0.23
```

#### 2.3 .env設定ファイル作成
```bash
# .env.exampleをコピー
cp .env.example .env

# Mailserver usermgmtのパスワード取得
USERMGMT_PASSWORD=$(grep USERMGMT_DB_PASSWORD /opt/onprem-infra-system/project-root-infra/services/mailserver/.env | cut -d '=' -f2)

# .envに追加
cat >> .env << EOF

# Mailserver Database
MAIL_DB_HOST=172.20.0.60
MAIL_DB_PORT=3306
MAIL_DB_NAME=mailserver_usermgmt
MAIL_DB_USER=usermgmt
MAIL_DB_PASSWORD=${USERMGMT_PASSWORD}
EOF

# 確認
cat .env | grep MAIL_DB
```

**期待出力**:
```
MAIL_DB_HOST=172.20.0.60
MAIL_DB_PORT=3306
MAIL_DB_NAME=mailserver_usermgmt
MAIL_DB_USER=usermgmt
MAIL_DB_PASSWORD=<actual_password>
```

---

### Step 3: データベース接続確認（10分）

#### 3.1 MariaDBコンテナ稼働確認
```bash
docker ps | grep mariadb
```

**期待出力**:
```
mailserver-mariadb-1  ... Up ... 172.20.0.60:3306
```

#### 3.2 Python スクリプトで接続テスト
```bash
cd /opt/onprem-infra-system/project-root-infra/services/unified-portal/backend
source venv/bin/activate

# 接続テストスクリプト作成
cat > test_db_connection.py << 'EOF'
#!/usr/bin/env python3
"""Database connection test script."""
import sys
from app.config import get_settings
from app.database import mail_engine
from sqlalchemy import text

settings = get_settings()

print(f"Connecting to: {settings.mail_db_host}:{settings.mail_db_port}/{settings.mail_db_name}")

try:
    with mail_engine.connect() as conn:
        # Test query
        result = conn.execute(text("SELECT COUNT(*) as count FROM users"))
        user_count = result.scalar()
        print(f"✅ Connection successful! Users count: {user_count}")

        result = conn.execute(text("SELECT COUNT(*) as count FROM domains"))
        domain_count = result.scalar()
        print(f"✅ Domains count: {domain_count}")

        result = conn.execute(text("SELECT COUNT(*) as count FROM audit_logs"))
        log_count = result.scalar()
        print(f"✅ Audit logs count: {log_count}")

except Exception as e:
    print(f"❌ Connection failed: {e}")
    sys.exit(1)

print("\n✅ All database checks passed!")
EOF

# 実行
python test_db_connection.py
```

**期待出力**:
```
Connecting to: 172.20.0.60:3306/mailserver_usermgmt
✅ Connection successful! Users count: 5
✅ Domains count: 3
✅ Audit logs count: 42
✅ All database checks passed!
```

**トラブルシューティング**:
- **エラー: "Can't connect to MySQL server"**: MariaDBコンテナが起動しているか確認
- **エラー: "Access denied"**: パスワードが正しいか確認（`.env` と `services/mailserver/.env`）
- **エラー: "Unknown database"**: データベース名が正しいか確認

---

### Step 4: バックエンド起動確認（10分）

```bash
cd /opt/onprem-infra-system/project-root-infra/services/unified-portal/backend
source venv/bin/activate

# 開発サーバー起動
python -m app.main
```

**期待出力**:
```
INFO:     Will watch for changes in these directories: ['/opt/onprem-infra-system/project-root-infra/services/unified-portal/backend']
INFO:     Uvicorn running on http://0.0.0.0:8000 (Press CTRL+C to quit)
INFO:     Started reloader process using StatReload
INFO:     Started server process
INFO:     Waiting for application startup.
INFO:     Starting Unified Portal v1.0.0
INFO:     Application startup complete.
```

**別ターミナルで確認**:
```bash
# ヘルスチェック
curl http://localhost:8000/health

# Swagger UI確認（ブラウザで開く）
xdg-open http://localhost:8000/docs

# Mailserver API確認
curl http://localhost:8000/api/v1/mailserver/users \
  -H "Authorization: Bearer <token>"
# （まだ認証トークンがないので401エラーが正常）
```

---

### Step 5: フロントエンド環境設定（5分）

```bash
cd /opt/onprem-infra-system/project-root-infra/services/unified-portal/frontend

# 依存関係インストール
npm install

# インストール確認
npm list --depth=0 | grep -E "react|vite|typescript"
```

**期待出力**:
```
├── react@18.2.0
├── react-dom@18.2.0
├── typescript@5.0.0
└── vite@5.0.0
```

---

### Step 6: フロントエンド起動確認（5分）

```bash
cd /opt/onprem-infra-system/project-root-infra/services/unified-portal/frontend

# 開発サーバー起動
npm run dev
```

**期待出力**:
```
VITE v5.0.0  ready in 1234 ms

  ➜  Local:   http://localhost:5173/
  ➜  Network: use --host to expose
  ➜  press h to show help
```

**ブラウザで確認**:
```bash
# ブラウザを開く
xdg-open http://localhost:5173
```

**検証項目**:
- [ ] ログイン画面が表示される
- [ ] サイドバーに「メール管理」メニューが表示される
- [ ] コンソールにエラーが出ていない

---

## 🧪 Phase 2: 機能テスト（所要時間: 約80分）

### Step 7: ユニットテスト実行（20分）

#### 7.1 バックエンドテスト
```bash
cd /opt/onprem-infra-system/project-root-infra/services/unified-portal/backend
source venv/bin/activate

# 全テスト実行
pytest tests/ -v --cov=app --cov-report=html --cov-report=term

# カバレッジレポート確認
xdg-open htmlcov/index.html
```

**期待出力**:
```
========================= test session starts ==========================
collected 25 items

tests/test_mailserver_router.py::test_list_users PASSED         [  4%]
tests/test_mailserver_router.py::test_create_user PASSED        [  8%]
...
tests/test_mail_user_service.py::test_hash_password PASSED      [100%]

---------- coverage: platform linux, python 3.9.18 ----------
Name                                    Stmts   Miss  Cover
-----------------------------------------------------------
app/models/mail_user.py                    25      0   100%
app/services/mail_user_service.py         120     15    88%
...
-----------------------------------------------------------
TOTAL                                     850    150    82%
========================= 25 passed in 10.52s ==========================
```

**最低基準**:
- 全テストがパス
- カバレッジ > 80%

#### 7.2 フロントエンドテスト
```bash
cd /opt/onprem-infra-system/project-root-infra/services/unified-portal/frontend

# テスト実行
npm run test
```

**期待出力**:
```
 PASS  src/components/mailserver/__tests__/UserTable.test.tsx
 PASS  src/components/mailserver/__tests__/UserForm.test.tsx
...
Test Suites: 10 passed, 10 total
Tests:       45 passed, 45 total
```

---

### Step 8: E2Eテスト - メールユーザー管理（30分）

**前提**: バックエンド・フロントエンドが起動している状態

#### 8.1 ログイン
1. http://localhost:5173 を開く
2. ログイン（デフォルト認証情報を使用）
3. ダッシュボードが表示されることを確認

#### 8.2 ユーザー一覧表示
1. サイドバーから「メール管理」→「ユーザー」をクリック
2. 既存ユーザー一覧が表示されることを確認
3. Flask usermgmtと同じユーザーが表示されることを確認

#### 8.3 ユーザー作成
1. 「新規ユーザー作成」ボタンをクリック
2. フォーム入力:
   - Email: `test-unified@kuma8088.com`
   - Password: `TestPass123!`
   - Domain: `kuma8088.com` を選択
   - Quota: `2048`
3. 「作成」をクリック
4. 成功メッセージが表示されることを確認
5. 一覧に新規ユーザーが表示されることを確認

**Flask usermgmtで確認**:
```bash
# 別ブラウザタブで Flask usermgmt を開く
xdg-open http://172.20.0.80:5000

# ログイン後、ユーザー一覧で `test-unified@kuma8088.com` が存在することを確認
```

#### 8.4 ユーザー編集
1. 作成したユーザーの「編集」ボタンをクリック
2. Quota を `3072` に変更
3. 「更新」をクリック
4. 一覧で Quota が更新されていることを確認

#### 8.5 パスワード変更
1. 「パスワード変更」ボタンをクリック
2. 新しいパスワード: `NewPass456!`
3. 「変更」をクリック
4. 成功メッセージを確認

**Dovecotで認証テスト**（オプション）:
```bash
docker exec -it mailserver-dovecot-1 doveadm auth test \
  test-unified@kuma8088.com NewPass456!
```

#### 8.6 有効/無効切替
1. 「無効化」ボタンをクリック
2. ユーザーのステータスが「無効」に変わることを確認
3. もう一度「有効化」ボタンをクリック
4. ステータスが「有効」に戻ることを確認

#### 8.7 監査ログ確認
1. サイドバーから「メール管理」→「監査ログ」をクリック
2. 上記操作のログが全て記録されていることを確認:
   - `create` - test-unified@kuma8088.com作成
   - `update` - Quota変更
   - `password_change` - パスワード変更
   - `update` - ステータス切替（2回）

#### 8.8 ユーザー削除
1. 「削除」ボタンをクリック
2. 確認ダイアログで「削除」を選択
3. ユーザーが一覧から削除されることを確認

**Flask usermgmtで確認**:
- `test-unified@kuma8088.com` が存在しないことを確認

---

### Step 9: DNS管理機能テスト（15分）

#### 9.1 Cloudflareリンク確認
1. サイドバーから「ドメイン管理」をクリック
2. 任意のゾーンで「Cloudflareで管理」ボタンをクリック
3. 新規タブでCloudflareダッシュボードが開くことを確認

#### 9.2 DNSレコード編集
1. 任意のレコードで「編集」をクリック
2. TTL を変更（例: 3600 → 7200）
3. 「更新」をクリック
4. 成功メッセージを確認

#### 9.3 DNS検証ツール
1. 「DNS検証」ボタンをクリック
2. ドメイン名とレコードタイプを入力
3. 「検証」をクリック
4. dig結果が表示されることを確認

---

### Step 10: パフォーマンステスト（15分）

```bash
# Apache Bench インストール（未インストールの場合）
sudo dnf install -y httpd-tools

# API パフォーマンステスト
cd /opt/onprem-infra-system/project-root-infra/services/unified-portal/backend

# 100リクエスト、10並列
ab -n 100 -c 10 \
  -H "Authorization: Bearer <token>" \
  http://localhost:8000/api/v1/mailserver/users

# 結果確認
# Time per request: < 500ms (平均) であること
# Failed requests: 0 であること
```

**期待出力**:
```
Concurrency Level:      10
Time taken for tests:   2.500 seconds
Complete requests:      100
Failed requests:        0
Total transferred:      50000 bytes
Requests per second:    40.00 [#/sec] (mean)
Time per request:       250.000 [ms] (mean)  <- 500ms以下
Time per request:       25.000 [ms] (mean, across all concurrent requests)
```

---

## 🚀 Phase 3: 本番デプロイ（所要時間: 約200分）

### Step 11: Docker Compose設定作成（30分）

#### 11.1 docker-compose.yml確認・更新
```bash
cd /opt/onprem-infra-system/project-root-infra/services/unified-portal

# 既存のdocker-compose.ymlを確認
cat docker-compose.yml
```

**必要な修正**:
```yaml
version: '3.8'

services:
  backend:
    build:
      context: ./backend
      dockerfile: Dockerfile
    container_name: unified-portal-backend
    ports:
      - "8000:8000"
    environment:
      - MAIL_DB_HOST=172.20.0.60
      - MAIL_DB_PORT=3306
      - MAIL_DB_NAME=mailserver_usermgmt
      - MAIL_DB_USER=usermgmt
      - MAIL_DB_PASSWORD=${MAIL_DB_PASSWORD}  # .envから読み込み
    networks:
      - unified-portal-net
      - mailserver_default  # 既存Mailserverネットワークに接続
    restart: unless-stopped
    healthcheck:
      test: ["CMD", "curl", "-f", "http://localhost:8000/health"]
      interval: 30s
      timeout: 10s
      retries: 3

  frontend:
    build:
      context: ./frontend
      dockerfile: Dockerfile
    container_name: unified-portal-frontend
    ports:
      - "5173:80"  # Nginxポート
    depends_on:
      - backend
    networks:
      - unified-portal-net
    restart: unless-stopped

  nginx:
    image: nginx:alpine
    container_name: unified-portal-nginx
    ports:
      - "8080:80"
    volumes:
      - ./config/nginx/conf.d:/etc/nginx/conf.d:ro
    depends_on:
      - backend
      - frontend
    networks:
      - unified-portal-net
    restart: unless-stopped

networks:
  unified-portal-net:
    driver: bridge
  mailserver_default:
    external: true  # 既存ネットワークを使用
```

#### 11.2 .env本番設定
```bash
# .envファイルを作成（docker-compose用）
cat > .env << EOF
MAIL_DB_PASSWORD=$(grep USERMGMT_DB_PASSWORD /opt/onprem-infra-system/project-root-infra/services/mailserver/.env | cut -d '=' -f2)
EOF

# 確認
cat .env
```

---

### Step 12: Nginx設定作成（20分）

```bash
cd /opt/onprem-infra-system/project-root-infra/services/unified-portal
mkdir -p config/nginx/conf.d

# Nginxリバースプロキシ設定
cat > config/nginx/conf.d/unified-portal.conf << 'EOF'
# Unified Portal - Reverse Proxy Configuration

# Backend API
upstream backend {
    server backend:8000;
}

# Frontend
upstream frontend {
    server frontend:80;
}

server {
    listen 80;
    server_name admin.kuma8088.com;

    # Security headers
    add_header X-Content-Type-Options "nosniff" always;
    add_header X-Frame-Options "SAMEORIGIN" always;
    add_header X-XSS-Protection "1; mode=block" always;

    # API endpoint
    location /api/ {
        proxy_pass http://backend;
        proxy_set_header Host $host;
        proxy_set_header X-Real-IP $remote_addr;
        proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for;
        proxy_set_header X-Forwarded-Proto $scheme;

        # CORS headers（必要に応じて）
        add_header Access-Control-Allow-Origin "*" always;
        add_header Access-Control-Allow-Methods "GET, POST, PUT, DELETE, OPTIONS" always;
        add_header Access-Control-Allow-Headers "Authorization, Content-Type" always;
    }

    # Health check
    location /health {
        proxy_pass http://backend/health;
    }

    # API docs
    location /docs {
        proxy_pass http://backend/docs;
    }

    # Frontend static files
    location / {
        proxy_pass http://frontend;
        proxy_set_header Host $host;
        proxy_set_header X-Real-IP $remote_addr;
        proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for;
        proxy_set_header X-Forwarded-Proto $scheme;
    }

    # Access log
    access_log /var/log/nginx/unified-portal-access.log;
    error_log /var/log/nginx/unified-portal-error.log;
}
EOF
```

---

### Step 13: Cloudflare Tunnel設定（15分）

```bash
# Cloudflare Tunnel設定ファイル確認
cat /opt/onprem-infra-system/project-root-infra/services/unified-portal/config/cloudflared/config.yml
```

**追加内容**:
```yaml
tunnel: <your-tunnel-id>
credentials-file: /etc/cloudflared/credentials.json

ingress:
  # Unified Portal
  - hostname: admin.kuma8088.com
    service: http://unified-portal-nginx:80

  # 既存設定（Blog System等）
  - hostname: blog.kuma8088.com
    service: http://nginx:80

  # Catch-all
  - service: http_status:404
```

**設定反映**:
```bash
# Cloudflare Tunnel設定更新
# (実際には `cloudflared tunnel route dns <tunnel-id> admin.kuma8088.com` 等が必要)
# 詳細は services/unified-portal/docs/cloudflare-tunnel-setup.md 参照
```

---

### Step 14: Docker イメージビルド（30分）

```bash
cd /opt/onprem-infra-system/project-root-infra/services/unified-portal

# バックエンドDockerfile確認
cat backend/Dockerfile

# フロントエンドDockerfile確認
cat frontend/Dockerfile

# イメージビルド
docker compose build

# イメージ確認
docker images | grep unified-portal
```

**期待出力**:
```
unified-portal-backend   latest   123abc456def   2 minutes ago   450MB
unified-portal-frontend  latest   789ghi012jkl   1 minute ago    150MB
```

---

### Step 15: Docker Compose起動（15分）

```bash
cd /opt/onprem-infra-system/project-root-infra/services/unified-portal

# 起動
docker compose up -d

# コンテナ確認
docker compose ps

# ログ確認
docker compose logs -f
```

**期待出力**:
```
NAME                         STATUS        PORTS
unified-portal-backend       Up            0.0.0.0:8000->8000/tcp
unified-portal-frontend      Up            0.0.0.0:5173->80/tcp
unified-portal-nginx         Up            0.0.0.0:8080->80/tcp
```

**ヘルスチェック**:
```bash
# Backend
curl http://localhost:8000/health

# Nginx経由
curl http://localhost:8080/health

# Cloudflare Tunnel経由（DNS伝播後）
curl https://admin.kuma8088.com/health
```

---

### Step 16: 本番環境動作確認（30分）

#### 16.1 HTTPSアクセス確認
```bash
# ブラウザで開く
xdg-open https://admin.kuma8088.com
```

**検証項目**:
- [ ] HTTPS接続成功（証明書エラーなし）
- [ ] ログイン画面表示
- [ ] ログイン成功
- [ ] ダッシュボード表示

#### 16.2 全機能テスト
**E2Eテストと同じ手順を本番環境で実施**:
1. メールユーザー作成
2. メールユーザー編集
3. パスワード変更
4. 有効/無効切替
5. 監査ログ確認
6. ユーザー削除
7. DNS管理（Cloudflareリンク、レコード編集）

#### 16.3 Flask usermgmt並行稼働確認
```bash
# Flask usermgmt起動確認
docker ps | grep usermgmt

# アクセス確認
xdg-open http://172.20.0.80:5000
```

**検証**:
- [ ] Flask usermgmtが正常稼働
- [ ] Unified Portalと同じデータが表示される
- [ ] 両方同時にアクセス可能

---

### Step 17: 監視・ログ設定（20分）

#### 17.1 ログローテーション設定
```bash
sudo tee /etc/logrotate.d/unified-portal << 'EOF'
/var/log/unified-portal/*.log {
    daily
    rotate 30
    compress
    delaycompress
    missingok
    notifempty
    create 0644 root root
}
EOF
```

#### 17.2 ログ確認
```bash
# アプリケーションログ
docker compose logs -f backend

# Nginxログ
docker exec unified-portal-nginx tail -f /var/log/nginx/unified-portal-access.log
```

---

### Step 18: バックアップ・ロールバック準備（40分）

#### 18.1 本番環境バックアップ
```bash
# 全データバックアップ
/opt/onprem-infra-system/project-root-infra/services/mailserver/scripts/backup-mailserver.sh

# Unified Portal設定バックアップ
tar -czf /mnt/backup-hdd/unified-portal-production_$(date +%Y%m%d_%H%M%S).tar.gz \
  /opt/onprem-infra-system/project-root-infra/services/unified-portal
```

#### 18.2 ロールバック手順確認
詳細は [08_ROLLBACK_PLAN.md](08_ROLLBACK_PLAN.md) 参照

**簡易ロールバック**:
```bash
# Unified Portal停止
cd /opt/onprem-infra-system/project-root-infra/services/unified-portal
docker compose down

# Flask usermgmt確認
docker ps | grep usermgmt
xdg-open http://172.20.0.80:5000
```

---

## ✅ 完了チェックリスト

### Phase 1: 環境構築
- [ ] リポジトリ最新化完了
- [ ] バックエンド仮想環境作成・依存関係インストール完了
- [ ] .env設定完了（MAIL_DB_PASSWORD設定済み）
- [ ] データベース接続確認完了（users, domains, audit_logs読み取り成功）
- [ ] バックエンド起動確認完了（http://localhost:8000/docs 表示）
- [ ] フロントエンド起動確認完了（http://localhost:5173 表示）

### Phase 2: 機能テスト
- [ ] バックエンドユニットテスト全てパス（カバレッジ > 80%）
- [ ] フロントエンドテスト全てパス
- [ ] E2Eテスト - メールユーザーCRUD操作成功
- [ ] E2Eテスト - 監査ログ記録確認
- [ ] Flask usermgmtとデータ同期確認
- [ ] DNS管理機能確認（Cloudflareリンク、レコード編集、検証ツール）
- [ ] パフォーマンステスト（レスポンスタイム < 500ms）

### Phase 3: 本番デプロイ
- [ ] Docker Compose設定作成完了
- [ ] Nginx設定作成完了
- [ ] Cloudflare Tunnel設定完了
- [ ] Dockerイメージビルド成功
- [ ] Docker Compose起動成功（全コンテナUp状態）
- [ ] HTTPSアクセス成功（https://admin.kuma8088.com）
- [ ] 本番環境で全機能テスト完了
- [ ] Flask usermgmt並行稼働確認
- [ ] ログ設定完了
- [ ] バックアップ作成完了

---

## 🚨 トラブルシューティング

### 問題: データベース接続エラー
**症状**: `Can't connect to MySQL server on '172.20.0.60'`

**原因**: MariaDBコンテナが起動していない、またはネットワーク設定誤り

**解決策**:
```bash
# MariaDB起動確認
docker ps | grep mariadb

# 起動していない場合
cd /opt/onprem-infra-system/project-root-infra/services/mailserver
docker compose up -d mariadb

# ネットワーク確認
docker network ls | grep mailserver
docker network inspect mailserver_default
```

---

### 問題: 認証エラー（Access denied）
**症状**: `Access denied for user 'usermgmt'@'%'`

**原因**: パスワード誤り

**解決策**:
```bash
# Mailserver .envから正しいパスワード取得
grep USERMGMT_DB_PASSWORD /opt/onprem-infra-system/project-root-infra/services/mailserver/.env

# Unified Portal .envに正しく設定
vi /opt/onprem-infra-system/project-root-infra/services/unified-portal/backend/.env
```

---

### 問題: Dockerコンテナが起動しない
**症状**: `docker compose up -d` でエラー

**原因**: ポート競合、イメージビルド失敗

**解決策**:
```bash
# ポート使用状況確認
sudo ss -tlnp | grep -E '8000|5173|8080'

# 既存コンテナ停止
docker compose down

# イメージ再ビルド
docker compose build --no-cache

# 起動
docker compose up -d
```

---

### 問題: Flask usermgmtと並行稼働できない
**症状**: 片方しか起動しない、データが同期しない

**原因**: データベース接続設定誤り

**解決策**:
- 両方とも同じデータベース（`mailserver_usermgmt`）を参照しているか確認
- ネットワーク設定を確認（`mailserver_default` ネットワークに接続）

---

## 📞 サポート

### 問題が解決しない場合
1. [08_ROLLBACK_PLAN.md](08_ROLLBACK_PLAN.md) でロールバック手順を確認
2. Flask usermgmtに切り戻し
3. Issue作成: `docs/application/unified-portal/integration/issues/`

---

**次のステップ**: [08_ROLLBACK_PLAN.md](08_ROLLBACK_PLAN.md) でロールバック計画を確認
