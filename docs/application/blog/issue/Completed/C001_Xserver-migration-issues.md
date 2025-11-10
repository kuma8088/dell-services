# P001: Xserver → Dell Docker 環境移行時の包括的課題

**優先度**: High
**ステータス**: Phase 1 Critical対応完了（Task 1-1, 1-2, 1-3 ✅）
**作成日**: 2025-11-10
**最終更新**: 2025-11-10 02:30 (Task 1-1/1-2/1-3 完了)

---

## 📋 問題の概要

Xserver から Dell Docker 環境へ WordPress サイト（14サイト）を移行した際、レンタルサーバーでは自動的に提供されていた機能が Docker 環境では未実装のため、複数の問題が発生している。

---

## 🔍 発見された問題一覧

### 1. メール送信機能の欠如 ⚠️ **Critical**

**症状**:
```
エラー: メールを送信できませんでした。サイトのメール送信が正しく設定されていない可能性があります。
```

**影響範囲**: 全 14 WordPress サイト
- パスワードリセットメール送信不可
- お問い合わせフォーム送信不可
- WordPress通知メール送信不可

**根本原因**:
- **Xserver**: サーバー内で PHP `mail()` を使うと自動的に Xserver SMTP 経由で送信
- **Dell Docker**: WordPress コンテナ（`wordpress:php8.3-fpm-alpine`）に sendmail/postfix が**未インストール**

**現在の状況**: kuma8088-elementordemo1 のみ WP Mail SMTP プラグインで暫定対応済み

---

### 2. ファイルシステム書き込み権限の問題 ⚠️ **Critical**

**症状**:
```
要求されたアクションを実行するには、WordPress が Web サーバーにアクセスする必要があります。
次に進むには FTP の認証情報を入力してください。
```

**発生タイミング**:
- プラグインのインストール・更新
- テーマのインストール・更新
- WordPressコア更新
- メディアアップロード（場合による）

**根本原因**:

| 項目 | Xserver | Dell Docker |
|------|---------|-------------|
| Web サーバー | Apache/Nginx | Nginx (別コンテナ) |
| PHP プロセス | Apache モジュール or PHP-FPM | PHP-FPM (別コンテナ) |
| ファイル所有者 | 同一ユーザー or 適切に設定済み | 1000:1000（ホストユーザー） |
| PHP プロセス実行ユーザー | 適切に設定済み | www-data (UID 82) |
| 結果 | 書き込み可能 | **書き込み不可** → FTP要求 |

**詳細分析**:
```bash
# 現在の状態
docker compose exec wordpress ls -la /var/www/html/kuma8088
drwxr-xr-x    2 1000     1000          4096 Nov  8 23:23 .

# PHP-FPMプロセスの実行ユーザー
www-data (UID 82, GID 82)

# 結果: UID 82 が UID 1000 のファイルに書き込めない
```

**Xserver の仕組み**:
- ファイル所有者とPHPプロセスユーザーが一致、または
- suEXEC/CGI ラッパーで適切に権限管理、または
- グループ権限で書き込み可能

---

### 3. FTP/SFTP サーバーの不在

**症状**: FTP認証情報を求められても、FTPサーバーが存在しない

**根本原因**:
- **Xserver**: FTP/SFTP サーバーが標準で稼働（バックアップ手段として利用）
- **Dell Docker**: FTP/SFTP サーバー未実装

**2つの解決策の比較**:

#### 解決策A: FS_METHOD = 'direct' + ファイル所有者修正 ⭐ **推奨**

**原理**:
- WordPress がファイルシステムに直接書き込み可能にする
- ファイル所有者を `www-data` (PHP-FPM実行ユーザー) に統一
- FTP/SFTP サーバー不要

**メリット**:
- ✅ セキュリティリスク最小（FTPサーバーの脆弱性を回避）
- ✅ 運用負荷最小（FTPアカウント管理不要）
- ✅ パフォーマンス最適（直接書き込みが最速）
- ✅ WordPress のベストプラクティス

