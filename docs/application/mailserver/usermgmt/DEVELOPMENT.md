# 開発進捗トラッキング (Development Progress)

**最終更新**: 2025-11-05
**現在のフェーズ**: Phase 1 - ドキュメント整備（MVP準備）
**全体進捗**: MVP 20% (2/10 フェーズ完了)

---

## 📊 開発方針

### MVP（最小構成）とExtended（拡張構成）の分離

本プロジェクトは**段階的リリース**戦略を採用します：

**MVP（最小実用製品）- v0.5.0**
- 🎯 **目標**: 基本的なWeb UI経由でのユーザ管理機能を提供
- 📦 **スコープ**: MariaDB + Flask + Bootstrap 5による管理画面
- 🔐 **認証**: Flask-Login によるセッション管理
- 📝 **データ永続化**: MariaDB (`mailserver_usermgmt` データベース)
- ⚡ **リリース時期**: Phase 1-5 完了後

**Extended（拡張構成）- v1.0.0+**
- 🔄 **追加機能**: Dovecot SQL認証統合、Nginx統合、高度なテスト
- 🏗️ **インフラ統合**: docker-compose統合、バックアップ自動化
- 📊 **モニタリング**: 監査ログ、パフォーマンス最適化
- 🚀 **リリース時期**: MVP安定稼働後

---

## 🎯 MVPロードマップ（最小構成 v0.5.0）

| Phase | タスク | ステータス | 開始日 | 完了日 | 担当者 |
|-------|--------|----------|--------|--------|--------|
| **Phase 0** | プロジェクト初期化 | ✅ 完了 | 2025-11-04 | 2025-11-04 | system-admin |
| **Phase 1** | ドキュメント整備 | ✅ 完了 | 2025-11-05 | 2025-11-05 | system-admin |
| **Phase 2** | データベース基盤構築 | ⏳ 未着手 | - | - | - |
| **Phase 3** | 認証システム実装 | ⏳ 未着手 | - | - | - |
| **Phase 4** | ユーザCRUD機能実装 | ⏳ 未着手 | - | - | - |
| **Phase 5** | UI/テンプレート実装 | ⏳ 未着手 | - | - | - |

**MVP完了条件**:
- ✅ Tailscale VPN経由でWebブラウザからアクセス可能
- ✅ ログイン認証が機能している
- ✅ ユーザの新規作成・編集・削除が可能
- ✅ MariaDBに変更が永続化されている
- ✅ 基本的なUI（Bootstrap 5）が動作している

---

## 🚀 Extendedロードマップ（拡張構成 v1.0.0）

| Phase | タスク | ステータス | 開始日 | 完了日 | 担当者 |
|-------|--------|----------|--------|--------|--------|
| **Phase 6** | Dovecot SQL認証統合 | ⏳ MVP後 | - | - | - |
| **Phase 7** | Nginx統合 | ⏳ MVP後 | - | - | - |
| **Phase 8** | テスト・検証 | ⏳ MVP後 | - | - | - |
| **Phase 9** | 本番デプロイ準備 | ⏳ MVP後 | - | - | - |
| **Phase 10** | 本番リリース | ⏳ MVP後 | - | - | - |

**Extended完了条件**:
- ✅ DovecotがMariaDBから直接認証可能
- ✅ Nginx `/admin` パス統合完了
- ✅ 包括的なテストスイート整備
- ✅ docker-compose.yml統合
- ✅ バックアップ・ロールバック手順確立

---

# 📋 MVP フェーズ詳細（Phase 0-5）

## Phase 0: プロジェクト初期化 ✅

**期間**: 2025-11-04
**ステータス**: 完了

### タスク一覧

- [x] ディレクトリ構造作成 (`app/`, `templates/`, `static/`, `config/`)
- [x] `requirements.txt` 作成 (Flask, SQLAlchemy, Flask-Login等)
- [x] `Dockerfile` 作成 (Python 3.11-slim ベース)
- [x] 基本的な `app.py` 実装 (health エンドポイント)
- [x] `.gitignore` 設定

