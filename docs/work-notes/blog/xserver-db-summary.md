# Xserver データベース整理結果

**⚠️ 機密情報**: このファイルは `.gitignore` で保護されています

**作成日**: 2025-11-08
**データソース**: Xserver管理画面

---

## 📊 サマリー

| 項目 | 数 | 備考 |
|------|-----|------|
| **合計DB数** | 18個 | 全環境 |
| **WordPress利用中** | 14個 | 稼働中サイト |
| **移行WP** | 3個 | 独自ドメイン（ルート） |
| **不明だが移行** | 3個 | パスワード情報なし |
| **合計容量** | 約1.1GB | 全DB合計 |
| **最大DB** | 303.6 MB | webmakeprofit.org |

---

## 📋 全データベース一覧

### 1. 移行対象（独自ドメインルート）✅

| DB名 | ユーザー名 | パスワード | 容量 | URL | 優先度 |
|------|-----------|----------|------|-----|--------|
| gwpbk492_wt1 | gwpbk492_wt4 | **r5QjPNqZ** ✅ | 303.6 MB | https://webmakeprofit.org | 🟡 中 |
| gwpbk492_wt4 | gwpbk492_wt5 | **N6uBHQYw** ✅ | 193.7 MB | https://webmakesprofit.com | 🟡 中 |
| gwpbk492_wt5 | gwpbk492_wt6 | **Aa2V9tuK** ✅ | 3.5 MB | https://toyota-phv.jp | 🟢 低 |

**✅ 更新**: 全サイトのパスワード判明（2025-11-08）

---

### 2. WordPress利用中（サブディレクトリ構成）

#### 2-1. fx-trader-life.com 配下

| DB名 | ユーザー名 | パスワード | 容量 | URL | 移行判定 |
|------|-----------|----------|------|-----|---------|
| **gwpbk492_wp3** | gwpbk492_wp2 | mx9ssys031 | 29.6 MB | http://fx-trader-life.com/wp-admin/ | ✅ **メインサイト（優先度高）** |
| gwpbk492_62q47 | gwpbk492_th6h6 | 0l29jx1wfh | 2.9 MB | http://fx-trader-life.com/MFKC/wp-admin/ | 🟡 サブディレクトリ |
| gwpbk492_e1rb6 | gwpbk492_c73vs | 1tmlc7tlzy | 1.0 MB | http://fx-trader-life.com/4-line-trade | 🟡 サブディレクトリ |
| gwpbk492_x9a11 | gwpbk492_a2gfg | chrmh6frjh | 6.2 MB | http://fx-trader-life.com/lp | 🟡 サブディレクトリ |

**合計容量**: 39.7 MB（4サイト）

#### 2-2. kuma8088.com 配下

| DB名 | ユーザー名 | パスワード | 容量 | URL | 移行判定 |
|------|-----------|----------|------|-----|---------|
| gwpbk492_wp7 | gwpbk492_wp1 | s5qvs1q19a | 0.8 MB | http://kuma8088.com/cameramanual/wp-admin/ | 🟡 サブディレクトリ |

**注**: kuma8088.com メインサイトのDB情報が不明（別途確認必要）

#### 2-3. gwpbk492.xsrv.jp 配下（Xserverデフォルトドメイン）

