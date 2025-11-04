# 開発進捗トラッキング (Development Progress)

**最終更新**: 2025-11-05
**現在のフェーズ**: Phase 1 - ドキュメント整備
**全体進捗**: 10% (1/10 フェーズ完了)

---

## 📊 全体ロードマップ

| Phase | タスク | ステータス | 開始日 | 完了日 | 担当者 |
|-------|--------|----------|--------|--------|--------|
| **Phase 0** | プロジェクト初期化 | ✅ 完了 | 2025-11-04 | 2025-11-04 | system-admin |
| **Phase 1** | ドキュメント整備 | ✅ 完了 | 2025-11-05 | 2025-11-05 | system-admin |
| **Phase 2** | データベース基盤構築 | ⏳ 未着手 | - | - | - |
| **Phase 3** | 認証システム実装 | ⏳ 未着手 | - | - | - |
| **Phase 4** | ユーザCRUD機能実装 | ⏳ 未着手 | - | - | - |
| **Phase 5** | UI/テンプレート実装 | ⏳ 未着手 | - | - | - |
| **Phase 6** | Dovecot SQL認証統合 | ⏳ 未着手 | - | - | - |
| **Phase 7** | Nginx統合 | ⏳ 未着手 | - | - | - |
| **Phase 8** | テスト・検証 | ⏳ 未着手 | - | - | - |
| **Phase 9** | 本番デプロイ準備 | ⏳ 未着手 | - | - | - |
| **Phase 10** | 本番リリース | ⏳ 未着手 | - | - | - |

---

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

### 成果物

- `README.md` - プロジェクトの全体像、アーキテクチャ、セットアップ手順
- `DEVELOPMENT.md` - フェーズ別進捗管理
- `API.md` - RESTful API 仕様書
- `CHANGELOG.md` - バージョン管理と変更履歴

### 課題・メモ

- ドキュメントは開発進行に伴い継続的に更新
- 設計書 (`05_user_management_design.md`) との整合性維持

---

## Phase 2: データベース基盤構築 ⏳

**期間**: 未定
**ステータス**: 未着手
**見積もり**: 2-3時間

### タスク一覧

- [ ] `app/services/database.py` - SQLAlchemy 初期化、DB接続管理
- [ ] `app/models/user.py` - User モデル定義
- [ ] `app/models/domain.py` - Domain モデル定義
- [ ] `app/models/audit_log.py` - AuditLog モデル定義
- [ ] `scripts/init_db.py` - MariaDB スキーマ作成スクリプト
- [ ] MariaDB データベース作成 (`mailserver_usermgmt`)
- [ ] テーブル作成 (users, domains, audit_logs)
- [ ] DB接続テスト

### 前提条件

- MariaDB コンテナ稼働中 (`mailserver-mariadb`)
- `.env` ファイルに `USERMGMT_DB_PASSWORD` 設定済み

### 成果物 (予定)

- SQLAlchemy モデル定義ファイル
- データベーススキーマ (SQL)
- 初期化スクリプト

### 技術メモ

```python
# SQLAlchemy 設定例
SQLALCHEMY_DATABASE_URI = f"mysql+pymysql://{DB_USER}:{DB_PASSWORD}@{DB_HOST}:{DB_PORT}/{DB_NAME}"
SQLALCHEMY_TRACK_MODIFICATIONS = False
```

---

## Phase 3: 認証システム実装 ⏳

**期間**: 未定
**ステータス**: 未着手
**見積もり**: 2-3時間

### タスク一覧

- [ ] Flask-Login 統合
- [ ] `app/routes/auth.py` - ログイン/ログアウトルート
- [ ] `app/services/password.py` - パスワードハッシュ化 (SHA512-CRYPT)
- [ ] `templates/login.html` - ログイン画面
- [ ] セッション管理 (Cookie設定)
- [ ] CSRF 保護 (Flask-WTF)
- [ ] 認証デコレータ (`@login_required`)

### 前提条件

- Phase 2 (データベース基盤) 完了

### 成果物 (予定)

- ログイン/ログアウト機能
- セッション管理
- 管理者認証

### 技術メモ

```python
# パスワードハッシュ化
from passlib.hash import sha512_crypt

def hash_password(password: str) -> str:
    return "{SHA512-CRYPT}" + sha512_crypt.hash(password)
```

---

## Phase 4: ユーザCRUD機能実装 ⏳

**期間**: 未定
**ステータス**: 未着手
**見積もり**: 4-5時間

### タスク一覧

- [ ] `app/routes/users.py` - ユーザ管理ルート
- [ ] `app/services/user_service.py` - ユーザ操作ビジネスロジック
- [ ] ユーザ一覧表示 (`GET /users`)
- [ ] ユーザ作成 (`POST /users/new`)
- [ ] ユーザ編集 (`POST /users/<email>/edit`)
- [ ] ユーザ削除 (`POST /users/<email>/delete`)
- [ ] パスワード変更 (`POST /users/<email>/password`)
- [ ] 監査ログ記録

### 前提条件

- Phase 2 (データベース基盤) 完了
- Phase 3 (認証システム) 完了

### 成果物 (予定)

- ユーザCRUD API エンドポイント
- ビジネスロジック実装
- 監査ログ機能

### 技術メモ

```python
# ユーザ作成例
@app.route('/users/new', methods=['POST'])
@login_required
def create_user():
    email = request.form['email']
    password = request.form['password']
    quota = int(request.form.get('quota', 1024))

    # ユーザ作成ロジック
    user_service.create_user(email, password, quota)

    # 監査ログ記録
    audit_log.log('USER_CREATED', email, request.remote_addr)

    flash('ユーザを作成しました', 'success')
    return redirect(url_for('users.list'))
```

---

