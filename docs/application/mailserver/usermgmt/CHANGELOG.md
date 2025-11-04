# 変更履歴 (Changelog)

このファイルは、メールユーザ管理システムの主要な変更履歴を記録します。

フォーマットは [Keep a Changelog](https://keepachangelog.com/ja/1.0.0/) に基づいています。
バージョン管理は [Semantic Versioning](https://semver.org/lang/ja/) に従います。

---

## [Unreleased] - 開発中

### 追加予定 (Planned)
- データベースモデル実装 (User, Domain, AuditLog)
- Flask-Login 認証システム
- ユーザCRUD操作 (作成・編集・削除)
- Bootstrap 5 ベースのUI
- Dovecot SQL認証統合
- Nginx リバースプロキシ設定
- 監査ログ機能
- レスポンシブデザイン (モバイル対応)

---

## [0.1.0] - 2025-11-05

### 追加 (Added)
- **ドキュメント整備**:
  - `README.md` - プロジェクト概要、アーキテクチャ、セットアップ手順
  - `DEVELOPMENT.md` - 開発進捗トラッキング (Phase 0-10)
  - `API.md` - API エンドポイント仕様
  - `CHANGELOG.md` - 変更履歴 (本ファイル)

### 変更 (Changed)
- ドキュメント配置場所を `services/mailserver/usermgmt/` から `Docs/application/mailserver/usermgmt/` に変更

---

## [0.0.1] - 2025-11-04

### 追加 (Added)
- **プロジェクト初期化**:
  - ディレクトリ構造作成 (`app/`, `templates/`, `static/`, `config/`)
  - `requirements.txt` - Python 依存関係定義
  - `Dockerfile` - Docker コンテナ定義
  - `app.py` - 最小構成の Flask アプリケーション
    - `/health` エンドポイント (Docker healthcheck 用)
    - MariaDB 接続設定 (環境変数ベース)

### 技術スタック
- **Backend**: Flask 3.0.0, SQLAlchemy 2.0.23, Python 3.11+
- **Database**: MariaDB 10.11 (既存コンテナ利用)
- **Frontend**: Bootstrap 5.3 (予定)
- **Deployment**: Docker + Gunicorn 21.2.0

---

## リリースノート記法

### 変更タイプ
- `追加 (Added)` - 新機能
- `変更 (Changed)` - 既存機能の変更
- `非推奨 (Deprecated)` - 近い将来削除予定の機能
- `削除 (Removed)` - 削除された機能
- `修正 (Fixed)` - バグ修正
- `セキュリティ (Security)` - セキュリティ関連の変更

### バージョン番号規則 (Semantic Versioning)
- **メジャーバージョン (X.0.0)**: 互換性のない API 変更
- **マイナーバージョン (0.X.0)**: 後方互換性のある機能追加
- **パッチバージョン (0.0.X)**: 後方互換性のあるバグ修正

---

## 今後のリリース予定

### v0.2.0 - データベース基盤構築 (Phase 2)
**予定日**: 未定

**追加予定**:
- SQLAlchemy モデル定義 (User, Domain, AuditLog)
- MariaDB スキーマ作成スクリプト
- データベース接続管理
- マイグレーションツール設定

---

### v0.3.0 - 認証システム実装 (Phase 3)
**予定日**: 未定

**追加予定**:
- Flask-Login 統合
- ログイン/ログアウトルート
- セッション管理
- CSRF 保護
- パスワードハッシュ化 (SHA512-CRYPT)

---

### v0.4.0 - ユーザCRUD機能実装 (Phase 4)
**予定日**: 未定

**追加予定**:
- ユーザ一覧表示
- ユーザ作成
- ユーザ編集
- ユーザ削除
- パスワード変更
- 監査ログ記録

---

### v0.5.0 - UI/テンプレート実装 (Phase 5)
**予定日**: 未定

**追加予定**:
- Bootstrap 5 ベーステンプレート
- ダッシュボード画面
- ユーザ管理画面
- フォームバリデーション
- レスポンシブデザイン

---

### v0.6.0 - Dovecot SQL認証統合 (Phase 6)
**予定日**: 未定

**追加予定**:
- `dovecot-sql.conf.ext` 設定
- `auth-sql.conf.ext` 設定
- File認証とSQL認証の並行稼働

**変更**:
- Dovecot 設定更新 (SQL認証追加)

---

### v0.7.0 - Nginx統合 (Phase 7)
**予定日**: 未定

**追加予定**:
- Nginx `/admin` パス設定
- Tailscale VPN アクセス制限
- HTTPS 強制リダイレクト
- セキュアCookie設定

---

### v0.8.0 - テスト・検証 (Phase 8)
**予定日**: 未定

**追加予定**:
- ユニットテスト (pytest)
- 統合テスト
- セキュリティテスト
- パフォーマンステスト
- テストカバレッジレポート

---

### v0.9.0 - 本番デプロイ準備 (Phase 9)
**予定日**: 未定

**追加予定**:
- docker-compose.yml 統合
- バックアップスクリプト
- ロールバック手順書
- モニタリング設定

---

### v1.0.0 - 本番リリース (Phase 10) 🚀
**予定日**: 未定

**マイルストーン**:
- 全機能実装完了
- テスト完了
- ドキュメント完備
- 本番環境デプロイ

---

## メンテナンス方針

### セキュリティアップデート
- 重大な脆弱性: 即座にパッチリリース
- 軽微な脆弱性: 次回マイナーバージョンに含める

### 依存関係更新
- Python パッケージ: 月次チェック
- Docker ベースイメージ: 月次チェック

### バックポート方針
- メジャーバージョンの最新版のみサポート
- セキュリティパッチは前バージョンにもバックポート

---

## 連絡先

**メンテナ**: system-admin
**問い合わせ**: Tailscale VPN 経由で連絡
**バグレポート**: `/opt/onprem-infra-system/project-root-infra/Docs/application/mailserver/usermgmt/` 配下に issue.md を作成

---

## リンク

- **プロジェクト概要**: [README.md](README.md)
- **開発進捗**: [DEVELOPMENT.md](DEVELOPMENT.md)
- **API仕様**: [API.md](API.md)
- **設計書**: [../05_user_management_design.md](../05_user_management_design.md)
