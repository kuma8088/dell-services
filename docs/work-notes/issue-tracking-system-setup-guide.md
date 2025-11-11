# Issue Tracking System Setup Guide

**作成日**: 2025-11-11
**ステータス**: 推奨事項
**優先度**: HIGH
**カテゴリ**: プロジェクト管理

---

## 📋 現状の課題

### 問題点

現在、Blog System関連のIssueが以下のように管理されている：

```
docs/application/blog/issue/
├── active/
│   ├── P010_https-mixed-content-error.md
│   └── P011-subdirectory-display-issue.md
└── README.md (Issue一覧)
```

**課題**:
- ❌ 担当者・期限の記載なし
- ❌ 優先度が明確でない
- ❌ ステータス管理が不十分（Raised, Processing, Resolved のみ）
- ❌ 9つの改善提案（I001-I009）が作成されたが未着手
- ❌ 進捗追跡が困難

---

## 🎯 目標

### 導入すべき機能

| 機能 | 現状 | 目標 |
|------|------|------|
| **優先度管理** | なし | Critical / High / Medium / Low |
| **担当者割り当て** | なし | 各Issueに担当者 |
| **期限設定** | なし | Due Date設定 |
| **ステータス管理** | 3段階 | Todo / In Progress / Blocked / Done |
| **ラベル** | なし | bug, enhancement, documentation等 |
| **マイルストーン** | なし | Phase単位でグループ化 |

---

## 🔧 選択肢

### Option 1: GitHub Issues（推奨）⭐

**メリット**:
- ✅ 無料（パブリックリポジトリ）
- ✅ Git連携（commit, PRと紐付け）
- ✅ Project Boardsでカンバン管理
- ✅ テンプレート機能
- ✅ Markdown対応
- ✅ API連携可能

**デメリット**:
- ⚠️ プライベートリポジトリの場合、チーム機能に制限あり（Free tier）

**セットアップ手順**:

1. **Issue Templatesの作成**

`.github/ISSUE_TEMPLATE/bug_report.md`:
```markdown
---
name: Bug Report
about: Create a bug report
title: '[BUG] '
labels: bug
assignees: ''
---

**Description**
明確で簡潔なバグの説明

**To Reproduce**
再現手順:
1. Go to '...'
2. Click on '....'
3. See error

**Expected behavior**
期待される動作

**Screenshots**
スクリーンショット（あれば）

**Environment**
- OS: [e.g. Rocky Linux 9.6]
- Service: [e.g. Blog System]
- Component: [e.g. Nginx]

**Additional context**
その他の情報
```

`.github/ISSUE_TEMPLATE/improvement.md`:
```markdown
---
name: Improvement
about: Suggest an improvement
title: '[IMPROVEMENT] '
labels: enhancement
assignees: ''
---

**Current Situation**
現在の状況

**Proposed Improvement**
提案する改善内容

**Benefits**
期待される効果

**Implementation Plan**
実装計画（optional）

**Priority**
- [ ] Critical
- [ ] High
- [ ] Medium
- [ ] Low
```

2. **ラベル作成**

```bash
# GitHub CLI使用（要インストール: brew install gh）
gh label create "P-Critical" --color "d73a4a" --description "Critical priority"
gh label create "P-High" --color "ff6347" --description "High priority"
gh label create "P-Medium" --color "ffa500" --description "Medium priority"
gh label create "P-Low" --color "0e8a16" --description "Low priority"

gh label create "C-Bug" --color "d73a4a" --description "Something isn't working"
gh label create "C-Enhancement" --color "a2eeef" --description "New feature or request"
gh label create "C-Documentation" --color "0075ca" --description "Improvements to documentation"

gh label create "S-Todo" --color "ededed" --description "Not started yet"
gh label create "S-In Progress" --color "fbca04" --description "Currently being worked on"
gh label create "S-Blocked" --color "b60205" --description "Blocked by dependency"
gh label create "S-Done" --color "0e8a16" --description "Completed"

gh label create "Component-Nginx" --color "c5def5" --description "Nginx related"
gh label create "Component-WordPress" --color "c5def5" --description "WordPress related"
gh label create "Component-MariaDB" --color "c5def5" --description "MariaDB related"
```

3. **Project Board作成**

GitHub Web UI:
1. リポジトリ → Projects → New Project
2. Board Template選択
3. カラム設定:
   - `📋 Backlog` - 未着手
   - `🔄 In Progress` - 作業中
   - `🚧 Blocked` - ブロック中
   - `✅ Done` - 完了

4. **既存Issueの移行**

