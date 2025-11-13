# Cloudflare Tunnel設定: admin.kuma8088.com

## 📍 Zero Trust Dashboard
https://one.dash.cloudflare.com/

## 🔧 設定箇所
Networks → Tunnels → blog-tunnel → Public Hostnames → Add a public hostname

## ✅ 追加するホスト名

### admin.kuma8088.com
- **Hostname**: admin.kuma8088.com
- **Service Type**: HTTP
- **Service URL**: http://172.20.0.91:80
- **HTTP Settings**:
  - HTTP Host Header: admin.kuma8088.com
  - No TLS Verify: Off (デフォルト)

## 📝 説明

### Service URLについて
- `172.20.0.91`: unified-portal-frontend コンテナのIPアドレス（Nginx）
- `:80`: Nginxのリスニングポート
- Nginxが `/api/*` リクエストを `172.20.0.90:8000` (Backend) にプロキシ

### DNS設定
Cloudflare Tunnelを追加すると、admin.kuma8088.com のDNSレコードが自動的に作成されます。
- Type: CNAME
- Value: <tunnel-id>.cfargotunnel.com
- Proxy status: Proxied (オレンジクラウド)

## ✅ 設定後の確認

1. **Docker コンテナ起動**:
```bash
cd /opt/onprem-infra-system/project-root-infra/services/unified-portal
docker compose build
docker compose up -d
docker compose ps
```

2. **ローカル動作確認**:
```bash
curl -I http://172.20.0.91/health
curl -I http://172.20.0.91/api/v1/auth/login
```

3. **Cloudflare Tunnel経由の確認**:
```bash
curl -I https://admin.kuma8088.com/health
curl -I https://admin.kuma8088.com/api/v1/auth/login
```

4. **ブラウザで確認**:
- https://admin.kuma8088.com - Login画面が表示される
- https://admin.kuma8088.com/docs - API documentation (FastAPI Swagger)
- https://admin.kuma8088.com/health - Health check response

## 🔒 認証情報

### 初回ログイン
- **Username**: admin
- **Password**: (`.env` ファイルの `ADMIN_PASSWORD`)

⚠️ **重要**: 初回ログイン後、必ずパスワードを変更してください。

## 🔍 トラブルシューティング

### 502 Bad Gateway
- Backend/Frontendコンテナが起動しているか確認: `docker compose ps`
- Nginxログ確認: `docker compose logs frontend`
- Backendログ確認: `docker compose logs backend`

### 401 Unauthorized (ログインできない)
- `.env` ファイルの認証情報を確認
- Backendコンテナが環境変数を読み込んでいるか確認: `docker compose exec backend env | grep ADMIN`

### CORS Error
- `docker-compose.yml` の `CORS_ORIGINS` に `https://admin.kuma8088.com` が含まれているか確認
- Backendを再起動: `docker compose restart backend`

## 📚 関連ドキュメント
- [Backend README](/services/unified-portal/backend/README.md)
- [Frontend README](/services/unified-portal/frontend/README.md)
- [Blog System Cloudflare Tunnel設定](/docs/application/blog/cloudflare-tunnel-hostnames.md)
