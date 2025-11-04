# Dovecot IMAP 認証トラブルシューティング記録

**日付**: 2025-11-03
**問題**: Roundcube Webmail から Dovecot IMAP サーバーへの接続失敗
**エラーメッセージ**: "IMAPサーバーへの接続に失敗しました。"

---

## 📋 問題の概要

Webmail (`https://dell-workstation.tail67811d.ts.net/`) で `test@kuma8088.com` でログインしようとすると、「IMAPサーバーへの接続に失敗しました」というエラーが発生。

### 環境情報
- **Dovecot バージョン**: 2.3.21 (Docker: dovecot/dovecot:2.3.21)
- **コンテナ IP**: 172.20.0.30
- **IMAPS ポート**: 993
- **Roundcube**: ssl://dovecot:993 経由で接続
- **SSL 証明書**: Tailscale 証明書 (`dell-workstation.tail67811d.ts.net`)

---

## 🔍 実施した調査と修正

### 修正 #1: SSL 証明書パスの修正
**問題**: dovecot.conf で環境変数 `$MAGICDNS_NAME` が展開されていなかった

**修正前**:
```conf
ssl_cert = </var/lib/tailscale/certs/$MAGICDNS_NAME.crt
ssl_key = </var/lib/tailscale/certs/$MAGICDNS_NAME.key
```

**修正後** (`config/dovecot/dovecot.conf:9-10`):
```conf
ssl_cert = </var/lib/tailscale/certs/tls.crt
ssl_key = </var/lib/tailscale/certs/tls.key
```

**結果**: SSL handshake は成功するようになった

---

### 修正 #2: users ファイルのマウント追加
**問題**: users ファイルがコンテナ内で `/etc/dovecot/users` にマウントされていなかった

**修正** (`docker-compose.yml:121`):
```yaml
volumes:
  - ./config/dovecot:/etc/dovecot/custom
  - ./config/dovecot/users:/etc/dovecot/users:ro  # 追加
  - mail_data:/var/mail/vhosts
  - /var/lib/tailscale/certs:/var/lib/tailscale/certs:ro
  - ./logs/dovecot:/var/log
```

---

### 修正 #3: カスタム設定ファイルの使用
**問題**: Dovecot がデフォルト設定で起動していた

**修正** (`docker-compose.yml:109`):
```yaml
dovecot:
  image: dovecot/dovecot:2.3.21
  container_name: mailserver-dovecot
  hostname: dovecot
  restart: always
  command: ["/usr/sbin/dovecot", "-F", "-c", "/etc/dovecot/custom/dovecot.conf"]  # 追加
```

---

### 修正 #4: SSL プロトコル設定の更新
**問題**: 非推奨の `ssl_protocols` ディレクティブを使用

**修正前**:
```conf
ssl_protocols = !SSLv3 !TLSv1 !TLSv1.1
```

**修正後** (`config/dovecot/dovecot.conf:11`):
```conf
ssl_min_protocol = TLSv1.2
```

---

### 修正 #5: Postfix SASL 認証の無効化
**問題**: Postfix ユーザーが存在しないため、auth サービスが起動失敗

**修正** (`config/dovecot/dovecot.conf:56-63`):
```conf
# Postfix SASL認証 (現在無効化 - Postfixユーザーなし)
#service auth {
#    unix_listener /var/spool/postfix/private/auth {
#        mode = 0660
#        user = postfix
#        group = postfix
#    }
#}
```

---

### 修正 #6: Roundcube SSL 検証のスキップ
**問題**: 証明書の CN (`dell-workstation.tail67811d.ts.net`) とホスト名 (`dovecot`) が一致しない

**修正** (`docker-compose.yml:215-216`):
```yaml
environment:
  - ROUNDCUBEMAIL_IMAP_CONN_OPTIONS={"ssl":{"verify_peer":false,"verify_peer_name":false}}
  - ROUNDCUBEMAIL_SMTP_CONN_OPTIONS={"ssl":{"verify_peer":false,"verify_peer_name":false}}
```

