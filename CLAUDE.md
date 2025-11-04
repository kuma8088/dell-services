# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

---

## 📋 プロジェクト概要（日本語サマリー）

**目的**: Dell WorkStation (Rocky Linux 9.6) 上で KVM ベースの AWS VPC シミュレーション環境を構築し、段階的に Docker コンテナオーケストレーション環境へ移行するインフラ構築プロジェクト

**特徴**:
- **ドキュメント駆動型リポジトリ**: 実行可能な手順書を Git 管理、アプリケーションコードは含まない
- **フェーズ別構築**: KVM/仮想ネットワーク → Docker 環境 → サービスデプロイメント
- **将来的な AWS 移行**: Terraform + AWS MGN による段階的クラウド移行を想定

**ハードウェア制約**:
- CPU: 6コア/12スレッド、メモリ: 32GB、ストレージ: 3.6TB HDD + 390GB SSD
- VM リソース: 最大 8 vCPU (1:2 オーバーコミット)、24GB RAM (70% 上限)

**ネットワーク構成**: AWS VPC 相当の 5 セグメント構成 (Management/Public/Private/Database/Container)
- 詳細は後述の「Network Architecture」セクション参照

**進行状況**:
- ✅ Phase 1-2: KVM + 仮想ネットワーク完了
- 🔄 Phase 3: Docker インフラ構築中
- 🔄 Application: Mailserver (EC2 v6.0) 運用中

**重要な参照ドキュメント**:
- 📖 インフラ手順書: [Docs/infra/procedures/README.md](Docs/infra/procedures/README.md)
- 📧 Mailserver: [Docs/application/mailserver/README.md](Docs/application/mailserver/README.md)
- 🔧 Terraform: [services/mailserver/terraform/README.md](services/mailserver/terraform/README.md)

---

## 🚨 重要な作業ルール

### 1. インフラ構成変更前の公式ドキュメント確認（必須）

**CRITICAL RULE**: KVM/libvirt/ネットワーク/ストレージ構成を変更する際は、必ず公式ドキュメントを WebFetch で確認してください。

```bash
# 推奨確認手順
1. WebFetch で公式ドキュメントを取得
   - LibVirt XML format: https://libvirt.org/formatnetwork.html
   - KVM networking: https://wiki.libvirt.org/Networking.html
   - Rocky Linux docs: https://docs.rockylinux.org/

2. 現在の設定を確認
   sudo virsh net-dumpxml <network>  # ネットワーク設定
   sudo virsh dumpxml <vm>           # VM 設定
   nmcli connection show             # NetworkManager 状態

3. 変更を適用（テスト → 検証 → 本番）
```

**理由**: インフラの誤設定は本番障害に直結します。ポート番号・ネットワークレンジ・サービス動作を仮定せず、常に実態を確認してください。

### 2. SSH ポート設定

**絶対禁止**: Port 22 の使用
**必須**: セグメント別ポート範囲 (2201-2280) を使用

| セグメント | SSH ポート範囲 |
|-----------|---------------|
| Management | 2201-2210 |
| Public | 2211-2230 |
| Private | 2231-2250 |
| Database | 2251-2260 |
| Container | 2261-2280 |

### 3. 手順書の扱い

- **実行前**: 必ず手順書全体を読み、前提条件・期待される出力・ロールバック手順を確認
- **実行中**: コマンド実行結果を記録、期待値と異なる場合は停止して原因調査
- **実行後**: バリデーション実施、結果を Git コミット

詳細: [Docs/infra/procedures/README.md](Docs/infra/procedures/README.md)

---

## 📂 リポジトリ構造

```
project-root-infra/
├── Docs/
│   ├── infra/
│   │   ├── procedures/          # フェーズ別手順書（Phase 1-6）
│   │   ├── infra-specs/         # KVM インフラ要件定義
│   │   └── docker-specs/        # Docker インフラ要件定義
│   └── application/
│       └── mailserver/          # Mailserver アプリケーション仕様
├── services/
│   └── mailserver/              # Mailserver Docker Compose + Terraform
├── AGENTS.md                    # 注: 別プロジェクトの AI ツール参照（本リポジトリとは無関係）
├── CLAUDE.md                    # 本ファイル
└── README.md                    # プロジェクト概要
```

