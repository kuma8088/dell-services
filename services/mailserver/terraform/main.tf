# ============================================================================
# Mailserver Infrastructure - Terraform Configuration
# ============================================================================
# Purpose: AWS infrastructure for hybrid mail server (Fargate MX + Dell)
# Version: v5.2
# Sections: 3.1-3.5 from 04_installation.md
# ============================================================================

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
  region = var.aws_region

  default_tags {
    tags = {
      Project     = "mailserver"
      Environment = var.environment
      ManagedBy   = "terraform"
      Version     = "v5.2"
    }
  }
}

# ============================================================================
# Variables
# ============================================================================

variable "aws_region" {
  description = "AWS region for mail server infrastructure"
  type        = string
  default     = "ap-northeast-1"
}

variable "environment" {
  description = "Environment name (dev, staging, production)"
  type        = string
  default     = "production"
}

variable "vpc_cidr" {
  description = "CIDR block for VPC"
  type        = string
  default     = "10.0.0.0/16"
}

variable "public_subnet_1a_cidr" {
  description = "CIDR block for public subnet in ap-northeast-1a"
  type        = string
  default     = "10.0.1.0/24"
}

variable "public_subnet_1c_cidr" {
  description = "CIDR block for public subnet in ap-northeast-1c"
  type        = string
  default     = "10.0.2.0/24"
}

variable "cluster_name" {
  description = "ECS cluster name"
  type        = string
  default     = "mailserver-cluster"
}

variable "log_retention_days" {
  description = "CloudWatch Logs retention period in days"
  type        = number
  default     = 30
}

# ============================================================================
# Section 3.1: VPC Configuration
# ============================================================================

resource "aws_vpc" "mailserver_vpc" {
  cidr_block           = var.vpc_cidr
  enable_dns_support   = true
  enable_dns_hostnames = true

  tags = {
    Name = "mailserver-vpc"
  }
}

resource "aws_internet_gateway" "mailserver_igw" {
  vpc_id = aws_vpc.mailserver_vpc.id

  tags = {
    Name = "mailserver-igw"
  }
}

# ============================================================================
# Section 3.2: Public Subnet Configuration
# ============================================================================

resource "aws_subnet" "public_subnet_1a" {
  vpc_id                  = aws_vpc.mailserver_vpc.id
  cidr_block              = var.public_subnet_1a_cidr
  availability_zone       = "${var.aws_region}a"
  map_public_ip_on_launch = true

  tags = {
    Name = "mailserver-public-subnet-1a"
  }
}

resource "aws_subnet" "public_subnet_1c" {
  vpc_id                  = aws_vpc.mailserver_vpc.id
  cidr_block              = var.public_subnet_1c_cidr
  availability_zone       = "${var.aws_region}c"
  map_public_ip_on_launch = true

  tags = {
    Name = "mailserver-public-subnet-1c"
  }
}

# ============================================================================
# Section 3.3: Route Table Configuration
# ============================================================================

resource "aws_route_table" "mailserver_public_rt" {
  vpc_id = aws_vpc.mailserver_vpc.id

  route {
    cidr_block = "0.0.0.0/0"
    gateway_id = aws_internet_gateway.mailserver_igw.id
  }

  tags = {
    Name = "mailserver-public-rt"
  }
}

resource "aws_route_table_association" "public_subnet_1a_association" {
  subnet_id      = aws_subnet.public_subnet_1a.id
  route_table_id = aws_route_table.mailserver_public_rt.id
}

resource "aws_route_table_association" "public_subnet_1c_association" {
  subnet_id      = aws_subnet.public_subnet_1c.id
  route_table_id = aws_route_table.mailserver_public_rt.id
}

# ============================================================================
# Section 3.4: Security Group Configuration
# ============================================================================

resource "aws_security_group" "fargate_sg" {
  name        = "mailserver-fargate-sg"
  description = "Security group for Fargate MX gateway"
  vpc_id      = aws_vpc.mailserver_vpc.id

  ingress {
    description = "Allow SMTP inbound traffic from internet"
    from_port   = 25
    to_port     = 25
    protocol    = "tcp"
    cidr_blocks = ["0.0.0.0/0"]
  }

  ingress {
    description = "Allow Tailscale VPN inbound traffic"
    from_port   = 41641
    to_port     = 41641
    protocol    = "udp"
    cidr_blocks = ["0.0.0.0/0"]
  }

  egress {
    description = "Allow all outbound traffic"
    from_port   = 0
    to_port     = 0
    protocol    = "-1"
    cidr_blocks = ["0.0.0.0/0"]
  }

  tags = {
    Name = "mailserver-fargate-sg"
  }
}

# ============================================================================
# Section 3.5: Elastic IP Configuration
# ============================================================================

resource "aws_eip" "mailserver_eip" {
  domain = "vpc"

  tags = {
    Name = "mailserver-eip"
  }
}

# ============================================================================
# ECS Cluster Configuration
# ============================================================================