---

### 修正 #7: IMAP ポート設定の構文エラー修正
**問題**: `port =143` (スペースなし)

**修正** (`config/dovecot/dovecot.conf:37`):
```conf
# 修正前
port =143

# 修正後
port = 143
```

---

### 修正 #9: Roundcube 接続先ホスト名の統一
**問題**: Roundcube が `ssl://dovecot:993` へ接続しており、Dovecot が提示する証明書の CN/SAN (`dell-workstation.tail67811d.ts.net`) と不一致で TLS 検証に失敗していた。

**修正** (`services/mailserver/docker-compose.yml:209-220`):
```yaml
- ROUNDCUBEMAIL_DEFAULT_HOST=ssl://dovecot
+ ROUNDCUBEMAIL_DEFAULT_HOST=ssl://dell-workstation.tail67811d.ts.net
+
extra_hosts:
  - "dell-workstation.tail67811d.ts.net:172.20.0.30"
```

**補足**:
- TLS 検証回避用に追加していた `ROUNDCUBEMAIL_IMAP_CONN_OPTIONS` / `ROUNDCUBEMAIL_SMTP_CONN_OPTIONS` を削除し、デフォルトの証明書検証に戻した。
- `docker compose -f services/mailserver/docker-compose.yml up -d roundcube` で Roundcube コンテナを再作成。
- `curl` を用いたログインテスト（`test@kuma8088.com` / `testtest`）後、`https://dell-workstation.tail67811d.ts.net/?_task=mail` にて Inbox HTML が取得できることを確認。
- `docker logs mailserver-roundcube --tail 50` で IMAP/TLS のエラーが消え、`GET /?_task=login`→`POST /?_task=login` が 302 → Inbox 表示へ遷移することを確認。

**結果**: Roundcube Webmail からの IMAP ログインが成功するようになった。

---

### 修正 #10: Roundcube SMTP 接続エラーの解消
**問題**: Roundcube からメール送信時に `smtp error (-1): server connection failed` が表示され、Postfix 587/TLS への接続がハングしていた。

**原因調査**:
- `docker exec mailserver-roundcube php -r 'fsockopen(\"postfix\",587,...)'` で SMTP バナーが返らず、Postfix 側で待ち状態になることを確認。
- `docker exec mailserver-postfix ls -l /var/spool/postfix/private/` に `auth` ソケットが存在せず、`main.cf` で `smtpd_sasl_*` が有効なままになっていた（Dovecot `service auth` を無効化済みのため不整合）。
- Roundcube の SMTP 接続先が `tls://postfix` となっており、証明書 CN (`dell-workstation.tail67811d.ts.net`) と一致しない。

**修正**:
1. Postfix テンプレートを更新 (`services/mailserver/config/postfix/main.cf.tmpl`):
   ```diff
   -smtpd_relay_restrictions = permit_mynetworks, permit_sasl_authenticated, defer_unauth_destination
   -smtpd_sasl_type = dovecot
   -smtpd_sasl_path = private/auth
   -smtpd_sasl_auth_enable = yes
   +smtpd_relay_restrictions = permit_mynetworks, defer_unauth_destination
   +smtpd_sasl_auth_enable = no
   ```
   → `docker compose -f services/mailserver/docker-compose.yml up -d --force-recreate postfix` で再生成。
2. Roundcube の SMTP ホストを証明書 CN に合わせる (`services/mailserver/docker-compose.yml:213-219`):
   ```diff
   - ROUNDCUBEMAIL_SMTP_SERVER=tls://postfix
   + ROUNDCUBEMAIL_SMTP_SERVER=tls://dell-workstation.tail67811d.ts.net
   ```
   併せて `extra_hosts` の上書きを削除し、DNS 解決で Tailscale IP を利用。
   → `docker compose -f services/mailserver/docker-compose.yml up -d --force-recreate roundcube` で反映。

