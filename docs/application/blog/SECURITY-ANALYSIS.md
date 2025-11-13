# Blog System セキュリティ分析

**作成日**: 2025-11-13
**対象**: Blog System（16 WordPressサイト）

---

## 📋 現在のセキュリティ構成

### Cloudflareによる保護（有効）

#### 1. Cloudflare Tunnel
- **機能**: Originサーバー（Dell）を直接インターネットに晒さない
- **効果**:
  - IPアドレスの隠蔽
  - DDoS攻撃からの保護
  - SSL/TLS暗号化（自動）

#### 2. Cloudflare DNS + Proxy
- **機能**: DNSレベルでのトラフィック制御
- **利用可能な機能**（プランによって異なる）:

**Freeプラン（現在）**:
- ✅ DDoS防御（無制限）
- ✅ SSL/TLS暗号化
- ✅ CDNキャッシュ
- ✅ 基本的なWAFルール（限定的）
- ⚠️ Rate Limiting（制限あり）
- ❌ Bot Management（Proプラン以上）
- ❌ 高度なWAFルール（Proプラン以上）

**Proプラン（月額$20/ドメイン）**:
- ✅ 高度なWAFルール
- ✅ カスタムルール（20個まで）
- ✅ Rate Limiting
- ✅ ページルール（20個）

---

## ⚠️ 現在のセキュリティギャップ

### 1. WordPress特有の脆弱性対策（未実装）

#### ログイン保護
- ❌ **ブルートフォース攻撃対策**: 未実装
- ❌ **ログイン試行回数制限**: 未実装
- ❌ **2段階認証**: 未実装
- ❌ **CAPTCHA**: 未実装

#### XMLRPCプロテクション
- ❌ **XMLRPC無効化**: 未実装（DDoS攻撃の標的になりやすい）
- ❌ **Pingback/Trackback無効化**: 未実装

#### ファイルアップロード
- ❌ **アップロード拡張子制限**: 未実装
- ❌ **ファイルサイズ制限**: php.iniのみ（64MB）
- ❌ **マルウェアスキャン**: 未実装

### 2. サーバーレベルのセキュリティ

#### Nginxセキュリティヘッダー
- ⚠️ **X-Frame-Options**: 未確認
- ⚠️ **X-Content-Type-Options**: 未確認
- ⚠️ **X-XSS-Protection**: 未確認
- ⚠️ **Content-Security-Policy**: 未実装

#### ファイアウォール
- ✅ **Docker内部ネットワーク**: 172.22.0.0/24（隔離）
- ✅ **Cloudflare Tunnel**: 直接アクセス不可
- ❌ **iptables/firewalld**: 未確認

---

## 🛡️ 推奨セキュリティ対策

### Phase 1: 即座に実装すべき対策（Critical）

#### 1. WordPressセキュリティプラグイン導入

**推奨プラグイン**: Wordfence Security（無料版）

```bash
# 全16サイトにWordfence導入
cd /opt/onprem-infra-system/project-root-infra/services/blog

for site in kuma8088 demo1-kuma8088 webmakeprofit uminomoto-shoyu \
    akihide-shiraki-fc kodomo-toushi moshilog tousi-mama \
    furusato-media kosodate-genki warakuwork jissenjournalism \
    lachic-style kuma8088-life kuma8088-money kuma8088-blog; do
    docker compose exec wordpress wp plugin install wordfence \
        --activate --path="/var/www/html/$site"
done
```

**機能**:
- ブルートフォース攻撃防御
- マルウェアスキャン
- ファイアウォール
- ログイン試行回数制限
- 2段階認証

#### 2. XMLRPC無効化

**方法A: プラグイン（推奨）**
```bash
# Disable XML-RPC プラグイン導入
for site in kuma8088 demo1-kuma8088 ...; do
    docker compose exec wordpress wp plugin install disable-xml-rpc \
        --activate --path="/var/www/html/$site"
done
```

**方法B: Nginx設定**
```nginx
# services/blog/config/nginx/conf.d/security.conf
location = /xmlrpc.php {
    deny all;
    access_log off;
    log_not_found off;
}
```

