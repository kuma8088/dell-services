# メールユーザ管理システム - 設計書

**文書バージョン**: 1.0
**作成日**: 2025-11-04
**対象環境**: Dell RockyLinux 9.6 (Tailscale VPN内部アクセス専用)
**設計方式**: Webベースユーザ管理インターフェース
**参照文書**: 02_design.md v6.0, 01_requirements.md v6.0

---

## 1. システム概要

### 1.1 目的

メールサーバーのユーザ管理を、Webインターフェースを通じて簡便に行えるようにする。現在の`/etc/dovecot/users`ファイルベースの手動管理から、Webベースの管理に移行し、運用効率を向上させる。

### 1.2 スコープ

**対象機能**:
- メールアカウント追加・編集・削除
- ドメイン単位でのアカウント管理（グルーピング表示）
- パスワード設定・変更
- メールボックス容量（quota）設定
- ユーザ一覧表示（ドメイン別フィルタリング）

**アクセス制限**:
- **Tailscale VPN内部アクセス専用**（インターネットからの直接アクセス不可）
- HTTPS接続必須（Tailscale証明書使用）
- 管理者認証必須（初期段階はBasic認証、将来的にはTailscale OAuth）

### 1.3 アーキテクチャ方針

```
┌─────────────────────────────────────────────────────────────────┐
│                   Tailscale VPN ネットワーク                     │
│                   (100.x.x.x/10 プライベート空間)                │
│                                                                   │
│  ┌──────────────┐  ┌──────────────┐  ┌──────────────┐          │
│  │  PC/Mac      │  │  iPhone      │  │   Android    │          │
│  │  管理者デバイス│  │  管理者デバイス│  │  管理者デバイス│          │
│  └──────┬───────┘  └──────┬───────┘  └──────┬───────┘          │
│         │                  │                  │                   │
│         └──────────────────┼──────────────────┘                   │
│                            │ HTTPS (443)                          │
│                            ▼                                      │
│                  ┌─────────────────────┐                         │
│                  │   Nginx Reverse     │                         │
│                  │   Proxy (172.20.0.10)│                        │
│                  │   Port 443          │                         │
│                  └──────────┬──────────┘                         │
│                             │                                     │
│                             ▼                                     │
│                  ┌─────────────────────┐                         │
│                  │  User Management    │                         │
│                  │  Web App            │                         │
│                  │  (Flask/FastAPI)    │                         │
│                  │  172.20.0.90        │                         │
│                  └──────────┬──────────┘                         │
│                             │                                     │
│                   ┌─────────┴─────────┐                         │
│                   │                   │                          │
│                   ▼                   ▼                          │
│         ┌─────────────────┐  ┌─────────────────┐               │
│         │  Dovecot Users  │  │  MariaDB        │               │
│         │  File Handler   │  │  (将来拡張)     │               │
│         │  /etc/dovecot/  │  │  172.20.0.60    │               │
│         │  users          │  │                 │               │
│         └─────────────────┘  └─────────────────┘               │
└─────────────────────────────────────────────────────────────────┘
```

---

## 2. 技術スタック

### 2.1 バックエンド

**フレームワーク**: Flask (Python 3.11+)
- **理由**: シンプルな管理画面に最適、軽量、既存のPython環境と統合しやすい
- **代替案**: FastAPI（将来的なAPI拡張を見据える場合）

**主要ライブラリ**:
```python
# Web Framework
Flask==3.0.0
Flask-WTF==1.2.1           # フォーム処理
Flask-Login==0.6.3         # 認証セッション管理

# パスワードハッシュ
passlib==1.7.4             # SHA512-CRYPT生成
bcrypt==4.1.1              # 将来的なbcrypt移行用

# データベース (将来拡張)
SQLAlchemy==2.0.23
pymysql==1.1.0

# セキュリティ
python-dotenv==1.0.0       # 環境変数管理
cryptography==41.0.7       # 追加暗号化機能
```

### 2.2 フロントエンド

**テンプレートエンジン**: Jinja2 (Flask標準)

**CSSフレームワーク**: Bootstrap 5.3
- **理由**: レスポンシブデザイン対応、モバイルデバイス（iPhone/Android）での管理に最適

**JavaScript**: 最小限のVanilla JS
- フォームバリデーション
- 動的ドメインフィルタリング

### 2.3 データストレージ

**既存MariaDBコンテナ活用**: `mailserver-mariadb` (172.20.0.60)
- 既にDocker Composeで稼働中のMariaDB 10.11.7を利用
- 新規データベース`mailserver_usermgmt`を作成（既存`roundcubemail`と分離）
- 既存環境への影響なし（独立したデータベース）

**データストレージ戦略**:

**選択肢A: 最初からMariaDBベース（推奨）**
- ユーザデータ: MariaDB `mailserver_usermgmt`データベース
- Dovecot設定: パラレル運用（File認証 + SQL認証の両方有効）
- 移行フェーズ不要で初期構築が簡単

**選択肢B: ファイルベース → MariaDB段階的移行**
- フェーズ1: `/etc/dovecot/users`ファイルベース
- フェーズ2: MariaDBへ段階的移行
- 移行中も既存ユーザの認証継続（ダウンタイムなし）

**推奨**: 選択肢A（最初からMariaDB）
- 理由: 監査ログ、検索機能、将来拡張を考慮するとMariaDBベースが有利
- 既存環境への影響: Dovecot設定に`!include auth-sql.conf.ext`追加のみ（既存File認証も並行稼働可能）

---

## 3. データモデル

### 3.1 現在のDovecot Usersファイル形式

```
test@kuma8088.com:{SHA512-CRYPT}$6$...hash...:5000:5000::/var/mail/vhosts/kuma8088.com/test::
```

**フィールド構成**:
1. Email address
2. Password hash (SHA512-CRYPT形式)
3. UID (固定: 5000)
4. GID (固定: 5000)
5. Home directory (空欄)
6. Maildir path
7. Extra fields (空欄)

### 3.2 アプリケーションデータモデル

