#!/bin/bash
# Fargate タスク再起動時に Public IP を取得して DNS A レコードを更新

CLUSTER_NAME="mailserver-cluster"
SERVICE_NAME="mailserver-mx-service"
HOSTED_ZONE_ID="YOUR_ROUTE53_ZONE_ID"  # Route53 利用時
DOMAIN_NAME="mx.kuma8088.com"

# Fargate タスクの Public IP 取得
TASK_ARN=$(aws ecs list-tasks --cluster $CLUSTER_NAME --service-name $SERVICE_NAME --query 'taskArns[0]' --output text)
ENI_ID=$(aws ecs describe-tasks --cluster $CLUSTER_NAME --tasks $TASK_ARN --query 'tasks[0].attachments[0].details[?name==`networkInterfaceId`].value' --output text)
FARGATE_PUBLIC_IP=$(aws ec2 describe-network-interfaces --network-interface-ids $ENI_ID --query 'NetworkInterfaces[0].Association.PublicIp' --output text)

echo "Current Fargate Public IP: $FARGATE_PUBLIC_IP"

# Route53 A レコード更新
aws route53 change-resource-record-sets \
  --hosted-zone-id $HOSTED_ZONE_ID \
  --change-batch "{
    \"Changes\": [{
      \"Action\": \"UPSERT\",
      \"ResourceRecordSet\": {
        \"Name\": \"$DOMAIN_NAME\",
        \"Type\": \"A\",
        \"TTL\": 300,
        \"ResourceRecords\": [{\"Value\": \"$FARGATE_PUBLIC_IP\"}]
      }
    }]
  }"

echo "DNS A record updated: $DOMAIN_NAME -> $FARGATE_PUBLIC_IP"
