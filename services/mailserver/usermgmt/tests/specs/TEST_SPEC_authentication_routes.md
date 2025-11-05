# テスト仕様書: 認証ルート

**対象フェーズ**: Phase 3 - 認証システム実装
**対象コンポーネント**: 認証ルート (ログイン/ログアウト)
**作成日**: 2025-11-05
**優先度**: 🔴 高 (MVP必須)

---

## 1. テスト目的

認証ルートが正しく動作し、以下の機能を提供することを検証する：
- ログイン/ログアウト機能
- セッション管理
- CSRF保護
- @login_required デコレータ
- エラーハンドリング

---

## 2. テスト対象機能

### 2.1 認証ルート (app/routes/auth.py)
- `POST /auth/login`: ログイン処理
- `POST /auth/logout`: ログアウト処理
- `GET /auth/login`: ログイン画面表示

### 2.2 セキュリティ機能
- CSRF トークン検証 (Flask-WTF)
- セッション Cookie 設定 (HttpOnly, Secure, SameSite)
- パスワード検証
- 有効化ユーザーのみログイン可能

### 2.3 デコレータ
- `@login_required`: 未認証アクセスのブロック

---

## 3. テストケース一覧

### TC-AR-001: ログイン成功テスト
**目的**: 有効な認証情報でログインが成功することを検証

**テストデータ**:
```python
email = 'testuser1@example.com'
password = 'ValidPassword123!'
```

**テスト手順**:
1. 有効なユーザーをDBに作成
2. POST /auth/login にメールアドレスとパスワードを送信
3. レスポンスステータスコードが 302 (リダイレクト) であることを確認
4. セッションにユーザーIDが設定されることを確認
5. `current_user.is_authenticated` が True であることを確認

**期待結果**:
- ✅ ステータスコード: 302 (リダイレクト)
- ✅ セッションにユーザーID設定
- ✅ `current_user.is_authenticated == True`
- ✅ リダイレクト先: `/` (ダッシュボード)

---

### TC-AR-002: ログイン失敗テスト
**目的**: 無効な認証情報でログインが失敗することを検証

**テストケース**:

#### TC-AR-002-1: 誤ったパスワード
```python
email = 'testuser1@example.com'
password = 'WrongPassword'
```

**期待結果**:
- ✅ ステータスコード: 200 (ログイン画面再表示)
- ✅ エラーメッセージ表示
- ✅ `current_user.is_authenticated == False`

#### TC-AR-002-2: 存在しないメールアドレス
```python
email = 'nonexistent@example.com'
password = 'AnyPassword'
```

**期待結果**:
- ✅ ステータスコード: 200 (ログイン画面再表示)
- ✅ エラーメッセージ表示
- ✅ `current_user.is_authenticated == False`

#### TC-AR-002-3: 無効化されたユーザー
```python
email = 'disabled@example.com'  # enabled=False
password = 'ValidPassword123!'
```

**期待結果**:
- ✅ ステータスコード: 200 (ログイン画面再表示)
- ✅ エラーメッセージ: 「アカウントが無効です」
- ✅ `current_user.is_authenticated == False`

---

### TC-AR-003: ログアウトテスト
**目的**: ログアウト処理が正しく動作することを検証

**テスト手順**:
1. ログイン済みセッションを作成
2. POST /auth/logout を実行
3. セッションがクリアされることを確認
4. `current_user.is_authenticated` が False であることを確認

**期待結果**:
- ✅ ステータスコード: 302 (リダイレクト)
- ✅ セッションクリア
- ✅ `current_user.is_authenticated == False`
- ✅ リダイレクト先: `/auth/login`

---

### TC-AR-004: @login_required デコレータテスト
**目的**: 未認証アクセスが適切にブロックされることを検証

**テストケース**:

#### TC-AR-004-1: 未認証アクセス
```python
# ログインせずに保護されたルートにアクセス
GET /dashboard
```

**期待結果**:
- ✅ ステータスコード: 302 (リダイレクト)
- ✅ リダイレクト先: `/auth/login?next=/dashboard`