**Userクラス（Python）**:
```python
class MailUser:
    email: str                    # test@kuma8088.com
    domain: str                   # kuma8088.com (emailから抽出)
    password_hash: str            # {SHA512-CRYPT}$6$...
    uid: int = 5000               # 固定値
    gid: int = 5000               # 固定値
    maildir: str                  # /var/mail/vhosts/{domain}/{localpart}
    quota: int                    # MB単位 (例: 1024 = 1GB)
    created_at: datetime
    updated_at: datetime

    def to_dovecot_line(self) -> str:
        """Dovecot usersファイル形式に変換"""
        return f"{self.email}:{self.password_hash}:{self.uid}:{self.gid}::{self.maildir}::"
```

**Domainクラス（Python）**:
```python
class Domain:
    name: str                     # kuma8088.com
    description: str              # "メインドメイン"
    default_quota: int            # デフォルトメールボックス容量(MB)
    user_count: int               # このドメインのユーザ数
    total_quota: int              # このドメインの合計容量(MB)
```

### 3.3 将来のMariaDBスキーマ（フェーズ2）

```sql
CREATE TABLE domains (
    id INT PRIMARY KEY AUTO_INCREMENT,
    name VARCHAR(255) UNIQUE NOT NULL,
    description VARCHAR(500),
    default_quota INT DEFAULT 1024,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,
    INDEX idx_name (name)
);

CREATE TABLE users (
    id INT PRIMARY KEY AUTO_INCREMENT,
    email VARCHAR(255) UNIQUE NOT NULL,
    domain_id INT NOT NULL,
    password_hash VARCHAR(255) NOT NULL,
    quota INT DEFAULT 1024,
    uid INT DEFAULT 5000,
    gid INT DEFAULT 5000,
    maildir VARCHAR(500) NOT NULL,
    enabled BOOLEAN DEFAULT TRUE,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,
    FOREIGN KEY (domain_id) REFERENCES domains(id) ON DELETE CASCADE,
    INDEX idx_email (email),
    INDEX idx_domain (domain_id)
);

CREATE TABLE audit_logs (
    id INT PRIMARY KEY AUTO_INCREMENT,
    action ENUM('create', 'update', 'delete', 'password_change') NOT NULL,
    user_email VARCHAR(255) NOT NULL,
    admin_ip VARCHAR(45) NOT NULL,
    details JSON,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    INDEX idx_user (user_email),
    INDEX idx_created (created_at)
);
```

---

## 4. APIエンドポイント設計

### 4.1 認証エンドポイント

| エンドポイント | メソッド | 説明 | 認証 |
|--------------|---------|------|------|
| `/login` | GET, POST | 管理者ログイン画面 | 不要 |
| `/logout` | POST | ログアウト | 必須 |

### 4.2 ユーザ管理エンドポイント

| エンドポイント | メソッド | 説明 | 認証 |
|--------------|---------|------|------|
| `/` | GET | ダッシュボード（ドメイン一覧） | 必須 |
| `/users` | GET | 全ユーザ一覧 | 必須 |
| `/users?domain={domain}` | GET | ドメイン別ユーザ一覧 | 必須 |
| `/users/new` | GET, POST | 新規ユーザ作成フォーム | 必須 |
| `/users/<email>/edit` | GET, POST | ユーザ編集フォーム | 必須 |
| `/users/<email>/delete` | POST | ユーザ削除 | 必須 |
| `/users/<email>/password` | GET, POST | パスワード変更フォーム | 必須 |

### 4.3 ドメイン管理エンドポイント

| エンドポイント | メソッド | 説明 | 認証 |
|--------------|---------|------|------|
| `/domains` | GET | ドメイン一覧 | 必須 |
| `/domains/<domain>` | GET | ドメイン詳細（ユーザ一覧） | 必須 |

### 4.4 API仕様例

**POST /users/new - ユーザ作成**

```json
// Request Body
{
  "email": "newuser@kuma8088.com",
  "password": "SecurePassword123!",
  "quota": 2048
}

// Response (Success)
{
  "status": "success",
  "message": "ユーザ newuser@kuma8088.com を作成しました",
  "user": {
    "email": "newuser@kuma8088.com",
    "domain": "kuma8088.com",
    "quota": 2048,
    "created_at": "2025-11-04T10:30:00Z"
  }
}

// Response (Error)
{
  "status": "error",
  "message": "このメールアドレスは既に登録されています"
}
```

---

## 5. UI/UX設計

### 5.1 画面一覧

**1. ログイン画面** (`/login`)
```
┌────────────────────────────────────────┐
│  メールサーバー管理システム            │
│                                        │
│  ┌──────────────────────────────────┐ │
│  │ ユーザー名: [_______________]   │ │
│  │ パスワード: [_______________]   │ │
│  │                                  │ │
│  │         [ ログイン ]             │ │
│  └──────────────────────────────────┘ │
│                                        │
│  ⚠️ Tailscale VPN接続が必要です      │
└────────────────────────────────────────┘
```

**2. ダッシュボード** (`/`)
```
┌────────────────────────────────────────────────────────────┐
│  メールサーバー管理                    [ログアウト]         │
├────────────────────────────────────────────────────────────┤
│  📊 ドメイン一覧                                           │
│                                                            │
│  ┌─────────────────────────────────────────────────────┐ │
│  │ ドメイン         ユーザ数   合計容量    操作         │ │
│  ├─────────────────────────────────────────────────────┤ │
│  │ kuma8088.com        2      3.0 GB    [詳細を見る]   │ │
│  │ example.com         5      8.5 GB    [詳細を見る]   │ │
│  └─────────────────────────────────────────────────────┘ │
│                                                            │
│  [+ 新規ユーザ追加]                                       │
└────────────────────────────────────────────────────────────┘
```

**3. ユーザ一覧画面** (`/users` または `/domains/{domain}`)
```
┌────────────────────────────────────────────────────────────┐
│  kuma8088.com のユーザ一覧                                 │
├────────────────────────────────────────────────────────────┤
│  [ドメイン選択: kuma8088.com ▼]  [+ 新規ユーザ追加]      │
│                                                            │
│  ┌─────────────────────────────────────────────────────┐ │
│  │ メールアドレス          容量     操作                │ │
│  ├─────────────────────────────────────────────────────┤ │
│  │ test@kuma8088.com      1.0 GB   [編集] [削除]      │ │
│  │ info@kuma8088.com      2.0 GB   [編集] [削除]      │ │
│  └─────────────────────────────────────────────────────┘ │
└────────────────────────────────────────────────────────────┘
```

