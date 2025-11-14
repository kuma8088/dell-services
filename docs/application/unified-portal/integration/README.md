# Unified Portal 統合プロジェクト

**プロジェクト名**: Mailserver Usermgmt統合 + DNS管理強化 + 追加機能実装

**目的**: 既存のMailserver usermgmt（Flask）の機能をUnified Portal（FastAPI + React）に統合し、統一された管理ポータルを構築する。

**安全性方針**: 既存コードを変更せず、並行稼働可能な形で段階的に実装

---

## 📋 ドキュメント一覧

### 1. 実装要件（REQUIREMENTS）
**ファイル**: [01_REQUIREMENTS.md](01_REQUIREMENTS.md)

**内容**:
- ビジネス要件
- 機能要件
- 非機能要件
- 制約事項

### 2. アーキテクチャ設計（ARCHITECTURE）
**ファイル**: [02_ARCHITECTURE.md](02_ARCHITECTURE.md)

**内容**:
- システム構成図
- データフロー
- 既存システムとの連携方法
- 技術スタック詳細

### 3. タスク分解（TASK BREAKDOWN）
**ファイル**: [03_TASK_BREAKDOWN.md](03_TASK_BREAKDOWN.md)

**内容**:
- 全タスクリスト
- **Web側実装タスク**（Claude Code on the webで実行可能）
- **ローカル側実装タスク**（ローカル環境で実行必要）
- 依存関係
- 優先順位

### 4. Web側実装ガイド（WEB IMPLEMENTATION）
**ファイル**: [04_WEB_IMPLEMENTATION.md](04_WEB_IMPLEMENTATION.md)

**内容**:
- Web側で実装するファイル一覧
- コード生成内容
- 実行手順
- 検証方法

### 5. ローカル側実装ガイド（LOCAL IMPLEMENTATION）
**ファイル**: [05_LOCAL_IMPLEMENTATION.md](05_LOCAL_IMPLEMENTATION.md)

**内容**:
- ローカルで実行する作業一覧
- 環境構築手順
- Docker Compose設定変更
- データベース接続設定
- 動作確認手順
- トラブルシューティング

### 6. API仕様（API SPECIFICATION）
**ファイル**: [06_API_SPECIFICATION.md](06_API_SPECIFICATION.md)

**内容**:
- 全エンドポイント一覧
- リクエスト/レスポンス仕様
- 認証方式
- エラーハンドリング

### 7. テスト計画（TEST PLAN）
**ファイル**: [07_TEST_PLAN.md](07_TEST_PLAN.md)

**内容**:
- 単体テスト計画
- 統合テスト計画
- E2Eテスト計画
- テストケース一覧

### 8. ロールバック計画（ROLLBACK PLAN）
**ファイル**: [08_ROLLBACK_PLAN.md](08_ROLLBACK_PLAN.md)

**内容**:
- 問題発生時の切り戻し手順
- データ保護戦略
- 並行稼働期間の管理

---

## 🎯 プロジェクト概要

### Phase 1: Mailserver機能統合
- メールユーザー管理（CRUD）
- メールドメイン管理（CRUD）
- 監査ログ表示
- 既存MariaDBへの接続

### Phase 2: DNS管理強化（#017）
- Cloudflareダッシュボードリンク
- DNSレコード編集機能
- バルク操作
- DNS検証ツール

### Phase 3: 追加機能
- 認証統一（JWT + RBAC）
- Docker Management API
- WordPress Management API
- Database Management API
- その他管理機能

---

## 🏗️ 実装戦略

### 既存システムへの影響ゼロ
1. **新規ディレクトリで開発**
   - `services/unified-portal/` 配下に全て実装
   - 既存 `services/mailserver/usermgmt/` は一切変更しない

2. **並行稼働**
   - Flask usermgmtとFastAPI Unified Portalを同時稼働
   - 段階的にユーザーを移行
   - 問題があればすぐ切り戻し可能

3. **データベース共有**
   - 既存MariaDB（`mailserver_usermgmt`）を共有
   - テーブル構造は変更しない
   - SQLAlchemy ORMで既存テーブルをマッピング

### Web側とローカル側の分離
| 作業内容 | 実行場所 | 理由 |
|---------|---------|------|
| ファイル作成・コード生成 | **Web側** | エディタ不要、高速 |
| Docker Compose起動確認 | **ローカル** | Dockerデーモンが必要 |
| データベース接続確認 | **ローカル** | Dell WorkStationのMariaDBに接続 |
| API動作確認 | **ローカル** | 実際の環境で検証 |
| フロントエンドビルド | **Web側** | npm installのみローカル |

---

## 📅 実装スケジュール（推奨）

### Week 1: ドキュメント作成 + Web側実装
- [ ] Day 1-2: 全ドキュメント作成（Web側で完了）
- [ ] Day 3-4: バックエンドコード生成（Web側で完了）
- [ ] Day 5: フロントエンドコード生成（Web側で完了）

### Week 2: ローカル統合 + テスト
- [ ] Day 1-2: ローカル環境構築・DB接続
- [ ] Day 3-4: 動作確認・デバッグ
- [ ] Day 5: 並行稼働テスト

### Week 3: 本番デプロイ + 移行
- [ ] Day 1-2: 本番環境デプロイ
- [ ] Day 3-4: ユーザー移行
- [ ] Day 5: 旧システム廃止準備

---

## ✅ 成功基準

### Phase 1完了条件
- [ ] Unified PortalからメールユーザーCRUD操作が可能
- [ ] 監査ログが正常に記録される
- [ ] Flask usermgmtと同等の機能を提供
- [ ] レスポンスタイム < 500ms
- [ ] 全テストがパス

### Phase 2完了条件
- [ ] DNS管理ページでCloudflareリンクが機能
- [ ] DNSレコード編集が可能
- [ ] バルク操作が正常動作

### Phase 3完了条件
- [ ] 全API統合が完了
- [ ] WebSocketリアルタイム更新が動作
- [ ] 監視・アラート機能が稼働

---

## 🚨 リスク管理

### 想定リスク
1. **データベース接続問題**
   - 対策: ローカル実装ガイドに詳細手順記載

2. **認証の不整合**
   - 対策: JWT実装を慎重に行う、テスト充実

3. **パフォーマンス問題**
   - 対策: ベンチマークテスト実施

4. **既存システムへの影響**
   - 対策: 完全分離アーキテクチャ、ロールバック計画

---

## 📞 サポート

### 質問・問題が発生した場合
1. 該当するドキュメントの「トラブルシューティング」セクションを確認
2. `08_ROLLBACK_PLAN.md` でロールバック手順を確認
3. Issue作成（`docs/application/unified-portal/integration/issues/`）

---

**作成日**: 2025-11-14
**ステータス**: 🔄 ドキュメント作成中
**次のアクション**: 01_REQUIREMENTS.md の作成
