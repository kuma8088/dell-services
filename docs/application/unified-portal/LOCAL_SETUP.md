# Unified Portal - ローカル環境セットアップ手順

Phase 1-L: 環境構築（L-001 ~ L-006）

## 前提条件

- Dell WorkStation（Rocky Linux 9.6）にSSH接続済み
- Mailserver稼働中（Docker Compose）
- Python 3.10以上インストール済み

## L-001: .env設定ファイル作成

### 1. USERMGMT_DB_PASSWORD を取得

```bash
cd /opt/onprem-infra-system/project-root-infra/services/mailserver
grep USERMGMT_DB_PASSWORD .env
```

**出力例:**
```
USERMGMT_DB_PASSWORD=your-actual-password-here
```

このパスワードをコピーしてください。

### 2. .env ファイル作成

```bash
cd /opt/onprem-infra-system/project-root-infra/services/unified-portal/backend

# .env.local-setup をコピー
cp .env.local-setup .env

# <USERMGMT_DB_PASSWORD> を実際のパスワードに置換
nano .env
```

**編集内容:**
- `<USERMGMT_DB_PASSWORD>` → 上記で取得したパスワード
- `<YOUR_CLOUDFLARE_TOKEN>` → Cloudflare API Token（必要に応じて）
- `<YOUR_EMAIL>` → あなたのメールアドレス

**最終的な .env の例:**
```env
# Database - Unified Portal (main database)
DATABASE_URL=mysql+pymysql://usermgmt:ActualPassword123@172.20.0.60:3306/unified_portal

# Database - Mailserver User Management
MAILSERVER_DATABASE_URL=mysql+pymysql://usermgmt:ActualPassword123@172.20.0.60:3306/mailserver_usermgmt
```

### 3. パーミッション設定

```bash
chmod 600 .env
```

**検証:**
```bash
cat .env | grep MAILSERVER_DATABASE_URL
```

✅ `MAILSERVER_DATABASE_URL=mysql+pymysql://usermgmt:ActualPassword@...` が表示されればOK

---

## L-002: Python依存関係インストール

### 1. venv作成（初回のみ）

```bash
cd /opt/onprem-infra-system/project-root-infra/services/unified-portal/backend

# venvがない場合のみ作成
if [ ! -d "venv" ]; then
    python3 -m venv venv
fi
```

### 2. venv有効化

```bash
source venv/bin/activate
```

**確認:** プロンプトが `(venv)` から始まることを確認

### 3. pip アップグレード

```bash
pip install --upgrade pip
```

### 4. 依存関係インストール

```bash
pip install -r requirements.txt
```

**所要時間:** 約2-3分

### 5. インストール確認

```bash
pip list | grep -E "fastapi|sqlalchemy|passlib|pymysql"
```

**期待出力:**
```
fastapi                  0.109.0
passlib                  1.7.4
pymysql                  1.1.0
SQLAlchemy               2.0.25
```

✅ すべてのパッケージが表示されればOK

---

## L-003: データベース接続確認

### 1. Mailserver DB接続テスト

```bash
cd /opt/onprem-infra-system/project-root-infra/services/unified-portal/backend
source venv/bin/activate

python -c "
from app.database import mailserver_engine
from sqlalchemy import text

try:
    with mailserver_engine.connect() as conn:
        result = conn.execute(text('SELECT COUNT(*) FROM users'))
        user_count = result.scalar()
        print(f'✅ Mailserver DB接続成功')
        print(f'   Users count: {user_count}')

        result = conn.execute(text('SELECT COUNT(*) FROM domains'))
        domain_count = result.scalar()
        print(f'   Domains count: {domain_count}')
except Exception as e:
    print(f'❌ エラー: {e}')
    import sys
    sys.exit(1)
"
```

**期待出力:**
```
✅ Mailserver DB接続成功
   Users count: 3
   Domains count: 2
```

### 2. トラブルシューティング

**エラー: `ModuleNotFoundError: No module named 'app'`**
```bash
# venv を有効化し忘れ
source venv/bin/activate
```

**エラー: `Can't connect to MySQL server`**
```bash
# Mailserver コンテナ稼働確認
cd /opt/onprem-infra-system/project-root-infra/services/mailserver
docker compose ps | grep mariadb

# 172.20.0.60 に接続できるか確認
ping -c 3 172.20.0.60
```

**エラー: `Access denied for user 'usermgmt'`**
```bash
# パスワードが間違っている
cat .env | grep MAILSERVER_DATABASE_URL
grep USERMGMT_DB_PASSWORD ../../../mailserver/.env
# パスワードが一致しているか確認
```

✅ 上記コマンドでエラーなく実行できればOK

---

## L-004: バックエンド起動確認

### 1. FastAPI サーバー起動

```bash
cd /opt/onprem-infra-system/project-root-infra/services/unified-portal/backend
source venv/bin/activate

python -m app.main
```

**期待出力:**
```
INFO:     Started server process [12345]
INFO:     Waiting for application startup.
INFO:     Application startup complete.
INFO:     Uvicorn running on http://0.0.0.0:8000 (Press CTRL+C to quit)
```