**4. ユーザ作成/編集フォーム** (`/users/new` または `/users/{email}/edit`)
```
┌────────────────────────────────────────────────────────────┐
│  新規ユーザ作成                                            │
├────────────────────────────────────────────────────────────┤
│  メールアドレス: [___________]@[ドメイン選択 ▼]          │
│                   例: test                                 │
│                                                            │
│  パスワード:     [___________________________]            │
│  パスワード確認: [___________________________]            │
│                                                            │
│  メールボックス容量: [1024] MB (= 1 GB)                   │
│                                                            │
│  ┌──────────────────────────────────────────────────────┐│
│  │ 💡 パスワードは8文字以上、英数字記号を含む必要があります││
│  └──────────────────────────────────────────────────────┘│
│                                                            │
│         [作成]  [キャンセル]                              │
└────────────────────────────────────────────────────────────┘
```

### 5.2 レスポンシブデザイン

**モバイル対応**:
- Bootstrap 5のグリッドシステム使用
- タッチ操作に最適化されたボタンサイズ
- スワイプジェスチャーでのナビゲーション

**アクセシビリティ**:
- WCAG 2.1 Level AA準拠
- キーボードナビゲーション対応
- スクリーンリーダー対応

---

## 6. セキュリティ設計

### 6.1 アクセス制御

**ネットワークレベル**:
- **Tailscale VPN必須**: Nginxは100.x.x.x/10からのアクセスのみ許可
- **HTTPS強制**: HTTP→HTTPSリダイレクト
- **証明書**: Tailscale Let's Encrypt証明書使用

**Nginx設定例**:
```nginx
# Tailscale IPアドレスからのアクセスのみ許可
geo $tailscale_ip {
    default 0;
    100.0.0.0/10 1;
}

server {
    listen 443 ssl;
    server_name dell-workstation.tail67811d.ts.net;

    # Tailscale以外からのアクセス拒否
    if ($tailscale_ip = 0) {
        return 403;
    }

    ssl_certificate /var/lib/tailscale/certs/tls.crt;
    ssl_certificate_key /var/lib/tailscale/certs/tls.key;

    location /admin {
        proxy_pass http://172.20.0.90:5000;
        proxy_set_header X-Real-IP $remote_addr;
        proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for;
    }
}
```

### 6.2 認証方式

**フェーズ1（初期実装）**: Flask-Loginによるセッションベース認証
```python
# 環境変数で管理者パスワード設定
ADMIN_USERNAME = os.getenv('ADMIN_USERNAME', 'admin')
ADMIN_PASSWORD_HASH = os.getenv('ADMIN_PASSWORD_HASH')

# ログイン処理
@app.route('/login', methods=['GET', 'POST'])
def login():
    if request.method == 'POST':
        username = request.form['username']
        password = request.form['password']

        if username == ADMIN_USERNAME and verify_password(password, ADMIN_PASSWORD_HASH):
            user = User(username)
            login_user(user)
            return redirect(url_for('dashboard'))
        else:
            flash('ユーザー名またはパスワードが正しくありません')

    return render_template('login.html')
```

**フェーズ2（将来拡張）**: Tailscale OAuth統合
- Tailscale IDによる自動認証
- ドメイン単位でのアクセス制御（kuma8088.comドメイン管理者のみ許可など）

### 6.3 パスワードセキュリティ

**ハッシュ方式**: SHA512-CRYPT (Dovecot互換)
```python
from passlib.hash import sha512_crypt

def hash_password(password: str) -> str:
    """Dovecot互換のSHA512-CRYPTハッシュ生成"""
    return "{SHA512-CRYPT}" + sha512_crypt.hash(password)

def verify_password(password: str, hash_with_prefix: str) -> bool:
    """パスワード検証"""
    hash_only = hash_with_prefix.replace("{SHA512-CRYPT}", "")
    return sha512_crypt.verify(password, hash_only)
```

**パスワードポリシー**:
- 最小長: 8文字
- 複雑性: 英大文字、英小文字、数字、記号のうち3種類以上
- 履歴: 過去3回のパスワードと重複不可（将来実装）

### 6.4 CSRF保護

**Flask-WTF使用**:
```python
from flask_wtf.csrf import CSRFProtect

app = Flask(__name__)
app.config['SECRET_KEY'] = os.getenv('SECRET_KEY')
csrf = CSRFProtect(app)

# フォーム定義
class UserForm(FlaskForm):
    email = StringField('Email', validators=[DataRequired(), Email()])
    password = PasswordField('Password', validators=[DataRequired(), Length(min=8)])
    quota = IntegerField('Quota (MB)', validators=[DataRequired(), NumberRange(min=1)])
    submit = SubmitField('作成')
```

### 6.5 ファイルアクセス制御

**Dovecot usersファイル操作**:
```python
import fcntl
import tempfile
import shutil

class DovecotUserFile:
    def __init__(self, filepath='/etc/dovecot/users'):
        self.filepath = filepath

    def read_users(self) -> List[MailUser]:
        """排他ロックでファイル読み取り"""
        with open(self.filepath, 'r') as f:
            fcntl.flock(f, fcntl.LOCK_SH)  # 共有ロック
            users = [MailUser.from_line(line) for line in f if line.strip()]
            fcntl.flock(f, fcntl.LOCK_UN)  # ロック解除
        return users

    def write_users(self, users: List[MailUser]):
        """アトミック書き込み（一時ファイル→リネーム）"""
        with tempfile.NamedTemporaryFile(mode='w', delete=False) as tmp:
            fcntl.flock(tmp, fcntl.LOCK_EX)  # 排他ロック
            for user in users:
                tmp.write(user.to_dovecot_line() + '\n')
            fcntl.flock(tmp, fcntl.LOCK_UN)
            tmp_path = tmp.name

        # アトミックリネーム
        shutil.move(tmp_path, self.filepath)
        os.chmod(self.filepath, 0o640)
        os.chown(self.filepath, 0, 5000)  # root:vmail
```

