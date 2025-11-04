# 変更履歴 (Changelog)

このファイルは、メールユーザ管理システムの主要な変更履歴を記録します。

フォーマットは [Keep a Changelog](https://keepachangelog.com/ja/1.0.0/) に基づいています。
バージョン管理は [Semantic Versioning](https://semver.org/lang/ja/) に従います。

---

## 📊 リリース戦略：MVP → Extended

本プロジェクトは**段階的リリース**戦略を採用しています：

- **MVP（最小実用製品）**: v0.1.0 〜 v0.5.0（Phase 0-5）
  - 基本的なWeb UI経由でのユーザ管理機能
  - MariaDB + Flask + Bootstrap 5による管理画面

- **Extended（拡張構成）**: v0.6.0 〜 v1.0.0（Phase 6-10）
  - Dovecot SQL認証統合
  - Nginx統合
  - 包括的なテスト・本番環境対応

---

## [Unreleased] - 開発中

### MVP フェーズ (Phase 2-5) - v0.5.0 に向けて
- データベースモデル実装 (User, AuditLog) - Phase 2
- Flask-Login 認証システム - Phase 3
- ユーザCRUD操作 (作成・編集・削除) - Phase 4
- Bootstrap 5 ベースのUI - Phase 5
- レスポンシブデザイン (モバイル対応) - Phase 5

### Extended フェーズ (Phase 6-10) - v1.0.0 に向けて
- Dovecot SQL認証統合 - Phase 6
- Nginx リバースプロキシ設定 - Phase 7
- 包括的なテストスイート - Phase 8
- 本番デプロイ自動化 - Phase 9

---

## [0.1.0] - 2025-11-05

### 追加 (Added)
- **ドキュメント整備（MVP/Extended フェーズ分離）**:
  - `README.md` - プロジェクト概要、MVP/Extended アーキテクチャ、セットアップ手順
  - `DEVELOPMENT.md` - 開発進捗トラッキング（MVP: Phase 0-5、Extended: Phase 6-10）
  - `API.md` - API エンドポイント仕様（MVP/Extended分離）
  - `CHANGELOG.md` - 変更履歴 (本ファイル、MVP マイルストーン追加)

### 変更 (Changed)
- ドキュメント配置場所を `services/mailserver/usermgmt/` から `docs/application/mailserver/usermgmt/` に変更（小文字 `docs`）
- **開発方針**: 段階的リリース戦略を採用（MVP v0.5.0 → Extended v1.0.0）
- Phase 構成を MVP/Extended に分離:
  - **MVP**: Phase 0-5（基本機能実装）
  - **Extended**: Phase 6-10（拡張機能・本番対応）

---

## [0.0.1] - 2025-11-04

### 追加 (Added)
- **プロジェクト初期化（Phase 0）**:
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

# 📅 MVP リリースロードマップ（v0.5.0）

## [0.2.0] - データベース基盤構築 (Phase 2) ⏳

**予定日**: 未定
**優先度**: 🔴 高（MVP必須）

### 追加予定 (Planned)
- SQLAlchemy モデル定義
  - `app/models/user.py` - User モデル（email, password_hash, maildir, quota, enabled）
  - `app/models/audit_log.py` - AuditLog モデル（簡易版：作成・更新・削除イベント）
- `app/services/database.py` - SQLAlchemy 初期化、DB接続管理
- `scripts/init_db.py` - MariaDB スキーマ作成スクリプト
- DB接続テスト

### 技術的決定
- MariaDB データベース: `mailserver_usermgmt`
- 接続プール設定: POOL_SIZE=5, POOL_RECYCLE=3600

---

## [0.3.0] - 認証システム実装 (Phase 3) ⏳

**予定日**: 未定
**優先度**: 🔴 高（MVP必須）

### 追加予定 (Planned)
- Flask-Login 統合
- `app/routes/auth.py` - ログイン/ログアウトルート
- `app/services/password.py` - パスワードハッシュ化 (SHA512-CRYPT)
- `templates/login.html` - ログイン画面（Bootstrap 5）
- セッション管理（HttpOnly, Secure Cookie）
- CSRF 保護（Flask-WTF）
- 認証デコレータ (`@login_required`)

### セキュリティ
- パスワードハッシュ: SHA512-CRYPT（Dovecot互換）
- セッションCookie: HttpOnly, Secure, SameSite=Strict

---

## [0.4.0] - ユーザCRUD機能実装 (Phase 4) ⏳

**予定日**: 未定
**優先度**: 🔴 高（MVP必須）

### 追加予定 (Planned)
- `app/routes/users.py` - ユーザ管理ルート
- `app/services/user_service.py` - ユーザ操作ビジネスロジック
- ユーザ一覧表示 (`GET /users`)
- ユーザ作成 (`POST /users/new`)
  - maildir自動生成: `/var/mail/vmail/{domain}/{username}/`
- ユーザ編集 (`POST /users/<email>/edit`)
- ユーザ削除 (`POST /users/<email>/delete`)
- パスワード変更 (`POST /users/<email>/password`)
- 基本的な監査ログ記録（作成・更新・削除イベント）

### データ永続化
- MariaDB `users` テーブルへのCRUD操作
- `audit_logs` テーブルへの操作履歴記録

---

## [0.5.0] - UI/テンプレート実装 (Phase 5) 🎯 **MVP マイルストーン**

**予定日**: 未定
**優先度**: 🔴 高（MVP完了条件）

### 追加予定 (Planned)
- `templates/base.html` - ベーステンプレート（Bootstrap 5）
- `templates/dashboard.html` - ダッシュボード（ユーザ数表示）
- `templates/users/list.html` - ユーザ一覧
- `templates/users/create.html` - ユーザ作成フォーム
- `templates/users/edit.html` - ユーザ編集フォーム
- `static/css/custom.css` - カスタムスタイル（最小限）
- `static/js/validation.js` - フォームバリデーション
- レスポンシブデザイン対応（PC/Mac/スマホ/タブレット）

### デザインガイドライン
- カラースキーム: Bootstrap 5 デフォルト
- フォント: システムフォント（游ゴシック、Segoe UI）
- アイコン: Bootstrap Icons（CDN経由）
- レイアウト: シンプルなトップナビゲーション

### MVP 完了条件
このバージョンで以下の条件を満たす：
- ✅ Webブラウザから管理画面にアクセス可能
- ✅ ログイン認証が機能している
- ✅ ユーザの新規作成・編集・削除が可能
- ✅ MariaDBに変更が永続化されている
- ✅ 基本的なUI（Bootstrap 5）が動作している（PC/スマホ対応）
- ✅ 簡易な監査ログ（作成・更新・削除イベント）

---

# 🚀 Extended リリースロードマップ（v1.0.0）

## [0.6.0] - Dovecot SQL認証統合 (Phase 6) ⏳

**予定日**: MVP完了後
**優先度**: 🟡 中（Extended拡張）

### 追加予定 (Planned)
- `services/mailserver/config/dovecot/dovecot-sql.conf.ext` - MariaDB接続設定
- `services/mailserver/config/dovecot/auth-sql.conf.ext` - SQL認証設定
- File認証とSQL認証の並行稼働
- SQL認証テスト手順書

### 変更 (Changed)
- `dovecot.conf` に `!include auth-sql.conf.ext` 追加
- Dovecot 再起動手順整備（ダウンタイム約5秒）

### 検証項目
- 既存ユーザ（File認証）でIMAPログイン可能
- 新規ユーザ（SQL認証）でIMAPログイン可能
- Web管理画面で作成したユーザで即座にメール受信可能

---

## [0.7.0] - Nginx統合 (Phase 7) ⏳

**予定日**: MVP完了後
**優先度**: 🟡 中（Extended拡張）

### 追加予定 (Planned)
- Nginx `/admin` パス設定（usermgmtコンテナへプロキシ）
- Tailscale VPN アクセス制限（geo ディレクティブ: `100.0.0.0/10`）
- HTTPS 強制リダイレクト
- セキュアCookie設定（HttpOnly, Secure, SameSite=Strict）

### セキュリティ強化
- Tailscale VPN外からのアクセス拒否（403 Forbidden）
- HTTPS経由のみアクセス可能（HTTP→HTTPS自動リダイレクト）

---

## [0.8.0] - テスト・検証 (Phase 8) ⏳

**予定日**: MVP完了後
**優先度**: 🟢 低（Extended拡張）

### 追加予定 (Planned)
- ユニットテスト（pytest）
  - `tests/test_models.py` - モデルテスト
  - `tests/test_routes.py` - ルートテスト
  - `tests/test_services.py` - サービスロジックテスト
- 統合テスト
  - ユーザ作成 → IMAP ログインテスト
  - パスワード変更 → IMAP ログインテスト
  - ユーザ削除 → IMAP ログイン失敗テスト
- セキュリティテスト
  - CSRF 保護確認
  - SQLインジェクション対策確認
  - XSS 対策確認
- パフォーマンステスト
- テストカバレッジレポート

---

## [0.9.0] - 本番デプロイ準備 (Phase 9) ⏳

**予定日**: MVP完了後
**優先度**: 🟡 中（Extended拡張）

### 追加予定 (Planned)
- docker-compose.yml に usermgmt サービス統合
- 環境変数設定（`.env` ファイルテンプレート）
- バックアップスクリプト（MariaDB ダンプ自動化）
- ロールバック手順書
- モニタリング設定（ログ監視、アラート）

---

## [1.0.0] - 本番リリース (Phase 10) 🚀

**予定日**: MVP安定稼働後
**優先度**: 🟢 低（Extended完了）

### マイルストーン
- 全機能実装完了（MVP + Extended）
- テスト完了（ユニット・統合・セキュリティ・パフォーマンス）
- ドキュメント完備（運用手順書、トラブルシューティング）
- 本番環境デプロイ完了

### 最終検証チェックリスト
- ✅ 既存ユーザ（test@kuma8088.com）でIMAPログイン可能
- ✅ Webアプリから新規ユーザ作成可能
- ✅ 作成したユーザで即座にIMAPログイン可能
- ✅ パスワード変更後、新パスワードでログイン可能
- ✅ ユーザ削除後、IMAPログイン不可
- ✅ 監査ログに全操作が記録されている
- ✅ Tailscale VPN 外からのアクセスが拒否される
- ✅ バックアップ・ロールバック手順が確立されている

---

## メンテナンス方針

### セキュリティアップデート
- 重大な脆弱性: 即座にパッチリリース
- 軽微な脆弱性: 次回マイナーバージョンに含める

### 依存関係更新
- Python パッケージ: 月次チェック（`pip list --outdated`）
- Docker ベースイメージ: 月次チェック

### バックポート方針
- メジャーバージョンの最新版のみサポート
- セキュリティパッチは前バージョンにもバックポート

---

## 連絡先

**メンテナ**: system-admin
**問い合わせ**: Tailscale VPN 経由で連絡
**バグレポート**: `docs/application/mailserver/usermgmt/` 配下に issue.md を作成

---

## リンク

- **プロジェクト概要**: [README.md](README.md) ← **MVP/Extended アーキテクチャ分離済み**
- **開発進捗**: [DEVELOPMENT.md](DEVELOPMENT.md) ← **MVP/Extended フェーズ管理**
- **API仕様**: [API.md](API.md)
- **設計書**: [../05_user_management_design.md](../05_user_management_design.md)
