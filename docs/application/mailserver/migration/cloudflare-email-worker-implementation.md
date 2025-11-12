# Cloudflare Email Worker移行実装手順書

**作成日**: 2025-11-12
**対象**: EC2 MX Gateway廃止、Cloudflare Email Worker実装
**ステータス**: 実装準備中

---

## 目次

1. [選定理由](#1-選定理由)
2. [システム設計](#2-システム設計)
3. [実装手順](#3-実装手順)
4. [テスト手順](#4-テスト手順)
5. [本番移行手順](#5-本番移行手順)
6. [ロールバック手順](#6-ロールバック手順)
7. [運用・保守](#7-運用保守)

---

## 1. 選定理由

### 1.1 Cloudflare Email Worker方式を選択した理由

**コスト:**
- ✅ **月額¥0** - EC2 t4g.nano（¥525/月）→ ¥0
- ✅ Cloudflare Workers無料枠: 10万リクエスト/日（十分）
- ✅ Cloudflare Email Routing: 完全無料

**技術的メリット:**
- ✅ **エッジ実行** - 世界中のCloudflare DCで実行、レイテンシ最小
- ✅ **コールドスタートなし** - AWS Lambdaと違い常に高速起動
- ✅ **既存インフラ活用** - Cloudflare Tunnelを既にBlog Systemで使用中
- ✅ **サーバーレス** - EC2管理作業（パッチ、監視）が不要

**運用メリット:**
- ✅ **シンプルな構成** - EC2、Tailscale VPN廃止で構成がシンプルに
- ✅ **スケーラビリティ** - Cloudflareのグローバルネットワーク活用
- ✅ **高可用性** - Cloudflareのインフラに依存、SLA 99.99%

**実装コスト:**
- ⚠️ 初期実装が必要（Dell側API + Worker）
- ⚠️ 学習コスト（Cloudflare Workers API）
- ✅ **但し、一度実装すれば保守は容易**（JavaScript/TypeScript）

**比較:**

| 項目 | EC2維持 | Cloudflare Worker |
|------|---------|------------------|
| 月額コスト | ¥525 | **¥0** |
| 初期実装 | 不要 | **必要** |
| 保守作業 | 定期的 | **最小限** |
| レイテンシ | 高（VPN経由） | **超低（エッジ）** |
| 可用性 | 99.9% | **99.99%** |

**結論:** 初期実装コストはかかるが、長期的なコスト削減、運用効率化、パフォーマンス向上を考慮し、**Cloudflare Email Worker方式を採用**。

---

## 2. システム設計

### 2.1 アーキテクチャ

**新しいメール受信フロー:**
```
Internet (Port 25)
  ↓
Cloudflare Email Routing
  ↓
Cloudflare Email Worker (JavaScript実行、エッジ)
  ↓ HTTPS POST
Cloudflare Tunnel (既存、Blog System用)
  ↓
Dell側 メール受信APIエンドポイント (Flask/FastAPI)
  ↓ LMTP (localhost:2525)
Dell側 Dovecot
  ↓
Mailbox Storage
```

**送信フロー（変更なし）:**
```
Mail Client (Port 587)
  ↓
Dell Postfix
  ↓
SendGrid Relay
  ↓
Internet
```

### 2.2 コンポーネント設計

#### 2.2.1 Cloudflare Email Routing

**設定:**
- **MXレコード**: Cloudflareが自動設定
- **ルーティングルール**: すべてのメールをWorkerに転送
- **ドメイン**: kuma8088.com

#### 2.2.2 Cloudflare Email Worker

**役割:** メールをパース→Dell側APIに転送

**実装言語:** JavaScript/TypeScript

**主要機能:**
- メール受信イベントハンドリング
- メール内容のJSON化
- Dell側APIへのHTTPS POST
- エラーハンドリング・リトライ

**制限:**
- メモリ: 128MB
- 実行時間: 30秒
- CPU時間: 10ms（無料枠）/ 50ms（有料枠）

**コード例:**
```javascript
export default {
  async email(message, env, ctx) {
    try {
      // メール本文を読み取り
      const rawEmail = await streamToArrayBuffer(message.raw);
      const emailText = new TextDecoder().decode(rawEmail);

      // メタデータ取得
      const emailData = {
        from: message.from,
        to: message.to,
        subject: message.headers.get("subject"),
        raw: emailText,
        timestamp: new Date().toISOString()
      };

      // Dell側APIに転送
      const response = await fetch(env.DELL_API_ENDPOINT, {
        method: "POST",
        headers: {
          "Content-Type": "application/json",
          "X-API-Key": env.API_KEY,
          "User-Agent": "Cloudflare-Email-Worker/1.0"
        },
        body: JSON.stringify(emailData),
        // タイムアウト設定
        signal: AbortSignal.timeout(25000)
      });

      if (!response.ok) {
        throw new Error(`API返答エラー: ${response.status}`);
      }

      console.log(`メール転送成功: ${message.to}`);

    } catch (error) {
      console.error("メール処理エラー:", error);
      // エラー時は受信拒否（リトライされる）
      message.setReject(`Processing failed: ${error.message}`);
    }
  }
};

// Helper function
async function streamToArrayBuffer(stream) {
  const chunks = [];
  const reader = stream.getReader();
  while (true) {
    const { done, value } = await reader.read();
    if (done) break;
    chunks.push(value);
  }
  return new Uint8Array(chunks.flat());
}
```

#### 2.2.3 Dell側メール受信API

**役割:** WorkerからHTTPSでメール受信→Dovecot LMTPに転送

**実装言語:** Python (Flask/FastAPI)

**エンドポイント:** `POST /api/v1/inbound-mail`

**認証:** X-API-Keyヘッダー

**処理フロー:**
1. API Key検証
2. メールデータのバリデーション
3. RFC822形式のメールをDovecot LMTPに転送
4. 結果を返却

**配置場所:** `/opt/mailserver-api/`

**Docker化:** 既存のmailserver stackに追加

#### 2.2.4 Cloudflare Tunnel

**役割:** Dell側APIをインターネットに公開（既存のBlog用Tunnelを拡張）

**設定:**
- **Tunnel名**: `dell-services` (既存)
- **新規ホスト名**: `mail-api.kuma8088.com`
- **転送先**: `http://localhost:8080` (Dell側API)

**既存構成:**
```yaml
# 既存: services/blog/config/cloudflared/config.yml
ingress:
  - hostname: blog.kuma8088.com
    service: http://nginx:80
  # ... 他のBlogサイト

  # 新規追加:
  - hostname: mail-api.kuma8088.com
    service: http://mailserver-api:8080

  - service: http_status:404
```

### 2.3 セキュリティ設計

**認証:**
- API Key認証（Workerに環境変数で設定）
- 最低64文字のランダム文字列

**通信:**
- Cloudflare Tunnel: 自動HTTPS（証明書不要）
- Worker → API: HTTPS暗号化通信

**アクセス制御:**
- Dell側API: Cloudflare Tunnelのみ受付（外部直接アクセス不可）
- Workerから以外のアクセスはAPI Keyで拒否

**ログ:**
- Worker: Cloudflare Logsに記録
- Dell側API: `/var/log/mailserver-api/access.log`

### 2.4 エラーハンドリング

**Worker側:**
- API呼び出し失敗 → メール受信拒否（送信者にリトライさせる）
- タイムアウト（25秒） → 受信拒否
- パースエラー → ログに記録してスキップ

**Dell側API:**
- LMTP転送失敗 → HTTP 500返却（Workerがリトライ）
- バリデーションエラー → HTTP 400返却（リトライしない）

---

## 3. 実装手順

### Phase 1: Dell側メール受信API実装

#### 3.1.1 APIディレクトリ作成

```bash
cd /opt/onprem-infra-system/project-root-infra/services/mailserver
mkdir -p api/app
cd api
```

#### 3.1.2 FastAPI実装

**ファイル:** `api/app/main.py`

```python
from fastapi import FastAPI, HTTPException, Header, Request
from pydantic import BaseModel, EmailStr
import smtplib
import os
import logging
from datetime import datetime

# ロギング設定
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler('/var/log/mailserver-api/app.log'),
        logging.StreamHandler()
    ]
)
logger = logging.getLogger(__name__)

app = FastAPI(title="Mailserver Inbound API", version="1.0.0")

# 環境変数
API_KEY = os.getenv("API_KEY")
LMTP_HOST = os.getenv("LMTP_HOST", "dovecot")
LMTP_PORT = int(os.getenv("LMTP_PORT", "2525"))

# リクエストモデル
class InboundEmail(BaseModel):
    from_addr: str = Field(alias="from")
    to: EmailStr
    subject: str
    raw: str
    timestamp: str

# ヘルスチェック
@app.get("/health")
async def health_check():
    return {"status": "healthy", "timestamp": datetime.utcnow().isoformat()}

# メール受信エンドポイント
@app.post("/api/v1/inbound-mail")
async def receive_inbound_mail(
    email: InboundEmail,
    x_api_key: str = Header(None)
):
    # API Key検証
    if not x_api_key or x_api_key != API_KEY:
        logger.warning(f"不正なAPI Key: {x_api_key[:10]}...")
        raise HTTPException(status_code=401, detail="Invalid API Key")

    logger.info(f"メール受信: From={email.from_addr}, To={email.to}, Subject={email.subject}")

    try:
        # Dovecot LMTPに転送
        smtp = smtplib.SMTP(LMTP_HOST, LMTP_PORT, timeout=30)

        # LMTP配送
        result = smtp.sendmail(
            email.from_addr,
            [email.to],
            email.raw.encode('utf-8')
        )

        smtp.quit()

        logger.info(f"LMTP転送成功: {email.to}")
        return {
            "status": "success",
            "message": "Email delivered to LMTP",
            "recipient": email.to
        }

    except smtplib.SMTPException as e:
        logger.error(f"LMTP転送エラー: {str(e)}")
        raise HTTPException(status_code=500, detail=f"LMTP error: {str(e)}")

    except Exception as e:
        logger.error(f"予期しないエラー: {str(e)}")
        raise HTTPException(status_code=500, detail=f"Internal error: {str(e)}")
```

#### 3.1.3 requirements.txt

**ファイル:** `api/requirements.txt`

```
fastapi==0.104.1
uvicorn[standard]==0.24.0
pydantic[email]==2.5.0
```

#### 3.1.4 Dockerfile

**ファイル:** `api/Dockerfile`

```dockerfile
FROM python:3.11-slim

WORKDIR /app

# システムパッケージ更新
RUN apt-get update && apt-get install -y --no-install-recommends \
    curl \
    && rm -rf /var/lib/apt/lists/*

# Python依存関係インストール
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# アプリケーションコピー
COPY app/ ./app/

# ログディレクトリ作成
RUN mkdir -p /var/log/mailserver-api

# ヘルスチェック
HEALTHCHECK --interval=30s --timeout=5s --start-period=10s --retries=3 \
  CMD curl -f http://localhost:8080/health || exit 1

# 起動
CMD ["uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "8080"]
```

#### 3.1.5 docker-compose.yml更新

**ファイル:** `services/mailserver/docker-compose.yml`

既存のdocker-compose.ymlに以下を追加：

```yaml
services:
  # ... 既存のサービス ...

  # メール受信APIエンドポイント
  mailserver-api:
    build: ./api
    container_name: mailserver-api
    hostname: mailserver-api
    restart: always
    networks:
      mailserver_network:
        ipv4_address: 172.20.0.100
    ports:
      - "8080:8080"
    environment:
      - API_KEY=${MAILSERVER_API_KEY}
      - LMTP_HOST=dovecot
      - LMTP_PORT=2525
      - TZ=${TZ}
    volumes:
      - ./logs/mailserver-api:/var/log/mailserver-api
    depends_on:
      - dovecot
    healthcheck:
      test: ["CMD", "curl", "-f", "http://localhost:8080/health"]
      interval: 30s
      timeout: 5s
      retries: 3
```

#### 3.1.6 .env更新

**ファイル:** `services/mailserver/.env`

```bash
# 既存の環境変数...

# メール受信API
MAILSERVER_API_KEY=<64文字以上のランダム文字列>
```

**API Key生成:**
```bash
openssl rand -base64 48
```

#### 3.1.7 APIビルド・起動

```bash
cd /opt/onprem-infra-system/project-root-infra/services/mailserver

# APIコンテナビルド
docker compose build mailserver-api

# 起動
docker compose up -d mailserver-api

# ログ確認
docker compose logs -f mailserver-api

# ヘルスチェック
curl http://localhost:8080/health
```

---

### Phase 2: Cloudflare Tunnel設定更新

#### 3.2.1 現在のCloudflare Tunnel確認

```bash
# Blog用Cloudflare Tunnel確認
cd /opt/onprem-infra-system/project-root-infra/services/blog
cat config/cloudflared/config.yml
```

#### 3.2.2 Tunnel設定に新規ホスト名追加

**オプションA: Blog用Tunnelを拡張（推奨）**

**ファイル:** `services/blog/config/cloudflared/config.yml`

```yaml
tunnel: <your-tunnel-id>
credentials-file: /etc/cloudflared/credentials.json

ingress:
  # 既存のBlogサイト
  - hostname: blog.kuma8088.com
    service: http://wordpress:80
  # ... 他のBlogサイト ...

  # 新規: メール受信API
  - hostname: mail-api.kuma8088.com
    service: http://172.20.0.100:8080
    originRequest:
      connectTimeout: 30s
      noTLSVerify: false

  - service: http_status:404
```

**オプションB: 別Tunnelを作成**

別のTunnelを作成する場合は、Cloudflare Dashboard → Zero Trust → Tunnelsで新規作成。

#### 3.2.3 Cloudflare DNS設定

Cloudflare Dashboard → DNS → Recordsで以下を確認：

```
mail-api.kuma8088.com  CNAME  <tunnel-id>.cfargotunnel.com  (Auto, Proxied)
```

Tunnel設定を保存すると自動的に作成されます。

#### 3.2.4 Tunnel再起動

```bash
cd /opt/onprem-infra-system/project-root-infra/services/blog

# Cloudflaredコンテナ再起動
docker compose restart cloudflared

# ログ確認
docker compose logs -f cloudflared
```

#### 3.2.5 API接続テスト

```bash
# 外部からヘルスチェック
curl https://mail-api.kuma8088.com/health

# 期待される応答:
# {"status":"healthy","timestamp":"2025-11-12T..."}
```

---

### Phase 3: Cloudflare Email Worker実装

#### 3.3.1 Cloudflare Workers作成

**Cloudflare Dashboard → Workers & Pages → Create application → Create Worker**

**Worker名:** `mailserver-inbound-relay`

#### 3.3.2 Workerコード実装

**ファイル:** `worker.js`

```javascript
/**
 * Cloudflare Email Worker - Mailserver Inbound Relay
 *
 * メール受信 → Dell側APIに転送
 */

export default {
  async email(message, env, ctx) {
    const startTime = Date.now();

    try {
      // メール基本情報取得
      const from = message.from;
      const to = message.to;
      const subject = message.headers.get("subject") || "(件名なし)";

      console.log(`[INFO] メール受信: From=${from}, To=${to}, Subject=${subject}`);

      // メール本文を文字列に変換
      const rawEmail = await streamToString(message.raw);

      // Dell側APIに送信するデータ
      const emailData = {
        from: from,
        to: to,
        subject: subject,
        raw: rawEmail,
        timestamp: new Date().toISOString()
      };

      // Dell側APIにPOST
      const response = await fetch(env.DELL_API_ENDPOINT, {
        method: "POST",
        headers: {
          "Content-Type": "application/json",
          "X-API-Key": env.API_KEY,
          "User-Agent": "Cloudflare-Email-Worker/1.0"
        },
        body: JSON.stringify(emailData),
        // 25秒タイムアウト（Worker制限30秒より短く）
        signal: AbortSignal.timeout(25000)
      });

      const elapsed = Date.now() - startTime;

      if (!response.ok) {
        const errorText = await response.text();
        console.error(`[ERROR] API応答エラー (${response.status}): ${errorText}, 経過時間=${elapsed}ms`);

        // 5xxエラー: 一時的エラーとして受信拒否（リトライされる）
        if (response.status >= 500) {
          message.setReject(`Temporary API error: ${response.status}`);
        } else {
          // 4xxエラー: 恒久的エラーとして受信拒否（リトライしない）
          message.setReject(`Permanent API error: ${response.status}`);
        }
        return;
      }

      const result = await response.json();
      console.log(`[SUCCESS] メール転送成功: ${to}, 経過時間=${elapsed}ms, 結果=${JSON.stringify(result)}`);

    } catch (error) {
      const elapsed = Date.now() - startTime;
      console.error(`[ERROR] メール処理エラー: ${error.message}, 経過時間=${elapsed}ms`);

      // エラー時は一時的エラーとして受信拒否（送信者がリトライ）
      message.setReject(`Processing failed: ${error.message}`);
    }
  }
};

/**
 * ReadableStreamを文字列に変換
 */
async function streamToString(stream) {
  const chunks = [];
  const reader = stream.getReader();

  try {
    while (true) {
      const { done, value } = await reader.read();
      if (done) break;
      chunks.push(value);
    }

    // Uint8Arrayを連結
    const totalLength = chunks.reduce((acc, chunk) => acc + chunk.length, 0);
    const result = new Uint8Array(totalLength);
    let offset = 0;

    for (const chunk of chunks) {
      result.set(chunk, offset);
      offset += chunk.length;
    }

    // UTF-8デコード
    return new TextDecoder('utf-8').decode(result);

  } finally {
    reader.releaseLock();
  }
}
```

#### 3.3.3 環境変数設定

Cloudflare Dashboard → Workers → mailserver-inbound-relay → Settings → Variables

**環境変数:**
- `DELL_API_ENDPOINT`: `https://mail-api.kuma8088.com/api/v1/inbound-mail`
- `API_KEY`: `<.envで生成したAPI Key>`（Encryptedで設定）

#### 3.3.4 Workerデプロイ

Dashboard上で「Save and Deploy」をクリック

---

### Phase 4: Cloudflare Email Routing設定

#### 3.4.1 Email Routing有効化

**Cloudflare Dashboard → Email → Email Routing → Enable Email Routing**

1. ドメイン選択: `kuma8088.com`
2. MXレコード自動設定を承認
3. 確認メール受信 → リンククリックで有効化

#### 3.4.2 Routing Rule作成

**Dashboard → Email → Email Routing → Routes → Create route**

**設定:**
- **Route type:** Send to Worker
- **Match:** All addresses (`*@kuma8088.com`)
- **Action:** Send to Worker
- **Worker:** `mailserver-inbound-relay`
- **Priority:** 1

#### 3.4.3 Catch-all設定

すべてのメールをWorkerに転送するため、Catch-allを有効化：

**Dashboard → Email → Email Routing → Settings**
- **Catch-all action:** Send to Worker → `mailserver-inbound-relay`

---

## 4. テスト手順

### 4.1 ローカルテスト（Dell側API）

```bash
# 1. API Keyを環境変数に設定
export API_KEY="<.envのMAILSERVER_API_KEY>"

# 2. テストメール送信
curl -X POST https://mail-api.kuma8088.com/api/v1/inbound-mail \
  -H "Content-Type: application/json" \
  -H "X-API-Key: $API_KEY" \
  -d '{
    "from": "test@example.com",
    "to": "user@kuma8088.com",
    "subject": "Test Email",
    "raw": "From: test@example.com\r\nTo: user@kuma8088.com\r\nSubject: Test Email\r\n\r\nThis is a test message.",
    "timestamp": "2025-11-12T10:00:00Z"
  }'

# 期待される応答:
# {"status":"success","message":"Email delivered to LMTP","recipient":"user@kuma8088.com"}

# 3. Dovecotログ確認
docker compose logs dovecot | grep LMTP | tail -10
```

### 4.2 Worker動作テスト

#### 4.2.1 テストメール送信（外部から）

Gmail等から `user@kuma8088.com` 宛にテストメール送信

#### 4.2.2 Workerログ確認

**Cloudflare Dashboard → Workers → mailserver-inbound-relay → Logs → Begin log stream**

期待されるログ:
```
[INFO] メール受信: From=sender@gmail.com, To=user@kuma8088.com, Subject=Test
[SUCCESS] メール転送成功: user@kuma8088.com, 経過時間=234ms
```

#### 4.2.3 Dell側ログ確認

```bash
# Dell側APIログ
docker compose logs mailserver-api | tail -20

# Dovecot受信ログ
docker compose logs dovecot | grep LMTP | tail -10

# メールボックス確認
ls -lh /opt/onprem-infra-system/project-root-infra/services/mailserver/data/mail/kuma8088.com/user/
```

### 4.3 エラーハンドリングテスト

#### 4.3.1 API Key不正テスト

```bash
# 不正なAPI Keyでテスト
curl -X POST https://mail-api.kuma8088.com/api/v1/inbound-mail \
  -H "Content-Type: application/json" \
  -H "X-API-Key: invalid-key" \
  -d '{...}'

# 期待: HTTP 401 Unauthorized
```

#### 4.3.2 LMTP停止時テスト

```bash
# Dovecot停止
docker compose stop dovecot

# テストメール送信（外部から）
# 期待: Workerログに[ERROR]、送信者にエラー通知

# Dovecot再起動
docker compose start dovecot
```

---

## 5. 本番移行手順

### 5.1 事前準備

#### 5.1.1 バックアップ

```bash
# 現在のメールボックスをバックアップ
cd /opt/onprem-infra-system/project-root-infra/services/mailserver
./scripts/backup-mailserver.sh --component all

# バックアップ確認
ls -lh /mnt/backup-hdd/mailserver/daily/$(date +%Y-%m-%d)/
```

#### 5.1.2 現在のMXレコード確認

```bash
dig MX kuma8088.com

# 現在: mail.kuma8088.com (EC2)
```

#### 5.1.3 TTL短縮（移行24時間前）

Cloudflare Dashboard → DNS → MXレコードのTTLを300秒（5分）に変更

### 5.2 移行実施

#### 5.2.1 MXレコード切り替え

**Cloudflare Dashboard → DNS → Records**

**削除:**
- `MX 10 mail.kuma8088.com`

**追加（Email Routing有効化時に自動追加済み）:**
```
MX 1  route1.mx.cloudflare.net
MX 2  route2.mx.cloudflare.net
MX 3  route3.mx.cloudflare.net
```

#### 5.2.2 DNS伝播確認

```bash
# MXレコード確認（5-10分待つ）
dig MX kuma8088.com

# Cloudflare MXレコードが返ることを確認
# route1.mx.cloudflare.net, route2.mx.cloudflare.net, route3.mx.cloudflare.net
```

#### 5.2.3 メール受信テスト

```bash
# 外部（Gmail等）からテストメール送信
# → user@kuma8088.com

# Workerログ確認
# Cloudflare Dashboard → Workers → Logs

# Dell側受信確認
docker compose logs mailserver-api | tail -20
docker compose logs dovecot | grep LMTP | tail -10
```

### 5.3 EC2廃止

#### 5.3.1 EC2監視（24時間）

MXレコード切り替え後、24時間はEC2を稼働させたまま監視：

```bash
# EC2ログ確認（メール受信が来ないことを確認）
ssh ec2-user@mail.kuma8088.com
docker logs mailserver-postfix | tail -50

# 24時間後、新規メール受信がないことを確認
```

#### 5.3.2 EC2停止

```bash
# Terraformでインスタンス停止（削除前にテスト）
cd /opt/onprem-infra-system/project-root-infra/services/mailserver/terraform
terraform plan -var="instance_state=stopped"
terraform apply -var="instance_state=stopped"
```

**インスタンス停止後、1週間様子見**

#### 5.3.3 EC2完全削除

問題なければEC2を完全削除：

```bash
cd /opt/onprem-infra-system/project-root-infra/services/mailserver/terraform

# EC2インスタンス削除
terraform destroy -target=aws_instance.mailserver_mx
terraform destroy -target=aws_eip_association.mailserver_eip_ec2

# EIPは保持（必要に応じて削除）
# terraform destroy -target=aws_eip.mailserver_eip
```

---

## 6. ロールバック手順

### 6.1 即座にロールバック（緊急時）

```bash
# 1. MXレコードをEC2に戻す
# Cloudflare Dashboard → DNS → Records
# MX 10 mail.kuma8088.com (EC2 EIP)

# 2. Email Routing無効化
# Cloudflare Dashboard → Email → Email Routing → Disable

# 3. EC2 Postfix再起動
ssh ec2-user@mail.kuma8088.com
docker restart mailserver-postfix

# 4. MX伝播確認（5分）
dig MX kuma8088.com

# 5. テストメール送信
# 外部から user@kuma8088.com にメール送信

# 6. EC2ログ確認
docker logs mailserver-postfix | tail -20
```

### 6.2 段階的ロールバック（問題調査時）

```bash
# 1. Email Routingを一時停止
# Dashboard → Email → Email Routing → Routes → Disable

# 2. Workerログ確認
# Dashboard → Workers → Logs

# 3. Dell側APIログ確認
docker compose logs mailserver-api | grep ERROR

# 4. 問題修正後、Routeを再有効化
# Dashboard → Email → Email Routing → Routes → Enable
```

---

## 7. 運用・保守

### 7.1 日次監視

#### 7.1.1 Workerログ監視

```bash
# Cloudflare Dashboard → Workers → mailserver-inbound-relay → Logs

# 確認項目:
# - エラー率（目標: 0.1%未満）
# - 平均レスポンスタイム（目標: 500ms未満）
# - タイムアウト発生（目標: 0件）
```

#### 7.1.2 Dell側APIログ監視

```bash
# エラーログ確認
docker compose logs mailserver-api | grep ERROR

# アクセスログ統計
docker compose exec mailserver-api tail -100 /var/log/mailserver-api/app.log | \
  grep "メール受信" | wc -l
```

#### 7.1.3 Dovecot LMTP監視

```bash
# LMTP配送成功数
docker compose logs dovecot | grep "saved mail to" | wc -l

# LMTPエラー確認
docker compose logs dovecot | grep -i "lmtp.*error"
```

### 7.2 週次監視

#### 7.2.1 Cloudflare Workers使用量確認

**Dashboard → Workers & Pages → mailserver-inbound-relay → Metrics**

- **リクエスト数**: 無料枠10万/日以内か確認
- **CPU時間**: 無料枠10ms/リクエスト以内か確認
- **エラー率**: 0.1%未満を維持

#### 7.2.2 Dell側ディスク使用量確認

```bash
# メールボックス容量
du -sh /opt/onprem-infra-system/project-root-infra/services/mailserver/data/mail/

# ログ容量
du -sh /opt/onprem-infra-system/project-root-infra/services/mailserver/logs/
```

### 7.3 月次保守

#### 7.3.1 コスト確認

**Cloudflare Dashboard → Analytics → Workers**

- Workers無料枠超過の有無確認
- 無料枠超過の場合: Workers Paidプラン($5/月)検討

#### 7.3.2 セキュリティパッチ

```bash
# Dell側APIコンテナ再ビルド
cd /opt/onprem-infra-system/project-root-infra/services/mailserver
docker compose pull mailserver-api
docker compose up -d --build mailserver-api

# Workerコード更新（必要に応じて）
# Dashboard → Workers → Edit code
```

#### 7.3.3 API Key更新（3ヶ月毎推奨）

```bash
# 1. 新しいAPI Key生成
NEW_API_KEY=$(openssl rand -base64 48)

# 2. .env更新
nano services/mailserver/.env
# MAILSERVER_API_KEY=<NEW_API_KEY>

# 3. API再起動
docker compose restart mailserver-api

# 4. Cloudflare Worker環境変数更新
# Dashboard → Workers → Settings → Variables
# API_KEY = <NEW_API_KEY>

# 5. 動作確認
curl https://mail-api.kuma8088.com/health
```

### 7.4 トラブルシューティング

#### 7.4.1 メール受信できない

**確認手順:**
```bash
# 1. MXレコード確認
dig MX kuma8088.com

# 2. Email Routing有効確認
# Dashboard → Email → Email Routing → Status

# 3. Workerログ確認
# Dashboard → Workers → Logs

# 4. Dell側API確認
curl https://mail-api.kuma8088.com/health
docker compose logs mailserver-api | tail -50

# 5. Dovecot LMTP確認
docker compose exec dovecot doveadm service status lmtp
```

#### 7.4.2 Workerタイムアウト

**原因:**
- Dell側APIレスポンス遅延
- Cloudflare Tunnel接続問題

**対処:**
```bash
# 1. Dell側API応答時間確認
time curl -X POST https://mail-api.kuma8088.com/api/v1/inbound-mail \
  -H "X-API-Key: $API_KEY" \
  -H "Content-Type: application/json" \
  -d '{...}'

# 2. Cloudflare Tunnel確認
docker compose logs cloudflared | tail -50

# 3. Dovecot LMTP応答確認
echo "QUIT" | nc localhost 2525
```

#### 7.4.3 API Key漏洩時の緊急対応

```bash
# 1. 即座にAPI Key更新
NEW_API_KEY=$(openssl rand -base64 48)

# 2. .env更新
nano services/mailserver/.env
docker compose restart mailserver-api

# 3. Worker環境変数更新
# Dashboard → Workers → Settings → Variables

# 4. 不正アクセスログ確認
docker compose logs mailserver-api | grep "不正なAPI Key"
```

---

## 8. 参考資料

**Cloudflare公式ドキュメント:**
- [Email Routing](https://developers.cloudflare.com/email-routing/)
- [Email Workers](https://developers.cloudflare.com/email-routing/email-workers/)
- [Cloudflare Workers](https://developers.cloudflare.com/workers/)
- [Cloudflare Tunnel](https://developers.cloudflare.com/cloudflare-one/connections/connect-apps/)

**内部ドキュメント:**
- [services/mailserver/docker-compose.yml](../../../services/mailserver/docker-compose.yml)
- [services/blog/config/cloudflared/config.yml](../../../services/blog/config/cloudflared/config.yml)
- [docs/application/blog/cloudflare-tunnel-hostnames.md](../../blog/cloudflare-tunnel-hostnames.md)

**関連Issue:**
- Mailserver infrastructure optimization

---

**実装完了後の次のステップ:**
1. ✅ この実装手順書に従って実装
2. ✅ テスト完了後、本番移行
3. ✅ EC2廃止完了（月額¥525削減）
4. ✅ 運用監視体制確立
