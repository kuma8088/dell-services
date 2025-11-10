# ブログシステム構築プロジェクト

**プロジェクト概要**: XserverからブログをDell WorkStation + Cloudflare Tunnelへ移植

**構築環境**: Dell WorkStation (Rocky Linux 9.6) + Docker Compose

**作成日**: 2025-11-08
**最終更新**: 2025-11-09

---

## 📋 ドキュメント構成

### 要件・設計・実装ドキュメント

| ドキュメント | 内容 | ステータス |
|------------|------|-----------|
| [01_requirements.md](./01_requirements.md) | 要件定義書 | ✅ 完了 |
| [02_design.md](./02_design.md) | システム設計書 | ✅ 完了 |
| [03_installation.md](./03_installation.md) | 構築手順書 | ✅ 完了 |
| [04_migration.md](./04_migration.md) | Xserver移行手順書 | ✅ 完了 |
| [phase-a1-bulk-migration.md](./phase-a1-bulk-migration.md) | Phase A-1 一括移行実装 | ✅ 完了 |
| [cloudflare-tunnel-hostnames.md](./cloudflare-tunnel-hostnames.md) | Cloudflare Tunnel設定 | ✅ 完了 |
| [phase-011-subdirectory-display-issue.md](./phase-011-subdirectory-display-issue.md) | **Phase 011** サブディレクトリ表示問題 | 📝 起票済み |
| 05_testing.md | テスト計画書 | 📝 未作成 |

---

## 🎯 プロジェクト概要

### 目的

**主目的**: Xserverブログを自社インフラへ移植し、コスト削減とデータ主権確保

**技術目標**:
- ✅ Dell WorkStation内Docker Compose環境構築
- ✅ Cloudflare Tunnel導入（動的IP対応）
- ✅ 既存Mailserverインフラとの共存
- 🔄 Phase 11-Bバックアップシステムへの統合（予定）

### スコープ

**対象範囲**:
- WordPress環境構築（Docker Compose）✅ 完了
- Cloudflare Tunnel設定 ✅ 完了
- Xserverからのデータ移行 ✅ Phase A-1完了
- バックアップ・リストア機能 📝 Phase A-2予定

**対象外**:
- デザイン変更
- 新機能追加（移行完了後に検討）
- AWS移行（Phase 12以降）

---

## 🏗️ システムアーキテクチャ

### コンテナ構成

```
blog_network (Docker Bridge)
├── wordpress (PHP-FPM 8.2 + wp-cli)
├── nginx (HTTP リバースプロキシ)
├── mariadb (10.11.7)
└── cloudflared (Cloudflare Tunnel)
```

### ネットワークフロー

```
[ユーザー] → [Cloudflare Edge] → [Tunnel] → [Dell nginx:8080] → [WordPress]
              ↓                     ↓
           DDoS保護            outbound接続のみ
           SSL/TLS自動         (ポート開放不要)
           CDN
```

### ストレージ配置

| データ種別 | 配置先 | デバイス | 理由 |
|-----------|--------|---------|------|
| **MariaDB** | `/var/lib/docker/volumes/` | SSD | 高速DB性能 |
| **Logs** | `/var/lib/docker/volumes/` | SSD | 高速ログ書込 |
| **WordPress files** | `/mnt/backup-hdd/blog/sites/` | HDD | 大容量メディア (95GB+) |
| **Backups** | `/mnt/backup-hdd/blog/backups/` | HDD | 長期保存（予定） |

---

## 📊 技術スタック

| レイヤー | 技術 | バージョン | 備考 |
|---------|------|-----------|------|
| **OS** | Rocky Linux | 9.6 | 既存環境 |
| **コンテナ** | Docker + Compose | 24.0.x + 2.x | 既存環境 |
| **Webサーバー** | Nginx | 1.26.3 | リバースプロキシ |
| **アプリ** | WordPress | 6.4+ | 各サイト既存バージョン |
| **PHP** | PHP-FPM | 8.2.25 | WordPress推奨 |
| **DB** | MariaDB | 10.11.7 | Mailserverと同バージョン |
| **トンネル** | cloudflared | latest | Cloudflare公式 |
| **SSL/TLS** | Cloudflare証明書 | - | 自動管理 |

---

## 🚀 現在の状態（Phase A-1完了）

### ✅ 完了した作業

1. **Docker Compose環境構築**
   - 4コンテナ構成（nginx, wordpress, mariadb, cloudflared）
   - ポート: 8080 (HTTP内部)、3307 (MariaDB内部)
   - ネットワーク: `blog_network`（Mailserverと分離）