**デメリット**:
- ⚠️ ファイル所有者の初回変更が必要（エントリーポイントで自動化可能）
- ⚠️ セキュリティ侵害時にファイル改変リスク（ただしXserverも同様）

**実装コスト**: 低（Dockerfile + エントリーポイントスクリプト）

---

#### 解決策B: FTP/SFTP サーバー導入

**原理**:
- vsftpd または proftpd コンテナを追加
- WordPress が FTP 経由でファイル書き込み

**メリット**:
- ✅ ファイル所有者を変更不要
- ✅ Xserver と同じ仕組み

**デメリット**:
- ❌ セキュリティリスク増加（追加の攻撃面）
- ❌ FTP は平文通信（SFTP/FTPSが必要 → 設定複雑化）
- ❌ コンテナ追加による運用負荷増加
- ❌ パフォーマンス低下（FTP通信のオーバーヘッド）
- ❌ FTPアカウント管理の運用負荷

**実装コスト**: 中〜高（コンテナ追加、アカウント管理、セキュリティ設定）

---

**推奨理由**:

1. **WordPress 公式推奨**: [WordPress Codex](https://wordpress.org/support/article/editing-wp-config-php/#wordpress-upgrade-constants) では `FS_METHOD = 'direct'` が推奨
2. **セキュリティ**: FTPサーバーは不要な攻撃面を増やす
3. **運用効率**: ファイル所有者変更は一度の設定で完了
4. **実績**: 多くの Docker 環境で採用されている方法

**重要**: 解決策Aでプラグインインストールが機能することは、実装後のテストで実証します。

---

### 4. WP-Cron システムの違い

**症状**: スケジュールされたタスク（記事予約投稿、自動更新チェック等）の実行タイミング

**根本原因**:

| 項目 | Xserver | Dell Docker |
|------|---------|-------------|
| Cron実装 | システムcron or 最適化されたWP-Cron | WP-Cron（アクセス駆動型） |
| 実行タイミング | 定期的（分単位） | サイトアクセス時のみ |
| 低トラフィックサイト | 問題なし | タスク実行遅延の可能性 |

**影響**:
- アクセスが少ないサイトでは予約投稿が遅れる可能性
- 自動更新チェックが遅延する可能性

---

### 5. PHPモジュール・設定の違い

**確認済みPHPモジュール**:
```bash
✅ curl, gd, imagick, mbstring, xml, zip, opcache
❌ ftp (不要 - 後述の解決策で対応)
❌ redis, memcache (未実装だがOPcacheで代替可能)
```

**PHP設定**:
```
max_execution_time = 0 (無制限)
memory_limit = 256M
post_max_size = 64M
upload_max_filesize = 64M
opcache.enable = On
```

**評価**: 問題なし（Xserver と同等以上）

---

### 6. SSL/TLS証明書管理

**症状**: SSL証明書の取得・更新プロセスが異なる

**根本原因**:

| 項目 | Xserver | Dell Docker |
|------|---------|-------------|
| SSL証明書 | Let's Encrypt 自動取得・更新 | Cloudflare Tunnel（証明書は Cloudflare 管理） |
| 証明書の場所 | サーバー内（/etc/letsencrypt等） | Cloudflare Edge |
| 更新方法 | 自動（certbot cron） | 自動（Cloudflare管理） |

**影響**: 特になし（Cloudflare Tunnelが自動管理）

**評価**: 問題なし（むしろCloudflare管理の方が運用負荷小）

---

### 7. 自動バックアップシステムの欠如 ⚠️ **High Priority**

**症状**: Blog Systemの自動バックアップが未実装

**確認結果**:
```bash
/mnt/backup-hdd/blog/backups/daily/ → 空
/mnt/backup-hdd/blog/backups/weekly/ → 空
crontab -l | grep blog → 設定なし
```

**根本原因**:
- **Xserver**: 自動バックアップ機能が標準装備（日次バックアップ14日分保持等）
- **Dell Docker**: バックアップディレクトリは作成済みだが、**スクリプト未実装**

**影響**:
- データ損失リスク（障害時に復旧不可）
- WordPressサイトデータ（14サイト分）
- MariaDBデータベース（15データベース）

**必要な対応**:
1. WordPress サイトファイルの日次/週次バックアップ
2. MariaDB データベースダンプの自動化
3. バックアップローテーション（保持期間設定）
4. S3オフサイトバックアップ（Mailserver と同様の仕組み）

---

### 8. データベース管理ツールの不在

**症状**: phpMyAdmin 等のGUIデータベース管理ツールがない

**根本原因**:
- **Xserver**: phpMyAdmin が標準提供
- **Dell Docker**: 未実装

**現在の代替手段**:
```bash
# wp-cli でデータベース操作
docker compose exec wordpress wp db query "SHOW TABLES;" --path=/var/www/html/kuma8088 --allow-root

# 直接MariaDBコンテナにアクセス
docker compose exec mariadb mysql -u root -p
```

**評価**:
- ✅ wp-cli で対応可能（WordPress用途には十分）
- ⚠️ phpMyAdmin があると便利だが、必須ではない
- **優先度**: Low（必要に応じて追加検討）

---

### 9. ログ管理・ローテーション

**症状**: ログローテーション設定が未実装

**確認結果**:
```bash
/etc/logrotate.d/ → blog 関連設定なし
docker volume inspect blog_blog_logs → ログは蓄積するが削除されない
```

**根本原因**:
- **Xserver**: ログローテーション自動設定済み
- **Dell Docker**: ログは `/var/log/nginx`, `/var/log/php` に蓄積されるが、**ローテーション未設定**

**影響**:
- ディスク容量の圧迫（長期運用でログが肥大化）
- 古いログの削除が手動

**必要な対応**:
1. logrotate 設定ファイル作成
2. ログの保持期間設定（例: 30日）
3. 圧縮設定（gzip）

**優先度**: Medium（すぐには問題ないが、長期運用で必要）

---

### 10. モニタリング・アラート機能

**症状**: サービス障害時の通知機能がない

**確認結果**:
- Docker ヘルスチェック: ✅ 実装済み（cloudflared, nginx, wordpress, mariadb）
- アラート通知: ❌ 未実装

**根本原因**:
- **Xserver**: サーバー監視とメール通知
- **Dell Docker**: ヘルスチェックはあるが、**障害時の通知機能なし**

**影響**:
- サービスダウン時に気づかない可能性
- 復旧対応が遅れる

**必要な対応**:
1. ヘルスチェック失敗時のメール通知
2. リソース使用率の監視（CPU/メモリ/ディスク）
3. Cloudflare Tunnel切断時の通知

**優先度**: Medium（本番移行前に実装推奨）

---

### 11. WAF・セキュリティ機能

**症状**: WAF（Web Application Firewall）の有無

**確認結果**:

| 項目 | Xserver | Dell Docker |
|------|---------|-------------|
| WAF | 標準装備（XServer WAF） | Cloudflare（無料プランのセキュリティ機能） |
| DDoS対策 | Xserver側で対策 | Cloudflare（無料プランでも基本的な対策） |
| 不正アクセス検知 | サーバー側で検知 | Cloudflare Bot Management（有料） |

**評価**:
- ✅ Cloudflare の無料プランでも基本的なセキュリティは確保
- ⚠️ Xserver WAF と完全に同等ではない
- **優先度**: Low（Cloudflare で最低限カバー）

---

### 12. ステージング環境

**症状**: テスト環境がない

**根本原因**:
- **Xserver**: ステージング環境機能あり（プランによる）
- **Dell Docker**: 本番環境のみ

**影響**:
- プラグイン更新やテーマ変更を本番で直接テスト
- リスクが高い

**評価**:
- **現状**: blog.* サブドメインがステージング環境として機能（Phase A-1）
- **本番移行後**: ステージング環境が必要になる可能性

**優先度**: Medium（本番移行後に検討）

---

## 💡 恒久対応方針

### 問題1・2の統合解決策: Dockerfile カスタマイズ ⭐ **推奨**

**アプローチ**:
1. **ssmtp インストール** → メール送信問題解決
2. **ファイル所有者の適切な設定** → FTP認証問題解決
3. **FS_METHOD = 'direct'** → WordPress が直接ファイル書き込み

**メリット**:
- ✅ 一度の設定で全 14 サイトに対応
- ✅ FTPサーバー不要（セキュリティリスク排除）
- ✅ Xserver と同じユーザー体験
- ✅ プラグイン不要
- ✅ インフラ層で一元管理

**実装方法**:

#### 1. Dockerfile 作成

```dockerfile
# services/blog/Dockerfile
FROM wordpress:php8.3-fpm-alpine

# ssmtp インストール（メール送信）
RUN apk add --no-cache ssmtp

# ssmtp 設定
RUN echo "mailhub=dell-workstation.tail67811d.ts.net:587" > /etc/ssmtp/ssmtp.conf && \
    echo "FromLineOverride=YES" >> /etc/ssmtp/ssmtp.conf && \
    echo "UseTLS=YES" >> /etc/ssmtp/ssmtp.conf && \
    echo "UseSTARTTLS=YES" >> /etc/ssmtp/ssmtp.conf && \
    echo "hostname=dell-workstation.tail67811d.ts.net" >> /etc/ssmtp/ssmtp.conf

# sendmail シンボリックリンク
RUN ln -sf /usr/sbin/ssmtp /usr/sbin/sendmail

# エントリーポイントスクリプト（ファイル所有者修正）
COPY docker-entrypoint-custom.sh /usr/local/bin/
RUN chmod +x /usr/local/bin/docker-entrypoint-custom.sh

ENTRYPOINT ["docker-entrypoint-custom.sh"]
CMD ["php-fpm"]
```

#### 2. カスタムエントリーポイント作成

```bash
# services/blog/docker-entrypoint-custom.sh
#!/bin/sh
set -e

# ファイル所有者を www-data に変更（初回のみ実行）
if [ ! -f /var/www/html/.permissions-fixed ]; then
    echo "Fixing file permissions..."
    chown -R www-data:www-data /var/www/html
    touch /var/www/html/.permissions-fixed
    echo "Permissions fixed."
fi

# 元の docker-entrypoint.sh を実行
exec docker-entrypoint.sh "$@"
```

#### 3. wp-config.php に FS_METHOD 追加

```php
// wp-config.php の任意の場所（DB設定の前など）に追加
define('FS_METHOD', 'direct');
```

**または、全サイトに一括適用**:
```bash
# 全サイトの wp-config.php に FS_METHOD を追加
for site in /var/www/html/*/wp-config.php; do
    if ! grep -q "FS_METHOD" "$site"; then
        sed -i "/DB_COLLATE/a define('FS_METHOD', 'direct');" "$site"
    fi
done
```

#### 4. docker-compose.yml 修正

```yaml
wordpress:
  build:
    context: .
    dockerfile: Dockerfile
  # image: wordpress:php8.3-fpm-alpine  # ← コメントアウト
  container_name: blog-wordpress
  extra_hosts:
    - "dell-workstation.tail67811d.ts.net:172.20.0.20"
  networks:
    blog_network:
      ipv4_address: 172.22.0.30
    mailserver_network: {}  # Mailserver ネットワークに接続
  volumes:
    - blog_wordpress_sites:/var/www/html
    - ./config/php/php.ini:/usr/local/etc/php/conf.d/custom.ini:ro
  # ... 以下既存設定

networks:
  blog_network:
    driver: bridge
    ipam:
      config:
        - subnet: 172.22.0.0/24
          gateway: 172.22.0.1
  mailserver_network:
    external: true
    name: mailserver_mailserver_network
```

#### 5. ビルドと再起動

```bash
cd /opt/onprem-infra-system/project-root-infra/services/blog

# イメージビルド
docker compose build wordpress

# コンテナ再起動
docker compose up -d wordpress

# パーミッション修正確認
docker compose exec wordpress ls -la /var/www/html/kuma8088 | head -5
# 期待結果: drwxr-xr-x ... www-data www-data ...
```

---

### 問題4（WP-Cron）の対応方針

**2つのアプローチ**:

#### オプションA: システムcronで定期実行（推奨）

```bash
# ホストのcrontabに追加
*/15 * * * * docker compose -f /opt/onprem-infra-system/project-root-infra/services/blog/docker-compose.yml exec -T wordpress wp cron event run --due-now --path=/var/www/html/kuma8088 --allow-root > /dev/null 2>&1
```

**メリット**:
- 確実に定期実行される
- アクセスの少ないサイトでも問題なし

**デメリット**:
- 全サイト分のcron設定が必要（14サイト × 複数パス）

#### オプションB: WP-Cronのまま運用

**判断基準**:
- トラフィックが多いサイト → 現状のWP-Cronで問題なし
- トラフィックが少ないサイト → システムcron推奨

**現時点の推奨**: まずはWP-Cronのままで運用し、問題が発生したサイトのみシステムcronを追加

---

## 📝 実装手順（統合対応）

### Phase 1: Dockerfile + ファイル権限対応

1. **Dockerfile 作成**
```bash
cat > /opt/onprem-infra-system/project-root-infra/services/blog/Dockerfile <<'EOF'
FROM wordpress:php8.3-fpm-alpine

RUN apk add --no-cache ssmtp

RUN echo "mailhub=dell-workstation.tail67811d.ts.net:587" > /etc/ssmtp/ssmtp.conf && \
    echo "FromLineOverride=YES" >> /etc/ssmtp/ssmtp.conf && \
    echo "UseTLS=YES" >> /etc/ssmtp/ssmtp.conf && \
    echo "UseSTARTTLS=YES" >> /etc/ssmtp/ssmtp.conf && \
    echo "hostname=dell-workstation.tail67811d.ts.net" >> /etc/ssmtp/ssmtp.conf

RUN ln -sf /usr/sbin/ssmtp /usr/sbin/sendmail

COPY docker-entrypoint-custom.sh /usr/local/bin/
RUN chmod +x /usr/local/bin/docker-entrypoint-custom.sh

ENTRYPOINT ["docker-entrypoint-custom.sh"]
CMD ["php-fpm"]
EOF
```

2. **エントリーポイントスクリプト作成**
```bash
cat > /opt/onprem-infra-system/project-root-infra/services/blog/docker-entrypoint-custom.sh <<'EOF'
#!/bin/sh
set -e

if [ ! -f /var/www/html/.permissions-fixed ]; then
    echo "Fixing file permissions..."
    chown -R www-data:www-data /var/www/html
    touch /var/www/html/.permissions-fixed
    echo "Permissions fixed."
fi

exec docker-entrypoint.sh "$@"
EOF

chmod +x /opt/onprem-infra-system/project-root-infra/services/blog/docker-entrypoint-custom.sh
```

3. **docker-compose.yml 修正**
   - `image:` をコメントアウト
   - `build:` セクション追加
   - `extra_hosts` 追加
   - `mailserver_network` 追加

4. **ビルドと再起動**
```bash
cd /opt/onprem-infra-system/project-root-infra/services/blog
docker compose build wordpress
docker compose up -d wordpress
```

### Phase 2: wp-config.php に FS_METHOD 追加

```bash
# WordPress コンテナ内で実行
docker compose exec wordpress sh -c '
for dir in /var/www/html/*/; do
    config="${dir}wp-config.php"
    if [ -f "$config" ] && ! grep -q "FS_METHOD" "$config"; then
        sed -i "/DB_COLLATE/a define('\''FS_METHOD'\'', '\''direct'\'');" "$config"
        echo "Added FS_METHOD to $config"
    fi
done
'
```

### Phase 3: テスト

**メール送信テスト**:
```bash
# 任意のサイトでテスト
docker compose exec wordpress wp eval "wp_mail('naoya.iimura@gmail.com', 'Test', 'Test message from kuma8088');" \
  --path=/var/www/html/kuma8088 --allow-root
```

**ファイル書き込みテスト**:
1. WordPress管理画面にログイン
2. プラグイン → 新規追加 → 任意のプラグインをインストール
3. FTP認証を求められないことを確認

### Phase 4: kuma8088-elementordemo1 の WP Mail SMTP 削除

```bash
# プラグインが不要になるため削除
docker compose exec wordpress wp plugin deactivate wp-mail-smtp \
  --path=/var/www/html/kuma8088-elementordemo1 --allow-root

docker compose exec wordpress wp plugin delete wp-mail-smtp \
  --path=/var/www/html/kuma8088-elementordemo1 --allow-root
```

---

## 🔄 ロールバック手順

問題が発生した場合:

```bash
cd /opt/onprem-infra-system/project-root-infra/services/blog

# docker-compose.yml を元に戻す
git checkout docker-compose.yml

# Dockerfile とスクリプト削除
rm Dockerfile docker-entrypoint-custom.sh

# コンテナ再起動
docker compose up -d wordpress
```

---

## 📊 問題一覧と対応状況

| # | 問題 | 優先度 | 対応方針 | ステータス |
|---|------|--------|----------|-----------|
| 1 | メール送信機能の欠如 | Critical | ssmtp (Dockerfile) | 方針決定 |
| 2 | ファイル書き込み権限 | Critical | パーミッション修正 + FS_METHOD | 方針決定 |
| 3 | FTP/SFTP サーバー | - | 解決策A（FS_METHOD）推奨 | 方針決定 |
| 4 | WP-Cron | Low | 現状維持 | 対応不要 |
| 5 | PHPモジュール・設定 | - | 問題なし | ✅ 完了 |
| 6 | SSL/TLS証明書 | - | Cloudflare管理 | ✅ 完了 |
| 7 | 自動バックアップ | High | Mailserver スクリプト拡張 | 未対応 |
| 8 | DB管理ツール | Low | wp-cli で対応可 | 対応不要 |
| 9 | ログローテーション | Medium | logrotate 設定 | 未対応 |
| 10 | モニタリング・アラート | Medium | 統一監視システム | 未対応 |
| 11 | WAF・セキュリティ | Low | Cloudflare で最低限カバー | ✅ 完了 |
| 12 | ステージング環境 | Medium | 本番移行後に検討 | 後回し |

---

## 📋 実装タスクリスト

### Phase 1: Critical 問題の解決（必須）

#### Task 1-1: Dockerfile + ssmtp 実装 ✅ **完了** (2025-11-10)
- [x] Dockerfile 作成（ssmtp インストール）
- [x] エントリーポイントスクリプト作成（パーミッション修正）
- [x] docker-compose.yml 修正（build, extra_hosts, mailserver_network）
- [x] イメージビルドと再起動
- [x] メール送信テスト（全14サイト）

**成功基準**: ✅ 達成
- 全サイトで `wp_mail()` が機能すること → ✅ テスト成功（naoya.iimura@gmail.com へ送信確認）
- Postfix 経由でメール送信できること → ✅ ssmtp経由でPostfix relay可能

**実装内容**:
- `services/blog/Dockerfile`: ssmtp インストール、設定、sendmail シンボリックリンク
- `services/blog/docker-entrypoint-custom.sh`: ファイル所有者を www-data に修正
- `services/blog/docker-compose.yml`: build設定、extra_hosts、mailserver_network接続

---

#### Task 1-2: ファイル書き込み権限修正 ✅ **完了** (2025-11-10)
- [x] 全サイトの wp-config.php に `FS_METHOD = 'direct'` 追加（16ファイル）
- [x] プラグインインストールテスト（任意のサイト）
- [x] FTP認証が求められないことを確認

**成功基準**: ✅ 完全達成
- プラグイン・テーマのインストール/更新が FTP なしで可能 → ✅ 確認済み
- WordPress 管理画面から直接操作可能 → ✅ 確認済み

**実装内容**:
- 全16サイトの wp-config.php に `define('FS_METHOD', 'direct');` 追加
- ファイル所有者修正（www-data:www-data）でファイル書き込み権限確保
- ブラウザテストでFTP認証プロンプトが表示されないことを確認

---

#### Task 1-3: 暫定対応の削除 ✅ **完了** (2025-11-10)
- [x] kuma8088-elementordemo1 の WP Mail SMTP プラグイン削除
- [x] WordPress コンテナから mailserver_network への手動接続削除（docker-compose.yml で管理）
- [x] /etc/hosts の手動追記削除（extra_hosts で管理）

**成功基準**:
- インフラ設定が docker-compose.yml に集約されていること
- 手動設定が残っていないこと

**注**: Phase 2以降のタスクは個別issueで管理します。
- I004: バックアップシステム不具合修正
- I005: バックアップシステム改善
- その他の運用改善タスク

---

## 📚 関連リンク

- [WordPress Filesystem API](https://developer.wordpress.org/apis/filesystem/)
- [ssmtp Alpine Linux](https://pkgs.alpinelinux.org/package/edge/main/x86_64/ssmtp)
- [Docker entrypoint best practices](https://docs.docker.com/develop/develop-images/dockerfile_best-practices/)
- [WordPress File Permissions](https://wordpress.org/support/article/changing-file-permissions/)

---

## 📝 更新履歴

- 2025-11-10: ファイル作成、Xserver移行課題として包括的に再構成
- 2025-11-10: メール送信問題（kuma8088-elementordemo1で暫定対応）
- 2025-11-10: ファイル書き込み権限問題の発見と対応方針決定
- 2025-11-10: FTP問題を2つの解決策として再構成（解決策A推奨）
- 2025-11-10: 追加問題の洗い出し（問題6-12追加）
  - SSL/TLS証明書管理
  - 自動バックアップシステムの欠如
  - データベース管理ツール
  - ログローテーション
  - モニタリング・アラート
  - WAF・セキュリティ
  - ステージング環境
- 2025-11-10: 実装タスクリスト作成（Phase 1-4）
- 2025-11-10 02:30: **Phase 1 Critical対応完了**
  - Task 1-1: Dockerfile + ssmtp 実装 ✅
    - `services/blog/Dockerfile` 作成（ssmtp, sendmail, custom entrypoint）
    - `services/blog/docker-entrypoint-custom.sh` 作成（www-data 権限修正）
    - `docker-compose.yml` 修正（build, extra_hosts, mailserver_network）
    - メール送信テスト成功（naoya.iimura@gmail.com へ送信確認）
  - Task 1-2: ファイル書き込み権限修正 ✅
    - 全16サイトの wp-config.php に `define('FS_METHOD', 'direct');` 追加
    - ファイル所有者 www-data:www-data 確認
    - ブラウザでプラグインインストールテスト完了（FTP認証プロンプト表示されず）
  - Task 1-3: 暫定対応削除 ✅
    - WP Mail SMTP プラグイン削除
    - docker-compose.yml への設定集約完了
