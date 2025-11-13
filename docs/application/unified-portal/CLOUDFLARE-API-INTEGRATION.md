# Cloudflare API統合ガイド

**作成日**: 2025-11-13
**対象**: 統合管理ポータル - ドメイン管理機能

---

## 📋 概要

統合管理ポータルのドメイン管理機能では、**Cloudflare API**を使用してDNSレコードの管理を行います。

### Cloudflare DNSを使用する理由

- ✅ **DDoS防御**: 無制限のDDoS攻撃防御
- ✅ **CDN**: 世界中のエッジサーバーで高速配信
- ✅ **WAF**: SQLインジェクション、XSS等の攻撃防御
- ✅ **SSL/TLS**: 自動証明書発行・更新
- ✅ **99.99% 稼働率**: 高い信頼性
- ✅ **API統合**: 簡単にDNSレコード管理
- ✅ **コスト**: Freeプランで十分（$0/月）

---

## 🔑 Cloudflare API Token取得

### Step 1: Cloudflare Dashboardにログイン

https://dash.cloudflare.com/

### Step 2: API Token作成

1. 右上のプロフィールアイコン → **My Profile**
2. 左メニュー → **API Tokens**
3. **Create Token** ボタンをクリック

### Step 3: テンプレート選択

**"Edit zone DNS"** テンプレートを選択 → **Use template**

### Step 4: 権限設定

#### Permissions（権限）
- Zone → **DNS** → **Edit**
- Zone → **Zone** → **Read**

#### Zone Resources（対象ゾーン）
- **All zones from an account** を選択
  - または、特定のゾーンのみ選択

#### Client IP Address Filtering（オプション）
- Dell WorkStationの固定IPがあれば設定（推奨）
- なければスキップ

#### TTL（オプション）
- Start Date: 今日
- End Date: 無期限 または 1年後（定期的に更新推奨）

### Step 5: トークン生成

1. **Continue to summary** → **Create Token**
2. **トークンが表示される（1回のみ）**
   ```
   YOUR_CLOUDFLARE_API_TOKEN_HERE
   ```
3. **必ずコピーして安全に保管**

### Step 6: トークンテスト

```bash
# トークンが正しく動作するかテスト
curl -X GET "https://api.cloudflare.com/client/v4/user/tokens/verify" \
     -H "Authorization: Bearer YOUR_CLOUDFLARE_API_TOKEN_HERE" \
     -H "Content-Type: application/json"

# 成功時の出力例
{
  "success": true,
  "errors": [],
  "messages": [],
  "result": {
    "id": "...",
    "status": "active"
  }
}
```

---

## ⚙️ Backend設定

### 環境変数設定

```bash
# services/unified-portal/backend/.env
cat >> .env << 'EOF'

# Cloudflare API
CLOUDFLARE_API_TOKEN=YOUR_CLOUDFLARE_API_TOKEN_HERE
CLOUDFLARE_EMAIL=your-email@example.com
EOF
```

### config.py 更新

すでに実装済み（`services/unified-portal/backend/app/config.py`）:

```python
class Settings(BaseSettings):
    # ... 既存設定 ...

    # Cloudflare API
    cloudflare_api_token: str = ""
    cloudflare_email: str = ""
```

---

## 🔌 API エンドポイント仕様

### 1. ゾーン一覧取得

**GET** `/api/v1/domains/zones`

**Response**:
```json
{
  "domains": [
    {
      "id": "zone-id-123",
      "name": "kuma8088.com",
      "status": "active",
      "name_servers": ["ns1.cloudflare.com", "ns2.cloudflare.com"]
    }
  ]
}
```

### 2. DNSレコード一覧取得

**GET** `/api/v1/domains/{domain}/dns`

**Response**:
```json
{
  "records": [
    {
      "id": "record-id-123",
      "type": "A",
      "name": "@",
      "content": "172.67.148.123",
      "ttl": 1,
      "proxied": true
    },
    {
      "id": "record-id-456",
      "type": "MX",
      "name": "@",
      "content": "route1.mx.cloudflare.net",
      "priority": 85,
      "ttl": 1
    }
  ]
}
```

### 3. DNSレコード作成

**POST** `/api/v1/domains/{domain}/dns`

**Request**:
```json
{
  "type": "A",
  "name": "www",
  "content": "172.67.148.123",
  "ttl": 1,
  "proxied": true
}
```

**Response**:
```json
{
  "success": true,
  "record": {
    "id": "new-record-id",
    "type": "A",
    "name": "www",
    "content": "172.67.148.123"
  }
}
```

### 4. DNSレコード更新

**PUT** `/api/v1/domains/{domain}/dns/{record_id}`

**Request**:
```json
{
  "content": "172.67.148.124",
  "ttl": 3600
}
```

### 5. DNSレコード削除

**DELETE** `/api/v1/domains/{domain}/dns/{record_id}`

**Response**:
```json
{
  "success": true,
  "message": "DNS record deleted successfully"
}
```

---

## 📝 使用例

### Python（Backend）

```python
import httpx
from typing import List, Dict

async def get_dns_records(zone_id: str, api_token: str) -> List[Dict]:
    """Cloudflare DNSレコード取得"""
    async with httpx.AsyncClient() as client:
        response = await client.get(
            f"https://api.cloudflare.com/client/v4/zones/{zone_id}/dns_records",
            headers={
                "Authorization": f"Bearer {api_token}",
                "Content-Type": "application/json",
            },
        )
        data = response.json()
        return data["result"]

async def create_dns_record(
    zone_id: str,
    api_token: str,
    record_type: str,
    name: str,
    content: str,
    ttl: int = 1,
    proxied: bool = False
) -> Dict:
    """Cloudflare DNSレコード作成"""
    async with httpx.AsyncClient() as client:
        response = await client.post(
            f"https://api.cloudflare.com/client/v4/zones/{zone_id}/dns_records",
            headers={
                "Authorization": f"Bearer {api_token}",
                "Content-Type": "application/json",
            },
            json={
                "type": record_type,
                "name": name,
                "content": content,
                "ttl": ttl,
                "proxied": proxied,
            },
        )
        data = response.json()
        return data["result"]
```

