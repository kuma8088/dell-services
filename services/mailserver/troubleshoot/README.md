# Mailserver Troubleshooting Guide

メールサーバーのトラブルシューティングドキュメント集

---

## 📚 トラブルシューティングドキュメント一覧

### 認証・ログイン問題

| ドキュメント | 日付 | 問題 | 解決策 |
|------------|------|------|--------|
| [MAIL_CLIENT_LOGIN_FAILURE_2025-11-04.md](MAIL_CLIENT_LOGIN_FAILURE_2025-11-04.md) | 2025-11-04 | メールクライアントログイン失敗 | Dovecot SQL認証設定修正（認証情報混同） |
| [DOVECOT_TROUBLESHOOTING_2025-11-03.md](DOVECOT_TROUBLESHOOTING_2025-11-03.md) | 2025-11-03 | Dovecot認証エラー | 設定検証手順 |

### メール受信問題

| ドキュメント | 日付 | 問題 | 解決策 |
|------------|------|------|--------|
| [GMAILRECIEVEISSUE.md](GMAILRECIEVEISSUE.md) | - | Gmail受信問題 | 受信フロー調査 |
| [INBOUND_MAIL_FAILURE_2025-11-03.md](INBOUND_MAIL_FAILURE_2025-11-03.md) | 2025-11-03 | インバウンドメール失敗 | EC2 MX → Dell LMTP経路確認 |

### EC2 MX Gateway問題

| ドキュメント | 日付 | 問題 | 解決策 |
|------------|------|------|--------|
| [EC2_MX_DIAGNOSTIC_COMMANDS.md](EC2_MX_DIAGNOSTIC_COMMANDS.md) | - | EC2診断コマンド集 | relay_domains, transport, ログ確認 |
| [EC2_MAIL_PROTOCOL_ISSUE_2025-11-04.md](EC2_MAIL_PROTOCOL_ISSUE_2025-11-04.md) | 2025-11-04 | EC2メールプロトコル問題 | Relay access denied対応 |

### SMTP接続問題

| ドキュメント | 日付 | 問題 | 解決策 |
|------------|------|------|--------|
| [SMTP_CONNECTION_FAILURE_2025-11-03.md](SMTP_CONNECTION_FAILURE_2025-11-03.md) | 2025-11-03 | SMTP接続失敗 | Postfix設定確認 |

---

## 🔍 問題別クイックリファレンス

### メールクライアントでログインできない

**症状**: Thunderbird/Outlookで「パスワードが一致しない」エラー

**確認手順**:
1. [MAIL_CLIENT_LOGIN_FAILURE_2025-11-04.md](MAIL_CLIENT_LOGIN_FAILURE_2025-11-04.md) を参照
2. Dovecot SQL認証設定確認
3. データベース接続テスト

**よくある原因**:
- Dovecot SQL認証設定の認証情報混同（`MYSQL_PASSWORD` vs `USERMGMT_DB_PASSWORD`）
- uid/gid不一致（5000 vs 1000）

---

### 特定ドメインのメールが受信できない

**症状**: 送信はできるが受信ができない、Gmail等から拒否される

**確認手順**:
1. [EC2_MX_DIAGNOSTIC_COMMANDS.md](EC2_MX_DIAGNOSTIC_COMMANDS.md) を参照
2. EC2の`relay_domains`確認
3. `/etc/postfix/transport`確認

**よくある原因**:
- EC2の`relay_domains`に新ドメインが未登録
- `transport.db`が存在しない
- "Relay access denied" エラー

**解決方法**:
```bash
# relay_domains追加
docker exec mailserver-postfix postconf -e "relay_domains = existing.com, newdomain.com"

# transport追加
docker exec mailserver-postfix sh -c 'echo "newdomain.com smtp:[100.110.222.53]:2525" >> /etc/postfix/transport'
docker exec mailserver-postfix postmap /etc/postfix/transport
docker exec mailserver-postfix postfix reload
```

---

### Dovecot認証エラー

**症状**: IMAP/POP3ログイン時に認証失敗

**確認手順**:
1. [DOVECOT_TROUBLESHOOTING_2025-11-03.md](DOVECOT_TROUBLESHOOTING_2025-11-03.md) を参照
2. SQL認証設定確認
3. データベースユーザー存在確認

**デバッグコマンド**:
```bash
# Dovecotログ確認
docker compose logs dovecot | grep -i "sql\|auth"

# データベース接続テスト
docker exec -it mailserver-usermgmt python -c "
import pymysql
conn = pymysql.connect(host='mailserver-mariadb', user='usermgmt',
                       password='SecureMailUserMgmt2024!', database='mailserver_usermgmt')
print('✅ Connection successful')
"

# ユーザー存在確認
docker exec mailserver-mariadb mysql -uusermgmt -p'SecureMailUserMgmt2024!' mailserver_usermgmt \
  -e "SELECT email, enabled FROM users WHERE email='user@example.com';"
```

