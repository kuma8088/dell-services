# メール不達時の調査ドキュメント

## 概要

特定のアドレスへのメールが届かない場合の体系的な調査手順を記載します。

## 前提条件

- **Dell Workstation**: Mailserver（Postfix, Dovecot, MariaDB）がDockerコンテナで稼働中
- **EC2**: MX Gateway（PostfixがDockerコンテナで稼働）
- メールフロー: 送信元 → EC2 (MX) → Dell (LMTP) → 受信箱

**重要:** Dell側、EC2側ともにPostfixはDockerコンテナで稼働しています。

## 調査フロー

```
1. Dell側: ユーザー/ドメイン存在確認
2. EC2側: メール受信確認（MXレコード）
3. EC2側: Dellへのリレー確認
4. Dell側: Postfix受信確認
5. Dell側: Dovecot配送確認
```

---

## 1. Dell側調査（基本確認）

### 1.1 ユーザーとドメインの存在確認

```bash
# 作業ディレクトリに移動
cd /opt/onprem-infra-system/project-root-infra/services/mailserver

# ドメイン存在確認
docker compose exec -T mariadb mysql -u root -p'TQhaCB7Gffg%F-DZ' mailserver_usermgmt \
  -e "SELECT id, name FROM domains WHERE name = 'toyota-phv.jp';"

# ユーザー存在確認（ドメインとJOIN）
docker compose exec -T mariadb mysql -u root -p'TQhaCB7Gffg%F-DZ' mailserver_usermgmt \
  -e "SELECT u.email, d.name as domain, u.enabled, u.maildir
      FROM users u
      JOIN domains d ON u.domain_id = d.id
      WHERE u.email = 'info@toyota-phv.jp';"
```

**期待結果:**
- ドメイン `toyota-phv.jp` が存在し、`id` が取得できる
- ユーザー `info@toyota-phv.jp` が存在し、`enabled = 1`
- `maildir` が正しく設定されている（例: `toyota-phv.jp/info/`）

**問題が見つかった場合:**
- ユーザーが存在しない → User Management APIで作成
- `enabled = 0` → User Management APIで有効化
- ドメインが存在しない → User Management APIでドメイン登録

---

### 1.2 Postfixログ確認（Dell側）

```bash
# 過去1時間のログから該当ドメインを検索
docker compose logs postfix --since 1h 2>&1 | grep -i "toyota-phv"

# より詳細な検索（全期間）
docker compose logs postfix 2>&1 | grep -A 5 -B 5 "info@toyota-phv.jp"

# リレーエラーを検索
docker compose logs postfix 2>&1 | grep -E "(reject|relay denied|relay=none)"
```

**期待結果:**
- `relay=local` または `relay=dovecot` の記録がある
- `status=sent` が記録されている

**問題パターン:**
- ログに記録なし → EC2からDellへメールが到達していない（次のセクションへ）
- `relay denied` → EC2が `relay_domains` に登録されていない
- `status=deferred` → 一時エラー（ディスク容量、権限など）
- `status=bounced` → 恒久エラー（ユーザー不在など）

---

### 1.3 Dovecotログ確認（Dell側）

```bash
# Dovecot LMTPログ確認
docker compose logs dovecot --since 1h 2>&1 | grep -i "toyota-phv"

# 配送成功ログ検索
docker compose logs dovecot 2>&1 | grep -E "(saved|msgid|lmtp)" | grep "toyota-phv"
```

**期待結果:**
- `saved mail to INBOX` のような配送成功ログがある
- メッセージIDが記録されている

**問題パターン:**
- ログに記録なし → Postfixから受け取っていない
- `Permission denied` → ファイルシステム権限問題
- `Quota exceeded` → 容量制限超過

---

## 2. EC2側調査（MX Gateway）

### 2.1 EC2へのSSH接続

```bash
# Dell WorkstationからEC2へSSH
# ポート番号は実際の設定に合わせてください（CLAUDE.mdの制約参照）
ssh -i ~/.ssh/your-key.pem ec2-user@<EC2-PUBLIC-IP> -p <SSH-PORT>
```

---

### 2.2 Postfixログ確認（EC2側）- 最優先確認項目

**注:** EC2のPostfixはDockerコンテナで稼働しています。まずこれらのコマンドで全体像を把握してください。

