# メールサーバー構築プロジェクト - 要件定義書

**文書バージョン**: 5.0
**作成日**: 2025-10-31（初版）/ 2025-10-31（v2.0改訂）/ 2025-10-31（v2.1改訂）/ 2025-11-01（v3.0改訂）/ 2025-11-01（v4.0改訂）/ 2025-11-01（v5.0改訂）
**対象環境**: AWS Fargate（MXゲートウェイ） + Dell RockyLinux 9.6（メール本体） + Tailscale VPN
**プロジェクト種別**: 個人利用（Tailscale VPNプライベートアクセス + AWS Fargate MXゲートウェイ）
**構築方式**: AWS ECS Fargate Postfix（MX） + Dell Docker Compose（Dovecot/Roundcube） + SendGrid SMTP Relay（送信）

---

## 1. プロジェクト概要

### 1.1 目的
Xserver WEBメール機能相当のメールサーバーを**AWS Fargate（MXゲートウェイ）+ Dell RockyLinux 9.6（メール本体）のハイブリッド構成**で構築し、**Tailscale VPNネットワーク経由**でメールの送受信およびWEBメール管理を可能にする。

**アーキテクチャの特徴**:
- **AWS Fargate**: インターネットからのメール受信（Port 25）を担当するサーバーレスMXゲートウェイ
- **Dell RockyLinux**: Tailscaleプライベートネットワーク内でメールボックス管理・WEBメール提供
- **SendGrid SMTP Relay**: 外部への送信メールを担当（Port 587/TLS認証）
- **Tailscale VPN**: FargateとDell間、およびクライアント-Dell間の安全な通信経路

### 1.2 適用範囲
- **個人利用専用**：Tailscale VPNプライベートネットワークでのアクセスに限定し、Dell環境への直接公開を回避
- **サーバーレスMX**: AWS Fargateで常時稼働のEC2インスタンスを不要にし、運用コストを削減
- **SMTP送信分離**: SendGridを利用して送信ドメイン認証（SPF/DKIM/DMARC）をクラウド側で管理
- 初級管理者でも運用可能な自動化されたシステムを構築する
- 将来的な拡張（ユーザー数・ドメイン数増加）に対応可能な設計とする

### 1.3 参照ドキュメント
- `/Docs/application/mailserver/xserver-mail-function` - Xserver WEBメール機能仕様
- `/CLAUDE.md` - プロジェクトインフラ構成・既存Docker環境仕様

---

## 2. 機能要件

### 2.1 必須機能

#### 2.1.1 メール送受信機能
| 機能ID | 機能名 | 詳細 | 優先度 |
|--------|--------|------|--------|
| F-001 | SMTP送信 | Tailscale経由でのSMTP over TLS (Port 587) → SendGrid SMTP Relay | 🔴 必須 |
| F-002 | IMAP受信 | Tailscale経由でのIMAP over TLS (Port 993) | 🔴 必須 |
| F-003 | POP3受信 | Tailscale経由でのPOP3 over TLS (Port 995) | 🔴 必須 |
| F-004 | スマホ対応 | Tailscaleクライアントを介したiOS/Androidメールアプリ接続 | 🔴 必須 |
| F-005 | 外部メール受信 | AWS Fargate MXゲートウェイでPort 25受信 → Tailscale転送 | 🔴 必須 |

#### 2.1.2 WEBメール機能
| 機能ID | 機能名 | 詳細 | 優先度 |
|--------|--------|------|--------|
| F-101 | ブラウザアクセス | Tailscale経由HTTPSでのWEBメール利用 | 🔴 必須 |
| F-102 | 新規作成・返信・転送 | 基本的なメール操作 | 🔴 必須 |
| F-103 | 添付ファイル | 最大25MB添付ファイル対応（超過時は安全な外部共有を案内） | 🔴 必須 |
| F-104 | アドレス帳 | 連絡先管理機能 | 🟡 推奨 |
| F-105 | 日本語対応 | UI日本語表示 | 🔴 必須 |

