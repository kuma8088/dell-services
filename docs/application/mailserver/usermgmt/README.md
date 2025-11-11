# メールユーザ管理システム (Mail User Management)

**バージョン**: v0.5.0-dev (MVP開発中)
**更新日**: 2025-11-05
**ステータス**: 🚧 開発中 - Phase 1 完了 (MVP準備完了)

---

## 📋 概要

メールサーバーのユーザアカウントを Web インターフェースから管理するための Flask ベースの管理画面です。

### 開発方針：MVP → Extended

本プロジェクトは**段階的リリース**戦略を採用しています：

#### 🎯 MVP（最小実用製品）v0.5.0 - 現在開発中
- **目標**: 基本的なWeb UI経由でのユーザ管理機能
- **スコープ**: MariaDB + Flask + Bootstrap 5による管理画面
- **主要機能**:
  - ✉️ メールユーザの追加・編集・削除 (CRUD操作)
  - 🔐 パスワード設定・変更 (Dovecot互換SHA512-CRYPT)
  - 💾 メールボックス容量(quota)設定
  - 📊 シンプルなダッシュボード（ユーザ一覧）
  - 🔒 Flask-Login セッション認証
  - 📝 基本的な監査ログ（作成・更新・削除イベント）

#### 🚀 Extended（拡張構成）v1.0.0+ - MVP完了後
- **追加機能**:
  - 🏢 ドメイン別のユーザ管理・グルーピング表示
  - 🔄 Dovecot SQL認証統合（MariaDBから直接IMAP認証）
  - 🌐 Nginx `/admin` パス統合
  - 🔒 Tailscale VPN アクセス制限（geo ディレクティブ）
  - ✅ 包括的なテストスイート
  - 🏗️ docker-compose.yml 統合
  - 📦 バックアップ・ロールバック自動化

**技術スタック**:
- **Backend**: Flask 3.0, SQLAlchemy 2.0, Python 3.11+
- **Database**: MariaDB 10.11 (既存の `mailserver-mariadb` コンテナ利用)
- **Frontend**: Bootstrap 5.3, Jinja2 テンプレート
- **Security**: Flask-Login, Flask-WTF (CSRF保護)
- **Deployment**: Docker + Gunicorn

---

## 🏗️ アーキテクチャ

### MVP アーキテクチャ（v0.5.0）

```
┌─────────────────────────────────────────────────────────┐
│           ローカルネットワーク / Tailscale VPN            │
│                                                          │
│  管理者デバイス (PC/Mac/iPhone/Android)                  │
│         │ HTTP (開発中) / HTTPS (Extended)                │
│         ▼                                                │
│  ┌─────────────────┐                                    │
│  │  usermgmt       │ Flask + Gunicorn                    │
│  │  172.20.0.90    │ Port 5000                           │
│  │                 │ (直接アクセス - MVP)                 │
│  └────────┬────────┘                                    │
│           │                                              │
│           ▼                                              │
│  ┌─────────────────┐                                    │
│  │  MariaDB        │ mailserver_usermgmt データベース    │
│  │  172.20.0.60    │ users, audit_logs テーブル          │
│  └─────────────────┘                                    │
└─────────────────────────────────────────────────────────┘
```

### Extended アーキテクチャ（v1.0.0+）

```
┌─────────────────────────────────────────────────────────┐
│           Tailscale VPN ネットワーク (100.x.x.x/10)      │
│                                                          │
│  管理者デバイス (PC/Mac/iPhone/Android)                  │
│         │ HTTPS (443)                                    │
│         ▼                                                │
│  ┌─────────────────┐                                    │
│  │  Nginx Reverse  │ /admin パス (Extended)              │
│  │  Proxy          │ → usermgmt コンテナへプロキシ        │
│  │  + Tailscale    │   Tailscale IP アクセス制限          │
│  └────────┬────────┘                                    │
│           │                                              │
│           ▼                                              │
│  ┌─────────────────┐                                    │
│  │  usermgmt       │ Flask + Gunicorn                    │
│  │  172.20.0.90    │ Port 5000                           │
│  └────────┬────────┘                                    │
│           │                                              │
│           ▼                                              │
│  ┌─────────────────┐          ┌──────────────┐         │
│  │  MariaDB        │ ←────────│  Dovecot     │         │
│  │  172.20.0.60    │  SQL認証  │  (Extended)  │         │
│  └─────────────────┘          └──────────────┘         │
└─────────────────────────────────────────────────────────┘
```

