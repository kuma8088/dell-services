# Unified Portal - 未解決の問題

最終更新: 2025-11-14

---

## 概要

Unified Portalのフロントエンド開発における未解決の問題をトラッキングします。

---

## 🔴 Issue #1: UIコンポーネント不足（Critical）

**優先度**: Critical
**影響範囲**: フロントエンドビルド全体
**ステータス**: 未解決

### 問題

shadcn/uiのUIコンポーネントが不足しているため、フロントエンドビルドが失敗します。

### 不足しているコンポーネント

1. `alert` - Dashboard.tsx, Security.tsx等で使用
2. `badge` - Docker.tsx等で使用
3. `tabs` - Dashboard.tsx等で使用

### エラーメッセージ

```
ERROR in ./src/pages/Dashboard.tsx
Module not found: Error: Can't resolve '@/components/ui/alert'

ERROR in ./src/pages/Docker.tsx
Module not found: Error: Can't resolve '@/components/ui/badge'

ERROR in ./src/pages/Dashboard.tsx
Module not found: Error: Can't resolve '@/components/ui/tabs'
```

### 修正方針

shadcn-uiのCLIを使用してコンポーネントを追加します。

### 修正コマンド

```bash
cd /opt/onprem-infra-system/project-root-infra/services/unified-portal/frontend

# 不足しているコンポーネントを追加
npx shadcn-ui@latest add alert
npx shadcn-ui@latest add badge
npx shadcn-ui@latest add tabs
```

### 修正後の確認

```bash
cd /opt/onprem-infra-system/project-root-infra/services/unified-portal

# ビルド実行
docker compose build frontend

# コンテナ再起動
docker compose up -d frontend

# ログ確認
docker compose logs -f frontend
```

### 影響を受けるファイル

- `frontend/src/pages/Dashboard.tsx`
- `frontend/src/pages/Docker.tsx`
- `frontend/src/pages/Security.tsx`

---

## 🟡 Issue #2: IntersectionObserver型エラー（Medium）

**優先度**: Medium
**影響範囲**: Backup.tsx
**ステータス**: 未解決

### 問題

`Backup.tsx:72:30`で`IntersectionObserver`の型エラーが発生しています。

### エラーメッセージ

```
TS2769: No overload matches this call.
  Overload 1 of 2, '(callback: IntersectionObserverCallback, options?: IntersectionObserverInit | undefined): IntersectionObserver', gave the following error.
    Argument of type '(entries: any) => void' is not assignable to parameter of type 'IntersectionObserverCallback'.
```

### 修正方針

`IntersectionObserverCallback`型を明示的に指定します。

### 修正例

```typescript
// 修正前
const observer = new IntersectionObserver((entries) => {
  // ...
});

// 修正後
const observer = new IntersectionObserver((entries: IntersectionObserverEntry[]) => {
  // ...
});
```

### 影響を受けるファイル

- `frontend/src/pages/Backup.tsx:72`

---

## 🟡 Issue #3: 未使用import警告（Low）

**優先度**: Low
**影響範囲**: Database.tsx
**ステータス**: 未解決

### 問題

`Database.tsx:11:10`で未使用のimport `DatabaseIcon`に関する警告が発生しています。

### エラーメッセージ

```
'DatabaseIcon' is defined but never used. (@typescript-eslint/no-unused-vars)
```

### 修正方針

1. `DatabaseIcon`を使用するコードを追加する
2. または、使用しない場合はimport文を削除する

### 修正例（Option 1: 削除）

```typescript
// 修正前
import { DatabaseIcon, Server, RefreshCw, AlertCircle } from 'lucide-react';

// 修正後
import { Server, RefreshCw, AlertCircle } from 'lucide-react';
```

### 影響を受けるファイル

- `frontend/src/pages/Database.tsx:11`

---

## 📋 Issue一覧サマリー

| Issue | 優先度 | ステータス | 影響範囲 |
|-------|--------|------------|----------|
| #1: UIコンポーネント不足 | 🔴 Critical | 未解決 | ビルド全体 |
| #2: IntersectionObserver型エラー | 🟡 Medium | 未解決 | Backup.tsx |
| #3: 未使用import警告 | 🟡 Low | 未解決 | Database.tsx |

---

## 次のアクション

1. **最優先**: Issue #1を修正してビルドを成功させる
2. Issue #2の型エラーを修正
3. Issue #3のコード整理

---

## 参考リンク

- [shadcn/ui Documentation](https://ui.shadcn.com/)
- [TypeScript Handbook - Intersection Types](https://www.typescriptlang.org/docs/handbook/2/objects.html#intersection-types)
- [ESLint no-unused-vars](https://eslint.org/docs/latest/rules/no-unused-vars)
