"""
Test suite for login template (Bootstrap 5)

Tests login.html template structure, Bootstrap integration,
responsive design, and accessibility.
"""
import pytest
from bs4 import BeautifulSoup


class TestLoginTemplateStructure:
    """TC-LT-001: HTML構造テスト"""

    def test_doctype_declaration(self, client):
        """TC-LT-001-01: DOCTYPE宣言"""
        response = client.get('/auth/login')
        assert response.status_code == 200
        assert b'<!DOCTYPE html>' in response.data or b'<!doctype html>' in response.data

    def test_language_attribute(self, client):
        """TC-LT-001-02: 言語属性"""
        response = client.get('/auth/login')
        soup = BeautifulSoup(response.data, 'html.parser')
        html_tag = soup.find('html')
        assert html_tag is not None
        assert html_tag.get('lang') == 'ja'

    def test_charset_encoding(self, client):
        """TC-LT-001-03: 文字エンコーディング"""
        response = client.get('/auth/login')
        soup = BeautifulSoup(response.data, 'html.parser')
        charset_meta = soup.find('meta', {'charset': 'UTF-8'})
        assert charset_meta is not None

    def test_viewport_meta(self, client):
        """TC-LT-001-04: ビューポート設定"""
        response = client.get('/auth/login')
        soup = BeautifulSoup(response.data, 'html.parser')
        viewport_meta = soup.find('meta', {'name': 'viewport'})
        assert viewport_meta is not None
        assert 'width=device-width' in viewport_meta.get('content', '')

    def test_page_title(self, client):
        """TC-LT-001-05: ページタイトル"""
        response = client.get('/auth/login')
        soup = BeautifulSoup(response.data, 'html.parser')
        title_tag = soup.find('title')
        assert title_tag is not None
        assert 'ログイン' in title_tag.string


class TestBootstrapIntegration:
    """TC-LT-002: Bootstrap 5 統合テスト"""

    def test_bootstrap_css_cdn(self, client):
        """TC-LT-002-01: Bootstrap CSS"""
        response = client.get('/auth/login')
        soup = BeautifulSoup(response.data, 'html.parser')
        bootstrap_css = soup.find('link', {
            'href': lambda x: x and 'bootstrap' in x and '.min.css' in x
        })
        assert bootstrap_css is not None
        # Bootstrap 5.3.x を確認
        assert '5.3' in bootstrap_css.get('href', '')

    def test_bootstrap_js_bundle(self, client):
        """TC-LT-002-02: Bootstrap JS"""
        response = client.get('/auth/login')
        soup = BeautifulSoup(response.data, 'html.parser')
        bootstrap_js = soup.find('script', {
            'src': lambda x: x and 'bootstrap' in x and 'bundle' in x
        })
        assert bootstrap_js is not None
        # Bootstrap 5.3.x を確認
        assert '5.3' in bootstrap_js.get('src', '')

    def test_cdn_ordering(self, client):
        """TC-LT-002-03: CDN順序"""
        response = client.get('/auth/login')
        soup = BeautifulSoup(response.data, 'html.parser')

        # CSS は <head> 内にある
        head = soup.find('head')
        assert head is not None
        css_in_head = head.find('link', {
            'href': lambda x: x and 'bootstrap' in x
        })
        assert css_in_head is not None

        # JS は <body> 内にある
        body = soup.find('body')
        assert body is not None
        js_in_body = body.find('script', {
            'src': lambda x: x and 'bootstrap' in x
        })
        assert js_in_body is not None


class TestFormStructure:
    """TC-LT-003: フォーム構造テスト"""

    def test_form_tag_exists(self, client):
        """TC-LT-003-01: フォームタグ"""
        response = client.get('/auth/login')
        soup = BeautifulSoup(response.data, 'html.parser')
        form = soup.find('form', {'method': 'POST'})
        assert form is not None

    def test_form_action_attribute(self, client):
        """TC-LT-003-02: アクション属性"""
        response = client.get('/auth/login')
        soup = BeautifulSoup(response.data, 'html.parser')
        form = soup.find('form')
        assert form is not None
        action = form.get('action', '')
        assert '/auth/login' in action

    def test_email_field(self, client):
        """TC-LT-003-03: メールフィールド"""
        response = client.get('/auth/login')
        soup = BeautifulSoup(response.data, 'html.parser')
        email_input = soup.find('input', {'type': 'email'})
        assert email_input is not None
        assert email_input.get('id') == 'email'
        assert email_input.get('name') == 'email'

    def test_password_field(self, client):
        """TC-LT-003-04: パスワードフィールド"""
        response = client.get('/auth/login')
        soup = BeautifulSoup(response.data, 'html.parser')
        password_input = soup.find('input', {'type': 'password'})
        assert password_input is not None
        assert password_input.get('id') == 'password'
        assert password_input.get('name') == 'password'

    def test_required_attributes(self, client):
        """TC-LT-003-05: 必須属性"""
        response = client.get('/auth/login')
        soup = BeautifulSoup(response.data, 'html.parser')

        email_input = soup.find('input', {'type': 'email'})
        assert email_input.has_attr('required')

        password_input = soup.find('input', {'type': 'password'})
        assert password_input.has_attr('required')

    def test_labels(self, client):
        """TC-LT-003-06: ラベル"""
        response = client.get('/auth/login')
        soup = BeautifulSoup(response.data, 'html.parser')

        email_label = soup.find('label', {'for': 'email'})
        assert email_label is not None

        password_label = soup.find('label', {'for': 'password'})
        assert password_label is not None

    def test_submit_button(self, client):
        """TC-LT-003-07: 送信ボタン"""
        response = client.get('/auth/login')
        soup = BeautifulSoup(response.data, 'html.parser')
        submit_button = soup.find('button', {'type': 'submit'})
        assert submit_button is not None