#### 2.1.3 複数ドメイン対応
| 機能ID | 機能名 | 詳細 | 優先度 |
|--------|--------|------|--------|
| F-201 | マルチドメイン | 複数ドメインでのメールアドレス作成 | 🔴 必須 |
| F-202 | ドメイン追加 | 設定変更による柔軟なドメイン追加 | 🔴 必須 |
| F-203 | ドメイン別管理 | ドメインごとのユーザー管理 | 🟡 推奨 |

#### 2.1.4 セキュリティ機能
| 機能ID | 機能名 | 詳細 | 優先度 |
|--------|--------|------|--------|
| F-301 | SSL/TLS暗号化 | 全通信の暗号化 | 🔴 必須 |
| F-302 | SPF設定 | SendGrid管理の送信ドメイン認証（SPF） | 🔴 必須 |
| F-303 | DKIM署名 | SendGrid管理のDomainKeys Identified Mail | 🔴 必須 |
| F-304 | DMARC設定 | SendGrid管理のドメインベース認証・報告・適合 | 🔴 必須 |
| F-305 | スパムフィルタ | Rspamd等による迷惑メール自動振り分け | 🔴 必須 |
| F-306 | ウイルスチェック | ClamAV等による添付ファイルのウイルススキャン | 🔴 必須 |
| F-307 | Fargate VPN接続 | AWS FargateからTailscaleプライベートネットワークへの安全な転送 | 🔴 必須 |

### 2.2 運用機能要件

#### 2.2.1 自動化機能
| 機能ID | 機能名 | 詳細 | 優先度 |
|--------|--------|------|--------|
| F-401 | 自動証明書更新 | Tailscale HTTPS証明書自動発行・更新 | 🔴 必須 |
| F-402 | ログローテーション | Dockerログドライバー設定 + CloudWatch Logs（Fargate） | 🔴 必須 |
| F-403 | セキュリティ更新 | コンテナイメージ定期更新（Dell + Fargate） | 🔴 必須 |
| F-404 | バックアップ | Docker volumeの日次バックアップ（Dell側のみ） | 🔴 必須 |
| F-405 | ヘルスチェック | コンテナ死活監視・自動再起動（Dell + Fargate） | 🔴 必須 |
| F-406 | アラート通知 | ヘルスチェック失敗時にメール/チャットへ通知 | 🔴 必須 |
| F-407 | Fargate自動スケーリング | ECS Service Auto Scalingによるタスク数調整 | 🟡 推奨 |

#### 2.2.2 管理機能
| 機能ID | 機能名 | 詳細 | 優先度 |
|--------|--------|------|--------|
| F-501 | ユーザー管理 | メールアカウント追加・削除（Dell側） | 🔴 必須 |
| F-502 | ドメイン管理 | ドメイン追加・削除（Dell + SendGrid DNS設定） | 🔴 必須 |
| F-503 | 容量管理 | メールボックス容量確認（Dell側） | 🟡 推奨 |
| F-504 | SendGrid管理 | API Key管理、送信ドメイン認証設定 | 🔴 必須 |

---

## 3. 非機能要件

### 3.1 性能要件

| 項目 | 要件 | 備考 |
|------|------|------|
| **メール処理量** | 100通/日 | 初期想定 |
| **同時接続数** | 5名 | 初期ユーザー数 |
| **メールボックス容量** | 2,000MB/ユーザー | 1ユーザーあたり |
| **添付ファイルサイズ** | 最大25MB/メール | 送受信とも |
| **レスポンス時間** | WEBメール: 3秒以内 | 画面遷移時 |
| **メール配信時間** | 5分以内 | 通常時 |
| **Fargate起動時間** | 30秒以内 | コールドスタート時 |
| **SendGrid配信時間** | 3分以内 | 外部送信時 |

### 3.2 可用性要件

