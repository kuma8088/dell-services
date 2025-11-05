# テスト仕様書: User Service (P4-T2)

**作成日**: 2025-11-05
**対象モジュール**: `app/services/user_service.py`
**テストファイル**: `tests/test_user_service.py`

---

## 📋 テスト概要

User Service のビジネスロジックをテストします。

### テスト対象機能

1. ユーザ一覧取得
2. ユーザ作成
3. ユーザ取得（メールアドレス指定）
4. ユーザ更新
5. ユーザ削除
6. ユーザ有効/無効切り替え
7. パスワード変更
8. 監査ログ記録

---

## 🎯 テストケース一覧

### 1. ユーザ一覧取得 (list_users)

#### TC-US-001: 全ユーザ取得成功
**前提条件**: データベースに3件のユーザが存在
**入力**: なし
**期待結果**:
- 3件のユーザリストが返される
- 各ユーザに id, email, domain_id, enabled, created_at 属性が含まれる

#### TC-US-002: ドメインフィルタ付き取得
**前提条件**: example.com ドメインに2件、test.com ドメインに1件のユーザが存在
**入力**: `domain_id=1` (example.com)
**期待結果**:
- 2件のユーザリストが返される
- 全ユーザの domain_id が 1

#### TC-US-003: 空のユーザリスト
**前提条件**: データベースが空
**入力**: なし
**期待結果**:
- 空リストが返される
- エラーが発生しない

---

### 2. ユーザ作成 (create_user)

#### TC-US-004: ユーザ作成成功
**前提条件**: example.com ドメインが存在（domain_id=1）
**入力**:
```python
{
    'email': 'newuser@example.com',
    'password': 'SecurePass123!',
    'domain_id': 1,
    'quota': 2048,
    'enabled': True
}
```
**期待結果**:
- ユーザが作成される
- password_hash に `{SHA512-CRYPT}` プレフィックスが含まれる
- maildir が `/var/mail/vmail/example.com/newuser/` に設定される
- uid=5000, gid=5000 がデフォルト設定される
- audit_logs に CREATE イベントが記録される

#### TC-US-005: 重複メールアドレスエラー
**前提条件**: test@example.com ユーザが既に存在
**入力**:
```python
{
    'email': 'test@example.com',
    'password': 'SecurePass123!',
    'domain_id': 1
}
```
**期待結果**:
- `ValueError` 例外が発生
- エラーメッセージ: "Email address already exists"

#### TC-US-006: 無効なドメインIDエラー
**前提条件**: domain_id=999 が存在しない
**入力**:
```python
{
    'email': 'test@invalid.com',
    'password': 'SecurePass123!',
    'domain_id': 999
}
```
**期待結果**:
- `ValueError` 例外が発生
- エラーメッセージ: "Domain not found"

#### TC-US-007: maildir 自動生成
**前提条件**: example.com ドメインが存在
**入力**:
```python
{
    'email': 'user.name+tag@example.com',
    'password': 'SecurePass123!',
    'domain_id': 1
}
```
**期待結果**:
- maildir が `/var/mail/vmail/example.com/user.name+tag/` に設定される
- 特殊文字（+, .）が正しく処理される

---

### 3. ユーザ取得 (get_user_by_email)

#### TC-US-008: ユーザ取得成功
**前提条件**: test@example.com ユーザが存在
**入力**: `email='test@example.com'`
**期待結果**:
- User オブジェクトが返される
- email, domain_id, enabled 属性が正しく設定されている

#### TC-US-009: 存在しないユーザ
**入力**: `email='nonexistent@example.com'`
**期待結果**:
- `None` が返される
- エラーが発生しない

---

### 4. ユーザ更新 (update_user)

#### TC-US-010: クォータ更新成功
**前提条件**: test@example.com ユーザが存在（quota=1024）
**入力**:
```python
{
    'email': 'test@example.com',
    'quota': 4096
}
```
**期待結果**:
- quota が 4096 に更新される
- updated_at タイムスタンプが更新される
- audit_logs に UPDATE イベントが記録される

