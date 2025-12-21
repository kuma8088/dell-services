# Dell メールサーバー設定 - edgeshift.tech

> **実装完了**: 2025-12-21

## 概要

EdgeShift ポートフォリオサイト (`edgeshift.tech`) のメール受信を Dell メールサーバーで処理するための設定。

Cloudflare Email Routing から `mailserver-inbound-relay` Worker 経由でメールが転送される。

## 実装結果サマリー

| 項目 | 状態 |
|------|------|
| ドメイン登録 | ✅ edgeshift.tech (id=9) |
| contact@edgeshift.tech | ✅ 作成・受信確認済み |
| info@edgeshift.tech | ✅ 作成済み |
| admin@edgeshift.tech | ✅ 作成済み |
| Postfix 設定 | ✅ virtual_mailbox_domains に登録済み |
| テストメール | ✅ Gmail → contact@ 受信成功 |

---

## 実装手順（実績）

### Phase 1: .env 更新

```bash
cd /opt/onprem-infra-system/project-root-infra/services/mailserver

# バックアップ
cp .env .env.backup.$(date +%Y%m%d_%H%M%S)

# MAIL_ADDITIONAL_DOMAINS に edgeshift.tech を追加
# 変更前: fx-trader-life.com,webmakeprofit.org,webmakesprofit.com
# 変更後: fx-trader-life.com,webmakeprofit.org,webmakesprofit.com,edgeshift.tech
```

### Phase 2: Postfix 再起動

**重要**: `docker compose restart` では .env の変更が反映されない。`up -d` でコンテナを再作成する必要がある。

```bash
docker compose up -d postfix
```

確認:
```bash
docker compose exec postfix postconf virtual_mailbox_domains
# 出力: virtual_mailbox_domains = kuma8088.com, edgeshift.tech, fx-trader-life.com, ...
```

### Phase 3: ドメイン・ユーザー作成（Web UI）

**注意**: usermgmt は REST API 未実装。Web UI のみ使用可能。

**アクセス**: `https://admin.kuma8088.com/`

#### ドメイン作成
- URL: `/domains/new`
- Domain name: `edgeshift.tech`
- Description: `EdgeShift Portfolio`
- Default quota: `2048` MB

#### ユーザー作成（3アカウント）
- URL: `/users/new`

| Email | Quota |
|-------|-------|
| contact@edgeshift.tech | 2048 MB |
| info@edgeshift.tech | 2048 MB |
| admin@edgeshift.tech | 2048 MB |

### Phase 4: 動作確認

```bash
# DB 確認
docker compose exec usermgmt python3 -c "
import sys; sys.path.insert(0, '/app')
from app import create_app
from app.services.domain_service import DomainService
app = create_app()
with app.app_context():
    d = DomainService.get_domain_by_name('edgeshift.tech')
    print(f'Domain: {d.name} (id={d.id})')
"

# メールボックス確認
docker compose exec dovecot ls -la /var/mail/vhosts/edgeshift.tech/
```

---

## メールフロー

```
外部メール → Cloudflare MX → Email Routing → mailserver-inbound-relay Worker
  → Dell mailserver-api (port 5000) → Dovecot LMTP (port 2525) → メールボックス
```

### 受信ログ例（2025-12-21 17:49）
```
mailserver-api | Inbound email received from naoya.iimura@gmail.com to contact@edgeshift.tech subject=test
mailserver-api | LMTP delivery succeeded for contact@edgeshift.tech
```

---

## メールクライアント設定

```
サーバー: mail.kuma8088.com

# IMAP（受信）
ポート: 993
暗号化: SSL/TLS
ユーザー: contact@edgeshift.tech

# SMTP（送信）
ポート: 587
暗号化: STARTTLS
ユーザー: contact@edgeshift.tech
```

**Roundcube**: `https://mail.kuma8088.com/`

---

## トラブルシューティング

### .env 変更が反映されない
```bash
# restart ではなく up -d を使用
docker compose up -d postfix
```

### usermgmt API が 404
usermgmt は Web UI のみ。REST API (`/api/domains`, `/api/users`) は未実装。

### メールが届かない
```bash
# ログ確認
docker compose logs -f mailserver-api dovecot

# Postfix ドメイン確認
docker compose exec postfix postconf virtual_mailbox_domains
```

---

## 完了チェックリスト

- [x] .env に edgeshift.tech 追加
- [x] Postfix 再起動（`up -d`）
- [x] virtual_mailbox_domains 確認
- [x] edgeshift.tech ドメイン作成
- [x] contact@edgeshift.tech 作成
- [x] info@edgeshift.tech 作成
- [x] admin@edgeshift.tech 作成
- [x] テストメール受信確認（Gmail → contact@）
