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
    description = "Allow SMTP Submission inbound traffic"
    from_port   = 587
    to_port     = 587
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
  name              = local.ecs_log_group_name
  retention_in_days = var.log_retention_days

  tags = {
    Name = local.ecs_log_group_tag_name
  }
}

# ============================================================================
# IAM Role: ECS Task Execution Role
# ============================================================================

resource "aws_iam_role" "execution_role" {
  name = local.ecs_execution_role_name

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
    Name = local.ecs_execution_role_name
  }
}

# Attach AWS managed policy for ECS task execution
resource "aws_iam_role_policy_attachment" "execution_role_policy" {
  role       = aws_iam_role.execution_role.name
  policy_arn = "arn:aws:iam::aws:policy/service-role/AmazonECSTaskExecutionRolePolicy"
}

# Inline policy granting Secrets Manager access to execution role
resource "aws_iam_role_policy" "execution_role_secrets_access" {
  name = local.ecs_execution_policy_name
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
  name = local.ecs_task_role_name

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
    Name = local.ecs_task_role_name
  }
}

# Inline policy granting Secrets Manager access
resource "aws_iam_role_policy" "task_role_secrets_access" {
  name = local.ecs_task_policy_name
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
  name              = local.ec2_log_group_name
  retention_in_days = var.log_retention_days

  tags = {
    Name        = local.ec2_log_group_tag_name
    Environment = var.environment
  }
}

# IAM Role for EC2 Instance
resource "aws_iam_role" "ec2_mx_role" {
  name = local.ec2_role_name

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
    Name        = local.ec2_role_name
    Environment = var.environment
  }
}

# IAM Policy for Secrets Manager Access (Tailscale Auth Key)
resource "aws_iam_role_policy" "ec2_secrets_policy" {
  name = local.ec2_secrets_policy_name
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
  name = local.ec2_cloudwatch_policy_name
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
  name = local.ec2_profile_name
  role = aws_iam_role.ec2_mx_role.name

  tags = {
    Name        = local.ec2_profile_name
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
  user_data = file("${path.module}/${local.user_data_filename}")

  root_block_device {
    volume_type = "gp3"
    volume_size = 8
    encrypted   = true
  }

  tags = {
    Name        = local.ec2_instance_name
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