resource "aws_ecs_cluster" "mailserver_cluster" {
  name = var.cluster_name

  setting {
    name  = "containerInsights"
    value = "enabled"
  }

  tags = {
    Name = var.cluster_name
  }
}

# ============================================================================
# CloudWatch Logs Configuration
# ============================================================================

resource "aws_cloudwatch_log_group" "ecs_mailserver_mx" {
  name              = "/ecs/mailserver-mx"
  retention_in_days = var.log_retention_days

  tags = {
    Name = "mailserver-mx-logs"
  }
}

# ============================================================================
# IAM Role: ECS Task Execution Role
# ============================================================================

resource "aws_iam_role" "execution_role" {
  name = "mailserver-execution-role"

  assume_role_policy = jsonencode({
    Version = "2012-10-17"
    Statement = [
      {
        Effect = "Allow"
        Principal = {
          Service = "ecs-tasks.amazonaws.com"
        }
        Action = "sts:AssumeRole"
      }
    ]
  })

  tags = {
    Name = "mailserver-execution-role"
  }
}

# Attach AWS managed policy for ECS task execution
resource "aws_iam_role_policy_attachment" "execution_role_policy" {
  role       = aws_iam_role.execution_role.name
  policy_arn = "arn:aws:iam::aws:policy/service-role/AmazonECSTaskExecutionRolePolicy"
}

# ============================================================================
# IAM Role: ECS Task Role (for application runtime)
# ============================================================================

resource "aws_iam_role" "task_role" {
  name = "mailserver-task-role"

  assume_role_policy = jsonencode({
    Version = "2012-10-17"
    Statement = [
      {
        Effect = "Allow"
        Principal = {
          Service = "ecs-tasks.amazonaws.com"
        }
        Action = "sts:AssumeRole"
      }
    ]
  })

  tags = {
    Name = "mailserver-task-role"
  }
}

# Inline policy granting Secrets Manager access
resource "aws_iam_role_policy" "task_role_secrets_access" {
  name = "mailserver-secrets-access"
  role = aws_iam_role.task_role.id

  policy = jsonencode({
    Version = "2012-10-17"
    Statement = [
      {
        Effect = "Allow"
        Action = [
          "secretsmanager:GetSecretValue",
          "secretsmanager:DescribeSecret"
        ]
        Resource = [
          "arn:aws:secretsmanager:${var.aws_region}:*:secret:mailserver/tailscale/fargate-auth-key-*",
          "arn:aws:secretsmanager:${var.aws_region}:*:secret:mailserver/sendgrid/api-key-*"
        ]
      }
    ]
  })
}

# ============================================================================
# Outputs
# ============================================================================

output "vpc_id" {
  description = "VPC ID for mail server infrastructure"
  value       = aws_vpc.mailserver_vpc.id
}

output "vpc_cidr" {
  description = "VPC CIDR block"
  value       = aws_vpc.mailserver_vpc.cidr_block
}

output "internet_gateway_id" {
  description = "Internet Gateway ID"
  value       = aws_internet_gateway.mailserver_igw.id
}

output "public_subnet_1a_id" {
  description = "Public subnet ID in ap-northeast-1a"
  value       = aws_subnet.public_subnet_1a.id
}

output "public_subnet_1c_id" {
  description = "Public subnet ID in ap-northeast-1c"
  value       = aws_subnet.public_subnet_1c.id
}

output "route_table_id" {
  description = "Public route table ID"
  value       = aws_route_table.mailserver_public_rt.id
}

output "security_group_id" {
  description = "Fargate security group ID"
  value       = aws_security_group.fargate_sg.id
}

output "elastic_ip" {
  description = "Elastic IP address for mail server"
  value       = aws_eip.mailserver_eip.public_ip
}

output "elastic_ip_allocation_id" {
  description = "Elastic IP allocation ID"
  value       = aws_eip.mailserver_eip.id
}

output "ecs_cluster_name" {
  description = "ECS cluster name"
  value       = aws_ecs_cluster.mailserver_cluster.name
}

output "ecs_cluster_arn" {
  description = "ECS cluster ARN"
  value       = aws_ecs_cluster.mailserver_cluster.arn
}

output "cloudwatch_log_group_name" {
  description = "CloudWatch Logs group name"
  value       = aws_cloudwatch_log_group.ecs_mailserver_mx.name
}

output "execution_role_arn" {
  description = "ECS task execution role ARN"
  value       = aws_iam_role.execution_role.arn
}

output "task_role_arn" {
  description = "ECS task role ARN"
  value       = aws_iam_role.task_role.arn
}

# ============================================================================
# Usage Instructions
# ============================================================================

# Initialize Terraform:
#   terraform init
#
# Plan infrastructure changes:
#   terraform plan
#
# Apply infrastructure:
#   terraform apply
#
# Destroy infrastructure (CAUTION):
#   terraform destroy
#
# Format code:
#   terraform fmt
#
# Validate configuration:
#   terraform validate
#
# Show current state:
#   terraform show
#
# Generate dependency graph:
#   terraform graph | dot -Tpng > graph.png
