# Xserver移行前確認チェックリスト

**作成日**: 2025-11-08
**ステータス**: Phase A-0 準備中

---

## ✅ 完了済み

- ✅ 全18個のデータベース情報整理完了
- ✅ 移行対象サイトの容量確認完了
- ✅ パスワード判明サイト（12サイト）の情報保存完了
- ✅ `.gitignore` での機密情報保護確認完了

---

## ⚠️ Xserver管理画面で確認が必要な項目

### 1. kuma8088.com メインサイトのDB情報 🔴 最優先

**現状**: サブディレクトリ `/cameramanual/` のDB情報のみ判明

**必要な情報**:
```
□ kuma8088.com ルートのDB名
□ kuma8088.com ルートのDBユーザー名
□ kuma8088.com ルートのDBパスワード
```

**確認方法**:
1. Xserver管理画面ログイン
2. 「MySQL設定」→「データベース一覧」
3. `kuma8088.com` または `gwpbk492_wt3` で検索
4. 該当DBの詳細を確認

**予想されるDB名**:
- `gwpbk492_wt3` または
- `gwpbk492_wp1` または
- その他の `gwpbk492_*` 形式

---

### 2. 独自ドメインルートサイトのパスワード ✅ **完了**

| サイト | DB名 | DBユーザー名 | パスワード | 容量 |
|-------|------|-------------|----------|------|
| webmakeprofit.org | gwpbk492_wt1 | gwpbk492_wt4 | ✅ **r5QjPNqZ** | 303.6 MB |
| webmakesprofit.com | gwpbk492_wt4 | gwpbk492_wt5 | ✅ **N6uBHQYw** | 193.7 MB |
| toyota-phv.jp | gwpbk492_wt5 | gwpbk492_wt6 | ✅ **Aa2V9tuK** | 3.5 MB |

**✅ 完了日**: 2025-11-08
**📝 保存先**: `xserver-credentials.env` に反映済み

~~**確認方法**~~:
1. ~~Xserver管理画面 → 「MySQL設定」→「パスワード変更」~~
2. ~~各DB（`gwpbk492_wt1`, `gwpbk492_wt4`, `gwpbk492_wt5`）のパスワードを確認~~
3. ~~パスワードが不明の場合は、新規パスワードを生成してメモ~~

---

### 3. 不明DB 3件の用途確認 🟡 任意（部分完了）

| DB名 | 容量 | パスワード | 確認内容 |
|------|------|----------|---------|
| gwpbk492_p3ca6 | 101.2 MB | ✅ **a2XMFdWU** | ⚠️ URL調査必要<br>□ 使用中のWordPressサイトか？<br>□ 移行対象か？ |
| gwpbk492_wp5 | 52.3 MB | ✅ **m5FYtweM** | ⚠️ URL調査必要<br>□ 使用中のWordPressサイトか？<br>□ 移行対象か？ |
| gwpbk492_wt2 | 48.7 MB | ❌ 未確認 | ❌ パスワード確認必要<br>❌ URL調査必要<br>□ 移行対象か？ |

**✅ 完了日**: 2025-11-08（パスワード2件判明）
**📝 保存先**: `xserver-credentials.env` に反映済み

**残りの確認方法**:
1. **gwpbk492_wt2のパスワード**: Xserver管理画面 → 「MySQL設定」→「パスワード変更」
2. **全3サイトのURL調査**:
   - Xserver SSH接続 → `grep -r "gwpbk492_p3ca6" ~/*/public_html/*/wp-config.php`
   - または phpMyAdmin → 各DB → `wp_options` テーブル → `siteurl` 確認
3. 移行対象かどうか判断

**判断基準**:
- **移行する**: 稼働中で重要なサイト
- **移行しない**: テストサイト、古いサイト、不要なサイト

---

### 4. courses.kuma8088.com（サブドメイン）のDB情報 🟡 任意

**現状**: サブドメインサイトの情報が不明

**必要な情報**:
```
□ courses.kuma8088.com のDB名
□ courses.kuma8088.com のDBユーザー名
□ courses.kuma8088.com のDBパスワード
```

**確認方法**:
1. `courses.kuma8088.com` へアクセス
2. WordPressサイトが存在するか確認
3. 存在する場合、Xserver管理画面でDB情報を確認