### TypeScript（Frontend）

```typescript
// src/lib/api.ts
export const cloudflareAPI = {
  async getDNSRecords(domain: string) {
    const response = await fetch(`/api/v1/domains/${domain}/dns`);
    return response.json();
  },

  async createDNSRecord(domain: string, record: DNSRecord) {
    const response = await fetch(`/api/v1/domains/${domain}/dns`, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify(record),
    });
    return response.json();
  },

  async deleteDNSRecord(domain: string, recordId: string) {
    const response = await fetch(`/api/v1/domains/${domain}/dns/${recordId}`, {
      method: 'DELETE',
    });
    return response.json();
  },
};
```

---

## 🆕 新規ドメイン追加フロー

### 1. ドメイン購入

お名前.com、ムームードメイン等でドメインを購入

### 2. Cloudflareにドメイン追加

```bash
# Cloudflare Dashboard
https://dash.cloudflare.com/

# "Add a Site" → ドメイン名入力 → Free プラン選択
```

### 3. NSレコード変更

Cloudflareが指定するネームサーバーに変更:

```
ns1.cloudflare.com
ns2.cloudflare.com
```

**変更場所**: ドメインレジストラの管理画面（お名前.comの場合）

**反映時間**: 最大48時間（通常は数時間）

### 4. DNSレコード設定

#### A Record（WordPress用）
```
Type: A
Name: @
Content: Cloudflare Tunnel経由でDellへ
Proxy: ON（オレンジクラウド）
```

#### MX Record（メール用）
```
Type: MX
Name: @
Content: route1.mx.cloudflare.net
Priority: 85
```

### 5. 統合ポータルから確認

```bash
# Frontend: /domains ページ
# - ドメイン一覧に新規ドメインが表示される
# - DNS/SSL/メール状態が確認できる
```

---

## 🔒 セキュリティベストプラクティス

### API Token管理

1. **最小権限の原則**
   - 必要な権限のみ付与（DNS Edit + Zone Read）
   - 全ゾーンではなく、特定ゾーンのみ指定（可能な場合）

2. **IP制限**
   - Dell WorkStationの固定IPのみ許可

3. **定期ローテーション**
   - 6ヶ月〜1年ごとにトークン再発行

4. **環境変数管理**
   - `.env`ファイルは`.gitignore`に追加
   - 本番環境では環境変数または秘密管理サービス使用

### DNSレコード変更ログ

```python
# 変更履歴を記録（推奨）
async def create_dns_record_with_audit(zone_id, record, user_id):
    result = await create_dns_record(zone_id, record)

    # 監査ログ
    await audit_log.create({
        "action": "dns_record_create",
        "zone_id": zone_id,
        "record_type": record.type,
        "record_name": record.name,
        "user_id": user_id,
        "timestamp": datetime.now(),
    })

    return result
```

---

## 📊 Cloudflare料金プラン比較

| 機能 | Free | Pro ($20/月) | Business ($200/月) |
|------|------|--------------|-------------------|
| DDoS防御 | ✅ 無制限 | ✅ 無制限 | ✅ 無制限 |
| SSL/TLS | ✅ | ✅ | ✅ |
| CDN | ✅ | ✅ | ✅ |
| WAF | ⚠️ 基本 | ✅ 高度 | ✅ 高度+ |
| Rate Limiting | ❌ | ✅ | ✅ |
| Page Rules | 3個 | 20個 | 50個 |
| Custom Rules | ❌ | 20個 | 100個 |
| Bot Management | ❌ | ⚠️ 限定 | ✅ |
| **推奨度** | ✅ 現状維持可 | ✅ 推奨 | ⚠️ 過剰 |

**結論**: **Proプラン（$20/月）**へのアップグレードを推奨
- Rate Limitingでブルートフォース攻撃防御
- 高度なWAFルールでWordPress特有の攻撃防御

---

## 🛠️ トラブルシューティング

### 問題: API Token が無効

**エラー**:
```json
{
  "success": false,
  "errors": [{"code": 9109, "message": "Invalid access token"}]
}
```

**解決策**:
1. トークンが正しくコピーされているか確認
2. トークンの有効期限を確認
3. 権限設定を確認（DNS Edit + Zone Read）
4. トークンを再発行

### 問題: Zone ID が取得できない

**解決策**:
```bash
# Zone ID取得方法
curl -X GET "https://api.cloudflare.com/client/v4/zones?name=kuma8088.com" \
     -H "Authorization: Bearer YOUR_TOKEN" \
     -H "Content-Type: application/json"
```

### 問題: DNSレコード作成が失敗

**エラー例**:
```json
{
  "errors": [{"code": 81057, "message": "The record already exists."}]
}
```

**解決策**:
- 重複レコードを削除してから再作成
- または、PUT（更新）を使用

---

## 📚 参考リソース

- [Cloudflare API Documentation](https://developers.cloudflare.com/api/)
- [Cloudflare DNS API](https://developers.cloudflare.com/api/operations/dns-records-for-a-zone-list-dns-records)
- [Cloudflare Zone API](https://developers.cloudflare.com/api/operations/zones-get)
- [API Token Permissions](https://developers.cloudflare.com/fundamentals/api/get-started/create-token/)

---

## 📅 更新履歴

- 2025-11-13: 初版作成（Cloudflare API統合ガイド）