**権限設定**:
- ファイルパーミッション: `640` (rw-r-----)
- 所有者: `root:vmail` (または `root:dovecot`)
- アプリケーション実行ユーザ: `root`または`sudo`権限付与

### 6.6 監査ログ

**操作ログ記録**:
```python
import logging

audit_logger = logging.getLogger('audit')
audit_handler = logging.FileHandler('/var/log/mailserver/user-management-audit.log')
audit_handler.setFormatter(logging.Formatter(
    '%(asctime)s - %(levelname)s - [%(remote_addr)s] %(action)s - %(details)s'
))
audit_logger.addHandler(audit_handler)

def log_action(action: str, details: dict):
    """監査ログ記録"""
    audit_logger.info(f"{action}", extra={
        'remote_addr': request.remote_addr,
        'action': action,
        'details': json.dumps(details)
    })

# 使用例
@app.route('/users/new', methods=['POST'])
@login_required
def create_user():
    # ... ユーザ作成処理 ...
    log_action('USER_CREATED', {'email': email, 'quota': quota})
```

---

## 7. Docker統合設計

### 7.1 Dockerコンテナ構成

**新規コンテナ**: `mailserver-usermgmt`

```yaml
# docker-compose.yml に追加
services:
  usermgmt:
    build:
      context: ./usermgmt
      dockerfile: Dockerfile
    container_name: mailserver-usermgmt
    hostname: usermgmt
    restart: always
    networks:
      mailserver_network:
        ipv4_address: 172.20.0.90
    environment:
      - TZ=${TZ}
      - ADMIN_USERNAME=${USERMGMT_ADMIN_USERNAME}
      - ADMIN_PASSWORD_HASH=${USERMGMT_ADMIN_PASSWORD_HASH}
      - SECRET_KEY=${USERMGMT_SECRET_KEY}
      - FLASK_ENV=production
    volumes:
      - ./config/dovecot/users:/etc/dovecot/users
      - ./logs/usermgmt:/var/log/usermgmt
      - ./data/usermgmt:/var/lib/usermgmt
    depends_on:
      - dovecot
    healthcheck:
      test: ["CMD", "curl", "-f", "http://localhost:5000/health"]
      interval: 30s
      timeout: 10s
      retries: 3
      start_period: 40s
```

### 7.2 Dockerfile

```dockerfile
FROM python:3.11-slim

# 作業ディレクトリ
WORKDIR /app

# システムパッケージインストール
RUN apt-get update && apt-get install -y \
    curl \
    && rm -rf /var/lib/apt/lists/*

# Pythonパッケージインストール
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# アプリケーションコピー
COPY app/ ./app/
COPY config/ ./config/

# 実行ユーザ（root権限でDovecot usersファイル書き込み必要）
USER root

# 起動コマンド
CMD ["gunicorn", "-w", "2", "-b", "0.0.0.0:5000", "app:app"]
```

### 7.3 Nginx統合

**Nginx設定更新** (`config/nginx/templates/default.conf.template`):

```nginx
# 既存のRoundcube設定に追加
upstream usermgmt {
    server 172.20.0.90:5000;
}

server {
    listen 443 ssl http2;
    server_name ${MAIL_HOSTNAME};

    ssl_certificate ${TLS_CERT_FILE};
    ssl_certificate_key ${TLS_KEY_FILE};

    # Tailscale IPアドレスチェック
    geo $tailscale_ip {
        default 0;
        100.0.0.0/10 1;
    }

    # ユーザ管理画面（/admin パス）
    location /admin {
        if ($tailscale_ip = 0) {
            return 403 "Access denied. Tailscale VPN required.";
        }

        proxy_pass http://usermgmt;
        proxy_set_header Host $host;
        proxy_set_header X-Real-IP $remote_addr;
        proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for;
        proxy_set_header X-Forwarded-Proto $scheme;

        # セッションCookie設定
        proxy_cookie_path / "/; HttpOnly; Secure; SameSite=Strict";
    }

    # 既存のRoundcube設定（/ パス）
    location / {
        proxy_pass http://roundcube;
        # ... 既存設定 ...
    }
}
```

---

## 8. 実装フェーズと既存環境への影響

### 8.1 推奨実装方式: MariaDBベース（最初から）

**実装期間**: 2週間

**実装手順概要**:

```
ステップ1: MariaDB準備（既存環境影響: なし）
├─ 既存MariaDBコンテナに新規DB作成
├─ スキーマ作成（users, domains, audit_logs）
└─ 既存環境への影響: なし（独立したDB）

ステップ2: Flask Webアプリ開発（既存環境影響: なし）
├─ Docker統合（usermgmtコンテナ追加）
├─ CRUD API実装（MariaDB接続）
└─ 既存環境への影響: なし（新規コンテナ）

ステップ3: Dovecot SQL認証追加（⚠️ 既存環境変更）
├─ auth-sql.conf.ext作成
├─ dovecot.conf に !include 追加（File認証と並行）
├─ dovecot-sql.conf.ext作成（MariaDB接続設定）
└─ 既存環境への影響: Dovecot再起動必要（5秒程度）
    既存File認証ユーザは継続して認証可能（互換性維持）

ステップ4: 既存ユーザデータ移行（⚠️ データ整合性確認必要）
├─ /etc/dovecot/users → MariaDB移行スクリプト実行
├─ データ整合性検証
└─ 既存環境への影響: なし（File認証も並行稼働）
    移行後もFile認証ユーザは継続利用可能

ステップ5: Nginx統合（既存環境影響: 最小）
├─ /admin パス追加（既存 / パスはRoundcubeのまま）
└─ 既存環境への影響: Nginx reload のみ（ダウンタイムなし）
```

**既存環境への影響ポイント（重要）**:

