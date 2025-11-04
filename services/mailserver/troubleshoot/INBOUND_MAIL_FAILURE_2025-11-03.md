# Inbound Mail Receiving Failure - 2025-11-03

## 問題の概要

**症状**: メール送信は成功するが、送信したメールへの返信が受信できない

**発生日時**: 2025-11-03

**影響範囲**: すべてのドメイン (kuma8088.com, fx-trader-life.com, webmakeprofit.org, webmakesprofit.com)

## 調査プロセス

### 1. 初期調査: サービス状態確認

```bash
# ECS タスク状態確認
aws ecs describe-tasks --cluster mailserver-cluster \
  --tasks $(aws ecs list-tasks --cluster mailserver-cluster --service-name mailserver-mx-service --query 'taskArns[0]' --output text) \
  --query 'tasks[0].{Status:lastStatus,Health:healthStatus}'
```

**結果**: タスクは RUNNING/HEALTHY

```bash
# Docker コンテナログ確認
docker logs mailserver-postfix --tail 50 2>&1 | grep -E "(Error|Failed)"
docker logs mailserver-dovecot --tail 50 2>&1 | grep -E "(Error|Failed)"
```

**結果**: エラーなし、しかしメール受信のログも一切なし

### 2. メールフロー調査: Fargate → Dell

```bash
# Fargate Postfix ログ確認
aws logs tail /ecs/mailserver-mx --since 30m --format short | head -100
```

**結果**: MARKメッセージのみ、SMTPトラフィックなし → **Fargateにメールが届いていない**

### 3. DNS/ネットワーク調査

```bash
# MXレコード確認
dig +short kuma8088.com MX
# 出力:
# 20 _dc-mx.33c5c49abc97.kuma8088.com.
# 10 mx.kuma8088.com.

# MXホスト名のIPアドレス解決
dig +short mx.kuma8088.com A
# 出力: 43.207.242.167
```

```bash
# Fargate タスクの実際のPublic IP確認
TASK_ARN=$(aws ecs list-tasks --cluster mailserver-cluster --service-name mailserver-mx-service --query 'taskArns[0]' --output text)

# ENI ID取得
ENI_ID=$(aws ecs describe-tasks --cluster mailserver-cluster --tasks "$TASK_ARN" --query 'tasks[0].attachments[0].details[?name==`networkInterfaceId`].value' --output text)

# Public IP確認
aws ec2 describe-network-interfaces --network-interface-ids "$ENI_ID" --query 'NetworkInterfaces[0].Association.PublicIp' --output text
# 出力: 18.177.139.144
```

## 根本原因

**Elastic IP がFargateタスクに関連付けられていない（というより、関連付けられない）**

- **MX record `mx.kuma8088.com`**: `43.207.242.167` ← **Cloudflare で固定Elastic IPを指すよう設定済み**
- **現在のFargate Public IP**: `18.177.139.144` (タスク起動ごとに払い出される一時IP)
- **Elastic IP状態**: `eipalloc-04e838a5b1c9c7dde` (未割り当て)

**深掘り結果**:

1. Fargate タスクは `awsvpc` ネットワークモードで自動生成される ENI にのみ紐づく。
2. この ENI は AWS が管理しており、`aws ec2 associate-address --network-interface-id <ENI>` を実行すると **AuthFailure (Access denied) を返す**。  
   権限不足に見えるが、実際は **Fargate 管理 ENI には Elastic IP をアタッチできない** という制約によるもの。
3. したがってタスク再起動のたびに Public IP が変わり、MX レコードが指す固定 IP との整合性が取れずに SMTP が届かない。

## 修正方法

### オプション 1: （不可）Elastic IP を Fargate タスク ENI に直接関連付ける

**結論**: Fargate の `awsvpc` ENI はマネージドリソースであり、`AssociateAddress` API を実行すると `AuthFailure` が返る。IAM 権限を付与しても関連付けは拒否されるため、この選択肢は利用できない。

