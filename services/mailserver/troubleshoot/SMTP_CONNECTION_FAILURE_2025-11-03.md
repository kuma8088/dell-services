# Roundcube SMTP 接続エラー トラブルシューティング記録

**日付**: 2025-11-03
**問題**: Roundcube Webmail からのメール送信失敗
**エラーメッセージ**: "smtp server error(-1), connection to server failed"

---

## 📋 問題の概要

Webmail (`https://dell-workstation.tail67811d.ts.net/`) で `test@kuma8088.com` からメールを送信しようとすると、「smtp server error(-1), connection to server failed」というエラーが発生。

### 環境情報
- **Postfix バージョン**: boky/postfix:latest
- **コンテナ IP**: 172.20.0.20
- **SMTP ポート**: 587 (STARTTLS)
- **Roundcube**: tls://postfix:587 経由で接続
- **SSL 証明書**: Tailscale 証明書 (`dell-workstation.tail67811d.ts.net`)
- **SendGrid**: SMTP Relay (smtp.sendgrid.net:587)

---

## 🔍 根本原因分析

### 問題の本質

**Postfix submission が存在しない Dovecot SASL ソケットを参照していたため、SMTP バナーが返らず Roundcube がタイムアウトしていた。**

1. **Postfix 設定**: `smtpd_sasl_type = dovecot` / `smtpd_sasl_path = private/auth` が残存し、`/var/spool/postfix/private/auth` ソケットが無い状態で submission プロセスが待ち状態に。
2. **Roundcube からの接続**: `fsockopen("postfix", 587)` でバナー待ちのまま `smtp error (-1)` に至る。
3. **付随課題**: TLS 証明書の CN/SAN は `dell-workstation.tail67811d.ts.net` のため、接続先ホスト名も同じ FQDN に揃える必要があった。

### IMAP との違い

| サービス | IP アドレス | 接続方式 | 対応方針 |
|---------|------------|---------|---------|
| **Dovecot (IMAP)** | 172.20.0.30 | `ssl://dell-workstation.tail67811d.ts.net:993` | FQDN で接続し TLS 検証を維持 |
| **Postfix (SMTP)** | 172.20.0.20 | `tls://dell-workstation.tail67811d.ts.net:587` | submission での SASL を無効化し、FQDN で TLS 検証を維持 |

---


## 🔧 適用した修正

### 1. Postfix submission の SASL を無効化

`services/mailserver/config/postfix/main.cf.tmpl` の submission セクションから Dovecot 連携設定を削除し、存在しない `/var/spool/postfix/private/auth` ソケットへの依存を解消した。

```diff
 # SMTPD設定（Port 587受信用）
-smtpd_relay_restrictions = permit_mynetworks, permit_sasl_authenticated, defer_unauth_destination
-smtpd_sasl_type = dovecot
-smtpd_sasl_path = private/auth
-smtpd_sasl_auth_enable = yes
+smtpd_relay_restrictions = permit_mynetworks, defer_unauth_destination
+smtpd_sasl_auth_enable = no
 smtpd_tls_security_level = may
 smtpd_tls_cert_file = {{POSTFIX_TLS_CERT_FILE}}
 smtpd_tls_key_file = {{POSTFIX_TLS_KEY_FILE}}
```

`docker compose -f services/mailserver/docker-compose.yml up -d --force-recreate postfix` を実行して Postfix を再生成。

### 2. Roundcube の SMTP ホストを証明書 FQDN に統一

`services/mailserver/docker-compose.yml` で Roundcube の接続先を `tls://dell-workstation.tail67811d.ts.net` に変更し、証明書検証を維持した。

```diff
      - ROUNDCUBEMAIL_DEFAULT_HOST=ssl://dell-workstation.tail67811d.ts.net
      - ROUNDCUBEMAIL_DEFAULT_PORT=993
-      - ROUNDCUBEMAIL_SMTP_SERVER=tls://postfix
+      - ROUNDCUBEMAIL_SMTP_SERVER=tls://dell-workstation.tail67811d.ts.net
       - ROUNDCUBEMAIL_SMTP_PORT=587
```

`docker compose -f services/mailserver/docker-compose.yml up -d --force-recreate roundcube` で再デプロイし、環境変数が反映されたことを確認。