```bash
# P010の例
gh issue create \
  --title "P010: HTTPS Mixed Content Error" \
  --body "$(cat docs/application/blog/issue/active/P010_https-mixed-content-error.md)" \
  --label "P-High,C-Bug,Component-Nginx" \
  --assignee "@me"

# P011の例
gh issue create \
  --title "P011: kuma8088.com Subdirectory Display Issue" \
  --body "$(cat docs/application/blog/issue/active/P011-subdirectory-display-issue.md)" \
  --label "P-Critical,C-Bug,Component-Nginx,Component-WordPress" \
  --assignee "@me"
```

---

### Option 2: Gitea Issues

**メリット**:
- ✅ Self-hosted（プライバシー完全管理）
- ✅ GitHub風UI
- ✅ 軽量

**デメリット**:
- ⚠️ 追加インフラが必要
- ⚠️ メンテナンス負荷

**セットアップ手順**:
```bash
# Docker Composeで簡単セットアップ
docker run -d \
  --name gitea \
  -p 3000:3000 \
  -v /opt/gitea:/data \
  gitea/gitea:latest
```

---

### Option 3: Jira（エンタープライズ向け）

**メリット**:
- ✅ 強力な機能（スプリント、バーンダウンチャート等）
- ✅ Slack/Email連携

**デメリット**:
- ⚠️ 有料（Free tierは10ユーザーまで）
- ⚠️ 学習コスト高い

---

### Option 4: Simple Markdown（現状維持改善版）

**メリット**:
- ✅ 追加ツール不要
- ✅ Git管理

**デメリット**:
- ❌ 検索・フィルタリングが困難
- ❌ 通知機能なし

**改善例**:

`docs/application/blog/issue/ISSUES.md`:
```markdown
# Blog System Issues

| ID | Title | Priority | Status | Assignee | Due Date | Labels |
|----|-------|----------|--------|----------|----------|--------|
| P011 | kuma8088.com表示問題 | 🔴 Critical | 🔄 In Progress | @user | 2025-11-15 | nginx, wordpress |
| P010 | HTTPS混在エラー | 🟠 High | 📋 Todo | @user | 2025-11-20 | nginx |
| I001 | Management Portal統合 | 🟡 Medium | 📋 Todo | - | TBD | enhancement |
| I002 | Portal Design刷新 | 🟢 Low | 📋 Todo | - | TBD | ui, enhancement |
```

---

## 📊 推奨方法

### 短期（今すぐ）: GitHub Issues

**理由**:
- すでにGitHubを使用している
- 無料で強力な機能
- Git workflow と統合

**実装手順** (15分):
```bash
# 1. Issue Templates作成
mkdir -p .github/ISSUE_TEMPLATE
# 上記テンプレートを作成

# 2. ラベル作成
# 上記gh labelコマンドを実行

# 3. Project Board作成
# Web UIで作成

# 4. 既存Issue移行
# 上記gh issue createコマンドを実行
```

### 中期（1ヶ月後）: Project Board活用

- スプリント管理
- Milestone設定
- Automationルール設定

### 長期（3ヶ月後）: CI/CD連携

```yaml
# .github/workflows/issue-triage.yml
name: Issue Triage

on:
  issues:
    types: [opened]

jobs:
  triage:
    runs-on: ubuntu-latest
    steps:
      - name: Add to project
        uses: actions/add-to-project@v0.4.0
        with:
          project-url: https://github.com/users/<USER>/projects/<PROJECT_NUMBER>
          github-token: ${{ secrets.ADD_TO_PROJECT_PAT }}

      - name: Auto-label
        uses: actions/labeler@v4
        with:
          repo-token: ${{ secrets.GITHUB_TOKEN }}
```

---

## ✅ 成功基準

### 1ヶ月後の目標:
- ✅ 全Issueに優先度・担当者・期限設定
- ✅ 週次レビュー実施（毎週月曜）
- ✅ 完了Issue数 > 新規Issue数

### 3ヶ月後の目標:
- ✅ Issue解決率80%以上
- ✅ 平均解決時間 < 2週間
- ✅ ドキュメント化率100%（完了Issueは必ずドキュメント更新）

---

## 🔗 参考資料

- [GitHub Issues Documentation](https://docs.github.com/en/issues)
- [GitHub Project Boards](https://docs.github.com/en/issues/organizing-your-work-with-project-boards)
- [Gitea](https://gitea.io/)
- [Jira](https://www.atlassian.com/software/jira)

---

**Last Updated**: 2025-11-11
**Author**: Claude
**Status**: 📋 Recommendation - GitHub Issues推奨
