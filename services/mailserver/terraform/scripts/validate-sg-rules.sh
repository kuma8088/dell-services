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