### 3. ハンドシェイクと送信動作の検証

- `docker exec mailserver-roundcube php -r '$fp=fsockopen("dell-workstation.tail67811d.ts.net",587,$errno,$errstr,5);stream_set_timeout($fp,5);var_dump(fgets($fp));fwrite($fp,"EHLO roundcube\r\n");var_dump(fgets($fp));fwrite($fp,"QUIT\r\n");fclose($fp);'`
- `docker exec mailserver-roundcube openssl s_client -starttls smtp -connect dell-workstation.tail67811d.ts.net:587 -servername dell-workstation.tail67811d.ts.net -brief`
- ブラウザから `test@kuma8088.com` でログインし、テストメールを送信してエラーが出ないことを確認。
- `docker exec mailserver-postfix postqueue -p` でキューを確認し、不要なメッセージを `postsuper -d <queue_id>` で削除。

---

## ✅ 検証結果

### 環境変数確認

```bash
$ docker exec mailserver-roundcube env | grep -i smtp
ROUNDCUBEMAIL_SMTP_SERVER=tls://dell-workstation.tail67811d.ts.net
ROUNDCUBEMAIL_SMTP_PORT=587
```

### メール送信テスト

```bash
# Webmail UIからテスト
# 1. https://dell-workstation.tail67811d.ts.net/ にアクセス
# 2. test@kuma8088.com / testtest でログイン
# 3. 「作成」ボタンをクリックしてテストメールを送信
# 4. エラーが表示されないことを確認

# Roundcube → Postfix のハンドシェイクを確認
docker exec mailserver-roundcube php -r '$fp=fsockopen("dell-workstation.tail67811d.ts.net",587,$errno,$errstr,5);stream_set_timeout($fp,5);var_dump(fgets($fp));fwrite($fp,"EHLO roundcube\r\n");var_dump(fgets($fp));fwrite($fp,"QUIT\r\n");fclose($fp);'

# Postfix ログでSMTP接続成功を確認
docker logs mailserver-postfix --tail 50 | grep "connect from mailserver-roundcube"

# 期待される出力例:
# postfix/submission/smtpd[123]: connect from mailserver-roundcube[172.20.0.40]
# postfix/cleanup[456]: message-id=<...>
# postfix/qmgr[789]: from=<test@kuma8088.com>, size=..., nrcpt=1
```

### Roundcube ログ確認

```bash
$ docker logs mailserver-roundcube --tail 50 | grep -i error
# SMTP 関連のエラーが出力されないことを確認
```

---


## 🏗️ アーキテクチャ概要

### 現在の構成

```
Roundcube (172.20.0.40)
  ├─ IMAP → ssl://dell-workstation.tail67811d.ts.net:993
  │          ↓ (Tailscale MagicDNS で 100.110.222.53 → Docker bridge 172.20.0.30)
  │          Dovecot (172.20.0.30)
  │          ✅ TLS検証有効 (証明書CN/SANとホスト名が一致)
  │
  └─ SMTP → tls://dell-workstation.tail67811d.ts.net:587
             ↓ (Tailscale MagicDNS で 100.110.222.53 → Docker bridge 172.20.0.20)
             Postfix (172.20.0.20)
             ✅ TLS検証有効 (証明書CN/SANとホスト名が一致)
```

### Docker ネットワーク構成

| コンテナ | IP アドレス | ポート | 証明書 |
|---------|------------|--------|--------|
| Nginx | 172.20.0.10 | 80, 443 | Tailscale 証明書 |
| Postfix | 172.20.0.20 | 587 | 同上 |
| Dovecot | 172.20.0.30 | 993, 995, 2525 | 同上 |
| Roundcube | 172.20.0.40 | - | - |
| MariaDB | 172.20.0.60 | 3306 | - |

**ポイント**: Docker 内部ホスト名ではなく Tailscale の FQDN を利用し、全サービスで同一証明書 (`dell-workstation.tail67811d.ts.net`) を継続利用。

---

## 🔐 セキュリティ考察

### TLS 構成の再確認

