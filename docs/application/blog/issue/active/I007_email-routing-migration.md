# I007: Cloudflare Email Routing 移行（EC2廃止）

**関連タスク**: [#007] Email Routingへの変更（EC2の廃止）
**ステータス**: Inbox
**優先度**: Medium
**作成日**: 2025-11-10
**担当**: 未割当

---

## 📋 課題概要

EC2でPostfix MX Gatewayを稼働しているが、Cloudflare Email Routingへ移行することでEC2インスタンスを廃止し、月額コストを削減する。

---

## 🎯 目標

EC2 MX Gateway廃止により、月額コスト約$5-10削減（t2.micro想定）。

---

## 📌 現状

### 現在のメールフロー
```
外部 → EC2 (MX Gateway, Postfix) → Dell (Postfix Relay) → Dovecot LMTP → Mailbox
     ↑                              ↓
     MXレコード                    SendGrid (送信)
```

### EC2構成
- インスタンスタイプ: t2.micro（推定）
- OS: Rocky Linux 9（推定）
- Postfix: Docker コンテナ
- Terraform管理: `services/mailserver/terraform/`

---

## 💡 提案される解決策

### 移行後のメールフロー
```
外部 → Cloudflare Email Routing → Dell (Postfix + Dovecot) → Mailbox
                                  ↓
                                  SendGrid (送信)
```

### Cloudflare Email Routing
- 無料プラン: 無制限の受信転送
- カスタムドメイン対応
- SPF/DKIM/DMARC対応
- Catch-all アドレス対応

---

## 📋 移行手順（案）

### Phase 1: 事前準備
- [ ] Cloudflare Email Routing 設定確認
- [ ] Dell Postfix設定変更（EC2経由なし受信対応）
- [ ] テスト環境構築

### Phase 2: DNS変更準備
- [ ] 現在のMXレコード確認
- [ ] Cloudflare Email Routing用MXレコード準備
- [ ] TTL短縮（24時間前）

### Phase 3: 移行実施
- [ ] Cloudflare Email Routing設定
- [ ] MXレコード変更
- [ ] DNS伝播確認（24-48時間）
- [ ] メール受信テスト

### Phase 4: EC2廃止
- [ ] 1週間の安定動作確認
- [ ] EC2インスタンス停止
- [ ] 2週間の監視期間
- [ ] EC2インスタンス削除
- [ ] Terraform state更新

---

## 🔧 技術的変更点

### Dell Postfix設定変更
```conf
# main.cf
# EC2からの relay_domains 削除
# Cloudflare IPレンジからの受信許可
mynetworks = 127.0.0.0/8, 172.20.0.0/24, 172.22.0.0/24, 173.245.48.0/20, 103.21.244.0/22, ...

# smtpd_recipient_restrictions 調整
smtpd_recipient_restrictions =
    permit_mynetworks,
    reject_unauth_destination
```

### Cloudflare Email Routing設定
- 転送先: Dell Postfix（Tailscale or 固定IP）
- ルール設定: ドメイン単位の転送

---

## ⚠️ リスク

### High
- メール配送遅延・損失リスク（移行期間中）
- DNSキャッシュ問題

### Medium
- Cloudflare障害時の影響
- 転送制限（1日あたり）の可能性

### 軽減策
- 段階的移行（テストドメイン先行）
- ロールバック手順準備
- 監視強化

---

## 💰 コスト試算

### Before
- EC2 t2.micro: $8.50/月（オンデマンド、東京リージョン）
- EBS: $1.00/月（8GB）
- **合計**: $9.50/月 = $114/年

### After
- Cloudflare Email Routing: $0/月（無料）
- **削減額**: $114/年

---

## 🚧 ブロッカー

- Dell Postfixへの直接受信設定変更必要
- Tailscale経由の受信可否確認

---

## 📝 次のステップ

1. Cloudflare Email Routing制限確認
2. Dell Postfix設定変更設計
3. テストドメインでPOC実施
4. 本番移行計画策定

---

## 📚 関連ドキュメント

- `docs/application/01_improvement+issue.md` - タスク#007
- `services/mailserver/terraform/` - EC2 Terraform構成
- `services/mailserver/config/postfix/main.cf.tmpl` - Postfix設定

---

## 📅 更新履歴

- 2025-11-10: Issue作成
