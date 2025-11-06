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

# Get current AWS account ID
data "aws_caller_identity" "current" {}

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
    description = "Allow SSH inbound traffic from internet"
    from_port   = 22
    to_port     = 22
    protocol    = "tcp"
    cidr_blocks = ["0.0.0.0/0"]
  }

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

# Inline policy granting Secrets Manager access to execution role
resource "aws_iam_role_policy" "execution_role_secrets_access" {
  name = "mailserver-execution-secrets-access"
  role = aws_iam_role.execution_role.id

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
          "arn:aws:secretsmanager:${var.aws_region}:${data.aws_caller_identity.current.account_id}:secret:mailserver/tailscale/fargate-auth-key-*",
          "arn:aws:secretsmanager:${var.aws_region}:${data.aws_caller_identity.current.account_id}:secret:mailserver/sendgrid/api-key-*"
        ]
      }
    ]
  })
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
# EC2 MX Gateway Resources (v6.0 Architecture)
# ============================================================================
# Purpose: EC2-based MX gateway replacing Fargate
# Implements lessons learned from Fargate troubleshooting
# Reference: Docs/application/mailserver/04_EC2Server.md
# ============================================================================

# CloudWatch Log Group for EC2
resource "aws_cloudwatch_log_group" "ec2_mx_logs" {
  name              = terraform.workspace == "staging" ? "/ec2/mailserver-mx-staging" : "/ec2/mailserver-mx"
  retention_in_days = var.log_retention_days

  tags = {
    Name        = terraform.workspace == "staging" ? "mailserver-mx-ec2-logs-staging" : "mailserver-mx-ec2-logs"
    Environment = var.environment
  }
}

# IAM Role for EC2 Instance
resource "aws_iam_role" "ec2_mx_role" {
  name = terraform.workspace == "staging" ? "mailserver-ec2-mx-role-staging" : "mailserver-ec2-mx-role"

  assume_role_policy = jsonencode({
    Version = "2012-10-17"
    Statement = [
      {
        Action = "sts:AssumeRole"
        Effect = "Allow"
        Principal = {
          Service = "ec2.amazonaws.com"
        }
      }
    ]
  })

  tags = {
    Name        = terraform.workspace == "staging" ? "mailserver-ec2-mx-role-staging" : "mailserver-ec2-mx-role"
    Environment = var.environment
  }
}

# IAM Policy for Secrets Manager Access (Tailscale Auth Key)
resource "aws_iam_role_policy" "ec2_secrets_policy" {
  name = terraform.workspace == "staging" ? "mailserver-ec2-secrets-policy-staging" : "mailserver-ec2-secrets-policy"
  role = aws_iam_role.ec2_mx_role.id

  policy = jsonencode({
    Version = "2012-10-17"
    Statement = [
      {
        Effect = "Allow"
        Action = [
          "secretsmanager:GetSecretValue"
        ]
        Resource = "arn:aws:secretsmanager:${var.aws_region}:${data.aws_caller_identity.current.account_id}:secret:mailserver/tailscale/ec2-auth-key-*"
      }
    ]
  })
}

# IAM Policy for CloudWatch Logs
resource "aws_iam_role_policy" "ec2_cloudwatch_policy" {
  name = terraform.workspace == "staging" ? "mailserver-ec2-cloudwatch-policy-staging" : "mailserver-ec2-cloudwatch-policy"
  role = aws_iam_role.ec2_mx_role.id

  policy = jsonencode({
    Version = "2012-10-17"
    Statement = [
      {
        Effect = "Allow"
        Action = [
          "logs:CreateLogGroup",
          "logs:CreateLogStream",
          "logs:PutLogEvents",
          "logs:DescribeLogStreams"
        ]
        Resource = "${aws_cloudwatch_log_group.ec2_mx_logs.arn}:*"
      }
    ]
  })
}

# IAM Instance Profile
resource "aws_iam_instance_profile" "ec2_mx_profile" {
  name = terraform.workspace == "staging" ? "mailserver-ec2-mx-profile-staging" : "mailserver-ec2-mx-profile"
  role = aws_iam_role.ec2_mx_role.name

  tags = {
    Name        = terraform.workspace == "staging" ? "mailserver-ec2-mx-profile-staging" : "mailserver-ec2-mx-profile"
    Environment = var.environment
  }
}

# EC2 Instance for MX Gateway
resource "aws_instance" "mailserver_mx" {
  ami                         = "ami-0ad4e047a362f26b8" # Amazon Linux 2023 (ARM64) ap-northeast-1
  instance_type               = "t4g.nano"
  subnet_id                   = aws_subnet.public_subnet_1a.id
  vpc_security_group_ids      = [aws_security_group.fargate_sg.id]
  associate_public_ip_address = true
  iam_instance_profile        = aws_iam_instance_profile.ec2_mx_profile.name

  # Conditionally use staging or production user_data based on workspace
  user_data = file("${path.module}/${terraform.workspace == "staging" ? "user_data_staging.sh" : "user_data.sh"}")

  root_block_device {
    volume_type = "gp3"
    volume_size = 8
    encrypted   = true
  }

  tags = {
    Name        = terraform.workspace == "staging" ? "mailserver-mx-ec2-staging" : "mailserver-mx-ec2"
    Environment = var.environment
    Purpose     = "MX Gateway with Tailscale"
  }
}

# Elastic IP Association to EC2
resource "aws_eip_association" "mailserver_eip_ec2" {
  instance_id   = aws_instance.mailserver_mx.id
  allocation_id = aws_eip.mailserver_eip.id
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

output "ec2_instance_id" {
  description = "EC2 MX Gateway instance ID"
  value       = aws_instance.mailserver_mx.id
}

output "ec2_instance_public_ip" {
  description = "EC2 MX Gateway public IP (Elastic IP)"
  value       = aws_eip.mailserver_eip.public_ip
}

output "ec2_instance_private_ip" {
  description = "EC2 MX Gateway private IP"
  value       = aws_instance.mailserver_mx.private_ip
}

output "ec2_cloudwatch_log_group" {
  description = "CloudWatch Logs group for EC2"
  value       = aws_cloudwatch_log_group.ec2_mx_logs.name
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
