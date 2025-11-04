# メールサーバー構築プロジェクト - ファイアウォール設定手順書（RX-600KI）

**文書バージョン**: 2.1
**作成日**: 2025-11-01（初版）/ 2025-11-01（v1.1改訂）/ 2025-11-01（v2.0 Tailscale VPN対応改訂）/ 2025-11-01（v2.1改訂）
**対象機器**: NTT東日本 光電話ルータ RX-600KI + Dell RockyLinux 9.6（firewalld）
**対象環境**: Dell RockyLinux 9.6 + Docker Compose + Tailscale VPN
**対象者**: ネットワーク管理者
**参照文書**: 01_requirements.md v3.0, 02_design.md v3.1

---

## ⚠️ 重要な変更（v2.0 - Tailscale VPN対応）

**Tailscale VPN前提のため、RX-600KIでのポート転送設定は原則不要です。**

### v2.0での主要変更点:
- ✅ **RX-600KIポート転送**: 不要（Port 25を除く）
- ✅ **DHCP固定割り当て**: 維持（ローカルネットワーク管理用）
- ✅ **ホストfirewalld設定**: 追加（Tailscale VPNアクセス制御）
- ✅ **Port 25（SMTP受信）**: 外部メールサーバーからの受信が必要な場合のみホスト側firewalldで許可
- ❌ **Port 465/587/993/995/80/443**: Tailscale VPN経由のみアクセス可能（ルーターポート転送不要）

### 従来構成（v1.x）との比較:

| 設定項目 | v1.x（グローバルIP公開） | v2.0（Tailscale VPN） |
|---------|-------------------------|----------------------|
| RX-600KI静的IPマスカレード | 7ポート必要 | 不要（Port 25のみ条件付き） |
| RX-600KI DHCP固定割り当て | 必要 | 必要（ローカルIP固定用） |
| ホストfirewalld設定 | 簡易設定 | Tailscale VPNアクセス制御 |
| Let's Encrypt証明書 | 必要（Port 80開放） | 不要（Tailscale HTTPS証明書） |
| A/CNAMEレコード | 必要 | 不要（MagicDNS使用） |

---

## 📋 目次

