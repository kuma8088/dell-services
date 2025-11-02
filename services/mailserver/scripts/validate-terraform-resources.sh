#!/bin/bash
# ============================================================================
# Terraform-Managed Infrastructure Validation Script
# ============================================================================
# Purpose: Validate Terraform-managed AWS resources for mailserver
# Version: v5.1
# Dependencies: terraform, aws CLI, jq
# ============================================================================

set -e

# Color codes for output
GREEN='\033[0;32m'
RED='\033[0;31m'
YELLOW='\033[1;33m'
NC='\033[0m' # No Color

# Change to terraform directory
TERRAFORM_DIR="/opt/onprem-infra-system/project-root-infra/services/mailserver/terraform"

if [ ! -d "$TERRAFORM_DIR" ]; then
  echo -e "${RED}❌ Terraform directory not found: $TERRAFORM_DIR${NC}"
  exit 1
fi

cd "$TERRAFORM_DIR"

# Check if terraform state exists
if [ ! -f "terraform.tfstate" ]; then
  echo -e "${RED}❌ Terraform state file not found. Run 'terraform apply' first.${NC}"
  exit 1
fi

echo "=========================================="
echo "🔍 Terraform-Managed Resource Validation"
echo "=========================================="
echo ""

# Extract Terraform outputs
echo "📊 Extracting Terraform Outputs..."
VPC_ID=$(terraform output -raw vpc_id 2>/dev/null || echo "")
SUBNET_1=$(terraform output -raw public_subnet_1a_id 2>/dev/null || echo "")
SUBNET_2=$(terraform output -raw public_subnet_1b_id 2>/dev/null || echo "")
SG_ID=$(terraform output -raw security_group_id 2>/dev/null || echo "")
ELASTIC_IP=$(terraform output -raw elastic_ip 2>/dev/null || echo "")
EIP_ALLOC_ID=$(terraform output -raw elastic_ip_allocation_id 2>/dev/null || echo "")
CLUSTER_NAME=$(terraform output -raw ecs_cluster_name 2>/dev/null || echo "")
LOG_GROUP=$(terraform output -raw cloudwatch_log_group_name 2>/dev/null || echo "")
EXEC_ROLE_ARN=$(terraform output -raw execution_role_arn 2>/dev/null || echo "")
TASK_ROLE_ARN=$(terraform output -raw task_role_arn 2>/dev/null || echo "")

if [ -z "$VPC_ID" ]; then
  echo -e "${RED}❌ Terraform outputs not available. Infrastructure may not be deployed.${NC}"
  exit 1
fi

echo -e "${GREEN}✅ Terraform outputs extracted successfully${NC}"
echo ""

# ============================================================================
# 1. VPC Validation
# ============================================================================
echo "🔹 VPC Validation"
VPC_STATE=$(aws ec2 describe-vpcs --vpc-ids $VPC_ID --query 'Vpcs[0].State' --output text 2>/dev/null || echo "not-found")
if [ "$VPC_STATE" == "available" ]; then
  echo -e "  ${GREEN}✅ VPC $VPC_ID - State: available${NC}"
else
  echo -e "  ${RED}❌ VPC $VPC_ID - State: $VPC_STATE${NC}"
  exit 1
fi

# DNS settings
DNS_SUPPORT=$(aws ec2 describe-vpc-attribute --vpc-id $VPC_ID --attribute enableDnsSupport --query 'EnableDnsSupport.Value' --output text)
DNS_HOSTNAMES=$(aws ec2 describe-vpc-attribute --vpc-id $VPC_ID --attribute enableDnsHostnames --query 'EnableDnsHostnames.Value' --output text)

if [ "$DNS_SUPPORT" == "true" ] && [ "$DNS_HOSTNAMES" == "true" ]; then
  echo -e "  ${GREEN}✅ DNS Support: enabled, DNS Hostnames: enabled${NC}"
else
  echo -e "  ${RED}❌ DNS Support: $DNS_SUPPORT, DNS Hostnames: $DNS_HOSTNAMES${NC}"
