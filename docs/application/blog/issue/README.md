# Blog System Issue Management

このディレクトリでは、Blog System に関連する課題（Issue）を管理します。

---

## 📂 ディレクトリ構造

```
docs/application/blog/issue/
├── README.md              # このファイル
├── active/                # アクティブな課題（作業中・新規）
│   ├── I001-I009_*.md    # Improvement Issues
│   └── P010-P011_*.md    # Problem Issues
└── completed/             # 完了した課題
    └── C001_*.md
```

---

## 🏷️ ファイル命名規則

### プレフィックス

- **I###**: **Improvement** - 改善提案、新機能要望（`active/` ディレクトリ）
- **P###**: **Problem** - 問題、バグ、不具合（`active/` ディレクトリ）
- **C###**: **Completed** - 完了した課題（`completed/` ディレクトリに移動）

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

### 1. 新規課題作成

**Improvement（改善提案）の場合:**
```bash
cd docs/application/blog/issue/active/
touch I010_new-feature.md
```

**Problem（問題・バグ）の場合:**
```bash
cd docs/application/blog/issue/active/
touch P012_bug-description.md
```

**テンプレート:**
```markdown
# {I/P}###: 課題タイトル

**タイプ**: Improvement / Problem
**ステータス**: Open / In Progress / Blocked
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

### 2. 作業完了

```bash
# C### にリネーム
mv active/I010_new-feature.md completed/C010_new-feature.md

# ファイル内のステータスを更新
# **ステータス**: Open/In Progress → Completed
# **完了日**: YYYY-MM-DD を追加
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

### Active - Problems（問題・バグ）
- **P010**: HTTPS混在コンテンツエラー
- **P011**: kuma8088.com表示問題（Phase 011） ⚠️ **High**
  - blog.kuma8088.com配下10サイトでElementorプレビュー/静的ファイル404
  - 根本原因: Cloudflare HTTPS検出欠落
  - 解決策: `fastcgi_param HTTPS on;` 追加

### Active - Improvements（改善提案）
- **I001**: 管理ポータル統合
- **I002**: ポータルデザイン刷新
- **I003**: ポータル機能拡張
- **I004**: バックアップ不具合修正 ⚠️ **Critical**
- **I005**: バックアップ改善
- **I006**: キャッシュシステム
- **I007**: Email Routing移行
- **I008**: 本番ドメイン移行
- **I009**: サイト動作確認

### Completed（完了）
- **C001**: Xserver移行問題対応（Phase A-1完了、2025-11）

---

## 🎯 優先度ガイドライン

- **Critical** ⚠️: システム停止、データ損失リスク → 即座に対応
- **High**: 運用効率に大きな影響 → 1週間以内
- **Medium**: 改善、最適化 → 1ヶ月以内
- **Low**: Nice to have → 計画的に対応

---

## 📝 更新履歴

- 2025-11-11: ディレクトリ構造整理（active/, completed/に再編成）
- 2025-11-11: プレフィックス定義更新（I=Improvement, P=Problem）
- 2025-11-10: Issue管理ディレクトリ作成
- 2025-11-10: I001-I009, P010-P011, C001 作成