2. **WordPress 15サイト移行**
   - データベース: 15 DB インポート完了
   - ファイル: 95GB rsync完了
   - 設定: wp-config.php 一括修正完了
   - URL置換: 8,700+ 置換完了（`https://domain.com` → `http://blog.domain.com`）

3. **Nginx設定**
   - 5仮想ホスト設定完了
   - 14サイト対応（ルート4 + サブディレクトリ10）
   - alias設定修正済み

4. **Cloudflare Tunnel設定**
   - 14 Public Hostnames登録完了
   - HTTPS自動証明書発行済み
   - DNS自動作成済み

5. **動作確認**
   - ✅ 13サイト: 正常動作
   - 🔒 2サイト: パスワード保護（設定通り）
   - ⚠️ 1サイト: 既知の問題（後述）

### 📋 サイト一覧（14サイト）

**ルートドメインサイト（4サイト）**:
1. https://blog.fx-trader-life.com ✅
2. https://blog.webmakeprofit.org ✅
3. https://blog.webmakesprofit.com ✅
4. https://blog.toyota-phv.jp ✅

**サブディレクトリサイト - fx-trader-life（3サイト）**:
5. https://blog.fx-trader-life.com/MFKC 🔒 パスワード保護
6. https://blog.fx-trader-life.com/4-line-trade 🔒 パスワード保護
7. https://blog.fx-trader-life.com/lp ✅

**サブディレクトリサイト - webmakeprofit（1サイト）**:
8. https://blog.webmakeprofit.org/coconala ✅

**サブディレクトリサイト - kuma8088（6サイト）**:
9. https://blog.kuma8088.com/cameramanual ⚠️ PHP互換性エラー
10. https://blog.kuma8088.com/elementordemo1 ✅
11. https://blog.kuma8088.com/elementordemo02 ✅
12. https://blog.kuma8088.com/elementor-demo-03 ✅
13. https://blog.kuma8088.com/elementor-demo-04 ✅
14. https://blog.kuma8088.com/ec02test ✅

---

## ⚠️ 既知の問題（後回し対応）

### ✅ 解決済み: webmakeprofit.org Elementorキャッシュ問題
- **症状**: 本ページで画像非表示（Elementorエディタでは表示）
- **原因**: Elementorキャッシュ
- **解決**: ✅ Codexにより解決済み（2025-11-10）

### 🔴 1. blog.kuma8088.com サブディレクトリサイト表示問題 ★Phase 011起票済み

- **症状**: blog.kuma8088.com配下の10サイトでElementorプレビュー機能と静的ファイル（CSS/JS/画像）が正常に表示されない
- **影響サイト**:
  - /elementordemo1, /elementordemo02, /elementor-demo-03, /elementor-demo-04
  - /ec02test, /cameramanual, /cameramanual-gwpbk492
  - /test（要確認）, / ルートサイト（要確認）
- **根本原因**:
  1. Nginxサブディレクトリルーティング方式（1ドメイン多サイト）
  2. 絶対URL混在（旧ドメインgwpbk492.xsrv.jp残存）
  3. Cloudflare Tunnel WAF/Bot Fight Modeによるブロッキング
- **対処**: 📝 [phase-011-subdirectory-display-issue.md](./phase-011-subdirectory-display-issue.md) 参照
- **推奨解決策**: 独立サブドメイン化（elementordemo1.kuma8088.com等）
- **優先度**: 🔴 HIGH（10サイト影響、編集機能使用不可）

### 2. cameramanual PHP互換性エラー
- **症状**: HTTP 500エラー
- **原因**: テーマが`create_function()`使用（PHP 7.2非推奨、8.0削除）
- **場所**: `/var/www/html/kuma8088-cameramanual/wp-content/themes/sinka/widget/recommend_post.php:88`
- **対処案**:
  - テーマ修正
  - または別テーマへ変更
- **優先度**: 🟡 MEDIUM

---

## 🔧 Phase A-1追加修正（2025-11-10）

### 旧Xserverドメイン参照の修正

**問題**: 一部サイトのデータベースURLが旧Xserverドメインを参照していたため、リダイレクトが発生

**影響サイト**:
- `wp_fx_trader_life_4line`: `http://fx-trader-life.com/4-line-trade` → 旧ドメイン
- `wp_fx_trader_life_mfkc`: `https://fx-trader-life.com/MFKC` → 旧ドメイン
- `wp_kuma8088_cameramanual`: `http://gwpbk492.xsrv.jp/cameramanual` → 旧Xserverサブドメイン