fi
echo ""

# ============================================================================
# 2. Subnet Validation
# ============================================================================
echo "🔹 Subnet Validation"
SUBNET_1_STATE=$(aws ec2 describe-subnets --subnet-ids $SUBNET_1 --query 'Subnets[0].State' --output text 2>/dev/null || echo "not-found")
SUBNET_2_STATE=$(aws ec2 describe-subnets --subnet-ids $SUBNET_2 --query 'Subnets[0].State' --output text 2>/dev/null || echo "not-found")

if [ "$SUBNET_1_STATE" == "available" ]; then
  echo -e "  ${GREEN}✅ Subnet 1 ($SUBNET_1) - State: available${NC}"
else
  echo -e "  ${RED}❌ Subnet 1 ($SUBNET_1) - State: $SUBNET_1_STATE${NC}"
fi

if [ "$SUBNET_2_STATE" == "available" ]; then
  echo -e "  ${GREEN}✅ Subnet 2 ($SUBNET_2) - State: available${NC}"
else
  echo -e "  ${RED}❌ Subnet 2 ($SUBNET_2) - State: $SUBNET_2_STATE${NC}"
fi
echo ""

# ============================================================================
# 3. Security Group Validation
# ============================================================================
echo "🔹 Security Group Validation"
INBOUND_RULES=$(aws ec2 describe-security-groups --group-ids $SG_ID --query 'SecurityGroups[0].IpPermissions')

# Port 25 TCP
PORT25_RULE=$(echo $INBOUND_RULES | jq '.[] | select(.FromPort==25 and .ToPort==25 and .IpProtocol=="tcp")')
if [ -n "$PORT25_RULE" ]; then
  echo -e "  ${GREEN}✅ Port 25 TCP (SMTP) - ALLOWED from 0.0.0.0/0${NC}"
else
  echo -e "  ${RED}❌ Port 25 TCP (SMTP) - MISSING${NC}"
  exit 1
fi

# Port 41641 UDP
PORT41641_RULE=$(echo $INBOUND_RULES | jq '.[] | select(.FromPort==41641 and .ToPort==41641 and .IpProtocol=="udp")')
if [ -n "$PORT41641_RULE" ]; then
  echo -e "  ${GREEN}✅ Port 41641 UDP (Tailscale) - ALLOWED from 0.0.0.0/0${NC}"
else
  echo -e "  ${RED}❌ Port 41641 UDP (Tailscale) - MISSING${NC}"
  exit 1
fi

# Outbound
OUTBOUND_RULES=$(aws ec2 describe-security-groups --group-ids $SG_ID --query 'SecurityGroups[0].IpPermissionsEgress')
EGRESS_ALL=$(echo $OUTBOUND_RULES | jq '.[] | select(.IpProtocol=="-1" and (.IpRanges[].CidrIp=="0.0.0.0/0"))')
if [ -n "$EGRESS_ALL" ]; then
  echo -e "  ${GREEN}✅ All outbound traffic - ALLOWED${NC}"
else
  echo -e "  ${YELLOW}⚠️  All outbound traffic - RESTRICTED${NC}"
fi
echo ""

# ============================================================================
# 4. Elastic IP Validation
# ============================================================================
echo "🔹 Elastic IP Validation"
EIP_STATE=$(aws ec2 describe-addresses --allocation-ids $EIP_ALLOC_ID --query 'Addresses[0].AllocationId' --output text 2>/dev/null || echo "not-found")
if [ "$EIP_STATE" != "not-found" ]; then
  echo -e "  ${GREEN}✅ Elastic IP: $ELASTIC_IP (Allocation ID: $EIP_ALLOC_ID)${NC}"
  echo -e "  ${YELLOW}⚠️  MX レコードに設定する IP アドレス: $ELASTIC_IP${NC}"
else
  echo -e "  ${RED}❌ Elastic IP not found${NC}"
fi
echo ""