| ステップ | 操作 | 既存環境への影響 | ダウンタイム | ロールバック方法 |
|---------|------|----------------|------------|----------------|
| **1. MariaDB DB作成** | `CREATE DATABASE mailserver_usermgmt` | **影響なし** | なし | `DROP DATABASE` |
| **2. Webアプリデプロイ** | `docker-compose up -d usermgmt` | **影響なし** | なし | `docker-compose stop usermgmt` |
| **3. Dovecot SQL認証追加** | dovecot.conf編集 + 再起動 | **Dovecot再起動（5秒）** | 5秒 | 設定ファイル戻す + 再起動 |
| **4. データ移行** | Pythonスクリプト実行 | **影響なし**（File認証並行） | なし | N/A（File認証継続可能） |
| **5. Nginx設定** | nginx reload | **影響なし** | なし | 設定ファイル戻す + reload |

**⚠️ 重要な安全策**:

1. **Dovecot認証の並行稼働**: File認証（`/etc/dovecot/users`）とSQL認証（MariaDB）を両方有効にする
   ```conf
   # dovecot.conf
   !include auth-passwdfile.conf.ext  # 既存File認証（継続）
   !include auth-sql.conf.ext         # 新規SQL認証（追加）
   ```
   → 既存ユーザ（File）も新規ユーザ（SQL）も両方認証可能

2. **段階的切り替え**: 既存ユーザをすぐに削除せず、SQL移行後もFileエントリを残す
   → 問題発生時はFileフォールバック可能

3. **バックアップ**: 各ステップ前に設定ファイルとDBをバックアップ

**検証基準**:
- ✅ 既存ユーザ（`test@kuma8088.com`, `info@kuma8088.com`）が移行後もログイン可能
- ✅ WebアプリからMariaDBへの新規ユーザ作成が即座にDovecotログイン可能
- ✅ パスワード変更が即座に反映
- ✅ ユーザ削除後にDovecotアクセス不可
- ✅ 監査ログで全操作が記録

---

### 8.2 代替実装方式: ファイルベース → MariaDB段階的移行

**実装期間**: 3週間（フェーズ1: 1週間、フェーズ2: 2週間）

**フェーズ1: ファイルベースMVP（1週間）**

**スコープ**:
- Flask Webアプリ基本実装（Dovecot usersファイル読み書き）
- ユーザCRUD操作（File直接編集）
- Docker統合

**既存環境への影響**: なし（Fileを直接編集するだけ）

**フェーズ2: MariaDB移行（2週間）**

**スコープ**:
- MariaDBスキーマ実装
- Dovecot SQL認証追加（File認証と並行）
- データ移行スクリプト
- 監査ログ実装

**既存環境への影響**: Dovecot再起動（5秒）、File認証並行稼働で互換性維持

**推奨しない理由**:
- フェーズ1のFile操作コードが無駄になる
- 移行フェーズで開発期間が1週間延びる
- 監査ログ機能がフェーズ2まで利用不可

---

### 8.3 高度な機能（将来拡張）

**実装期間**: 4週間（既存システム安定後）

**スコープ**:
- Tailscale OAuth統合
- ドメイン別管理者権限
- メールボックス使用量表示（quota実使用量）
- バルクユーザインポート（CSV）
- メール転送設定
- エイリアス管理

**既存環境への影響**: 最小（認証方式変更のみ、Dovecot設定変更なし）

---

## 9. 詳細実装手順（MariaDBベース推奨方式）

### 9.1 ステップ1: MariaDB準備（既存環境影響: なし）

**実施内容**: 新規データベース`mailserver_usermgmt`を作成

**手順**:
```bash
# 1. MariaDBコンテナに接続
docker exec -it mailserver-mariadb mysql -u root -p${MYSQL_ROOT_PASSWORD}

# 2. 新規データベース作成
CREATE DATABASE mailserver_usermgmt CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci;

# 3. アプリケーション用ユーザ作成
CREATE USER 'usermgmt'@'%' IDENTIFIED BY 'SecurePassword123!';
GRANT ALL PRIVILEGES ON mailserver_usermgmt.* TO 'usermgmt'@'%';
FLUSH PRIVILEGES;

# 4. テーブル作成
USE mailserver_usermgmt;

CREATE TABLE domains (
    id INT PRIMARY KEY AUTO_INCREMENT,
    name VARCHAR(255) UNIQUE NOT NULL,
    description VARCHAR(500),
    default_quota INT DEFAULT 1024,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,
    INDEX idx_name (name)
);

CREATE TABLE users (
    id INT PRIMARY KEY AUTO_INCREMENT,
    email VARCHAR(255) UNIQUE NOT NULL,
    domain_id INT NOT NULL,
    password_hash VARCHAR(255) NOT NULL,
    quota INT DEFAULT 1024,
    uid INT DEFAULT 5000,
    gid INT DEFAULT 5000,
    maildir VARCHAR(500) NOT NULL,
    enabled BOOLEAN DEFAULT TRUE,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,
    FOREIGN KEY (domain_id) REFERENCES domains(id) ON DELETE CASCADE,
    INDEX idx_email (email),
    INDEX idx_domain (domain_id)
);

CREATE TABLE audit_logs (
    id INT PRIMARY KEY AUTO_INCREMENT,
    action ENUM('create', 'update', 'delete', 'password_change') NOT NULL,
    user_email VARCHAR(255) NOT NULL,
    admin_ip VARCHAR(45) NOT NULL,
    details JSON,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    INDEX idx_user (user_email),
    INDEX idx_created (created_at)
);

EXIT;
```

**検証**:
```bash
docker exec mailserver-mariadb mysql -u usermgmt -p'SecurePassword123!' mailserver_usermgmt -e "SHOW TABLES;"
# 出力: domains, users, audit_logs
```

**既存環境への影響**: なし（独立したデータベース）

**ロールバック**:
```bash
docker exec -it mailserver-mariadb mysql -u root -p${MYSQL_ROOT_PASSWORD} \
  -e "DROP DATABASE mailserver_usermgmt; DROP USER 'usermgmt'@'%';"
```

---

### 9.2 ステップ2: Flask Webアプリ開発（既存環境影響: なし）

**実施内容**: Flaskアプリケーションのディレクトリ構造作成とDocker統合