**失敗ログ例**:

```
An error occurred (AuthFailure) when calling the AssociateAddress operation:
You do not have permission to access the specified resource.
```

→ **設計として非対応**。他の選択肢を採用する必要がある。

### オプション 2: Elastic IP を Fargate タスクに割り当て (推奨)

**アーキテクチャ変更が必要**:

Fargateタスク自体は直接Elastic IPをサポートしていないため、以下のいずれかの方法が必要：

#### 2-A. Network Load Balancer (NLB) 経由

```
Internet
   │  (Elastic IP 43.207.242.167)
   ▼
Network Load Balancer (TCP/25 listener)
   ▼
Fargate タスク (mailserver-mx-service)
```

**メリット**:
- 固定IPアドレス (Elastic IP を NLB に割り当て)
- 高可用性 (複数タスクへの負荷分散)
- タスク再起動時もIP変更なし

**デメリット**:
- 追加コスト ($16-20/月)
- 構成が複雑化

#### 2-B. EC2 Proxy経由 (簡易版)

```
Internet → EC2 (Elastic IP) → Postfix Proxy → Fargate Task
```

**メリット**:
- 固定IPアドレス
- 低コスト (t4g.nano: ~$3/月)

**デメリット**:
- EC2インスタンス管理が必要
- Single Point of Failure

#### 2-C. AWS Global Accelerator (高可用性版)

```
Internet → Global Accelerator (静的IP x2) → NLB → Fargate Task
```

**メリット**:
- グローバル固定IP
- 最高の可用性とパフォーマンス

**デメリット**:
- 高コスト ($20-30/月)

### オプション 3: Cloudflare A レコードを自動更新（Dynamic DNS 方式）

**アーキテクチャ**:
```
Fargate Task 起動イベント → EventBridge → Lambda/Step Functions → Cloudflare API で Aレコード更新
```

**実装手順（例）**:

1. EventBridge で `ECS Task State Change (RUNNING)` をトリガー
2. Lambda で `DescribeTasks` → ENI → Public IP を取得
3. Cloudflare API (Zone DNS Records エンドポイント) に `PUT` し、`mx.kuma8088.com` の A レコードを新しい IP に更新（TTL 60s 推奨）
4. CloudWatch Logs や Slack/Webhook で更新結果を通知

**メリット**:
- 既存の Cloudflare 運用を継続しつつ自動化できる
- 月額コストは Lambda 実行料のみ
- Elastic IP を保持しないため AWS リソースが増えない

**デメリット**:
- DNS 伝播の遅延中は旧 IP に届く可能性がある
- Cloudflare API 呼び出し失敗時は手動更新が必要
- NLB 構成と比べると可用性（単一 IP 保障）はやや劣る

## 推奨ソリューション

- **可用性重視**: オプション 2-A (NLB ＋ Elastic IP)  
  追加コストは発生するが、MX レコードを固定 IP に揃えられ、DNS 更新遅延もない。
- **コスト最優先**: オプション 3 (Dynamic DNS)  
  既存リソースを流用でき、月額コストを抑えられる。ただし DNS 更新の仕組みを監視する必要がある。
- **構成簡素化**: オプション 4 (EC2 移行)  
  t4g.nano などの低コストインスタンスで固定 IP を直接割り当てられるが、OS パッチ適用など運用負荷が増える。

現状 Fargate に Elastic IP を直付けする選択肢は存在しないため、上記いずれかを選択して実装する。

---

### 1. Elastic IP 関連付け確認

```bash
# Elastic IP状態確認
aws ec2 describe-addresses --allocation-ids eipalloc-04e838a5b1c9c7dde \
  --query 'Addresses[0]' --output json

# 期待される出力: NetworkInterfaceIdが設定されていること
```

### 2. DNS確認