#### 3. Nginxセキュリティヘッダー追加

**services/blog/config/nginx/conf.d/security-headers.conf**:
```nginx
# Security Headers
add_header X-Frame-Options "SAMEORIGIN" always;
add_header X-Content-Type-Options "nosniff" always;
add_header X-XSS-Protection "1; mode=block" always;
add_header Referrer-Policy "strict-origin-when-cross-origin" always;
add_header Permissions-Policy "geolocation=(), microphone=(), camera=()" always;

# Content Security Policy (調整必要)
# add_header Content-Security-Policy "default-src 'self'; script-src 'self' 'unsafe-inline' 'unsafe-eval'; style-src 'self' 'unsafe-inline';" always;
```

### Phase 2: 中期的に実装すべき対策（High）

#### 4. Cloudflare WAFルール設定

**Cloudflare Dashboard → Security → WAF**:

```yaml
# WordPressログインページ保護
Rule 1:
  Expression: (http.request.uri.path contains "/wp-login.php")
  Action: Challenge (CAPTCHA)

# XMLRPC保護
Rule 2:
  Expression: (http.request.uri.path eq "/xmlrpc.php")
  Action: Block

# wp-admin保護（管理者IPのみ許可）
Rule 3:
  Expression: (http.request.uri.path contains "/wp-admin" and ip.src ne YOUR_IP)
  Action: Challenge
```

#### 5. Rate Limiting設定

**Cloudflare Dashboard → Security → Rate Limiting**:

```yaml
# ログインページRate Limiting
Rule:
  Match: http.request.uri.path contains "/wp-login.php"
  Requests: 5 requests per 60 seconds
  Action: Block for 600 seconds
```

#### 6. ファイルアップロード制限

**wp-config.php に追加**:
```php
// ファイルアップロード制限
define('ALLOW_UNFILTERED_UPLOADS', false);

// 許可する拡張子
define('ALLOWED_FILE_TYPES', 'jpg|jpeg|png|gif|pdf|doc|docx|ppt|pptx|xls|xlsx|zip');
```

### Phase 3: 長期的に検討すべき対策（Medium）

#### 7. WAF専用ソリューション導入

**選択肢**:
- **ModSecurity**: Nginx用WAFモジュール（OWASP Core Rule Set）
- **fail2ban**: ログベースの侵入防止
- **CrowdSec**: コミュニティベースのIPS

#### 8. セキュリティ監視・ログ管理

- Wordfenceログ統合
- Nginx access/errorログ監視
- 異常検知アラート設定

#### 9. 定期的なセキュリティ監査

- WordPress Core/Plugin/Theme 更新チェック（週次）
- 脆弱性スキャン（月次）
- パスワードローテーション（四半期）

---

## 🔍 現在のリスク評価

### Critical（即座に対応必要）

1. **ブルートフォース攻撃**: ❌ 未対策
   - **リスク**: ログインページへの総当たり攻撃
   - **影響**: サイト乗っ取り、データ漏洩
   - **対策**: Wordfence導入（Phase 1-1）

2. **XMLRPC DDoS攻撃**: ❌ 未対策
   - **リスク**: XMLRPC経由のDDoS攻撃
   - **影響**: サーバーダウン、リソース枯渇
   - **対策**: XMLRPC無効化（Phase 1-2）

### High（早急に対応推奨）

3. **セキュリティヘッダー欠落**: ⚠️ 部分的
   - **リスク**: XSS、クリックジャッキング
   - **影響**: ユーザー情報漏洩
   - **対策**: Nginxヘッダー追加（Phase 1-3）

4. **Rate Limiting未設定**: ⚠️ 未設定
   - **リスク**: アプリケーションレベルDDoS
   - **影響**: サービス停止
   - **対策**: Cloudflare Rate Limiting（Phase 2-5）

### Medium（中長期的に検討）

5. **WAF未導入**: ⚠️ Cloudflare Freeプラン限定的
   - **リスク**: SQLインジェクション、XSS等
   - **影響**: データベース改ざん
   - **対策**: ModSecurity導入（Phase 3-7）