**手順**:
```bash
cd /opt/onprem-infra-system/project-root-infra/services/mailserver

# 1. ディレクトリ構造作成
mkdir -p usermgmt/{app,config,templates,static}
mkdir -p usermgmt/app/{models,routes,services}

# 2. requirements.txt作成
cat > usermgmt/requirements.txt << 'EOF'
Flask==3.0.0
Flask-WTF==1.2.1
Flask-Login==0.6.3
passlib==1.7.4
SQLAlchemy==2.0.23
pymysql==1.1.0
python-dotenv==1.0.0
gunicorn==21.2.0
EOF

# 3. Dockerfile作成
cat > usermgmt/Dockerfile << 'EOF'
FROM python:3.11-slim

WORKDIR /app

RUN apt-get update && apt-get install -y curl && rm -rf /var/lib/apt/lists/*

COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

COPY app/ ./app/
COPY config/ ./config/

USER root

CMD ["gunicorn", "-w", "2", "-b", "0.0.0.0:5000", "app:app"]
EOF

# 4. docker-compose.yml に追加
cat >> docker-compose.yml << 'EOF'

  # User Management Web Application
  usermgmt:
    build:
      context: ./usermgmt
      dockerfile: Dockerfile
    container_name: mailserver-usermgmt
    hostname: usermgmt
    restart: always
    networks:
      mailserver_network:
        ipv4_address: 172.20.0.90
    environment:
      - TZ=${TZ}
      - DB_HOST=172.20.0.60
      - DB_PORT=3306
      - DB_NAME=mailserver_usermgmt
      - DB_USER=usermgmt
      - DB_PASSWORD=${USERMGMT_DB_PASSWORD}
      - ADMIN_USERNAME=${USERMGMT_ADMIN_USERNAME}
      - ADMIN_PASSWORD_HASH=${USERMGMT_ADMIN_PASSWORD_HASH}
      - SECRET_KEY=${USERMGMT_SECRET_KEY}
      - FLASK_ENV=production
    volumes:
      - ./logs/usermgmt:/var/log/usermgmt
      - ./data/usermgmt:/var/lib/usermgmt
    depends_on:
      - mariadb
      - dovecot
    healthcheck:
      test: ["CMD", "curl", "-f", "http://localhost:5000/health"]
      interval: 30s
      timeout: 10s
      retries: 3
      start_period: 40s
EOF

# 5. .env ファイルに環境変数追加
cat >> .env << 'EOF'

# User Management Application
USERMGMT_DB_PASSWORD=SecurePassword123!
USERMGMT_ADMIN_USERNAME=admin
USERMGMT_ADMIN_PASSWORD_HASH={SHA512-CRYPT}$6$...  # パスワードハッシュを生成
USERMGMT_SECRET_KEY=$(openssl rand -hex 32)
EOF
```

**Flask アプリケーション基本構造作成**:
```bash
# app/__init__.py
cat > usermgmt/app/__init__.py << 'EOF'
from flask import Flask
from flask_login import LoginManager
from flask_wtf.csrf import CSRFProtect
import os

app = Flask(__name__)
app.config['SECRET_KEY'] = os.getenv('SECRET_KEY')
app.config['SQLALCHEMY_DATABASE_URI'] = (
    f"mysql+pymysql://{os.getenv('DB_USER')}:{os.getenv('DB_PASSWORD')}"
    f"@{os.getenv('DB_HOST')}:{os.getenv('DB_PORT')}/{os.getenv('DB_NAME')}"
)

login_manager = LoginManager()
login_manager.init_app(app)
csrf = CSRFProtect(app)

from app import routes
EOF

# app/routes.py (簡易版)
cat > usermgmt/app/routes.py << 'EOF'
from flask import render_template, redirect, url_for
from flask_login import login_required
from app import app

@app.route('/health')
def health():
    return {'status': 'healthy'}, 200

@app.route('/')
@login_required
def dashboard():
    return render_template('dashboard.html')
EOF
```

**コンテナビルド・起動**:
```bash
docker-compose build usermgmt
docker-compose up -d usermgmt
```

**検証**:
```bash
docker ps | grep usermgmt
docker logs mailserver-usermgmt
curl http://172.20.0.90:5000/health
# 出力: {"status":"healthy"}
```

**既存環境への影響**: なし（新規コンテナ起動のみ）

**ロールバック**:
```bash
docker-compose stop usermgmt
docker-compose rm -f usermgmt
```

---

### 9.3 ステップ3: Dovecot SQL認証追加（⚠️ 既存環境変更）

**実施内容**: Dovecot設定にSQL認証を追加（File認証と並行稼働）

**⚠️ 注意**: このステップでDovecotの再起動が発生します（約5秒のダウンタイム）

**バックアップ**:
```bash
cd /opt/onprem-infra-system/project-root-infra/services/mailserver
cp config/dovecot/dovecot.conf config/dovecot/dovecot.conf.backup.$(date +%Y%m%d)
```

**手順**:
```bash
# 1. dovecot-sql.conf.ext 作成
cat > config/dovecot/dovecot-sql.conf.ext << 'EOF'
driver = mysql
connect = host=172.20.0.60 dbname=mailserver_usermgmt user=usermgmt password=SecurePassword123!

# パスワード認証クエリ
password_query = \
  SELECT email as user, password_hash as password, \
         '/var/mail/vhosts/%d/%n' as userdb_home, \
         uid, gid \
  FROM users WHERE email='%u' AND enabled=1

# ユーザ情報クエリ
user_query = \
  SELECT '/var/mail/vhosts/%d/%n' as home, \
         uid, gid \
  FROM users WHERE email='%u' AND enabled=1

# パスワードスキーム
default_pass_scheme = SHA512-CRYPT
EOF

# 2. auth-sql.conf.ext 作成
cat > config/dovecot/auth-sql.conf.ext << 'EOF'
passdb {
  driver = sql
  args = /etc/dovecot/custom/dovecot-sql.conf.ext
}

userdb {
  driver = sql
  args = /etc/dovecot/custom/dovecot-sql.conf.ext
}
EOF

# 3. dovecot.conf にSQL認証を追加
# 既存の auth-passwdfile.conf.ext の後に追加
sed -i '/!include auth-passwdfile.conf.ext/a !include auth-sql.conf.ext' config/dovecot/dovecot.conf
```