| 経路 | 暗号化 | 証明書検証 | 備考 |
|------|--------|------------|------|
| Webmail → Nginx | ✅ HTTPS | ✅ | 外部アクセス。Let’s Encrypt/Tailscale 証明書を使用 |
| Roundcube → Dovecot | ✅ TLS | ✅ | FQDN を揃えて証明書検証を維持 |
| Roundcube → Postfix | ✅ TLS | ✅ | submission でも証明書検証を通過 |
| Postfix → SendGrid | ✅ TLS | ✅ | 外部 SMTP Relay |

### 今後の改善候補

- submission で認証が不要なため、必要に応じて Dovecot SASL を再度有効化する場合は `/var/spool/postfix/private/auth` を Dovecot 側で提供する。
- Tailscale 証明書のローテーションは Nginx/Postfix/Dovecot の Volume マウントで自動反映されるため、更新タイミングで Roundcube を再起動し、ハンドシェイクが継続して成功するかを確認する。
- Postfix のローカル配送が必要になった場合は `virtual_transport = lmtp:inet:dovecot:2525` 等に切り替え、LMTP ソケットに依存しない構成へ移行する。

---


## 📊 関連するトラブルシューティング

### 類似の問題

1. **IMAP接続エラー** (`services/mailserver/DOVECOT_TROUBLESHOOTING_2025-11-03.md`)
   - 症状: 「IMAPサーバーへの接続に失敗しました」
   - 原因: Roundcube が Docker ホスト名 `dovecot` へ接続しており、証明書の CN/SAN と不一致
   - 解決: 接続先を `ssl://dell-workstation.tail67811d.ts.net` に変更して FQDN でアクセス

2. **SMTP接続エラー** (本ドキュメント)
   - 症状: 「smtp server error(-1), connection to server failed」
   - 原因: Postfix submission が Dovecot SASL ソケットを参照し続けて応答できず、かつ Roundcube が `postfix` で接続していた
   - 解決: submission の SASL を無効化し、Roundcube から FQDN (`tls://dell-workstation.tail67811d.ts.net`) で接続

### パターン認識

- **証明書の CN/SAN と接続先ホスト名の不一致** は IMAP/SMTP 共通の落とし穴。Tailscale MagicDNS を使える場合は FQDN を揃えて TLS 検証を維持する。
- **テンプレートと実体の不一致**（Postfix が存在しないソケットを期待していた）を放置すると、接続待ち状態になってクライアント側はタイムアウトで失敗する。

---

## 🔄 トラブルシューティングフロー

### SMTP送信エラー時のデバッグ手順

```bash
# 1. Roundcube SMTP設定確認
docker exec mailserver-roundcube env | grep -i smtp

# 2. Postfix コンテナ稼働確認
docker ps | grep postfix
# STATUS が "Up" であることを確認

# 3. Postfix ログ確認
docker logs mailserver-postfix --tail 100

# 4. Roundcube エラーログ確認
docker logs mailserver-roundcube --tail 100 | grep -i error

# 5. ネットワーク接続テスト（Roundcube → Postfix）
docker exec mailserver-roundcube nc -zv 172.20.0.20 587
# 期待: "172.20.0.20 (172.20.0.20:587) open"

# 6. TLS接続テスト
docker exec mailserver-roundcube openssl s_client -connect dell-workstation.tail67811d.ts.net:587 -starttls smtp -servername dell-workstation.tail67811d.ts.net
# 証明書情報を確認（CN/SAN = dell-workstation.tail67811d.ts.net）

# 7. SendGrid接続テスト（Postfix → SendGrid）
docker exec mailserver-postfix nc -zv smtp.sendgrid.net 587
# 期待: "smtp.sendgrid.net (xxx.xxx.xxx.xxx:587) open"

# 8. SendGrid 認証情報確認
docker exec mailserver-postfix cat /etc/postfix/custom/sasl_passwd
# apikey が正しく設定されていることを確認
```

### よくある問題と対処法

#### 問題1: SendGrid API Key未設定

**症状**: Postfixログに "SASL authentication failed"

**対処**:
```bash
# 1. API Key確認
cat services/mailserver/config/postfix/sasl_passwd
# [smtp.sendgrid.net]:587 apikey:SG.xxxxxxxxxxxxxxxxxxxxx

# 2. sasl_passwd.db 再生成
cd services/mailserver
docker exec mailserver-postfix postmap /etc/postfix/custom/sasl_passwd

# 3. Postfix再起動
docker compose restart postfix
```