---

## 🌐 Network Architecture

### Phase 2+ Production Networks (AWS VPC Equivalent)

すべてのネットワークは libvirt type=nat + dnsmasq (DNS/DHCP) で構成:

| Segment | CIDR | Gateway | DHCP Range | SSH Ports | Domain |
|---------|------|---------|------------|-----------|--------|
| Management | 10.0.0.0/24 | 10.0.0.1 | 10.0.0.10-50 | 2201-2210 | lab.local |
| Public | 10.0.1.0/24 | 10.0.1.1 | 10.0.1.100-200 | 2211-2230 | lab.local |
| Private | 10.0.2.0/24 | 10.0.2.1 | 10.0.2.100-200 | 2231-2250 | lab.local |
| Database | 10.0.3.0/24 | 10.0.3.1 | Static IP only | 2251-2260 | lab.local |
| Container | 10.0.4.0/24 | 10.0.4.1 | 10.0.4.100-200 | 2261-2280 | lab.local |

**ルーティングルール**:
- Management → 全セグメント（フルアクセス）
- Public → Private, Database, Container
- Private → Database, Container
- Database → **他セグメントへのアウトバウンド禁止**（セキュリティ隔離）
- 全セグメント → インターネット (NAT 経由)

**重要**: Phase 1 の `default` ネットワーク (192.168.122.0/24) は Phase 2 で廃止済み

---

## 🚀 実装フェーズとステータス

### Phase 1: Minimal KVM Environment (✅ COMPLETED)
- 手順書: `procedures/2.1-rocky-linux-kvm-host-setup.md`
- 完了条件: test-vm 起動、ネットワーク接続、コンソールアクセス確認

### Phase 2: AWS VPC Network Simulation (✅ COMPLETED)
- 手順書: `procedures/2.2-virtual-network-setup.md`
- 完了条件: 5 セグメント稼働、ルーティング検証、default ネットワーク停止

### Phase 3: Docker Infrastructure Setup (🔄 IN PROGRESS)
- **手順書**:
  - `Docs/infra/procedures/3-docker/3.1-docker-environment-setup.md`
  - `Docs/infra/procedures/3-docker/3.2-storage-backup-setup.md`
  - `Docs/infra/procedures/3-docker/3.3-monitoring-security-setup.md`
  - `Docs/infra/procedures/3-docker/3.4-infrastructure-validation.md`
- **ストレージ構成**:
  - システムデータ: 50GB (SSD `/var/lib/docker`)
  - ボリューム/イメージ: 3.6TB (HDD `/data/docker`)
  - バックアップ: 外付け HDD (`/mnt/backup`) 週次 rsync
- **完了条件**: Docker 稼働、ストレージ構成完了、監視/セキュリティベースライン確立、バリデーションテスト合格

### Phase 4-5: Resource Management & Terraform (未着手)
- KVM リソースマネージャー (VM/ストレージ自動化)
- Terraform ステート生成と GitHub 統合

### Phase 6+: Service Deployment (一部進行中)
- Webmail サービスコンテナ化 (🔄 進行中 - Mailserver Application 参照)
- ブログ移行、商用サービス開発環境構築

---

## 📧 Mailserver Application (🔄 IN PROGRESS)

**現行バージョン**: v6.0 (EC2-based MX Gateway)

**アーキテクチャ**: ハイブリッドクラウドメールサーバー (AWS EC2 + Dell オンプレミス + SendGrid)
- v6.0 (EC2): 稼働中 - ホストレベル Tailscale 統合
- v5.1 (Fargate): 廃止 (VPN ネットワーク隔離問題のため)

**コスト試算**: 約 $4.81/月 (AWS)

