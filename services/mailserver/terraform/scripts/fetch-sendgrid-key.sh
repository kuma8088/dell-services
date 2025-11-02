#!/bin/bash
# Secrets Manager から SendGrid API Key を取得
aws secretsmanager get-secret-value \
  --secret-id mailserver/sendgrid/api-key \
  --query 'SecretString' \
  --output text