#### TC-US-011: 複数フィールド更新
**前提条件**: test@example.com ユーザが存在
**入力**:
```python
{
    'email': 'test@example.com',
    'quota': 2048,
    'enabled': False
}
```
**期待結果**:
- quota が 2048 に更新される
- enabled が False に更新される
- updated_at タイムスタンプが更新される

#### TC-US-012: 存在しないユーザ更新エラー
**入力**:
```python
{
    'email': 'nonexistent@example.com',
    'quota': 2048
}
```
**期待結果**:
- `ValueError` 例外が発生
- エラーメッセージ: "User not found"

#### TC-US-013: メールアドレス変更禁止
**前提条件**: test@example.com ユーザが存在
**入力**:
```python
{
    'email': 'test@example.com',
    'new_email': 'newemail@example.com'
}
```
**期待結果**:
- `ValueError` 例外が発生
- エラーメッセージ: "Email address cannot be changed"
- （メールアドレス変更は削除→再作成で対応）

---

### 5. ユーザ削除 (delete_user)

#### TC-US-014: ユーザ削除成功
**前提条件**: test@example.com ユーザが存在
**入力**: `email='test@example.com'`
**期待結果**:
- ユーザがデータベースから削除される
- audit_logs に DELETE イベントが記録される
- 削除後に get_user_by_email で取得不可

#### TC-US-015: 存在しないユーザ削除エラー
**入力**: `email='nonexistent@example.com'`
**期待結果**:
- `ValueError` 例外が発生
- エラーメッセージ: "User not found"

---

### 6. ユーザ有効/無効切り替え (toggle_user_status)

#### TC-US-016: ユーザ無効化
**前提条件**: test@example.com ユーザが enabled=True
**入力**: `email='test@example.com'`, `enabled=False`
**期待結果**:
- enabled が False に更新される
- audit_logs に DISABLE イベントが記録される

#### TC-US-017: ユーザ有効化
**前提条件**: test@example.com ユーザが enabled=False
**入力**: `email='test@example.com'`, `enabled=True`
**期待結果**:
- enabled が True に更新される
- audit_logs に ENABLE イベントが記録される

---

### 7. パスワード変更 (change_password)

#### TC-US-018: パスワード変更成功
**前提条件**: test@example.com ユーザが存在
**入力**:
```python
{
    'email': 'test@example.com',
    'new_password': 'NewSecurePass456!'
}
```
**期待結果**:
- password_hash が更新される
- 新しいハッシュに `{SHA512-CRYPT}` プレフィックスが含まれる
- 古いハッシュと異なる
- audit_logs に PASSWORD_CHANGE イベントが記録される

#### TC-US-019: 存在しないユーザのパスワード変更エラー
**入力**:
```python
{
    'email': 'nonexistent@example.com',
    'new_password': 'NewPass123!'
}
```
**期待結果**:
- `ValueError` 例外が発生
- エラーメッセージ: "User not found"

---

### 8. 監査ログ記録 (log_audit)

#### TC-US-020: CREATE イベントログ
**入力**:
```python
{
    'action': 'CREATE',
    'user_email': 'newuser@example.com',
    'performed_by': 'admin@example.com',
    'details': 'User created with quota 1024MB'
}
```
**期待結果**:
- audit_logs テーブルに新しいレコードが追加される
- action='CREATE', user_email, performed_by, details が正しく記録される
- created_at タイムスタンプが自動設定される

#### TC-US-021: UPDATE イベントログ
**入力**:
```python
{
    'action': 'UPDATE',
    'user_email': 'test@example.com',
    'performed_by': 'admin@example.com',
    'details': 'Quota changed from 1024MB to 2048MB'
}
```
**期待結果**:
- audit_logs テーブルに UPDATE レコードが追加される