| 項目 | 要件 | 備考 |
|------|------|------|
| **稼働時間** | ベストエフォート | ヘルスチェック+通知で検知 |
| **Fargate可用性** | AWS SLA準拠（99.99%） | ECS Service Auto Scaling有効化 |
| **メンテナンス時間** | 深夜時間帯（自動） | 2:00-4:00 JST |
| **バックアップ頻度** | 日次（推奨） | 深夜時間帯（Dell側のみ） |
| **復旧目標時間（RTO）** | 4時間以内 | 手動復旧 |
| **復旧目標時点（RPO）** | 24時間以内 | データ損失許容範囲 |

### 3.3 拡張性要件

| 項目 | 初期値 | 拡張目標 |
|------|--------|----------|
| **ユーザー数** | 5名 | 50名まで対応可能 |
| **ドメイン数** | 1-3個 | 10個まで対応可能 |
| **メール処理量** | 100通/日 | 1,000通/日まで対応可能 |
| **メールボックス容量** | 2GB/ユーザー | 10GB/ユーザーまで拡張可能 |
| **Fargateタスク数** | 1タスク | Auto Scaling最大5タスク |

### 3.4 セキュリティ要件

| カテゴリ | 要件 | 実装方法 |
|----------|------|----------|
| **通信暗号化** | 全プロトコルSSL/TLS必須 | Tailscale HTTPS証明書（自動発行） |
| **認証** | パスワード認証 | PLAIN/LOGIN over TLS |
| **ネットワークアクセス制御** | Tailscale VPN経由のみ | TailscaleプライベートネットワークでIP制限 |
| **送信ドメイン認証** | SPF/DKIM/DMARC設定 | SendGrid DNS設定（自動管理） |
| **Fargate-Dell間通信** | Tailscale VPN暗号化トンネル | Fargateコンテナ内Tailscaleクライアント |
| **コンテナ分離** | 各サービス独立コンテナ | Docker Composeネットワーク分離 |
| **Secret管理** | パスワード・認証情報保護 | `.env`（600権限）+ AWS Secrets Manager（Fargate） |
| **非rootコンテナ** | root権限最小化 | コンテナ内非rootユーザー実行 |
| **パスワードポリシー** | 8文字以上推奨 | 管理者が設定 |
| **ログ保存** | 30日間保存 | CloudWatch Logs（Fargate） + Dockerログドライバー（Dell） |
| **SendGrid API Key** | 環境変数保護 | AWS Secrets Manager統合 |

### 3.5 運用性要件

| 項目 | 要件 | 備考 |
|------|------|------|
| **管理者技術レベル** | 初級 | Docker基本コマンド実行可能 |
| **監視** | Dockerヘルスチェック + 外部監視スクリプト + CloudWatch Alarms | RTO/RPO達成のために必須 |
| **アラート** | メール/チャット通知を自動送信 | 重大アラートは即時通知 |
| **ドキュメント** | 構築・運用手順書完備 | Docker Compose環境前提 + Fargate構築手順 |
| **自動化** | 最大限自動化 | cron + docker composeコマンド + AWS CLI |
| **リソース管理** | コンテナリソース制限 | CPU/メモリ上限設定必須（Dell + Fargate） |
| **Fargateコスト管理** | 使用量ベース課金 | CloudWatch Cost Explorer監視 |

### 3.6 互換性要件

| カテゴリ | 要件 | 対応 |
|----------|------|------|
| **メールクライアント** | 標準プロトコル対応 | IMAP/POP3/SMTP |
| **WEBブラウザ** | Chrome, Firefox, Safari, Edge | 最新版および1世代前 |
| **スマートフォン** | iOS Mail, Android Gmail | 標準メールアプリ |
| **文字コード** | UTF-8, ISO-2022-JP | 日本語対応 |

---

## 4. システム制約

### 4.1 ハードウェア環境

