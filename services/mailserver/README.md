# Mailserver Services

このディレクトリは Dell 側メールサーバー環境を Docker Compose で起動するための設定とスクリプトを保持します。Postfix の構成はテンプレート化され、コンテナ起動時に自動生成されます。

## 仕組みの概要

- `docker-compose.yml` の `postfix` サービスは `./config/postfix/main.cf.tmpl` を参照し、エントリポイントスクリプト (`scripts/postfix-entrypoint.sh`) が起動時に `/etc/postfix/main.cf` を生成します。
- テンプレートは環境変数で値が埋め込まれます。`MAIL_DOMAIN`・`MAIL_HOSTNAME`・`MAIL_ADDITIONAL_DOMAINS`・`POSTFIX_RELAYHOST`・`POSTFIX_MESSAGE_SIZE_LIMIT`・`POSTFIX_TLS_CERT_FILE`・`POSTFIX_TLS_KEY_FILE` を設定すると、再起動ごとに最新値へ反映されます。
- `MAIL_ADDITIONAL_DOMAINS` にスペース区切りで複数ドメインを指定すると、自動で `virtual_mailbox_domains` にカンマ区切りで展開されます。
- `config/postfix/sasl_passwd` はコンテナ起動時に `/etc/postfix/sasl_passwd` へコピーされ、`postmap` が自動実行されます。

## 事前準備

### 1. `.env` の主な項目

```
# メインドメイン
MAIL_DOMAIN=kuma8088.com
MAIL_HOSTNAME=mail.kuma8088.com
MAIL_ADDITIONAL_DOMAINS="fx-trader-life.com webmakeprofit.org webmakesprofit.com"

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

## 起動

```bash
cd /opt/onprem-infra-system/project-root-infra/services/mailserver
docker compose up -d postfix
```

初回起動時に `postfix-entrypoint.sh` がテンプレートをレンダリングし、`/etc/postfix/main.cf` と SASL マップを生成します。ログは `logs/postfix/` に出力されます。

## トラブルシュート

- **TLS 証明書が見つからない**: `POSTFIX_TLS_CERT_FILE` と `POSTFIX_TLS_KEY_FILE` のパスを確認し、ホスト側でファイルが存在するかチェックしてください。スクリプトはファイル欠如を警告しますが、Postfix は TLS なしで起動します。
- **SendGrid 認証失敗**: `config/postfix/sasl_passwd` が正しい API Key を保持しているか、コンテナ起動後に `postmap` が自動生成した `sasl_passwd.db` が存在するか確認します。
- **追加ドメインが反映されない**: `.env` の `MAIL_ADDITIONAL_DOMAINS` を編集後、`docker compose restart postfix` で再起動すると新しい main.cf が生成されます。

## 構成ファイルの追加

Postfix の補助設定（`master.cf` など）を追加する場合は `config/postfix/` 配下に配置し、必要に応じて `postfix-entrypoint.sh` でコピー処理を追加してください。テンプレートは `config/postfix/main.cf.tmpl` として管理されるため、直接 `/etc/postfix/main.cf` を編集しても再起動時に上書きされます。