**検証**:
- `docker exec mailserver-roundcube openssl s_client -starttls smtp -connect dell-workstation.tail67811d.ts.net:587` で TLSv1.3 / CN 一致を確認。
- `docker exec mailserver-roundcube php -r '...fsockopen(\"postfix\",587...)'` で `220 mail.kuma8088.com ESMTP Postfix` バナーを受信。
- Roundcube UI からの送信操作でエラーが再発しないことを手動確認（ブラウザ操作）。

**補足**:
- Postfix がローカルドメイン宛てメールを `lmtp:unix:private/dovecot-lmtp` に配送しようとするとソケット不在でキュー滞留するため、別途 `virtual_transport` を TCP LMTP (例: `lmtp:inet:dovecot:2525`) へ移行する必要がある点を認識済み。

**結果**: Roundcube からの SMTP 接続が即時に確立され、送信時の `smtp error (-1)` が解消。

---

### 修正 #8: users ファイルのパーミッション修正
**問題**: UID 5000 で作成されたが、コンテナ内の vmail ユーザーは UID 1000

**調査結果**:
```bash
# ホスト側
-rw-------. 1 system-admin system-admin 187 Nov  3 13:38 config/dovecot/users

# コンテナ内
vmail:x:1000:1000::/srv/vmail:/bin/sh
```

**修正**:
```bash
chmod 644 config/dovecot/users
```

**修正後**:
```bash
-rw-r--r--. 1 system-admin system-admin 187 Nov  3 13:38 config/dovecot/users
```

---

### 修正 #9: パスワードハッシュの再生成
**問題**: 正しいパスワードは `testtest` だった (`test1234` ではない)

**ハッシュ生成コマンド**:
```bash
docker run --rm dovecot/dovecot:2.3.21 doveadm pw -s SHA512-CRYPT -p testtest
```

**生成されたハッシュ**:
```
{SHA512-CRYPT}$6$AsaBrRHlvZiiCa1q$PML7EaM2PvWhUOXXb2VwLlYnjBEbfqQcnd4zmuKjPlzmng7Q5M774u.JAFF4NFT1YYvkroIOG5FHnZSODGK5J1
```

**更新後の users ファイル** (`config/dovecot/users`):
```
test@kuma8088.com:{SHA512-CRYPT}$6$AsaBrRHlvZiiCa1q$PML7EaM2PvWhUOXXb2VwLlYnjBEbfqQcnd4zmuKjPlzmng7Q5M774u.JAFF4NFT1YYvkroIOG5FHnZSODGK5J1:5000:5000::/var/mail/vhosts/kuma8088.com/test::
```

---

## ✅ 検証結果

### IMAP 直接接続テスト (成功)
```bash
timeout 5 openssl s_client -connect 172.20.0.30:993 -quiet <<EOF
a1 LOGIN test@kuma8088.com testtest
a2 LOGOUT
EOF
```

**出力**:
```
* OK [CAPABILITY IMAP4rev1 SASL-IR LOGIN-REFERRALS ID ENABLE IDLE LITERAL+ AUTH=PLAIN AUTH=LOGIN] Dovecot ready.
a1 OK [CAPABILITY IMAP4rev1 ...] Logged in
* BYE Logging out
a2 OK Logout completed (0.001 + 0.000 + 0.003 secs).
```

✅ **IMAP 認証は成功している**

---

## ✅ 直近の確認結果

---

## 📊 現在の設定状態

### Dovecot サービスステータス
```
name: imap-login
process_count: 0
process_avail: 0
process_limit: 100
client_limit: 1
listening: y
process_total: 0
```

### Dovecot 認証設定
```conf
auth_mechanisms = plain login
passdb {
    driver = passwd-file
    args = scheme=SHA512-CRYPT username_format=%u /etc/dovecot/users
}

userdb {
    driver = static
    args = uid=vmail gid=vmail home=/var/mail/vhosts/%d/%n
}
```