#### A. 過去1時間の全メール配送状況（推奨）

```bash
# 過去1時間の全メール配送ログ（from/to/status）
sudo docker logs mailserver-postfix --since 1h 2>&1 | grep -E "(from=|to=|status=)"

# ドメイン別に集計（どのドメインにメールが来ているか確認）
sudo docker logs mailserver-postfix --since 1h 2>&1 | grep "to=" | grep -oE "@[a-zA-Z0-9.-]+" | sort | uniq -c
```

#### B. 特定ドメインのログ検索

```bash
# 過去1時間から toyota-phv.jp のログを検索
sudo docker logs mailserver-postfix --since 1h 2>&1 | grep -i "toyota-phv"

# from/to/statusだけに絞って検索
sudo docker logs mailserver-postfix --since 1h 2>&1 | grep -E "(from=|to=|status=)" | grep -i "toyota-phv"

# より詳細な時刻指定
sudo docker logs mailserver-postfix --since "$(date -u -d '1 hour ago' '+%Y-%m-%dT%H:%M:%S')" 2>&1 | grep -i "toyota-phv"
```

#### C. 大量ログの確認（全期間）

```bash
# 最新10000行から検索
sudo docker logs mailserver-postfix --tail 10000 2>&1 | grep -E "(from=|to=|status=)" | grep -i "toyota-phv"

# 全ログを less で確認
sudo docker logs mailserver-postfix 2>&1 | less
```

**期待結果:**
- 外部からEC2へのメール受信ログがある: `from=<送信元>`, `to=<info@toyota-phv.jp>`
- EC2からDellへのリレーログがある: `relay=[100.64.x.x][25]`, `status=sent`

**問題パターン:**
- 受信ログなし → MXレコード問題、ファイアウォール、SendGrid設定
- リレーログなし → `relay_domains` 未設定
- `Connection refused` → Dell側Postfixが起動していない
- `Connection timed out` → Tailscaleネットワーク問題

---

### 2.3 Postfix設定確認（EC2側）

```bash
# relay_domains設定確認（どのドメインをリレーするか）
sudo docker exec mailserver-postfix postconf relay_domains

# relay_transport設定確認（リレー先の指定）★重要
sudo docker exec mailserver-postfix postconf relay_transport

# relayhost設定確認（代替設定）
sudo docker exec mailserver-postfix postconf relayhost

# 全リレー関連設定を表示
sudo docker exec mailserver-postfix postconf -n | grep -E "(relay|transport)"

# Tailscaleアドレス確認（ホストまたはコンテナ内）
tailscale status | grep dell
```

**期待結果:**
- `relay_domains` に `toyota-phv.jp` が含まれている
- `relay_transport = lmtp:[100.110.222.53]:2525` （Dellへのリレー設定）
- Tailscaleで Dell の IP が `100.110.222.53` として表示される

**重要:** `relay_transport`が設定されている場合、`relay_domains`に含まれる全ドメインは自動的にその宛先にリレーされます。`relayhost`や`transport_maps`は不要です。

**問題が見つかった場合:**
- `relay_domains` に未登録 → Terraform で追加（`services/mailserver/terraform/main.tf`）
- `relay_transport` が未設定または間違っている → Terraformで修正
- Tailscale接続なし → `tailscale status` で確認、必要なら再起動

---

### 2.4 EC2メール受信テスト

```bash
# EC2が外部からメールを受信できるか確認
# Dell Workstationから実行
telnet <EC2-PUBLIC-IP> 25

# Telnetセッションで以下を入力:
EHLO test.example.com
MAIL FROM:<test@example.com>
RCPT TO:<info@toyota-phv.jp>
DATA
Subject: Test
Test message
.
QUIT
```

**期待結果:**
- `250 2.1.0 Ok` が返る（MAIL FROM / RCPT TO）
- `250 2.0.0 Ok: queued` が返る（DATA送信後）

**問題パターン:**
- `554 Relay access denied` → `relay_domains` 未設定
- `Connection refused` → EC2のPort 25が閉じている
- タイムアウト → セキュリティグループでPort 25が許可されていない

---

## 3. ネットワーク診断

### 3.1 Tailscale接続確認（Dell側）