**実施作業**:
1. **全14サイトURL監査**: 全データベースの`home`/`siteurl`設定を確認
2. **データベースURL修正**: 3サイトのURLを新blogサブドメインに更新
   ```sql
   -- 4-line-trade
   UPDATE wp_fx_trader_life_4line.wp_options
   SET option_value = "http://blog.fx-trader-life.com/4-line-trade"
   WHERE option_name IN ("siteurl", "home");

   -- MFKC
   UPDATE wp_fx_trader_life_mfkc.wp_options
   SET option_value = "http://blog.fx-trader-life.com/MFKC"
   WHERE option_name IN ("siteurl", "home");

   -- cameramanual
   UPDATE wp_kuma8088_cameramanual.wp_options
   SET option_value = "http://blog.kuma8088.com/cameramanual"
   WHERE option_name IN ("siteurl", "home");
   ```

**結果**: ✅ 全14サイトが正しいblogサブドメインを参照、リダイレクト問題解消

**検証方法**: MCP Playwright自動テストで動作確認済み

---

## 📂 ディレクトリ構成（実装済み）

```
/opt/onprem-infra-system/project-root-infra/services/blog/
├── docker-compose.yml        # Docker Compose定義
├── .env                       # 環境変数（Git管理外）
├── config/
│   ├── nginx/
│   │   ├── nginx.conf        # Nginx メイン設定
│   │   └── conf.d/           # 仮想ホスト設定
│   │       ├── fx-trader-life.conf
│   │       ├── webmakeprofit.conf
│   │       ├── webmakesprofit.conf
│   │       ├── toyota-phv.conf
│   │       └── kuma8088.conf
│   ├── php/
│   │   └── php.ini           # PHP設定
│   └── mariadb/
│       ├── my.cnf            # MariaDB設定
│       └── init/
│           └── 01-create-databases.sql  # DB初期化SQL
└── (データは /mnt/backup-hdd/blog/ にマウント)
```

### データ配置

```
/mnt/backup-hdd/blog/
├── sites/                    # WordPress ファイル（95GB）
│   ├── fx-trader-life/
│   ├── webmakeprofit/
│   ├── webmakesprofit/
│   ├── toyota-phv/
│   ├── kuma8088/
│   ├── kuma8088-cameramanual/
│   └── ... (全15サイト)
└── backups/                  # バックアップ（予定）
```

---

## 🔧 運用コマンド

### Docker操作

```bash
cd /opt/onprem-infra-system/project-root-infra/services/blog

# コンテナ状態確認
docker compose ps

# ログ確認
docker compose logs -f nginx
docker compose logs -f wordpress

# サービス再起動
docker compose restart nginx

# コンテナ内シェル
docker compose exec wordpress bash
docker compose exec nginx sh
```

### WordPress操作

```bash
# wp-cli コマンド実行
docker compose exec -T wordpress wp --help --allow-root

# URL一括置換（例）
docker compose exec -T wordpress wp search-replace \
  "https://old-domain.com" "http://blog.new-domain.com" \
  --path=/var/www/html/site-name \
  --allow-root \
  --skip-columns=guid
```

---

## 💾 バックアップ仕様（Phase A-2予定）

### バックアップスケジュール（予定）

| 種別 | 実行時刻 | 保存期間 | 保存先 |
|------|---------|---------|--------|
| **日次** | AM 3:30 | 7世代 | `/mnt/backup-hdd/blog/backups/daily/` |
| **週次** | 日曜 AM 2:30 | 4世代 | `/mnt/backup-hdd/blog/backups/weekly/` |
| **S3同期** | AM 4:30 | 30日間 | S3バケット（Phase 11-B統合時） |

### バックアップ対象（予定）

- WordPress DB（MariaDB dump）× 15サイト
- WordPress files（`/mnt/backup-hdd/blog/sites/`）
- Nginx設定
- Docker Compose設定

---

## 🔒 セキュリティ対策

### 実装済み

- ✅ **通信暗号化**: Cloudflare証明書（HTTPS自動）
- ✅ **データベース**: Docker内部ネットワークのみアクセス（ポート3307非公開）
- ✅ **ファイルパーミッション**: www-data (82:82) 所有権設定
- ✅ **認証情報管理**: `.env`ファイル Git管理外

### 今後の対策（予定）

- [ ] **WordPress管理画面**: IP制限またはベーシック認証
- [ ] **定期更新**: WordPress/プラグイン月次更新
- [ ] **バックアップ**: 日次自動バックアップ

---

## 📈 性能要件

| 項目 | 目標値 | 現状 |
|------|--------|------|
| **ページ表示速度** | < 3秒 | ✅ 確認済み |
| **同時接続数** | 10-50ユーザー | 初期想定 |
| **稼働率** | > 99% (月間) | Uptime監視予定 |
| **DB応答時間** | < 100ms | SSD配置で高速 |