1. [設定概要](#1-設定概要)
2. [事前準備](#2-事前準備)
3. [ポート転送設定（不要化）](#3-ポート転送設定)
4. [DHCPアドレス固定割り当て](#4-dhcpアドレス固定割り当て)
5. [セキュリティ設定](#5-セキュリティ設定)
6. [設定確認](#6-設定確認)
7. [トラブルシューティング](#7-トラブルシューティング)
8. [設定バックアップ](#8-設定バックアップ)
9. [定期メンテナンス](#9-定期メンテナンス)
10. [セキュリティベストプラクティス](#10-セキュリティベストプラクティス)
11. [承認](#11-承認)

---

## 1. 設定概要

### 1.1 設定目的（Tailscale VPN前提）

**Tailscale VPNを利用したプライベートネットワークアクセス前提**のため、以下の最小限の設定のみ実施します:

- **RX-600KI DHCP固定割り当て**: メールサーバーのローカルIPアドレスを192.168.1.39に固定
- **ホストfirewalld設定**: Tailscale VPN経由のアクセス制御とPort 25（SMTP受信）の条件付き許可
- **RX-600KI静的IPマスカレード**: 不要（Tailscale VPN経由でアクセス）

### 1.2 設定対象ポート（Tailscale VPN前提）

| サービス | プロトコル | ポート | アクセス元 | RX-600KI転送 | ホストfirewalld |
|---------|-----------|-------|-----------|-------------|---------------|
| SMTP（受信） | TCP | 25 | インターネット | ❌ 不要 | ⚠️ 条件付き許可 |
| SMTP Submission | TCP | 587 | Tailscale VPN | ❌ 不要 | ✅ VPN経由のみ |
| SMTPS | TCP | 465 | Tailscale VPN | ❌ 不要 | ✅ VPN経由のみ |
| IMAPS | TCP | 993 | Tailscale VPN | ❌ 不要 | ✅ VPN経由のみ |
| POP3S | TCP | 995 | Tailscale VPN | ❌ 不要 | ✅ VPN経由のみ |
| HTTP | TCP | 80 | Tailscale VPN | ❌ 不要 | ✅ VPN経由のみ |
| HTTPS | TCP | 443 | Tailscale VPN | ❌ 不要 | ✅ VPN経由のみ |

**注記**:
- **Port 25（SMTP受信）**: 外部メールサーバーからメールを受信する場合のみ、ホスト側firewalldで許可
- **その他全ポート**: Tailscale VPN経由でのみアクセス可能（RX-600KIでのポート転送不要）

### 1.3 設定対象機器情報

| 項目 | 情報 | 備考 |
|------|------|------|
| **ルーター型番** | NTT東日本 RX-600KI | 光電話ルータ |
| **管理画面URL** | http://ntt.setup/ または http://192.168.1.1 | ブラウザからアクセス |
| **メールサーバー内部IP** | 192.168.1.39 | Dell WorkStation（Rocky Linux 9.6） |
| **メールサーバーMACアドレス** | 6c:2b:59:f0:29:f7 | `ip link show eno1` で確認 |

---

## 2. 事前準備

### 2.1 管理画面アクセス

```bash
# メールサーバー（192.168.1.39）から実行

# 1. ルーターにpingで疎通確認
ping -c 3 192.168.1.1

# 2. ブラウザで管理画面にアクセス
# URL: http://ntt.setup/ または http://192.168.1.1
```

**ログイン情報**:
- **ユーザー名**: `user` (半角英小文字)
- **パスワード**: 機器設定用パスワード（お客様にて初回設定時に登録したもの）
- ※工場出荷時はパスワード未設定。初回アクセス時に設定ウィザードで登録
- ※パスワードを忘れた場合は、ルーター本体の初期化が必要

### 2.2 メールサーバー情報確認

メールサーバー側で以下の情報を確認します。

```bash
# メールサーバーで実行

# 1. ネットワークインターフェース確認
ip addr show eno1

# 出力例:
# 2: eno1: <BROADCAST,MULTICAST,UP,LOWER_UP> mtu 1500 qdisc mq state UP group default qlen 1000
#     link/ether 6c:2b:59:f0:29:f7 brd ff:ff:ff:ff:ff:ff
#     inet 192.168.1.39/24 brd 192.168.1.255 scope global noprefixroute eno1
#        valid_lft forever preferred_lft forever

# 2. MACアドレス確認
ip link show eno1 | grep link/ether

# 出力例:
# link/ether 6c:2b:59:f0:29:f7 brd ff:ff:ff:ff:ff:ff

# 3. 現在のIPアドレス確認
ip -4 addr show eno1 | grep inet

# 出力例:
# inet 192.168.1.39/24 brd 192.168.1.255 scope global noprefixroute eno1

# 4. デフォルトゲートウェイ確認
ip route | grep default

# 出力例:
# default via 192.168.1.1 dev eno1 proto static metric 100
```

**確認事項**:
- [ ] IPアドレス: 192.168.1.39
- [ ] MACアドレス: 6c:2b:59:f0:29:f7
- [ ] ゲートウェイ: 192.168.1.1

---

## 3. ポート転送設定

Tailscale VPN 構成では、RX-600KIでのポート転送や静的IPマスカレード設定は不要です（Port 25 を含むすべてのサービスはVPN内で完結します）。

> **注意**: ここに記載していたv1.x向け静的IPマスカレード手順は廃止しました。誤って旧手順を適用しないでください。

---

## 4. DHCPアドレス固定割り当て

### 4.1 DHCP固定割り当て設定

メールサーバーのIPアドレスを固定化するため、MACアドレスベースのDHCP固定割り当てを設定します。

#### 設定手順

1. **DHCP設定画面を開く**
   - 管理画面トップページ → 「詳細設定」ボタンをクリック
   - 左側メニュー → 「DHCPv4サーバ設定」をクリック

2. **DHCP固定IPアドレス設定を開く**
   - 「DHCPv4サーバ設定」画面で「DHCP固定IPアドレス設定」ボタンをクリック

3. **固定割り当てエントリ追加**
   - 新規エントリの「編集」ボタンをクリック

4. **設定入力**
   - **MACアドレス**: `6c2b59f029f7` （コロンなし、2文字ずつ連続入力）
     - ⚠️ 注意: RX-600KIではMACアドレスをコロン区切りなしで入力
     - 入力例: 元のMAC `6c:2b:59:f0:29:f7` → 入力値 `6c2b59f029f7`
   - **IPアドレス**: `192.168.1.39`
   - 重複したMACアドレスは登録できないため、既存エントリと重複しないよう確認

5. **設定保存**
   - 「設定」ボタンをクリック
   - 確認ダイアログで「OK」

5. **メールサーバー側でネットワーク再起動**

   ```bash
   # メールサーバーで実行
   sudo nmcli connection down eno1
   sudo nmcli connection up eno1

   # IPアドレス確認
   ip -4 addr show eno1 | grep inet
   # 出力例: inet 192.168.1.39/24 brd 192.168.1.255 scope global noprefixroute eno1
   ```

6. **ルーター側で確認**
   - DHCP設定画面 → 「DHCPクライアント一覧」
   - MACアドレス `6c:2b:59:f0:29:f7` に対して `192.168.1.39` が割り当てられていることを確認

### 4.2 DHCP固定割り当て確認表

| 項目 | 値 | 備考 |
|------|-----|------|
| **MACアドレス（実際）** | 6c:2b:59:f0:29:f7 | メールサーバー eno1 |
| **MACアドレス（RX-600KI入力値）** | 6c2b59f029f7 | コロンなし連続入力 |
| **固定IPアドレス** | 192.168.1.39 | /24 (255.255.255.0) |
| **ゲートウェイ** | 192.168.1.1 | RX-600KI |
| **DNSサーバー** | 192.168.1.1 | ルーター経由 |

---

## 5. セキュリティ設定

### 5.1 パケットフィルタリング設定（オプション）

より高度なセキュリティが必要な場合、パケットフィルタリングを設定します。

#### 設定手順

1. **パケットフィルタリング画面を開く**
   - 管理画面 → 「詳細設定」→ 「セキュリティ」→ 「パケットフィルタ設定」

2. **デフォルトポリシー確認**
   - 受信: 拒否（デフォルト）
   - 送信: 許可（デフォルト）

3. **許可ルール追加（必要に応じて）**

   メールサーバーへのアクセスはTailscale VPNで制御されているため、追加ルールは不要。

### 5.2 DoS攻撃対策（RX-600KI機能確認）

RX-600KIには基本的なDoS攻撃対策機能が組み込まれています。

- **SYN Flood対策**: 有効（デフォルト）
- **Ping of Death対策**: 有効（デフォルト）
- **Land Attack対策**: 有効（デフォルト）

設定確認:
- 管理画面 → 「詳細設定」→ 「セキュリティ」→ 「DoS攻撃防御設定」

### 5.3 管理画面アクセス制限（推奨）

管理画面への不正アクセスを防ぐため、以下を実施:

1. **管理パスワード変更**
   - 管理画面 → 「メンテナンス」→ 「管理者パスワード変更」
   - 強力なパスワードに変更（12文字以上、英数記号混在）

2. **外部からの管理画面アクセス無効化**
   - 管理画面 → 「詳細設定」→ 「セキュリティ」→ 「リモート管理設定」
   - 「外部からの設定を許可する」: ✗（チェックを外す）

3. **管理画面アクセスログ確認**
   - 管理画面 → 「情報」→ 「ログ情報」
   - 定期的に不正アクセスがないか確認

### 5.4 ホストfirewalld設定（Tailscale VPN対応）

```bash
# tailscaleサービスを恒久的に許可
sudo firewall-cmd --permanent --add-service=tailscale

# メール関連サービス（VPN経由で使用）
sudo firewall-cmd --permanent --add-service=smtp
sudo firewall-cmd --permanent --add-service=submission
sudo firewall-cmd --permanent --add-service=imaps
sudo firewall-cmd --permanent --add-service=pop3s
sudo firewall-cmd --permanent --add-service=https

# 反映
sudo firewall-cmd --reload

# 設定確認
sudo firewall-cmd --list-services
```

- Port 25 を外部から受け入れる場合は、外部SMTPリレーの送信元IPを限定した rich rule を追加する。Tailnet 限定運用の場合は追加不要。 

---

## 6. 設定確認

### 6.1 ルーター側設定確認

#### チェックリスト

- [ ] RX-600KIでポート転送 / 静的IPマスカレードが無効になっている
- [ ] DHCP固定割り当て: 192.168.1.39 が設定済み
- [ ] 管理パスワード: 変更済み
- [ ] リモート管理: 無効化済み

#### 設定確認コマンド（メールサーバーから）

```bash
# 1. ゲートウェイへの疎通確認
ping -c 3 192.168.1.1

# 2. Tailscaleステータス
sudo tailscale status
sudo tailscale ip -4

# 3. tailnet内名前解決
tailscale netcheck
nslookup mail.kuma8088.com 100.100.100.100
```

### 6.2 Tailscaleクライアントからの接続確認

```bash
# クライアントPC/スマホで実行
tailscale status

# SMTP Submission
openssl s_client -connect mail.kuma8088.com:587 -starttls smtp

# IMAP
openssl s_client -connect mail.kuma8088.com:993

# HTTPS (Roundcube)
curl -k https://mail.kuma8088.com/
```

---

## 7. トラブルシューティング

### 7.1 Tailscale接続が確立できない

#### 症状
Tailscaleクライアントからメールサーバーへ到達できない、または VPN 接続が不安定

#### 確認項目

1. **Tailscaleステータス確認（ホスト側）**
   ```bash
   sudo tailscale status
   sudo tailscale ping mail.kuma8088.com
   ```

2. **ACL/ポリシー確認**
   - 管理コンソール（https://login.tailscale.com/admin/acls）で対象デバイスに対する通信が許可されているか確認

3. **firewalld設定確認**
   ```bash
   sudo firewall-cmd --list-services
   # tailscale, smtp, submission, imaps など必要サービスが登録されているか
   sudo firewall-cmd --list-ports
   ```

4. **Dockerコンテナ状態確認**
   ```bash
   cd /opt/mailserver
   docker compose ps
   ```

5. **Tailscale再起動**
   ```bash
   sudo systemctl restart tailscaled
   ```

### 7.2 DHCP固定割り当てが機能しない

#### 症状
メールサーバーのIPアドレスが変わってしまう

#### 対処方法

1. **MACアドレス確認**
   ```bash
   ip link show eno1 | grep link/ether
   # 正しいMACアドレス: 6c:2b:59:f0:29:f7
   ```

2. **DHCP設定確認**
   ```
   管理画面 → DHCPサーバ設定 → 固定割り当てエントリ
   - MACアドレスが正しいか確認
   - IPアドレスが 192.168.1.39 か確認
   ```

3. **ネットワーク再起動**
   ```bash
   sudo nmcli connection down eno1
   sudo nmcli connection up eno1
   ip -4 addr show eno1 | grep inet
   ```

4. **DHCPリース確認**
   ```
   管理画面 → DHCPサーバ設定 → DHCPクライアント一覧
   - メールサーバーが 192.168.1.39 で表示されているか確認
   ```

### 7.3 管理画面にアクセスできない

#### 症状
http://ntt.setup/ または http://192.168.1.1 にアクセスできない

#### 対処方法

1. **ネットワーク接続確認**
   ```bash
   ping -c 3 192.168.1.1
   # 疎通確認
   ```

2. **ブラウザキャッシュクリア**
   - Ctrl+Shift+Delete でキャッシュクリア
   - シークレットモードで再アクセス

3. **別のブラウザで試行**
   - Firefox, Chrome, Edge など別ブラウザで試行

4. **IPアドレス直接指定**
   - http://192.168.1.1 で直接アクセス

5. **ルーター物理再起動**
   - 電源ケーブルを抜いて30秒待機
   - 電源を入れ直して2-3分待機

### 7.4 HTTPS (Tailscale経由) にアクセスできない

#### 症状
https://mail.kuma8088.com にアクセスできない、または証明書エラー

#### 確認項目

1. **Tailscale接続確認**
   ```bash
   tailscale status
   tailscale ping mail.kuma8088.com
   ```

2. **SSL証明書確認**
   ```bash
   # メールサーバーで実行
    ls -la /var/lib/tailscale/certs/
   # mail.kuma8088.com.crt / .key が存在するか確認
   ```

3. **証明書再発行**
   ```bash
   sudo tailscale cert mail.kuma8088.com
   ```

4. **Nginx設定確認**
   ```bash
   docker compose logs nginx | grep -i error
   # エラーログ確認
   ```

5. **クライアント側確認**
   - Tailscaleクライアントが tailnet に接続されているか
   - ブラウザの信頼ストアにTailscale証明書が信頼されているか

### 7.5 メール送信できるが受信できない

#### 症状
外部SMTPリレー（SendGrid等）からメールが届かない

#### 確認項目

1. **リレーサービスの配信状態確認**
   - リレーサービスのダッシュボードで配送履歴・失敗ログを確認

2. **Postfixログ確認**
   ```bash
   docker compose logs postfix | tail -50
   # エラーメッセージ確認
   ```

3. **リレー連携設定確認**
   - Submission(587) の認証情報が正しいか
   - Postfix `relayhost` / `smtp_sasl_password_maps` の設定を確認

---

## 8. 設定バックアップ

### 9.1 ルーター設定バックアップ

定期的にルーター設定をバックアップしてください。

#### バックアップ手順

1. **管理画面ログイン**
   - http://ntt.setup/ にアクセス

2. **設定保存**
   - 「メンテナンス」→ 「設定値の保存/復元」
   - 「設定値の保存」をクリック
   - ファイル名: `RX-600KI_backup_YYYYMMDD.cfg`

3. **保存先**
   - ローカルPC: `~/Downloads/RX-600KI_backup_YYYYMMDD.cfg`
   - 外部ストレージにもコピー推奨

### 9.2 設定復元手順

設定を復元する場合:

1. **管理画面ログイン**
2. 「メンテナンス」→ 「設定値の保存/復元」
3. 「設定値の復元」→ バックアップファイル選択
4. 「復元」ボタンをクリック
5. ルーター自動再起動（約2分）

---

## 9. 定期メンテナンス

### 10.1 月次確認項目

- [ ] ポート転送設定: 7エントリが有効
- [ ] DHCP固定割り当て: 192.168.1.39 が正常
- [ ] 管理画面アクセスログ確認
- [ ] ファームウェア更新確認

### 10.2 ファームウェア更新

1. **現在のバージョン確認**
   - 管理画面 → 「情報」→ 「装置情報」
   - ファームウェアバージョン確認

2. **更新確認**
   - 管理画面 → 「メンテナンス」→ 「ファームウェア更新」
   - 「更新確認」ボタンをクリック

3. **更新実行**
   - 新しいバージョンがある場合は「更新」ボタンをクリック
   - 更新中は電源を切らない（約5-10分）

---

## 10. セキュリティベストプラクティス

### 11.1 推奨セキュリティ設定

- ✅ **管理パスワード変更**: 初期パスワードから変更済み
- ✅ **リモート管理無効化**: 外部からの管理画面アクセス無効
- ✅ **UPnP無効化**: 不要な自動ポート開放を防止
- ✅ **定期的なログ確認**: 不正アクセス監視
- ✅ **ファームウェア最新化**: セキュリティパッチ適用

### 11.2 UPnP無効化手順

UPnP（Universal Plug and Play）は自動的にポート転送を行うため、セキュリティリスクがあります。

1. **UPnP設定画面を開く**
   - 管理画面 → 「詳細設定」→ 「その他の設定」→ 「UPnP設定」

2. **UPnP無効化**
   - 「UPnP機能」: ✗（チェックを外す）
   - 「設定」ボタンをクリック

---

## 11. 承認

| 役割 | 氏名 | 設定日 | 署名 |
|------|------|--------|------|
| 設定者 |  |  |  |
| 確認者 |  |  |  |
| 承認者 |  |  |  |

---

**文書改訂履歴**

| バージョン | 日付 | 変更内容 | 作成者 |
|-----------|------|----------|--------|
| 1.0 | 2025-11-01 | 初版作成 | Claude |
| 1.1 | 2025-11-01 | 関連ドキュメント参照名を最新構成（03_installation.md / 04_testing.md）へ更新 | Codex |
| 2.0 | 2025-11-01 | Tailscale VPN対応化（ポート転送手順を非推奨化、firewalld強化、Let's Encrypt手順撤廃） | Codex |
| 2.1 | 2025-11-01 | ポート転送手順の完全削除、Tailscale接続確認手順・証明書更新手順を整備、付録をTailscale情報に刷新 | Codex |

---

## 付録A: 設定値一覧表

### A.1 Tailscaleノード情報

| 項目 | 値 |
|------|-----|
| ホスト名 | mail.kuma8088.com |
| Tailnet IP (IPv4) | 100.x.x.x（`tailscale ip -4`で確認） |
| Tailnet IP (IPv6) | fd7a:115c:a1e0:xxxx::xxxx |
| MagicDNS名 | mailserver.tailXXXXX.ts.net |
| ACLタグ | mailserver |

### A.2 DHCP固定割り当て設定

| 項目 | 値 |
|------|-----|
| MACアドレス（実際） | 6c:2b:59:f0:29:f7 |
| MACアドレス（RX-600KI入力値） | 6c2b59f029f7 （コロンなし） |
| IPアドレス | 192.168.1.39 |
| サブネットマスク | 255.255.255.0 (/24) |
| ゲートウェイ | 192.168.1.1 |
| DNSサーバー | 192.168.1.1 |

### A.3 セキュリティ設定

| 項目 | 設定値 |
|------|--------|
| 管理パスワード | 変更済み（12文字以上） |
| リモート管理 | 無効 |
| UPnP | 無効 |
| DoS攻撃防御 | 有効（デフォルト） |
| パケットフィルタ | デフォルトポリシー: 受信拒否 |

---

## 付録B: 参考情報

### B.1 RX-600KI公式情報

- **メーカー**: NTT東日本
- **製品ページ**: https://web116.jp/shop/hikari_r/rx600ki/rx600ki_00.html
- **マニュアル**: ルーター本体または公式サイトからダウンロード

### B.2 関連ドキュメント

- **要件定義書**: `01_requirements.md`
- **設計書**: `02_design.md`
- **構築手順書**: `03_installation.md`
- **テスト手順書**: `04_testing.md`

### B.3 外部リンク

- **Tailscale Docs**: https://tailscale.com/kb/
- **tailscale cert**: https://tailscale.com/kb/1153/tailscale-cert
- **tailscale ACLs**: https://tailscale.com/kb/1018/acls
