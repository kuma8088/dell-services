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

## 🧭 作業手順まとめ

1. **Phase 1: 事前準備**  
   - Cloudflare Email Routingの仕様や制限を確認し、Dell Postfix側でCloudflare経路を想定した設定案（`mynetworks`のIPレンジ入れ替えや`relay_domains`整理）を作成。  
   - テスト環境を用意し、Cloudflare経由のメール受信がDellで処理できるか事前検証する。
2. **Phase 2: DNS変更準備**  
   - 現行MXレコードとTTLを棚卸し、切替24時間前にはTTLを短縮。  
   - Cloudflareで利用するMX/TXTレコード値を確定し、SPF/DKIM/DMARCの整合を取る。
3. **Phase 3: 移行実施**  
   - Cloudflare Email Routingに転送先（Dell Postfix/Tailscale経路）を登録し、ルールを有効化。  
   - MXをCloudflare指定値へ切り替え、24–48時間はDNS伝播と実受信を監視しながら複数ドメインで受信テストを実施。
4. **Phase 4: EC2廃止**  
   - 1週間以上、Cloudflare経由の安定稼働を確認しつつログ監視。  
   - 問題なければEC2を停止→さらに2週間監視→削除→Terraform state反映の順でクリーンアップ。
5. **リスク対策**  
   - Cloudflare障害やDNSキャッシュ遅延に備え、段階的にドメインを移行しロールバック手順を明文化。  
   - 切替期間はDell PostfixログとCloudflareの受信統計を併せて確認し、メール損失がないかを継続チェック。

---

## 🖥️ Dell Postfix設定（コピペ用）

1. **バックアップと環境変数定義**
   ```bash
   sudo cp /etc/postfix/main.cf /etc/postfix/main.cf.bak-$(date +%Y%m%d%H%M)
   sudo cp /etc/postfix/master.cf /etc/postfix/master.cf.bak-$(date +%Y%m%d%H%M)

   MAIL_HOSTNAME="mail.webmakeprofit.org"   # DellのFQDNに置き換え
   MAIL_DOMAIN="webmakeprofit.org"          # 代表ドメインに置き換え
   RELAYHOST="[smtp.sendgrid.net]:587"      # 既存の送信リレー設定に合わせる
   VIRTUAL_DOMAINS="webmakeprofit.org,fx-trader-life.com"  # 受信対象ドメイン一覧
   ```

2. **main.cf主要パラメータの一括更新**  
   Cloudflare Email Routing経由での受信を想定し、`postconf -e`で必要箇所を上書きする。
   ```bash
   sudo postconf -e "myhostname = ${MAIL_HOSTNAME}"
   sudo postconf -e "mydomain = ${MAIL_DOMAIN}"
   sudo postconf -e "myorigin = \$mydomain"
   sudo postconf -e "mydestination = "
   sudo postconf -e "relayhost = ${RELAYHOST}"
   sudo postconf -e "virtual_mailbox_domains = ${VIRTUAL_DOMAINS}"
   sudo postconf -e 'virtual_transport = lmtp:unix:private/dovecot-lmtp'
   sudo postconf -e 'smtpd_tls_security_level = may'
   sudo postconf -e 'smtpd_recipient_restrictions = permit_mynetworks, reject_unauth_destination'
   sudo postconf -e 'smtpd_relay_restrictions = permit_mynetworks, defer_unauth_destination'
   sudo postconf -e 'smtpd_sasl_auth_enable = no'
   sudo postconf -e 'smtp_sasl_auth_enable = yes'
   sudo postconf -e 'smtp_sasl_password_maps = hash:/etc/postfix/sasl_passwd'
   sudo postconf -e 'smtp_sasl_security_options = noanonymous'
   sudo postconf -e 'smtp_tls_security_level = encrypt'
   sudo postconf -e 'smtp_tls_note_starttls_offer = yes'
   sudo postconf -e 'message_size_limit = 52428800'
   ```

3. **Cloudflare IPレンジを `mynetworks` に登録**  
   Cloudflare Email Routingの公式IPv4レンジをすべて許可し、社内ネットワークと併せて設定する。
   ```bash
   sudo postconf -e 'mynetworks = 127.0.0.0/8, 172.20.0.0/24, 172.22.0.0/24, \
   103.21.244.0/22, 103.22.200.0/22, 103.31.4.0/22, 104.16.0.0/13, 104.24.0.0/14, \
   108.162.192.0/18, 131.0.72.0/22, 141.101.64.0/18, 162.158.0.0/15, 172.64.0.0/13, \
   173.245.48.0/20, 188.114.96.0/20, 190.93.240.0/20, 197.234.240.0/22, \
   198.41.128.0/17'
   ```

4. **Cloudflare ↔ Dell 直結用の`smtpd_client_restrictions`を強化**  
   受信クライアントをCloudflare+ローカルに絞り、不正中継を防止する。
   ```bash
   sudo postconf -e 'smtpd_client_restrictions = permit_mynetworks, reject'
   ```

5. **SendGrid資格情報の確認（必要時のみ）**
   ```bash
   sudo tee /etc/postfix/sasl_passwd >/dev/null <<'EOF'
   [smtp.sendgrid.net]:587 apikey:SG.xxxxxx        # 既存のSendGrid APIキーを貼り付け
   EOF
   sudo chmod 600 /etc/postfix/sasl_passwd
   sudo postmap /etc/postfix/sasl_passwd
   ```

6. **設定のテストと再読み込み**
   ```bash
   sudo postfix check
   sudo systemctl reload postfix
   sudo postconf | egrep '^(myhostname|mynetworks|relayhost|virtual_mailbox_domains|smtpd_recipient_restrictions) ='
   ```

7. **疎通確認**
   ```bash
   # Cloudflare経由のテストメール（外部Gmail等から送信）を受信
   sudo tail -f /var/log/maillog
   ```

これらのコマンドをコピペで実行すれば、Dell側PostfixをCloudflare Email Routing前提の設定へ切り替えられる。

---

## 📚 関連ドキュメント

- `docs/application/01_improvement+issue.md` - タスク#007
- `services/mailserver/terraform/` - EC2 Terraform構成
- `services/mailserver/config/postfix/main.cf.tmpl` - Postfix設定

---

## 📅 更新履歴

- 2025-11-10: Issue作成