```bash
# MXレコード確認
dig +short mx.kuma8088.com A
# 例: 18.177.139.144 (Fargateタスク再起動後の最新Public IP)

# 複数のDNSサーバーから確認
dig @8.8.8.8 +short mx.kuma8088.com A  # Google DNS
dig @1.1.1.1 +short mx.kuma8088.com A  # Cloudflare DNS
# 例: 18.177.139.144 が返る
```

### 3. Cloudflare ログ確認

```bash
# Cloudflare Audit Log / Analytics で更新履歴を確認
# 例: CDN キャッシュログや DNS 変更ログを確認
```
### 3. SMTP接続テスト

```bash
# Fargate Postfixへの直接接続テスト
telnet 18.177.139.144 25
# 期待される応答:
# 220 mx.kuma8088.com ESMTP Postfix (Fargateの応答)

# ポート開放確認
nc -zv 18.177.139.144 25
# 期待される出力: Connection succeeded
```

### 3. テストメール送信と受信確認

```bash
# 外部メールアドレスからkuma8088.comアドレスにメール送信
# → Roundcube でメール受信を確認

# Fargate ログ確認
aws logs tail /ecs/mailserver-mx --since 5m --format short | grep "connect from"
# 期待される出力: 接続ログが表示される

# Dell Postfix ログ確認
docker logs mailserver-postfix --since 5m | grep "from=<"
# 期待される出力: Fargateからのリレーメールログ

# Dovecot LMTP配信ログ確認
docker logs mailserver-dovecot --since 5m | grep "saved mail"
# 期待される出力: メールボックスへの配信ログ
```

## 今後の改善計画

### Phase 1: 即座の対応 (完了)
- [x] DNS調査により根本原因特定
- [ ] Cloudflare でDNSレコード手動更新
- [ ] メール受信テスト

### Phase 2: 自動化実装 (推奨)
- [ ] Lambda関数作成 (ECSタスクIP取得 → Cloudflare API更新)
- [ ] EventBridge Rule作成 (ECSタスク状態変更イベント)
- [ ] IAM Role/Policy設定
- [ ] 動作テスト (タスク再起動 → DNS自動更新確認)

### Phase 3: 監視強化
- [ ] CloudWatch Alarm: MXレコードとFargate IPのミスマッチ検出
- [ ] SNS通知: DNS更新失敗時のアラート
- [ ] ヘルスチェック: 外部から定期的にSMTP接続テスト

## 関連ドキュメント

- `services/mailserver/README.md` - メールサーバーアーキテクチャ概要
- `Docs/application/mailserver/04_installation.md` - インストール手順
- `services/mailserver/terraform/` - インフラストラクチャ定義

## 学んだ教訓

1. **Fargate の動的IP割り当ての影響**:
   - タスク再起動時にPublic IPが変更される
   - DNS TTLを短く設定しても、手動更新は運用負荷が高い

2. **固定IPの必要性**:
   - MXレコードには固定IPが必須
   - Elastic IP、NLB、または Dynamic DNS による自動化が必要

3. **監視の重要性**:
   - DNS/IP ミスマッチを自動検出する仕組みが必要
   - メール受信失敗を早期に検知するヘルスチェック

4. **コスト vs 運用負荷のトレードオフ**:
   - NLB ($16-20/月) vs Dynamic DNS (ほぼ無料)
   - 自動化による運用負荷削減の価値

---

# EC2移行後のメール配信失敗 - 2025-11-04

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
echo "Test email body" | sudo docker exec -i mailserver-postfix sendmail -f test@kuma8088.com info@kuma8088.com

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

### 3. Fargate task definition ⚠️ 参考（非推奨アーキテクチャ）

**ファイル**: `services/mailserver/fargate-task-definition.json`

**該当行**: 38-39行目

**注意**: Fargateアーキテクチャは非推奨（Elastic IP制約のため）。参考のみ。

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
- Task Definition (`fargate-task-definition.json`)

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