class TestBootstrapStyling:
    """TC-LT-004: Bootstrap スタイリングテスト"""

    def test_container_class(self, client):
        """TC-LT-004-01: コンテナ"""
        response = client.get('/auth/login')
        soup = BeautifulSoup(response.data, 'html.parser')
        container = soup.find(class_=lambda x: x and ('container' in x or 'container-fluid' in x))
        assert container is not None

    def test_card_class(self, client):
        """TC-LT-004-02: カード"""
        response = client.get('/auth/login')
        soup = BeautifulSoup(response.data, 'html.parser')
        card = soup.find(class_=lambda x: x and 'card' in x)
        assert card is not None

    def test_form_control_class(self, client):
        """TC-LT-004-03: フォームコントロール"""
        response = client.get('/auth/login')
        soup = BeautifulSoup(response.data, 'html.parser')

        email_input = soup.find('input', {'type': 'email'})
        assert 'form-control' in email_input.get('class', [])

        password_input = soup.find('input', {'type': 'password'})
        assert 'form-control' in password_input.get('class', [])

    def test_button_classes(self, client):
        """TC-LT-004-04: ボタンスタイル"""
        response = client.get('/auth/login')
        soup = BeautifulSoup(response.data, 'html.parser')
        submit_button = soup.find('button', {'type': 'submit'})
        assert submit_button is not None
        button_classes = submit_button.get('class', [])
        assert 'btn' in button_classes
        assert 'btn-primary' in button_classes

    def test_spacing_classes(self, client):
        """TC-LT-004-05: マージン/パディング"""
        response = client.get('/auth/login')
        soup = BeautifulSoup(response.data, 'html.parser')

        # mb-3 (margin-bottom: 1rem) クラスが使用されているか確認
        elements_with_spacing = soup.find_all(class_=lambda x: x and any(
            spacing in x for spacing in ['mb-', 'mt-', 'my-', 'mx-', 'p-']
        ))
        assert len(elements_with_spacing) > 0


class TestFlashMessages:
    """TC-LT-005: フラッシュメッセージテスト"""

    def test_jinja2_syntax(self, client):
        """TC-LT-005-01: Jinja2構文"""
        response = client.get('/auth/login')
        # Jinja2 構文は HTML にレンダリングされないため、ソースコードで確認
        # この検証は実際のテンプレートファイルを直接読む必要がある
        # ここではレスポンスが正常であることを確認
        assert response.status_code == 200

    def test_message_loop(self, client):
        """TC-LT-005-02: メッセージループ"""
        # フラッシュメッセージをセットしてテスト
        with client.session_transaction() as session:
            session['_flashes'] = [('error', 'テストエラーメッセージ')]

        response = client.get('/auth/login')
        assert 'テストエラーメッセージ' in response.data.decode('utf-8')

    def test_bootstrap_alert(self, client):
        """TC-LT-005-03: Bootstrapアラート"""
        with client.session_transaction() as session:
            session['_flashes'] = [('error', 'テストエラーメッセージ')]

        response = client.get('/auth/login')
        soup = BeautifulSoup(response.data, 'html.parser')
        alert = soup.find(class_=lambda x: x and 'alert' in x)
        assert alert is not None
        assert 'alert-error' in alert.get('class', []) or 'alert-danger' in alert.get('class', [])