### 成果物

- `app.py` - 最小構成のFlaskアプリケーション
- `requirements.txt` - 依存関係定義
- `Dockerfile` - コンテナ化設定
- ディレクトリ構造完成

### 課題・メモ

- MariaDB接続設定は環境変数で管理
- Docker healthcheck は `/health` エンドポイント使用

---

## Phase 1: ドキュメント整備 ✅

**期間**: 2025-11-05
**ステータス**: 完了

### タスク一覧

- [x] `README.md` 作成 - プロジェクト概要、セットアップ手順
- [x] `DEVELOPMENT.md` 作成 - 開発進捗トラッキング (本ファイル)
- [x] `API.md` 作成 - API エンドポイント仕様
- [x] `CHANGELOG.md` 作成 - 変更履歴
- [x] MVP/Extended フェーズ分離

### 成果物

- `README.md` - プロジェクトの全体像、アーキテクチャ、セットアップ手順
- `DEVELOPMENT.md` - MVP/Extendedフェーズ別進捗管理
- `API.md` - RESTful API 仕様書（MVP/Extended分離）
- `CHANGELOG.md` - バージョン管理と変更履歴

### 課題・メモ

- ドキュメントは開発進行に伴い継続的に更新
- 設計書 (`05_user_management_design.md`) との整合性維持
- MVP完了後にExtendedフェーズへ移行

---

## Phase 2: データベース基盤構築 ⏳

**期間**: 未定
**ステータス**: 未着手
**見積もり**: 2-3時間
**優先度**: 🔴 高（MVP必須）

### 前提条件

- ✅ MariaDB コンテナ稼働中 (`mailserver-mariadb`)
- ✅ DB切り替え完了（メール送受信確認済み）
- ⏳ `.env` ファイルに `USERMGMT_DB_PASSWORD` 設定

### タスク一覧

- [ ] `app/services/database.py` - SQLAlchemy 初期化、DB接続管理
- [ ] `app/models/user.py` - User モデル定義
- [ ] `app/models/domain.py` - Domain モデル定義（簡易版）
- [ ] `app/models/audit_log.py` - AuditLog モデル定義（簡易版）
- [ ] `scripts/init_db.py` - MariaDB スキーマ作成スクリプト
- [ ] DB接続テスト

### 成果物 (予定)

```python
# User モデル（MVP最小構成）
class User(db.Model):
    __tablename__ = 'users'

    email = Column(String(255), primary_key=True)
    password_hash = Column(String(255), nullable=False)
    maildir = Column(String(255), nullable=False)
    quota = Column(Integer, default=1024)
    enabled = Column(Boolean, default=True)
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
```

### 技術メモ

```python
# SQLAlchemy 設定例
SQLALCHEMY_DATABASE_URI = f"mysql+pymysql://{DB_USER}:{DB_PASSWORD}@{DB_HOST}:{DB_PORT}/{DB_NAME}"
SQLALCHEMY_TRACK_MODIFICATIONS = False
SQLALCHEMY_POOL_SIZE = 5
SQLALCHEMY_POOL_RECYCLE = 3600
```

---

## Phase 3: 認証システム実装 ⏳

**期間**: 未定
**ステータス**: 未着手
**見積もり**: 2-3時間
**優先度**: 🔴 高（MVP必須）

### 前提条件

- ✅ Phase 2 (データベース基盤) 完了

### タスク一覧

- [ ] Flask-Login 統合
- [ ] `app/routes/auth.py` - ログイン/ログアウトルート
- [ ] `app/services/password.py` - パスワードハッシュ化 (SHA512-CRYPT)
- [ ] `templates/login.html` - ログイン画面（Bootstrap 5）
- [ ] セッション管理 (Cookie設定)
- [ ] CSRF 保護 (Flask-WTF)
- [ ] 認証デコレータ (`@login_required`)

### 成果物 (予定)