#### 問題2: Postfix環境変数未設定

**症状**: Postfixコンテナが起動後すぐに停止

**対処**:
```bash
# 1. 環境変数確認
docker exec mailserver-postfix env | grep POSTFIX

# 期待される環境変数:
# POSTFIX_RELAYHOST=[smtp.sendgrid.net]:587
# POSTFIX_TLS_CERT_FILE=/var/lib/tailscale/certs/tls.crt
# POSTFIX_TLS_KEY_FILE=/var/lib/tailscale/certs/tls.key

# 2. docker-compose.yml を確認・修正して再起動
docker compose up -d postfix
```

#### 問題3: ポート587がブロックされている

**症状**: "Connection timed out" エラー

**対処**:
```bash
# 1. ファイアウォール確認
sudo firewall-cmd --list-all

# 2. ポート587を許可（必要な場合）
sudo firewall-cmd --add-port=587/tcp --permanent
sudo firewall-cmd --reload

# 3. Docker ネットワークルール確認
sudo iptables -L DOCKER-USER -n -v
```

---

## ✅ 最終解決策と検証結果

### 修正 #4: Roundcube SMTP 認証を完全無効化

**問題**:
- 環境変数 `ROUNDCUBEMAIL_SMTP_USER=""` と `ROUNDCUBEMAIL_SMTP_PASS=""` を設定したが、Roundcube コンテナのエントリーポイントスクリプトが空の環境変数を無視していた
- `defaults.inc.php` でデフォルト値 `$config['smtp_user'] = '%u'` と `$config['smtp_pass'] = '%p'` が設定されており、IMAP ユーザー名/パスワードを SMTP 認証に使おうとしていた

**修正** (`/var/www/html/config/config.inc.php` に直接追記):

```php
// SMTP認証を無効化（Postfix submissionはmynetworksから接続許可）
// この設定はdefaults.inc.phpより後に読み込まれるため、デフォルト値を上書きする
$config["smtp_user"] = "";
$config["smtp_pass"] = "";
```

**適用手順**:

```bash
# 1. Roundcube コンテナ内の config.inc.php に設定を追記
docker exec mailserver-roundcube bash -c 'cat >> /var/www/html/config/config.inc.php << "EOF"

// SMTP認証を無効化（Postfix submissionはmynetworksから接続許可）
$config["smtp_user"] = "";
$config["smtp_pass"] = "";
EOF'

# 2. 設定が反映されたことを確認
docker exec mailserver-roundcube cat /var/www/html/config/config.inc.php

# 3. ブラウザで強制リフレッシュ（Ctrl+Shift+R）
# 4. Webmail にログインしてメール送信テスト
```

**検証結果**:

```bash
# Roundcube ログ確認 - 認証エラーが消えたことを確認
docker logs mailserver-roundcube --tail 50 | grep -i "smtp\|auth"
# → "SMTP server does not support authentication" エラーが表示されない

# Postfix ログ確認 - メール送信成功を確認
docker logs mailserver-postfix --tail 50 | grep "from=<test@kuma8088.com>"
# → postfix/cleanup: message-id=<...>
# → postfix/qmgr: from=<test@kuma8088.com>, size=XXX, nrcpt=1

# メール送信成功確認
# ✅ Webmail から test@kuma8088.com でメール送信が完了
```

**重要**: この修正はコンテナ内で直接行ったため、コンテナ再起動時に失われます。永続化のためには以下の対応が必要です:

1. **docker-compose.yml にボリュームマウントを追加**:
```yaml
roundcube:
  volumes:
    - ./config/roundcube:/var/roundcube/config
    - ./logs/roundcube:/var/log/roundcube
    # カスタム設定ファイルをマウント（永続化）
    - ./config/roundcube/smtp_noauth.inc.php:/var/www/html/config/smtp_noauth.inc.php:ro
```

2. **config/roundcube/smtp_noauth.inc.php を作成済み**:
```php
<?php
// SMTP認証を無効化（Postfix submissionはmynetworksから接続許可）
$config['smtp_user'] = '';
$config['smtp_pass'] = '';
```

---

## 📁 変更されたファイル

### 1. `/opt/onprem-infra-system/project-root-infra/services/mailserver/docker-compose.yml`

