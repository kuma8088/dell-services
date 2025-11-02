# メールサーバー構築プロジェクト - 構築手順書

**文書バージョン**: 5.2
**作成日**: 2025-10-31（初版）/ 2025-11-01（v2.0改訂）/ 2025-11-01（v3.0改訂）/ 2025-11-02（v3.1改訂）/ 2025-11-02（v5.0改訂）/ 2025-11-02（v5.1改訂）/ 2025-11-02（v5.2改訂）
**対象環境**: AWS Fargate (Public IP MX Gateway) + Dell RockyLinux 9.6 + Docker Compose + SendGrid SMTP Relay + Tailscale VPN
**対象者**: AWS/Linux中級管理者
**参照文書**: 01_requirements.md v5.0、02_design.md v5.0、03_Firewall(RX-600KI).md v2.1

---

## 📋 目次

1. [事前準備](#1-事前準備)
2. [環境構築](#2-環境構築)
3. [AWS環境構築](#3-aws環境構築)
4. [SendGrid設定](#4-sendgrid設定)
5. [Tailscale VPN設定](#5-tailscale-vpn設定)
6. [Dell環境構築](#6-dell環境構築)
7. [統合テスト](#7-統合テスト)
8. [自動化設定](#8-自動化設定)
9. [トラブルシューティング](#9-トラブルシューティング)

---

## 1. 事前準備

### 1.1 必要情報の確認

以下の情報を事前に準備してください：

| 項目 | 実際の値 | 備考 |
|------|----------|------|
| **AWSアカウント** | - | Fargate/VPC/Secrets Manager利用 |
| **AWSリージョン** | ap-northeast-1 | 推奨リージョン |
| **SendGridアカウント** | https://sendgrid.com/ | SMTP Relay用 |
| **Tailscaleアカウント** | https://login.tailscale.com/ | VPN接続用 |
| **プライマリドメイン** | kuma8088.com | メインドメイン |
| **追加ドメイン** | fx-trader-life.com, webmakeprofit.org, webmakesprofit.com | 複数ドメイン対応 |
| **メールサーバー内部IP** | 192.168.1.39 | Dell側DHCP固定割り当て |
| **管理者メール** | naoya.iimura@gmail.com | アラート通知先 |

### 1.2 アーキテクチャ概要

```
インターネット
  ↓ Port 25
AWS Fargate (Public IP + Postfix MX Gateway)
  ↓ Tailscale VPN (LMTP Port 2525)
Dell RockyLinux (Dovecot Mail Host)
  ↓ Port 587
SendGrid SMTP Relay
  ↓ Port 25
外部メールサーバー
```

**データフロー**:
- **受信**: インターネット → Fargate Postfix (Public IP) → Tailscale → Dell Dovecot (LMTP) → Rspamd/ClamAV → Maildir
- **送信**: Client → Dell Postfix → SendGrid → インターネット
- **Webmail**: Client → Tailscale → Dell Nginx → Roundcube

**🔄 将来の拡張オプション**:
- Application Load Balancer (ALB) を追加することで、マルチAZ冗長化と自動スケーリングが可能
- 現在はシンプルなPublic IP Fargate構成で運用

### 1.3 前提条件確認

#### AWS CLI設定

```bash
# AWS CLIバージョン確認
aws --version
# 出力例: aws-cli/2.x.x Python/3.x.x Linux/x86_64

# AWS認証情報設定
aws configure
# AWS Access Key ID: <YOUR_ACCESS_KEY>
# AWS Secret Access Key: <YOUR_SECRET_KEY>
# Default region name: ap-northeast-1
# Default output format: json

# 認証確認
aws sts get-caller-identity
```

#### Dell RockyLinux環境確認

```bash
# OSバージョン確認
cat /etc/redhat-release
# 出力例: Rocky Linux release 9.6 (Blue Onyx)

# 現在のユーザー確認
whoami
# root または sudo権限を持つユーザーであること

# ディスク容量確認（最低20GB必要）
df -h /
```

### 1.4 システム最新化

```bash
# システムパッケージ更新（Dell）
sudo dnf update -y

# システム再起動（カーネル更新があった場合）
sudo reboot
```

---

## 2. 環境構築

### 2.1 必要パッケージインストール（Dell）

```bash
# 開発ツールとユーティリティのインストール
sudo dnf install -y \
  git \
  vim \
  wget \
  curl \
  tar \
  gzip \
  net-tools \
  bind-utils \
  jq \
  firewalld
```

### 2.2 Dockerインストール（Dell）

```bash
# Docker公式リポジトリ追加
sudo dnf config-manager --add-repo https://download.docker.com/linux/centos/docker-ce.repo

# Dockerインストール
sudo dnf install -y docker-ce docker-ce-cli containerd.io

# Docker起動と自動起動設定
sudo systemctl start docker
sudo systemctl enable docker

# Dockerバージョン確認
sudo docker --version
# 出力例: Docker version 24.0.x, build xxxxx

# 現在のユーザーをdockerグループに追加（sudo不要にする）
sudo usermod -aG docker $USER

# グループ設定を反映（一度ログアウト・ログインするか以下実行）
newgrp docker

# Docker動作確認
docker run hello-world
```

### 2.3 Docker Composeインストール（Dell）

```bash
# Docker Compose v2 インストール（Dockerプラグイン版）
sudo dnf install -y docker-compose-plugin

# バージョン確認
docker compose version
# 出力例: Docker Compose version v2.x.x
```

### 2.4 ファイアウォール設定（Dell）

```bash
# firewalld起動と自動起動設定
sudo systemctl start firewalld
sudo systemctl enable firewalld

# Tailscale VPN経由でアクセスされるポートを開放
sudo firewall-cmd --permanent --add-port=993/tcp   # IMAPS
sudo firewall-cmd --permanent --add-port=995/tcp   # POP3S
sudo firewall-cmd --permanent --add-port=443/tcp   # HTTPS
sudo firewall-cmd --permanent --add-port=2525/tcp  # LMTP (Fargate → Dell)

# 設定リロード
sudo firewall-cmd --reload

# 開放ポート確認
sudo firewall-cmd --list-all
```

### 2.5 SELinux設定（Dell）

```bash
# 現在のSELinux状態確認
getenforce

# SELinuxをPermissiveモードに変更（初期構築時）
# ※本番運用時はEnforcingモードに戻すことを推奨
sudo setenforce 0

# 永続的にPermissiveモードにする場合
sudo sed -i 's/^SELINUX=enforcing/SELINUX=permissive/' /etc/selinux/config

# ※セキュリティを重視する場合は、SELinuxポリシーを適切に設定してEnforcingモードで運用
```

---

## 3. AWS環境構築

### 3.1 Terraform による AWS インフラストラクチャプロビジョニング

#### 概要

このセクションでは、Terraform を使用して以下の AWS リソースを一括プロビジョニングします：

- VPC、サブネット、ルートテーブル、インターネットゲートウェイ
- セキュリティグループ（Fargate MX Gateway 用）
- Elastic IP（オプション）
- ECS Cluster（Fargate 専用）
- CloudWatch Logs グループ
- IAM Role（ECS Task Execution Role、Task Role）

**Terraform 管理対象外（手動設定が必要）**:
- AWS Secrets Manager（Section 3.2）- セキュリティベストプラクティス
- ECS Task Definition（Section 6）- デプロイメント固有
- ECS Service（Section 6）- デプロイメント固有

#### 前提条件

```bash
# Terraform インストール確認
terraform --version
# 出力例: Terraform v1.x.x

# Terraform がインストールされていない場合
# Rocky Linux 9.6:
sudo dnf install -y dnf-plugins-core
sudo dnf config-manager --add-repo https://rpm.releases.hashicorp.com/RHEL/hashicorp.repo
sudo dnf install terraform

# AWS CLI 認証確認（事前準備セクションで設定済み）
aws sts get-caller-identity
```

#### Terraform ワークフロー

```bash
# 1. プロジェクトディレクトリに移動
cd /opt/onprem-infra-system/project-root-infra/services/mailserver/terraform

# 2. Terraform 初期化（初回のみ）
# ⚠️ 前提条件: AWS CLI認証が完了していること
aws sts get-caller-identity || { echo "❌ AWS認証エラー"; exit 1; }

terraform init

# 3. 設定ファイル検証
terraform validate
# 出力: Success! The configuration is valid.

# 4. インフラストラクチャ変更プレビュー
terraform plan

# 5. インフラストラクチャ適用
terraform apply

# プロンプト表示:
# Do you want to perform these actions?
#   Terraform will perform the actions described above.
#   Only 'yes' will be accepted to approve.
#
#   Enter a value: yes

# 適用完了後、以下の出力が表示されます:
# Apply complete! Resources: 13 added, 0 changed, 0 destroyed.
#
# Outputs:
#
# cloudwatch_log_group_name = "/ecs/mailserver-mx"
# ecs_cluster_arn = "arn:aws:ecs:ap-northeast-1:XXXXXXXXXXXX:cluster/mailserver-cluster"
# ecs_cluster_name = "mailserver-cluster"
# elastic_ip = "13.XXX.XXX.XXX"
# elastic_ip_allocation_id = "eipalloc-XXXXXXXXXXXX"
# execution_role_arn = "arn:aws:iam::XXXXXXXXXXXX:role/mailserver-execution-role"
# internet_gateway_id = "igw-XXXXXXXXXXXX"
# public_subnet_1a_id = "subnet-XXXXXXXXXXXX"
# public_subnet_1c_id = "subnet-XXXXXXXXXXXX"
# route_table_id = "rtb-XXXXXXXXXXXX"
# security_group_id = "sg-XXXXXXXXXXXX"
# task_role_arn = "arn:aws:iam::XXXXXXXXXXXX:role/mailserver-task-role"
# vpc_cidr = "10.0.0.0/16"
# vpc_id = "vpc-XXXXXXXXXXXX"

# 6. 出力値を環境変数にエクスポート（後続セクションで使用）
export VPC_ID=$(terraform output -raw vpc_id)
export SUBNET_1=$(terraform output -raw public_subnet_1a_id)
export SUBNET_2=$(terraform output -raw public_subnet_1c_id)
export FARGATE_SG_ID=$(terraform output -raw security_group_id)
export ELASTIC_IP=$(terraform output -raw elastic_ip)
export EIP_ALLOC_ID=$(terraform output -raw elastic_ip_allocation_id)
export EXECUTION_ROLE_ARN=$(terraform output -raw execution_role_arn)
export TASK_ROLE_ARN=$(terraform output -raw task_role_arn)

# 環境変数検証スクリプト（必須）
cat > ~/validate-terraform-exports.sh << 'EOF'
#!/bin/bash
set -e

echo "=== Terraform Exports Validation ==="

# VPC ID検証
echo -n "VPC ID: $VPC_ID "
[[ $VPC_ID =~ ^vpc-[0-9a-f]{17}$ ]] && echo "✅" || { echo "❌ Invalid format"; exit 1; }

# Subnet検証
echo -n "Subnet 1a: $SUBNET_1 "
[[ $SUBNET_1 =~ ^subnet-[0-9a-f]{17}$ ]] && echo "✅" || { echo "❌ Invalid format"; exit 1; }

echo -n "Subnet 1c: $SUBNET_2 "
[[ $SUBNET_2 =~ ^subnet-[0-9a-f]{17}$ ]] && echo "✅" || { echo "❌ Invalid format"; exit 1; }

# Security Group検証
echo -n "Security Group: $FARGATE_SG_ID "
[[ $FARGATE_SG_ID =~ ^sg-[0-9a-f]{17}$ ]] && echo "✅" || { echo "❌ Invalid format"; exit 1; }

# Elastic IP検証
echo -n "Elastic IP: $ELASTIC_IP "
[[ $ELASTIC_IP =~ ^[0-9]{1,3}\.[0-9]{1,3}\.[0-9]{1,3}\.[0-9]{1,3}$ ]] && echo "✅" || { echo "❌ Invalid format"; exit 1; }

# EIP Allocation ID検証
echo -n "EIP Allocation ID: $EIP_ALLOC_ID "
[[ $EIP_ALLOC_ID =~ ^eipalloc-[0-9a-f]{17}$ ]] && echo "✅" || { echo "❌ Invalid format"; exit 1; }

# IAM Role ARN検証
echo -n "Execution Role ARN: $EXECUTION_ROLE_ARN "
[[ $EXECUTION_ROLE_ARN =~ ^arn:aws:iam::[0-9]{12}:role/ ]] && echo "✅" || { echo "❌ Invalid format"; exit 1; }

echo -n "Task Role ARN: $TASK_ROLE_ARN "
[[ $TASK_ROLE_ARN =~ ^arn:aws:iam::[0-9]{12}:role/ ]] && echo "✅" || { echo "❌ Invalid format"; exit 1; }

echo ""
echo "=== Validation Summary ==="
echo "✅ All environment variables are correctly formatted"
echo ""
echo "⚠️ 重要: 以下のIPアドレスを記録してください"
echo "Elastic IP: $ELASTIC_IP"
echo "用途: セクション7.3でMXレコードに設定します"
echo ""
EOF

chmod +x /opt/onprem-infra-system/project-root-infra/services/mailserver/terraform/scripts/validate-terraform-exports.sh
/opt/onprem-infra-system/project-root-infra/services/mailserver/terraform/scripts/validate-terraform-exports.sh
```

#### インフラストラクチャ検証

```bash
# Terraform 管理状態確認
terraform show

# 特定リソースの詳細確認
terraform state show aws_vpc.mailserver_vpc
terraform state show aws_security_group.fargate_sg
terraform state show aws_eip.mailserver_eip

# AWS コンソールでの検証
# 1. VPC コンソール: VPC、サブネット、ルートテーブル確認
# 2. EC2 コンソール: セキュリティグループ、Elastic IP 確認
# 3. ECS コンソール: Cluster 確認
# 4. IAM コンソール: Role 確認
# 5. CloudWatch コンソール: Logs グループ確認
```

#### セキュリティグループ検証スクリプト

Terraform で作成したセキュリティグループの設定を検証します：

```bash
# 検証スクリプト作成
cat > ~/validate-sg-rules.sh << 'EOF'
#!/bin/bash
set -e

FARGATE_SG_ID="$1"

if [ -z "$FARGATE_SG_ID" ]; then
  echo "Usage: $0 <FARGATE_SG_ID>"
  exit 1
fi

echo "=== Fargate Security Group Validation ==="
echo "Security Group ID: $FARGATE_SG_ID"
echo ""

# インバウンドルール検証
echo "📥 Inbound Rules Validation:"
INBOUND_RULES=$(aws ec2 describe-security-groups --group-ids $FARGATE_SG_ID --query 'SecurityGroups[0].IpPermissions')

# Port 25 TCP 検証（0.0.0.0/0から許可必須）
PORT25_RULE=$(echo $INBOUND_RULES | jq '.[] | select(.FromPort==25 and .ToPort==25 and .IpProtocol=="tcp")')
if [ -n "$PORT25_RULE" ]; then
  echo "✅ Port 25 TCP (SMTP) - ALLOWED from 0.0.0.0/0"
else
  echo "❌ Port 25 TCP (SMTP) - MISSING (Critical for MX gateway)"
  exit 1
fi

# Port 41641 UDP 検証（Tailscale DERP）
PORT41641_RULE=$(echo $INBOUND_RULES | jq '.[] | select(.FromPort==41641 and .ToPort==41641 and .IpProtocol=="udp")')
if [ -n "$PORT41641_RULE" ]; then
  echo "✅ Port 41641 UDP (Tailscale) - ALLOWED from 0.0.0.0/0"
else
  echo "❌ Port 41641 UDP (Tailscale) - MISSING (Critical for VPN connectivity)"
  exit 1
fi

# アウトバウンドルール検証
echo ""
echo "📤 Outbound Rules Validation:"
OUTBOUND_RULES=$(aws ec2 describe-security-groups --group-ids $FARGATE_SG_ID --query 'SecurityGroups[0].IpPermissionsEgress')

# 全トラフィック許可検証
EGRESS_ALL=$(echo $OUTBOUND_RULES | jq '.[] | select(.IpProtocol=="-1" and (.IpRanges[].CidrIp=="0.0.0.0/0"))')
if [ -n "$EGRESS_ALL" ]; then
  echo "✅ All outbound traffic - ALLOWED to 0.0.0.0/0"
else
  echo "⚠️ All outbound traffic - RESTRICTED (may cause connectivity issues)"
fi

echo ""
echo "=== Validation Summary ==="
echo "✅ Security Group $FARGATE_SG_ID is correctly configured"
EOF

chmod +x ~/validate-sg-rules.sh

# 検証実行
~/validate-sg-rules.sh $FARGATE_SG_ID
```

**期待される出力**:
```
=== Fargate Security Group Validation ===
Security Group ID: sg-0123456789abcdef0

📥 Inbound Rules Validation:
✅ Port 25 TCP (SMTP) - ALLOWED from 0.0.0.0/0
✅ Port 41641 UDP (Tailscale) - ALLOWED from 0.0.0.0/0

📤 Outbound Rules Validation:
✅ All outbound traffic - ALLOWED to 0.0.0.0/0

=== Validation Summary ===
✅ Security Group sg-0123456789abcdef0 is correctly configured
```

#### IP アドレス戦略について

**Elastic IP（推奨）**:
- Terraform で Elastic IP が自動作成されます
- 固定 IP アドレスにより DNS 運用が簡素化
- 月額コスト: $3.60/月
- MX レコードに設定する IP アドレスは `terraform output elastic_ip` で取得

**Dynamic IP（コスト最適化）**:
- Elastic IP リソースを Terraform 設定から削除することで Dynamic IP に変更可能
- タスク再起動時の DNS 自動更新スクリプトが必要（セクション 8 参照）
- 月額コスト: 無料

#### Terraform Apply失敗時の復旧手順

**シナリオ1: 正常なインフラ適用**

```bash
# Given: AWS認証が有効 AND terraform init 完了
# When: terraform apply 実行 AND プロンプトで "yes" 入力
# Then:
#   - "Apply complete! Resources: 13 added" が表示される
#   - 全出力値が有効な形式で表示される
#   - terraform.tfstate ファイルが作成される

# 成功検証基準:
# 1. elastic_ip が有効なIPv4アドレス形式 (例: 13.XXX.XXX.XXX)
# 2. vpc_id が vpc-XXXXXXXXXXXX 形式
# 3. security_group_id が sg-XXXXXXXXXXXX 形式
# 4. 全出力値が "null" でないこと
```

**シナリオ2: インフラ一部作成済み（例: VPCは成功、Subnetで失敗）**

```bash
# 1. 現在のState確認
terraform state list
# 出力例:
# aws_vpc.mailserver_vpc
# （Subnet等は未作成でリストに表示されない）

# 2. エラー原因解決
# - AWS上限緩和が必要な場合: AWSサポートに依頼
# - 設定ミスの場合: terraform/main.tf を修正

# 3. 再適用（Terraformが差分を自動検出して続行）
terraform plan  # 差分確認
terraform apply
```

**シナリオ3: State破損が疑われる場合**

```bash
# 1. Stateバックアップ（破損対策）
cp terraform.tfstate terraform.tfstate.backup.$(date +%Y%m%d_%H%M%S)

# 2. AWSリソース現状確認
aws ec2 describe-vpcs --filters "Name=tag:Name,Values=mailserver-vpc" --query 'Vpcs[0].VpcId' --output text
# 出力例: vpc-0123456789abcdef0

# 3. State修復（Stateに記録されていないが実際に存在するリソースをインポート）
terraform import aws_vpc.mailserver_vpc <VPC_ID>

# 4. State整合性確認
terraform plan
# 期待値: "No changes. Your infrastructure matches the configuration."
```

**シナリオ4: 完全ロールバックが必要な場合**

```bash
# 1. 作成済みリソース一覧取得
terraform state list

# 2. 削除実行（警告をよく読んでから承認）
terraform destroy

# 3. 問題解決後、再構築
terraform plan  # 構築内容の再確認
terraform apply
```

#### Terraform リソース削除（注意）

```bash
# ⚠️ 警告: 以下のコマンドはすべての AWS リソースを削除します
# 本番環境では実行しないでください

# リソース削除前チェックリスト（必須）
# 1. ECS Serviceが削除されていることを確認
aws ecs list-services --cluster mailserver-cluster --query 'serviceArns' --output text
# 期待値: 空出力（サービスが存在しない）

# 2. 実行中のECS Taskが存在しないことを確認
aws ecs list-tasks --cluster mailserver-cluster --query 'taskArns' --output text
# 期待値: 空出力（タスクが存在しない）

# 3. バックアップ確認
terraform show > /tmp/terraform_backup_$(date +%Y%m%d_%H%M%S).txt

# 上記すべて確認後、削除実行
# リソース削除プレビュー
terraform plan -destroy

# リソース削除実行
terraform destroy

# プロンプト表示:
# Do you really want to destroy all resources?
#   Terraform will destroy all your managed infrastructure, as shown above.
#   There is no undo. Only 'yes' will be accepted to confirm.
#
#   Enter a value: yes
```

#### トラブルシューティング

**エラー: "Error creating VPC: VpcLimitExceeded"**
- 原因: AWS アカウントの VPC 上限に達している
- 対処: 未使用の VPC を削除するか、AWS サポートに上限緩和を依頼

**エラー: "Error creating Elastic IP: AddressLimitExceeded"**
- 原因: Elastic IP の上限（デフォルト 5 個）に達している
- 対処: 未使用の EIP を解放するか、AWS サポートに上限緩和を依頼

**エラー: "Error creating IAM Role: EntityAlreadyExists"**
- 原因: 同名の IAM Role が既に存在
- 対処: 既存の Role を削除するか、`terraform/main.tf` で Role 名を変更

**Elastic IP関連付けエラー: "Resource already associated"**:
- 原因: 既存のElastic IPが別のENIに関連付けられている
- 対処:
```bash
# 既存関連付け確認
aws ec2 describe-addresses --allocation-ids $EIP_ALLOC_ID

# 既存関連付け解除（必要に応じて）
aws ec2 disassociate-address --association-id <ASSOCIATION_ID>

# 再関連付け
aws ec2 associate-address \
  --allocation-id $EIP_ALLOC_ID \
  --network-interface-id $ENI_ID
```

**Terraform State ロック**:
- S3 バックエンドと DynamoDB テーブルを使用した State ロック機能は未実装
- 複数人での同時作業は避けてください
- 将来の拡張: S3 + DynamoDB によるリモート State 管理を推奨

### 3.6 AWS Secrets Manager設定

#### Tailscale Auth Key保存

```bash
# ⚠️ Tailscaleコンソールで Auth Key を生成してください
# https://login.tailscale.com/admin/settings/keys
# - Reusable: Yes
# - Ephemeral: Yes
# - Tags: fargate-mx
# - Expiration: Never

# ⚠️ セキュリティ注意: Auth Key を一時ファイルから読み込む
# (シェル履歴に残さないため)
echo "Tailscale Auth Key を含むファイルを用意してください"
echo "例: /tmp/ts_auth.key (パーミッション 600)"
read -p "Auth Key ファイルパス: " TS_KEY_FILE

# ファイルから読み込み
TS_AUTHKEY=$(cat "$TS_KEY_FILE")

# 即座にファイルを削除
rm -f "$TS_KEY_FILE"

# シェル履歴からも削除
history -d $((HISTCMD-3))
history -d $((HISTCMD-2))
history -d $((HISTCMD-1))

# Secrets Managerにシークレット作成
aws secretsmanager create-secret \
  --name mailserver/tailscale/fargate-auth-key \
  --description "Tailscale Auth Key for Fargate MX Gateway" \
  --secret-string "$TS_AUTHKEY"

# シークレットARN取得
TS_SECRET_ARN=$(aws secretsmanager describe-secret \
  --secret-id mailserver/tailscale/fargate-auth-key \
  --query 'ARN' \
  --output text)

echo "Tailscale Secret ARN: $TS_SECRET_ARN"
```

#### SendGrid API Key保存（後ほど設定）

```bash
# ⚠️ SendGridコンソールでAPI Keyを生成した後に実行
# セクション4で実施
```

**⚠️ 注意**: IAM Role、ECS Cluster、CloudWatch Logs は Section 3.1 の Terraform で自動作成されています。手動作成は不要です。

---

## 4. SendGrid設定

### 4.1 SendGridアカウント作成

```bash
# 1. SendGridアカウント作成: https://sendgrid.com/
# 2. プラン選択: Free（月100通）または Essentials（月50,000通 $19.95/月）
# 3. アカウント認証完了（メール確認）
```

### 4.2 SendGrid API Key生成

```bash
# 1. SendGridコンソールにログイン: https://app.sendgrid.com/
# 2. Settings → API Keys
# 3. "Create API Key" クリック
# 4. API Key Name: mailserver-dell-smtp
# 5. API Key Permissions: Restricted Access → Mail Send: Full Access
# 6. "Create & View" クリック
# 7. API Keyをコピー（SG.XXXXXXXXXXXXXXXXXXXXXXXXXXXX）

# ⚠️ セキュリティ注意: API Key を一時ファイルから読み込む
# (シェル履歴に残さないため)
echo "SendGrid API Key を含むファイルを用意してください"
echo "例: /tmp/sendgrid_api.key (パーミッション 600)"
read -p "API Key ファイルパス: " SG_KEY_FILE

# ファイルから読み込み
SENDGRID_API_KEY=$(cat "$SG_KEY_FILE")

# 即座にファイルを削除
rm -f "$SG_KEY_FILE"

# シェル履歴からも削除
history -d $((HISTCMD-3))
history -d $((HISTCMD-2))
history -d $((HISTCMD-1))

# ⚠️ この値は後ほどDell側Postfix設定で使用します
```

### 4.3 SendGridドメイン認証

#### プライマリドメイン認証（kuma8088.com）

```bash
# 1. SendGridコンソール: Settings → Sender Authentication → Domain Authentication
# 2. "Authenticate Your Domain" クリック
# 3. DNS Host: Cloudflare
# 4. Domain: kuma8088.com
# 5. "Next" → SendGridがDNSレコードを生成
```

**Cloudflareに追加するDNSレコード**（SendGrid生成値に基づく）:

```
# SPFレコード
Type: TXT
Name: @
Content: v=spf1 include:sendgrid.net ~all
TTL: Auto

# DKIMレコード（SendGrid生成）
Type: CNAME
Name: s1._domainkey
Content: s1.domainkey.u12345678.wl.sendgrid.net.
TTL: Auto

Type: CNAME
Name: s2._domainkey
Content: s2.domainkey.u12345678.wl.sendgrid.net.
TTL: Auto

# DMARCレコード
Type: TXT
Name: _dmarc
Content: v=DMARC1; p=quarantine; rua=mailto:naoya.iimura@gmail.com
TTL: Auto
```

#### 追加ドメイン認証

同様の手順で以下のドメインも認証：
- fx-trader-life.com
- webmakeprofit.org
- webmakesprofit.com

### 4.4 SendGrid認証確認

```bash
# SendGridコンソールでドメイン認証ステータス確認
# Settings → Sender Authentication → Domain Authentication
# Status: "Verified" になっていることを確認

# DNS浸透確認
dig TXT kuma8088.com | grep sendgrid
dig CNAME s1._domainkey.kuma8088.com
dig TXT _dmarc.kuma8088.com
```

### 4.5 SendGrid API Key 管理戦略

#### セキュリティレベル選択ガイド

**Level 1: 開発環境** - ローカルファイル管理（最も簡単）
- API Key を Dell ホスト上の `/opt/onprem-infra-system/project-root-infra/services/mailserver/config/postfix/sasl_passwd` に直接保存
- パーミッション 600 で保護
- バックアップ時は暗号化必須

**Level 2: 商用環境** - AWS Secrets Manager 統合（推奨）
- API Key を AWS Secrets Manager に保存
- Dell ホストから AWS CLI で動的取得
- 定期的なローテーション機能利用可能
- 監査ログ記録

#### Level 1 実装（開発環境）

```bash
# Dell ホスト上で直接ファイル作成（セクション6.2で実施）
# 後述の「SendGrid認証情報設定」セクションを参照
echo "Level 1（ローカルファイル管理）を選択 - セクション6.2で設定"
```

#### Level 2 実装（商用環境 - 推奨）

```bash
# Secrets Managerにシークレット作成
aws secretsmanager create-secret \
  --name mailserver/sendgrid/api-key \
  --description "SendGrid API Key for SMTP Relay" \
  --secret-string "$SENDGRID_API_KEY"

# シークレットARN取得
SENDGRID_SECRET_ARN=$(aws secretsmanager describe-secret \
  --secret-id mailserver/sendgrid/api-key \
  --query 'ARN' \
  --output text)

echo "SendGrid Secret ARN: $SENDGRID_SECRET_ARN"

# Dell ホストでの取得スクリプト作成（セクション6.2で使用）
cat > ~/fetch-sendgrid-key.sh << 'EOF'
#!/bin/bash
# Secrets Manager から SendGrid API Key を取得
aws secretsmanager get-secret-value \
  --secret-id mailserver/sendgrid/api-key \
  --query 'SecretString' \
  --output text
EOF

chmod 700 ~/fetch-sendgrid-key.sh

echo "✅ Level 2（Secrets Manager）設定完了"
echo "Dell ホストで ~/fetch-sendgrid-key.sh を実行して API Key を取得してください"
```

---

## 5. Tailscale VPN設定

### 5.1 Tailscaleインストール（Dell）

```bash
# Tailscaleリポジトリ追加
curl -fsSL https://pkgs.tailscale.com/stable/rhel/9/tailscale.repo | \
  sudo tee /etc/yum.repos.d/tailscale.repo

# Tailscaleインストール
sudo dnf install -y tailscale

# Tailscaleサービス起動と自動起動設定
sudo systemctl enable --now tailscaled

# Tailscaleネットワークに参加（ブラウザで認証）
sudo tailscale up --accept-routes

# Tailscale状態確認
tailscale status

# TailscaleネットワークIPアドレス確認
tailscale ip -4
# 出力例: 100.x.x.x

# ホスト名設定
sudo tailscale set --hostname mailserver

# MagicDNS名確認
MAGICDNS_NAME=$(tailscale status --json | jq -r '.Self.DNSName')
echo "MagicDNS名: $MAGICDNS_NAME"
# 出力例: mailserver.tail67811d.ts.net.
```

### 5.2 Tailscale ACL設定

```bash
# 1. Tailscaleコンソール: https://login.tailscale.com/admin/acls
# 2. 以下のACLルールを追加
```

**ACL設定内容**:

```json
{
  "tagOwners": {
    "tag:fargate-mx": ["autogroup:admin"],
    "tag:mailserver": ["autogroup:admin"]
  },
  "grants": [
    {
      "src": ["tag:fargate-mx"],
      "dst": ["tag:mailserver"],
      "ip": ["tcp:25", "tcp:2525", "udp:41641"]
    },
    {
      "src": ["autogroup:member"],
      "dst": ["tag:mailserver"],
      "ip": ["tcp:993", "tcp:995", "tcp:80", "tcp:443"]
    }
  ],
}
```

**説明**:
- `tag:fargate-mx`: Fargateタスクに付与するタグ（Fargate → Dell LMTP Port 2525アクセス許可）
- `autogroup:members`: 全Tailscaleユーザー（Dell Webmail/IMAP/POP3アクセス許可）

### 5.3 Tailscale HTTPS証明書取得（Dell）

```bash
# MagicDNS名確認
MAGICDNS_NAME=$(tailscale status --json | jq -r '.Self.DNSName' | sed 's/\.$//')
echo "MagicDNS名: $MAGICDNS_NAME"

# Tailscale HTTPS証明書取得
sudo tailscale cert $MAGICDNS_NAME

# 証明書取得成功の確認
ls -la /var/lib/tailscale/certs/

# 期待される出力:
# ${MAGICDNS_NAME}.crt (公開鍵証明書)
# ${MAGICDNS_NAME}.key (秘密鍵)

# 証明書内容確認
openssl x509 -in /var/lib/tailscale/certs/${MAGICDNS_NAME}.crt -noout -text | grep -A1 "Subject Alternative Name"
```

### 5.4 firewalld Tailscale統合（Dell）

```bash
# FirewalldをTailscaleに統合（推奨）
sudo firewall-cmd --permanent --zone=trusted --add-interface=tailscale0
sudo firewall-cmd --reload

# 設定確認
sudo firewall-cmd --list-all --zone=trusted
```

---

## 6. Dell環境構築

### 6.1 プロジェクトセットアップ

#### ディレクトリ構造作成

```bash
# プロジェクトルートディレクトリ作成
sudo mkdir -p /opt/onprem-infra-system/project-root-infra/services/mailserver

# 所有権を現在のユーザーに変更
sudo chown -R $USER:$USER /opt/onprem-infra-system/project-root-infra/services/mailserver

# ディレクトリ構造作成
cd /opt/onprem-infra-system/project-root-infra/services/mailserver
mkdir -p config/{postfix,dovecot,nginx/conf.d,roundcube,rspamd,clamav}
mkdir -p data/{mail,db,rspamd,clamav}
mkdir -p logs/{postfix,dovecot,nginx,roundcube,rspamd,clamav}
mkdir -p scripts
mkdir -p backups

# ディレクトリ構造確認
tree -L 3 /opt/onprem-infra-system/project-root-infra/services/mailserver
```

#### 環境変数ファイル作成

```bash
# .envファイル作成
cat > /opt/onprem-infra-system/project-root-infra/services/mailserver/.env << EOF
# メインドメイン設定
MAIL_DOMAIN=kuma8088.com
MAIL_HOSTNAME=mail.kuma8088.com

# 追加ドメイン（スペース区切り）
MAIL_ADDITIONAL_DOMAINS="fx-trader-life.com webmakeprofit.org webmakesprofit.com"

# データベース設定
MYSQL_ROOT_PASSWORD=YourStrongRootPassword123!
MYSQL_DATABASE=roundcube
MYSQL_USER=roundcube
MYSQL_PASSWORD=YourStrongRoundcubePassword123!

# Roundcube設定
ROUNDCUBE_DES_KEY=YourRandom24CharacterKey!

# 管理者メールアドレス（アラート通知先）
ADMIN_EMAIL=naoya.iimura@gmail.com

# タイムゾーン
TZ=Asia/Tokyo

# メールユーザーID
VMAIL_UID=5000
VMAIL_GID=5000

# リソース制限（CPU/メモリ）
POSTFIX_CPU_LIMIT=1.0
POSTFIX_MEM_LIMIT=2g
DOVECOT_CPU_LIMIT=1.0
DOVECOT_MEM_LIMIT=2g
RSPAMD_CPU_LIMIT=1.0
RSPAMD_MEM_LIMIT=2g
CLAMAV_CPU_LIMIT=1.0
CLAMAV_MEM_LIMIT=2g
EOF

# ⚠️ 重要: 以下を必ず変更してください！
# - MYSQL_ROOT_PASSWORD: 強力なパスワード（16文字以上推奨）
# - MYSQL_PASSWORD: 強力なパスワード（16文字以上推奨）
# - ROUNDCUBE_DES_KEY: ランダムな24文字キー

# パーミッション設定（機密情報のため読み取り制限）
chmod 600 /opt/onprem-infra-system/project-root-infra/services/mailserver/.env
```

### 6.2 Postfix設定（SendGrid Relay専用）

#### Postfix main.cf設定

```bash
cat > /opt/onprem-infra-system/project-root-infra/services/mailserver/config/postfix/main.cf << 'EOF'
# 基本設定
myhostname = mail.kuma8088.com
mydomain = kuma8088.com
myorigin = $mydomain
mydestination =

# ネットワーク設定
inet_interfaces = all
inet_protocols = ipv4
mynetworks = 127.0.0.0/8, 172.20.0.0/24

# SendGrid SMTP Relay設定
relayhost = [smtp.sendgrid.net]:587
smtp_sasl_auth_enable = yes
smtp_sasl_password_maps = hash:/etc/postfix/sasl_passwd
smtp_sasl_security_options = noanonymous
smtp_tls_security_level = encrypt
smtp_tls_note_starttls_offer = yes

# メールボックス設定（受信はDovecot LMTP経由）
virtual_mailbox_domains = kuma8088.com, fx-trader-life.com, webmakeprofit.org, webmakesprofit.com
virtual_transport = lmtp:unix:private/dovecot-lmtp

# メッセージサイズ制限
message_size_limit = 26214400

# SMTPD設定（Port 587受信用）
smtpd_relay_restrictions = permit_mynetworks, permit_sasl_authenticated, defer_unauth_destination
smtpd_sasl_type = dovecot
smtpd_sasl_path = private/auth
smtpd_sasl_auth_enable = yes
smtpd_tls_security_level = may
smtpd_tls_cert_file = /var/lib/tailscale/certs/${MAGICDNS_NAME}.crt
smtpd_tls_key_file = /var/lib/tailscale/certs/${MAGICDNS_NAME}.key
EOF

# MagicDNS名を実際の値に置換
MAGICDNS_NAME=$(tailscale status --json | jq -r '.Self.DNSName')
sed -i "s/\${MAGICDNS_NAME}/$MAGICDNS_NAME/g" /opt/onprem-infra-system/project-root-infra/services/mailserver/config/postfix/main.cf
```

#### SendGrid認証情報設定

**Level 1（ローカルファイル管理）の場合**:

```bash
# ⚠️ セクション4.2で取得した $SENDGRID_API_KEY が環境変数に設定されていることを確認
# 設定されていない場合は再度セキュアな方法で取得

# SASL認証ファイル作成
cat > /opt/onprem-infra-system/project-root-infra/services/mailserver/config/postfix/sasl_passwd << EOF
[smtp.sendgrid.net]:587 apikey:$SENDGRID_API_KEY
EOF

# パーミッション設定（必須）
chmod 600 /opt/onprem-infra-system/project-root-infra/services/mailserver/config/postfix/sasl_passwd

# 環境変数をクリア（セキュリティ）
unset SENDGRID_API_KEY

# ⚠️ このファイルはDocker起動後にコンテナ内でpostmapコマンドで処理されます
```

**Level 2（Secrets Manager統合）の場合**:

```bash
# Secrets Manager から API Key を取得
SENDGRID_API_KEY=$(~/fetch-sendgrid-key.sh)

# SASL認証ファイル作成
cat > /opt/onprem-infra-system/project-root-infra/services/mailserver/config/postfix/sasl_passwd << EOF
[smtp.sendgrid.net]:587 apikey:$SENDGRID_API_KEY
EOF

# パーミッション設定（必須）
chmod 600 /opt/onprem-infra-system/project-root-infra/services/mailserver/config/postfix/sasl_passwd

# 環境変数をクリア（セキュリティ）
unset SENDGRID_API_KEY

# ⚠️ このファイルはDocker起動後にコンテナ内でpostmapコマンドで処理されます

echo "✅ SendGrid認証情報設定完了（Secrets Manager経由）"
```

### 6.3 Dovecot設定（LMTP受信 + IMAP/POP3）

#### Dovecot dovecot.conf設定

```bash
cat > /opt/onprem-infra-system/project-root-infra/services/mailserver/config/dovecot/dovecot.conf << EOF
# プロトコル設定
protocols = imap pop3 lmtp

# メールディレクトリ設定
mail_location = maildir:/var/mail/vhosts/%d/%n

# SSL/TLS設定
ssl = required
ssl_cert = </var/lib/tailscale/certs/$MAGICDNS_NAME.crt
ssl_key = </var/lib/tailscale/certs/$MAGICDNS_NAME.key
ssl_protocols = !SSLv3 !TLSv1 !TLSv1.1
ssl_cipher_list = ECDHE-RSA-AES128-GCM-SHA256:ECDHE-RSA-AES256-GCM-SHA384

# 認証設定
auth_mechanisms = plain login
passdb {
  driver = passwd-file
  args = scheme=SHA512-CRYPT username_format=%u /etc/dovecot/users
}

userdb {
  driver = static
  args = uid=vmail gid=vmail home=/var/mail/vhosts/%d/%n
}

# LMTP設定（Fargate → Dellへの転送受信）
service lmtp {
  inet_listener lmtp {
    port = 2525
    address = *
  }
}

# IMAP設定
service imap-login {
  inet_listener imap {
    port = 143
  }
  inet_listener imaps {
    port = 993
    ssl = yes
  }
}

# POP3設定
service pop3-login {
  inet_listener pop3 {
    port = 110
  }
  inet_listener pop3s {
    port = 995
    ssl = yes
  }
}

# Postfix SASL認証
service auth {
  unix_listener /var/spool/postfix/private/auth {
    mode = 0660
    user = postfix
    group = postfix
  }
}

# プラグイン設定
protocol lmtp {
  mail_plugins = \$mail_plugins sieve
}

protocol imap {
  mail_plugins = \$mail_plugins imap_sieve
}
EOF
```

### 6.4 Nginx設定

#### nginx.conf

```bash
cat > /opt/onprem-infra-system/project-root-infra/services/mailserver/config/nginx/nginx.conf << 'EOF'
user nginx;
worker_processes auto;
error_log /var/log/nginx/error.log warn;
pid /var/run/nginx.pid;

events {
    worker_connections 1024;
}

http {
    include /etc/nginx/mime.types;
    default_type application/octet-stream;

    log_format main '$remote_addr - $remote_user [$time_local] "$request" '
                    '$status $body_bytes_sent "$http_referer" '
                    '"$http_user_agent" "$http_x_forwarded_for"';

    access_log /var/log/nginx/access.log main;

    sendfile on;
    tcp_nopush on;
    keepalive_timeout 65;
    gzip on;

    include /etc/nginx/conf.d/*.conf;
}
EOF
```

#### Roundcube VirtualHost設定

```bash
cat > /opt/onprem-infra-system/project-root-infra/services/mailserver/config/nginx/conf.d/mailserver.conf << EOF
server {
    listen 80;
    server_name $MAGICDNS_NAME;

    # HTTPSへリダイレクト
    location / {
        return 301 https://\$server_name\$request_uri;
    }
}

server {
    listen 443 ssl http2;
    server_name $MAGICDNS_NAME;

    # Tailscale HTTPS証明書
    ssl_certificate /var/lib/tailscale/certs/$MAGICDNS_NAME.crt;
    ssl_certificate_key /var/lib/tailscale/certs/$MAGICDNS_NAME.key;
    ssl_protocols TLSv1.2 TLSv1.3;
    ssl_ciphers HIGH:!aNULL:!MD5;
    ssl_prefer_server_ciphers on;

    # セキュリティヘッダー
    add_header Strict-Transport-Security "max-age=31536000; includeSubDomains" always;
    add_header X-Frame-Options "SAMEORIGIN" always;
    add_header X-Content-Type-Options "nosniff" always;
    add_header X-XSS-Protection "1; mode=block" always;

    # Roundcubeへプロキシ
    location / {
        proxy_pass http://172.20.0.40:80;
        proxy_set_header Host \$host;
        proxy_set_header X-Real-IP \$remote_addr;
        proxy_set_header X-Forwarded-For \$proxy_add_x_forwarded_for;
        proxy_set_header X-Forwarded-Proto \$scheme;

        # タイムアウト設定
        proxy_connect_timeout 600;
        proxy_send_timeout 600;
        proxy_read_timeout 600;
        send_timeout 600;

        # バッファ設定
        client_max_body_size 25M;
    }
}
EOF
```

### 6.5 Docker Compose設定

```bash
cat > /opt/onprem-infra-system/project-root-infra/services/mailserver/docker-compose.yml << 'EOF'
version: '3.8'

networks:
  mailserver_network:
    driver: bridge
    ipam:
      config:
        - subnet: 172.20.0.0/24

volumes:
  mail_data:
    driver: local
    driver_opts:
      type: none
      o: bind
      device: /opt/onprem-infra-system/project-root-infra/services/mailserver/data/mail
  db_data:
    driver: local
    driver_opts:
      type: none
      o: bind
      device: /opt/onprem-infra-system/project-root-infra/services/mailserver/data/db
  rspamd_data:
    driver: local
    driver_opts:
      type: none
      o: bind
      device: /opt/onprem-infra-system/project-root-infra/services/mailserver/data/rspamd
  clamav_data:
    driver: local
    driver_opts:
      type: none
      o: bind
      device: /opt/onprem-infra-system/project-root-infra/services/mailserver/data/clamav

services:
  # MariaDB データベース
  mariadb:
    image: mariadb:10.11.7
    container_name: mailserver-mariadb
    hostname: mariadb
    restart: always
    networks:
      mailserver_network:
        ipv4_address: 172.20.0.60
    environment:
      - MYSQL_ROOT_PASSWORD=${MYSQL_ROOT_PASSWORD}
      - MYSQL_DATABASE=${MYSQL_DATABASE}
      - MYSQL_USER=${MYSQL_USER}
      - MYSQL_PASSWORD=${MYSQL_PASSWORD}
      - TZ=${TZ}
    volumes:
      - db_data:/var/lib/mysql
    healthcheck:
      test: ["CMD", "mysqladmin", "ping", "-h", "localhost", "-u", "root", "-p${MYSQL_ROOT_PASSWORD}"]
      interval: 30s
      timeout: 10s
      retries: 3

  # Postfix MTA (SendGrid Relay専用)
  postfix:
    image: bokysan/postfix:latest
    container_name: mailserver-postfix
    hostname: ${MAIL_HOSTNAME}
    restart: always
    networks:
      mailserver_network:
        ipv4_address: 172.20.0.20
    ports:
      - "587:587"
    environment:
      - HOSTNAME=${MAIL_HOSTNAME}
      - DOMAIN=${MAIL_DOMAIN}
      - TZ=${TZ}
    volumes:
      - ./config/postfix:/etc/postfix/custom
      - mail_data:/var/mail/vhosts
      - /var/lib/tailscale/certs:/var/lib/tailscale/certs:ro
      - ./logs/postfix:/var/log
    depends_on:
      - rspamd
    deploy:
      resources:
        limits:
          cpus: '${POSTFIX_CPU_LIMIT}'
          memory: '${POSTFIX_MEM_LIMIT}'
    healthcheck:
      test: ["CMD", "nc", "-z", "localhost", "587"]
      interval: 30s
      timeout: 10s
      retries: 3
      start_period: 40s

  # Dovecot MDA (LMTP + IMAP/POP3)
  dovecot:
    image: dovecot/dovecot:2.3.21
    container_name: mailserver-dovecot
    hostname: dovecot
    restart: always
    networks:
      mailserver_network:
        ipv4_address: 172.20.0.30
    ports:
      - "2525:2525"  # LMTP (Fargate → Dell)
      - "993:993"    # IMAPS
      - "995:995"    # POP3S
    environment:
      - TZ=${TZ}
    volumes:
      - ./config/dovecot:/etc/dovecot/custom
      - mail_data:/var/mail/vhosts
      - /var/lib/tailscale/certs:/var/lib/tailscale/certs:ro
      - ./logs/dovecot:/var/log
    deploy:
      resources:
        limits:
          cpus: '${DOVECOT_CPU_LIMIT}'
          memory: ${DOVECOT_MEM_LIMIT}
    healthcheck:
      test: ["CMD", "nc", "-z", "localhost", "2525"]
      interval: 30s
      timeout: 10s
      retries: 3
      start_period: 40s

  # Rspamd スパムフィルタ
  rspamd:
    image: rspamd/rspamd:3.8
    container_name: mailserver-rspamd
    hostname: rspamd
    restart: always
    networks:
      mailserver_network:
        ipv4_address: 172.20.0.70
    volumes:
      - rspamd_data:/var/lib/rspamd
      - ./config/rspamd:/etc/rspamd/override.d
      - ./logs/rspamd:/var/log/rspamd
    environment:
      - TZ=${TZ}
    depends_on:
      - clamav
    deploy:
      resources:
        limits:
          cpus: '${RSPAMD_CPU_LIMIT}'
          memory: ${RSPAMD_MEM_LIMIT}
    healthcheck:
      test: ["CMD", "curl", "-f", "http://localhost:11334/"]
      interval: 30s
      timeout: 10s
      retries: 3
      start_period: 60s

  # ClamAV ウイルススキャン
  clamav:
    image: clamav/clamav:1.3
    container_name: mailserver-clamav
    hostname: clamav
    restart: always
    networks:
      mailserver_network:
        ipv4_address: 172.20.0.80
    volumes:
      - clamav_data:/var/lib/clamav
      - ./logs/clamav:/var/log/clamav
    environment:
      - TZ=${TZ}
    deploy:
      resources:
        limits:
          cpus: '${CLAMAV_CPU_LIMIT}'
          memory: ${CLAMAV_MEM_LIMIT}
    healthcheck:
      test: ["CMD", "/usr/local/bin/clamdcheck.sh"]
      interval: 60s
      timeout: 10s
      retries: 3
      start_period: 120s

  # Roundcube Webmail
  roundcube:
    image: roundcube/roundcubemail:1.6.7-apache
    container_name: mailserver-roundcube
    hostname: roundcube
    restart: always
    networks:
      mailserver_network:
        ipv4_address: 172.20.0.40
    environment:
      - ROUNDCUBEMAIL_DB_TYPE=mysql
      - ROUNDCUBEMAIL_DB_HOST=mariadb
      - ROUNDCUBEMAIL_DB_NAME=${MYSQL_DATABASE}
      - ROUNDCUBEMAIL_DB_USER=${MYSQL_USER}
      - ROUNDCUBEMAIL_DB_PASSWORD=${MYSQL_PASSWORD}
      - ROUNDCUBEMAIL_DEFAULT_HOST=ssl://dovecot
      - ROUNDCUBEMAIL_DEFAULT_PORT=993
      - ROUNDCUBEMAIL_SMTP_SERVER=tls://postfix
      - ROUNDCUBEMAIL_SMTP_PORT=587
      - ROUNDCUBEMAIL_UPLOAD_MAX_FILESIZE=25M
      - ROUNDCUBEMAIL_DES_KEY=${ROUNDCUBE_DES_KEY}
      - TZ=${TZ}
    volumes:
      - ./config/roundcube:/var/roundcube/config
      - ./logs/roundcube:/var/log/roundcube
    depends_on:
      - mariadb
      - dovecot
      - postfix
    healthcheck:
      test: ["CMD", "curl", "-f", "http://localhost/"]
      interval: 30s
      timeout: 10s
      retries: 3
      start_period: 40s

  # Nginx Reverse Proxy
  nginx:
    image: nginx:1.26-alpine
    container_name: mailserver-nginx
    hostname: nginx
    restart: always
    networks:
      mailserver_network:
        ipv4_address: 172.20.0.10
    ports:
      - "80:80"
      - "443:443"
    environment:
      - TZ=${TZ}
    volumes:
      - ./config/nginx/nginx.conf:/etc/nginx/nginx.conf:ro
      - ./config/nginx/conf.d:/etc/nginx/conf.d:ro
      - /var/lib/tailscale/certs:/var/lib/tailscale/certs:ro
      - ./logs/nginx:/var/log/nginx
    depends_on:
      - roundcube
    healthcheck:
      test: ["CMD", "wget", "--quiet", "--tries=1", "--spider", "http://localhost/"]
      interval: 30s
      timeout: 10s
      retries: 3
      start_period: 40s
EOF

# docker-compose.ymlのシンタックスチェック
cd /opt/onprem-infra-system/project-root-infra/services/mailserver
docker compose config
```

### 6.6 Dell メールサーバー起動と検証

#### 6.6.1 コンテナ起動

```bash
cd /opt/onprem-infra-system/project-root-infra/services/mailserver

# 全サービス起動
docker compose up -d

# 初回起動ログ確認（イメージプル状況）
docker compose logs --tail=100
```

#### 6.6.2 起動検証スクリプト作成

```bash
# 自動化された起動検証スクリプト作成
cat > ~/validate-docker-services.sh << 'EOF'
#!/bin/bash
set -e

COMPOSE_DIR="/opt/onprem-infra-system/project-root-infra/services/mailserver"
MAX_WAIT=180  # 最大3分待機

cd $COMPOSE_DIR

echo "=== Docker Compose サービス起動検証 ==="
echo "検証開始時刻: $(date)"
echo ""

# 全サービスリスト
SERVICES=("mariadb" "postfix" "dovecot" "roundcube" "rspamd" "clamav" "nginx")

# 起動待機（最大3分）
echo "⏳ サービス起動待機中..."
ELAPSED=0
while [ $ELAPSED -lt $MAX_WAIT ]; do
  ALL_RUNNING=true

  for SERVICE in "${SERVICES[@]}"; do
    STATUS=$(docker compose ps $SERVICE --format json | jq -r '.[0].State' 2>/dev/null || echo "missing")
    if [ "$STATUS" != "running" ]; then
      ALL_RUNNING=false
      break
    fi
  done

  if [ "$ALL_RUNNING" = true ]; then
    echo "✅ 全サービスが起動しました（${ELAPSED}秒経過）"
    break
  fi

  sleep 5
  ELAPSED=$((ELAPSED + 5))
  echo "   待機中... ${ELAPSED}/${MAX_WAIT}秒"
done

if [ $ELAPSED -ge $MAX_WAIT ]; then
  echo "❌ タイムアウト: 一部のサービスが起動しませんでした"
  docker compose ps
  exit 1
fi

echo ""
echo "=== サービス個別ヘルスチェック ==="

# MariaDB ヘルスチェック
echo -n "MariaDB: "
MARIADB_HEALTH=$(docker inspect mailserver-mariadb --format='{{.State.Health.Status}}' 2>/dev/null || echo "no-healthcheck")
if [ "$MARIADB_HEALTH" = "healthy" ]; then
  echo "✅ Healthy"
else
  echo "⚠️ Status: $MARIADB_HEALTH"
fi

# Postfix ポート確認
echo -n "Postfix (Port 587): "
POSTFIX_PORT=$(docker compose ps postfix --format json | jq -r '.[0].Publishers[] | select(.TargetPort==587) | .PublishedPort' 2>/dev/null || echo "missing")
if [ "$POSTFIX_PORT" = "587" ]; then
  echo "✅ Listening on 0.0.0.0:587"
else
  echo "❌ Port 587 not exposed"
  exit 1
fi

# Dovecot LMTP ポート確認
echo -n "Dovecot (Port 2525 LMTP): "
DOVECOT_PORT=$(docker compose ps dovecot --format json | jq -r '.[0].Publishers[] | select(.TargetPort==2525) | .PublishedPort' 2>/dev/null || echo "missing")
if [ "$DOVECOT_PORT" = "2525" ]; then
  echo "✅ Listening on 0.0.0.0:2525"
else
  echo "❌ Port 2525 (LMTP) not exposed"
  exit 1
fi

# Roundcube ポート確認
echo -n "Roundcube (Port 8080): "
ROUNDCUBE_PORT=$(docker compose ps roundcube --format json | jq -r '.[0].Publishers[] | select(.TargetPort==8080) | .PublishedPort' 2>/dev/null || echo "missing")
if [ "$ROUNDCUBE_PORT" = "8080" ]; then
  echo "✅ Listening on 0.0.0.0:8080"
else
  echo "⚠️ Port 8080 not exposed (check nginx proxy)"
fi

# Nginx ポート確認
echo -n "Nginx (Port 80/443): "
NGINX_PORT_80=$(docker compose ps nginx --format json | jq -r '.[0].Publishers[] | select(.TargetPort==80) | .PublishedPort' 2>/dev/null || echo "missing")
NGINX_PORT_443=$(docker compose ps nginx --format json | jq -r '.[0].Publishers[] | select(.TargetPort==443) | .PublishedPort' 2>/dev/null || echo "missing")
if [ "$NGINX_PORT_80" = "80" ] && [ "$NGINX_PORT_443" = "443" ]; then
  echo "✅ Listening on 0.0.0.0:80 and 0.0.0.0:443"
else
  echo "⚠️ HTTP/HTTPS ports not fully exposed"
fi

# Rspamd 起動確認
echo -n "Rspamd: "
RSPAMD_STATUS=$(docker compose ps rspamd --format json | jq -r '.[0].State' 2>/dev/null || echo "missing")
if [ "$RSPAMD_STATUS" = "running" ]; then
  echo "✅ Running"
else
  echo "❌ Status: $RSPAMD_STATUS"
  exit 1
fi

# ClamAV 起動確認
echo -n "ClamAV: "
CLAMAV_STATUS=$(docker compose ps clamav --format json | jq -r '.[0].State' 2>/dev/null || echo "missing")
if [ "$CLAMAV_STATUS" = "running" ]; then
  echo "✅ Running"
else
  echo "❌ Status: $CLAMAV_STATUS"
  exit 1
fi

echo ""
echo "=== ボリューム検証 ==="
VOLUMES=("mail_data" "db_data" "rspamd_data" "clamav_data")
for VOL in "${VOLUMES[@]}"; do
  VOL_PATH=$(docker volume inspect mailserver_$VOL --format '{{.Mountpoint}}' 2>/dev/null || echo "missing")
  if [ "$VOL_PATH" != "missing" ]; then
    echo "✅ $VOL: $VOL_PATH"
  else
    echo "❌ $VOL: Volume not found"
    exit 1
  fi
done

echo ""
echo "=== 検証サマリー ==="
echo "✅ 全サービスが正常に起動しました"
echo "✅ 全ポートが適切に公開されています"
echo "✅ 全ボリュームがマウントされています"
echo ""
echo "次のステップ:"
echo "1. セクション 6.7: Postfix SASL認証ファイル生成"
echo "2. セクション 6.8: ユーザー作成"
echo "3. セクション 7: Fargate ↔ Dell 統合テスト"
EOF

chmod +x ~/validate-docker-services.sh

# 検証実行
~/validate-docker-services.sh
```

**期待される出力**:
```
=== Docker Compose サービス起動検証 ===
検証開始時刻: 2025-11-02 12:00:00

⏳ サービス起動待機中...
✅ 全サービスが起動しました（45秒経過）

=== サービス個別ヘルスチェック ===
MariaDB: ✅ Healthy
Postfix (Port 587): ✅ Listening on 0.0.0.0:587
Dovecot (Port 2525 LMTP): ✅ Listening on 0.0.0.0:2525
Roundcube (Port 8080): ✅ Listening on 0.0.0.0:8080
Nginx (Port 80/443): ✅ Listening on 0.0.0.0:80 and 0.0.0.0:443
Rspamd: ✅ Running
ClamAV: ✅ Running

=== ボリューム検証 ===
✅ mail_data: /opt/onprem-infra-system/project-root-infra/services/mailserver/data/mail
✅ db_data: /opt/onprem-infra-system/project-root-infra/services/mailserver/data/db
✅ rspamd_data: /opt/onprem-infra-system/project-root-infra/services/mailserver/data/rspamd
✅ clamav_data: /opt/onprem-infra-system/project-root-infra/services/mailserver/data/clamav

=== 検証サマリー ===
✅ 全サービスが正常に起動しました
✅ 全ポートが適切に公開されています
✅ 全ボリュームがマウントされています

次のステップ:
1. セクション 6.7: Postfix SASL認証ファイル生成
2. セクション 6.8: ユーザー作成
3. セクション 7: Fargate ↔ Dell 統合テスト
```

**⚠️ 検証失敗時のトラブルシューティング**:

```bash
# 特定サービスのログ確認
docker compose logs <service-name> --tail=100

# 全サービス状態確認
docker compose ps

# コンテナ再起動
docker compose restart <service-name>

# 完全再起動
docker compose down
docker compose up -d
~/validate-docker-services.sh
```

### 6.7 Postfix SASL認証ファイル生成

```bash
# Postfixコンテナ内でpostmapコマンド実行
docker exec mailserver-postfix postmap /etc/postfix/custom/sasl_passwd

# Postfix再起動
docker compose restart postfix

# Postfix設定確認
docker exec mailserver-postfix postconf | grep relay
```

### 6.8 ユーザー作成

#### ユーザー追加スクリプト作成

```bash
cat > /opt/onprem-infra-system/project-root-infra/services/mailserver/scripts/add-user.sh << 'EOF'
#!/bin/bash
# メールユーザー追加スクリプト

EMAIL=$1
PASSWORD=$2

if [ -z "$EMAIL" ] || [ -z "$PASSWORD" ]; then
    echo "Usage: $0 <email> <password>"
    exit 1
fi

DOMAIN=$(echo $EMAIL | cut -d@ -f2)
USER=$(echo $EMAIL | cut -d@ -f1)

# Dovecot users ファイルにユーザー追加
HASH=$(docker run --rm -it dovecot/dovecot doveadm pw -s SHA512-CRYPT -p $PASSWORD | tr -d '\r')
echo "$EMAIL:$HASH:5000:5000::/var/mail/vhosts/$DOMAIN/$USER::" \
  >> /opt/onprem-infra-system/project-root-infra/services/mailserver/config/dovecot/users

# メールディレクトリ作成
mkdir -p /opt/onprem-infra-system/project-root-infra/services/mailserver/data/mail/$DOMAIN/$USER/{cur,new,tmp}
chown -R 5000:5000 /opt/onprem-infra-system/project-root-infra/services/mailserver/data/mail/$DOMAIN/$USER

# サービス再起動
docker compose restart dovecot postfix

echo "User $EMAIL added successfully"
EOF

chmod +x /opt/onprem-infra-system/project-root-infra/services/mailserver/scripts/add-user.sh
```

#### 初期ユーザー作成

```bash
# Dovecot usersファイル作成
touch /opt/onprem-infra-system/project-root-infra/services/mailserver/config/dovecot/users
chmod 600 /opt/onprem-infra-system/project-root-infra/services/mailserver/config/dovecot/users

# 各ドメインでテストユーザー追加例
/opt/onprem-infra-system/project-root-infra/services/mailserver/scripts/add-user.sh admin@kuma8088.com YourStrongPassword1!
/opt/onprem-infra-system/project-root-infra/services/mailserver/scripts/add-user.sh admin@fx-trader-life.com YourStrongPassword2!

# ⚠️ パスワードを実際の強力なパスワードに置換してください
```

---

## 7. 統合テスト

### 7.1 Fargate Task Definition作成

```bash
# Task Definitionファイル作成
cat > /tmp/fargate-task-definition.json << EOF
{
  "family": "mailserver-mx-task",
  "networkMode": "awsvpc",
  "requiresCompatibilities": ["FARGATE"],
  "cpu": "256",
  "memory": "512",
  "executionRoleArn": "$EXECUTION_ROLE_ARN",
  "taskRoleArn": "$TASK_ROLE_ARN",
  "containerDefinitions": [
    {
      "name": "postfix",
      "image": "postfix:3.8-alpine",
      "essential": true,
      "environment": [
        {
          "name": "RELAY_HOST",
          "value": "mailserver.tail67811d.ts.net:2525"
        },
        {
          "name": "RELAY_PROTOCOLS",
          "value": "lmtp"
        }
      ],
      "portMappings": [
        {
          "containerPort": 25,
          "protocol": "tcp"
        }
      ],
      "healthCheck": {
        "command": ["CMD-SHELL", "nc -z localhost 25 || exit 1"],
        "interval": 30,
        "timeout": 5,
        "retries": 3,
        "startPeriod": 60
      },
      "logConfiguration": {
        "logDriver": "awslogs",
        "options": {
          "awslogs-group": "/ecs/mailserver-mx",
          "awslogs-region": "ap-northeast-1",
          "awslogs-stream-prefix": "postfix"
        }
      }
    },
    {
      "name": "tailscale",
      "image": "tailscale/tailscale:stable",
      "essential": true,
      "secrets": [
        {
          "name": "TS_AUTHKEY",
          "valueFrom": "$TS_SECRET_ARN"
        }
      ],
      "environment": [
        {
          "name": "TS_STATE_DIR",
          "value": "/var/lib/tailscale"
        },
        {
          "name": "TS_USERSPACE",
          "value": "true"
        }
      ],
      "logConfiguration": {
        "logDriver": "awslogs",
        "options": {
          "awslogs-group": "/ecs/mailserver-mx",
          "awslogs-region": "ap-northeast-1",
          "awslogs-stream-prefix": "tailscale"
        }
      }
    }
  ]
}
EOF

# ⚠️ RELAY_HOSTを実際のDell Tailscale MagicDNS名に変更
MAGICDNS_NAME=$(tailscale status --json | jq -r '.Self.DNSName')
sed -i "s/mailserver\.tail67811d\.ts\.net/$MAGICDNS_NAME/g" /tmp/fargate-task-definition.json

# Task Definition登録
aws ecs register-task-definition \
  --cli-input-json file:///tmp/fargate-task-definition.json

# Task Definition ARN取得
TASK_DEF_ARN=$(aws ecs list-task-definitions \
  --family-prefix mailserver-mx-task \
  --query 'taskDefinitionArns[0]' \
  --output text)

echo "Task Definition ARN: $TASK_DEF_ARN"

# クリーンアップ
rm /tmp/fargate-task-definition.json
```

### 7.2 ECS Service作成（Public IP Fargate構成）

```bash
# ECS Service作成（ALB不使用、Public IP直接受信）
aws ecs create-service \
  --cluster mailserver-cluster \
  --service-name mailserver-mx-service \
  --task-definition $TASK_DEF_ARN \
  --desired-count 1 \
  --launch-type FARGATE \
  --network-configuration "awsvpcConfiguration={subnets=[$SUBNET_1,$SUBNET_2],securityGroups=[$FARGATE_SG_ID],assignPublicIp=ENABLED}"

# Service起動確認
aws ecs describe-services \
  --cluster mailserver-cluster \
  --services mailserver-mx-service

# Task起動確認（1-2分待機）
watch -n 5 'aws ecs list-tasks --cluster mailserver-cluster --service-name mailserver-mx-service'

# TaskのPublic IP取得
TASK_ARN=$(aws ecs list-tasks \
  --cluster mailserver-cluster \
  --service-name mailserver-mx-service \
  --query 'taskArns[0]' \
  --output text)

ENI_ID=$(aws ecs describe-tasks \
  --cluster mailserver-cluster \
  --tasks $TASK_ARN \
  --query 'tasks[0].attachments[0].details[?name==`networkInterfaceId`].value' \
  --output text)

FARGATE_PUBLIC_IP=$(aws ec2 describe-network-interfaces \
  --network-interface-ids $ENI_ID \
  --query 'NetworkInterfaces[0].Association.PublicIp' \
  --output text)

echo "⚠️ 重要: Fargate Task Public IP: $FARGATE_PUBLIC_IP"
echo "⚠️ このIPアドレスをMXレコードに設定してください"
echo "⚠️ 注意: Taskが再起動するとPublic IPは変わります（Elastic IP使用を推奨）"
```

**🔄 Elastic IP使用の場合**:

```bash
# 既に作成したElastic IPをENIに関連付け
aws ec2 associate-address \
  --allocation-id $EIP_ALLOC_ID \
  --network-interface-id $ENI_ID

# Elastic IP関連付け確認
aws ec2 describe-addresses --allocation-ids $EIP_ALLOC_ID

echo "✅ Elastic IP ($ELASTIC_IP) がFargateタスクに関連付けられました"
echo "⚠️ MXレコードに設定するIPアドレス: $ELASTIC_IP"
```

### 7.3 DNS設定（MXレコード）

**⚠️ 重要**: このセクションでは、セクション3.1で取得したElastic IPをMXレコードに設定します。

**前提条件**:
- ✅ セクション3.1 Terraform apply完了（Elastic IP取得済み）
- ✅ セクション7.2 ECS Service作成完了（Fargateタスク起動済み）
- ✅ 環境変数 `$ELASTIC_IP` が設定されていること（セクション3.1で設定）

**依存関係**:
```
セクション3.1: Terraform apply → Elastic IP取得 ($ELASTIC_IP)
    ↓
セクション7.2: ECS Service作成 → Fargateタスク起動
    ↓
セクション7.3: DNS設定 → MXレコードに $ELASTIC_IP を設定
```

#### Option 1: Elastic IP使用の場合（推奨）

```bash
# 0. Elastic IP確認（セクション3.1で取得した値）
echo "設定するElastic IP: $ELASTIC_IP"
# 期待値例: 54.123.45.67

# ⚠️ この値をメモしてDNS設定に使用してください

# 1. Cloudflare管理画面にログイン
# 2. kuma8088.comドメインを選択
# 3. DNS → Records → Add record

# Aレコード追加（Elastic IP用）
# Type: A
# Name: mx
# IPv4 address: $ELASTIC_IP の値を入力 (例: 54.123.45.67)
# TTL: Auto

# MXレコード追加
# Type: MX
# Name: @
# Mail server: mx.kuma8088.com
# Priority: 10
# TTL: Auto

# 追加ドメインも同様にAレコード + MXレコード設定
# - fx-trader-life.com → mx.fx-trader-life.com → $ELASTIC_IP
# - webmakeprofit.org → mx.webmakeprofit.org → $ELASTIC_IP
# - webmakesprofit.com → mx.webmakesprofit.com → $ELASTIC_IP
```

#### Option 2: Dynamic Public IP使用の場合（非推奨）

```bash
# ⚠️ Taskが再起動するたびにPublic IPが変わるため、手動更新が必要

# Aレコード追加（現在のPublic IP）
# Type: A
# Name: mx
# IPv4 address: <FARGATE_PUBLIC_IP> (例: 3.234.56.78)
# TTL: 300 (5分) ← 短いTTLを設定

# MXレコード追加
# Type: MX
# Name: @
# Mail server: mx.kuma8088.com
# Priority: 10
# TTL: Auto
```

#### DNS設定確認

```bash
# MXレコード確認
dig MX kuma8088.com

# 期待される出力:
# kuma8088.com.  300  IN  MX  10 mx.kuma8088.com.

# Aレコード確認
dig A mx.kuma8088.com

# 期待される出力:
# mx.kuma8088.com.  300  IN  A  <ELASTIC_IP>
```

### 7.4 統合テスト実施

#### Fargate → Dell LMTP転送テスト

```bash
# 外部からPort 25経由でテストメール送信
# Gmailなどから kuma8088.com ドメイン宛にメール送信

# Dell側ログ確認
docker compose logs dovecot | grep -i lmtp
docker compose logs rspamd | tail -50

# メールボックス確認
ls -la /opt/onprem-infra-system/project-root-infra/services/mailserver/data/mail/kuma8088.com/admin/new/
```

#### Dell → SendGrid送信テスト

```bash
# WEBメール（https://${MAGICDNS_NAME}）からログイン
# admin@kuma8088.com で外部アドレス宛に送信

# Dell側Postfixログ確認
docker compose logs postfix | grep -i sendgrid

# SendGrid Activity確認
# SendGridコンソール: Activity → Email Activity
```

#### WEBメールアクセステスト

```bash
# ブラウザで以下にアクセス（Tailscaleクライアントから）
# https://${MAGICDNS_NAME}

# ログイン情報:
# ユーザー名: admin@kuma8088.com
# パスワード: YourStrongPassword1!
```

---

## 8. 自動化設定

### 8.1 バックアップスクリプト作成

```bash
cat > /opt/onprem-infra-system/project-root-infra/services/mailserver/scripts/backup.sh << 'EOF'
#!/bin/bash
# メールサーバーバックアップスクリプト

BACKUP_DIR="/opt/onprem-infra-system/project-root-infra/services/mailserver/backups"
DATE=$(date +%Y%m%d_%H%M%S)

# バックアップディレクトリ確認
mkdir -p $BACKUP_DIR

# メールデータバックアップ
echo "Backing up mail data..."
tar -czf $BACKUP_DIR/mail_$DATE.tar.gz -C /opt/onprem-infra-system/project-root-infra/services/mailserver/data mail/

# データベースバックアップ
echo "Backing up database..."
docker exec mailserver-mariadb mysqldump -u root -p$MYSQL_ROOT_PASSWORD roundcube \
  > $BACKUP_DIR/db_$DATE.sql

# 設定ファイルバックアップ
echo "Backing up config..."
tar -czf $BACKUP_DIR/config_$DATE.tar.gz -C /opt/onprem-infra-system/project-root-infra/services/mailserver config/

# Tailscale証明書バックアップ
echo "Backing up Tailscale certs..."
tar -czf $BACKUP_DIR/tailscale_certs_$DATE.tar.gz /var/lib/tailscale/certs/

# 7日以上前のバックアップ削除
echo "Cleaning old backups..."
find $BACKUP_DIR -name "*.tar.gz" -mtime +7 -delete
find $BACKUP_DIR -name "*.sql" -mtime +7 -delete

echo "Backup completed: $DATE"
EOF

chmod +x /opt/onprem-infra-system/project-root-infra/services/mailserver/scripts/backup.sh

# バックアップテスト実行
/opt/onprem-infra-system/project-root-infra/services/mailserver/scripts/backup.sh
```

### 8.2 Tailscale証明書更新スクリプト

```bash
cat > /opt/onprem-infra-system/project-root-infra/services/mailserver/scripts/tailscale-renew.sh << 'EOF'
#!/bin/bash
# Tailscale HTTPS証明書更新スクリプト

set -euo pipefail

MAGICDNS_NAME=$(tailscale status --json | jq -r '.Self.DNSName')
CERT_DIR="/var/lib/tailscale/certs"

tailscale cert --cert-file ${CERT_DIR}/${MAGICDNS_NAME}.crt \
               --key-file  ${CERT_DIR}/${MAGICDNS_NAME}.key \
               "${MAGICDNS_NAME}"

# サービスへ反映
docker restart mailserver-nginx mailserver-postfix mailserver-dovecot
EOF

chmod +x /opt/onprem-infra-system/project-root-infra/services/mailserver/scripts/tailscale-renew.sh

# 証明書更新テスト
/opt/onprem-infra-system/project-root-infra/services/mailserver/scripts/tailscale-renew.sh
```

### 8.3 cron設定

```bash
# cron設定追加
crontab -e

# 以下を追加:
# 毎日深夜3:00にバックアップ実行
0 3 * * * /opt/onprem-infra-system/project-root-infra/services/mailserver/scripts/backup.sh >> /opt/onprem-infra-system/project-root-infra/services/mailserver/logs/backup.log 2>&1

# Tailscale証明書自動更新（日次）
30 3 * * * /opt/onprem-infra-system/project-root-infra/services/mailserver/scripts/tailscale-renew.sh >> /opt/onprem-infra-system/project-root-infra/services/mailserver/logs/tailscale-cert.log 2>&1

# cron設定確認
crontab -l
```

### 8.4 Infrastructure Drift検出（推奨: 週次実行）

```bash
# Terraform管理リソースの構成ドリフト検出スクリプト作成
cat > ~/check-infrastructure-drift.sh << 'EOF'
#!/bin/bash
set -e

cd /opt/onprem-infra-system/project-root-infra/services/mailserver/terraform

echo "=== Infrastructure Drift Detection ==="
echo "実行日時: $(date)"
echo ""

# Terraform管理リソースのドリフト検出
echo "📊 Terraform管理リソースの検証中..."
terraform plan -detailed-exitcode > /dev/null 2>&1
EXIT_CODE=$?

if [ $EXIT_CODE -eq 0 ]; then
  echo "✅ Terraform管理リソース: ドリフトなし"
elif [ $EXIT_CODE -eq 2 ]; then
  echo "⚠️ Terraform管理リソース: 構成ドリフト検出"
  echo "   詳細確認: terraform plan"
  echo "   修正方法: terraform apply で構成を修正"
else
  echo "❌ Terraform管理リソース: エラー発生"
  echo "   詳細確認: terraform plan"
  exit 1
fi

echo ""

# 手動管理リソースの存在確認
echo "📋 手動管理リソースの検証中..."

# Secrets Manager検証
echo -n "Secrets Manager Secrets: "
SECRET_COUNT=$(aws secretsmanager list-secrets \
  --filters Key=name,Values=mailserver/ \
  --query 'length(SecretList)' --output text)

if [ "$SECRET_COUNT" -ge 2 ]; then
  echo "✅ 必要なSecrets存在 ($SECRET_COUNT個)"
else
  echo "⚠️ Secrets不足 (期待値: 2個以上、実際: $SECRET_COUNT個)"
  echo "   確認: aws secretsmanager list-secrets --filters Key=name,Values=mailserver/"
fi

# ECS Service検証
echo -n "ECS Service: "
SERVICE_STATUS=$(aws ecs describe-services \
  --cluster mailserver-cluster \
  --services mailserver-mx-service \
  --query 'services[0].status' --output text 2>/dev/null || echo "NOT_FOUND")

if [ "$SERVICE_STATUS" == "ACTIVE" ]; then
  DESIRED=$(aws ecs describe-services \
    --cluster mailserver-cluster \
    --services mailserver-mx-service \
    --query 'services[0].desiredCount' --output text)
  RUNNING=$(aws ecs describe-services \
    --cluster mailserver-cluster \
    --services mailserver-mx-service \
    --query 'services[0].runningCount' --output text)

  if [ "$DESIRED" -eq "$RUNNING" ]; then
    echo "✅ 正常稼働 (Desired: $DESIRED, Running: $RUNNING)"
  else
    echo "⚠️ タスク数不一致 (Desired: $DESIRED, Running: $RUNNING)"
  fi
else
  echo "❌ Serviceが存在しないか、ACTIVE状態ではありません (Status: $SERVICE_STATUS)"
fi

echo ""
echo "=== 検出サマリー ==="
if [ $EXIT_CODE -eq 0 ] && [ "$SECRET_COUNT" -ge 2 ] && [ "$SERVICE_STATUS" == "ACTIVE" ]; then
  echo "✅ 全リソースの構成が正常です"
else
  echo "⚠️ 一部リソースに構成ドリフトまたは異常が検出されました"
  echo "   詳細は上記の検証結果を確認してください"
fi
EOF

chmod +x ~/check-infrastructure-drift.sh

# 手動実行テスト
~/check-infrastructure-drift.sh

# cron設定追加（週次実行: 毎週日曜日 AM 2:00）
crontab -e

# 以下を追加:
# 毎週日曜日 AM 2:00 に Infrastructure Drift検出
0 2 * * 0 ~/check-infrastructure-drift.sh >> /var/log/infrastructure-drift.log 2>&1
```

**期待される出力**:
```
=== Infrastructure Drift Detection ===
実行日時: 2025-11-02 02:00:00

📊 Terraform管理リソースの検証中...
✅ Terraform管理リソース: ドリフトなし

📋 手動管理リソースの検証中...
Secrets Manager Secrets: ✅ 必要なSecrets存在 (2個)
ECS Service: ✅ 正常稼働 (Desired: 1, Running: 1)

=== 検出サマリー ===
✅ 全リソースの構成が正常です
```

### 8.5 CloudWatch Logs運用要件

**ログ保持期間**: 30日（Terraform設定済み）
- 理由: コスト最適化（1ヶ月以上の調査は稀）
- 長期保存が必要な場合: S3エクスポート設定を検討

**推奨アラート設定**（手動設定が必要）:

#### Postfixエラーログ検出

```bash
# メトリックフィルタ作成
aws logs put-metric-filter \
  --log-group-name /ecs/mailserver-mx \
  --filter-name PostfixErrors \
  --filter-pattern '[time, container=postfix, level=error, ...]' \
  --metric-transformations \
    metricName=PostfixErrorCount,metricNamespace=Mailserver,metricValue=1

# CloudWatch Alarm作成
aws cloudwatch put-metric-alarm \
  --alarm-name PostfixHighErrorRate \
  --alarm-description "Alert when Postfix errors exceed threshold" \
  --metric-name PostfixErrorCount \
  --namespace Mailserver \
  --statistic Sum \
  --period 300 \
  --threshold 10 \
  --comparison-operator GreaterThanThreshold \
  --evaluation-periods 1 \
  --alarm-actions <SNS_TOPIC_ARN>
```

#### Tailscale接続エラー検出

```bash
# メトリックフィルタ作成
aws logs put-metric-filter \
  --log-group-name /ecs/mailserver-mx \
  --filter-name TailscaleConnectionErrors \
  --filter-pattern '[time, container=tailscale, level, msg="*connection*failed*"]' \
  --metric-transformations \
    metricName=TailscaleErrorCount,metricNamespace=Mailserver,metricValue=1

# CloudWatch Alarm作成
aws cloudwatch put-metric-alarm \
  --alarm-name TailscaleConnectionFailure \
  --alarm-description "Alert when Tailscale VPN connection fails" \
  --metric-name TailscaleErrorCount \
  --namespace Mailserver \
  --statistic Sum \
  --period 300 \
  --threshold 5 \
  --comparison-operator GreaterThanThreshold \
  --evaluation-periods 1 \
  --alarm-actions <SNS_TOPIC_ARN>
```

### 8.6 CloudWatch Alarms設定（Public IP Fargate構成）

```bash
# SNSトピック作成
SNS_TOPIC_ARN=$(aws sns create-topic \
  --name mailserver-alerts \
  --query 'TopicArn' \
  --output text)

echo "SNS Topic ARN: $SNS_TOPIC_ARN"

# メールサブスクリプション作成
aws sns subscribe \
  --topic-arn $SNS_TOPIC_ARN \
  --protocol email \
  --notification-endpoint naoya.iimura@gmail.com

# ⚠️ メール確認してサブスクリプション承認してください

# FargateTaskStopped アラーム作成（ALB不使用のためTask停止を監視）
aws cloudwatch put-metric-alarm \
  --alarm-name FargateTaskStopped \
  --alarm-description "Alert when Fargate task count drops to zero" \
  --metric-name DesiredTaskCount \
  --namespace AWS/ECS \
  --statistic Average \
  --period 60 \
  --threshold 1 \
  --comparison-operator LessThanThreshold \
  --evaluation-periods 1 \
  --dimensions Name=ServiceName,Value=mailserver-mx-service Name=ClusterName,Value=mailserver-cluster \
  --alarm-actions $SNS_TOPIC_ARN

# FargateHighCPU アラーム作成
aws cloudwatch put-metric-alarm \
  --alarm-name FargateHighCPU \
  --alarm-description "Alert when Fargate CPU exceeds 80%" \
  --metric-name CPUUtilization \
  --namespace AWS/ECS \
  --statistic Average \
  --period 600 \
  --threshold 80 \
  --comparison-operator GreaterThanThreshold \
  --evaluation-periods 1 \
  --dimensions Name=ServiceName,Value=mailserver-mx-service Name=ClusterName,Value=mailserver-cluster \
  --alarm-actions $SNS_TOPIC_ARN

# FargateHighMemory アラーム作成
aws cloudwatch put-metric-alarm \
  --alarm-name FargateHighMemory \
  --alarm-description "Alert when Fargate Memory exceeds 80%" \
  --metric-name MemoryUtilization \
  --namespace AWS/ECS \
  --statistic Average \
  --period 600 \
  --threshold 80 \
  --comparison-operator GreaterThanThreshold \
  --evaluation-periods 1 \
  --dimensions Name=ServiceName,Value=mailserver-mx-service Name=ClusterName,Value=mailserver-cluster \
  --alarm-actions $SNS_TOPIC_ARN

# アラーム一覧確認
aws cloudwatch describe-alarms --alarm-names FargateTaskStopped FargateHighCPU FargateHighMemory
```

**📊 監視メトリクス説明**:
- **FargateTaskStopped**: タスクが停止した場合に即座にアラート（ALB不使用のため、タスク停止=メール受信停止）
- **FargateHighCPU**: CPU使用率が80%を超えた場合にアラート（スケールアップ検討）
- **FargateHighMemory**: メモリ使用率が80%を超えた場合にアラート（スケールアップ検討）

---

## 9. トラブルシューティング

### 9.1 Fargateタスクが起動しない

```bash
# タスク起動状態確認
aws ecs list-tasks --cluster mailserver-cluster --service-name mailserver-mx-service

# タスク詳細確認
TASK_ARN=$(aws ecs list-tasks --cluster mailserver-cluster --service-name mailserver-mx-service --query 'taskArns[0]' --output text)
aws ecs describe-tasks --cluster mailserver-cluster --tasks $TASK_ARN

# CloudWatch Logs確認
aws logs tail /ecs/mailserver-mx --follow

# Tailscale接続確認
aws logs filter-log-events \
  --log-group-name /ecs/mailserver-mx \
  --filter-pattern "tailscale" \
  --max-items 50
```

### 9.2 メール受信できない（Fargate → Dell）

#### Public IP疎通確認

```bash
# Fargate Task Public IP確認
TASK_ARN=$(aws ecs list-tasks --cluster mailserver-cluster --service-name mailserver-mx-service --query 'taskArns[0]' --output text)
ENI_ID=$(aws ecs describe-tasks --cluster mailserver-cluster --tasks $TASK_ARN --query 'tasks[0].attachments[0].details[?name==`networkInterfaceId`].value' --output text)
FARGATE_PUBLIC_IP=$(aws ec2 describe-network-interfaces --network-interface-ids $ENI_ID --query 'NetworkInterfaces[0].Association.PublicIp' --output text)

echo "Fargate Public IP: $FARGATE_PUBLIC_IP"

# 外部からSMTP Port 25疎通確認
telnet $FARGATE_PUBLIC_IP 25
# または
nc -zv $FARGATE_PUBLIC_IP 25
```

#### Fargate → Dell LMTP転送確認

```bash
# Dell側LMTP待受確認
docker exec mailserver-dovecot netstat -tuln | grep 2525

# Tailscale接続確認（Dell）
tailscale status

# Dovecot LMTPログ確認
docker compose logs dovecot | grep -i lmtp

# Fargate → Dell疎通確認（Fargate側）
# ⚠️ Fargateタスク内でテスト実施が必要（ECS Exec有効化が必要）
```

#### DNS設定確認

```bash
# MXレコード確認
dig MX kuma8088.com

# Aレコード確認（Elastic IP使用の場合）
dig A mx.kuma8088.com

# 外部DNSサーバーからの確認
dig @8.8.8.8 MX kuma8088.com
```

### 9.3 メール送信できない（Dell → SendGrid）

```bash
# Postfixログ確認
docker compose logs postfix | grep -i sendgrid

# SendGrid認証確認
docker exec mailserver-postfix postconf | grep relay

# SendGrid APIキー確認
cat /opt/onprem-infra-system/project-root-infra/services/mailserver/config/postfix/sasl_passwd

# SendGrid Activity確認
# SendGridコンソール: Activity → Email Activity
```

### 9.4 WEBメールアクセスできない

```bash
# Nginxログ確認
docker compose logs nginx | tail -50

# Roundcubeログ確認
docker compose logs roundcube | tail -50

# Tailscale証明書確認
ls -la /var/lib/tailscale/certs/

# Tailscale接続確認
tailscale status
```

### 9.5 DNSレコード確認

```bash
# MXレコード確認
dig MX kuma8088.com

# SPFレコード確認（SendGrid）
dig TXT kuma8088.com | grep sendgrid

# DKIMレコード確認（SendGrid）
dig CNAME s1._domainkey.kuma8088.com

# DMARCレコード確認
dig TXT _dmarc.kuma8088.com
```

---

## 10. 次のステップ

構築が完了したら、以下を実施してください：

1. **テスト手順書実行**: `Docs/application/mailserver/05_testing.md`
2. **監視設定**: CloudWatch Alarms、SNS通知の動作確認
3. **セキュリティ強化**: IAMポリシーの最小権限化、Secrets Managerローテーション設定
4. **ドキュメント更新**: 実際の設定値（ARN、DNS名等）をドキュメントに反映

---

## 11. 承認

| 役割 | 氏名 | 承認日 | 署名 |
|------|------|--------|------|
| 作成者 | Claude | 2025-11-02 | ✓ |
| レビュアー |  |  |  |
| 実施者 |  |  |  |

---

## 12. 文書改訂履歴

| バージョン | 日付 | 変更内容 | 作成者 | 参照文書 |
|-----------|------|----------|--------|----------|
| 1.0 | 2025-10-31 | 初版作成 | Claude | - |
| 2.0 | 2025-11-01 | マルチドメイン対応（4ドメイン）、Rspamd/ClamAV統合、Postfix milter設定追加、NTT RX-600KI固定IP対応、Cloudflare DNS管理対応 | Claude | 01_requirements.md v2.1、02_design.md v2.3、03_Firewall(RX-600KI).md v1.1 |
| 3.0 | 2025-11-01 | **Tailscale VPN対応への全面改訂**: Tailscale VPN設定セクション追加（6章）、SSL証明書取得をTailscale HTTPSへ変更、Let's Encrypt/Certbot手順削除、ポート転送設定を不要化、MagicDNS対応、Nginx設定をTailscale証明書パスへ更新、DNS設定を外部SMTPリレー前提へ簡素化、動作確認手順をTailscaleクライアント経由へ変更 | Claude | 01_requirements.md v3.0、02_design.md v3.1、03_Firewall(RX-600KI).md v2.1 |
| 3.1 | 2025-11-02 | Tailnet個人運用向けに手順整合（外部SMTP/DNS関連を任意扱いへ整理、Tailscale証明書マウント先と設定を統一、誤記修正、バックアップ・自動化・トラブルシュートを最新構成に更新） | Codex | 01_requirements.md v3.0、02_design.md v3.1、03_Firewall(RX-600KI).md v2.1 |
| 5.0 | 2025-11-02 | **ハイブリッドクラウド構成への全面改訂**: AWS Fargate MX Gateway追加（3章）、SendGrid SMTP Relay統合（4章）、Tailscale VPN Fargate/Dell間接続（5章）、Dell側LMTP受信/Send専用Postfix設定（6章）、統合テスト手順追加（7章）、CloudWatch監視設定追加（8.4章）、MXレコードをALB DNS名へ変更、SendGrid SPF/DKIM/DMARC認証設定追加 | Claude | 01_requirements.md v5.0、02_design.md v5.0、03_Firewall(RX-600KI).md v2.1 |
| 5.1 | 2025-11-02 | **Public IP Fargate構成への簡素化**: ALBをオプション化、Public IP直接受信構成へ変更（3.3章）、Elastic IP割り当てセクション追加（3.5章）、ECS Service作成をALB不使用に更新（7.2章）、DNS設定をPublic IP/Elastic IP対応に変更（7.3章）、CloudWatch AlarmsからALB依存を削除（8.4章）、トラブルシューティングをPublic IP構成に更新（9.2章）、コスト最適化（ALB月額$16.20削減） | Claude | 01_requirements.md v5.0、02_design.md v5.0、03_Firewall(RX-600KI).md v2.1 |
| 5.2 | 2025-11-02 | **品質改善（エキスパートレビュー対応）**: 環境変数検証スクリプト追加（3.1章）、Terraform Apply失敗時復旧手順追加（Given/When/Thenシナリオ形式、3.1章）、MXレコード設定タイミング明記と依存関係図追加（7.3章）、CloudWatch Logs運用要件追加（8.5章）、Infrastructure Drift検出スクリプト追加（8.4章）、Elastic IP関連付けエラー復旧手順追加（トラブルシューティング）、AWS CLI認証確認の前提条件追加（3.1章）、セクション番号調整（8.4→8.6） | Claude | エキスパートパネルレビュー（Wiegers/Adzic/Fowler/Nygard/Hightower）|

**v5.0 主要変更点**:
- **AWS環境構築**: 新規セクション追加（3章）
  - VPC/サブネット/セキュリティグループ作成
  - Application Load Balancer (ALB) 設定
  - ECS Fargate Cluster/Task Definition/Service作成
  - AWS Secrets Manager (Tailscale Auth Key保存)
  - IAM Role (Execution Role/Task Role) 作成
  - CloudWatch Logs設定
- **SendGrid統合**: 新規セクション追加（4章）
  - SendGridアカウント作成/API Key生成
  - ドメイン認証（SPF/DKIM/DMARC）
  - Secrets Manager統合
- **Tailscale VPN拡張**: Fargate対応（5章）
  - Fargate用Ephemeral Auth Key生成
  - Tailscale ACL設定（tag:fargate-mx）
  - Dell側Tailscale接続設定
- **Dell側構成変更**: LMTP受信 + SendGrid送信専用（6章）
  - Dovecot LMTP listener (Port 2525)
  - Postfix SendGrid Relay設定
  - Docker Compose Port mapping更新
- **統合テスト**: 新規セクション追加（7章）
  - Fargate → Dell LMTP転送テスト
  - Dell → SendGrid送信テスト
  - MXレコードDNS設定
- **監視強化**: CloudWatch Alarms追加（8.4章）
  - FargateTaskUnhealthy/FargateHighCPU/FargateHighMemory
  - SNS通知設定
- **DNS設定変更**: MXレコードをALB DNS名に変更
  - SPF/DKIM/DMARCをSendGrid提供値に変更
  - Aレコード/PTRレコード設定削除（Fargate Elastic IP不使用）

**v5.1 主要変更点**:
- **ALBオプション化**: Application Load Balancer を将来の拡張オプションとして位置づけ（3.3章アーキテクチャ図更新）
- **Public IP Fargate構成**: シンプルなPublic IP直接受信構成に変更（当面の運用方針）
- **セキュリティグループ簡素化**: ALB SG削除、Fargate SGのみでPort 25を0.0.0.0/0から許可（3.3章）
- **Elastic IP対応**: オプションで固定IP割り当て可能（3.5章新規追加、月額$3.60）
- **ECS Service更新**: ALB/Target Group参照を削除、Public IP直接割り当て構成へ変更（7.2章）
- **DNS設定更新**: MXレコードをPublic IP/Elastic IPに変更、Aレコード設定追加（7.3章）
- **監視最適化**: FargateTaskUnhealthy アラームを FargateTaskStopped に変更（ALB依存削除、8.4章）
- **トラブルシューティング強化**: Public IP疎通確認、DNS設定確認セクション追加（9.2章）
- **コスト最適化**: ALB月額$16.20削減、Elastic IP使用時は+$3.60/月

**v5.2 主要変更点**（品質改善 - エキスパートレビュー対応）:
- **検証スクリプト追加**: 環境変数フォーマット自動検証（3.1章）
  - VPC ID/Subnet ID/Security Group ID/Elastic IP/IAM Role ARN の正規表現検証
  - セクション7.3（DNS設定）へのElastic IP値引き継ぎを確実化
- **復旧手順体系化**: Terraform Apply失敗時の4シナリオ対応（3.1章）
  - シナリオ1: 正常適用（Given/When/Then形式で成功検証基準明記）
  - シナリオ2: 部分作成済み（差分再適用手順）
  - シナリオ3: State破損（terraform import による復旧）
  - シナリオ4: 完全ロールバック（terraform destroy 前チェックリスト追加）
- **依存関係明確化**: MXレコード設定タイミングと前提条件の可視化（7.3章）
  - セクション3.1 → 7.2 → 7.3 の依存関係図追加
  - 環境変数 $ELASTIC_IP の確認手順追加
- **運用要件追加**: CloudWatch Logs保持期間とアラート設定指針（8.5章新規追加）
  - Postfixエラーログメトリックフィルタ設定
  - Tailscale接続エラーメトリックフィルタ設定
  - 30日保持期間の根拠（コスト最適化）明記
- **構成ドリフト検出**: Infrastructure Drift検出スクリプト（8.4章新規追加）
  - Terraform管理リソースの週次検証（terraform plan -detailed-exitcode）
  - 手動管理リソース存在確認（Secrets Manager、ECS Service）
  - cron設定による自動化（毎週日曜日 AM 2:00）
- **エラー復旧強化**: Elastic IP関連付けエラー復旧手順（トラブルシューティング）
  - 既存関連付け解除手順追加
  - 再関連付けコマンド明記
- **前提条件強化**: AWS CLI認証確認を terraform init 前に明示（3.1章）
  - aws sts get-caller-identity による認証確認
  - 失敗時のエラーメッセージ表示