```python
# パスワードハッシュ化
from passlib.hash import sha512_crypt

def hash_password(password: str) -> str:
    """Dovecot互換SHA512-CRYPTハッシュ生成"""
    return "{SHA512-CRYPT}" + sha512_crypt.hash(password)

def verify_password(password: str, hash: str) -> bool:
    """パスワード検証"""
    hash_value = hash.replace("{SHA512-CRYPT}", "")
    return sha512_crypt.verify(password, hash_value)
```

### 検証項目

- [ ] ログイン成功時にセッションCookieが設定される
- [ ] ログアウト時にセッションが破棄される
- [ ] `@login_required` デコレータが未認証アクセスをブロック

---

## Phase 4: ユーザCRUD機能実装 ⏳

**期間**: 未定
**ステータス**: 未着手
**見積もり**: 4-5時間
**優先度**: 🔴 高（MVP必須）

### 前提条件

- ✅ Phase 2 (データベース基盤) 完了
- ✅ Phase 3 (認証システム) 完了

### タスク一覧

- [ ] `app/routes/users.py` - ユーザ管理ルート
- [ ] `app/services/user_service.py` - ユーザ操作ビジネスロジック
- [ ] ユーザ一覧表示 (`GET /users`)
- [ ] ユーザ作成 (`POST /users/new`)
- [ ] ユーザ編集 (`POST /users/<email>/edit`)
- [ ] ユーザ削除 (`POST /users/<email>/delete`)
- [ ] パスワード変更 (`POST /users/<email>/password`)
- [ ] 基本的な監査ログ記録（作成・更新・削除イベント）

### 成果物 (予定)

```python
# ユーザ作成例（MVP最小構成）
@app.route('/users/new', methods=['POST'])
@login_required
def create_user():
    email = request.form['email']
    password = request.form['password']
    quota = int(request.form.get('quota', 1024))

    # maildir自動生成
    domain = email.split('@')[1]
    username = email.split('@')[0]
    maildir = f"/var/mail/vmail/{domain}/{username}/"

    # ユーザ作成
    user = User(
        email=email,
        password_hash=hash_password(password),
        maildir=maildir,
        quota=quota,
        enabled=True
    )

    db.session.add(user)
    db.session.commit()

    flash(f'ユーザ {email} を作成しました', 'success')
    return redirect(url_for('users.list'))
```

### 検証項目

- [ ] ユーザ作成後、MariaDBに反映される
- [ ] ユーザ編集後、変更が永続化される
- [ ] ユーザ削除後、DBから削除される
- [ ] パスワード変更後、新パスワードでログイン可能

---

## Phase 5: UI/テンプレート実装 ⏳

**期間**: 未定
**ステータス**: 未着手
**見積もり**: 3-4時間
**優先度**: 🔴 高（MVP必須）

### 前提条件

- ✅ Phase 4 (ユーザCRUD機能) 完了

### タスク一覧

- [ ] `templates/base.html` - ベーステンプレート (Bootstrap 5)
- [ ] `templates/dashboard.html` - ダッシュボード（ユーザ数表示）
- [ ] `templates/users/list.html` - ユーザ一覧
- [ ] `templates/users/create.html` - ユーザ作成フォーム
- [ ] `templates/users/edit.html` - ユーザ編集フォーム
- [ ] `static/css/custom.css` - カスタムスタイル（最小限）
- [ ] `static/js/validation.js` - フォームバリデーション
- [ ] レスポンシブデザイン対応 (モバイル/タブレット)

### 成果物 (予定)

