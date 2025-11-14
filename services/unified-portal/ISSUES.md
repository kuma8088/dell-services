# Unified Portal - Issues

## 🔴 Issue #1: フロントエンドビルドエラー - UIコンポーネント不足

**発生日時**: 2025-11-14 23:03
**優先度**: Critical
**ステータス**: Open
**担当**: 開発チーム

### 問題概要

フロントエンドのビルドが失敗しているため、DomainManagement.tsxに実装した2カラムレイアウトの変更が本番環境に反映されない。

### エラー詳細

```
src/pages/AdminUserManagement.tsx(41,41): error TS2307: Cannot find module '@/components/ui/alert' or its corresponding type declarations.
src/pages/DatabaseManagement.tsx(12,23): error TS2307: Cannot find module '@/components/ui/badge' or its corresponding type declarations.
src/pages/WordPressManagement.tsx(22,58): error TS2307: Cannot find module '@/components/ui/tabs' or its corresponding type declarations.
```

### 不足しているコンポーネント

1. `@/components/ui/alert` - AdminUserManagement.tsxで使用
2. `@/components/ui/badge` - DatabaseManagement.tsxで使用
3. `@/components/ui/tabs` - WordPressManagement.tsxで使用

### 影響範囲

- フロントエンド全体のビルドが失敗
- Docker イメージのビルドが完了しない
- コード変更（2カラムレイアウト実装）が本番環境に反映されない

### 修正方針

以下のいずれかを実施:

**Option 1: UIコンポーネントを追加** (推奨)
```bash
cd /opt/onprem-infra-system/project-root-infra/services/unified-portal/frontend
npx shadcn-ui@latest add alert
npx shadcn-ui@latest add badge
npx shadcn-ui@latest add tabs
```

**Option 2: 使用している箇所をコメントアウト** (一時的対処)
- AdminUserManagement.tsx: 41行目のalert import削除
- DatabaseManagement.tsx: 12行目のbadge import削除
- WordPressManagement.tsx: 22行目のtabs import削除

### 関連ファイル

- `/opt/onprem-infra-system/project-root-infra/services/unified-portal/frontend/src/pages/AdminUserManagement.tsx`
- `/opt/onprem-infra-system/project-root-infra/services/unified-portal/frontend/src/pages/DatabaseManagement.tsx`
- `/opt/onprem-infra-system/project-root-infra/services/unified-portal/frontend/src/pages/WordPressManagement.tsx`

---

## 🟡 Issue #2: TypeScriptエラー - IntersectionObserver型不一致

**発生日時**: 2025-11-14 23:03
**優先度**: Medium
**ステータス**: Open
**担当**: 開発チーム

### 問題概要

テストセットアップファイルでIntersectionObserverの型定義エラーが発生。

### エラー詳細

```
src/test/setup.ts(26,1): error TS2322: Type 'typeof IntersectionObserver' is not assignable to type '{ new (callback: IntersectionObserverCallback, options?: IntersectionObserverInit | undefined): IntersectionObserver; prototype: IntersectionObserver; }'.
  Types of property 'prototype' are incompatible.
    Type 'IntersectionObserver' is missing the following properties from type 'IntersectionObserver': root, rootMargin, thresholds
```

### 現在のコード (setup.ts:26)

```typescript
globalThis.IntersectionObserver = class IntersectionObserver {
  constructor() {}
  disconnect() {}
  observe() {}
  takeRecords() {
    return []
  }
  unobserve() {}
}
```

### 修正方針

IntersectionObserverモックに不足しているプロパティを追加:

```typescript
globalThis.IntersectionObserver = class IntersectionObserver {
  root = null
  rootMargin = '0px'
  thresholds = []

  constructor() {}
  disconnect() {}
  observe() {}
  takeRecords() {
    return []
  }
  unobserve() {}
} as any
```

### 関連ファイル

- `/opt/onprem-infra-system/project-root-infra/services/unified-portal/frontend/src/test/setup.ts`

---

## 🟡 Issue #3: TypeScript警告 - 未使用import

**発生日時**: 2025-11-14 23:03
**優先度**: Low
**ステータス**: Open
**担当**: 開発チーム

### 問題概要

MailserverManagement.tsxで未使用のimportに関する警告。

### エラー詳細

```
src/pages/MailserverManagement.tsx(12,3): error TS6133: 'CardDescription' is declared but its value is never read.
src/pages/MailserverManagement.tsx(13,3): error TS6133: 'CardHeader' is declared but its value is never read.
src/pages/MailserverManagement.tsx(14,3): error TS6133: 'CardTitle' is declared but its value is never read.
```

### 修正方針

未使用のimportを削除:

```typescript
// 削除対象
import {
  CardDescription,  // 削除
  CardHeader,       // 削除
  CardTitle,        // 削除
} from '@/components/ui/card'
```

### 関連ファイル

- `/opt/onprem-infra-system/project-root-infra/services/unified-portal/frontend/src/pages/MailserverManagement.tsx`

---

## 📋 Issue修正の優先順位

1. **Critical - Issue #1**: UIコンポーネント不足の解消（ビルドブロッカー）
2. **Medium - Issue #2**: IntersectionObserver型エラーの修正
3. **Low - Issue #3**: 未使用import警告の解消

## ビルド成功条件

すべてのIssueを修正後、以下のコマンドでビルドが成功すること:

```bash
cd /opt/onprem-infra-system/project-root-infra/services/unified-portal
docker compose build frontend
```

期待される結果: `exit code: 0`（ビルド成功）
