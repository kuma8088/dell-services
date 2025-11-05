# テスト仕様書: Flask-Login統合

**対象フェーズ**: Phase 3 - 認証システム実装
**対象コンポーネント**: Flask-Login統合、Userモデル、セッション管理
**作成日**: 2025-11-05
**優先度**: 🔴 高 (MVP必須)

---

## 1. テスト目的

Flask-Login統合が正しく動作し、以下の機能を提供することを検証する：
- Userモデルが Flask-Login の UserMixin を継承している
- LoginManager が正しく初期化されている
- user_loader コールバックが動作する
- セッション管理が正しく機能する

---

## 2. テスト対象機能

### 2.1 Userモデル (app/models/user.py)
- SQLAlchemy モデル定義
- Flask-Login UserMixin 継承
- 必須メソッド実装:
  - `get_id()`: ユーザーID取得
  - `is_authenticated`: 認証状態
  - `is_active`: アクティブ状態
  - `is_anonymous`: 匿名ユーザー判定

### 2.2 Flask-Login初期化 (app/__init__.py)
- LoginManager インスタンス作成
- `login_view` 設定
- `session_protection` 設定
- `user_loader` コールバック登録

### 2.3 セッション管理
- Cookie設定 (HttpOnly, Secure, SameSite)
- セッション有効期限
- Remember Me 機能

---

## 3. テストケース一覧

### TC-FL-001: Userモデル基本機能テスト
**目的**: Userモデルが正しく定義されていることを検証
**前提条件**: データベース接続が正常
**テストデータ**:
```python
test_user = {
    'email': 'test@example.com',
    'password_hash': '{SHA512-CRYPT}$6$test',
    'domain_id': 1,
    'maildir': '/var/mail/vmail/example.com/test/',
    'enabled': True
}
```

**テスト手順**:
1. Userモデルインスタンスを作成
2. 各属性が正しく設定されることを確認
3. データベースへの保存と取得を確認

**期待結果**:
- ✅ User インスタンスが作成される
- ✅ email, password_hash, maildir が正しく設定される
- ✅ enabled デフォルト値が True

---

### TC-FL-002: UserMixin統合テスト
**目的**: Flask-Login UserMixin が正しく動作することを検証
**前提条件**: Userモデルが UserMixin を継承
**テストデータ**: TC-FL-001 と同じ

**テスト手順**:
1. User インスタンスを作成
2. `is_authenticated` が True を返すことを確認
3. `is_active` が enabled=True の場合 True を返すことを確認
4. `is_anonymous` が False を返すことを確認
5. `get_id()` が user.id を返すことを確認

**期待結果**:
- ✅ `user.is_authenticated` == True
- ✅ `user.is_active` == True (enabled=True の場合)
- ✅ `user.is_active` == False (enabled=False の場合)
- ✅ `user.is_anonymous` == False
- ✅ `user.get_id()` == str(user.id)

---

### TC-FL-003: LoginManager初期化テスト
**目的**: LoginManager が正しく設定されることを検証
**前提条件**: Flask app が初期化されている

**テスト手順**:
1. Flask app を作成
2. LoginManager を初期化
3. login_view が設定されていることを確認
4. session_protection が設定されていることを確認

**期待結果**:
- ✅ LoginManager インスタンスが作成される
- ✅ `login_manager.login_view` == 'auth.login'
- ✅ `login_manager.session_protection` == 'strong'
- ✅ `login_manager.login_message` が設定されている

---

### TC-FL-004: user_loader コールバックテスト
**目的**: user_loader が正しくユーザーを読み込むことを検証
**前提条件**:
- データベースにテストユーザーが存在
- LoginManager が初期化されている

**テストデータ**:
```python
test_user_id = 1  # 既存ユーザーID
invalid_user_id = 99999  # 存在しないユーザーID
```