## Phase 5: UI/テンプレート実装 ⏳

**期間**: 未定
**ステータス**: 未着手
**見積もり**: 3-4時間

### タスク一覧

- [ ] `templates/base.html` - ベーステンプレート (Bootstrap 5)
- [ ] `templates/dashboard.html` - ダッシュボード
- [ ] `templates/users/list.html` - ユーザ一覧
- [ ] `templates/users/create.html` - ユーザ作成フォーム
- [ ] `templates/users/edit.html` - ユーザ編集フォーム
- [ ] `templates/domains/list.html` - ドメイン一覧
- [ ] `static/css/custom.css` - カスタムスタイル
- [ ] `static/js/validation.js` - フォームバリデーション
- [ ] レスポンシブデザイン対応 (モバイル/タブレット)

### 前提条件

- Phase 4 (ユーザCRUD機能) 完了

### 成果物 (予定)

- Bootstrap 5 ベースの UI
- レスポンシブデザイン
- フォームバリデーション

### デザインガイドライン

- **カラースキーム**: Bootstrap 5 デフォルト + カスタムカラー
- **フォント**: システムフォント (游ゴシック、Segoe UI)
- **アイコン**: Bootstrap Icons
- **レイアウト**: サイドバーナビゲーション

---

## Phase 6: Dovecot SQL認証統合 ⏳

**期間**: 未定
**ステータス**: 未着手
**見積もり**: 2-3時間

### タスク一覧

- [ ] `dovecot-sql.conf.ext` 作成 (MariaDB接続設定)
- [ ] `auth-sql.conf.ext` 作成 (SQL認証設定)
- [ ] `dovecot.conf` に `!include auth-sql.conf.ext` 追加
- [ ] Dovecot 再起動
- [ ] SQL認証テスト (既存ユーザでIMAPログイン)
- [ ] File認証とSQL認証の並行稼働確認

### 前提条件

- Phase 4 (ユーザCRUD機能) 完了
- MariaDB に users テーブル存在

### 成果物 (予定)

- Dovecot SQL認証設定ファイル
- File認証との並行稼働

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

**期間**: 未定
**ステータス**: 未着手
**見積もり**: 1-2時間

### タスク一覧

- [ ] Nginx 設定ファイル編集 (`config/nginx/templates/mailserver.conf.template`)
- [ ] `/admin` パス追加 (usermgmt コンテナへプロキシ)
- [ ] Tailscale IP アドレスチェック (`geo $tailscale_ip`)
- [ ] HTTPS 強制リダイレクト
- [ ] Cookie 設定 (HttpOnly, Secure, SameSite)
- [ ] Nginx reload
- [ ] アクセステスト (Tailscale VPN 経由)

### 前提条件

- Phase 5 (UI/テンプレート) 完了
- usermgmt コンテナ稼働中

### 成果物 (予定)

- Nginx リバースプロキシ設定
- Tailscale VPN アクセス制限

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

**期間**: 未定
**ステータス**: 未着手
**見積もり**: 2-3時間

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
- [ ] パフォーマンステスト
- [ ] レスポンシブデザインテスト (モバイル/タブレット)

### 成果物 (予定)

- テストコード (pytest)
- テストカバレッジレポート
- 検証チェックリスト

---

## Phase 9: 本番デプロイ準備 ⏳

**期間**: 未定
**ステータス**: 未着手
**見積もり**: 2時間

### タスク一覧

- [ ] docker-compose.yml に usermgmt サービス追加
- [ ] 環境変数設定 (`.env` ファイル)
- [ ] バックアップスクリプト作成
- [ ] ロールバック手順書作成
- [ ] モニタリング設定 (ログ監視)
- [ ] ドキュメント最終確認

### 成果物 (予定)

- デプロイ手順書
- ロールバック手順書
- バックアップスクリプト

---

## Phase 10: 本番リリース ⏳

**期間**: 未定
**ステータス**: 未着手
**見積もり**: 1時間

### タスク一覧

- [ ] 本番環境デプロイ
- [ ] 最終検証チェックリスト実施
- [ ] 既存ユーザ認証確認
- [ ] 新規ユーザ作成テスト
- [ ] パスワード変更テスト
- [ ] 監査ログ確認
- [ ] リリースノート作成

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

1. **データベース**: MariaDB ベースのアプローチを採用 (File ベースは採用しない)
   - 理由: 監査ログ、検索機能、将来拡張を考慮
   - 既存環境への影響: Dovecot 設定に `!include auth-sql.conf.ext` 追加のみ

2. **認証方式**: File 認証と SQL 認証の並行稼働
   - 理由: 既存ユーザとの互換性維持、段階的移行
   - 移行フェーズ不要

3. **UI フレームワーク**: Bootstrap 5
   - 理由: レスポンシブデザイン対応、モバイルデバイス管理に最適

4. **パスワードハッシュ**: SHA512-CRYPT
   - 理由: Dovecot 標準方式、既存環境との互換性

### パフォーマンス最適化メモ

- SQLAlchemy のコネクションプール設定
- Gunicorn ワーカー数: 2 (CPU 1コア想定)
- Nginx リバースプロキシキャッシュ (静的ファイル)

### セキュリティ強化メモ

- Tailscale VPN アクセス制限 (100.0.0.0/10)
- HTTPS 強制
- CSRF 保護 (Flask-WTF)
- セッション Cookie 設定 (HttpOnly, Secure, SameSite=Strict)

---

## 📅 次回のレビュー

**予定日**: Phase 2 完了後
**レビュー項目**:
- データベーススキーマの妥当性
- モデル定義の完全性
- DB接続の安定性

---

## 📞 連絡先

**開発担当**: system-admin
**レビュー担当**: system-admin
**質問・相談**: Tailscale VPN 経由で連絡
