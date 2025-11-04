# メールクライアントログイン失敗 - TLS Cipher不一致 - 2025-11-04

## 問題の概要

**症状**: macOS Mail、iOS Mail等の現代的なメールクライアントがDovecot IMAPサーバーにログインできない

**発生日時**: 2025-11-04

**エラーメッセージ**:
```
SSL_accept() failed: error:1417A0C1:SSL routines:tls_post_process_client_hello:no shared cipher
```

## 根本原因

**TLS Cipher Suite の互換性不足**

### 問題の構造

1. **Dovecot設定 (誤り)**:
   ```conf
   ssl_cipher_list = ECDHE-RSA-AES128-GCM-SHA256:ECDHE-RSA-AES256-GCM-SHA384
   ```
   - TLS 1.2の2種類のみ対応
   - ECDSA variant、ChaCha20-Poly1305 未対応
   - 現代的なメールクライアント (macOS Mail, iOS Mail, Android Gmail) と互換性なし

2. **ログに記録されていた接続パターン**:
   - ✅ 成功: `172.20.0.40` (Roundcube) → TLS handshake 成功
   - ❌ 失敗: `100.117.186.84` (Tailscale VPN経由のメールクライアント) → TLS handshake 失敗

3. **TLS handshake 失敗の結果**:
   - メールクライアントが接続を確立できない
   - ログに `no auth attempts in 0 secs` が記録される
   - ユーザーは「サーバーに接続できません」エラーを見る

## 解決方法

### 修正内容

Dovecot設定ファイルで暗号化スイートを拡張:

**修正前（誤り）**:
```conf
ssl_cipher_list = ECDHE-RSA-AES128-GCM-SHA256:ECDHE-RSA-AES256-GCM-SHA384
```

**修正後（正しい）**:
```conf
# 最新メールクライアント対応の暗号化スイート (TLS 1.2/1.3互換)
ssl_cipher_list = ECDHE-ECDSA-AES128-GCM-SHA256:ECDHE-RSA-AES128-GCM-SHA256:ECDHE-ECDSA-AES256-GCM-SHA384:ECDHE-RSA-AES256-GCM-SHA384:ECDHE-ECDSA-CHACHA20-POLY1305:ECDHE-RSA-CHACHA20-POLY1305:DHE-RSA-AES128-GCM-SHA256:DHE-RSA-AES256-GCM-SHA384
ssl_prefer_server_ciphers = yes
```

**追加された暗号化スイート**:
- ECDHE-ECDSA variants (楕円曲線暗号 ECDSA)
- ChaCha20-Poly1305 (モバイル端末最適化)
- DHE-RSA variants (後方互換性)

### 実行コマンド

```bash
# 1. 設定ファイル編集
vi /opt/onprem-infra-system/project-root-infra/services/mailserver/config/dovecot/dovecot.conf

# 2. 設定変更を反映
docker restart mailserver-dovecot

# 3. 設定確認
docker exec mailserver-dovecot doveconf -c /etc/dovecot/custom/dovecot.conf | grep ssl_cipher_list
```

## 2025-11-04 対応サマリ

- Postfix と Dovecot で `postfix_spool` ボリュームを共有し、`/var/spool/postfix/private/auth` ソケットを共用して submission ポートで SASL 認証を利用可能にした。
- Postfix エントリポイントで `smtpd_relay_restrictions=permit_mynetworks,permit_sasl_authenticated,defer_unauth_destination`、`smtpd_sasl_type=dovecot`、`smtpd_sasl_path=private/auth` を自動設定し、TLS を `encrypt` 強制に変更。
- Dovecot `service auth` を有効化し、ソケットを 0666 パーミッションで公開して Postfix から参照できるようにした。
- `rsyslogd` を起動し、`services/mailserver/logs/postfix/mail.log` 等に SMTP ログが保存されるよう調整（重複配送の検証に利用）。
- 上記の結果、macOS Mail からの送受信が成功し、Gmail 側での重複受信も解消。

### 動作確認

```bash
# リアルタイムログ監視
docker exec mailserver-dovecot tail -f /var/log/dovecot-info.log

# 成功時のログ例:
# imap-login: Info: Login: user=<test@kuma8088.com>, method=PLAIN, rip=100.117.186.84, lip=172.20.0.30, mpid=..., TLS, session=<...>
```

## 影響ファイルと修正箇所

### 修正完了ファイル ✅

**ファイル**: `services/mailserver/config/dovecot/dovecot.conf`

**修正箇所**: 行23-25

**修正内容**:
```conf
# SSL/TLS設定
ssl = required
ssl_cert = </var/lib/tailscale/certs/tls.crt
ssl_key = </var/lib/tailscale/certs/tls.key
ssl_min_protocol = TLSv1.2
# 最新メールクライアント対応の暗号化スイート (TLS 1.2/1.3互換)
ssl_cipher_list = ECDHE-ECDSA-AES128-GCM-SHA256:ECDHE-RSA-AES128-GCM-SHA256:ECDHE-ECDSA-AES256-GCM-SHA384:ECDHE-RSA-AES256-GCM-SHA384:ECDHE-ECDSA-CHACHA20-POLY1305:ECDHE-RSA-CHACHA20-POLY1305:DHE-RSA-AES128-GCM-SHA256:DHE-RSA-AES256-GCM-SHA384
ssl_prefer_server_ciphers = yes
```