**設定確認**:
```bash
grep "!include auth" config/dovecot/dovecot.conf
# 出力:
# !include auth-passwdfile.conf.ext
# !include auth-sql.conf.ext
```

**Dovecot再起動**:
```bash
docker restart mailserver-dovecot

# 起動確認（30秒待機）
sleep 30
docker logs mailserver-dovecot --tail 50
```

**検証**:
```bash
# SQL認証設定の読み込み確認
docker exec mailserver-dovecot doveconf -c /etc/dovecot/custom/dovecot.conf | grep "auth-sql"
```

**⚠️ 既存環境への影響**:
- **ダウンタイム**: Dovecot再起動中の約5秒間、IMAPログイン不可
- **認証**: File認証（`/etc/dovecot/users`）は継続稼働、SQL認証も有効

**ロールバック**:
```bash
# dovecot.conf から SQL認証の行を削除
sed -i '/!include auth-sql.conf.ext/d' config/dovecot/dovecot.conf

# Dovecot再起動
docker restart mailserver-dovecot
```

---

### 9.4 ステップ4: 既存ユーザデータ移行（⚠️ データ整合性確認必要）

**実施内容**: `/etc/dovecot/users` → MariaDB移行

**移行スクリプト作成**:
```bash
cat > usermgmt/migrate_users.py << 'EOF'
#!/usr/bin/env python3
import mysql.connector
import os

# MariaDB接続
conn = mysql.connector.connect(
    host='172.20.0.60',
    database='mailserver_usermgmt',
    user='usermgmt',
    password='SecurePassword123!'
)
cursor = conn.cursor()

# 既存usersファイル読み取り
with open('/etc/dovecot/users', 'r') as f:
    for line in f:
        if not line.strip():
            continue

        parts = line.strip().split(':')
        email = parts[0]
        password_hash = parts[1]
        uid = int(parts[2])
        gid = int(parts[3])
        maildir = parts[5]

        # ドメイン抽出
        domain = email.split('@')[1]

        # ドメイン登録（存在しない場合）
        cursor.execute(
            "INSERT IGNORE INTO domains (name, description, default_quota) VALUES (%s, %s, %s)",
            (domain, f"{domain} domain", 1024)
        )
        conn.commit()

        # domain_id取得
        cursor.execute("SELECT id FROM domains WHERE name = %s", (domain,))
        domain_id = cursor.fetchone()[0]

        # ユーザ登録
        cursor.execute("""
            INSERT INTO users (email, domain_id, password_hash, quota, uid, gid, maildir, enabled)
            VALUES (%s, %s, %s, %s, %s, %s, %s, %s)
            ON DUPLICATE KEY UPDATE
                password_hash = VALUES(password_hash),
                maildir = VALUES(maildir)
        """, (email, domain_id, password_hash, 1024, uid, gid, maildir, True))

        print(f"Migrated: {email}")

conn.commit()
cursor.close()
conn.close()

print("Migration completed successfully!")
EOF

chmod +x usermgmt/migrate_users.py
```

**移行実行**:
```bash
# Dockerコンテナ内で実行
docker exec -it mailserver-dovecot python3 /opt/mailserver/migrate_users.py
```

**データ整合性検証**:
```bash
# MariaDBのユーザ数確認
docker exec mailserver-mariadb mysql -u usermgmt -p'SecurePassword123!' mailserver_usermgmt \
  -e "SELECT email, domain_id, enabled FROM users;"

# 既存usersファイルの行数と比較
wc -l config/dovecot/users
# 出力: 2行（test@kuma8088.com, info@kuma8088.com）

# MariaDBのレコード数
docker exec mailserver-mariadb mysql -u usermgmt -p'SecurePassword123!' mailserver_usermgmt \
  -e "SELECT COUNT(*) FROM users;"
# 出力: 2
```

**認証テスト**:
```bash
# SQL認証でログインテスト（test@kuma8088.comで既存パスワード使用）
docker exec mailserver-dovecot doveadm auth test test@kuma8088.com <password>
# 出力: passdb: test@kuma8088.com auth succeeded
```

**⚠️ 既存環境への影響**:
- **File認証**: 継続稼働（`/etc/dovecot/users`は削除しない）
- **SQL認証**: 移行したユーザはSQLでも認証可能
- **ダウンタイム**: なし

**ロールバック**:
```bash
# MariaDBのユーザデータ削除
docker exec mailserver-mariadb mysql -u usermgmt -p'SecurePassword123!' mailserver_usermgmt \
  -e "TRUNCATE TABLE users; TRUNCATE TABLE domains;"

# File認証は元々有効なので影響なし
```

---

### 9.5 ステップ5: Nginx統合（既存環境影響: 最小）

**実施内容**: Nginx設定に`/admin`パス追加

**バックアップ**:
```bash
cp config/nginx/templates/default.conf.template \
   config/nginx/templates/default.conf.template.backup.$(date +%Y%m%d)
```

**手順**:
```bash
cat > config/nginx/templates/usermgmt.conf.template << 'EOF'
# User Management Upstream
upstream usermgmt {
    server 172.20.0.90:5000;
}

# Tailscale IPアドレスチェック
geo $tailscale_ip {
    default 0;
    100.0.0.0/10 1;
}

server {
    listen 443 ssl http2;
    server_name ${MAIL_HOSTNAME};

    ssl_certificate ${TLS_CERT_FILE};
    ssl_certificate_key ${TLS_KEY_FILE};

    # User Management Admin Panel
    location /admin {
        if ($tailscale_ip = 0) {
            return 403 "Access denied. Tailscale VPN required.";
        }

        proxy_pass http://usermgmt;
        proxy_set_header Host $host;
        proxy_set_header X-Real-IP $remote_addr;
        proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for;
        proxy_set_header X-Forwarded-Proto $scheme;

        # Cookie設定
        proxy_cookie_path / "/; HttpOnly; Secure; SameSite=Strict";
    }

    # Existing Roundcube Configuration
    location / {
        proxy_pass http://roundcube;
        # ... 既存設定 ...
    }
}
EOF
```

