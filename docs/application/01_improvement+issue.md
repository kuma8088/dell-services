# 改善・課題管理

このファイルでは、現在のシステム（Blog System / Mailserver）に対する今後の改善タスクと既知の課題を管理します。

**注意**: 実際の要件定義・設計構築・タスク管理は各ドキュメントディレクトリで行います。このファイルはタスク一覧の概要管理のみを目的としています。

---

## 📥 Inbox（新規タスク）

新規追加されたタスク。まだ着手していないもの。

### 管理システム

- [ ] **[#001] 管理ポータル（blog/mailserverの統合）**
  - 現状: Blog System と Mailserver で管理インターフェースが分離
  - 目標: 統合管理ポータルの構築
  - 詳細: `docs/application/blog/issue/I001_management-portal-integration.md`

- [ ] **[#002] 管理ポータルのデザイン変更（モダンでスタイリッシュにする）**
  - 現状: 既存デザインが機能的だが古風
  - 目標: モダンなUI/UXへの刷新
  - 詳細: `docs/application/blog/issue/I002_portal-design-modernization.md`

- [ ] **[#003] 管理ポータルの機能整理・追加**
  - 現状: 必要機能の洗い出しが未完了
  - 目標: 機能要件の明確化と実装
  - 詳細: `docs/application/blog/issue/I003_portal-feature-enhancement.md`

### バックアップ・データ管理

- [ ] **[#004] 自動バックアップの不具合修正（緊急）** ⚠️
  - 現状: 自動バックアップが機能していない
  - 目標: 日次/週次バックアップの正常動作復旧
  - 詳細: `docs/application/blog/issue/I004_backup-system-troubleshooting.md`
  - 関連: Phase 10 (ローカル) + Phase 11-B (S3) バックアップシステム
  - 結果待ち：20251114の自動バックアップの結果を確認しOKなら対応完了

- [ ] **[#005] バックアップシステムの更新**
  - 現状: Phase 10 (ローカル) + Phase 11-B (S3) が稼働中
  - 目標: 改善・最適化の検討
  - 詳細: `docs/application/blog/issue/I005_backup-system-improvement.md`
  - 結果待ち：20251114の自動バックアップの結果を確認しOKなら対応完了

- [ ] **[#006] キャッシュシステム（blogsystem）**
  - 現状: WordPress デフォルトキャッシュのみ
  - 目標: Redis/Memcached等の導入検討
  - 詳細: `docs/application/blog/issue/I006_cache-system-implementation.md`

- [ ] **[#016] 旧バックアップバケット(s3)の削除**

### インフラ最適化

- [ ] **[#015] Terraform(tfstate)のバックアップ**

### Blog System

- [ ] **[#013] SMTP経由でもメールが迷惑メール疑惑をGmailからかけられる対策**

- [ ] **[#014] https://webmakesprofit.comからメールが飛ばない問題**

---

## 🔄 Processing（作業中）

現在進行中のタスク。



---

## ✅ Completed（完了）

完了したタスク。完了日順（新しい順）。

- [x] **[#012] WordPress SMTP設定（Mailserver連携）** (2025-11-10)
  - 実装: WP Mail SMTP plugin + Postfix SMTP relay設定
  - 成果: 全16サイトで Mailserver (172.20.0.20:25) 経由のSMTP送信
  - 効果: SPF/DKIM認証により迷惑メール判定を回避
  - 詳細: `claudedocs/wordpress_smtp_configuration.md`

- [x] **[#010] WordPressメール送信機能の設定** (2025-11-10)
  - 実装: Dockerfile + ssmtp + docker-compose.yml による恒久対応
  - 成果: 全14サイトで wp_mail() 機能が動作、Postfix 経由でメール送信可能
  - 詳細: `docs/application/blog/issue/Completed/C001_Xserver-migration-issues.md` Phase 1完了

- [x] **[#011] blog.kuma8088.com サブディレクトリ表示問題（Phase 011）** ⚠️
  - 現状: blog.kuma8088.com配下10サイトでElementorプレビュー・静的ファイル404エラー
  - 根本原因: Cloudflare HTTPS検出欠落 + Nginx複雑な設定
  - 目標: 3つの解決アプローチから選択・実装
    - Phase 011-A（緊急）: Nginx設定修正
    - Phase 011-B（中期）: URL置換 + WAF調整
    - Phase 011-C（恒久）: 独立サブドメイン化 ★推奨
  - 詳細: `docs/application/blog/phase-011-subdirectory-display-issue.md`

- [x] **[#009] 移行先サイトの動作確認（Elementorやプラグインのライセンス等）**
  - 現状: Elementor Pro・プラグインライセンス状況未確認
  - 目標: ライセンス確認と本番環境での動作検証
  - 詳細: `docs/application/blog/issue/I009_site-validation.md`


- [x] **[#008] blog.*ドメインの本番移行**
  - 現状: blog.webmakeprofit.org 等のサブドメインで運用中（Phase A-1 テストフェーズ）
  - 目標: 本番ドメイン（webmakeprofit.org 等）への移行（Phase A-2）
  - 詳細: `docs/application/blog/issue/I008_production-domain-migration.md`
  - 次のアクション#007

- [x] **[#007] Email Routingへの変更（EC2の廃止）**
  - 現状: EC2で Postfix MX Gateway を稼働
  - 目標: Cloudflare Email Routing への移行でEC2コスト削減
  - 詳細: `docs/application/blog/issue/I007_email-routing-migration.md`

---

## 📝 更新履歴

- 2025-11-10: ファイル作成、初期タスク追加
- 2025-11-10: 緊急タスク追加「自動バックアップの不具合修正」
- 2025-11-10: ステータス管理セクション追加（Inbox/Processing/Completed）
- 2025-11-10: タスクナンバリング追加（#001-#007）
- 2025-11-10: Blog System カテゴリ追加、タスク #008-#009 追加（本番移行、動作確認）
- 2025-11-10: タスク #010 追加（WordPressメール送信機能の設定）
- 2025-11-10 02:40: タスク #010 完了（Phase 1 Critical対応完了）
- 2025-11-10 02:50: 個別issueファイル作成（I001-I009, C001）、詳細リンク追加
- 2025-11-10: タスク #011 追加（Phase 011: kuma8088.com表示問題）Processing
- 2025-11-10: タスク #012 完了（WordPress SMTP設定、全16サイト）
