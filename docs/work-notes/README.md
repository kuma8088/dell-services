# Work Notes & Analysis

このディレクトリは、Claude Codeによる作業成果物・分析レポート・調査記録を保管する場所です。

## 📋 目的

- AI開発中の調査結果・分析データを記録
- 将来のClaude instancesが過去の作業を参照できるように保管
- 一時的な作業ノートから有用な知見を蓄積

## 📂 ディレクトリ構造

### Mailserver

**[mailserver/](mailserver/)**

- `wordpress_smtp_configuration.md` - WordPress → Mailserver SMTP連携設定記録
  - Phase A-1で実施したWordPress 16サイトのSMTP設定手順
  - WP Mail SMTPプラグイン設定値
  - テスト結果

### Blog System

**[blog/](blog/)**

Xserverマイグレーション関連の調査記録:

- `README.md` - Xserver調査サマリー
- `database-export-ready.md` - データベースエクスポート準備状況
- `database-export-status.md` - エクスポート実行結果
- `xserver-checklist.md` - マイグレーションチェックリスト
- `xserver-db-summary.md` - データベース構成サマリー

## 🔒 機密情報の扱い

**IMPORTANT:** このディレクトリには機密情報を含めないでください。

- ✅ 設定手順、構成情報、分析結果
- ❌ パスワード、APIキー、認証情報

機密情報は以下で管理:
- 実環境: `/opt/onprem-infra-system/project-root-infra/services/{service}/.env`
- Git除外: `.gitignore`で明示的にブロック

## 📝 ファイル追加ガイドライン

新しい作業ノートを追加する際のルール:

1. **命名規則:**
   - 小文字・ハイフン区切り: `feature-name-analysis.md`
   - 日付付き: `2025-11-11-investigation.md` (一時的な調査の場合)

2. **内容:**
   - タイトルと目的を明記
   - 実施日と担当Claude instanceを記録（オプション）
   - 結果と次のステップを明確に

3. **整理:**
   - 有用な情報は適切なドキュメントに統合
   - 古い調査ノートは定期的にレビュー

## 🔗 関連ドキュメント

- [docs/INDEX.md](/docs/INDEX.md) - ドキュメント全体のクイックリファレンス
- [CLAUDE.md](/CLAUDE.md) - AI開発ガイドライン
- [docs/application/mailserver/](/docs/application/mailserver/) - Mailserver正式ドキュメント
- [docs/application/blog/](/docs/application/blog/) - Blog System正式ドキュメント