**Nginx reload**:
```bash
docker exec mailserver-nginx nginx -t
docker exec mailserver-nginx nginx -s reload
```

**検証**:
```bash
# Tailscale VPN経由でアクセステスト（管理者デバイスから）
curl -k https://dell-workstation.tail67811d.ts.net/admin
# 出力: ログイン画面HTML

# Tailscale外からのアクセステスト（失敗することを確認）
curl -k https://<Public_IP>/admin
# 出力: 403 Forbidden
```

**⚠️ 既存環境への影響**:
- **ダウンタイム**: なし（nginx reloadは瞬時）
- **Roundcube**: 影響なし（`/`パスは従来通り）

**ロールバック**:
```bash
rm config/nginx/templates/usermgmt.conf.template
docker exec mailserver-nginx nginx -s reload
```

---

### 9.6 最終検証チェックリスト

**既存ユーザ認証確認**:
- [ ] `test@kuma8088.com` でIMAPログイン可能（File認証）
- [ ] `test@kuma8088.com` でIMAPログイン可能（SQL認証）
- [ ] `info@kuma8088.com` でIMAPログイン可能（File認証）
- [ ] `info@kuma8088.com` でIMAPログイン可能（SQL認証）

**Webアプリ動作確認**:
- [ ] https://dell-workstation.tail67811d.ts.net/admin にTailscale VPN経由でアクセス可能
- [ ] ログイン画面表示
- [ ] 管理者認証成功
- [ ] ダッシュボードでドメイン一覧表示

**新規ユーザ作成テスト**:
- [ ] Webアプリから`newuser@kuma8088.com`作成
- [ ] MariaDBにレコード登録確認
- [ ] 即座にIMAPログイン可能

**パスワード変更テスト**:
- [ ] Webアプリから既存ユーザのパスワード変更
- [ ] 新パスワードでIMAPログイン可能
- [ ] 旧パスワードでIMAPログイン不可

**監査ログ確認**:
- [ ] 全操作が`audit_logs`テーブルに記録されている

---

## 10. 運用設計

### 10.1 バックアップ戦略

**MariaDBベース**:
```bash
# 毎日のバックアップ（cron）
0 2 * * * cp /opt/onprem-infra-system/project-root-infra/services/mailserver/config/dovecot/users \
  /backup/dovecot-users-$(date +\%Y\%m\%d).txt
```

**MariaDBベース（フェーズ2）**:
```bash
# 毎日のDBダンプ
0 2 * * * docker exec mailserver-mariadb mysqldump -u root -p${MYSQL_ROOT_PASSWORD} \
  mailserver > /backup/mailserver-db-$(date +\%Y\%m\%d).sql
```

### 9.2 モニタリング

**ヘルスチェック**:
```python
@app.route('/health')
def health():
    """Docker healthcheck用エンドポイント"""
    try:
        # Dovecot usersファイル読み取り可能性チェック
        with open('/etc/dovecot/users', 'r') as f:
            pass

        return jsonify({'status': 'healthy'}), 200
    except Exception as e:
        return jsonify({'status': 'unhealthy', 'error': str(e)}), 503
```

**ログ監視**:
- アプリケーションログ: `/var/log/usermgmt/app.log`
- 監査ログ: `/var/log/usermgmt/audit.log`
- Nginxアクセスログ: `/var/log/nginx/usermgmt-access.log`

### 9.3 セキュリティ更新

**定期メンテナンス**:
- Pythonパッケージ更新: 月次
- Dockerイメージ更新: 月次
- セキュリティパッチ適用: 緊急時即座

**脆弱性スキャン**:
```bash
# requirements.txtの脆弱性チェック
pip-audit

# Dockerイメージスキャン
docker scan mailserver-usermgmt
```

---

## 10. 今後の拡張性

### 10.1 機能拡張候補

- **メールフィルタリングルール管理**: Sieve scriptをWebから設定
- **統計ダッシュボード**: ドメイン別メール送受信量グラフ
- **自動アカウント停止**: 未使用アカウントの自動無効化
- **2段階認証**: 管理画面アクセスにTOTP追加
- **REST API公開**: 外部システムからのユーザ管理自動化

### 10.2 スケーラビリティ

**マルチドメイン対応**:
- ドメイン別管理者権限（`admin@kuma8088.com`は`kuma8088.com`のみ管理）
- Virtual domain routing

**マルチテナント対応**:
- 組織単位でのメールサーバー分離
- ドメインごとの独立したquota管理

---

## 11. セキュリティチェックリスト

### 11.1 デプロイ前チェック

- [ ] 環境変数で秘密鍵設定（`.env`ファイルはgit管理外）
- [ ] HTTPS強制（HTTPアクセス不可）
- [ ] Tailscale IP以外からのアクセス拒否
- [ ] CSRFトークン検証有効
- [ ] パスワードハッシュ化（平文保存禁止）
- [ ] SQLインジェクション対策（パラメータ化クエリ）
- [ ] XSS対策（Jinja2自動エスケープ有効）
- [ ] ファイルアクセス権限適切（640, root:vmail）
- [ ] 監査ログ有効化

### 11.2 運用中チェック

- [ ] 定期的なパスワード変更（管理者パスワード）
- [ ] ログ監視（不正アクセス試行検出）
- [ ] バックアップ検証（リストア可能性確認）
- [ ] 依存ライブラリ脆弱性スキャン（月次）
- [ ] Tailscale認証キー更新（年次）

---

## 12. 関連ドキュメント

- **システム設計**: `02_design.md` (v6.0)
- **要件定義**: `01_requirements.md` (v6.0)
- **インストール手順**: `04_installation.md` (v6.0)
- **トラブルシューティング**: `../services/mailserver/troubleshoot/`
- **Docker Compose設定**: `../services/mailserver/docker-compose.yml`

---

## 13. 改訂履歴

| バージョン | 日付 | 変更内容 | 担当者 |
|-----------|------|---------|--------|
| 1.0 | 2025-11-04 | 初版作成 | システム管理者 |

