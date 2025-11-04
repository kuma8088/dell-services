# スマホ・タブレット等デバイスからのメールアクセス設計書

**バージョン**: v2.0
**作成日**: 2025-11-04
**最終更新**: 2025-11-04（v2.0改訂）
**対象システム**: Hybrid Cloud Mail Server v6.0 (EC2 + Dell)
**設計方針**: コスト最小化（追加AWS費用 $0） + TLS 1.2/1.3互換性確保

---

## 📋 目次

1. [設計概要](#1-設計概要)
2. [アーキテクチャ](#2-アーキテクチャ)
3. [コスト分析](#3-コスト分析)
4. [Tailscale VPNセットアップ](#4-tailscale-vpnセットアップ)
5. [メールクライアント設定](#5-メールクライアント設定)
6. [接続テスト](#6-接続テスト)
7. [トラブルシューティング](#7-トラブルシューティング)

---

## 1. 設計概要

### 1.1 目的

スマホ、タブレット、外出先PCなど複数デバイスから、OS標準メールクライアントでメール送受信を可能にする。

### 1.2 設計方針

- **コスト最小化**: 追加AWSリソースなし（$0）
- **セキュリティ**: Tailscale VPN経由のみアクセス許可
- **複数デバイス対応**: スマホ、タブレット、PC全て対応
- **既存インフラ活用**: Dell WorkStationの既存Dovecot/Postfix設定を流用

### 1.3 利用プロトコル

| プロトコル | ポート | 用途 | サーバー |
|-----------|--------|------|---------|
| **IMAPS** | 993 | メール受信（暗号化） | Dell Dovecot |
| **Submission** | 587 | メール送信（STARTTLS） | Dell Postfix |
| **Tailscale VPN** | - | VPN経由プライベート接続 | Dell/各デバイス |

### 1.4 メールクライアント互換性要件

**対応OS・バージョン**:

| プラットフォーム | 最小バージョン | 推奨バージョン | 対応クライアント |
|----------------|--------------|--------------|----------------|
| **iOS** | iOS 11+ | iOS 15+ | Mail.app |
| **Android** | Android 7+ | Android 11+ | Gmail, 標準メール |
| **macOS** | macOS 10.12+ | macOS 12+ | Mail.app, Thunderbird |
| **Windows** | Windows 10+ | Windows 11 | Outlook, Thunderbird |

**TLS/SSL要件**:

| 項目 | 要件 | 説明 |
|-----|------|------|
| **TLS最小バージョン** | TLS 1.2以上 | TLS 1.0/1.1は非対応 |
| **TLS Cipher Suite** | 8種類対応 | ECDHE-ECDSA, ECDHE-RSA, ChaCha20-Poly1305, DHE-RSA |
| **証明書** | Let's Encrypt（Tailscale経由） | 初回接続時に承認必要 |

**重要な接続要件**:

⚠️ **必須**: Tailscale VPNホスト名 `dell-workstation.tail67811d.ts.net` を使用すること
- IPアドレス（`100.110.222.53`）での接続は**不可**
- MagicDNS が有効になっている必要がある
- 初回接続時にTLS証明書の承認が必要

---

## 2. アーキテクチャ

### 2.1 全体構成図

```
┌─────────────────────────────────────────────────────────────────┐
│ Internet                                                        │
│                                                                 │
│  ┌────────────┐   ┌─────────────┐   ┌──────────────┐         │
│  │ iPhone     │   │ Android     │   │ PC (外出先)  │         │
│  │ Tailscale  │   │ Tailscale   │   │ Tailscale    │         │
│  └─────┬──────┘   └──────┬──────┘   └──────┬───────┘         │
│        │                  │                  │                  │
└────────┼──────────────────┼──────────────────┼──────────────────┘
         │                  │                  │
         │ Tailscale VPN Network (100.x.x.x/8)│
         │                  │                  │
         └──────────────────┴──────────────────┘
                            │
                ┌───────────▼──────────────┐
                │ Dell WorkStation         │
                │ (100.110.222.53)         │
                │                          │
                │ ┌──────────────────────┐ │
                │ │ Dovecot              │ │
                │ │ - IMAPS:993          │ │◄─── メール受信
                │ │ - POP3S:995          │ │
                │ │ - LMTP:2525          │ │
                │ └──────────────────────┘ │
                │                          │
                │ ┌──────────────────────┐ │
                │ │ Postfix              │ │
                │ │ - Submission:587     │ │◄─── メール送信
                │ │ - SendGrid Relay     │ │
                │ └──────────────────────┘ │
                │                          │
                └──────────────────────────┘
```

### 2.2 通信フロー

#### 受信フロー
```
【外部からの受信】
外部送信者 → EC2 MX Gateway (SMTP:25)
           → Dell Dovecot (LMTP:2525) → メールボックス

【デバイスでの受信】
デバイス → Tailscale VPN → Dell Dovecot (IMAPS:993) → メール取得
```

#### 送信フロー
```
デバイス → Tailscale VPN → Dell Postfix (Submission:587)
        → SendGrid → 外部受信者
```

---

## 3. コスト分析

### 3.1 追加コスト: **$0/月**

| 項目 | 既存リソース | 追加コスト |
|-----|-------------|-----------|
| **Dell Dovecot IMAPS/POP3S** | 既存稼働中 | $0 |
| **Dell Postfix Submission** | 既存稼働中 | $0 |
| **Tailscale VPN** | 既存稼働中 (Dell + EC2) | $0 |
| **Tailscale デバイス追加** | 無料プラン (最大100デバイス) | $0 |

**合計追加コスト**: **$0/月**

### 3.2 既存システムコスト（参考）

- EC2 t4g.micro (MX Gateway): ~$3.02/月
- SendGrid Free (100通/日): $0
- **総コスト**: ~$3.02/月 (変更なし)

---

## 4. Tailscale VPNセットアップ

### 4.1 前提条件

- Tailscale アカウント（既存）
- Dell WorkStation がTailscaleネットワークに参加済み（100.110.222.53）

### 4.2 iOS (iPhone/iPad) セットアップ

#### ステップ1: アプリインストール
```
1. App Store を開く
2. "Tailscale" で検索
3. 「Tailscale」アプリをインストール
4. アプリを起動
```

#### ステップ2: VPN接続
```
1. 「Log in」をタップ
2. Tailscaleアカウントでログイン（Google/Microsoft等）
3. VPN構成の追加を許可
4. 「Connect」をタップ
5. 接続成功を確認（画面上部にVPNアイコン表示）
```

#### ステップ3: Dell接続確認
```
1. Safari で http://100.110.222.53 にアクセス
2. Roundcube ログイン画面が表示されればOK
```

### 4.3 Android セットアップ

#### ステップ1: アプリインストール
```
1. Google Play Store を開く
2. "Tailscale" で検索
3. 「Tailscale」アプリをインストール
4. アプリを起動
```

#### ステップ2: VPN接続
```
1. 「Log in」をタップ
2. Tailscaleアカウントでログイン
3. VPN接続を許可
4. 「Connect」をタップ
5. 通知バーにVPNアイコン表示を確認
```

#### ステップ3: Dell接続確認
```
1. Chrome で http://100.110.222.53 にアクセス
2. Roundcube ログイン画面が表示されればOK
```

### 4.4 macOS セットアップ

#### ステップ1: アプリインストール
```bash
# Homebrew経由（推奨）
brew install --cask tailscale

# または公式サイトからダウンロード
# https://tailscale.com/download/mac
```

#### ステップ2: VPN接続
```
1. Tailscale アプリを起動
2. メニューバーのTailscaleアイコンをクリック
3. 「Log in」を選択
4. ブラウザでログイン
5. "Connected" 表示を確認
```

#### ステップ3: Dell接続確認
```bash
# ターミナルで実行
ping 100.110.222.53
# 応答があればOK
```

### 4.5 Windows セットアップ

#### ステップ1: アプリインストール
```
1. https://tailscale.com/download/windows からインストーラーダウンロード
2. TailscaleSetup.exe を実行
3. インストール完了
```

#### ステップ2: VPN接続
```
1. タスクトレイのTailscaleアイコンをクリック
2. 「Log in」を選択
3. ブラウザでログイン
4. "Connected" 表示を確認
```

#### ステップ3: Dell接続確認
```cmd
# コマンドプロンプトで実行
ping 100.110.222.53
# 応答があればOK
```

---

## 5. メールクライアント設定

### 5.1 iPhone Mail 設定

#### アカウント追加手順

```
1. 設定 → メール → アカウント → アカウントを追加
2. 「その他」→「メールアカウントを追加」
3. 以下を入力:
   名前: （任意の表示名）
   メール: test@kuma8088.com
   パスワード: （Dovecot usersファイルで設定したパスワード）
   説明: kuma8088 Mail
4. 「次へ」をタップ
```

#### 受信メールサーバー設定（IMAP）

```
ホスト名: dell-workstation.tail67811d.ts.net
ユーザ名: test@kuma8088.com
パスワード: （Dovecot パスワード）
```

**詳細設定**:
```
1. 設定 → メール → アカウント → kuma8088 Mail → アカウント
2. 「IMAP」をタップ
3. 「受信メールサーバー」→「詳細」
   - SSLを使用: ON
   - 認証: パスワード
   - サーバーポート: 993
```

#### 送信メールサーバー設定（SMTP）

```
ホスト名: dell-workstation.tail67811d.ts.net
ユーザ名: test@kuma8088.com
パスワード: （Dovecot パスワード）
```

**詳細設定**:
```
1. 「送信メールサーバー」→「SMTP」→「プライマリサーバ」
2. 「詳細」をタップ
   - SSLを使用: OFF
   - 認証: パスワード
   - サーバーポート: 587
```

### 5.2 Android Gmail アプリ設定

#### アカウント追加手順

```
1. Gmail アプリを開く
2. メニュー → 設定 → アカウントを追加
3. 「その他」を選択
4. メールアドレス入力: test@kuma8088.com
5. 「個人用（IMAP）」を選択
```

#### 受信サーバー設定

```
サーバー: dell-workstation.tail67811d.ts.net
ポート: 993
セキュリティの種類: SSL/TLS
ユーザー名: test@kuma8088.com
パスワード: （Dovecot パスワード）
```

#### 送信サーバー設定

```
サーバー: dell-workstation.tail67811d.ts.net
ポート: 587
セキュリティの種類: STARTTLS
ユーザー名: test@kuma8088.com
パスワード: （Dovecot パスワード）
```

### 5.3 macOS Mail 設定

#### アカウント追加手順

```
1. Mail.app を起動
2. メール → アカウントを追加
3. 「その他のメールアカウント」→ 続ける
4. 以下を入力:
   名前: （任意の表示名）
   メールアドレス: test@kuma8088.com
   パスワード: （Dovecot パスワード）
5. 「サインイン」をクリック
```

#### 受信設定まとめ（IMAP）

| 設定項目 | 値 |
|---------|-----|
| **アカウントの種類** | IMAP |
| **メールサーバー** | dell-workstation.tail67811d.ts.net |
| **ユーザ名** | test@kuma8088.com |
| **パスワード** | （Dovecot パスワード） |
| **ポート** | 993 |
| **TLS/SSLを使用** | チェック（必須） |
| **認証** | パスワード |

**設定方法**:
1. Mail → 環境設定 → アカウント → 該当アカウント選択
2. 「アカウント情報」タブで基本情報を入力
3. 「詳細」タブでポート・SSL設定を変更

**重要**: TailscaleホストMail名 `dell-workstation.tail67811d.ts.net` を使用すること（IPアドレス不可）

#### 送信設定まとめ（SMTP）

| 設定項目 | 値 |
|---------|-----|
| **SMTPサーバー** | dell-workstation.tail67811d.ts.net |
| **ユーザ名** | test@kuma8088.com |
| **パスワード** | （Dovecot パスワード） |
| **ポート** | 587 |
| **TLS/SSLを使用** | チェック（STARTTLS） |
| **認証** | パスワード |

**設定方法**:
1. Mail → 環境設定 → アカウント → 該当アカウント選択
2. 「送信用メールサーバ (SMTP)」→ 「SMTPサーバリストを編集」
3. プライマリサーバーを選択して設定を変更

**重要**: Tailscaleホスト名 `dell-workstation.tail67811d.ts.net` を使用すること（IPアドレス不可）

### 5.4 Microsoft Outlook 設定

#### Windows/Mac 共通手順

```
1. Outlook を起動
2. ファイル → アカウントの追加
3. 「手動セットアップまたは追加のサーバーの種類」→ 次へ
4. 「POP または IMAP」を選択 → 次へ
```

#### 設定内容

**ユーザー情報**:
```
名前: （任意の表示名）
電子メールアドレス: test@kuma8088.com
```

**サーバー情報**:
```
アカウントの種類: IMAP
受信メールサーバー: dell-workstation.tail67811d.ts.net
送信メールサーバー (SMTP): dell-workstation.tail67811d.ts.net
```

**ログオン情報**:
```
ユーザー名: test@kuma8088.com
パスワード: （Dovecot パスワード）
```

#### 詳細設定

```
1. 「詳細設定」ボタンをクリック
2. 「送信サーバー」タブ:
   - 「送信サーバー (SMTP) は認証が必要」: チェック
   - 「受信メールサーバーと同じ設定を使用する」: チェック

3. 「詳細設定」タブ:
   受信サーバー (IMAP): 993
   このサーバーでは暗号化された接続 (SSL/TLS) が必要: チェック

   送信サーバー (SMTP): 587
   使用する暗号化接続の種類: TLS
```

---

## 6. 接続テスト

### 6.1 VPN接続テスト

#### すべてのデバイスで実行

**iOS/Android**:
```
1. Safariまたは Chrome で http://100.110.222.53 にアクセス
2. Roundcube ログイン画面が表示されることを確認
3. ログインしてメール一覧が表示されることを確認
```

**macOS/Windows**:
```bash
# ターミナル/コマンドプロンプトで実行
ping 100.110.222.53
# 応答があればOK

# IMAPS ポート確認（macOS/Linux）
nc -zv dell-workstation.tail67811d.ts.net 993
# Connection succeeded と表示されればOK

# SMTP Submission ポート確認
nc -zv dell-workstation.tail67811d.ts.net 587
# Connection succeeded と表示されればOK
```

### 6.2 メール受信テスト

#### テストメール送信（Dell側から実行）

```bash
# Dell WorkStation で実行
echo "Test mail from Dell" | sudo docker exec -i mailserver-postfix \
  sendmail -f test@kuma8088.com test@kuma8088.com

# Dell Dovecot ログ確認
sudo docker logs mailserver-dovecot --tail 20 | grep "saved mail"
# "saved mail to INBOX" と表示されればOK
```

#### デバイス側で受信確認

```
1. メールクライアントで「メールを受信」を実行
2. テストメールが受信トレイに表示されることを確認
3. メール本文が正しく表示されることを確認
```

### 6.3 メール送信テスト

#### デバイスから送信

```
1. メールクライアントで新規メール作成
2. 宛先: test@kuma8088.com（自分宛て）
3. 件名: Test from [デバイス名]
4. 本文: テスト送信
5. 送信
```

#### Dell側で配信確認

```bash
# Dell Postfix ログ確認
sudo docker logs mailserver-postfix --tail 30 | grep "status=sent"
# "status=sent (250 2.0.0 Ok: queued as ...)" と表示されればOK

# Dell Dovecot 配信確認
sudo docker logs mailserver-dovecot --tail 20 | grep "saved mail"
# "saved mail to INBOX" と表示されればOK
```

#### デバイスで受信確認

```
1. 送信したメールクライアントで「メールを受信」を実行
2. 送信したテストメールが受信トレイに届いていることを確認
```

---

## 7. トラブルシューティング

### 7.1 Tailscale VPN 接続エラー

#### 症状: VPNに接続できない

**確認項目**:
```
1. Tailscaleアプリでログイン状態を確認
2. デバイス認証が完了しているか確認（Tailscale Admin Console）
3. ネットワーク接続を確認（Wi-Fi/モバイルデータ）
```

**対処法**:
```
1. Tailscaleアプリを再起動
2. デバイスを再起動
3. Tailscaleアプリを再インストール
4. Tailscale Admin Console でデバイスを削除→再認証
```

#### 症状: 100.110.222.53 に ping が通らない

**確認項目**:
```bash
# Dell WorkStation で Tailscale 状態確認
sudo tailscale status
# dell-workstation の行に "active" と表示されているか確認
```

**対処法**:
```bash
# Dell側でTailscale再起動
sudo systemctl restart tailscaled
sudo tailscale up

# Dell側でfirewalld確認
sudo firewall-cmd --list-all
# tailscale0 がtrustedゾーンにあるか確認
```

### 7.2 IMAP受信エラー

#### 症状: 「メールサーバーに接続できません」

**確認項目**:
```
1. Tailscale VPN が接続されているか確認
2. サーバー設定が正しいか確認:
   - サーバー: dell-workstation.tail67811d.ts.net
   - ポート: 993
   - SSL/TLS: 有効
```

**対処法**:
```bash
# Dell側でDovecot稼働確認
sudo docker ps | grep mailserver-dovecot
# "Up" と表示されていればOK

# Dell側でIMAPポート確認
sudo docker exec mailserver-dovecot ss -tuln | grep :993
# "LISTEN" と表示されていればOK

# Dell側でDovecotログ確認
sudo docker logs mailserver-dovecot --tail 50 | grep -i error
# エラーがあれば内容を確認
```

#### 症状: 認証エラー（パスワード拒否）

**確認項目**:
```
1. ユーザー名が完全なメールアドレス形式か確認 (test@kuma8088.com)
2. パスワードが正しいか確認
```

**対処法**:
```bash
# Dell側でユーザー登録確認
sudo docker exec mailserver-dovecot cat /etc/dovecot/users
# test@kuma8088.com の行が存在するか確認

# パスワード再設定が必要な場合
sudo docker exec -it mailserver-dovecot bash
doveadm pw -s SHA512-CRYPT
# 新しいパスワードのハッシュをコピー

# /etc/dovecot/users を編集して再起動
sudo docker restart mailserver-dovecot
```

### 7.3 SMTP送信エラー

#### 症状: 「送信メールサーバーに接続できません」

**確認項目**:
```
1. サーバー設定が正しいか確認:
   - サーバー: dell-workstation.tail67811d.ts.net
   - ポート: 587
   - SSL/TLS: STARTTLS (または「使用」)
   - 認証: 有効
```

**対処法**:
```bash
# Dell側でPostfix稼働確認
sudo docker ps | grep mailserver-postfix
# "Up" と表示されていればOK

# Dell側でSMTP Submissionポート確認
sudo docker exec mailserver-postfix ss -tuln | grep :587
# "LISTEN" と表示されていればOK

# Dell側でPostfixログ確認
sudo docker logs mailserver-postfix --tail 50 | grep -i error
```

#### 症状: リレーアクセス拒否（Relay access denied）

**原因**: Postfix の mynetworks 設定にTailscaleネットワークが含まれていない

**対処法**:
```bash
# Dell側で docker-compose.yml の Postfix環境変数を確認
cat /opt/onprem-infra-system/project-root-infra/services/mailserver/docker-compose.yml | grep POSTFIX_mynetworks

# 以下が含まれているか確認:
# - POSTFIX_mynetworks=172.20.0.0/24, 100.0.0.0/8

# 設定変更が必要な場合はdocker-compose.ymlを編集して再起動
sudo docker-compose -f /opt/onprem-infra-system/project-root-infra/services/mailserver/docker-compose.yml restart postfix
```

### 7.4 証明書エラー

#### 症状: 「TLS証明書なし」または「証明書が信頼できません」

**原因**: Tailscale Let's Encrypt証明書の承認が必要、またはIPアドレスで接続している

**重要な前提条件**:
- ⚠️ **必ずTailscaleホスト名を使用**: `dell-workstation.tail67811d.ts.net`
- ❌ **IPアドレスは不可**: `100.110.222.53` では証明書エラーになる

**証明書情報**:
```
CN: dell-workstation.tail67811d.ts.net
SAN: DNS:dell-workstation.tail67811d.ts.net
発行者: Let's Encrypt (E8)
有効期限: 2026年1月31日（自動更新）
```

**対処法**:

**1. ホスト名確認（全デバイス共通）**:
```
サーバー設定で以下を確認:
✅ 正: dell-workstation.tail67811d.ts.net
❌ 誤: 100.110.222.53
❌ 誤: dell-workstation
```

**2. 初回接続時の証明書承認**:

**iOS/macOS**:
```
1. 初回接続時に「証明書を検証できません」と表示される
2. 証明書の詳細を確認:
   - CN が dell-workstation.tail67811d.ts.net であることを確認
   - 発行者が Let's Encrypt であることを確認
3. 「信頼する」をタップ/クリック
```

**Android**:
```
1. 初回接続時に証明書警告が表示される
2. 「詳細を表示」で証明書情報を確認
3. 「承認」をタップ
```

**3. Tailscale VPN接続確認**:
```bash
# デバイスでTailscale VPNが接続されているか確認
# iOS/Android: Tailscaleアプリで "Connected" 表示
# macOS/Windows: ターミナル/コマンドプロンプトで実行
ping dell-workstation.tail67811d.ts.net
# 応答があればMagicDNSが正常動作
```

### 7.5 デバイス別の一般的な問題

#### iPhone/iPad

**問題**: バックグラウンドでメールが受信されない

**対処法**:
```
1. 設定 → メール → アカウント → データの取得方法
2. 「プッシュ」を有効化
3. または「フェッチ」間隔を15分に設定
```

#### Android Gmail

**問題**: 同期エラーが頻繁に発生

**対処法**:
```
1. Gmail設定 → アカウント → 同期オプション
2. 「Wi-Fi接続時のみ同期」をOFFに変更
3. Tailscale VPN がバックグラウンドで常時接続されているか確認
```

#### macOS Mail

**問題**: 送信済みメールが二重に保存される

**対処法**:
```
1. Mail → 環境設定 → アカウント → メールボックスの特性
2. 「送信済みメールボックスをサーバに保存」: チェックを外す
```

---

## 8. セキュリティ考慮事項

### 8.1 Tailscale VPN セキュリティ

**利点**:
- End-to-End暗号化（WireGuardプロトコル）
- デバイス認証必須（未認証デバイスは接続不可）
- アクセスログ記録（Tailscale Admin Console）
- IP制限（100.x.x.x プライベートネットワークのみ）

**推奨設定**:
```
1. Tailscale Admin Console でデバイス一覧を定期確認
2. 不要なデバイスは削除
3. 2段階認証（2FA）を有効化
4. デバイス名を識別可能な名前に変更（例: iPhone-Personal, iPad-Work）
```

### 8.2 メール認証セキュリティ

**現状の認証方式**:
- Dovecot: PLAIN/LOGIN 認証（TLS暗号化通信内）
- Postfix: SASL 認証（STARTTLS暗号化）

**推奨事項**:
```
1. 強力なパスワード設定（16文字以上、英数字記号混在）
2. デバイス紛失時は即座にパスワード変更
3. デバイス本体のロック設定（パスコード/生体認証）
4. メールクライアントのパスワード保存は端末のキーチェーン利用
```

### 8.3 デバイス紛失時の対応手順

```
1. Tailscale Admin Console にログイン
2. 紛失デバイスを「Disable」に設定（即座にVPN接続切断）
3. Dell側でメールパスワード変更
4. 必要に応じてメール転送ルール設定を確認
5. デバイス発見後、Tailscale再認証とパスワード再設定
```

---

## 9. 運用上の注意事項

### 9.1 Tailscale VPN の常時接続

**推奨設定**:
```
すべてのデバイスでTailscale VPNを常時接続（Always-On）に設定
→ バックグラウンドメール受信が安定化
```

**iOS設定**:
```
設定 → 一般 → VPNとデバイス管理 → VPN
→ Tailscale を選択 → 「オンデマンド接続」を有効化
```

**Android設定**:
```
設定 → ネットワークとインターネット → VPN
→ Tailscale → 設定アイコン → 「常時接続VPN」を有効化
```

### 9.2 バッテリー消費

**Tailscale VPN常時接続によるバッテリー影響**:
- iOS: 約5-10%/日の追加消費
- Android: 約10-15%/日の追加消費

**対処法**:
```
1. 低電力モード時は手動でVPN接続
2. 夜間は自動切断（Tailscale設定）
3. モバイルデータ通信時のみVPN無効化（設定で制御）
```

### 9.3 Dell WorkStation メンテナンス時の影響

**Dell再起動時**:
```
1. すべてのデバイスでメール送受信が一時停止
2. Dell起動後、Tailscale/Docker自動起動（約2-3分）
3. デバイス側は再設定不要（自動復旧）
```

**長期メンテナンス時の代替手段**:
```
Dell停止中はRoundcube（Webメール）も利用不可
→ EC2経由のメール受信のみ継続（Dell復旧後に配信される）
```

---

## 10. 付録

### 10.1 各種設定ファイル参照

| 設定項目 | ファイルパス（Dell WorkStation） |
|---------|--------------------------------|
| Dovecot設定 | `services/mailserver/config/dovecot/dovecot.conf` |
| Dovecotユーザー | `services/mailserver/config/dovecot/users` |
| Postfix設定 | `services/mailserver/config/postfix/main.cf.tmpl` |
| Docker Compose | `services/mailserver/docker-compose.yml` |
| Tailscale状態 | `sudo tailscale status` |

### 10.2 よくある質問（FAQ）

**Q1: 複数のメールアドレスを使いたい**

A: Dell側で追加ユーザーを作成し、各デバイスで複数アカウント設定可能。

```bash
# Dell側でユーザー追加
sudo docker exec -it mailserver-dovecot bash
doveadm pw -s SHA512-CRYPT
# ハッシュ値をコピー

# /etc/dovecot/users に追加
newuser@kuma8088.com:{SHA512-CRYPT}ハッシュ値::::::

sudo docker restart mailserver-dovecot
```

**Q2: 外出先でVPN接続が不安定**

A: モバイルデータ通信の安定性に依存。以下を試す:

```
1. Tailscale接続プロトコルを変更（UDP → TCP）
2. Tailscale "Derp Map" で最寄りリレーサーバーに接続
3. 一時的にWi-Fi環境に移動
```

**Q3: メール送信が遅い**

A: Dell → SendGrid → 外部受信者のルートで遅延が発生する可能性。

```
通常: 数秒〜30秒程度
遅延時: SendGridキュー処理待ち（最大5分）

対処法:
- SendGrid ログを確認（https://app.sendgrid.com/）
- Dell Postfix ログでリレー状態を確認
```

### 10.3 関連ドキュメント

- **要件定義**: `Docs/application/mailserver/01_requirements.md` (v6.0)
- **システム設計**: `Docs/application/mailserver/02_design.md` (v6.0)
- **インストール手順**: `Docs/application/mailserver/04_installation.md`
- **TLS Cipher Suite問題**: `services/mailserver/troubleshoot/MAIL_CLIENT_LOGIN_FAILURE_2025-11-04.md`
- **EC2プロトコル問題**: `services/mailserver/troubleshoot/EC2_MAIL_PROTOCOL_ISSUE_2025-11-04.md`
- **Fargate版トラブルシューティング**: `services/mailserver/troubleshoot/INBOUND_MAIL_FAILURE_2025-11-03.md`

---

## 改訂履歴

| バージョン | 日付 | 変更内容 | 作成者 |
|-----------|------|----------|--------|
| 1.0 | 2025-11-04 | 初版作成（コスト最小化設計、Tailscale VPN経由） | Claude |
| 2.0 | 2025-11-04 | **TLS互換性要件追加・証明書情報修正** | Claude |

**v2.0 主要変更点（v1.0からの改訂）:**
- **メールクライアント互換性要件追加**: iOS 11+, Android 7+, macOS 10.12+ 等の最小バージョン明記
- **TLS/SSL要件明確化**: TLS 1.2以上、8種類のCipher Suite対応
- **証明書情報修正**: Tailscale Let's Encrypt証明書（自己署名ではない）
- **ホスト名要件強調**: IPアドレス不可、Tailscaleホスト名必須
- **トラブルシューティング強化**: 証明書エラー対処法を正確な情報に更新
- **関連文書参照追加**: TLS Cipher Suite トラブルシューティング文書へのリンク