#### 4.1.1 Dell RockyLinux（メール本体）
| 項目 | 仕様 |
|------|------|
| **サーバー** | Dell WorkStation (6 cores/12 threads, 32GB RAM) |
| **OS** | Rocky Linux 9.6 |
| **ネットワーク** | eno1: 192.168.1.39/24 (ホストOS) + Tailscale VPN |
| **コンテナ基盤** | Docker Engine + Docker Compose (Phase 3完了) |
| **ストレージ** | /data/docker: 3.6TB HDD (メールデータ用) |
| **バックアップ** | /mnt/backup: 外付けHDD (週次バックアップ) |

#### 4.1.2 AWS Fargate（MXゲートウェイ）
| 項目 | 仕様 |
|------|------|
| **プラットフォーム** | AWS ECS Fargate（サーバーレス） |
| **タスク定義** | CPU: 256 (.25 vCPU), Memory: 512 MB |
| **コンテナイメージ** | bokysan/postfix:latest + tailscale/tailscale:stable |
| **ネットワーク** | AWS VPC（パブリックサブネット） + Tailscale VPN |
| **Public IP** | Elastic IP（固定IP推奨）または Dynamic IP（DNS自動更新必要） |
| **ログ** | CloudWatch Logs（30日保存） |

### 4.2 ネットワーク環境（Tailscale VPN + AWS Fargate前提）

| 項目 | 前提条件 | 必要対応 |
|------|----------|----------|
| **Tailscale VPN** | Tailscaleアカウント取得 | Dell + Fargateコンテナに Tailscaleインストール |
| **Tailscale認証** | デバイス認証済み | 管理者デバイス + Fargate + Dellを Tailscaleネットワークに追加 |
| **MagicDNS** | Tailscale MagicDNS有効化 | Dell: `mailserver.tailXXXXX.ts.net` / Fargate: `fargate-mx.tailXXXXX.ts.net` |
| **AWS VPC** | Fargateデプロイ用VPC | パブリックサブネット + インターネットゲートウェイ |
| **ALB（Application Load Balancer）** | Port 25 SMTP受信 | Fargate ECS Serviceにリンク |
| **DNS管理** | DNS管理権限あり | CloudflareでMX, SPF, DKIM, DMARCレコード設定 |
| **MXレコード** | ALB DNSを指定 | `example.com. MX 10 alb-fargate-XXXXXX.ap-northeast-1.elb.amazonaws.com` |
| **逆引き(PTR)** | 不要（SendGrid送信） | SendGrid管理ドメインが送信元 |
| **送信リレー** | 必須（SendGrid SMTP Relay） | SendGrid API Key + ドメイン認証設定 |
| **ドメイン** | 取得済みドメインあり | メール受信用にDNS設定（MX → ALB） |
| **既存インフラ** | KVM+Docker環境稼働中 | 既存ネットワークと共存 |

### 4.3 必要ポート一覧

#### 4.3.1 AWS Fargate（MXゲートウェイ）
| ポート | プロトコル | 用途 | アクセス元 | 公開要否 |
|--------|-----------|------|-----------|----------|
| 25 | SMTP | インターネットからのメール受信 | インターネット（ALB経由） | ✅ 公開必須 |
| 41641 | UDP | Tailscale VPN | Tailscale coordination server | ✅ 公開必須 |

#### 4.3.2 Dell RockyLinux（メール本体）
| ポート | プロトコル | 用途 | アクセス元 | 公開要否 |
|--------|-----------|------|-----------|----------|
| 465 | SMTPS | SMTP over TLS（Tailscale） | Tailscaleクライアント | ❌ VPN内のみ |
| 587 | Submission | SMTP認証送信（Tailscale） | Tailscaleクライアント | ❌ VPN内のみ |
| 993 | IMAPS | IMAP over TLS（Tailscale） | Tailscaleクライアント | ❌ VPN内のみ |
| 995 | POP3S | POP3 over TLS（Tailscale） | Tailscaleクライアント | ❌ VPN内のみ |
| 80 | HTTP | Tailscale HTTPS証明書失効監視 | Tailscaleクライアント | ❌ VPN内のみ |
| 443 | HTTPS | WEBメール | Tailscaleクライアント | ❌ VPN内のみ |
| 2525 | LMTP | Fargate → Dell メール転送 | Tailscale VPN（Fargate） | ❌ VPN内のみ |
| 41641 | UDP | Tailscale VPN | Tailscale coordination server | ✅ 公開必須 |

