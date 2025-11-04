#!/bin/bash
# Tailscale Auth Key 作成とSecrets Manager登録スクリプト
# 参照: Docs/application/mailserver/04_EC2Server.md Section 4.2

set -e

AWS_REGION="ap-northeast-1"
SECRET_NAME="mailserver/tailscale/ec2-auth-key"

echo "=================================================="
echo "Tailscale Auth Key 作成手順"
echo "=================================================="
echo ""
echo "このスクリプトは Tailscale Auth Key を AWS Secrets Manager に登録します。"
echo ""
echo "【事前準備】"
echo "1. Tailscale Admin Console にログイン"
echo "   URL: https://login.tailscale.com/admin/settings/keys"
echo ""
echo "2. 「Generate auth key」をクリック"
echo ""
echo "3. 以下の設定で Auth Key を作成:"
echo "   - Description: EC2 MX Gateway"
echo "   - Reusable: No (一度のみ使用)"
echo "   - Expiration: 90 days"
echo "   - Pre-approved: Yes (事前承認)"
echo "   - Tags: tag:ec2-mx"
echo ""
echo "4. 生成された Auth Key をコピー"
echo ""
echo "=================================================="
echo ""

# Auth Key の入力を促す
read -sp "Tailscale Auth Key を入力してください: " TAILSCALE_AUTH_KEY
echo ""

if [ -z "$TAILSCALE_AUTH_KEY" ]; then
    echo "❌ エラー: Auth Key が入力されていません"
    exit 1
fi

# Auth Key の形式チェック (tskey- で始まる)
if [[ ! "$TAILSCALE_AUTH_KEY" =~ ^tskey- ]]; then
    echo "⚠️  警告: Auth Key が 'tskey-' で始まっていません"
    read -p "続行しますか? (y/N): " CONFIRM
    if [[ ! "$CONFIRM" =~ ^[Yy]$ ]]; then
        echo "処理を中止しました"
        exit 1
    fi
fi

echo ""
echo "=================================================="
echo "AWS Secrets Manager に登録します..."
echo "=================================================="

# Secrets Manager に Auth Key を登録
aws secretsmanager create-secret \
    --name "$SECRET_NAME" \
    --description "Tailscale auth key for EC2 MX Gateway" \
    --secret-string "$TAILSCALE_AUTH_KEY" \
    --region "$AWS_REGION" \
    --tags Key=Environment,Value=production Key=Service,Value=mailserver Key=Purpose,Value=tailscale-ec2-auth

if [ $? -eq 0 ]; then
    echo ""
    echo "✅ 成功: Tailscale Auth Key を Secrets Manager に登録しました"
    echo ""
    echo "Secret Name: $SECRET_NAME"
    echo "Region: $AWS_REGION"
    echo ""
    echo "次のステップ:"
    echo "1. terraform plan を実行して変更内容を確認"
    echo "2. terraform apply を実行してEC2インスタンスをデプロイ"
else
    echo ""
    echo "❌ エラー: Secrets Manager への登録に失敗しました"
    echo ""
    echo "トラブルシューティング:"
    echo "- AWS認証情報が正しく設定されているか確認"
    echo "- Secrets Manager へのアクセス権限があるか確認"
    echo "- 同名のシークレットが既に存在しないか確認"
    exit 1
fi

echo ""
echo "=================================================="
echo "登録完了"
echo "=================================================="