**認証フロー（Extended）**:
1. Dovecot File認証 (`/etc/dovecot/users`) - 既存ユーザとの互換性維持
2. Dovecot SQL認証 (MariaDB) - 新規ユーザ管理方式
3. 両方の認証方式が並行稼働（段階的移行）

---

## 🚀 クイックスタート（MVP）

### 前提条件

- ✅ Docker および Docker Compose がインストール済み
- ✅ MariaDB コンテナ稼働中 (`mailserver-mariadb`)
- ✅ DB切り替え完了（メール送受信確認済み）
- ⏳ Python 3.11+ (ローカル開発の場合)

### セットアップ手順（MVP開発版）

#### 1. 環境変数設定

`.env` ファイルに以下を追加:

```bash
# User Management Application (MVP)
DB_HOST=172.20.0.60
DB_PORT=3306
DB_NAME=mailserver_usermgmt
DB_USER=usermgmt
DB_PASSWORD=<secure-password>
SECRET_KEY=<random-secret-key>

# Admin credentials (MVP - 初回セットアップ用)
ADMIN_EMAIL=admin@kuma8088.com
ADMIN_PASSWORD=<admin-password>
```

**SECRET_KEY生成**:
```bash
openssl rand -hex 32
```

#### 2. MariaDB データベース初期化

```bash
# MariaDB コンテナに接続
docker exec -it mailserver-mariadb mysql -u root -p

# データベースとユーザ作成
CREATE DATABASE IF NOT EXISTS mailserver_usermgmt CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci;
CREATE USER IF NOT EXISTS 'usermgmt'@'%' IDENTIFIED BY '<DB_PASSWORD>';
GRANT ALL PRIVILEGES ON mailserver_usermgmt.* TO 'usermgmt'@'%';
FLUSH PRIVILEGES;
```

#### 3. ローカル開発サーバー起動（MVP開発中）

```bash
cd /opt/onprem-infra-system/project-root-infra/services/mailserver/usermgmt

# Python 仮想環境作成
python3 -m venv venv
source venv/bin/activate

# 依存関係インストール
pip install -r requirements.txt

# 開発サーバー起動
export FLASK_ENV=development
export FLASK_APP=app.py
python app.py
```

#### 4. アクセス（MVP開発版）

ブラウザで以下の URL にアクセス:

```
http://172.20.0.90:5000/
http://localhost:5000/  # ローカル開発の場合
```

**注**: MVP では Nginx 統合前のため、直接 Flask アプリにアクセスします。Extended フェーズで Nginx `/admin` パス統合を実施予定。

---

## 📂 プロジェクト構造

### MVP フェーズ（Phase 0-5）で実装するファイル

```
services/mailserver/usermgmt/
├── app/
│   ├── __init__.py          # Flask アプリ初期化 (Phase 2)
│   ├── models/              # SQLAlchemy モデル (Phase 2)
│   │   ├── __init__.py
│   │   ├── user.py          # User モデル
│   │   └── audit_log.py     # AuditLog モデル（簡易版）
│   ├── routes/              # Flask ルート (Phase 3-4)
│   │   ├── __init__.py
│   │   ├── auth.py          # 認証ルート (login/logout)
│   │   └── users.py         # ユーザ管理ルート
│   └── services/            # ビジネスロジック (Phase 2-4)
│       ├── __init__.py
│       ├── database.py      # DB接続管理
│       ├── user_service.py  # ユーザ操作サービス
│       └── password.py      # パスワードハッシュ化
├── templates/               # Jinja2 テンプレート (Phase 5)
│   ├── base.html            # ベーステンプレート
│   ├── login.html           # ログイン画面
│   ├── dashboard.html       # ダッシュボード
│   └── users/
│       ├── list.html        # ユーザ一覧
│       ├── create.html      # ユーザ作成フォーム
│       └── edit.html        # ユーザ編集フォーム
├── static/                  # CSS/JS (Phase 5)
│   ├── css/
│   │   └── custom.css       # カスタムスタイル（最小限）
│   └── js/
│       └── validation.js    # フォームバリデーション
├── scripts/                 # 運用スクリプト (Phase 2)
│   └── init_db.py           # DB初期化
├── app.py                   # ✅ アプリケーションエントリポイント (Phase 0)
├── requirements.txt         # ✅ Python 依存関係 (Phase 0)
├── Dockerfile               # ✅ Docker イメージ定義 (Phase 0)
└── .env.example             # 環境変数サンプル (Phase 2)
```

