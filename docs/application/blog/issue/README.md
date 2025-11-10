# Blog System Issue Management

このディレクトリでは、Blog System に関連する課題（Issue）を管理します。

---

## 📂 ディレクトリ構造

```
docs/application/blog/issue/
├── README.md              # このファイル
├── Completed/             # 完了した課題
│   └── C001_*.md
├── I001_*.md              # Inbox（新規課題）
├── I002_*.md
├── ...
└── P001_*.md              # Processing（作業中）
```

---

## 🏷️ ファイル命名規則

### プレフィックス

- **I###**: **Inbox** - 新規課題、まだ着手していないもの
- **P###**: **Processing** - 作業中の課題
- **C###**: **Completed** - 完了した課題（`Completed/` ディレクトリに移動）

### ファイル名形式

```
{プレフィックス}{番号3桁}_{課題名（英語、kebab-case）}.md
```

**例**:
- `I001_management-portal-integration.md`
- `P002_backup-system-implementation.md`
- `C001_Xserver-migration-issues.md`

---

## 📋 課題管理フロー

### 1. 新規課題作成（Inbox）

```bash
# I{次の番号}_課題名.md を作成
touch I010_new-feature.md
```

**テンプレート**:
```markdown
# I###: 課題タイトル

**関連タスク**: [#番号] タスク名
**ステータス**: Inbox
**優先度**: Critical/High/Medium/Low
**作成日**: YYYY-MM-DD
**担当**: 未割当

---

## 📋 課題概要
## 🎯 目標
## 📌 現状
## 💡 提案される解決策
## 📋 要件
## 🚧 ブロッカー
## 📝 次のステップ
## 📚 関連ドキュメント
## 📅 更新履歴
```

### 2. 作業開始（Processing）

```bash
# I### を P### にリネーム
mv I004_backup-system.md P004_backup-system.md

# ファイル内のステータスを更新
# **ステータス**: Inbox → Processing
```

### 3. 作業完了（Completed）

```bash
# P### を C### にリネーム
mv P004_backup-system.md C004_backup-system.md

# Completed ディレクトリに移動
mv C004_backup-system.md Completed/

# ファイル内のステータスを更新
# **ステータス**: Processing → Completed
```

---

## 🔗 課題とタスクの紐付け

各issueファイルは `docs/application/01_improvement+issue.md` のタスク番号と紐付きます。

| Issue | タスク | 説明 |
|-------|--------|------|
| I001 | [#001] | 管理ポータル統合 |
| I002 | [#002] | ポータルデザイン刷新 |
| I003 | [#003] | ポータル機能拡張 |
| I004 | [#004] | バックアップ不具合修正 |
| I005 | [#005] | バックアップ改善 |
| I006 | [#006] | キャッシュシステム |
| I007 | [#007] | Email Routing移行 |
| I008 | [#008] | 本番ドメイン移行 |
| I009 | [#009] | サイト動作確認 |
| P011 | [#011] | kuma8088.com表示問題（Phase 011） |
| C001 | [#010] | メール送信機能（完了） |

---

## 📊 現在の課題状況

### Inbox（新規）
- I001: 管理ポータル統合
- I002: ポータルデザイン刷新
- I003: ポータル機能拡張
- I004: バックアップ不具合修正 ⚠️ **Critical**
- I005: バックアップ改善
- I006: キャッシュシステム
- I007: Email Routing移行
- I008: 本番ドメイン移行
- I009: サイト動作確認

### Processing（作業中）
- P011: kuma8088.com表示問題（Phase 011） ⚠️ **High**

### Completed（完了）
- C001: Xserver移行問題対応（Phase 1完了）
- C002: WordPress SMTP設定（全16サイト、2025-11-10完了）

---

## 🎯 優先度ガイドライン

- **Critical** ⚠️: システム停止、データ損失リスク → 即座に対応
- **High**: 運用効率に大きな影響 → 1週間以内
- **Medium**: 改善、最適化 → 1ヶ月以内
- **Low**: Nice to have → 計画的に対応

---

## 📝 更新履歴

- 2025-11-10: Issue管理ディレクトリ作成
- 2025-11-10: I001-I009, C001 作成
- 2025-11-10: P011 追加（kuma8088.com表示問題）
- 2025-11-10: C002 追加（WordPress SMTP設定完了）
