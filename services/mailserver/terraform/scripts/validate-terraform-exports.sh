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