### Extended フェーズ（Phase 6-10）で追加するファイル

```
services/mailserver/usermgmt/
├── app/
│   ├── models/
│   │   └── domain.py        # Domain モデル (Phase 6)
│   └── routes/
│       └── domains.py       # ドメイン管理ルート (Phase 6)
├── templates/
│   └── domains/
│       └── list.html        # ドメイン一覧 (Phase 6)
├── scripts/
│   └── migrate_users.py     # 既存ユーザ移行 (Phase 6)
├── tests/                   # テストコード (Phase 8)
│   ├── test_models.py
│   ├── test_routes.py
│   └── test_services.py
└── config/
    └── nginx_integration.conf  # Nginx 設定 (Phase 7)
```

### ドキュメント（Phase 1 完了）

```
docs/application/mailserver/usermgmt/
├── README.md                # ✅ 本ファイル
├── CHANGELOG.md             # ✅ 変更履歴
├── phases/                  # ✅ フェーズ記録
│   ├── PHASE11_COMPLETION.md
│   ├── PHASE11A_COMPLETION.md
│   ├── PHASE11_DEVELOPMENT.md
│   └── PHASE11_EXTENDED_FEATURES.md
├── guides/                  # ✅ ガイド類
│   ├── DEVELOPMENT.md       # 開発進捗トラッキング
│   ├── USER_GUIDE.md        # ユーザーガイド
│   ├── API.md               # API エンドポイント仕様
│   └── ROLLBACK.md          # ロールバック手順
└── design/                  # ✅ 設計ドキュメント
    ├── 05_user_management_design.md
    └── ADMIN_USER_ROLE_DESIGN.md
```

---

## 🔐 セキュリティ

### MVP セキュリティ（v0.5.0）

- **認証**: Flask-Login によるセッション管理
- **CSRF 保護**: Flask-WTF による CSRF トークン検証
- **パスワードハッシュ**: SHA512-CRYPT (Dovecot 互換)
- **セッションCookie**: HttpOnly, Secure（HTTPS時）
- **監査ログ**: 基本的な作成・更新・削除イベント記録

### Extended セキュリティ（v1.0.0+）

上記に加えて：
- **Tailscale VPN 必須**: `100.0.0.0/10` 範囲からのアクセスのみ許可（Nginx geo）
- **HTTPS 強制**: HTTP アクセスは自動的に HTTPS にリダイレクト
- **Nginx リバースプロキシ**: `/admin` パス経由のみアクセス可能
- **包括的な監査ログ**: IP アドレス、User-Agent、操作詳細を記録

### パスワードセキュリティ（共通）

- **ハッシュ方式**: SHA512-CRYPT (Dovecot 互換)
- **パスワードポリシー** (MVP では推奨、Extended で強制):
  - 最小長: 8文字
  - 複雑性: 英大文字、英小文字、数字、記号のうち3種類以上
- **平文保存禁止**: データベースには必ずハッシュ化されたパスワードのみ保存

---

## 🛠️ 開発

### 開発環境セットアップ