**base.html テンプレート構成**:
```html
<!DOCTYPE html>
<html lang="ja">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>{% block title %}メールユーザ管理{% endblock %}</title>
    <link href="https://cdn.jsdelivr.net/npm/bootstrap@5.3.0/dist/css/bootstrap.min.css" rel="stylesheet">
    <link href="{{ url_for('static', filename='css/custom.css') }}" rel="stylesheet">
</head>
<body>
    <nav class="navbar navbar-expand-lg navbar-dark bg-primary">
        <div class="container-fluid">
            <a class="navbar-brand" href="/">メールユーザ管理</a>
            <div class="navbar-nav ms-auto">
                <a class="nav-link" href="{{ url_for('auth.logout') }}">ログアウト</a>
            </div>
        </div>
    </nav>

    <div class="container mt-4">
        {% with messages = get_flashed_messages(with_categories=true) %}
            {% for category, message in messages %}
                <div class="alert alert-{{ category }}">{{ message }}</div>
            {% endfor %}
        {% endwith %}

        {% block content %}{% endblock %}
    </div>

    <script src="https://cdn.jsdelivr.net/npm/bootstrap@5.3.0/dist/js/bootstrap.bundle.min.js"></script>
    <script src="{{ url_for('static', filename='js/validation.js') }}"></script>
</body>
</html>
```

### デザインガイドライン（MVP最小構成）

- **カラースキーム**: Bootstrap 5 デフォルト
- **フォント**: システムフォント (游ゴシック、Segoe UI)
- **アイコン**: Bootstrap Icons（CDN経由）
- **レイアウト**: シンプルなトップナビゲーション

### 検証項目

- [ ] PC/Mac/スマートフォンで画面表示確認
- [ ] フォーム送信でバリデーションエラーが表示される
- [ ] Flashメッセージが正しく表示される

---

# 🚀 Extended フェーズ詳細（Phase 6-10）

## Phase 6: Dovecot SQL認証統合 ⏳

**期間**: MVP完了後
**ステータス**: MVP後
**見積もり**: 2-3時間
**優先度**: 🟡 中（Extended拡張）

### 前提条件

- ✅ MVP (Phase 1-5) 完了
- ✅ MariaDB に users テーブル存在
- ✅ Webアプリからユーザ作成可能

### タスク一覧

- [ ] `dovecot-sql.conf.ext` 作成 (MariaDB接続設定)
- [ ] `auth-sql.conf.ext` 作成 (SQL認証設定)
- [ ] `dovecot.conf` に `!include auth-sql.conf.ext` 追加
- [ ] Dovecot 再起動
- [ ] SQL認証テスト (既存ユーザでIMAPログイン)
- [ ] File認証とSQL認証の並行稼働確認

### ⚠️ 注意事項

- Dovecot 再起動時に約5秒のダウンタイムが発生
- 既存の File認証 (`/etc/dovecot/users`) は継続稼働

### 検証項目

```bash
# SQL認証テスト
docker exec mailserver-dovecot doveadm auth test test@kuma8088.com <password>
# 期待される出力: passdb: test@kuma8088.com auth succeeded
```

---

## Phase 7: Nginx統合 ⏳

**期間**: MVP完了後
**ステータス**: MVP後
**見積もり**: 1-2時間
**優先度**: 🟡 中（Extended拡張）

### 前提条件

- ✅ MVP (Phase 1-5) 完了
- ✅ usermgmt コンテナ稼働中

### タスク一覧

- [ ] Nginx 設定ファイル編集 (`config/nginx/templates/mailserver.conf.template`)
- [ ] `/admin` パス追加 (usermgmt コンテナへプロキシ)
- [ ] Tailscale IP アドレスチェック (`geo $tailscale_ip`)
- [ ] HTTPS 強制リダイレクト
- [ ] Cookie 設定 (HttpOnly, Secure, SameSite)
- [ ] Nginx reload
- [ ] アクセステスト (Tailscale VPN 経由)

### 検証項目

```bash
# Tailscale VPN 経由でアクセス
curl -k https://dell-workstation.tail67811d.ts.net/admin
# 期待される出力: ログイン画面 HTML

# Tailscale 外からのアクセス (失敗することを確認)
curl -k https://<Public_IP>/admin
# 期待される出力: 403 Forbidden
```

---

## Phase 8: テスト・検証 ⏳

**期間**: MVP完了後
**ステータス**: MVP後
**見積もり**: 2-3時間
**優先度**: 🟢 低（Extended拡張）

### タスク一覧