---

### SMTP送信失敗

**症状**: メール送信時にエラー

**確認手順**:
1. [SMTP_CONNECTION_FAILURE_2025-11-03.md](SMTP_CONNECTION_FAILURE_2025-11-03.md) を参照
2. Postfix設定確認
3. SendGrid SASL認証確認

**デバッグコマンド**:
```bash
# Postfixログ確認
docker compose logs postfix | tail -50

# メールキュー確認
docker exec mailserver-postfix mailq

# 設定確認
docker exec mailserver-postfix postconf | grep smtp
```

---

## 🚨 緊急対応フロー

### 1. メール受信が完全停止している場合

```bash
# 1. Dell側確認
cd /opt/onprem-infra-system/project-root-infra/services/mailserver
docker compose ps
docker compose logs dovecot postfix | tail -100

# 2. EC2側確認（EC2にSSH）
docker logs mailserver-postfix 2>&1 | tail -100
docker exec mailserver-postfix postconf relay_domains
docker exec mailserver-postfix mailq

# 3. Tailscale VPN確認
tailscale status
ping 100.110.222.53  # Dell側
ping 100.70.131.116  # EC2側
```

### 2. 認証が完全停止している場合

```bash
# 1. Dovecot再起動
docker compose restart dovecot

# 2. MariaDB接続確認
docker compose logs mariadb | tail -50

# 3. SQL認証設定確認
docker exec mailserver-dovecot cat /etc/dovecot/custom/dovecot-sql.conf.ext

# 4. テストログイン
docker compose logs dovecot -f  # 別ターミナルで監視
# メールクライアントでログイン試行
```

### 3. ロールバック手順

Phase 11マイグレーション問題の場合:
- [docs/application/mailserver/usermgmt/ROLLBACK.md](../../../docs/application/mailserver/usermgmt/ROLLBACK.md) を参照

---

## 📊 診断コマンド一覧

### Dell側（Docker Compose環境）

```bash
cd /opt/onprem-infra-system/project-root-infra/services/mailserver

# コンテナ状態
docker compose ps

# ログ確認
docker compose logs <service-name> -f

# サービス再起動
docker compose restart <service-name>

# 設定確認
docker exec mailserver-dovecot doveconf -n
docker exec mailserver-postfix postconf -n
```

### EC2側（Docker環境）

```bash
# コンテナ名: mailserver-postfix

# relay_domains確認
docker exec mailserver-postfix postconf relay_domains

# transport確認
docker exec mailserver-postfix cat /etc/postfix/transport
docker exec mailserver-postfix postmap -q "domain.com" /etc/postfix/transport

# メールキュー
docker exec mailserver-postfix mailq

# ログ（Relay access denied等）
docker logs mailserver-postfix 2>&1 | grep -i "relay\|reject"
```

詳細は [EC2_MX_DIAGNOSTIC_COMMANDS.md](EC2_MX_DIAGNOSTIC_COMMANDS.md) を参照

---

## 🔗 関連ドキュメント

- **アーキテクチャ**: [docs/application/mailserver/README.md](../../../docs/application/mailserver/README.md)
- **User Management**: [docs/application/mailserver/usermgmt/README.md](../../../docs/application/mailserver/usermgmt/README.md)
- **開発ガイド**: [docs/application/mailserver/usermgmt/DEVELOPMENT.md](../../../docs/application/mailserver/usermgmt/DEVELOPMENT.md)
- **ロールバック**: [docs/application/mailserver/usermgmt/ROLLBACK.md](../../../docs/application/mailserver/usermgmt/ROLLBACK.md)
- **EC2自動同期仕様**: [docs/application/mailserver/06_EC2_Relay_Domains_Auto_Sync_Spec.md](../../../docs/application/mailserver/06_EC2_Relay_Domains_Auto_Sync_Spec.md)

---

## 📝 新しい問題を記録する際のガイドライン

### ファイル命名規則

```
<COMPONENT>_<ISSUE_TYPE>_<DATE>.md
例: DOVECOT_AUTH_FAILURE_2025-11-06.md
```

### ドキュメントテンプレート

```markdown
# [Component] [Issue Type]

**日付**: YYYY-MM-DD
**影響範囲**: [メール受信/送信/認証/etc]
**重要度**: [Critical/High/Medium/Low]

## 問題の概要

[問題の簡潔な説明]

## 症状

- [具体的な症状1]
- [具体的な症状2]

## 原因

[根本原因の特定]

## 解決方法

[実施した対処手順]

## 再発防止策

[今後の予防策]

## 関連ドキュメント

- [関連する他のトラブルシューティングドキュメント]
```

---

**最終更新**: 2025-11-06
**メンテナー**: system-admin
