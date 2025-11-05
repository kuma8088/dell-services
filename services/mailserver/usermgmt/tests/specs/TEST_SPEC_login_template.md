# TEST_SPEC_login_template.md

## テスト対象
- `templates/login.html` - ログイン画面テンプレート (Bootstrap 5)

## テスト目的
Bootstrap 5 を使用したログイン画面のレスポンシブデザイン、フォームバリデーション、アクセシビリティを検証する。

---

## テストカテゴリ

### TC-LT-001: HTML構造テスト
**目的**: 適切な HTML5 構造とメタタグの検証

| Test ID | テスト内容 | 検証項目 |
|---------|-----------|----------|
| TC-LT-001-01 | DOCTYPE宣言 | `<!DOCTYPE html>` が存在する |
| TC-LT-001-02 | 言語属性 | `<html lang="ja">` が設定されている |
| TC-LT-001-03 | 文字エンコーディング | `<meta charset="UTF-8">` が存在する |
| TC-LT-001-04 | ビューポート設定 | `<meta name="viewport">` が正しく設定されている |
| TC-LT-001-05 | ページタイトル | `<title>` タグが存在し、適切な内容である |

### TC-LT-002: Bootstrap 5 統合テスト
**目的**: Bootstrap 5 CDN の正しい読み込みとバージョン検証

| Test ID | テスト内容 | 検証項目 |
|---------|-----------|----------|
| TC-LT-002-01 | Bootstrap CSS | Bootstrap 5.3.x CSS CDN リンクが存在する |
| TC-LT-002-02 | Bootstrap JS | Bootstrap 5.3.x JS バンドル CDN が存在する |
| TC-LT-002-03 | CDN順序 | CSS は `<head>` に、JS は `</body>` 直前にある |

### TC-LT-003: フォーム構造テスト
**目的**: ログインフォームの正しい構造と属性検証

| Test ID | テスト内容 | 検証項目 |
|---------|-----------|----------|
| TC-LT-003-01 | フォームタグ | `<form method="POST">` が存在する |
| TC-LT-003-02 | アクション属性 | `action="{{ url_for('auth.login') }}"` が設定されている |
| TC-LT-003-03 | メールフィールド | `type="email"` の input が存在し、`id="email"`, `name="email"` を持つ |
| TC-LT-003-04 | パスワードフィールド | `type="password"` の input が存在し、`id="password"`, `name="password"` を持つ |
| TC-LT-003-05 | 必須属性 | email, password フィールドに `required` 属性がある |
| TC-LT-003-06 | ラベル | email, password フィールドに対応する `<label>` が存在する |
| TC-LT-003-07 | 送信ボタン | `type="submit"` のボタンが存在する |

### TC-LT-004: Bootstrap スタイリングテスト
**目的**: Bootstrap 5 のクラスが正しく適用されているか検証

| Test ID | テスト内容 | 検証項目 |
|---------|-----------|----------|
| TC-LT-004-01 | コンテナ | `.container` または `.container-fluid` クラスが使用されている |
| TC-LT-004-02 | カード | `.card` クラスを使用したログインカードが存在する |
| TC-LT-004-03 | フォームコントロール | input に `.form-control` クラスが適用されている |
| TC-LT-004-04 | ボタンスタイル | ボタンに `.btn .btn-primary` クラスが適用されている |
| TC-LT-004-05 | マージン/パディング | 適切な `.mb-3`, `.mt-3` などのスペーシングクラスが使用されている |

### TC-LT-005: フラッシュメッセージテスト
**目的**: Flask flash メッセージの表示検証

| Test ID | テスト内容 | 検証項目 |
|---------|-----------|----------|
| TC-LT-005-01 | Jinja2構文 | `{% with messages = get_flashed_messages(with_categories=true) %}` が存在する |
| TC-LT-005-02 | メッセージループ | `{% for category, message in messages %}` が存在する |
| TC-LT-005-03 | Bootstrapアラート | `.alert .alert-{{ category }}` クラスが使用されている |

### TC-LT-006: レスポンシブデザインテスト
**目的**: モバイル/タブレット/デスクトップでの表示検証

| Test ID | テスト内容 | 検証項目 |
|---------|-----------|----------|
| TC-LT-006-01 | ビューポート | viewport meta タグが正しく設定されている |
| TC-LT-006-02 | レスポンシブコンテナ | モバイルで適切な幅制約がある (`.col-md-6 .col-lg-4` など) |
| TC-LT-006-03 | 中央配置 | ログインカードが画面中央に配置されている (`.mx-auto` など) |

### TC-LT-007: アクセシビリティテスト
**目的**: WCAG 2.1 基準のアクセシビリティ検証

| Test ID | テスト内容 | 検証項目 |
|---------|-----------|----------|
| TC-LT-007-01 | ラベル関連付け | `<label for="email">` と `<input id="email">` が正しく関連付けられている |
| TC-LT-007-02 | プレースホルダー | プレースホルダーテキストが適切に設定されている（任意） |
| TC-LT-007-03 | フォーカス | フォーカス順序が論理的である (email → password → button) |
| TC-LT-007-04 | エラーメッセージ | エラーメッセージが視覚的に明確である |

### TC-LT-008: CSRF保護テスト
**目的**: CSRF トークンの存在検証（Flask-WTF 統合時）

| Test ID | テスト内容 | 検証項目 |
|---------|-----------|----------|
| TC-LT-008-01 | CSRFトークンフィールド | `<input type="hidden" name="csrf_token">` が存在する (Flask-WTF使用時) |

---

## テスト実装方針

### pytest + BeautifulSoup によるテンプレートテスト
- Flask テストクライアントで GET /auth/login を呼び出し
- レスポンス HTML を BeautifulSoup でパース
- HTML 構造、クラス、属性を検証

### テストクラス構成
```python
class TestLoginTemplateStructure:
    """TC-LT-001: HTML構造テスト"""

class TestBootstrapIntegration:
    """TC-LT-002: Bootstrap 5 統合テスト"""

class TestFormStructure:
    """TC-LT-003: フォーム構造テスト"""

class TestBootstrapStyling:
    """TC-LT-004: Bootstrap スタイリングテスト"""

class TestFlashMessages:
    """TC-LT-005: フラッシュメッセージテスト"""

class TestResponsiveDesign:
    """TC-LT-006: レスポンシブデザインテスト"""

class TestAccessibility:
    """TC-LT-007: アクセシビリティテスト"""

class TestCSRFProtection:
    """TC-LT-008: CSRF保護テスト"""
```

---

## 期待される結果
- すべてのテストケースが PASS する
- Bootstrap 5.3.x が正しく読み込まれる
- レスポンシブデザインが機能する
- アクセシビリティ基準を満たす
- CSRF 保護が適切に実装されている (Flask-WTF 有効時)

---

## テスト実行コマンド
```bash
python -m pytest tests/test_login_template.py -v
```