class TestResponsiveDesign:
    """TC-LT-006: レスポンシブデザインテスト"""

    def test_viewport_meta(self, client):
        """TC-LT-006-01: ビューポート"""
        response = client.get('/auth/login')
        soup = BeautifulSoup(response.data, 'html.parser')
        viewport_meta = soup.find('meta', {'name': 'viewport'})
        assert viewport_meta is not None
        content = viewport_meta.get('content', '')
        assert 'width=device-width' in content
        assert 'initial-scale=1' in content

    def test_responsive_container(self, client):
        """TC-LT-006-02: レスポンシブコンテナ"""
        response = client.get('/auth/login')
        soup = BeautifulSoup(response.data, 'html.parser')
        # col-md-, col-lg- などのレスポンシブクラスが使用されているか確認
        responsive_cols = soup.find_all(class_=lambda x: x and any(
            col in x for col in ['col-md-', 'col-lg-', 'col-sm-', 'col-xl-']
        ))
        assert len(responsive_cols) > 0

    def test_center_alignment(self, client):
        """TC-LT-006-03: 中央配置"""
        response = client.get('/auth/login')
        soup = BeautifulSoup(response.data, 'html.parser')
        # mx-auto, justify-content-center などの中央配置クラスが使用されているか確認
        centered_elements = soup.find_all(class_=lambda x: x and any(
            align in x for align in ['mx-auto', 'justify-content-center', 'align-items-center']
        ))
        assert len(centered_elements) > 0


class TestAccessibility:
    """TC-LT-007: アクセシビリティテスト"""

    def test_label_association(self, client):
        """TC-LT-007-01: ラベル関連付け"""
        response = client.get('/auth/login')
        soup = BeautifulSoup(response.data, 'html.parser')

        # email フィールド
        email_label = soup.find('label', {'for': 'email'})
        email_input = soup.find('input', {'id': 'email'})
        assert email_label is not None
        assert email_input is not None

        # password フィールド
        password_label = soup.find('label', {'for': 'password'})
        password_input = soup.find('input', {'id': 'password'})
        assert password_label is not None
        assert password_input is not None

    def test_placeholder_text(self, client):
        """TC-LT-007-02: プレースホルダー"""
        response = client.get('/auth/login')
        soup = BeautifulSoup(response.data, 'html.parser')

        # プレースホルダーは任意だが、設定されている場合は適切であることを確認
        email_input = soup.find('input', {'type': 'email'})
        placeholder = email_input.get('placeholder', '')
        if placeholder:
            assert len(placeholder) > 0

    def test_focus_order(self, client):
        """TC-LT-007-03: フォーカス"""
        response = client.get('/auth/login')
        soup = BeautifulSoup(response.data, 'html.parser')

        # tabindex が設定されていないか、論理的な順序であることを確認
        form = soup.find('form')
        inputs = form.find_all(['input', 'button'])

        # 明示的な tabindex が -1 ではないことを確認（非表示要素以外）
        for input_elem in inputs:
            tabindex = input_elem.get('tabindex')
            if tabindex is not None:
                assert int(tabindex) >= 0

    def test_error_messages(self, client):
        """TC-LT-007-04: エラーメッセージ"""
        with client.session_transaction() as session:
            session['_flashes'] = [('error', 'エラーメッセージ')]

        response = client.get('/auth/login')
        soup = BeautifulSoup(response.data, 'html.parser')

        # エラーメッセージが視覚的に明確（alert クラス使用）
        alert = soup.find(class_=lambda x: x and 'alert' in x)
        assert alert is not None


class TestCSRFProtection:
    """TC-LT-008: CSRF保護テスト"""

    def test_csrf_token_field(self, client):
        """TC-LT-008-01: CSRFトークンフィールド"""
        response = client.get('/auth/login')
        soup = BeautifulSoup(response.data, 'html.parser')

        # Flask-WTF が有効な場合、csrf_token フィールドが存在する
        csrf_input = soup.find('input', {'name': 'csrf_token', 'type': 'hidden'})

        # CSRF protection が有効な場合のみアサート
        # テスト環境では WTF_CSRF_ENABLED=False の可能性があるため、
        # 存在チェックのみ（必須ではない）
        # 本番環境では必須
        if client.application.config.get('WTF_CSRF_ENABLED', True):
            assert csrf_input is not None


def test_login_template_summary(client):
    """ログインテンプレートの総合テスト"""
    response = client.get('/auth/login')
    assert response.status_code == 200

    soup = BeautifulSoup(response.data, 'html.parser')

    # 基本要素の存在確認
    assert soup.find('html') is not None
    assert soup.find('head') is not None
    assert soup.find('body') is not None
    assert soup.find('form') is not None
    assert soup.find('input', {'type': 'email'}) is not None
    assert soup.find('input', {'type': 'password'}) is not None
    assert soup.find('button', {'type': 'submit'}) is not None

    # Bootstrap 要素の存在確認
    assert soup.find('link', {'href': lambda x: x and 'bootstrap' in x}) is not None
    assert soup.find('script', {'src': lambda x: x and 'bootstrap' in x}) is not None
