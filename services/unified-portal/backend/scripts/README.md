# Unified Portal - 管理スクリプト

**対象**: Dell WorkStation (Rocky Linux 9.6)

**作成日**: 2025-11-14

---

## 📋 スクリプト一覧

### 1. create-initial-admin.py

**目的**: 最初の管理者ユーザーを作成する

**使用タイミング**: Unified Portal初回セットアップ時

**前提条件**:
- MariaDB（unified_portal データベース）が稼働中
- admin_users テーブルが作成済み（migration実行済み）

**実行手順**:

```bash
# 1. unified-portal/backend ディレクトリへ移動
cd /opt/onprem-infra-system/project-root-infra/services/unified-portal/backend

# 2. 仮想環境がない場合は作成
python3 -m venv venv

# 3. 仮想環境を有効化
source venv/bin/activate

# 4. 依存関係をインストール（まだの場合）
pip install -r requirements.txt

# 5. データベースパスワードを環境変数に設定
export DB_PASSWORD='your-usermgmt-password'

# 6. スクリプトを実行
python3 scripts/create-initial-admin.py
```

**対話形式の入力例**:

```
============================================================
Unified Portal - Initial Admin User Creation
============================================================

Enter admin user details:

Username (default: admin): admin
Email: admin@kuma8088.com
Full name (optional): System Administrator
Password: ********
Confirm password: ********
Is superuser? (y/N): y

============================================================
Summary:
  Username: admin
  Email: admin@kuma8088.com
  Full name: System Administrator
  Superuser: True
============================================================

Create this user? (y/N): y

Hashing password...
Connecting to database...
Creating admin user...

============================================================
✅ Admin user created successfully!
============================================================

You can now login to the Unified Portal:
  URL: https://admin.kuma8088.com/login
  Username: admin
  Password: (the password you entered)
```

**トラブルシューティング**:

**エラー: `DB_PASSWORD environment variable not set`**
```bash
# DB_PASSWORDを設定してください
export DB_PASSWORD='your-password'
```

**エラー: `User with username 'admin' or email 'xxx@xxx.com' already exists`**
- 既に管理者ユーザーが存在します
- 別のユーザー名/メールアドレスを使用するか、既存ユーザーでログインしてください

**エラー: `Table 'admin_users' doesn't exist`**
```bash
# データベースマイグレーションを実行してください
cd /opt/onprem-infra-system/project-root-infra/services/unified-portal/backend

# マイグレーションSQL実行（Blog MariaDB）
docker exec -i blog-mariadb-1 mysql -u portal_admin -p'your-password' blog_management < migrations/001_add_admin_tables.sql
docker exec -i blog-mariadb-1 mysql -u portal_admin -p'your-password' blog_management < migrations/002_add_wordpress_sites.sql
```

---

### 2. create-portal-admin-users.sh

**目的**: Blog/Mailserver MariaDB に portal_admin データベースユーザーを作成

**使用タイミング**: Unified Portal初回セットアップ時

**前提条件**:
- Blog MariaDB コンテナ（blog-mariadb-1）が稼働中
- Mailserver MariaDB コンテナ（mailserver-mariadb-1）が稼働中
- 各MariaDBのrootパスワードを把握している

**実行手順**:

```bash
cd /opt/onprem-infra-system/project-root-infra/services/unified-portal/backend/scripts

# 実行権限を付与
chmod +x create-portal-admin-users.sh

# スクリプトを実行
./create-portal-admin-users.sh
```

**注意**: このスクリプトは**データベース接続用のユーザー**を作成します。ログイン用の管理者ユーザーではありません。

---

### 3. generate-encryption-key.sh

**目的**: データベース認証情報暗号化用のキーを生成

**使用タイミング**: Unified Portal初回セットアップ時

**実行手順**:

```bash
cd /opt/onprem-infra-system/project-root-infra/services/unified-portal/backend/scripts

# 実行権限を付与
chmod +x generate-encryption-key.sh

# スクリプトを実行
./generate-encryption-key.sh
```

**出力例**:

```
ENCRYPTION_KEY=xxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxx=
```

この出力を `.env` ファイルに追加してください。

---

## 📚 初回セットアップ完全ガイド

**所要時間**: 約15分

### Step 1: portal_admin データベースユーザー作成

```bash
cd /opt/onprem-infra-system/project-root-infra/services/unified-portal/backend/scripts
chmod +x create-portal-admin-users.sh
./create-portal-admin-users.sh
```

### Step 2: 暗号化キー生成

```bash
chmod +x generate-encryption-key.sh
./generate-encryption-key.sh
```

出力されたキーを `.env` ファイルに追加:

```bash
cd /opt/onprem-infra-system/project-root-infra/services/unified-portal
nano .env  # または vim .env
```

`.env` ファイルに追加:
```
ENCRYPTION_KEY=xxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxx=
```

### Step 3: データベースマイグレーション実行

```bash
cd /opt/onprem-infra-system/project-root-infra/services/unified-portal/backend

# Blog MariaDB（blog_management データベース）
docker exec -i blog-mariadb-1 mysql -u portal_admin -p'your-blog-portal-password' -e "CREATE DATABASE IF NOT EXISTS blog_management CHARACTER SET utf8mb4;"
docker exec -i blog-mariadb-1 mysql -u portal_admin -p'your-blog-portal-password' blog_management < migrations/001_add_admin_tables.sql
docker exec -i blog-mariadb-1 mysql -u portal_admin -p'your-blog-portal-password' blog_management < migrations/002_add_wordpress_sites.sql

# Mailserver MariaDB（unified_portal データベース）
docker exec -i mailserver-mariadb-1 mysql -u usermgmt -p'your-usermgmt-password' -e "CREATE DATABASE IF NOT EXISTS unified_portal CHARACTER SET utf8mb4;"
docker exec -i mailserver-mariadb-1 mysql -u usermgmt -p'your-usermgmt-password' unified_portal < migrations/001_add_admin_tables.sql
```

### Step 4: 初期管理者ユーザー作成

```bash
cd /opt/onprem-infra-system/project-root-infra/services/unified-portal/backend

# 仮想環境作成・有効化
python3 -m venv venv
source venv/bin/activate

# 依存関係インストール
pip install -r requirements.txt

# データベースパスワード設定
export DB_PASSWORD='your-usermgmt-password'

# 初期管理者作成
python3 scripts/create-initial-admin.py
```

### Step 5: ログイン確認

ブラウザで https://admin.kuma8088.com/login にアクセスし、作成した管理者ユーザーでログインしてください。

---

## 🔒 セキュリティ注意事項

1. **パスワードは必ず強力なものを使用**（12文字以上、大小英数字+記号）
2. **DB_PASSWORDは実行後に必ずunset**（`unset DB_PASSWORD`）
3. **初期管理者のパスワードは安全に保管**（パスワードマネージャー推奨）
4. **Superuserは最小限に**（通常は1人のみ）

---

## 📞 トラブル発生時

問題が発生した場合は、以下を確認してください:

1. **データベース接続確認**:
```bash
# Mailserver MariaDB
docker exec -it mailserver-mariadb-1 mysql -u usermgmt -p -e "SHOW DATABASES;"

# Blog MariaDB
docker exec -it blog-mariadb-1 mysql -u portal_admin -p -e "SHOW DATABASES;"
```

2. **テーブル確認**:
```bash
docker exec -it mailserver-mariadb-1 mysql -u usermgmt -p unified_portal -e "SHOW TABLES;"
```

3. **ログ確認**:
```bash
docker compose -f /opt/onprem-infra-system/project-root-infra/services/unified-portal/docker-compose.yml logs backend
```