| DB名 | ユーザー名 | パスワード | 容量 | URL | 移行判定 |
|------|-----------|----------|------|-----|---------|
| gwpbk492_38ogv | gwpbk492_xxuqz | z8kjx3d7bq | 8.8 MB | http://gwpbk492.xsrv.jp/elementordemo1/wp-admin/ | ❌ テストサイト |
| gwpbk492_c51ex | gwpbk492_n489j | 64g43dannk | 1.1 MB | http://gwpbk492.xsrv.jp/cameramanual/wp-admin/ | ❌ テストサイト |
| gwpbk492_h2xks | gwpbk492_y717a | hlnb2q4mcw | 8.3 MB | http://gwpbk492.xsrv.jp/elementordemo02/wp-admin/ | ❌ テストサイト |
| gwpbk492_koqr9 | gwpbk492_0bqrv | g8d03vbz8h | 11.5 MB | http://gwpbk492.xsrv.jp/ec02test/ | ❌ テストサイト |
| gwpbk492_o0vyw | gwpbk492_v8m8y | ii9y1nku7t | 10.5 MB | http://gwpbk492.xsrv.jp/elementor-demo-04/wp-admin/ | ❌ テストサイト |
| gwpbk492_rxhlz | gwpbk492_ijim2 | unfkpdrfeu | 18.9 MB | http://gwpbk492.xsrv.jp/elementor-demo-03/wp-admin/ | ❌ テストサイト |

**合計容量**: 59.1 MB（6サイト、全てElementor/ECテスト環境）

#### 2-4. webmakeprofit.org 配下（サブディレクトリ）

| DB名 | ユーザー名 | パスワード | 容量 | URL | 移行判定 |
|------|-----------|----------|------|-----|---------|
| gwpbk492_bxb90 | gwpbk492_we38z | 6ra1du4n6i | 14.6 MB | http://webmakeprofit.org/coconala/wp-admin/ | 🟡 サブディレクトリ |

---

### 3. 不明DB（用途調査中）

| DB名 | ユーザー名 | パスワード | 容量 | URL | 状況 |
|------|-----------|----------|------|-----|------|
| gwpbk492_p3ca6 | gwpbk492_socwr | **a2XMFdWU** ✅ | 101.2 MB | (不明) | **容量大：URL調査必要** |
| gwpbk492_wp5 | gwpbk492_h0cm9 | **m5FYtweM** ✅ | 52.3 MB | (不明) | **容量大：URL調査必要** |
| gwpbk492_wt2 | gwpbk492_wt7 | **(未確認)** | 48.7 MB | (不明) | **パスワード・URL調査必要** |

**合計容量**: 202.2 MB（3サイト）
**✅ 更新**: 2サイトのパスワード判明（2025-11-08）
**⚠️ 残課題**: gwpbk492_wt2のパスワード確認、全3サイトのURL調査（wp-config.phpまたはDB直接確認）

---

## 🎯 移行優先度の推奨

### Phase 1: 確定移行サイト（6サイト）

| サイト | DB名 | 容量 | 優先度 | 理由 |
|-------|------|------|--------|------|
| **fx-trader-life.com** | gwpbk492_wp3 | 29.6 MB | 🔴 最高 | メインサイト、独自ドメイン |
| **webmakeprofit.org** | gwpbk492_wt1 | 303.6 MB | 🟡 高 | 独自ドメイン、容量最大 |
| **webmakesprofit.com** | gwpbk492_wt4 | 193.7 MB | 🟡 高 | 独自ドメイン |
| **toyota-phv.jp** | gwpbk492_wt5 | 3.5 MB | 🟢 中 | 独自ドメイン、容量小 |
| **kuma8088.com** | **(要確認)** | **(不明)** | 🔴 最高 | メインサイト、独自ドメイン |
| **courses.kuma8088.com** | **(要確認)** | **(不明)** | 🟡 高 | サブドメイン |

**合計予想容量**: 約550-600 MB（kuma8088.com含む）

### Phase 2: 検討中サイト（任意）

- fx-trader-life.com/MFKC/ (2.9 MB)
- fx-trader-life.com/lp (6.2 MB)
- webmakeprofit.org/coconala/ (14.6 MB)

**合計容量**: 23.7 MB

### Phase 3: 移行対象外（テストサイト）

- gwpbk492.xsrv.jp 配下の全6サイト（Elementor/ECテスト環境）
- 合計容量: 59.1 MB

---

## ⚠️ 調査が必要な項目

### 1. kuma8088.com メインサイトのDB情報

