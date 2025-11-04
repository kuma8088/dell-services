# メールクライアント設定ガイド（ユーザーガイド）

📱 **クライアント側 / ユーザー向けドキュメント**

このディレクトリには、スマホ・タブレット・外出先PCなどのデバイスから、Hybrid Cloud Mail Serverにアクセスするための**ユーザーガイド**が格納されています。

⚠️ **サーバー構築・管理者向けドキュメントではありません** → `../04_installation.md` を参照

## 📁 ファイル一覧

| ファイル | 内容 | 対象者 |
|---------|------|--------|
| **01_device_access_design.md** | メールクライアント設定ガイド（v2.0） | **エンドユーザー**、システム管理者 |

## 🎯 利用目的

複数デバイスからOS標準メールクライアント（iPhone Mail, Android Gmail, macOS Mail, Outlook等）で、メール送受信を可能にする設定ガイドを提供します。

## 🔐 アクセス方式

**Tailscale VPN経由のプライベートアクセス**

- 追加AWSコスト: **$0/月**
- セキュリティ: End-to-End暗号化（WireGuard）
- 複数デバイス対応: スマホ、タブレット、PC全て対応

## 📱 対応デバイス

- **iOS**: iPhone, iPad
- **Android**: スマートフォン、タブレット
- **macOS**: MacBook, iMac
- **Windows**: ノートPC、デスクトップPC

## 📧 対応プロトコル

| プロトコル | ポート | 用途 |
|-----------|--------|------|
| IMAPS | 993 | メール受信（暗号化） |
| Submission | 587 | メール送信（STARTTLS） |

## 🔐 TLS/SSL要件

**v2.0 で追加された互換性要件**:

| 項目 | 要件 |
|-----|------|
| **TLS最小バージョン** | TLS 1.2以上 |
| **対応OS** | iOS 11+, Android 7+, macOS 10.12+, Windows 10+ |
| **TLS Cipher Suite** | 8種類対応（ECDHE-ECDSA, ECDHE-RSA, ChaCha20-Poly1305, DHE-RSA） |
| **証明書** | Let's Encrypt（Tailscale経由） |
| **ホスト名要件** | Tailscaleホスト名必須（IPアドレス不可） |

⚠️ **重要**: 接続時は必ず `dell-workstation.tail67811d.ts.net` を使用してください（IPアドレス不可）

## 🚀 クイックスタート

1. **01_device_access_design.md** を開く
2. 「4. Tailscale VPNセットアップ」でVPN接続
3. 「5. メールクライアント設定」でメールアカウント追加
4. 「6. 接続テスト」で動作確認

## 🔗 関連ドキュメント

**ユーザー向け**:
- **TLSトラブルシューティング**: `../../../services/mailserver/troubleshoot/MAIL_CLIENT_LOGIN_FAILURE_2025-11-04.md`

**管理者向け**:
- システム設計: `../02_design.md` (v6.0)
- サーバー構築・運用ガイド: `../04_installation.md` (v6.0)
- トラブルシューティング全般: `../../../services/mailserver/troubleshoot/`

---

**ドキュメント管理**:
- 作成日: 2025-11-04
- 最終更新: 2025-11-04（v2.0 - TLS互換性要件追加）