```bash
# Dell WorkstationでTailscale状態確認
sudo tailscale status

# EC2との疎通確認（Tailscale IP）
ping -c 4 100.64.x.x  # EC2のTailscale IP

# Port 25疎通確認（Dell→EC2）
nc -zv 100.64.x.x 25
```

---

### 3.2 EC2からDellへの疎通確認

```bash
# EC2でDellのTailscale IP確認
tailscale status | grep dell

# Port 25疎通確認（EC2→Dell）
nc -zv 100.64.y.y 25  # DellのTailscale IP

# 実際のSMTPテスト
telnet 100.64.y.y 25
```

---

## 4. トラブルシューティングチートシート

### 問題: メールがEC2に届いていない

**原因候補:**
- MXレコードが正しく設定されていない
- EC2のセキュリティグループでPort 25が許可されていない
- SendGridのInbound Parse設定が間違っている

**確認コマンド（Dell側）:**
```bash
# MXレコード確認
dig MX toyota-phv.jp

# EC2のPublic IP確認
# Terraform outputまたはAWS Consoleで確認
```

**確認コマンド（EC2側）:**
```bash
# Port 25リスン確認（ホスト側）
sudo ss -tlnp | grep :25

# Postfixコンテナが起動しているか確認
docker ps | grep postfix

# Docker Compose使用の場合
docker compose ps postfix

# ファイアウォール確認
sudo iptables -L -n | grep 25
```

---

### 問題: EC2に届いているがDellにリレーされない

**原因候補:**
- EC2の `relay_domains` に該当ドメインが未登録
- EC2の `relay_transport` 設定が間違っている
- Tailscale接続が切れている

**確認コマンド（EC2側）:**
```bash
# relay_domains確認
sudo docker exec mailserver-postfix postconf relay_domains | grep toyota-phv.jp

# relay_transport確認（重要）
sudo docker exec mailserver-postfix postconf relay_transport

# 全リレー設定確認
sudo docker exec mailserver-postfix postconf -n | grep -E "(relay|transport)"

# Tailscale接続確認
tailscale status | grep dell
ping -c 4 100.110.222.53  # DellのTailscale IP
```

**修正方法:**
```bash
# relay_domainsに追加（一時的、非推奨）
sudo docker exec mailserver-postfix postconf -e "relay_domains = $(sudo docker exec mailserver-postfix postconf -h relay_domains), toyota-phv.jp"
sudo docker restart mailserver-postfix

# relay_transportが未設定の場合（一時的）
sudo docker exec mailserver-postfix postconf -e "relay_transport = lmtp:[100.110.222.53]:2525"
sudo docker restart mailserver-postfix

# 恒久的にはTerraformで追加（推奨）:
# services/mailserver/terraform/main.tf の relay_domains に追加してterraform apply
```

---

### 問題: DellのPostfixに届いているが配送されない

**原因候補:**
- Dovecot LMTPが起動していない
- ユーザーのmaildirパーミッション問題
- ディスク容量不足

**確認コマンド（Dell側）:**
```bash
# Dovecotコンテナ状態確認
docker compose ps dovecot

# Dovecotログ確認
docker compose logs dovecot --tail 50

# ディスク容量確認
df -h /var/lib/docker/volumes/mailserver_maildata

# パーミッション確認
docker compose exec dovecot ls -la /var/mail/vmail/toyota-phv.jp/
```

**修正方法:**
```bash
# Dovecot再起動
docker compose restart dovecot

# パーミッション修正（必要なら）
docker compose exec dovecot chown -R vmail:vmail /var/mail/vmail/toyota-phv.jp/
```

---

### 問題: ユーザーが存在しない

**原因候補:**
- ドメインが User Management システムに登録されていない
- ユーザーが作成されていない
- ユーザーが無効化されている

**確認コマンド（Dell側）:**
```bash
# ドメイン確認
docker compose exec -T mariadb mysql -u root -p'TQhaCB7Gffg%F-DZ' mailserver_usermgmt \
  -e "SELECT * FROM domains WHERE name = 'toyota-phv.jp';"

# ユーザー確認
docker compose exec -T mariadb mysql -u root -p'TQhaCB7Gffg%F-DZ' mailserver_usermgmt \
  -e "SELECT u.email, u.enabled, d.name as domain
      FROM users u
      JOIN domains d ON u.domain_id = d.id
      WHERE u.email = 'info@toyota-phv.jp';"
```