### Docker Compose ネットワーク
```yaml
networks:
  mailserver_network:
    driver: bridge
    ipam:
      config:
        - subnet: 172.20.0.0/24

services:
  dovecot:
    networks:
      mailserver_network:
        ipv4_address: 172.20.0.30

  roundcube:
    networks:
      mailserver_network:
        ipv4_address: 172.20.0.40
```

---

## 🔧 次のデバッグステップ (保留中)

### 1. Roundcube ログの確認
```bash
docker logs mailserver-roundcube --tail 50
docker exec mailserver-roundcube cat /var/log/roundcube/errors.log
```

### 2. ネットワーク接続テスト
```bash
# Roundcube コンテナから Dovecot への接続確認
docker exec mailserver-roundcube ping -c 3 dovecot
docker exec mailserver-roundcube nc -zv dovecot 993
```

### 3. Dovecot 詳細ログの有効化
`dovecot.conf` に追加:
```conf
log_path = /var/log/dovecot.log
info_log_path = /var/log/dovecot-info.log
debug_log_path = /var/log/dovecot-debug.log
auth_verbose = yes
auth_debug = yes
mail_debug = yes
```

### 4. Roundcube デバッグモードの有効化
```bash
docker exec mailserver-roundcube sh -c "echo \$ROUNDCUBEMAIL_IMAP_CONN_OPTIONS"
```

---

## 📁 変更されたファイル

1. `/opt/onprem-infra-system/project-root-infra/services/mailserver/docker-compose.yml`
   - 109行目: Dovecot command 追加
   - 121行目: users ファイルマウント追加
   - 215-216行目: Roundcube SSL 検証スキップ追加

2. `/opt/onprem-infra-system/project-root-infra/services/mailserver/config/dovecot/dovecot.conf`
   - 9-10行目: SSL 証明書パス修正
   - 11行目: `ssl_min_protocol` に変更
   - 37行目: IMAP ポート構文修正
   - 56-63行目: Postfix SASL 無効化

3. `/opt/onprem-infra-system/project-root-infra/services/mailserver/config/dovecot/users`
   - パスワードハッシュを `testtest` 用に更新
   - パーミッションを 644 に変更

---

## 📝 学んだ教訓

1. **Docker コンテナの UID/GID 不一致**
   - ホスト側で作成したファイルの UID とコンテナ内のユーザー UID が異なると権限エラーが発生
   - 解決策: ファイルを読み取り可能 (644) にするか、コンテナ内の UID に合わせる

2. **環境変数の展開**
   - Dovecot 設定ファイルでは環境変数が自動展開されない
   - 絶対パスまたは既知のファイル名を使用する必要がある

3. **SSL 証明書のホスト名検証**
   - Docker ネットワーク内のホスト名 (`dovecot`) と証明書の CN (`dell-workstation.tail67811d.ts.net`) が一致しない場合、SSL 検証をスキップする必要がある

4. **IMAP 直接テストの重要性**
   - Roundcube 経由のテストだけでなく、`openssl s_client` を使った直接テストで認証層を分離してデバッグできる

---

## 🎯 現状まとめ

**動作している部分**:
- ✅ Dovecot コンテナ起動
- ✅ SSL/TLS 接続確立
- ✅ 認証サービス応答
- ✅ IMAP 直接ログイン成功 (`test@kuma8088.com` / `testtest`)

**動作していない部分**:
- ❌ Roundcube Webmail からの IMAP 接続
- ❌ ユーザーが Webmail にログインできない

**次の調査が必要**:
- Roundcube のログ確認
- Roundcube → Dovecot のネットワーク接続確認
- Roundcube の IMAP 接続設定の詳細確認

---

**レポート作成日**: 2025-11-03 18:30 JST
**作成者**: Claude Code DevOps Agent