#### 4.3.3 SendGrid SMTP Relay（外部送信）
| ポート | プロトコル | 用途 | アクセス元 | 公開要否 |
|--------|-----------|------|-----------|----------|
| 587 | SMTP/TLS | 認証付きSMTP送信 | Dell RockyLinux | ✅ 送信のみ |

### 4.4 構築方式制約

#### 4.4.1 Dell RockyLinux（メール本体）
| 項目 | 制約内容 |
|------|----------|
| **構築方式** | Docker Compose（既存Docker環境活用） |
| **ネットワーク** | Docker bridge network + host port mapping |
| **ストレージ** | /data/docker/volumes/mailserver (HDD, 大容量) |
| **既存サービス** | なし（新規構築） |
| **バックアップ先** | /mnt/backup/mailserver/ (日次自動バックアップ) |

#### 4.4.2 AWS Fargate（MXゲートウェイ）
| 項目 | 制約内容 |
|------|----------|
| **デプロイ方式** | ECS Task Definition + ECS Service |
| **ネットワーク** | awsvpc（パブリックサブネット） + Tailscale overlay |
| **ストレージ** | なし（ステートレス設計、メール即時転送） |
| **ログ** | CloudWatch Logs（30日保存） |
| **Secret管理** | AWS Secrets Manager（Tailscale Auth Key, SendGrid API Key） |

---

## 5. 前提条件・制約事項

### 5.1 前提条件

1. **ネットワーク環境**
   - Tailscaleアカウントが用意されていること
   - Dell RockyLinuxホストでTailscaleクライアントを動作させられること
   - AWS Fargateコンテナ内でTailscaleクライアントを動作させられること
   - 利用端末（PC/スマホ）がTailscaleネットワークに参加できること
   - インターネット回線とルーター管理権限があること

2. **AWS環境**
   - AWSアカウントが用意されていること
   - VPC、サブネット、インターネットゲートウェイが設定可能であること
   - ECS Fargate、Application Load Balancer、CloudWatch Logsの利用権限があること
   - AWS Secrets Managerでシークレット管理が可能であること

3. **SendGrid SMTP Relay**
   - SendGridアカウントが用意されていること
   - SendGrid API Keyを取得できること
   - 送信ドメイン認証（SPF/DKIM/DMARC）設定が可能であること

4. **ドメイン管理**
   - メールアドレスに独自ドメインを利用する場合、MX/SPF/DKIM/DMARCレコードを設定できること
   - MXレコードでALB DNS名を指定できること

5. **サーバー環境**
   - Rocky Linux 9.6が稼働していること
   - Docker環境が構築済みであること（Phase 3完了）
   - Docker Composeが利用可能であること
   - /data/docker ストレージが利用可能であること
   - root権限またはsudo権限があること

6. **管理者スキル**
   - LinuxのCLI基本操作ができること
   - Docker基本コマンド（docker, docker compose）が使用できること
   - AWS CLI基本操作ができること
   - テキストエディタ（vi/nano）を使用できること
   - SSH接続ができること

### 5.2 制約事項

1. **Fargate制約**
   - ステートレス設計（メール保存不可、即時Dell転送）
   - Tailscale VPN接続が必須（Dellへの転送経路）
   - Port 25受信のみ対応（送信はSendGrid経由）

2. **SendGrid制約**
   - 送信ドメイン認証設定が必須（SPF/DKIM/DMARC）
   - 送信量制限あり（プランに応じて100通/日〜）
   - API Key管理が必要

3. **監視・アラート**
   - 専用監視サービスは導入しない（コスト抑制のため）
   - Dockerヘルスチェック + CloudWatch Alarms + 外部スクリプトで死活監視を実施
   - 障害検知時はメール/チャットへ自動通知する