## 付随的な改善: ログ設定の有効化

### 問題

ログインエラーがファイルに記録されず、トラブルシューティングが困難だった。

### 解決

Dovecotのファイルログを有効化:

**追加設定** (`dovecot.conf` 行4-13):
```conf
# ログ設定
log_path = /var/log/dovecot.log
info_log_path = /var/log/dovecot-info.log
debug_log_path = /var/log/dovecot-debug.log
log_timestamp = "%Y-%m-%d %H:%M:%S "
auth_verbose = yes
auth_debug = yes
auth_debug_passwords = no
mail_debug = no
verbose_ssl = yes
```

**効果**:
- 認証エラーが詳細に記録される
- TLS handshake エラーが可視化される
- ログファイルパス: `services/mailserver/logs/dovecot/`

## メールクライアント設定ガイド

### macOS Mail / iOS Mail 推奨設定

**重要**: **必ずTailscaleホスト名を使用** (IPアドレス不可)

**受信サーバー (IMAP)**:
```
ホスト名: dell-workstation.tail67811d.ts.net
ポート: 993
暗号化: SSL/TLS
認証: パスワード
ユーザー名: test@kuma8088.com
```

**送信サーバー (SMTP)**:
```
ホスト名: dell-workstation.tail67811d.ts.net
ポート: 587
暗号化: STARTTLS
認証: パスワード
ユーザー名: test@kuma8088.com
```

**詳細設定**:
- IMAPパスの接頭辞: **空** (Maildir標準設定)
- TLS証明書: 自動検出 (初回接続時に承認が必要)

### TLS証明書について

**証明書情報**:
- CN: `dell-workstation.tail67811d.ts.net`
- SAN: `DNS:dell-workstation.tail67811d.ts.net`
- 発行者: Let's Encrypt (E8)
- 有効期限: 2026年1月31日

**「TLS証明書なし」警告の対処**:
1. ホスト名をIPアドレスではなく `dell-workstation.tail67811d.ts.net` に設定
2. 初回接続時に証明書の詳細を確認し「信頼する」をクリック
3. Tailscale VPN接続を確認

## 設計上の学び

### 1. TLS Cipher Suite の重要性

**教訓**: メールクライアントの多様性に対応するため、十分な暗号化スイートを設定する

**推奨設定**:
| 暗号化スイート | 用途 |
|--------------|------|
| ECDHE-ECDSA | 最新のmacOS/iOS (楕円曲線暗号) |
| ECDHE-RSA | 標準的なクライアント (RSA鍵交換) |
| ChaCha20-Poly1305 | モバイル端末最適化 (ARM CPU) |
| DHE-RSA | 後方互換性 (古いクライアント) |

### 2. ログ設定の必要性

**教訓**: 問題発生時の調査を迅速化するため、詳細なログを有効にする

**推奨ログ設定**:
```conf
auth_verbose = yes      # 認証試行の記録
auth_debug = yes        # 詳細な認証デバッグ
verbose_ssl = yes       # TLS handshake の詳細
```

### 3. アーキテクチャ理解の重要性

**教訓**: EC2はメールクライアントと直接接続しない

**正しいアーキテクチャ**:
- **メールクライアント** → Tailscale VPN → **Dell WorkStation Dovecot** (IMAP/POP3/SMTP)
- **外部からのメール受信** → Internet → **EC2 MX Gateway** (ポート25) → Tailscale VPN → **Dell WorkStation Dovecot** (LMTP 2525)

## 再発防止チェックリスト

### ✅ TLS Cipher Suite 確認

- [ ] TLS 1.2/1.3 対応の暗号化スイートが8種類以上設定されているか？
- [ ] ECDSA、RSA、ChaCha20-Poly1305 が含まれているか？
- [ ] `ssl_prefer_server_ciphers = yes` が設定されているか？

### ✅ ログ設定確認

- [ ] `auth_verbose = yes` が有効か？
- [ ] `verbose_ssl = yes` が有効か？
- [ ] ログファイルが `/var/log/dovecot*.log` に記録されているか？

### ✅ メールクライアント設定

- [ ] ホスト名として `dell-workstation.tail67811d.ts.net` を使用しているか？
- [ ] IPアドレス (`100.x.x.x`) で接続していないか？
- [ ] Tailscale VPN に接続しているか？

### ✅ 動作テスト

```bash
# 1. TLS cipher 設定確認
docker exec mailserver-dovecot doveconf | grep ssl_cipher_list

# 2. ログ監視
docker exec mailserver-dovecot tail -f /var/log/dovecot-info.log

# 3. メールクライアントから接続テスト

# 4. ログで成功確認
# 期待されるログ: "imap-login: Info: Login: user=<...>, TLS, session=<...>"
```

## 参考リンク

- **Dovecot SSL/TLS設定**: https://doc.dovecot.org/configuration_manual/dovecot_ssl_configuration/
- **Mozilla SSL Configuration Generator**: https://ssl-config.mozilla.org/
- **Tailscale証明書管理**: https://tailscale.com/kb/1153/enabling-https/
- **本プロジェクトメールサーバー手順書**: `Docs/application/mailserver/04_installation.md`
