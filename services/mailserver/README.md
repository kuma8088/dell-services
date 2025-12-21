# Mailserver Services

このディレクトリは Dell 側メールサーバー環境を Docker Compose で起動するための設定とスクリプトを保持します。Postfix の構成はテンプレート化され、コンテナ起動時に自動生成されます。

## Docker Compose サービス構成

Dell上で稼働中の9つのコンテナ:

| サービス | 役割 | ポート | 説明 |
|---------|------|--------|------|
| **postfix** | SMTP送信 | 25, 587 | SendGrid経由でメール送信 |
| **dovecot** | IMAP/POP3受信 | 993, 995, 2525 | メール受信・保存（LMTP） |
| **mariadb** | データベース | 3306 | ユーザー管理・Roundcube DB |
| **clamav** | ウイルススキャン | - | メール添付ファイルスキャン |
| **rspamd** | スパムフィルタ | - | スパム判定・学習 |
| **roundcube** | Webメール | 8080 | ブラウザメールクライアント |
| **usermgmt** | ユーザー管理 | 5000 | Flask管理画面（Phase 11） |
| **mailserver-api** | メール受信API | 5000 | Cloudflare Email Worker連携 |
| **nginx** | リバースプロキシ | 443 | HTTPS終端・Tailscale証明書 |

**ネットワーク構成**:
- Dell: Docker Composeでホスト上に直接起動
- メール受信: Cloudflare Email Routing → Email Worker → mailserver-api → Dovecot LMTP
- メール送信: Postfix → SendGrid Relay

**データ永続化**:
- メールボックス: `./data/vmail`
- MariaDB: `./data/db`
- Rspamd学習データ: `./data/rspamd`

## 仕組みの概要

- `docker-compose.yml` の `postfix` サービスは `./config/postfix/main.cf.tmpl` を参照し、エントリポイントスクリプト (`scripts/postfix-entrypoint.sh`) が起動時に `/etc/postfix/main.cf` を生成します。
- テンプレートは環境変数で値が埋め込まれます。`MAIL_DOMAIN`・`MAIL_HOSTNAME`・`MAIL_ADDITIONAL_DOMAINS`・`POSTFIX_RELAYHOST`・`POSTFIX_MESSAGE_SIZE_LIMIT`・`POSTFIX_TLS_CERT_FILE`・`POSTFIX_TLS_KEY_FILE` を設定すると、再起動ごとに最新値へ反映されます。
- `MAIL_ADDITIONAL_DOMAINS` にスペース区切りで複数ドメインを指定すると、自動で `virtual_mailbox_domains` にカンマ区切りで展開されます。
- `config/postfix/sasl_passwd` はコンテナ起動時に `/etc/postfix/sasl_passwd` へコピーされ、`postmap` が自動実行されます。
- ClamAV は `config/clamav/clamd.conf` と `config/clamav/freshclam.conf` を読み込みます。`LocalSocket` を `/var/run/clamav/clamd.ctl` に揃えているため、FreshClam の NotifyClamd が正しく動作し、ウイルス定義更新後にデーモンへ通知されます。
- Nginx は `/etc/nginx/templates/*.template` に配置した `mailserver.conf.template` を `envsubst` で展開します。`MAIL_HOSTNAME` と `TLS_CERT_FILE`/`TLS_KEY_FILE` は `.env` の値（Postfix と共通）を使用し、`NGINX_DOLLAR=$$` を渡すことで `$host` などの Nginx 変数を保持します。

## 事前準備

### 1. `.env` の主な項目

```
# メインドメイン
MAIL_DOMAIN=kuma8088.com
MAIL_HOSTNAME=mail.kuma8088.com
MAIL_ADDITIONAL_DOMAINS="fx-trader-life.com,webmakeprofit.org,webmakesprofit.com,edgeshift.tech"

# Roundcube / DB などは従来どおり

# Postfix テンプレートの可変パラメータ（必要に応じて上書き）
POSTFIX_RELAYHOST=[smtp.sendgrid.net]:587
POSTFIX_MESSAGE_SIZE_LIMIT=26214400
# Tailscale cert を固定名で発行した場合の証明書パス
POSTFIX_TLS_CERT_FILE=/var/lib/tailscale/certs/tls.crt
POSTFIX_TLS_KEY_FILE=/var/lib/tailscale/certs/tls.key
```

