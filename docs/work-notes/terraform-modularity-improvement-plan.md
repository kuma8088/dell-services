# Terraform Modularity Improvement Plan

**作成日**: 2025-11-11
**ステータス**: 計画中
**優先度**: MEDIUM
**所要時間**: 約2時間

---

## 📋 概要

現在の `services/mailserver/terraform/main.tf` は400行以上の単一ファイルとなっており、以下の課題がある：

- **再利用性の欠如**: 同様のインフラを構築する際にコピー&ペーストが必要
- **テスト困難**: 個別コンポーネントの単体テストができない
- **保守性の低下**: 複数の関心事が1ファイルに混在
- **パフォーマンス**: 大きなファイルはplan/apply操作が遅い

---

## 🎯 目標

### S3 Backupの良い例に倣う

現在の `services/mailserver/terraform/s3-backup/` は適切にモジュール化されている：

```
s3-backup/
├── main.tf           # リソース定義
├── iam.tf            # IAM定義
├── s3.tf             # S3設定
├── cloudwatch.tf     # 監視設定
├── lifecycle.tf      # ライフサイクル管理
└── variables.tf      # 変数定義
```

### EC2インフラの目標構造

```
services/mailserver/terraform/
├── modules/
│   ├── vpc/
│   │   ├── main.tf
│   │   ├── variables.tf
│   │   ├── outputs.tf
│   │   └── README.md
│   ├── security_groups/
│   │   ├── main.tf
│   │   ├── variables.tf
│   │   ├── outputs.tf
│   │   └── README.md
│   ├── ec2/
│   │   ├── main.tf
│   │   ├── variables.tf
│   │   ├── outputs.tf
│   │   └── README.md
│   └── secrets/
│       ├── main.tf
│       ├── variables.tf
│       ├── outputs.tf
│       └── README.md
├── main.tf           # モジュール呼び出し
├── variables.tf      # ルート変数
├── outputs.tf        # ルート出力
├── locals.tf         # ローカル変数
├── backend.tf        # S3バックエンド設定（オプション）
└── README.md         # インフラ説明
```

---

## 📝 実装手順

### Phase 1: モジュール設計（30分）

1. **現在のリソース分析**
   ```bash
   cd /opt/onprem-infra-system/project-root-infra/services/mailserver/terraform
   terraform state list
   ```

2. **モジュール分割計画**
   - VPCモジュール: VPC, Subnet, IGW, Route Table
   - Security Groupsモジュール: 全SG定義
   - EC2モジュール: EC2インスタンス, EIP, User Data
   - Secretsモジュール: Secrets Manager

3. **依存関係整理**
   ```mermaid
   graph TD
       A[VPC] --> B[Security Groups]
       A --> C[Secrets]
       B --> D[EC2]
       C --> D
   ```

### Phase 2: モジュール実装（60分）

#### 2-1. VPCモジュール作成

```bash
mkdir -p services/mailserver/terraform/modules/vpc
```

`modules/vpc/main.tf`:
```hcl
resource "aws_vpc" "main" {
  cidr_block           = var.vpc_cidr
  enable_dns_hostnames = true
  enable_dns_support   = true

  tags = merge(var.tags, {
    Name = "${var.environment}-vpc"
  })
}

resource "aws_subnet" "public" {
  count                   = length(var.public_subnet_cidrs)
  vpc_id                  = aws_vpc.main.id
  cidr_block              = var.public_subnet_cidrs[count.index]
  availability_zone       = var.availability_zones[count.index]
  map_public_ip_on_launch = true

  tags = merge(var.tags, {
    Name = "${var.environment}-public-subnet-${count.index + 1}"
  })
}

resource "aws_internet_gateway" "main" {
  vpc_id = aws_vpc.main.id

  tags = merge(var.tags, {
    Name = "${var.environment}-igw"
  })
}

resource "aws_route_table" "public" {
  vpc_id = aws_vpc.main.id

  route {
    cidr_block = "0.0.0.0/0"
    gateway_id = aws_internet_gateway.main.id
  }

  tags = merge(var.tags, {
    Name = "${var.environment}-public-rt"
  })
}

resource "aws_route_table_association" "public" {
  count          = length(aws_subnet.public)
  subnet_id      = aws_subnet.public[count.index].id
  route_table_id = aws_route_table.public.id
}
```

`modules/vpc/variables.tf`:
```hcl
variable "environment" {
  description = "Environment name (production, staging, dev)"
  type        = string
}

variable "vpc_cidr" {
  description = "VPC CIDR block"
  type        = string
  default     = "10.0.0.0/16"
}

variable "public_subnet_cidrs" {
  description = "List of public subnet CIDR blocks"
  type        = list(string)
  default     = ["10.0.1.0/24", "10.0.2.0/24"]
}

variable "availability_zones" {
  description = "List of availability zones"
  type        = list(string)
}

variable "tags" {
  description = "Common tags for all resources"
  type        = map(string)
  default     = {}
}
```