---

## 📊 Cloudflareプラン比較

| 機能 | Free | Pro ($20/月) | Business ($200/月) |
|------|------|--------------|-------------------|
| DDoS防御 | ✅ 無制限 | ✅ 無制限 | ✅ 無制限 |
| SSL/TLS | ✅ | ✅ | ✅ |
| WAF | ⚠️ 基本 | ✅ 高度 | ✅ 高度+ |
| Rate Limiting | ❌ | ✅ | ✅ |
| Bot Management | ❌ | ⚠️ 限定 | ✅ |
| ページルール | 3個 | 20個 | 50個 |
| カスタムルール | ❌ | 20個 | 100個 |
| **推奨度** | 現状維持可 | ✅ 推奨 | 過剰 |

**結論**: **Proプラン（$20/月）へのアップグレードを推奨**
- Rate Limitingでブルートフォース攻撃防御
- 高度なWAFルールでWordPress特有の攻撃防御
- コストパフォーマンス良好

---

## 🚀 実装手順

### Step 1: Wordfence導入（30分）

```bash
cd /opt/onprem-infra-system/project-root-infra/services/blog

# スクリプト作成
cat > ./scripts/install-wordfence.sh << 'EOF'
#!/bin/bash
SITES=(kuma8088 demo1-kuma8088 webmakeprofit uminomoto-shoyu \
    akihide-shiraki-fc kodomo-toushi moshilog tousi-mama \
    furusato-media kosodate-genki warakuwork jissenjournalism \
    lachic-style kuma8088-life kuma8088-money kuma8088-blog)

for site in "${SITES[@]}"; do
    echo "Installing Wordfence for $site..."
    docker compose exec wordpress wp plugin install wordfence \
        --activate --path="/var/www/html/$site"
done
EOF

chmod +x ./scripts/install-wordfence.sh
./scripts/install-wordfence.sh
```

### Step 2: XMLRPC無効化（10分）

```bash
# Nginxに追加
cat > ./config/nginx/conf.d/block-xmlrpc.conf << 'EOF'
location = /xmlrpc.php {
    deny all;
    access_log off;
    log_not_found off;
}
EOF

# Nginx再起動
docker compose exec nginx nginx -t
docker compose exec nginx nginx -s reload
```

### Step 3: セキュリティヘッダー追加（10分）

```bash
# セキュリティヘッダー追加
cat > ./config/nginx/conf.d/security-headers.conf << 'EOF'
add_header X-Frame-Options "SAMEORIGIN" always;
add_header X-Content-Type-Options "nosniff" always;
add_header X-XSS-Protection "1; mode=block" always;
add_header Referrer-Policy "strict-origin-when-cross-origin" always;
EOF

# Nginx再起動
docker compose exec nginx nginx -t
docker compose exec nginx nginx -s reload
```

### Step 4: Cloudflare設定（20分）

1. Cloudflare Dashboard ログイン
2. Security → WAF → Create rule
3. 上記のWAFルールを追加
4. Security → Rate Limiting → Create rule
5. 上記のRate Limitingルールを追加

---

## 📝 チェックリスト

- [ ] Wordfence導入（全16サイト）
- [ ] XMLRPC無効化（Nginx）
- [ ] セキュリティヘッダー追加（Nginx）
- [ ] Cloudflare WAFルール設定
- [ ] Cloudflare Rate Limiting設定
- [ ] WordPress自動更新有効化
- [ ] 定期バックアップ確認（既存）
- [ ] Cloudflare Proプラン検討

---

## 📚 参考リソース

- [Wordfence Documentation](https://www.wordfence.com/help/)
- [Cloudflare WAF](https://developers.cloudflare.com/waf/)
- [WordPress Security](https://wordpress.org/support/article/hardening-wordpress/)
- [OWASP WordPress Security](https://owasp.org/www-project-wordpress-security/)

---

## 📅 更新履歴

- 2025-11-13: 初版作成（セキュリティ分析）