**注**: サブドメインサイトが存在しない場合はスキップ

---

### 5. Xserver SSH/FTP情報 🔴 必須

**現状**: ホスト名・ユーザー名が不明

**必要な情報**:
```
□ SSHホスト名（例: sv12345.xserver.jp）
□ SSHユーザー名（例: gwpbk492）
□ SSHポート番号（通常: 10022）
□ FTPホスト名（例: gwpbk492.xsrv.jp）
□ FTPユーザー名（例: gwpbk492）
```

**確認方法**:
1. Xserver管理画面 → 「SSH設定」
2. ホスト名・ユーザー名・ポート番号を確認
3. `xserver-credentials.env` ファイルに記載

---

## 📊 移行対象サイトの最終確認

### 確定移行サイト（Phase 1）✅ **確定完了**

| サイト | DB名 | 容量 | パスワード | 状況 |
|-------|------|------|----------|------|
| **fx-trader-life.com** | gwpbk492_wp3 | 29.6 MB | ✅ 判明 | ✅ **移行準備完了** |
| **webmakeprofit.org** | gwpbk492_wt1 | 303.6 MB | ✅ 判明 | ✅ **移行準備完了** |
| **webmakesprofit.com** | gwpbk492_wt4 | 193.7 MB | ✅ 判明 | ✅ **移行準備完了** |
| **toyota-phv.jp** | gwpbk492_wt5 | 3.5 MB | ✅ 判明 | ✅ **移行準備完了** |

**合計容量**: **530 MB（4サイト）**
**✅ 更新**: 独自ドメイン3サイトのパスワード判明（2025-11-08）
**✅ 確定**: kuma8088.com メインサイト・courses.kuma8088.com は存在しないため移行対象外（2025-11-08）

---

### 検討中サイト（Phase 2・任意移行）

| サイト | DB名 | 容量 | パスワード | 移行判断 |
|-------|------|------|----------|---------|
| kuma8088.com/cameramanual | gwpbk492_wp7 | 0.8 MB | ✅ 判明 | □ 移行する □ 移行しない |
| fx-trader-life.com/MFKC | gwpbk492_62q47 | 2.9 MB | ✅ 判明 | □ 移行する □ 移行しない |
| fx-trader-life.com/4-line-trade | gwpbk492_e1rb6 | 1.0 MB | ✅ 判明 | □ 移行する □ 移行しない |
| fx-trader-life.com/lp | gwpbk492_x9a11 | 6.2 MB | ✅ 判明 | □ 移行する □ 移行しない |
| webmakeprofit.org/coconala | gwpbk492_bxb90 | 14.6 MB | ✅ 判明 | □ 移行する □ 移行しない |

**合計容量**: 25.5 MB（5サイト）

---

### 移行対象外（テストサイト）

| サイト | DB名 | 容量 | 理由 |
|-------|------|------|------|
| gwpbk492.xsrv.jp/elementordemo1 | gwpbk492_38ogv | 8.8 MB | Elementorテスト環境 |
| gwpbk492.xsrv.jp/elementordemo02 | gwpbk492_h2xks | 8.3 MB | Elementorテスト環境 |
| gwpbk492.xsrv.jp/elementor-demo-03 | gwpbk492_rxhlz | 18.9 MB | Elementorテスト環境 |
| gwpbk492.xsrv.jp/elementor-demo-04 | gwpbk492_o0vyw | 10.5 MB | Elementorテスト環境 |
| gwpbk492.xsrv.jp/ec02test | gwpbk492_koqr9 | 11.5 MB | ECサイトテスト環境 |
| gwpbk492.xsrv.jp/cameramanual | gwpbk492_c51ex | 1.1 MB | テストサイト |

**合計容量**: 59.1 MB（全て移行対象外）

---

## 📝 次のアクション

### Step 1: Xserver管理画面で情報収集 🔴 最優先

**所要時間**: 約15-20分

1. **kuma8088.com メインサイトのDB情報確認**（5分）
   - MySQL設定 → データベース一覧
   - DB名・ユーザー名・パスワードをメモ