4. **バックアップ**
   - Dell側のみ日次自動バックアップを実施
   - Fargate側はステートレス（バックアップ不要）
   - バックアップ先は /mnt/backup/mailserver/
   - 外部クラウドストレージへの転送は将来的な拡張

5. **スパム・ウイルス対策**
   - 初期構成にRspamd（スパム）とClamAV（ウイルス）を組み込む（Dell側）
   - チューニングや学習データの更新は運用フェーズで継続実施

6. **コンテナリソース**
   - 各コンテナにメモリ・CPU制限を設定
   - Dell: ホストリソースの70%までを上限とする
   - Fargate: タスク定義で256 CPU / 512 MB Memory固定

---

## 6. 技術スタック（概要）

### 6.1 推奨構成（ハイブリッド構成）

#### 6.1.1 AWS Fargate（MXゲートウェイ）
| コンポーネント | コンテナイメージ | 役割 | 公開ポート |
|----------------|------------------|------|------------|
| **MTA** | bokysan/postfix:latest | SMTP受信専用（Port 25） | 25（Public IP経由） |
| **VPN Client** | tailscale/tailscale:stable | Tailscale VPN接続 | 41641/udp |

**ECS Fargate構成:**
- タスク定義: CPU 256 (.25 vCPU), Memory 512 MB
- ネットワークモード: awsvpc
- ロードバランサー: Application Load Balancer（Port 25 SMTP）
- ログ: CloudWatch Logs（30日保存）
- Secret: AWS Secrets Manager（Tailscale Auth Key）

#### 6.1.2 Dell RockyLinux 9.6（メール本体）
| コンポーネント | コンテナイメージ | 役割 | 公開ポート |
|----------------|------------------|------|------------|
| **MDA** | dovecot/dovecot:2.3.21 | IMAP/POP3サーバー | 993, 995 |
| **Webmail** | roundcube/roundcubemail:1.6.7-apache | WEBメールUI | (内部) |
| **Database** | mariadb:10.11.7 | ユーザーDB・RoundcubeDB | (内部) |
| **Webserver** | nginx:1.26-alpine | リバースプロキシ・SSL終端 | 80, 443 |
| **SMTP送信** | bokysan/postfix:latest | SendGrid SMTP Relay送信 | (内部→587) |
| **DKIM** | （Postfix内蔵） | DKIM署名（bokysan/postfixに統合） | (内部) |
| **スパムフィルタ** | rspamd/rspamd:3.8 | スパム検出・振り分け | (内部) |
| **ウイルスチェック** | clamav/clamav:1.3 | ウイルススキャン | (内部) |

**Docker Compose構成:**
- ネットワーク: mailserver_network (bridge)
- ボリューム: maildata, maildb, letsencrypt, postfix-config, dovecot-config
- 永続化: /data/docker/volumes/mailserver/
- バックアップ: /mnt/backup/mailserver/ (日次)

#### 6.1.3 SendGrid SMTP Relay（外部送信）
| 項目 | 設定値 |
|------|--------|
| **SMTP Server** | smtp.sendgrid.net |
| **Port** | 587（TLS認証） |
| **認証方式** | PLAIN（API Key使用） |
| **送信ドメイン認証** | SPF/DKIM/DMARC（SendGrid管理） |

### 6.2 構築方式（ハイブリッド構成）

**選定理由:**
- **AWS Fargate**: サーバーレスでEC2インスタンス管理不要、Port 25受信のみに特化
- **SendGrid**: 送信ドメイン認証の自動管理、ISPブロック回避、送信レピュテーション管理
- **Dell Docker Compose**: 既存Docker環境（Phase 3）を活用、メールボックス管理・WEBメール提供
- **Tailscale VPN**: Fargate-Dell間の安全な通信経路、グローバルIP不要