**主要ドキュメント**:
- アーキテクチャ/セットアップ: [Docs/application/mailserver/README.md](Docs/application/mailserver/README.md)
- EC2 実装: [Docs/application/mailserver/04_EC2Server.md](Docs/application/mailserver/04_EC2Server.md)
- サービス構成: [services/mailserver/README.md](services/mailserver/README.md)
- Terraform 操作: [services/mailserver/terraform/README.md](services/mailserver/terraform/README.md)
- トラブルシュート: `services/mailserver/troubleshoot/` 配下の各 .md ファイル

**移行コンテキスト**: Fargate → EC2 移行により Tailscale VPN ネットワーク制約を解決（詳細はトラブルシュートドキュメント参照）

**現在の課題** (git status より):
- Dovecot SQL 認証設定追加中 (`auth-sql.conf.ext`, `dovecot-sql.conf.ext`)
- ユーザー管理設計進行中 (`05_user_management_design.md`)
- デバイス接続ドキュメント追加中 (`device/` ディレクトリ)
- Gmail 受信問題調査中 (`troubleshoot/GMAILRECIEVEISSUE.md`)
- メールクライアントログイン失敗調査 (`MAIL_CLIENT_LOGIN_FAILURE_2025-11-04.md`)

---

## 💾 Docker Storage Configuration

**ストレージレイアウト**:
- **システムデータ** (`/var/lib/docker`): 50GB SSD - Docker デーモンメタデータ、コンテナレイヤー、ランタイムデータ
- **ボリューム/イメージ** (`/data/docker`): 3.6TB HDD - Docker イメージ、永続ボリューム、ビルドキャッシュ
- **バックアップ** (`/mnt/backup`): 外付け HDD - 週次自動 rsync、ボリューム/イメージ/docker-compose 設定のフルバックアップ

**重要事項**:
- Docker bridge ネットワークは 172.17.0.0/16 を使用 (KVM の 10.0.x.0/24 と競合なし)
- カスタム Docker ネットワークは 10.0.0.0/16 および 192.168.122.0/24 範囲を避けること
- 週次自動バックアップは cron でスケジュール（詳細: `3.2-storage-backup-setup.md`）

---

## 🔧 よく使うコマンド

### KVM/LibVirt 操作

```bash
# ネットワーク状態確認
sudo virsh net-list --all
sudo virsh net-dumpxml <network-name>

# VM 操作
sudo virsh list --all
sudo virsh start <vm-name>
sudo virsh shutdown <vm-name>
sudo virsh console <vm-name>

# VM 設定確認
sudo virsh dumpxml <vm-name>
```

### Docker 操作

```bash
# コンテナ管理
cd /opt/onprem-infra-system/project-root-infra/services/mailserver
docker compose ps
docker compose up -d <service-name>
docker compose logs -f <service-name>
docker compose restart <service-name>

# ストレージ確認
docker system df
docker volume ls
docker image ls

# クリーンアップ
docker system prune -a --volumes
```

### Mailserver 固有コマンド

```bash
# SendGrid SASL 同期
cd services/mailserver
./scripts/sync-sendgrid-sasl.sh <secret-arn>
docker compose restart postfix

# Tailscale 証明書更新
MAGICDNS_NAME=$(tailscale status --json | jq -r '.Self.DNSName' | sed 's/\.$//')
sudo tailscale cert \
  --cert-file /var/lib/tailscale/certs/tls.crt \
  --key-file  /var/lib/tailscale/certs/tls.key \
  "${MAGICDNS_NAME}"

# Terraform 操作（詳細は services/mailserver/terraform/README.md 参照）
cd services/mailserver/terraform
terraform plan
terraform apply
aws ecs describe-services --cluster mailserver-cluster --services mailserver-service
```

### ログ確認

```bash
# Docker デーモンログ
sudo journalctl -u docker -f

# コンテナログ
docker compose logs -f <service-name>

# システムログ
sudo tail -f /var/log/messages
```

---

## 🔒 セキュリティ構成

**原則**:
- **SSH**: 公開鍵認証のみ、非標準ポート (2201-2280)、fail2ban 保護
- **Docker**: SELinux enforcing、API 保護、非 root アクセス、自動セキュリティ更新
- **コンテナ**: デフォルト非特権、シークレット管理、最小限の capabilities