- [ ] ユニットテスト作成 (`tests/`)
  - [ ] `test_models.py` - モデルテスト
  - [ ] `test_routes.py` - ルートテスト
  - [ ] `test_services.py` - サービスロジックテスト
- [ ] 統合テスト
  - [ ] ユーザ作成 → IMAP ログインテスト
  - [ ] パスワード変更 → IMAP ログインテスト
  - [ ] ユーザ削除 → IMAP ログイン失敗テスト
- [ ] セキュリティテスト
  - [ ] CSRF 保護確認
  - [ ] SQLインジェクション対策確認
  - [ ] XSS 対策確認

---

## Phase 9: 本番デプロイ準備 ⏳

**期間**: MVP完了後
**ステータス**: MVP後
**見積もり**: 2時間
**優先度**: 🟡 中（Extended拡張）

### タスク一覧

- [ ] docker-compose.yml に usermgmt サービス追加
- [ ] 環境変数設定 (`.env` ファイル)
- [ ] バックアップスクリプト作成
- [ ] ロールバック手順書作成
- [ ] モニタリング設定 (ログ監視)

---

## Phase 10: 本番リリース ⏳

**期間**: MVP完了後
**ステータス**: MVP後
**見積もり**: 1時間
**優先度**: 🟢 低（Extended拡張）

### 最終検証チェックリスト

- [ ] 既存ユーザ (test@kuma8088.com) でIMAPログイン可能
- [ ] Webアプリから新規ユーザ作成可能
- [ ] 作成したユーザで即座にIMAPログイン可能
- [ ] パスワード変更後、新パスワードでログイン可能
- [ ] ユーザ削除後、IMAPログイン不可
- [ ] 監査ログに全操作が記録されている
- [ ] Tailscale VPN 外からのアクセスが拒否される

---

## 🐛 既知の課題 (Known Issues)

現時点で既知の課題はありません。

---

## 📝 開発メモ

### 技術的な決定事項

1. **MVP/Extended分離方針**
   - MVP: Web管理画面の基本機能に集中（Phase 1-5）
   - Extended: Dovecot統合、Nginx統合、包括的テスト（Phase 6-10）
   - 理由: 段階的リリースによるリスク低減、早期フィードバック取得

2. **データベース**: MariaDB ベースのアプローチを採用
   - 理由: 監査ログ、検索機能、将来拡張を考慮
   - 現状: DB切り替え完了、メール送受信確認済み

3. **認証方式（MVP）**: Flask-Login によるセッション管理
   - 理由: シンプル、Python標準、迅速な開発
   - Extended: Tailscale OAuth統合を検討

4. **UI フレームワーク**: Bootstrap 5
   - 理由: レスポンシブデザイン対応、モバイルデバイス管理に最適

5. **パスワードハッシュ**: SHA512-CRYPT
   - 理由: Dovecot 標準方式、既存環境との互換性

### MVPリリース基準

以下の条件を満たした時点でMVP v0.5.0をリリース:
- ✅ Webブラウザから管理画面にログイン可能
- ✅ ユーザの追加・編集・削除が動作
- ✅ MariaDBへの変更が永続化
- ✅ 基本的なUIが動作（PC/スマホ対応）
- ✅ 簡易な監査ログ（作成・更新・削除イベント）

### Extendedリリース基準

MVP安定稼働後、以下を追加してv1.0.0をリリース:
- ✅ Dovecot SQL認証統合
- ✅ Nginx `/admin` パス統合
- ✅ 包括的なテストスイート
- ✅ docker-compose.yml統合
- ✅ バックアップ・ロールバック手順

---

## 📅 次回のレビュー

**MVP Phase 2 開始前レビュー**:
- データベーススキーマの妥当性確認
- モデル定義の設計レビュー
- 環境変数設定の確認

**MVP完了後レビュー**:
- Web管理画面の動作確認
- MariaDB永続化確認
- Extendedフェーズへの移行判断

---

## 📞 連絡先

**開発担当**: system-admin
**レビュー担当**: system-admin
**質問・相談**: Tailscale VPN 経由で連絡