```bash
# リポジトリクローン
cd /opt/onprem-infra-system/project-root-infra/services/mailserver/usermgmt

# Python 仮想環境作成
python3 -m venv venv
source venv/bin/activate

# 依存関係インストール
pip install -r requirements.txt

# 環境変数設定
cp .env.example .env
# .env ファイルを編集

# 開発サーバー起動
export FLASK_ENV=development
export FLASK_APP=app.py
python app.py
```

### テスト実行（Extended フェーズ）

```bash
# ユニットテスト
pytest tests/

# カバレッジレポート
pytest --cov=app tests/

# 統合テスト
pytest tests/integration/
```

### 開発進捗の確認

開発の進捗状況は `DEVELOPMENT.md` で管理しています。

**現在の進捗**:
- ✅ Phase 0: プロジェクト初期化完了
- ✅ Phase 1: ドキュメント整備完了（MVP/Extended分離）
- ⏳ Phase 2: データベース基盤構築（未着手）
- ⏳ Phase 3-5: MVP実装（未着手）
- ⏳ Phase 6-10: Extended拡張（MVP完了後）

---

## 📚 関連ドキュメント

**ガイド:**
- [開発進捗](guides/DEVELOPMENT.md) - MVP/Extended フェーズ管理
- [ユーザーガイド](guides/USER_GUIDE.md) - 管理画面の使い方
- [API仕様](guides/API.md) - エンドポイント仕様
- [ロールバック手順](guides/ROLLBACK.md) - 復旧手順

**設計:**
- [ユーザー管理設計](design/05_user_management_design.md)
- [管理者ロール設計](design/ADMIN_USER_ROLE_DESIGN.md)

**フェーズ記録:**
- [Phase 11完了報告](phases/PHASE11_COMPLETION.md)
- [Phase 11-A完了報告](phases/PHASE11A_COMPLETION.md)
- [Phase 11開発記録](phases/PHASE11_DEVELOPMENT.md)
- [Phase 11拡張機能](phases/PHASE11_EXTENDED_FEATURES.md)

**その他:**
- [変更履歴](CHANGELOG.md)
- [Mailserver概要](../README.md)

---

## 🐛 トラブルシューティング

### コンテナが起動しない（Extended フェーズ）

```bash
# ログ確認
docker logs mailserver-usermgmt

# MariaDB 接続テスト
docker exec mailserver-usermgmt python3 -c "
from app.services.database import db_engine
print('DB connection OK' if db_engine else 'DB connection failed')
"
```

### ログインできない

- `.env` ファイルの `ADMIN_EMAIL` と `ADMIN_PASSWORD` が正しく設定されているか確認
- パスワードハッシュは `{SHA512-CRYPT}` プレフィックスが必要（Extended フェーズ）

### MariaDB 接続エラー

```bash
# MariaDB コンテナ稼働確認
docker ps | grep mailserver-mariadb

# DB接続テスト
docker exec -it mailserver-mariadb mysql -u usermgmt -p -h 172.20.0.60 -e "SELECT 1"
```

### Tailscale VPN 経由でアクセスできない（Extended フェーズ）

- Nginx の geo ディレクティブで `100.0.0.0/10` が許可されているか確認
- Tailscale 接続ステータスを確認: `tailscale status`

---

## 🎯 MVP 完了条件

以下の条件を満たした時点で MVP v0.5.0 をリリース:

- ✅ Webブラウザから管理画面にアクセス可能
- ✅ ログイン認証が機能している
- ✅ ユーザの新規作成・編集・削除が可能
- ✅ MariaDBに変更が永続化されている
- ✅ 基本的なUI（Bootstrap 5）が動作している（PC/スマホ対応）
- ✅ 簡易な監査ログ（作成・更新・削除イベント）

---

## 📝 ライセンス

このプロジェクトは内部利用専用です。

---

## 👥 メンテナ

- システム管理者 (system-admin)

---

## 🔗 リンク

- **プロジェクトルート**: `/opt/onprem-infra-system/project-root-infra`
- **Mailserver サービス**: `services/mailserver/`
- **ドキュメント**: `docs/application/mailserver/`
- **開発進捗**: `DEVELOPMENT.md` ← **MVP/Extended フェーズ管理**
