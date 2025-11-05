# TEST_SPEC_session_csrf_validation.md

## テスト対象
- P3-T5: セッション管理 (Cookie設定)
- P3-T6: CSRF 保護 (Flask-WTF)
- P3-T7: @login_required デコレータ

## テスト目的
既存実装の統合検証とセキュリティ設定の確認

---

## テストカテゴリ

### TC-SCV-001: セッション Cookie 設定検証
**目的**: セッション Cookie のセキュリティ属性を検証

| Test ID | テスト内容 | 検証項目 |
|---------|-----------|----------|
| TC-SCV-001-01 | HttpOnly 設定 | `SESSION_COOKIE_HTTPONLY = True` が設定されている |
| TC-SCV-001-02 | Secure 設定 | `SESSION_COOKIE_SECURE = True` が設定されている |
| TC-SCV-001-03 | SameSite 設定 | `SESSION_COOKIE_SAMESITE = 'Strict'` が設定されている |
| TC-SCV-001-04 | セッション有効期限 | `PERMANENT_SESSION_LIFETIME = timedelta(hours=1)` が設定されている |

### TC-SCV-002: CSRF 保護検証
**目的**: CSRF 保護機能の動作確認

| Test ID | テスト内容 | 検証項目 |
|---------|-----------|----------|
| TC-SCV-002-01 | CSRF設定 | `WTF_CSRF_ENABLED = True` が本番環境で有効 |
| TC-SCV-002-02 | CSRFトークン存在 | ログインフォームに `csrf_token` フィールドが存在する |
| TC-SCV-002-03 | CSRF検証 | 無効なトークンで POST リクエストを送信すると 400 エラーが返る（本番環境のみ） |

### TC-SCV-003: @login_required デコレータ検証
**目的**: 認証保護の動作確認（既に P3-T3 でテスト済み）

| Test ID | テスト内容 | 検証項目 |
|---------|-----------|----------|
| TC-SCV-003-01 | 未認証リダイレクト | 未認証状態で '/' にアクセスすると '/auth/login' にリダイレクトされる |
| TC-SCV-003-02 | 認証後アクセス | 認証後は保護されたルートにアクセスできる |
| TC-SCV-003-03 | ログアウト後保護 | ログアウト後は再度保護ルートにアクセスできない |

---

## テスト実装方針

### Config 検証テスト
- `app.config` の値を直接チェック
- セキュリティ関連設定が正しく適用されているか確認

### 統合テスト
- P3-T3 の既存テストで @login_required は検証済み
- CSRF 保護はテスト環境では無効化されているため、設定存在のみ確認

---

## 期待される結果
- すべての設定テストが PASS する
- セキュリティ設定が適切に構成されている
- 既存の認証フローと連携している

---

## テスト実行コマンド
```bash
python -m pytest tests/test_session_csrf_validation.py -v
```
