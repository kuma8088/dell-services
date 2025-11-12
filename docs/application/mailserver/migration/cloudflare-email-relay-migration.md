# Cloudflare Email Relay移行計画

**作成日**: 2025-11-12
**対象**: Mailserver受信用EC2廃止とCloudflareメールリレー実装
**ステータス**: 計画段階

---

## 目次

1. [現状分析](#1-現状分析)
2. [Cloudflare Email Routingの制限と課題](#2-cloudflare-email-routingの制限と課題)
3. [移行オプション](#3-移行オプション)
4. [推奨案の詳細手順](#4-推奨案の詳細手順)
5. [テスト手順](#5-テスト手順)
6. [ロールバック手順](#6-ロールバック手順)
7. [コスト比較](#7-コスト比較)

---

## 1. 現状分析

### 1.1 現在のメールフロー

**受信メールフロー（EC2経由）:**
```
Internet (Port 25)
  ↓
EC2 MX Gateway (Postfix in Docker) ← 受信専用
  ↓ Tailscale VPN (100.110.222.53:2525)
  ↓ LMTP Protocol
Dell WorkStation (Dovecot)
  ↓
Mailbox Storage
```

**送信メールフロー（SendGrid経由、EC2を経由しない）:**
```
Mail Client (Port 587)
  ↓
Dell Postfix ← 送信専用
  ↓
SendGrid Relay
  ↓
Internet
```

**重要:**
- ✅ **EC2 MX Gatewayは受信専用** - Port 25でメール受信のみ処理
- ✅ **送信はSendGrid経由** - Dell側のPostfixから直接SendGridへ送信（EC2不使用）
- ⚠️ **EC2廃止の影響は受信フローのみ** - 送信には一切影響しない

### 1.2 現在のEC2構成

**役割:** ⚠️ **受信専用MX Gateway** - Port 25でメール受信し、Dell側にLMTP転送

**リソース:**
- **インスタンスタイプ**: t4g.nano (ARM64)
- **月額コスト**: 約$3.50 (~¥525)
- **OS**: Amazon Linux 2023
- **主要コンポーネント**:
  - Postfix (Dockerコンテナ) - 受信専用
  - Tailscale VPN - Dell側への安全な接続
  - CloudWatch Logs Agent

**設定:**
- **開放ポート**: Port 25のみ（SMTP受信）
- **MXレコード**: `mail.kuma8088.com` (EIP割り当て)
- **relay_domains**: `kuma8088.com` - 受信許可ドメイン
- **LMTP転送先**: `100.110.222.53:2525` (Tailscale経由でDell Dovecotへ)

**送信機能:** ❌ なし - 送信はDell側のPostfix → SendGrid経由で処理

### 1.3 EC2廃止による期待効果

**メリット:**
- 月額コスト削減: ~¥525/月 → ¥0/月
- EC2管理作業の削減（セキュリティパッチ、監視）
- Tailscale VPN管理の簡素化

**デメリット:**
- 別のメールリレーソリューションが必要
- 移行時のダウンタイムリスク

---

## 2. Cloudflare Email Routingの制限と課題

### 2.1 調査結果（2025-11-12）

**Cloudflare Email Routingの機能:**
- ✅ 無料でメール受信可能
- ✅ 検証済みメールアドレスへの転送
- ✅ Cloudflare Workersでカスタムロジック実装可能
- ❌ **カスタムSMTP/LMTPサーバーへの直接転送は不可能**
- ❌ 送信メール機能なし（受信のみ）

**公式ドキュメントからの引用:**
> "Cloudflare does not process outbound email, and does not have an SMTP server."
> "Destination addresses must be full email addresses you want emails forwarded to, not SMTP/LMTP server endpoints."

### 2.2 技術的制約

**転送先の制限:**
- 検証済みの外部メールアドレス（Gmail、Outlook等）のみ対応
- カスタムSMTPサーバーへの直接転送は**不可能**
- LMTPプロトコルでの転送は**不可能**

**これが意味すること:**
- **現在のEC2 → Dell LMTP構成をCloudflare Email Routingで直接置き換えることはできない**

---

## 3. 移行オプション

### オプション1: Cloudflare Email Routing + Fetchmail方式 ⚠️ 非推奨

**構成:**
```
Internet
  ↓
Cloudflare Email Routing
  ↓
Gmail/Outlookアカウント
  ↓ IMAP/POP3
Dell側 Fetchmail/Getmail
  ↓
Dovecot LMTP
```

**メリット:**
- EC2コスト削減
- Cloudflare Email Routing無料

**デメリット:**
- ⚠️ 複雑性が大幅に増加
- ⚠️ メール遅延（外部メールボックス経由のため数分～数十分）
- ⚠️ 外部メールボックスのストレージ管理が必要
- ⚠️ Fetchmail/Getmail の定期実行設定が必要
- ⚠️ 障害ポイントが増加（Cloudflare + 外部メールボックス + Fetchmail）
- ⚠️ セキュリティリスク（外部メールボックスにメールが保存される）

**コスト:**
- Cloudflare Email Routing: 無料
- 外部メールボックス: Gmail無料枠またはGoogle Workspace ($6/月)

**推奨度**: ❌ **非推奨** - 複雑性とリスクがコスト削減効果を上回る

---

### オプション2: Dell側を直接インターネット公開 ⚠️ 要検証

**構成:**
```
Internet (Port 25)
  ↓
ISP Router (Port 25フォワーディング)
  ↓
Dell Firewall
  ↓
Dell Dovecot (LMTP: 2525)
```

**メリット:**
- ✅ シンプルな構成（EC2不要）
- ✅ コスト削減
- ✅ レイテンシ最小

**デメリット:**
- ⚠️ **ISPがポート25をブロックしている可能性が高い**
- ⚠️ Dell側を直接インターネットに公開（セキュリティリスク）
- ⚠️ 固定グローバルIPが必要
- ⚠️ 動的IPの場合、DDNSとMXレコード更新が必要
- ⚠️ ISPによるメール送信制限（Outbound Port 25 Block）

**事前確認が必要:**
```bash
# ISPのPort 25ブロックを確認
telnet smtp.gmail.com 25
# → 接続できない場合、ISPがブロックしている
```

**推奨度**: ⚠️ **要検証** - ISP制約により実現不可能な可能性が高い

---

### オプション3: EC2構成の最適化（現状維持） ✅ 推奨

**構成:**
- 現在のEC2 MX Gateway構成を維持
- インスタンスサイズとコスト最適化

**メリット:**
- ✅ 実績のある安定構成
- ✅ リスク最小
- ✅ 移行作業不要
- ✅ Tailscale VPNで安全なDell接続

**コスト最適化案:**
- **t4g.nano** (現行): ~$3.50/月 (~¥525/月)
- **Lightsail $3.50/月プラン**: 固定IP無料、予測可能なコスト
- **Savings Plans**: 1年契約で~30%削減可能

**推奨度**: ✅ **推奨** - 安定性とコストのバランスが最良

---

### オプション4: Amazon SES Receiving ✅ 代替案として有力

**構成:**
```
Internet (Port 25)
  ↓
Amazon SES (MX Record)
  ↓
S3 Bucket (メール保存)
  ↓
Lambda Function (S3トリガー)
  ↓ HTTPS API
Dell側 カスタムAPI Endpoint
  ↓
Dovecot LMTP
```

**メリット:**
- ✅ EC2不要（サーバーレス）
- ✅ AWS統合（S3、Lambda、CloudWatch）
- ✅ スケーラビリティ高い
- ✅ ログ・監視が容易

**デメリット:**
- ⚠️ Dell側にHTTPS APIエンドポイントの実装が必要
- ⚠️ 初期実装コストが高い
- ⚠️ メール処理遅延（S3 → Lambda → API → LMTP）
- ⚠️ SES Receivingはリージョン制限あり（us-east-1, us-west-2, eu-west-1のみ）

**コスト:**
- SES受信: $0.10/1000メール
- S3ストレージ: $0.023/GB/月
- Lambda実行: 無料枠内で収まる可能性高い
- **月額想定**: 100メール/日で ~$0.30/月 (~¥45/月)

**推奨度**: ⭐ **有力な代替案** - サーバーレスでコスト削減可能だが実装コスト高

---

### オプション5: Cloudflare Email Worker + カスタムAPI 🔧 技術的に可能だが複雑

**構成:**
```
Internet
  ↓
Cloudflare Email Routing
  ↓
Cloudflare Email Worker
  ↓ HTTPS API
Dell側 カスタムAPI Endpoint
  ↓
Dovecot LMTP
```

**メリット:**
- ✅ EC2不要
- ✅ Cloudflare Workersは無料枠あり（100,000リクエスト/日）
- ✅ エッジでのメール処理（低レイテンシ）

**デメリット:**
- ⚠️ Dell側にHTTPS APIエンドポイントの実装が必要
- ⚠️ Cloudflare Workerでメールパース・転送ロジック実装が必要
- ⚠️ メール本文のサイズ制限（Workers: 128MB メモリ制限）
- ⚠️ 保守が複雑（Workerコード + Dell APIエンドポイント）

**コスト:**
- Cloudflare Email Routing: 無料
- Cloudflare Workers: 無料枠内で収まる可能性高い
- **月額想定**: ~¥0/月（開発コストを除く）

**推奨度**: 🔧 **技術的に可能だが複雑** - 保守コストが高い

---

## 4. 推奨案の詳細手順

### 4.1 短期推奨: オプション3（EC2構成の最適化）

**実施理由:**
- 安定性が最優先
- 移行リスクを回避
- 月額¥525のコストは許容範囲内

**最適化手順:**

#### 4.1.1 Lightsail移行の検討

**Lightsail $3.50/月プランの利点:**
- 固定IP無料（EC2はEIP料金がかかる）
- データ転送1TB/月無料
- 予測可能な固定コスト

**移行手順（オプション）:**
1. Lightsailインスタンス作成（Amazon Linux 2023, 512MB RAM）
2. 現在のEC2のuser_data.shを実行
3. MXレコードをLightsail静的IPに変更
4. テスト後、EC2削除

#### 4.1.2 Savings Plans適用

**1年契約で30%削減:**
- t4g.nano: $3.50/月 → $2.45/月 (~¥368/月)

**設定手順:**
```bash
# AWS Console → Cost Management → Savings Plans
# → Compute Savings Plans → 1-Year, No Upfront
# → $2.45/月をコミット
```

---

### 4.2 中長期推奨: オプション4（Amazon SES Receiving）

**実施タイミング:** Phase 12（AWS移行）と同時実施

**実装手順概要:**

#### Phase 1: Dell側APIエンドポイント実装

**要件:**
- Flask/FastAPI でHTTPS APIエンドポイント実装
- 受信: メール全文（RFC822形式）
- 処理: Dovecot LMTPにプロキシ転送
- 認証: API Key認証

**実装例（概要）:**
```python
# Dell側: /opt/mailserver-api/app.py
from flask import Flask, request
import smtplib

app = Flask(__name__)

@app.route('/inbound-mail', methods=['POST'])
def receive_mail():
    # API Key認証
    if request.headers.get('X-API-Key') != os.getenv('API_KEY'):
        return 'Unauthorized', 401

    # メール全文取得
    email_raw = request.json['email_raw']

    # Dovecot LMTPに転送
    smtp = smtplib.SMTP('localhost', 2525)
    smtp.sendmail('noreply@kuma8088.com',
                  request.json['recipient'],
                  email_raw)
    smtp.quit()

    return 'OK', 200
```

#### Phase 2: AWS SES + Lambda実装

**Terraformリソース:**
```hcl
# SES Receipt Rule Set
resource "aws_ses_receipt_rule_set" "mailserver" {
  rule_set_name = "mailserver-inbound"
}

# SES Receipt Rule
resource "aws_ses_receipt_rule" "save_to_s3" {
  rule_set_name = aws_ses_receipt_rule_set.mailserver.rule_set_name
  name          = "save-to-s3"
  recipients    = ["kuma8088.com"]
  enabled       = true

  s3_action {
    bucket_name = aws_s3_bucket.mail_storage.bucket
    position    = 1
  }
}

# Lambda Function (S3トリガー)
resource "aws_lambda_function" "mail_forwarder" {
  function_name = "mailserver-forwarder"
  runtime       = "python3.12"
  handler       = "lambda_function.lambda_handler"

  environment {
    variables = {
      DELL_API_ENDPOINT = "https://mail-api.dell.kuma8088.com/inbound-mail"
      API_KEY          = var.dell_api_key
    }
  }
}
```

**Lambda実装例:**
```python
import boto3
import requests
import os

s3 = boto3.client('s3')

def lambda_handler(event, context):
    # S3からメール取得
    bucket = event['Records'][0]['s3']['bucket']['name']
    key = event['Records'][0]['s3']['object']['key']

    obj = s3.get_object(Bucket=bucket, Key=key)
    email_raw = obj['Body'].read().decode('utf-8')

    # Dell側APIに転送
    response = requests.post(
        os.environ['DELL_API_ENDPOINT'],
        headers={'X-API-Key': os.environ['API_KEY']},
        json={'email_raw': email_raw, 'recipient': 'user@kuma8088.com'}
    )

    return {'statusCode': 200}
```

#### Phase 3: MXレコード切り替え

```bash
# Route53/Cloudflareで設定
# MX Record: 10 inbound-smtp.us-west-2.amazonaws.com
```

---

## 5. テスト手順

### 5.1 オプション3（EC2最適化）のテスト

**テスト項目:**
1. メール受信テスト
2. LMTP転送テスト
3. Tailscale VPN接続テスト
4. CloudWatch Logs確認

**実行手順:**
```bash
# 1. EC2にSSH接続
ssh ec2-user@mail.kuma8088.com

# 2. Postfixコンテナ確認
docker ps | grep postfix

# 3. テストメール送信（外部から）
# Gmail等から test@kuma8088.com 宛にメール送信

# 4. Dell側で受信確認
ssh dell-user@100.110.222.53
docker compose -f /opt/onprem-infra-system/project-root-infra/services/mailserver/docker-compose.yml logs dovecot | tail -20
```

### 5.2 オプション4（SES Receiving）のテスト

**テスト項目:**
1. SES受信テスト
2. S3保存確認
3. Lambda実行確認
4. Dell APIエンドポイント確認
5. Dovecot LMTP転送確認

**実行手順:**
```bash
# 1. Dell側APIエンドポイント起動確認
curl -H "X-API-Key: YOUR_API_KEY" \
     -X POST https://mail-api.dell.kuma8088.com/health

# 2. テストメール送信（外部から）
# Gmail等から test@kuma8088.com 宛にメール送信

# 3. S3保存確認
aws s3 ls s3://mailserver-inbound-bucket/

# 4. Lambda実行ログ確認
aws logs tail /aws/lambda/mailserver-forwarder --follow

# 5. Dell側受信確認
docker compose logs dovecot | grep LMTP
```

---

## 6. ロールバック手順

### 6.1 オプション3（EC2最適化）のロールバック

**手順:**
```bash
# 1. 元のEC2インスタンスが残っている場合
# MXレコードを元のEIPに戻す
# Route53/Cloudflare DNS設定変更

# 2. 元のEC2を削除済みの場合
# Terraformで再デプロイ
cd /opt/onprem-infra-system/project-root-infra/services/mailserver/terraform
terraform apply

# 3. MXレコード確認
dig MX kuma8088.com
```

### 6.2 オプション4（SES Receiving）のロールバック

**手順:**
```bash
# 1. MXレコードをEC2に戻す
# Route53/CloudflareでMXレコード変更
# MX 10 mail.kuma8088.com (EC2 EIP)

# 2. SES Receipt Ruleを無効化
aws ses update-receipt-rule \
    --rule-set-name mailserver-inbound \
    --rule save-to-s3 \
    --rule '{"Enabled":false}'

# 3. EC2 Postfix再起動
ssh ec2-user@mail.kuma8088.com
docker restart mailserver-postfix

# 4. メール受信テスト
# 外部からテストメール送信して確認
```

---

## 7. コスト比較

### 7.1 月額コスト比較

| オプション | 初期コスト | 月額コスト | 年額コスト | 備考 |
|-----------|-----------|-----------|-----------|------|
| **現状（EC2 t4g.nano）** | ¥0 | ¥525 | ¥6,300 | EIP + インスタンス |
| **オプション1（Fetchmail）** | ¥0 | ¥0～¥900 | ¥0～¥10,800 | Google Workspace使用時 |
| **オプション2（Dell直接）** | ¥0 | ¥0 | ¥0 | ISP制約で実現不可の可能性大 |
| **オプション3（EC2最適化）** | ¥0 | ¥525 | ¥6,300 | 現状維持 |
| **オプション3-A（Lightsail）** | ¥0 | ¥525 | ¥6,300 | 固定IP無料 |
| **オプション3-B（Savings Plans）** | ¥0 | ¥368 | ¥4,416 | 1年コミット |
| **オプション4（SES Receiving）** | ¥30,000～ | ¥45 | ¥540 | 初期実装コスト高 |
| **オプション5（Email Worker）** | ¥50,000～ | ¥0 | ¥0 | 初期実装コスト高 |

### 7.2 TCO（Total Cost of Ownership）比較（3年間）

| オプション | 初期コスト | 3年運用コスト | TCO (3年) | 保守工数 |
|-----------|-----------|-------------|----------|---------|
| **現状（EC2）** | ¥0 | ¥18,900 | ¥18,900 | 低 |
| **オプション3-B（Savings Plans）** | ¥0 | ¥13,248 | ¥13,248 | 低 |
| **オプション4（SES）** | ¥30,000 | ¥1,620 | ¥31,620 | 中 |
| **オプション5（Worker）** | ¥50,000 | ¥0 | ¥50,000 | 高 |

**結論:**
- **短期（1年以内）**: オプション3-B（EC2 + Savings Plans）が最適
- **中期（1-3年）**: オプション3-B継続が最適
- **長期（3年以上）**: オプション4（SES）が最適（初期投資回収後）

---

## 8. 推奨アクションプラン

### Phase 1: 即時実施（今週中）

**アクション:**
- ✅ EC2構成の維持を決定
- ✅ この移行計画書をリポジトリにコミット
- ⏳ Savings Plansの検討（1年コミット可能か確認）

**判断基準:**
- 現在の構成は安定稼働中（問題なし）
- 月額¥525は許容範囲内
- Cloudflare Email Routingの制限により直接置き換え不可

### Phase 2: Phase 12（AWS移行）と同時実施（6ヶ月後～）

**アクション:**
- Amazon SES Receivingの詳細設計
- Dell側APIエンドポイント実装
- Lambda関数実装
- Terraform IaC化

**判断基準:**
- Dell → AWS移行時にメールインフラも刷新
- サーバーレス化でコスト最適化
- スケーラビリティ向上

### Phase 3: 継続的な改善

**アクション:**
- 月次コスト監視
- メール配信成功率の監視
- セキュリティパッチ適用

---

## 9. まとめ

### 9.1 現在のシステム構成（重要）

**EC2 MX Gatewayの役割:**
- ⚠️ **受信専用** - Port 25でメール受信し、Dell側にLMTP転送
- ❌ **送信機能なし** - 送信は全てDell側のPostfix → SendGrid経由で処理
- ⚠️ **EC2廃止の影響範囲** - 受信フローのみ（送信には一切影響しない）

**Dell側の構成:**
- ✅ Dovecot: LMTP受信（Port 2525）+ IMAP/POP3提供
- ✅ Postfix: SendGrid経由でメール送信（Port 587）
- ✅ 送信フローはEC2不使用で既に独立している

### 9.2 重要な発見

**Cloudflare Email Routingの制限:**
- ❌ カスタムSMTP/LMTPサーバーへの直接転送は**不可能**
- ❌ 現在のEC2 MX Gateway構成を直接置き換えることは**できない**
- ✅ 検証済みメールアドレスへの転送のみ対応

### 9.3 最終推奨

**短期（現在～Phase 12）:**
- ✅ **オプション3-B: EC2 + Savings Plans**
- 理由: 安定性最優先、リスク最小、コストも許容範囲内

**中長期（Phase 12以降）:**
- ⭐ **オプション4: Amazon SES Receiving**
- 理由: サーバーレス、コスト最適、AWS統合

### 9.4 次のステップ

1. ✅ この移行計画書をGitにコミット
2. ⏳ Savings Plans適用の検討（オプション）
3. ⏳ Phase 12でSES Receiving実装の詳細設計開始

---

**参考資料:**
- [Cloudflare Email Routing公式ドキュメント](https://developers.cloudflare.com/email-routing/)
- [Amazon SES Receiving Email](https://docs.aws.amazon.com/ses/latest/dg/receiving-email.html)
- [services/mailserver/terraform/main.tf](../../../services/mailserver/terraform/main.tf)
- [services/mailserver/terraform/user_data.sh](../../../services/mailserver/terraform/user_data.sh)