**テスト手順**:
1. 有効なuser_idでuser_loaderを呼び出す
2. Userインスタンスが返されることを確認
3. 無効なuser_idでuser_loaderを呼び出す
4. None が返されることを確認

**期待結果**:
- ✅ load_user(valid_id) が User インスタンスを返す
- ✅ load_user(invalid_id) が None を返す
- ✅ 返されたUserの属性が正しい

---

### TC-FL-005: セッションCookie設定テスト
**目的**: セッションCookieが正しく設定されることを検証
**前提条件**: Flask app が初期化されている

**テスト手順**:
1. Flask app の設定を確認
2. SESSION_COOKIE_HTTPONLY が True であることを確認
3. SESSION_COOKIE_SECURE が True であることを確認
4. SESSION_COOKIE_SAMESITE が 'Strict' であることを確認
5. PERMANENT_SESSION_LIFETIME が設定されていることを確認

**期待結果**:
- ✅ `app.config['SESSION_COOKIE_HTTPONLY']` == True
- ✅ `app.config['SESSION_COOKIE_SECURE']` == True
- ✅ `app.config['SESSION_COOKIE_SAMESITE']` == 'Strict'
- ✅ `app.config['PERMANENT_SESSION_LIFETIME']` が設定されている (例: 3600秒)

---

### TC-FL-006: ログインセッション永続化テスト
**目的**: Remember Me 機能が動作することを検証
**前提条件**:
- LoginManager が初期化されている
- テストユーザーが存在

**テスト手順**:
1. remember=True でログイン
2. セッションCookieの有効期限が長期間であることを確認
3. remember=False でログイン
4. セッションCookieがブラウザセッションのみであることを確認

**期待結果**:
- ✅ remember=True の場合、Cookie有効期限が設定される
- ✅ remember=False の場合、Cookie有効期限がセッションのみ

---

## 4. テスト環境

### 4.1 テストデータベース
- **接続先**: 172.20.0.60:3306 (MariaDB 10.11.7)
- **データベース**: `mailserver_usermgmt_test` (テスト専用)
- **テーブル**: `users`, `domains`, `audit_logs`

### 4.2 テストユーザー
```python
TEST_USERS = [
    {
        'id': 1,
        'email': 'testuser1@example.com',
        'password_hash': '{SHA512-CRYPT}$6$rounds=5000$test',
        'domain_id': 1,
        'maildir': '/var/mail/vmail/example.com/testuser1/',
        'enabled': True
    },
    {
        'id': 2,
        'email': 'testuser2@example.com',
        'password_hash': '{SHA512-CRYPT}$6$rounds=5000$test2',
        'domain_id': 1,
        'maildir': '/var/mail/vmail/example.com/testuser2/',
        'enabled': False  # 無効化ユーザー
    }
]
```

---

## 5. 成功基準

すべてのテストケース (TC-FL-001 ~ TC-FL-006) が成功すること:
- ✅ Userモデルが正しく動作する
- ✅ Flask-Login統合が正しく機能する
- ✅ セッション管理が安全に設定されている
- ✅ user_loader が正しくユーザーを読み込む

---

## 6. テスト実行方法

```bash
# テストディレクトリに移動
cd /opt/onprem-infra-system/project-root-infra/services/mailserver/usermgmt

# テスト実行
python -m pytest tests/test_flask_login_integration.py -v

# カバレッジ付きテスト実行
python -m pytest tests/test_flask_login_integration.py --cov=app --cov-report=html
```

---

## 7. ロールバック基準

以下の場合、実装をロールバックする:
- ❌ TC-FL-002 (UserMixin統合) が失敗
- ❌ TC-FL-004 (user_loader) が失敗
- ❌ セキュリティ設定 (TC-FL-005) が不十分

---

## 8. 次ステップ

テスト合格後:
1. Task 3: パスワードハッシュ化サービス実装へ進む
2. Task 4: 認証ルート実装へ進む
3. 統合テスト実施