---

## ⚠️ 既存インフラとの共存確認

### リソース確認（2025-11-09時点）

| 項目 | Mailserver | Blog | 合計 | 制約 |
|------|-----------|------|------|------|
| **RAM** | 11GB | ~4GB | 15GB / 32GB | ✅ 余裕あり |
| **SSD** | [Mailserver分] | 20GB | - / 390GB | ✅ 余裕あり |
| **HDD** | 434MB | 95GB | 95.4GB / 3.4TB | ✅ 十分 |

### ポート競合回避

| サービス | Mailserver | Blog | 競合 |
|---------|-----------|------|------|
| **Nginx HTTP** | - | 8080（内部） | ✅ 回避 |
| **Nginx HTTPS** | 443（外部） | Tunnel経由 | ✅ 回避 |
| **MariaDB** | 3306（内部） | 3307（内部） | ✅ 回避 |

### Docker Network

- **Mailserver**: `mailserver_mailserver_network`, `staging_mailserver_network`
- **Blog**: `blog_network`（新規作成）
- ✅ ネットワーク分離完了

---

## 📝 移行プロセス

### ✅ Phase A-1: 一括移行（完了）

**実施内容**:
1. ✅ WordPress DB 15サイトバックアップ・インポート
2. ✅ WordPress files 95GB rsync転送
3. ✅ wp-config.php 一括修正（Dell MariaDB接続設定）
4. ✅ URL一括置換（8,700+ 置換）
5. ✅ Nginx設定（14サイト対応）
6. ✅ Cloudflare Tunnel設定（14 Public Hostnames）
7. ✅ 動作確認（11/14サイト正常動作）

**詳細**: [phase-a1-bulk-migration.md](./phase-a1-bulk-migration.md)

### 📝 Phase A-2: バックアップシステム構築（予定）

1. [ ] バックアップスクリプト作成
2. [ ] リストアスクリプト作成
3. [ ] cron自動化設定
4. [ ] Phase 11-B S3統合検討

### 📝 Phase B: 本番運用準備（予定）

1. [ ] 既知の問題修正（Elementor、PHP互換性）
2. [ ] 監視・アラート設定
3. [ ] 運用手順書作成

### 📝 Phase C: Xserver並行運用（予定）

1. [ ] 2週間並行運用
2. [ ] パフォーマンス監視
3. [ ] 問題修正

### 📝 Phase D: Xserver停止（予定）

1. [ ] Xserverメンテナンスモード
2. [ ] 契約解約手続き

---

## 📞 参考情報

### 関連ドキュメント

- [インフラドキュメント](../../infra/README.md)
- [Mailserver構築ドキュメント](../mailserver/README.md)
- [Docker環境構築手順](../../infra/procedures/3-docker/3.1-docker-environment-setup.md)
- [バックアップシステム実装](../mailserver/backup/03_implementation.md)
- [Cloudflare Tunnel設定](./cloudflare-tunnel-hostnames.md)

### 技術参考リンク

**WordPress公式**:
- [WordPress Requirements](https://wordpress.org/about/requirements/)
- [Installing WordPress](https://wordpress.org/support/article/how-to-install-wordpress/)

**Docker公式**:
- [Docker Hub - WordPress](https://hub.docker.com/_/wordpress)
- [Docker Hub - MariaDB](https://hub.docker.com/_/mariadb)

**Cloudflare Tunnel公式**:
- [Cloudflare Tunnel Documentation](https://developers.cloudflare.com/cloudflare-one/connections/connect-networks/)

---

## 🆘 トラブルシューティング

### WordPressアクセスできない

```bash
# コンテナ状態確認
cd /opt/onprem-infra-system/project-root-infra/services/blog
docker compose ps

# Nginxログ確認
docker compose logs nginx | tail -50

# Cloudflare Tunnelログ確認
docker compose logs cloudflared | tail -50
```

### データベース接続エラー

```bash
# MariaDBログ確認
docker compose logs mariadb | tail -50

# WordPress設定確認
docker compose exec wordpress cat /var/www/html/site-name/wp-config.php | grep DB_
```

### 画像表示されない

```bash
# パーミッション確認
docker compose exec wordpress ls -la /var/www/html/site-name/wp-content/uploads/

# 所有者確認
docker compose exec wordpress stat -c "%u:%g %a %n" /var/www/html/site-name/wp-config.php
# Expected: 82:82 (www-data)
```

---

**作成日**: 2025-11-08
**最終更新**: 2025-11-10
**バージョン**: 2.1
**作成者**: Claude

**現在のフェーズ**: Phase A-1完了、Phase A-2準備中