`POSTFIX_TLS_CERT_FILE` / `POSTFIX_TLS_KEY_FILE` を省略した場合、エントリポイントは `/var/lib/tailscale/certs/tls.crt` / `.key` を参照します。

### 2. Tailscale 証明書の固定パス化（推奨）

Tailscale の MagicDNS 名は再取得時に変わるため、証明書ファイル名を固定しておくと運用が簡単です。

```bash
MAGICDNS_NAME=$(tailscale status --json | jq -r '.Self.DNSName' | sed 's/\.$//')
sudo tailscale cert \
  --cert-file /var/lib/tailscale/certs/tls.crt \
  --key-file  /var/lib/tailscale/certs/tls.key \
  "${MAGICDNS_NAME}"
```

`tailscale cert` を定期的に実行する systemd timer を設定しておくと、証明書更新が自動化できます。

### 3. SendGrid API Key 取得（Secrets Manager）

AWS CLI の認証情報が設定されている状態で、Secrets Manager から API Key を取得し `sasl_passwd` に反映できます。

```bash
cd /opt/onprem-infra-system/project-root-infra/services/mailserver
./scripts/sync-sendgrid-sasl.sh \
  arn:aws:secretsmanager:ap-northeast-1:552927148143:secret:mailserver/sendgrid/api-key-76cdsG
# 実行後に Postfix を再読込
docker compose restart postfix
```

デフォルトのシークレット ID (`mailserver/sendgrid/api-key`) を使う場合は引数を省略できます。

## 起動

```bash
cd /opt/onprem-infra-system/project-root-infra/services/mailserver
docker compose up -d postfix
```

初回起動時に `postfix-entrypoint.sh` がテンプレートをレンダリングし、`/etc/postfix/main.cf` と SASL マップを生成します。ログは `logs/postfix/` に出力されます。

Nginx のテンプレートを反映する場合は以下のように起動します。`MAIL_HOSTNAME` や証明書パスを `.env` で更新したあとに再起動すると、`/etc/nginx/conf.d/mailserver.conf` が自動生成されます。

```bash
docker compose up -d nginx
docker compose logs -f nginx
```

ClamAV の設定を反映する場合は以下の順で再起動してください。

```bash
docker compose up -d clamav
docker compose logs -f clamav
```

FreshClam が正常に完了すると `freshclam.log` に「Clamd was NOT notified」警告が出ず、ウイルス定義更新後に通知メッセージが記録されます。

## トラブルシュート

- **TLS 証明書が見つからない**: `POSTFIX_TLS_CERT_FILE` と `POSTFIX_TLS_KEY_FILE` のパスを確認し、ホスト側でファイルが存在するかチェックしてください。スクリプトはファイル欠如を警告しますが、Postfix は TLS なしで起動します。
- **SendGrid 認証失敗**: `config/postfix/sasl_passwd` が正しい API Key を保持しているか、コンテナ起動後に `postmap` が自動生成した `sasl_passwd.db` が存在するか確認します。
- **追加ドメインが反映されない**: `.env` の `MAIL_ADDITIONAL_DOMAINS` を編集後、`docker compose restart postfix` で再起動すると新しい main.cf が生成されます。
- **Nginx が `$magicdns_name` など未知の変数で停止する**: テンプレートへ直接値を書き込む必要はありません。`.env` の `MAIL_HOSTNAME`／証明書パスを更新し、`docker compose up -d nginx` を再実行してください。`NGINX_DOLLAR=$$` 環境変数が渡されていることを確認すると `$host` や `$scheme` が正しく展開されます。

## 構成ファイルの追加

Postfix の補助設定（`master.cf` など）を追加する場合は `config/postfix/` 配下に配置し、必要に応じて `postfix-entrypoint.sh` でコピー処理を追加してください。テンプレートは `config/postfix/main.cf.tmpl` として管理されるため、直接 `/etc/postfix/main.cf` を編集しても再起動時に上書きされます。
