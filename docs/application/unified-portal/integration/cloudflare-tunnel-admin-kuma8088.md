# Cloudflare Tunnel設定: admin.kuma8088.com

## 📍 Zero Trust Dashboard
https://one.dash.cloudflare.com/

## 🔧 設定箇所
Networks → Tunnels → blog-tunnel → Public Hostnames

## ✅ 追加するホスト名

### Unified Portal Management Interface
**Hostname**: admin.kuma8088.com
**Service Type**: HTTP
**URL**: http://nginx:80
**HTTP Host Header**: admin.kuma8088.com

## 📝 設定手順

### 1. Cloudflare Zero Trust Dashboardにアクセス
```
https://one.dash.cloudflare.com/
```

### 2. Tunnelセクションに移動
```
Networks → Tunnels → blog-tunnel
```

### 3. Public Hostname追加
- **Add a public hostname** ボタンをクリック
- **Subdomain**: admin
- **Domain**: kuma8088.com
- **Path**: (空欄)
- **Service**:
  - Type: HTTP
  - URL: nginx:80
- **Additional application settings**:
  - HTTP Settings → HTTP Host Header: admin.kuma8088.com
- **Save hostname** ボタンをクリック

### 4. Nginx設定を Blog Nginxに配置

Unified Portal用のNginx設定をBlog Nginxに追加します:

```bash
# Unified Portal Nginx設定をBlog Nginxにコピー
cd /opt/onprem-infra-system/project-root-infra/services
cp unified-portal/config/nginx/conf.d/admin-kuma8088.conf \
   blog/config/nginx/conf.d/

# Blog Nginx再起動
cd blog
docker compose restart nginx

# Nginx設定確認
docker compose exec nginx nginx -t
docker compose logs -f nginx
```

### 5. DNS設定確認

Cloudflare Dashboard でDNSレコードを確認:
```
DNS → Records → admin.kuma8088.com
```

以下のレコードが自動作成されます:
- **Type**: CNAME
- **Name**: admin
- **Target**: [tunnel-id].cfargotunnel.com
- **Proxy status**: Proxied (オレンジクラウド)

### 6. 動作確認

```bash
# Health endpoint確認
curl -s https://admin.kuma8088.com/health | jq .

# API endpoint確認
curl -s https://admin.kuma8088.com/api/mailserver/domains | jq .total

# Frontend確認
curl -s https://admin.kuma8088.com/ | head -20
```

期待される結果:
- `/health`: `{"status":"healthy","service":"Unified Portal Backend","version":"0.1.0"}`
- `/api/mailserver/domains`: ドメイン一覧のJSON
- `/`: React frontend HTML

## 🔍 トラブルシューティング

### 502 Bad Gateway エラー
**原因**: Nginxがbackendに接続できない

**確認**:
```bash
# Backend稼働確認
docker ps | grep unified-portal-backend

# Nginx → Backend接続確認
cd /opt/onprem-infra-system/project-root-infra/services/blog
docker compose exec nginx curl -s http://172.20.0.92:8000/health
```

### 404 Not Found エラー
**原因**: Nginx設定ファイルが正しく配置されていない

**確認**:
```bash
# admin-kuma8088.conf存在確認
ls -la /opt/onprem-infra-system/project-root-infra/services/blog/config/nginx/conf.d/admin-kuma8088.conf

# Nginx設定ロード確認
docker compose exec nginx nginx -T | grep "admin.kuma8088.com"
```

### SSL/TLS エラー
**原因**: Cloudflare SSL/TLS設定が不正

**確認**:
```
Cloudflare Dashboard → SSL/TLS → Overview → Full (strict)
```

## 📊 設定完了後の状態

### Public Hostnames一覧
```
blog-tunnel:
  - blog.fx-trader-life.com → http://nginx:80
  - blog.webmakeprofit.org → http://nginx:80
  - blog.webmakesprofit.com → http://nginx:80
  - blog.toyota-phv.jp → http://nginx:80
  - blog.kuma8088.com (+ 10 subdirectories) → http://nginx:80
  - admin.kuma8088.com → http://nginx:80  ← NEW
```

### アクセスフロー
```
Internet
  ↓ HTTPS
Cloudflare Edge
  ↓ Cloudflare Tunnel (blog-tunnel)
Blog Nginx (172.22.0.50:80)
  ↓ Proxy to admin.kuma8088.com virtual host
Unified Portal Backend (172.20.0.92:8000) OR Frontend (172.20.0.91:80)
```

## ✅ 設定完了チェックリスト

- [ ] Cloudflare Zero Trust Dashboard でadmin.kuma8088.com Public Hostname追加完了
- [ ] admin-kuma8088.conf を Blog Nginx conf.d/ にコピー完了
- [ ] Blog Nginx再起動完了
- [ ] `nginx -t` で構文エラーなし
- [ ] https://admin.kuma8088.com/health で200 OK
- [ ] https://admin.kuma8088.com/api/mailserver/domains でJSON取得
- [ ] https://admin.kuma8088.com/ でReact frontend表示
- [ ] Cloudflare DNS Records でCNAME確認完了

## 📅 実施タイミング
L-016: Cloudflare Tunnel設定更新 (Phase 4-L: デプロイ・本番移行)

## 🔗 関連ドキュメント
- [03_TASK_BREAKDOWN.md](03_TASK_BREAKDOWN.md) - タスク一覧
- [Blog Cloudflare Tunnel設定](../../blog/cloudflare-tunnel-hostnames.md) - 既存設定参考