**実装方針:**
- AWS Fargate: ECS Task Definition + ECS Service + ALB構成
- Dell: Docker Composeでマルチコンテナ構成
- Tailscale: Fargate + Dell両方にTailscaleクライアントインストール
- SendGrid: Dell PostfixからPort 587/TLS経由で送信
- 環境変数・シークレット: AWS Secrets Manager（Fargate） + .env（Dell）

---

## 7. 成功基準

### 7.1 機能面

- ✅ インターネットからのメールをFargateで受信し、DellへTailscale経由で転送できる
- ✅ DellからSendGrid経由で外部へメール送信ができる
- ✅ スマートフォンからTailscale VPN経由でメールの送受信ができる
- ✅ ブラウザからWEBメールにアクセスしてメール操作ができる
- ✅ 複数ドメインでメールアドレスを作成できる
- ✅ SSL/TLS暗号化通信が行われている
- ✅ SendGrid管理のSPF/DKIM/DMARCが正しく設定されている

### 7.2 運用面

- ✅ SSL証明書が自動更新される（Tailscale HTTPS証明書）
- ✅ ログが適切にローテーションされる（CloudWatch Logs + Dockerログドライバー）
- ✅ 管理者が簡単にユーザーを追加・削除できる
- ✅ 構築手順書に従って初級者が再構築できる
- ✅ ヘルスチェック失敗時に管理者へ自動通知される
- ✅ Fargate MXゲートウェイが自動スケーリングされる（必要時）

### 7.3 性能面

- ✅ WEBメール画面の表示が3秒以内
- ✅ メール送受信が5分以内に完了
- ✅ 5名が同時にアクセスしても問題なく動作
- ✅ Fargate起動時間が30秒以内

---

## 8. リスク管理

### 8.1 識別されたリスク

| リスクID | リスク内容 | 影響度 | 発生確率 | 対策 |
|----------|-----------|--------|----------|------|
| R-001 | SendGrid SMTP Relay障害 | 🔴 高 | 低 | 複数SMTPリレーサービス契約・障害時の手動迂回手順整備 |
| R-002 | Fargate-Dell間Tailscale接続断 | 🔴 高 | 低 | ヘルスチェック・自動再接続・アラート通知 |
| R-003 | AWS Fargate障害 | 🔴 高 | 低 | AWS SLA準拠・複数AZ構成（将来的） |
| R-004 | スパムブラックリスト登録 | 🟡 中 | 低 | SendGrid送信レピュテーション管理・送信量制限 |
| R-005 | Dell側ディスク容量不足 | 🟡 中 | 低 | Docker volume容量監視、古いメール削除 |
| R-006 | コンテナ障害時のサービス停止 | 🟡 中 | 中 | ヘルスチェック・自動再起動設定（Dell + Fargate） |
| R-007 | 初級管理者での運用困難 | 🟡 中 | 中 | 詳細な運用手順書・トラブルシューティング作成 |
| R-008 | バックアップ失敗によるデータ損失 | 🔴 高 | 低 | 日次バックアップ+検証スクリプト（Dell側） |
| R-009 | SendGrid送信量超過 | 🟡 中 | 低 | 送信量監視・プランアップグレード手順整備 |
| R-010 | AWS Secrets Manager障害 | 🟡 中 | 低 | シークレットローテーション・バックアップ手順整備 |

### 8.2 対応優先順位

1. **最優先**: R-001（SendGridリレー障害）、R-002（Tailscale接続断）、R-008（バックアップ失敗）
2. **高優先**: R-003（Fargate障害）、R-004（スパム対策）、R-006（コンテナ障害）
3. **中優先**: R-005（容量管理）、R-007（運用ドキュメント）、R-009（送信量超過）、R-010（Secrets Manager障害）

---

## 9. 次のステップ