**修正方法:**
```bash
# User Management APIでドメイン作成
curl -X POST http://172.20.0.70:5001/api/domains \
  -H "Content-Type: application/json" \
  -d '{"name": "toyota-phv.jp"}'

# User Management APIでユーザー作成
curl -X POST http://172.20.0.70:5001/api/users \
  -H "Content-Type: application/json" \
  -d '{
    "email": "info@toyota-phv.jp",
    "password": "SecurePassword123!",
    "domain": "toyota-phv.jp"
  }'
```

---

## 5. ログ分析のベストプラクティス

### 5.1 時系列でログを追跡

```bash
# 特定時刻のログ確認（Dell側）
docker compose logs postfix --since "2024-01-15T10:00:00" --until "2024-01-15T11:00:00" | grep toyota-phv

# 特定時刻のログ確認（EC2側）
docker logs --since "2024-01-15T10:00:00" --until "2024-01-15T11:00:00" <postfix-container-name> 2>&1 | grep toyota-phv

# Docker Compose使用の場合（EC2側）
docker compose logs postfix --since "2024-01-15T10:00:00" --until "2024-01-15T11:00:00" | grep toyota-phv
```

### 5.2 メッセージIDで追跡

```bash
# メッセージIDを特定（EC2側で受信時）
docker logs <postfix-container-name> 2>&1 | grep "toyota-phv" | grep "message-id"

# Docker Compose使用の場合
docker compose logs postfix | grep "toyota-phv" | grep "message-id"

# そのメッセージIDをDell側で検索
docker compose logs postfix | grep "<message-id>"
docker compose logs dovecot | grep "<message-id>"
```

### 5.3 リアルタイムログ監視

```bash
# Dell側でリアルタイム監視
docker compose logs -f postfix dovecot

# EC2側でリアルタイム監視
docker logs -f <postfix-container-name>

# Docker Compose使用の場合（EC2側）
docker compose logs -f postfix
```

---

## 6. よくある質問

### Q1: メールが数時間遅れて届く

**原因:** EC2またはDellのPostfixがキューで再試行中

**確認:**
```bash
# Dell側のキュー確認
docker compose exec postfix postqueue -p

# EC2側のキュー確認
docker exec <postfix-container-name> postqueue -p

# Docker Compose使用の場合（EC2側）
docker compose exec postfix postqueue -p
```

**対処:**
```bash
# キューを強制フラッシュ（Dell側）
docker compose exec postfix postqueue -f

# キューを強制フラッシュ（EC2側）
docker exec <postfix-container-name> postqueue -f

# Docker Compose使用の場合（EC2側）
docker compose exec postfix postqueue -f
```

---

### Q2: 特定のドメインだけ届かない

**原因:** `relay_domains` または `transport` の設定漏れ

**対処:** EC2側の設定を確認し、Terraformで追加

---

### Q3: SPF/DKIM/DMARCエラーで届かない

**原因:** SendGrid経由送信時の認証設定不足

**確認:** SendGridのDNS設定とDMARC policyを確認

**注:** 本ドキュメントはメール受信に関する調査手順です。送信認証の問題は別ドキュメント参照。

---

## 7. エスカレーション基準

以下の場合はシステム管理者に報告:

- Dell/EC2ともにハードウェア/ネットワーク障害
- Tailscaleサービス障害
- SendGrid側の障害（受信機能停止）
- データベース破損
- ディスク容量が残り10%未満

---

## 8. 参考ドキュメント

- **メインガイド:** [docs/application/mailserver/README.md](../README.md)
- **トラブルシューティング:** [services/mailserver/troubleshoot/README.md](../../../../services/mailserver/troubleshoot/README.md)
- **Terraform設定:** [services/mailserver/terraform/](../../../../services/mailserver/terraform/)
- **User Management:** [docs/application/mailserver/usermgmt/](../usermgmt/)

---

## 9. 更新履歴

| 日付 | 変更内容 | 担当者 |
|------|---------|--------|
| 2025-01-06 | 初版作成 | Claude Code |