**現状**: gwpbk492_wp7 は `/cameramanual/` サブディレクトリのみ判明

**要調査**:
- kuma8088.com ルートのWordPress DB名・ユーザー名・パスワード
- courses.kuma8088.com (サブドメイン) のDB情報

**調査方法**:
1. Xserver管理画面 → MySQL設定 → データベース一覧
2. `kuma8088.com` で検索
3. 該当DBのパスワード確認

---

### 2. 不明DB 3件の詳細確認

| DB名 | 容量 | 対応 |
|------|------|------|
| gwpbk492_p3ca6 | 101.2 MB | Xserver管理画面でパスワード取得 or 移行不要判断 |
| gwpbk492_wp5 | 52.3 MB | 同上 |
| gwpbk492_wt2 | 48.7 MB | 同上 |

**調査方法**:
1. Xserver管理画面 → MySQL設定 → パスワード変更
2. 各DBのパスワードを新規生成
3. 該当WordPressサイトのURL確認（wp-config.php）

---

### 3. 独自ドメインルートサイトのパスワード

| サイト | DB名 | 対応 |
|-------|------|------|
| webmakeprofit.org | gwpbk492_wt1 | パスワード再確認 |
| webmakesprofit.com | gwpbk492_wt4 | パスワード再確認 |
| toyota-phv.jp | gwpbk492_wt5 | パスワード再確認 |

**調査方法**: Xserver管理画面でパスワード確認または再生成

---

## 📊 容量分析

### 容量分布（上位10件）

| 順位 | DB名 | サイト | 容量 | 割合 |
|------|------|--------|------|------|
| 1 | gwpbk492_wt1 | webmakeprofit.org | 303.6 MB | 27.6% |
| 2 | gwpbk492_wt4 | webmakesprofit.com | 193.7 MB | 17.6% |
| 3 | gwpbk492_p3ca6 | (不明) | 101.2 MB | 9.2% |
| 4 | gwpbk492_wp5 | (不明) | 52.3 MB | 4.8% |
| 5 | gwpbk492_wt2 | (不明) | 48.7 MB | 4.4% |
| 6 | gwpbk492_wp3 | fx-trader-life.com | 29.6 MB | 2.7% |
| 7 | gwpbk492_rxhlz | gwpbk492.xsrv.jp/elementor-demo-03 | 18.9 MB | 1.7% |
| 8 | gwpbk492_bxb90 | webmakeprofit.org/coconala | 14.6 MB | 1.3% |
| 9 | gwpbk492_koqr9 | gwpbk492.xsrv.jp/ec02test | 11.5 MB | 1.0% |
| 10 | gwpbk492_o0vyw | gwpbk492.xsrv.jp/elementor-demo-04 | 10.5 MB | 1.0% |

**合計**: 約1.1 GB（全18DB）
**移行対象予想**: 約530 MB（6サイト + 不明3件除外）

---

## 🔐 セキュリティ管理

### パスワード管理状況

| 状態 | DB数 | DB名 |
|------|------|------|
| **パスワード判明** | 12個 | WordPress利用中サイト |
| **パスワード不明** | 6個 | 移行WP 3個 + 不明 3個 |

### 次のアクション

1. **即座に実施**:
   - ✅ この情報を `claudedocs/` に保存（Git管理外）
   - ✅ `.gitignore` で保護済み確認

2. **Xserver管理画面で確認**:
   - 🔲 kuma8088.com メインサイトのDB情報
   - 🔲 courses.kuma8088.com のDB情報
   - 🔲 gwpbk492_wt1, wt4, wt5 のパスワード
   - 🔲 gwpbk492_p3ca6, wp5, wt2 の用途確認

3. **移行完了後**:
   - 🔲 全DBパスワードを変更（Phase F）
   - 🔲 このファイルを削除（`shred -u`）

---

**最終更新**: 2025-11-08
**次回確認**: Phase A-0 実施時