1. ✅ **要件定義書作成完了** （本ドキュメント - AWS Fargate + Dell + SendGrid + Tailscale前提）
2. ⏳ **設計書作成** (`02_design.md`)
   - AWS Fargateシステム構成図（ECS + ALB + CloudWatch）
   - Dell Docker Composeシステム構成図
   - Tailscale VPNネットワーク設計（Fargate-Dell接続）
   - SendGrid SMTP Relay統合設計
   - コンテナネットワーク設計
   - ボリューム・永続化設計（Dell側のみ）
   - セキュリティ設計（コンテナ分離・Secrets管理）
   - データフロー図（インターネット → Fargate → Dell → SendGrid）
3. ⏳ **構築手順書作成** (`04_installation.md`)
   - 前提条件確認（Tailscaleアカウント・AWSアカウント・SendGridアカウント・Docker環境・ドメイン）
   - AWS環境構築（VPC/サブネット/IGW/ALB/ECS Cluster）
   - Fargate Task Definition作成（Postfix + Tailscale）
   - ECS Service作成（ALB統合 + Auto Scaling）
   - SendGrid設定（API Key取得・ドメイン認証設定）
   - Dell docker-compose.yml作成
   - 各コンテナ設定ファイル作成
   - Tailscale証明書取得・デバイス認証（Fargate + Dell）
   - コンテナ起動・初期設定
4. ⏳ **テスト手順書作成** (`05_testing.md`)
   - 機能テスト（SMTP受信/IMAP/POP3/Webmail/SendGrid送信）
   - セキュリティテスト（SPF/DKIM/DMARC）
   - コンテナヘルスチェック検証（Dell + Fargate）
   - バックアップ・リストアテスト（Dell側）
   - Tailscale VPN接続テスト（Fargate-Dell間）
   - SendGrid送信テスト

---

## 10. 承認

| 役割 | 氏名 | 承認日 | 署名 |
|------|------|--------|------|
| 要件作成者 | Claude | 2025-11-01 | ✓ |
| プロジェクトオーナー |  | 2025-11-01 | ✓ (承認チェック完了) |

---

**文書改訂履歴**

| バージョン | 日付 | 変更内容 | 作成者 |
|-----------|------|----------|--------|
| 1.0 | 2025-10-31 | 初版作成 | Claude |
| 2.0 | 2025-10-31 | Docker前提・固定IP前提への全面改訂 | Claude |
| 2.1 | 2025-10-31 | セキュリティ・運用要件強化、DNS管理方式をRoute53/Cloudflareに統一 | Claude |
| 3.0 | 2025-11-01 | Tailscale VPN前提への全面改訂（個人利用プライベートアクセス化） | Claude |
| 4.0 | 2025-11-01 | ハイブリッド構成改訂（AWS EC2 + Dell RockyLinux + Tailscale VPN） | Claude |
| 5.0 | 2025-11-01 | サーバーレス化改訂（AWS Fargate + Dell + SendGrid + Tailscale VPN） | Claude |

**v5.0 主要変更点（v4.0からの改訂）:**
- **AWS EC2 → AWS Fargate移行**: サーバーレス化によりホスト管理不要、使用量ベース課金でコスト最適化
- **SendGrid SMTP Relay追加**: 外部送信専用にSendGridを採用、Dell側はPort 587/TLS経由で送信
- **送信ドメイン認証管理**: SPF/DKIM/DMARCをSendGridで自動管理、運用負荷削減
- **ステートレス設計**: Fargateはメール保存せず即時Dell転送、障害時の影響範囲を最小化
- **Elastic IP削除**: MXレコードはALB DNS名を指定、固定IP不要でコスト削減
- **DNS要件変更**: `example.com. MX 10 alb-fargate-XXXXXX.ap-northeast-1.elb.amazonaws.com`
- **ログ管理強化**: CloudWatch Logs（Fargate 30日保存）+ Dockerログドライバー（Dell）
- **Secret管理更新**: AWS Secrets Manager（Fargate用Tailscale Auth Key, SendGrid API Key）
- **リスク管理更新**: R-001（SendGridリレー障害）、R-009（送信量超過）、R-010（Secrets Manager障害）を追加
- **コスト構造変化**: EC2固定費 → Fargate変動費 + SendGrid従量課金でコスト最適化
