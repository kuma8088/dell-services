# Unified Portal - 統合管理ポータル

Blog SystemとMailserverを統一管理するWebベースの管理ポータル。

## 📋 概要

**目的**: Xserver風の直感的なUIで、Docker環境、WordPress、メールサーバー、ドメイン、バックアップを一元管理

**技術スタック**:
- **Backend**: FastAPI (Python 3.9+)
- **Frontend**: React 18 + TypeScript + Vite 5
- **UI Framework**: Tailwind CSS 3 + shadcn/ui
- **State Management**: Zustand + TanStack Query
- **Database**: SQLite (開発) / PostgreSQL or MySQL (本番)
- **外部連携**: Cloudflare API, Docker API, WordPress API

## 🎯 実装状況

### ✅ Phase 1: 基盤構築（実装中）

**完了済み**:
- ✅ プロジェクト構造作成
- ✅ FastAPI バックエンド基盤
  - config.py - 設定管理
  - database.py - SQLAlchemy ORM
  - main.py - アプリケーションエントリーポイント
- ✅ React フロントエンド基盤
  - Vite + TypeScript セットアップ
  - Tailwind CSS + shadcn/ui 統合
  - ルーティング設定（React Router）
- ✅ **Cloudflare DNS API統合** (2025-11-13完了)
  - ゾーン一覧取得
  - DNSレコードCRUD操作
  - Cloudflareプロキシ設定
  - TypeScript型定義完備
- ✅ Redis Object Cache統合（WordPress高速化）
  - docker-compose.yml更新
  - セットアップスクリプト
  - 性能テストツール
- ✅ 8つの管理ページUI実装
  - Dashboard - システム概要
  - Docker Management - コンテナ管理
  - Database Management - DB管理
  - PHP Management - PHP設定管理
  - Security Management - セキュリティ監視
  - WordPress Management - WPサイト管理
  - **Domain Management** - ドメイン・DNS管理（Cloudflare統合完了）
  - Backup Management - バックアップ管理

**実装中**:
- 🔄 残りのAPI統合（Docker, Database, PHP, Security, WordPress, Backup）
- 🔄 認証システム（JWT）
- 🔄 WebSocket（リアルタイム更新）

### 📝 Phase 2-4（計画中）

**Phase 2**: API統合完了
- Docker API統合（コンテナ管理）
- WordPress REST API統合（サイト管理）
- MariaDB管理API（データベース操作）
- バックアップAPI（restore/backup操作）

**Phase 3**: 高度な機能
- WebSocketによるリアルタイム更新
- SSO（Single Sign-On）統合
- 監視・アラート機能
- ログ集約・検索

**Phase 4**: 本番デプロイ
- Docker Compose本番設定
- Nginx リバースプロキシ
- SSL証明書設定
- CloudWatch統合

## 📚 ドキュメント

### 必読ドキュメント

1. **[ARCHITECTURE.md](ARCHITECTURE.md)** - アーキテクチャ設計
   - システム構成図
   - 技術選定理由
   - API設計方針
   - UI/UX設計（Xserver風）
   - 実装ロードマップ

2. **[LOCAL_DEVELOPMENT.md](LOCAL_DEVELOPMENT.md)** - ローカル開発環境
   - セットアップ手順
   - 開発サーバー起動方法
   - テスト実行方法
   - デバッグ手順
   - トラブルシューティング

3. **[CLOUDFLARE-API-INTEGRATION.md](CLOUDFLARE-API-INTEGRATION.md)** - Cloudflare統合
   - APIトークン作成手順
   - エンドポイント仕様
   - リクエスト/レスポンス例
   - セキュリティベストプラクティス
   - BIND vs Cloudflare比較
   - トラブルシューティング

## 🚀 クイックスタート

### 前提条件

- Python 3.9以上
- Node.js 18以上
- npm または yarn
- Docker（Docker API統合時に必要）
- Cloudflare API トークン（DNS管理時に必要）

### バックエンドセットアップ

```bash
cd services/unified-portal/backend

# 仮想環境作成
python -m venv venv
source venv/bin/activate  # Windows: venv\Scripts\activate

# 依存関係インストール
pip install -r requirements.txt

# 環境変数設定
cp .env.example .env
# .env を編集（特にCLOUDFLARE_API_TOKENを設定）

# 開発サーバー起動
python -m app.main
```

バックエンドAPI: http://localhost:8000
API ドキュメント: http://localhost:8000/docs

### フロントエンドセットアップ

```bash
cd services/unified-portal/frontend

# 依存関係インストール
npm install

# 環境変数設定
cp .env.example .env
# .env を編集（VITE_API_BASE_URLは通常デフォルトのままでOK）

# 開発サーバー起動
npm run dev
```

フロントエンド: http://localhost:5173

## 🔧 主要機能

### 1. Dashboard（ダッシュボード）

**機能**:
- システム全体の健全性表示
- リソース使用状況（CPU, RAM, ディスク）
- サービスステータス一覧
- 最近のアクティビティ
- アラート通知

**実装状況**: UI完成、API統合待ち

### 2. Domain Management（ドメイン管理）✅

**機能**:
- Cloudflareアカウントの全ゾーン表示
- DNSレコード一覧・検索
- DNSレコード作成（A, AAAA, CNAME, MX, TXT, NS, SRV）
- DNSレコード削除
- Cloudflareプロキシ設定（オレンジクラウド）
- TTL設定
- ゾーン情報表示（ステータス、ネームサーバー）

**実装状況**: ✅ **完全実装済み**（2025-11-13）

**参照**: [CLOUDFLARE-API-INTEGRATION.md](CLOUDFLARE-API-INTEGRATION.md)

### 3. Docker Management（Docker管理）