### 2. 別ターミナルで接続確認

**新しいターミナルを開く:**
```bash
curl http://localhost:8000/api/health
```

**期待出力:**
```json
{"status":"healthy","version":"0.1.0"}
```

✅ 上記JSONが返ってくればOK

### 3. サーバー停止

元のターミナルで `Ctrl+C` を押してサーバーを停止

---

## L-005: APIエンドポイント動作確認

### 1. バックエンドをバックグラウンドで起動

```bash
cd /opt/onprem-infra-system/project-root-infra/services/unified-portal/backend
source venv/bin/activate

nohup python -m app.main > /tmp/unified-portal.log 2>&1 &
echo $! > /tmp/unified-portal.pid
```

### 2. Swagger UI アクセス

ブラウザで以下のURLを開く:
```
http://<Dell WorkStationのIPアドレス>:8000/docs
```

または、ローカルポートフォワーディングを使用:
```bash
# ローカルマシンから SSH接続時
ssh -L 8000:localhost:8000 user@dell-workstation
```

その後、ブラウザで `http://localhost:8000/docs` を開く

### 3. Mailserver API テスト

Swagger UI で以下のエンドポイントをテスト:

#### GET /api/mailserver/domains
- **Try it out** → **Execute**
- **期待出力:** 既存ドメイン一覧のJSON

```json
[
  {
    "id": 1,
    "domain_name": "kuma8088.com",
    "is_active": true,
    "created_at": "2025-11-01T00:00:00"
  }
]
```

#### GET /api/mailserver/users
- **Try it out** → **Execute**
- **期待出力:** 既存ユーザー一覧のJSON

```json
[
  {
    "id": 1,
    "email": "admin@kuma8088.com",
    "domain_id": 1,
    "is_active": true,
    "created_at": "2025-11-01T00:00:00"
  }
]
```

#### GET /api/mailserver/audit-logs
- **Try it out** → **Execute**
- **期待出力:** 監査ログ一覧のJSON

### 4. サーバー停止

```bash
kill $(cat /tmp/unified-portal.pid)
rm /tmp/unified-portal.pid
```

✅ すべてのAPIが正常にレスポンスを返せばOK

---

## L-006: エラー修正・デバッグ

### 1. ログ確認

```bash
tail -f /tmp/unified-portal.log
```

### 2. よくあるエラーと対処

#### エラー: `ImportError: cannot import name 'MailUser' from 'app.models'`

**原因:** `app/models/__init__.py` にインポートが不足

**対処:**
```bash
cd /opt/onprem-infra-system/project-root-infra/services/unified-portal/backend
cat app/models/__init__.py
```

**期待内容:**
```python
"""Models package."""
from app.models.mail_user import MailUser
from app.models.mail_domain import MailDomain
from app.models.audit_log import AuditLog

__all__ = ["MailUser", "MailDomain", "AuditLog"]
```

もし不足していれば追加する。

#### エラー: `sqlalchemy.exc.OperationalError: (pymysql.err.OperationalError) (2003, "Can't connect to MySQL server")`

**原因:** Mailserver MariaDBコンテナが起動していない

**対処:**
```bash
cd /opt/onprem-infra-system/project-root-infra/services/mailserver
docker compose ps | grep mariadb
docker compose up -d mariadb
```

#### エラー: `AttributeError: module 'app.models' has no attribute 'MailUser'`

**原因:** モデルファイルが存在しない、または構文エラー

**対処:**
```bash
ls -la app/models/
# mail_user.py, mail_domain.py, audit_log.py が存在するか確認

# 構文チェック
python -m py_compile app/models/mail_user.py
python -m py_compile app/models/mail_domain.py
python -m py_compile app/models/audit_log.py
```

#### エラー: `ModuleNotFoundError: No module named 'passlib'`

**原因:** requirements.txt のインストール漏れ

**対処:**
```bash
source venv/bin/activate
pip install -r requirements.txt
```

### 3. デバッグモード起動

```bash
cd /opt/onprem-infra-system/project-root-infra/services/unified-portal/backend
source venv/bin/activate

DEBUG=true python -m app.main
```

詳細なエラーログが表示される。

---

## ✅ L-001 ~ L-006 完了確認

すべて完了したら、以下をチェック:

- [ ] `.env` ファイル作成済み（MAILSERVER_DATABASE_URL設定済み）
- [ ] `pip list` で必要なパッケージがインストール済み
- [ ] `python -c "from app.database import mailserver_engine; ..."` でDB接続成功
- [ ] `python -m app.main` でサーバー起動成功
- [ ] `http://localhost:8000/docs` でSwagger UI表示
- [ ] Mailserver API（/api/mailserver/domains, /users, /audit-logs）が正常動作

✅ すべてチェックできたら **Phase 1-L 完了** です！

次のステップ: フロントエンド実装（W-013 ~ W-025）

---

## 参考

- タスク詳細: [docs/application/unified-portal/integration/03_TASK_BREAKDOWN.md](../integration/03_TASK_BREAKDOWN.md)
- API仕様: Swagger UI (`http://localhost:8000/docs`)
- トラブルシューティング: このドキュメントのL-006セクション
