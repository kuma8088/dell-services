# EC2メールサーバー - SMTP→LMTPプロトコル不一致問題 - 2025-11-04

## 問題の概要

**症状**: EC2メールサーバー (MX Gateway) からDell (Dovecot LMTP) への全メール配信が失敗

**発生日時**: 2025-11-04

**エラーメッセージ**:
```
status=bounced (host 100.110.222.53[100.110.222.53] refused to talk to me: 500 5.5.1 Unknown command)
```

## 根本原因

**SMTPプロトコル → LMTPプロトコルの不一致**

### 問題の構造

1. **EC2 Postfix設定 (誤り)**:
   ```yaml
   RELAYHOST=[100.110.222.53]:2525  # SMTPプロトコルでリレー
   ```
   - `RELAYHOST`環境変数はSMTP-to-SMTPリレー用
   - EC2 PostfixはSMTPプロトコルで100.110.222.53:2525に接続試行

2. **Dell Dovecot設定 (正しい)**:
   ```yaml
   ports:
     - "2525:2525"  # LMTP サービス
   ```
   - ポート2525はDovecot **LMTP**サービス
   - LMTPプロトコルでのみ通信可能

3. **プロトコル不一致の結果**:
   - PostfixがSMTP HELOコマンドを送信
   - Dovecot LMTPは「Unknown command」エラーを返す
   - 全メールが`dsn=5.5.1, status=bounced`で配信失敗

## 解決方法

### 修正内容

EC2 docker-compose.ymlで`RELAYHOST`を削除し、`relay_transport`を使用：

**修正前（誤り）**:
```yaml
environment:
  - RELAYHOST=[100.110.222.53]:2525  # ❌ SMTP プロトコル
```

**修正後（正しい）**:
```yaml
environment:
  - POSTFIX_relay_transport=lmtp:[100.110.222.53]:2525  # ✅ LMTP プロトコル
```

### 実行コマンド

EC2インスタンス上で実行：

```bash
# 1. バックアップ
sudo cp /opt/mailserver/docker-compose.yml /opt/mailserver/docker-compose.yml.backup

# 2. 設定変更
sudo sed -i 's/RELAYHOST=\[100\.110\.222\.53\]:2525/POSTFIX_relay_transport=lmtp:[100.110.222.53]:2525/' /opt/mailserver/docker-compose.yml

# 3. コンテナ再起動
cd /opt/mailserver
sudo docker-compose down
sudo docker-compose up -d

# 4. ログで確認
sudo docker logs mailserver-postfix --tail 20 | grep relay_transport
# 期待される出力: ‣ INFO  Applying custom postfix setting: relay_transport=lmtp:[100.110.222.53]:2525
```

### 動作確認

```bash
# テストメール送信
echo "Test email body" | sudo docker exec -i mailserver-postfix sendmail -f test@kuma8088.com test@kuma8088.com

# ログ確認
sudo docker logs mailserver-postfix --tail 50 | grep "status="
# 成功時の出力: status=sent (250 2.0.0 <test@kuma8088.com> ... Saved)
```

## 影響ファイルと修正箇所

### 1. EC2 実行中の設定 ✅ 修正完了

**ファイル**: `/opt/mailserver/docker-compose.yml` (EC2インスタンス上)

**修正内容**:
- `RELAYHOST=[100.110.222.53]:2525` → `POSTFIX_relay_transport=lmtp:[100.110.222.53]:2525`
- `relay_domains=kuma8088.com, m8088.com` → `relay_domains=kuma8088.com` (m8088.com削除)

### 2. Terraform user_data.sh ⚠️ 要修正

**ファイル**: `services/mailserver/terraform/user_data.sh`

**該当行**: 134行目付近

```bash
# 修正前
RELAYHOST=[100.110.222.53]:2525

# 修正後
POSTFIX_relay_transport=lmtp:[100.110.222.53]:2525
```

## 設計上の学び

### 1. プロトコル理解の重要性

**SMTP vs LMTP の違い**:
| プロトコル | 用途 | 接続形態 | Postfix環境変数 |
|-----------|------|---------|----------------|
| **SMTP** | MTA間メール転送 | Server-to-Server | `RELAYHOST` |
| **LMTP** | MTA→MDA最終配信 | Server-to-Local | `relay_transport=lmtp:` |

**重要**: Dovecot LMTPへの配信では`RELAYHOST`ではなく`relay_transport=lmtp:`を使用

### 2. 誤設定の検出方法

**ログパターンによる検出**:
```bash
# SMTP→LMTPプロトコル不一致のサイン
grep "500 5.5.1 Unknown command" /var/log/mail.log

# 正しいLMTP配信のサイン
grep "status=sent.*Saved" /var/log/mail.log
```

### 3. 設定の一貫性

**注意点**:
- Docker Compose環境変数 (`docker-compose.yml`)
- Terraform user_data (`user_data.sh`)

**全ての設定ファイルで同じプロトコル設定を保つこと**

## 再構築時のチェックリスト

EC2メールサーバーをゼロから構築する際の確認事項：

### ✅ プロトコル設定確認

- [ ] `RELAYHOST`環境変数を使用していないか？
- [ ] `POSTFIX_relay_transport=lmtp:[Dell-IP]:2525`を設定しているか？
- [ ] Dell側のポート2525がDovecot LMTPサービスであることを確認

### ✅ 設定ファイル一貫性

- [ ] `/opt/mailserver/docker-compose.yml` (EC2実行中)
- [ ] `services/mailserver/terraform/user_data.sh` (IaC定義)
- [ ] 全ファイルで同じプロトコル設定になっているか？

### ✅ ドメイン設定確認

- [ ] `relay_domains`に不要なドメイン（例: m8088.com）が含まれていないか？
- [ ] 有効なドメインのみ（例: kuma8088.com）が設定されているか？

### ✅ 動作テスト

```bash
# 1. プロトコル設定確認
sudo docker logs mailserver-postfix | grep "relay_transport=lmtp"

# 2. テストメール送信
echo "Test" | sudo docker exec -i mailserver-postfix sendmail -f test@domain.com target@domain.com

# 3. 成功ログ確認
sudo docker logs mailserver-postfix | grep "status=sent.*Saved"

# 4. Dell側LMTP配信確認
sudo docker logs mailserver-dovecot | grep "saved mail"
```

## 参考リンク

- **Postfix LMTP Transport**: http://www.postfix.org/LMTP_README.html
- **Dovecot LMTP**: https://doc.dovecot.org/configuration_manual/protocols/lmtp_server/
- **本プロジェクトEC2手順書**: `Docs/application/mailserver/04_EC2Server.md`