#### TC-AR-004-2: 認証済みアクセス
```python
# ログイン後に保護されたルートにアクセス
GET /dashboard
```

**期待結果**:
- ✅ ステータスコード: 200 (正常表示)
- ✅ ダッシュボード画面が表示される

---

### TC-AR-005: CSRF保護テスト
**目的**: CSRF トークンが正しく検証されることを確認

**テストケース**:

#### TC-AR-005-1: CSRF トークンなし
```python
POST /auth/login (CSRF トークンなし)
```

**期待結果**:
- ✅ ステータスコード: 400 (Bad Request)
- ✅ エラーメッセージ: 「CSRF token missing」

#### TC-AR-005-2: 無効な CSRF トークン
```python
POST /auth/login (無効な CSRF トークン)
```

**期待結果**:
- ✅ ステータスコード: 400 (Bad Request)
- ✅ エラーメッセージ: 「CSRF token invalid」

#### TC-AR-005-3: 有効な CSRF トークン
```python
POST /auth/login (有効な CSRF トークン)
```

**期待結果**:
- ✅ ステータスコード: 302 (リダイレクト)
- ✅ ログイン成功

---

### TC-AR-006: セッション管理テスト
**目的**: セッションCookieが適切に設定されることを検証

**テストケース**:

#### TC-AR-006-1: セッションCookie設定
```python
# ログイン後のCookie確認
```

**期待結果**:
- ✅ Cookie名: `session`
- ✅ `HttpOnly=True`
- ✅ `Secure=True`
- ✅ `SameSite=Strict`

#### TC-AR-006-2: セッション永続化
```python
# `remember=True` でログイン
```

**期待結果**:
- ✅ セッション有効期限: 1時間
- ✅ `permanent=True`

---

### TC-AR-007: リダイレクト処理テスト
**目的**: ログイン後のリダイレクトが正しく動作することを検証

**テストケース**:

#### TC-AR-007-1: デフォルトリダイレクト
```python
POST /auth/login (next パラメータなし)
```

**期待結果**:
- ✅ リダイレクト先: `/` (ダッシュボード)

#### TC-AR-007-2: next パラメータ付きリダイレクト
```python
POST /auth/login?next=/users
```

**期待結果**:
- ✅ リダイレクト先: `/users`

#### TC-AR-007-3: 安全でない next パラメータ (オープンリダイレクト対策)
```python
POST /auth/login?next=http://malicious.com
```

**期待結果**:
- ✅ リダイレクト先: `/` (デフォルトにフォールバック)

---

## 4. テスト環境

### 4.1 依存関係
- **Flask-Login**: セッション管理
- **Flask-WTF**: CSRF保護
- **pytest**: テストフレームワーク
- **pytest-flask**: Flask テストヘルパー

### 4.2 テストデータベース
- データベース: `mailserver_usermgmt_test`
- テストユーザー: `conftest.py` で自動作成

---

## 5. 成功基準

すべてのテストケース (TC-AR-001 ~ TC-AR-007) が成功すること:
- ✅ ログイン/ログアウトが動作する
- ✅ パスワード検証が正確
- ✅ CSRF保護が機能している
- ✅ セッション管理が適切
- ✅ @login_required デコレータが動作する
- ✅ リダイレクト処理が安全

---

## 6. テスト実行方法

```bash
# テストディレクトリに移動
cd /opt/onprem-infra-system/project-root-infra/services/mailserver/usermgmt

# テスト実行
python -m pytest tests/test_authentication_routes.py -v

# カバレッジ付きテスト実行
python -m pytest tests/test_authentication_routes.py --cov=app/routes --cov-report=html
```

---

## 7. ロールバック基準

以下の場合、実装をロールバックする:
- ❌ TC-AR-001 (ログイン成功) が失敗
- ❌ TC-AR-003 (ログアウト) が失敗
- ❌ TC-AR-005 (CSRF保護) が失敗

---

## 8. 次ステップ

テスト合格後:
1. P3-T4: ログイン画面テンプレート実装
2. P3-T5: セッション管理設定
3. 統合テスト実施