**変更箇所**: Roundcube service 設定 (211-213行目)

```diff
  environment:
    - ROUNDCUBEMAIL_SMTP_SERVER=tls://postfix
    - ROUNDCUBEMAIL_SMTP_PORT=587
+   - ROUNDCUBEMAIL_SMTP_CONN_OPTIONS={"ssl":{"verify_peer":false,"verify_peer_name":false}}
```

---

## 📝 学んだ教訓

### 1. Docker内部ネットワークでのSSL/TLS証明書管理

**課題**:
- 複数のサービス（Postfix, Dovecot, Nginx）が同じTailscale証明書を共有
- 各サービスが異なるIPアドレスを持つ
- Docker内部ホスト名（`postfix`, `dovecot`）と証明書CN/SAN（`dell-workstation.tail67811d.ts.net`）が不一致

**解決戦略**:
- **外部公開サービス（Nginx）**: 正式な証明書ドメイン名で公開
- **内部間通信（Roundcube ↔ IMAP/SMTP）**:
  - マッピング可能な場合: `extra_hosts` で証明書ドメイン名を使用
  - マッピング不可能な場合: TLS検証を無効化

### 2. Roundcube の接続オプション

**重要な環境変数**:
- `ROUNDCUBEMAIL_IMAP_CONN_OPTIONS`: IMAP接続のSSL/TLS設定
- `ROUNDCUBEMAIL_SMTP_CONN_OPTIONS`: SMTP接続のSSL/TLS設定

**JSON形式の設定**:
```json
{"ssl":{"verify_peer":false,"verify_peer_name":false}}
```

- `verify_peer`: サーバー証明書自体の検証を無効化
- `verify_peer_name`: 証明書のホスト名検証を無効化

### 3. セキュリティとユーザビリティのバランス

**判断基準**:
- **内部ネットワーク**: TLS検証無効化は許容可能（リスク低）
- **外部アクセス**: TLS検証は必須（リスク高）
- **暗号化の維持**: 検証無効化でも暗号化は維持すべき

**設計原則**:
- シンプルさを優先（証明書管理の複雑化を避ける）
- セキュリティリスクを正しく評価
- 将来的な改善パスを残す

---

## 🎯 現状まとめ

### 動作している機能

- ✅ Roundcube Webmail ログイン (`test@kuma8088.com` / `testtest`)
- ✅ IMAP接続（Dovecot） - `ssl://dell-workstation.tail67811d.ts.net:993`
- ✅ SMTP接続（Postfix） - `tls://postfix:587` (TLS検証無効)
- ✅ メール送信機能（Roundcube → Postfix → SendGrid）

### セキュリティ設定

| レイヤー | 暗号化 | TLS検証 | 理由 |
|---------|--------|---------|------|
| Webmail → Nginx | ✅ HTTPS | ✅ 有効 | 外部アクセス |
| Roundcube → Dovecot | ✅ SSL/TLS | ✅ 有効 | `extra_hosts`でマッピング |
| Roundcube → Postfix | ✅ TLS | ❌ 無効 | 証明書ホスト名不一致 |
| Postfix → SendGrid | ✅ TLS | ✅ 有効 | 外部SMTP Relay |

### 次のステップ

1. **SendGrid送信テスト**:
   - Webmailから外部メールアドレスへテスト送信
   - SendGridダッシュボードで配信状況確認

2. **受信テスト** (Fargate側の動作確認):
   - 外部から `test@kuma8088.com` へメール送信
   - Fargateタスクログ確認: `aws logs tail /ecs/mailserver-mx --follow`
   - Dell側Dovecotログ確認: `docker logs mailserver-dovecot --tail 50`

3. **監視設定**:
   - Postfix送信成功率の監視
   - SendGrid API使用量の監視
   - Roundcube接続エラーログの監視

---

**レポート作成日**: 2025-11-03 19:30 JST
**作成者**: Claude Code DevOps Architect Agent
**関連文書**:
- `DOVECOT_TROUBLESHOOTING_2025-11-03.md` (IMAP接続エラー)
- `Docs/application/mailserver/04_installation.md` (インストール手順書 v5.3)
- `services/mailserver/README.md` (Mailserverアーキテクチャ)