2. **独自ドメイン3サイトのパスワード確認**（5分）
   - gwpbk492_wt1, wt4, wt5 のパスワード確認
   - パスワードが不明な場合は新規生成

3. **SSH/FTP情報確認**（3分）
   - SSH設定でホスト名・ユーザー名確認
   - FTP設定でホスト名・ユーザー名確認

4. **不明DB 3件の用途確認**（任意、5分）
   - gwpbk492_p3ca6, wp5, wt2 の詳細確認
   - 移行対象か判断

---

### Step 2: xserver-credentials.env を更新

**ファイルパス**: `/opt/onprem-infra-system/project-root-infra/docs/application/blog/claudedocs/xserver-credentials.env`

**更新内容**:
```bash
# Step 1で確認した情報を以下に記入

# kuma8088.com メインサイト
export XSERVER_KUMA8088_DB_NAME="<確認したDB名>"
export XSERVER_KUMA8088_DB_USER="<確認したDBユーザー名>"
export XSERVER_KUMA8088_DB_PASS="<確認したパスワード>"

# 独自ドメインサイトのパスワード
export XSERVER_TOYOTA_DB_PASS="<確認したパスワード>"
export XSERVER_WEBMAKEPROFIT_DB_PASS="<確認したパスワード>"
export XSERVER_WEBMAKESPROFIT_DB_PASS="<確認したパスワード>"

# SSH/FTP情報
export XSERVER_SSH_HOST="<確認したホスト名>"
export XSERVER_SSH_USER="<確認したユーザー名>"
```

---

### Step 3: 移行対象サイトの最終確定

**判断基準**:
- ✅ **必須移行**: kuma8088.com, fx-trader-life.com, webmakeprofit.org（容量大）
- 🟡 **推奨移行**: webmakesprofit.com, toyota-phv.jp
- 🟢 **任意移行**: サブディレクトリサイト（/MFKC, /lp, /coconala）

**決定事項**:
```
最終移行対象サイト数: ___ サイト
合計容量: ___ MB
```

---

### Step 4: Phase A-0 実行準備完了確認

**完了チェックリスト**（2025-11-08 最終更新）:
```
✅ 全移行対象サイトのDB情報が揃った（4サイト完全確定）
   ✅ fx-trader-life.com（29.6 MB）
   ✅ webmakeprofit.org（303.6 MB）
   ✅ webmakesprofit.com（193.7 MB）
   ✅ toyota-phv.jp（3.5 MB）
   ✅ kuma8088.com メインサイト: 存在しないため移行対象外
   ✅ courses.kuma8088.com: 存在しないため移行対象外

✅ xserver-credentials.env が更新された（2025-11-08）
   - 独自ドメイン3サイトのパスワード反映済み
   - 不明DB 2件のパスワード追加済み
   - kuma8088.com/courses.kuma8088.com 不存在を明記

⚠️ SSH/FTP情報が確認できていない（任意）
   - XSERVER_SSH_HOST: 未確認
   - XSERVER_SSH_USER: 未確認
   - ⚠️ 注: SSH/FTP情報は移行方法によっては不要（WPvivid GUI移行の場合）

✅ 移行対象サイト数が確定した
   - Phase 1 確定: 4サイト（530 MB）
   - Phase 2 任意: 5サイト（25.5 MB）

✅ Phase 1 確定サイトの合計容量が確認できた: 530 MB
```

**🎉 Phase A-0 準備完了**:
- ✅ **Phase A-0 実行可能**: 全4サイト（530 MB）のDB情報が完全に揃いました
- ✅ **次のステップ**: Phase A-0-1（サイズ調査）またはPhase C（テスト移行）へ進めます

**📝 残りのアクション（任意）**:
1. **SSH/FTP情報確認**（🟡 任意、所要時間3分）
   - SSH/rsyncスクリプト移行を選択する場合のみ必要
   - WPvivid GUI移行の場合は不要

---

## 📚 参照ドキュメント

- **詳細なDB情報**: `claudedocs/xserver-db-summary.md`
- **認証情報**: `claudedocs/xserver-credentials.env`
- **移行手順**: `../04_migration.md - Phase A-0`

---

**最終更新**: 2025-11-08
**次回確認**: Xserver管理画面での情報収集後