#### TC-US-022: DELETE イベントログ
**入力**:
```python
{
    'action': 'DELETE',
    'user_email': 'olduser@example.com',
    'performed_by': 'admin@example.com',
    'details': 'User account deleted'
}
```
**期待結果**:
- audit_logs テーブルに DELETE レコードが追加される

---

## 🏗️ テストフィクスチャ

### データベースセットアップ

```python
@pytest.fixture
def setup_domains(db_session):
    """テスト用ドメイン作成"""
    domain1 = Domain(name='example.com', description='Example domain')
    domain2 = Domain(name='test.com', description='Test domain')
    db_session.add(domain1)
    db_session.add(domain2)
    db_session.commit()
    return {'example.com': domain1.id, 'test.com': domain2.id}

@pytest.fixture
def setup_users(db_session, setup_domains):
    """テスト用ユーザ作成"""
    from app.services.password import hash_password

    users = [
        User(
            email='user1@example.com',
            password_hash=hash_password('Password1!'),
            domain_id=setup_domains['example.com'],
            maildir='/var/mail/vmail/example.com/user1/',
            quota=1024,
            enabled=True
        ),
        User(
            email='user2@example.com',
            password_hash=hash_password('Password2!'),
            domain_id=setup_domains['example.com'],
            maildir='/var/mail/vmail/example.com/user2/',
            quota=2048,
            enabled=True
        ),
        User(
            email='user3@test.com',
            password_hash=hash_password('Password3!'),
            domain_id=setup_domains['test.com'],
            maildir='/var/mail/vmail/test.com/user3/',
            quota=1024,
            enabled=False
        )
    ]

    for user in users:
        db_session.add(user)
    db_session.commit()

    return users
```

---

## ✅ 実装要件

### User Service メソッド

```python
class UserService:
    @staticmethod
    def list_users(domain_id=None):
        """ユーザ一覧取得"""
        pass

    @staticmethod
    def create_user(email, password, domain_id, quota=1024, enabled=True):
        """ユーザ作成"""
        pass

    @staticmethod
    def get_user_by_email(email):
        """ユーザ取得"""
        pass

    @staticmethod
    def update_user(email, **kwargs):
        """ユーザ更新"""
        pass

    @staticmethod
    def delete_user(email):
        """ユーザ削除"""
        pass

    @staticmethod
    def toggle_user_status(email, enabled):
        """ユーザ有効/無効切り替え"""
        pass

    @staticmethod
    def change_password(email, new_password):
        """パスワード変更"""
        pass

    @staticmethod
    def log_audit(action, user_email, performed_by, details=''):
        """監査ログ記録"""
        pass
```

---

## 📊 テストカバレッジ目標

- **Line Coverage**: 95% 以上
- **Branch Coverage**: 90% 以上
- **Function Coverage**: 100%

---

## 🔍 エッジケースと境界値テスト

### メールアドレス検証
- 空文字列
- 255文字制限
- 特殊文字（+, ., -）
- @なしアドレス
- 複数@アドレス

### クォータ検証
- 負の値
- 0
- 最大値 (2147483647)

### ドメインID検証
- 0
- 負の値
- 存在しないID

---

## 🧪 テスト実行コマンド

```bash
# User Service テストのみ実行
pytest tests/test_user_service.py -v

# カバレッジ付き実行
pytest tests/test_user_service.py --cov=app/services/user_service --cov-report=term-missing

# 詳細出力
pytest tests/test_user_service.py -vv --tb=short
```

---

## 📝 実装時の注意事項

1. **トランザクション管理**: 各操作は db.session.commit() でコミット
2. **エラーハンドリング**: 適切な例外を発生させる（ValueError, IntegrityError）
3. **監査ログ**: 全ての変更操作（CREATE, UPDATE, DELETE）で log_audit を呼び出す
4. **パスワードハッシュ**: `app.services.password.hash_password` を使用
5. **maildir 自動生成**: メールアドレスから domain と username を抽出
6. **テストデータクリーンアップ**: 各テスト後に db_session.rollback()

---

**承認**: system-admin
**作成日**: 2025-11-05
