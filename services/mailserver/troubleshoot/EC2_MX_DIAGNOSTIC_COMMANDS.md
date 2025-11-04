# EC2 MXゲートウェイ診断コマンド（必須5項目）

**対象**: `i-029e28809c430c815` (43.207.242.167)
**作成日**: 2025-11-04

---

## 🔴 必須確認（この順番で実行）

### 1. Dockerコンテナ稼働確認
```bash
sudo docker ps
```
**期待値**: `mailserver-postfix` が `Up` 状態

---

### 2. ポート25リスニング確認
```bash
sudo ss -tuln | grep ':25'
```
**期待値**: `0.0.0.0:25` でリスニング中

---

### 3. Postfixログ確認
```bash
sudo docker logs mailserver-postfix --tail 100
```
**確認ポイント**: `error`, `warning`, `reject`, `failed` が出ていないか

---

### 4. Tailscale接続確認
```bash
sudo tailscale status | grep 100.110.222.53
```
**期待値**: `100.110.222.53  dell-mailserver  ...  online`

---

### 5. Dell Dovecot LMTP接続テスト
```bash
timeout 5 nc -zv 100.110.222.53 2525
```
**期待値**: `Connection to 100.110.222.53 2525 port [tcp/*] succeeded!`

---

## 📋 問題があった場合の対処

### Docker起動していない → 起動
```bash
sudo docker start mailserver-postfix
```

### Port 25開いていない → Postfix起動
```bash
sudo docker exec mailserver-postfix postfix start
```

### Tailscale切断 → 再接続
```bash
sudo tailscale up
sudo docker restart mailserver-postfix
```

### LMTP接続失敗 → Dell側確認（別ターミナル）
```bash
# Dell WorkStationで実行
cd /opt/onprem-infra-system/project-root-infra/services/mailserver
docker compose ps dovecot
docker compose exec dovecot ss -tuln | grep 2525
```

### メールキュー滞留 → 強制再送
```bash
sudo docker exec mailserver-postfix postqueue -f
```

---

## 🔍 追加診断が必要な場合

### Postfix設定確認
```bash
sudo docker exec mailserver-postfix postconf relayhost transport_maps
sudo docker exec mailserver-postfix cat /etc/postfix/transport
```

### リアルタイムログ監視
```bash
sudo docker logs -f mailserver-postfix | grep --line-buffered "info@kuma8088.com"
```

### SMTP手動テスト
```bash
sudo docker exec -it mailserver-postfix telnet localhost 25
# EHLO test.local
# QUIT
```

---

**これで解決しない場合は結果を報告してください**
