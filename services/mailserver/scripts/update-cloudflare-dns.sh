#!/bin/bash
CLOUDFLARE_API_TOKEN="YOUR_CLOUDFLARE_API_TOKEN"
ZONE_ID="YOUR_CLOUDFLARE_ZONE_ID"
DNS_RECORD_ID="YOUR_DNS_RECORD_ID"
DOMAIN_NAME="mx.kuma8088.com"

# Fargate Public IP 取得（上記と同じ）
TASK_ARN=$(aws ecs list-tasks --cluster mailserver-cluster --service-name mailserver-mx-service --query 'taskArns[0]' --output text)
ENI_ID=$(aws ecs describe-tasks --cluster mailserver-cluster --tasks $TASK_ARN --query 'tasks[0].attachments[0].details[?name==`networkInterfaceId`].value' --output text)
FARGATE_PUBLIC_IP=$(aws ec2 describe-network-interfaces --network-interface-ids $ENI_ID --query 'NetworkInterfaces[0].Association.PublicIp' --output text)

# Cloudflare API で A レコード更新
curl -X PUT "https://api.cloudflare.com/client/v4/zones/$ZONE_ID/dns_records/$DNS_RECORD_ID" \
  -H "Authorization: Bearer $CLOUDFLARE_API_TOKEN" \
  -H "Content-Type: application/json" \
  --data "{\"type\":\"A\",\"name\":\"$DOMAIN_NAME\",\"content\":\"$FARGATE_PUBLIC_IP\",\"ttl\":300,\"proxied\":false}"

echo "Cloudflare DNS updated: $DOMAIN_NAME -> $FARGATE_PUBLIC_IP"