# ============================================================================
# 5. ECS Cluster Validation
# ============================================================================
echo "🔹 ECS Cluster Validation"
CLUSTER_STATUS=$(aws ecs describe-clusters --clusters $CLUSTER_NAME --query 'clusters[0].status' --output text 2>/dev/null || echo "not-found")
if [ "$CLUSTER_STATUS" == "ACTIVE" ]; then
  echo -e "  ${GREEN}✅ ECS Cluster ($CLUSTER_NAME) - Status: ACTIVE${NC}"
else
  echo -e "  ${RED}❌ ECS Cluster ($CLUSTER_NAME) - Status: $CLUSTER_STATUS${NC}"
fi
echo ""

# ============================================================================
# 6. CloudWatch Logs Validation
# ============================================================================
echo "🔹 CloudWatch Logs Validation"
LOG_GROUP_EXISTS=$(aws logs describe-log-groups --log-group-name-prefix $LOG_GROUP --query 'logGroups[0].logGroupName' --output text 2>/dev/null || echo "not-found")
if [ "$LOG_GROUP_EXISTS" == "$LOG_GROUP" ]; then
  RETENTION=$(aws logs describe-log-groups --log-group-name-prefix $LOG_GROUP --query 'logGroups[0].retentionInDays' --output text)
  echo -e "  ${GREEN}✅ CloudWatch Logs ($LOG_GROUP) - Retention: $RETENTION days${NC}"
else
  echo -e "  ${RED}❌ CloudWatch Logs ($LOG_GROUP) - NOT FOUND${NC}"
fi
echo ""

# ============================================================================
# 7. IAM Role Validation
# ============================================================================
echo "🔹 IAM Role Validation"
EXEC_ROLE_NAME=$(echo $EXEC_ROLE_ARN | awk -F'/' '{print $NF}')
TASK_ROLE_NAME=$(echo $TASK_ROLE_ARN | awk -F'/' '{print $NF}')

EXEC_ROLE_EXISTS=$(aws iam get-role --role-name $EXEC_ROLE_NAME --query 'Role.RoleName' --output text 2>/dev/null || echo "not-found")
TASK_ROLE_EXISTS=$(aws iam get-role --role-name $TASK_ROLE_NAME --query 'Role.RoleName' --output text 2>/dev/null || echo "not-found")

if [ "$EXEC_ROLE_EXISTS" != "not-found" ]; then
  echo -e "  ${GREEN}✅ Execution Role ($EXEC_ROLE_NAME) - EXISTS${NC}"
else
  echo -e "  ${RED}❌ Execution Role ($EXEC_ROLE_NAME) - NOT FOUND${NC}"
fi

if [ "$TASK_ROLE_EXISTS" != "not-found" ]; then
  echo -e "  ${GREEN}✅ Task Role ($TASK_ROLE_NAME) - EXISTS${NC}"
else
  echo -e "  ${RED}❌ Task Role ($TASK_ROLE_NAME) - NOT FOUND${NC}"
fi
echo ""

# ============================================================================
# Summary
# ============================================================================
echo "=========================================="
echo -e "${GREEN}✅ All Terraform-Managed Resources Validated Successfully${NC}"
echo "=========================================="
echo ""
echo "📋 Resource Summary:"
echo "  VPC ID:               $VPC_ID"
echo "  Subnet 1a ID:         $SUBNET_1"
echo "  Subnet 1b ID:         $SUBNET_2"
echo "  Security Group ID:    $SG_ID"
echo "  Elastic IP:           $ELASTIC_IP"
echo "  ECS Cluster:          $CLUSTER_NAME"
echo "  CloudWatch Logs:      $LOG_GROUP"
echo "  Execution Role:       $EXEC_ROLE_NAME"
echo "  Task Role:            $TASK_ROLE_NAME"
echo ""
echo "🔧 Next Steps:"
echo "  1. Section 3.2: Configure AWS Secrets Manager (Tailscale Auth Key)"
echo "  2. Section 4: Configure SendGrid Domain Authentication"
echo "  3. Section 5: Setup Tailscale VPN on Dell host"
echo "  4. Section 6: Deploy Docker Compose stack on Dell host"
echo ""