**機能**:
- 全コンテナ一覧表示
- コンテナ起動/停止/再起動
- ログ表示（リアルタイム）
- リソース使用状況
- ヘルスチェック
- イメージ管理

**実装状況**: UI完成、API統合待ち

### 4. WordPress Management（WordPress管理）

**機能**:
- 16サイトの一覧表示
- 新規サイト作成ウィザード
- サイト設定編集
- プラグイン管理
- テーマ管理
- バックアップ/リストア
- WP Mail SMTP設定

**実装状況**: UI完成、API統合待ち

### 5. Database Management（データベース管理）

**機能**:
- データベース一覧
- ユーザー管理
- SQLクエリ実行
- データベース作成/削除
- エクスポート/インポート
- 使用量表示

**実装状況**: UI完成、API統合待ち

### 6. PHP Management（PHP管理）

**機能**:
- PHP バージョン表示
- 拡張モジュール一覧
- php.ini設定表示・編集
- PHP-FPM 設定
- エラーログ表示

**実装状況**: UI完成、API統合待ち

### 7. Security Management（セキュリティ管理）

**機能**:
- セキュリティスコア表示
- 脆弱性チェック
- Wordfenceステータス
- XMLRPC無効化状況
- SSL証明書ステータス
- セキュリティヘッダー確認
- ワンクリック対策適用

**実装状況**: UI完成、API統合待ち

**参照**: [SECURITY-ANALYSIS.md](../blog/SECURITY-ANALYSIS.md)

### 8. Backup Management（バックアップ管理）

**機能**:
- バックアップ一覧表示
- 手動バックアップ実行
- スケジュール設定
- リストア操作
- S3同期状況
- ストレージ使用量

**実装状況**: UI完成、API統合待ち

## 🏗️ プロジェクト構造

```
services/unified-portal/
├── backend/                    # FastAPI バックエンド
│   ├── app/
│   │   ├── routers/           # APIルーター
│   │   │   ├── __init__.py
│   │   │   └── domains.py     # Cloudflare DNS API ✅
│   │   ├── config.py          # 設定管理
│   │   ├── database.py        # SQLAlchemy ORM
│   │   └── main.py            # エントリーポイント
│   ├── requirements.txt       # Python依存関係
│   └── .env.example           # 環境変数テンプレート
├── frontend/                   # React フロントエンド
│   ├── src/
│   │   ├── components/        # UIコンポーネント
│   │   │   ├── layout/        # レイアウト
│   │   │   └── ui/            # shadcn/ui
│   │   ├── pages/             # ページコンポーネント
│   │   │   ├── Dashboard.tsx
│   │   │   ├── DomainManagement.tsx  ✅
│   │   │   ├── DockerManagement.tsx
│   │   │   ├── WordPressManagement.tsx
│   │   │   ├── DatabaseManagement.tsx
│   │   │   ├── PhpManagement.tsx
│   │   │   ├── SecurityManagement.tsx
│   │   │   └── BackupManagement.tsx
│   │   ├── lib/               # ユーティリティ
│   │   │   ├── api.ts         # ベースAPIクライアント
│   │   │   └── domains-api.ts # ドメインAPI ✅
│   │   ├── App.tsx            # ルートコンポーネント
│   │   └── main.tsx           # エントリーポイント
│   ├── package.json           # npm依存関係
│   └── .env.example           # 環境変数テンプレート
└── docker-compose.yml         # 開発環境構成
```

## 🔗 関連Issue

- **I001**: 管理ポータル統合（Blog + Mailserver）- 🔄 実装中
- **I002**: ポータルデザイン刷新 - ✅ Xserver風UI完成
- **I003**: ポータル機能拡張 - 🔄 実装中
- **I006**: Redisキャッシュシステム - ✅ 完了（2025-11-13）

詳細: [docs/application/blog/issue/active/01_improvement+issue.md](../blog/issue/active/01_improvement+issue.md)

## 🛠️ 開発ガイドライン

### コーディング規約

**Python (Backend)**:
- PEP 8準拠
- Black フォーマッター（行長88）
- Type hints必須
- Docstring記述（Google Style）

**TypeScript (Frontend)**:
- ESLint + Prettier
- Strict mode有効
- 関数コンポーネント優先
- カスタムフック活用

### テスト

**Backend**:
```bash
pytest backend/tests -v --cov=app
```

**Frontend**:
```bash
npm run test
```

### コミットメッセージ

Conventional Commits形式:
- `feat:` - 新機能
- `fix:` - バグ修正
- `docs:` - ドキュメント
- `refactor:` - リファクタリング
- `test:` - テスト追加

例:
```
feat(domains): Add Cloudflare DNS record deletion
```

## 📖 参考資料

- [FastAPI Documentation](https://fastapi.tiangolo.com/)
- [React Documentation](https://react.dev/)
- [Tailwind CSS](https://tailwindcss.com/)
- [shadcn/ui](https://ui.shadcn.com/)
- [Cloudflare API](https://developers.cloudflare.com/api/)

## 🤝 コントリビューション

1. 新機能実装前に Issue を作成
2. `docs/application/unified-portal/` 配下にドキュメント追加
3. テストを書いてカバレッジ維持
4. Pull Request作成

## 📝 TODO

- [ ] 認証システム実装（JWT + Cookie）
- [ ] Docker API統合
- [ ] WordPress REST API統合
- [ ] WebSocket実装（リアルタイム更新）
- [ ] E2Eテスト（Playwright）
- [ ] CI/CD パイプライン
- [ ] 本番環境デプロイ設定

---

**作成日**: 2025-11-13
**最終更新**: 2025-11-13
**ステータス**: 🔄 Phase 1実装中