詳細なセキュリティ設定とベストプラクティスは各サービスの README.md を参照してください。

---

## ⚠️ よくある落とし穴と解決策

**代表的な問題**:
- **ネットワーク移行失敗**: default ネットワーク上の VM が移行後に動作しない → 無効化前に detach/attach 計画を立てる
- **iptables ルーティング**: 隔離ルールが機能しない → ルール順序を確認 (ACCEPT を DROP より前に配置)
- **リソース枯渇**: VM 起動失敗 → メモリ 70% 上限、CPU 1:2 オーバーコミット制限を遵守
- **Docker ストレージ競合**: デーモン起動失敗 → daemon.json 検証、パーミッション確認、SELinux コンテキストチェック

包括的なトラブルシューティングガイドは各手順書と README.md を参照してください。

---

## 🧪 テスト戦略

**原則**:
1. 前提条件を検証してから進行
2. 段階的にテスト（1 変更 → 検証 → 次へ）
3. 実際の結果 vs 期待値を記録
4. ロールバック能力を保持（変更前に設定をバックアップ）

詳細なテスト手順は各手順書のバリデーションセクションを参照してください。

---

## 📊 監視とロギング

**主要ログ格納場所**:
- Docker デーモン: `sudo journalctl -u docker`
- コンテナログ: `docker logs <container>`
- セキュリティ: fail2ban、SELinux audit ログ
- システム: `/var/log/messages`

**監視アプローチ**: 日次ログレビュー、週次ディスク使用量チェック、バックアップ検証

詳細な監視とアラート設定: `Docs/infra/procedures/3-docker/3.3-monitoring-security-setup.md`

---

## 🌩️ AWS 移行（将来）

インフラは最終的に以下を使用して AWS へ移行予定:
- **Terraform**: すべての KVM リソースを Terraform 構成としてエクスポート
- **AWS MGN**: Application Migration Service による VM 移行
- **段階的アプローチ**: 開発 (Dell) → ステージング (AWS Single-AZ) → 本番 (AWS Multi-AZ)

Terraform 構成作業時:
- AWS プロバイダー互換性を考慮
- ハードコード値ではなくデータソースを使用
- すべてのリソースに環境メタデータタグを付与
- 環境ごとに個別のステートファイルを保持

---

## 📚 サポートリソース

**公式ドキュメント**:
- LibVirt: https://libvirt.org/docs.html
- KVM: https://www.linux-kvm.org/page/Documents
- Rocky Linux: https://docs.rockylinux.org/
- Terraform LibVirt Provider: https://registry.terraform.io/providers/dmacvicar/libvirt/latest/docs

**プロジェクト参照**: 手順書のトラブルシューティングセクション、`Docs/infra/specs/` の仕様ドキュメント

---

## 📝 AI 生成手順書ガイドライン

本プロジェクトは AI ツール (Kiro/Claude/Codex) を使用して手順書を生成します。手順書のレビューまたは作成時:

- **人間レビュー必須**: すべての AI 生成手順書は実行前に検証が必要
- **バージョン管理**: 手順書の反復を Git で明確なバージョンマーカー付きで追跡
- **フィードバックループ**: 実行結果を記録して今後の手順書生成を改善
- **安全性チェック**: 常にロールバック手順とバリデーション基準を含める
- **コンテキスト保持**: 手順書更新を通じてシステム状態情報を維持

---

**Repository Nature Note**: これはドキュメント駆動型インフラリポジトリであり、ソフトウェア開発プロジェクトではありません。主要な成果物は段階的なインフラ構築手順書であり、Python/Node.js などのアプリケーションコードを含みません。「コード」は markdown 手順書内の bash コマンドであり、検証方法は実際のインフラ上での実行です。

**AGENTS.md Note**: AGENTS.md ファイルは本リポジトリとは無関係の別 AI 手順書生成プロジェクトを参照しています。本インフラドキュメントプロジェクトには直接適用されません。
