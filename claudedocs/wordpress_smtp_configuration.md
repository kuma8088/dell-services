# WordPress SMTP Configuration

## 概要

全WordPressサイトでMailserver経由のSMTP送信を設定しました。

## 構成

- **WordPressコンテナ**: 172.22.0.30 (blog_network)
- **Postfixコンテナ**: 172.20.0.20 (mailserver_network)
- **接続**: WordPress → Postfix → SendGrid → 受信者

## Mailserver側設定変更

### Postfix TLS設定

**問題**: `smtpd_tls_security_level = encrypt` によりSTARTTLSが必須で、内部ネットワークからの接続が拒否された

**解決**: `smtpd_tls_security_level = may` に変更（TLSオプショナル）

**変更コマンド**:
```bash
cd /opt/onprem-infra-system/project-root-infra/services/mailserver
docker compose exec postfix bash -c "postconf -e 'smtpd_tls_security_level = may' && postfix reload"
```

**変更後の設定**:
```
smtpd_tls_security_level = may
smtpd_tls_auth_only = no
mynetworks = 127.0.0.0/8, 172.20.0.0/24, 172.22.0.0/24
```

**意味**:
- `may`: TLSはオプション（内部ネットワークはTLSなしで接続可能）
- `mynetworks`: 信頼されたネットワークからの認証なしリレーを許可

### 永続化の必要性

**注意**: コンテナ再起動時に設定が失われる可能性があるため、`/opt/onprem-infra-system/project-root-infra/services/mailserver/config/postfix/main.cf.tmpl` の行29も確認してください。

現在のテンプレートでは既に `smtpd_tls_security_level = may` になっていますが、何らかの理由で `encrypt` に上書きされていた可能性があります。

## WordPress側設定

### 対象サイト（16サイト）

| サイト | ドメイン | From Email |
|--------|----------|------------|
| fx-trader-life | fx-trader-life.com | noreply@fx-trader-life.com |
| fx-trader-life-4line | fx-trader-life.com | noreply@fx-trader-life.com |
| fx-trader-life-lp | fx-trader-life.com | noreply@fx-trader-life.com |
| fx-trader-life-mfkc | fx-trader-life.com | noreply@fx-trader-life.com |
| kuma8088-cameramanual | kuma8088.com | noreply@kuma8088.com |
| kuma8088-cameramanual-gwpbk492 | kuma8088.com | noreply@kuma8088.com |
| kuma8088-ec02test | kuma8088.com | noreply@kuma8088.com |
| kuma8088-elementor-demo-03 | kuma8088.com | noreply@kuma8088.com |
| kuma8088-elementor-demo-04 | kuma8088.com | noreply@kuma8088.com |
| kuma8088-elementordemo02 | kuma8088.com | noreply@kuma8088.com |
| kuma8088-elementordemo1 | kuma8088.com | noreply@kuma8088.com |
| kuma8088-test | kuma8088.com | noreply@kuma8088.com |
| toyota-phv | fx-trader-life.com | noreply@fx-trader-life.com |
| webmakeprofit | webmakeprofit.org | noreply@webmakeprofit.org |
| webmakeprofit-coconala | webmakeprofit.org | noreply@webmakeprofit.org |
| webmakesprofit | webmakesprofit.com | noreply@webmakesprofit.com |

### WP Mail SMTP設定

**プラグイン**: WP Mail SMTP by WPForms (v4.6.0)

**SMTP設定**:
```json
{
  "mail": {
    "from_email": "noreply@{domain}",
    "from_name": "{Site Name}",
    "mailer": "smtp",
    "return_path": false,
    "from_email_force": true,
    "from_name_force": true
  },
  "smtp": {
    "host": "172.20.0.20",
    "port": 25,
    "encryption": "none",
    "autotls": false,
    "auth": false
  },
  "general": {
    "summary_report_email_disabled": false
  }
}
```

**設定内容**:
- **Host**: `172.20.0.20` (Postfixコンテナ)
- **Port**: `25` (内部リレー用)
- **Encryption**: `none` (内部ネットワークのためTLS不要)
- **Authentication**: `false` (mynetworksに含まれているため不要)

## メール送信フロー

```
WordPress
  ↓ wp_mail()
WP Mail SMTP Plugin
  ↓ SMTP (172.20.0.20:25, no TLS)
Postfix (Dell)
  ↓ SMTP (smtp.sendgrid.net:587, TLS)
SendGrid
  ↓ SMTP
受信者 (Gmail等)
```

## SPF/DKIM/DMARC認証

SendGrid経由で送信されるため、以下の認証が適用されます:

- **SPF**: `43.207.242.167` (EC2 MX Gateway) 経由でSendGridに転送
- **DKIM**: SendGridが署名
- **DMARC**: ドメインのDMARCポリシーに従う

## テスト結果

### PHPMailer直接テスト

```bash
cd /opt/onprem-infra-system/project-root-infra/services/blog
docker compose exec wordpress wp eval "
use PHPMailer\PHPMailer\PHPMailer;
\$mail = new PHPMailer(true);
\$mail->isSMTP();
\$mail->Host = '172.20.0.20';
\$mail->Port = 25;
\$mail->SMTPAuth = false;
\$mail->SMTPAutoTLS = false;
\$mail->setFrom('noreply@kuma8088.com', 'Test Site');
\$mail->addAddress('naoya.iimura@gmail.com');
\$mail->Subject = 'SMTP Test';
\$mail->Body = 'Test email';
echo 'Result: ' . (\$mail->send() ? 'SUCCESS' : 'FAILED');
" --path=/var/www/html/kuma8088-test --allow-root
```

**結果**: SUCCESS

### wp_mail()テスト

```bash
docker compose exec wordpress wp eval "
var_dump(wp_mail('naoya.iimura@gmail.com', 'Test Subject', 'Test Body'));
" --path=/var/www/html/kuma8088-test --allow-root
```

**結果**: bool(true)

## トラブルシューティング

### 問題: `530 5.7.0 Must issue a STARTTLS command first`

**原因**: Postfixが `smtpd_tls_security_level = encrypt` でSTARTTLS必須になっている

**解決**:
```bash
docker compose exec postfix postconf -e 'smtpd_tls_security_level = may'
docker compose exec postfix postfix reload
```

### 問題: メールが迷惑メールに分類される

**原因**: WordPress PHP mail()関数で直接送信（SPF/DKIM未設定）

**解決**: WP Mail SMTPプラグインでMailserver経由送信に変更（本ドキュメントの設定）

## 保守手順

### 新しいWordPressサイト追加時

1. WP Mail SMTPプラグインインストール:
```bash
wp plugin install wp-mail-smtp --activate --path=/var/www/html/{site-name} --allow-root
```

2. SMTP設定:
```bash
wp option update wp_mail_smtp \
  '{"mail":{"from_email":"noreply@{domain}","from_name":"{Site Name}","mailer":"smtp","return_path":false,"from_email_force":true,"from_name_force":true},"smtp":{"host":"172.20.0.20","port":25,"encryption":"none","autotls":false,"auth":false},"general":{"summary_report_email_disabled":false}}' \
  --format=json --path=/var/www/html/{site-name} --allow-root
```

### 設定確認

```bash
docker compose exec wordpress wp option get wp_mail_smtp --path=/var/www/html/{site-name} --allow-root
```

## 実装日

2025-11-10

## 実装者

Claude Code (AI Assistant)
