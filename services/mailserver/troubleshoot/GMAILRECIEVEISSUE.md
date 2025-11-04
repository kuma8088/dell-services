# Gmail 受信不達対応メモ

## 背景
- Gmail から `info@kuma8088.com` 宛のメールが EC2 上の Postfix まで届かず、ログにも痕跡なし。
- EC2 側は Docker コンテナ `mailserver-postfix` が 25/587 を待ち受けている。初期状態では自己署名証明書 (`CN=localhost`) と STARTTLS 設定不足のため接続が拒否されていた。

## 対応手順

### 1. Tailscale 証明書発行（EC2 ホスト）
```bash
sudo mkdir -p /etc/ssl/tailscale
sudo tailscale cert \
  --cert-file /etc/ssl/tailscale/mailserver.crt \
  --key-file  /etc/ssl/tailscale/mailserver.key \
  mailserver-mx-ec2-1.tail67811d.ts.net
sudo chmod 600 /etc/ssl/tailscale/mailserver.key
```

### 2. コンテナへ証明書配置
```bash
sudo docker exec mailserver-postfix mkdir -p /etc/postfix/tls
sudo docker cp /etc/ssl/tailscale/mailserver.crt mailserver-postfix:/etc/postfix/tls/mailserver.crt
sudo docker cp /etc/ssl/tailscale/mailserver.key mailserver-postfix:/etc/postfix/tls/mailserver.key
sudo docker exec mailserver-postfix chmod 600 /etc/postfix/tls/mailserver.key
```

### 3. Postfix 設定更新（コンテナ内）
```bash
sudo docker exec mailserver-postfix sh -c "
  sed -i 's|^smtpd_tls_cert_file.*|smtpd_tls_cert_file = /etc/postfix/tls/mailserver.crt|' /etc/postfix/main.cf
  sed -i 's|^smtpd_tls_key_file.*|smtpd_tls_key_file = /etc/postfix/tls/mailserver.key|' /etc/postfix/main.cf
  sed -i 's|^smtpd_tls_security_level.*|smtpd_tls_security_level = encrypt|' /etc/postfix/main.cf
"
sudo docker exec mailserver-postfix sh -c "
  sed -i '/^submission inet n.*smtpd\$/,/^smtps/{s/^# \\?-o/-o/}' /etc/postfix/master.cf
  sed -i '/mua_/d' /etc/postfix/master.cf
"
sudo docker exec mailserver-postfix postfix reload
```

### 4. 動作確認
```bash
openssl s_client -connect 43.207.242.167:587 -starttls smtp \
  -servername mailserver-mx-ec2-1.tail67811d.ts.net
```
`subject=CN=mailserver-mx-ec2-1.tail67811d.ts.net` が表示されれば OK。  
その後 Gmail から再送 → `sudo docker logs mailserver-postfix --since 2m | grep "status="` で `status=sent` を確認。

## 補足
- 過去の失敗メールは `sudo docker exec mailserver-postfix postqueue -p` で確認、不要なら `postsuper -d ALL deferred` で削除。
- Dell 側 container (`mailserver-postfix`/`mailserver-dovecot`) のログは `services/mailserver/logs/` 以下に保存されている。

---

## SPF レコード不備による Gmail 受信失敗（2025-11-04）

### 問題
- Gmail から `info@kuma8088.com` 宛のメールが数時間経過しても届かず、バウンスメールも無し
- EC2 Postfix のログにも受信記録が全く残らない
- MX レコード、ポート 25 リスニング、Tailscale 接続は全て正常

### 原因
**SPF レコードに EC2 MX ゲートウェイ IP (43.207.242.167) が含まれていなかった**

#### 修正前の SPF レコード
```
v=spf1 +a:sv13071.xserver.jp +a:kuma8088.com +mx include:spf.sender.xserver.jp ~all
```
→ EC2 IP が認証されず、Gmail が配信を拒否

### 診断手順

#### 1. EC2 側の基本確認
```bash
# EC2 にSSH接続
ssh ec2-user@43.207.242.167

# Docker コンテナ稼働確認
sudo docker ps

# ポート 25 リスニング確認
sudo ss -tuln | grep ':25'

# Postfix ログ確認（Gmail からの接続記録無し）
sudo docker logs mailserver-postfix --tail 100
```

#### 2. DNS レコード確認
```bash
# MX レコード確認（正常）
dig MX kuma8088.com +short
# 結果: 10 mx.kuma8088.com.
dig A mx.kuma8088.com +short
# 結果: 43.207.242.167

# SPF レコード確認（EC2 IP 不在を発見）
dig TXT kuma8088.com +short | grep spf
# 結果: "v=spf1 +a:sv13071.xserver.jp +a:kuma8088.com +mx include:spf.sender.xserver.jp ~all"
```

#### 3. Tailscale 接続確認（正常）
```bash
# Dell WorkStation から実行
sudo tailscale status | grep 100.110.222.53
# 結果: 100.110.222.53  dell-mailserver  ...  online

# LMTP ポート接続テスト（正常）
timeout 5 nc -zv 100.110.222.53 2525
# 結果: Connection to 100.110.222.53 2525 port [tcp/*] succeeded!
```

### 対応

#### 1. SPF レコード修正（Route 53）
AWS Route 53 で kuma8088.com の TXT レコードを以下に変更:

```
v=spf1 ip4:43.207.242.167 +a:sv13071.xserver.jp +a:kuma8088.com +mx include:spf.sender.xserver.jp ~all
```

**変更点**: `ip4:43.207.242.167` を追加して EC2 MX ゲートウェイを明示的に認証

#### 2. DNS 伝播確認
```bash
# SPF レコード更新確認
dig TXT kuma8088.com +short | grep spf
# 結果: "v=spf1 ip4:43.207.242.167 +a:sv13071.xserver.jp +a:kuma8088.com +mx include:spf.sender.xserver.jp ~all"
```

DNS 伝播完了まで数分待機。

#### 3. Gmail 再送テスト
Gmail から `info@kuma8088.com` 宛にテストメール送信。

### 結果（成功）

EC2 Postfix ログに即座に受信記録が表示:

```
2025-11-04T11:13:31.661716+00:00 INFO postfix/cleanup[2922]: A1652E2357: message-id=<CAH2a+36mNcq0XT1GrQPnb3J3kR3fg3SwvoeGwxNvMqz97SktRw@mail.gmail.com>
2025-11-04T11:13:31.664091+00:00 INFO postfix/qmgr[2386]: A1652E2357: from=<naoya.iimura@gmail.com>, size=4017, nrcpt=1 (queue active)
2025-11-04T11:13:31.894747+00:00 INFO postfix/lmtp[2923]: A1652E2357: to=<info@kuma8088.com>, relay=100.110.222.53[100.110.222.53]:2525, delay=0.24, delays=0.01/0.01/0.12/0.1, dsn=2.0.0, status=sent (250 2.0.0 <info@kuma8088.com> Qh/gLNvfCWlGDQAAkzG9Ng Saved)
```

**配信時間**: 0.24 秒（正常）

### 教訓
- **外部メールサーバーを利用する場合、必ず SPF レコードに IP を追加する**
- EC2 MX ゲートウェイのように SMTP リレーを行うサーバーは SPF 認証が必須
- SPF 不備の場合、Gmail はサイレントに配信を拒否（バウンスメール無し）
- DNS 変更後は必ず `dig TXT` で伝播を確認する

### 参考資料
- SPF レコード構文: https://www.rfc-editor.org/rfc/rfc7208.html
- Route 53 TXT レコード設定: AWS コンソール → Route 53 → Hosted zones → kuma8088.com