`modules/vpc/outputs.tf`:
```hcl
output "vpc_id" {
  description = "VPC ID"
  value       = aws_vpc.main.id
}

output "public_subnet_ids" {
  description = "List of public subnet IDs"
  value       = aws_subnet.public[*].id
}

output "internet_gateway_id" {
  description = "Internet Gateway ID"
  value       = aws_internet_gateway.main.id
}
```

#### 2-2. Security Groupsモジュール作成

（同様の手順でmodules/security_groups/を作成）

#### 2-3. EC2モジュール作成

（同様の手順でmodules/ec2/を作成）

### Phase 3: ルートモジュール統合（30分）

`main.tf`:
```hcl
terraform {
  required_version = ">= 1.0"

  required_providers {
    aws = {
      source  = "hashicorp/aws"
      version = "~> 5.0"
    }
  }
}

provider "aws" {
  region  = var.aws_region
  profile = var.aws_profile
}

locals {
  common_tags = {
    Project     = "Mailserver"
    Environment = var.environment
    ManagedBy   = "Terraform"
  }
}

module "vpc" {
  source = "./modules/vpc"

  environment         = var.environment
  vpc_cidr            = var.vpc_cidr
  public_subnet_cidrs = var.public_subnet_cidrs
  availability_zones  = var.availability_zones
  tags                = local.common_tags
}

module "security_groups" {
  source = "./modules/security_groups"

  environment = var.environment
  vpc_id      = module.vpc.vpc_id
  tags        = local.common_tags
}

module "ec2" {
  source = "./modules/ec2"

  environment       = var.environment
  instance_type     = var.instance_type
  ami_id            = var.ami_id
  subnet_id         = module.vpc.public_subnet_ids[0]
  security_group_id = module.security_groups.mailserver_sg_id
  tags              = local.common_tags

  depends_on = [module.vpc, module.security_groups]
}
```

---

## ✅ 検証手順

### 1. Terraform検証

```bash
cd /opt/onprem-infra-system/project-root-infra/services/mailserver/terraform

# フォーマット確認
terraform fmt -recursive

# 構文チェック
terraform validate

# Plan実行（差分確認）
terraform plan

# 差分が出ないことを確認
# Expected: "No changes. Your infrastructure matches the configuration."
```

### 2. 差分が出た場合

```bash
# リソース移動（例：VPCリソース）
terraform state mv aws_vpc.mailserver_vpc module.vpc.aws_vpc.main

# 全リソースを適切なモジュールに移動
```

### 3. Apply実行

```bash
# 差分がないことを再確認後
terraform apply
```

---

## 📊 期待される効果

### メリット

| 項目 | Before | After | 改善 |
|------|--------|-------|------|
| **ファイル行数** | 400+ 行 | 各ファイル50-100行 | ✅ 可読性向上 |
| **再利用性** | コピペ必要 | モジュールimport | ✅ DRY原則 |
| **テスト** | 困難 | モジュール単位で可能 | ✅ 品質向上 |
| **保守性** | 変更影響範囲不明確 | モジュール単位で明確 | ✅ 保守性向上 |

### デメリット

| 項目 | 内容 | 対策 |
|------|------|------|
| **初期学習コスト** | モジュール構造理解が必要 | README.md作成 |
| **ファイル数増加** | ディレクトリが複雑化 | 適切な命名・構造化 |

---

## 🚨 注意事項

### 1. State管理

- **CRITICAL**: Terraform state の破壊に注意
- **推奨**: Stateファイルバックアップ取得
  ```bash
  cp terraform.tfstate terraform.tfstate.backup-$(date +%Y%m%d-%H%M%S)
  ```

### 2. 本番環境への影響

- **ゼロダウンタイム**: Plan で `No changes` を確認してから apply
- **リソース再作成回避**: `terraform state mv` で既存リソースを移動

### 3. Rollback計画

- State backup から復元可能
- Git で main.tf の旧バージョンに戻す

---

## 📅 実装スケジュール

| Phase | タスク | 所要時間 | 担当 | ステータス |
|-------|--------|---------|------|----------|
| 1 | モジュール設計・分析 | 30分 | - | 📋 計画中 |
| 2 | VPCモジュール実装 | 20分 | - | 📋 計画中 |
| 3 | SGモジュール実装 | 20分 | - | 📋 計画中 |
| 4 | EC2モジュール実装 | 20分 | - | 📋 計画中 |
| 5 | ルートモジュール統合 | 30分 | - | 📋 計画中 |
| 6 | 検証・テスト | 30分 | - | 📋 計画中 |

**合計所要時間**: 約2時間

---

## 🔗 参考資料

- [Terraform Module Documentation](https://developer.hashicorp.com/terraform/language/modules)
- [Terraform Best Practices](https://www.terraform-best-practices.com/)
- [AWS Provider Documentation](https://registry.terraform.io/providers/hashicorp/aws/latest/docs)
- 現在のS3 Backup実装: `services/mailserver/terraform/s3-backup/`

---

**Last Updated**: 2025-11-11
**Author**: Claude
**Status**: 📋 Planning - Ready for Implementation
