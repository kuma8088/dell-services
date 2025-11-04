# Fargate メールサーバーデプロイメント - 検証レポート

**日付**: 2025-11-03
**ステータス**: ✅ **成功**
**タスク ARN**: `arn:aws:ecs:ap-northeast-1:552927148143:task/mailserver-cluster/f93116aaada746bc83746ec1b73ab460`
**パブリック IP**: `18.177.139.144`

---

## 📋 概要

Fargate メールサーバー MX ゲートウェイは、重要な IAM ポリシー設定問題を解決した後、正常にデプロイされました。システムは現在、Postfix と Tailscale の両方のコンテナが正常な状態で稼働しています。

---

## 🔧 発見され解決された問題

### 問題 #1: IAM ポリシーのアカウント ID ワイルドカード

**問題点**:
- IAM Execution Role ポリシーが Secrets Manager ARN の AWS アカウント ID にワイルドカード (`*`) を使用していた
- ECS タスクがエラーで失敗: `AccessDeniedException: User: arn:aws:sts::552927148143:assumed-role/mailserver-execution-role/... is not authorized to perform: secretsmanager:GetSecretValue`

**根本原因**:
```hcl
# Terraform main.tf (279-280行目) - 修正前
Resource = [
  "arn:aws:secretsmanager:${var.aws_region}:*:secret:mailserver/tailscale/fargate-auth-key-*",
  "arn:aws:secretsmanager:${var.aws_region}:*:secret:mailserver/sendgrid/api-key-*"
]
```

AWS Secrets Manager は IAM ポリシーで明示的なアカウント ID を要求します。ワイルドカードはクロスアカウントアクセス制御では受け入れられません。

**解決策**:
```hcl
# Terraform main.tf (279-283行目) - 修正後
Resource = [
  "arn:aws:secretsmanager:${var.aws_region}:${data.aws_caller_identity.current.account_id}:secret:mailserver/tailscale/fargate-auth-key-*",
  "arn:aws:secretsmanager:${var.aws_region}:${data.aws_caller_identity.current.account_id}:secret:mailserver/sendgrid/api-key-*"
]
```

アカウント ID を動的に取得するため、`data.aws_caller_identity.current` データソースを追加しました。

**変更されたファイル**:
- `/opt/onprem-infra-system/project-root-infra/services/mailserver/terraform/main.tf` (33行目, 282-283行目)

**Terraform 変更適用**:
```bash
terraform apply
# リソース: 0 追加, 1 変更, 0 破棄
```

---

### 問題 #2: Task Definition の変数展開

**問題点**:
- 初期手順では heredoc を適切な変数展開なしで使用していた
- JSON ファイルに `$EXECUTION_ROLE_ARN` のようなリテラル文字列が含まれていた
- 登録が失敗: "invalid Systems Manager parameter name"

**解決策**:
インストールマニュアル (セクション 7.1, 1873-2004行目) には、変数展開用の `envsubst` を使用した正しい手順がすでに含まれています。マニュアル検証により、このアプローチが正しく機能することが確認されました。

**重要な手順** (すでに文書化済み):
1. 実際の ARN 値で環境変数を設定
2. `${VARIABLE}` プレースホルダーでテンプレート JSON を作成
3. `envsubst` を使用して変数を展開 → 最終 JSON
4. 登録前にプレースホルダーが残っていないことを検証

---

## ✅ デプロイメント検証結果

### コンテナステータス
```
┌─────────────────────────────────┐
│       DescribeTasks            │
├─────────┬─────────────┬─────────┤
│ Health  │    Name     │  Status │
├─────────┼─────────────┼─────────┤
│ UNKNOWN │  tailscale  │ RUNNING │
│ HEALTHY │  postfix    │ RUNNING │
└─────────┴─────────────┴─────────┘
```

### ネットワーク構成
- **タスク ARN**: `arn:aws:ecs:ap-northeast-1:552927148143:task/mailserver-cluster/f93116aaada746bc83746ec1b73ab460`
- **ENI ID**: `eni-008dd6312e2b10681`
- **パブリック IP**: `18.177.139.144`
- **Elastic IP** (Terraform管理): `43.207.242.167`

### IAM ポリシー検証
```json
{
  "Statement": [
    {
      "Action": [
        "secretsmanager:GetSecretValue",
        "secretsmanager:DescribeSecret"
      ],
      "Effect": "Allow",
      "Resource": [
        "arn:aws:secretsmanager:ap-northeast-1:552927148143:secret:mailserver/tailscale/fargate-auth-key-*",
        "arn:aws:secretsmanager:ap-northeast-1:552927148143:secret:mailserver/sendgrid/api-key-*"
      ]
    }
  ]
}
```

✅ アカウント ID `552927148143` が明示的に設定されました（ワイルドカードなし）。

---

## 📚 必要な文書更新

### 1. 文書バージョンの更新
**ファイル**: `/opt/onprem-infra-system/project-root-infra/Docs/application/mailserver/04_installation.md`
**3行目**:
```markdown
**文書バージョン**: 5.2 → 5.3
**作成日**: ... / 2025-11-03（v5.3改訂）
```

### 2. トラブルシューティングエントリの追加
**ファイル**: `04_installation.md`
**セクション**: 9. トラブルシューティング (2524行目以降)

新しいサブセクションを追加:

```markdown
### 9.X Fargate Task起動エラー: "AccessDeniedException: secretsmanager:GetSecretValue"

**症状**:
```
ResourceInitializationError: unable to pull secrets or registry auth:
execution resource retrieval failed: unable to retrieve secret from asm:
... AccessDeniedException: User: arn:aws:sts::XXXXXXXXXXXX:assumed-role/
mailserver-execution-role/... is not authorized to perform:
secretsmanager:GetSecretValue on resource: ...
```

**原因**:
IAM Execution Role の Secrets Manager ポリシーで AWS アカウント ID にワイルドカード (`*`) が使用されていた場合、AWS は明示的なアカウント ID を要求するため、アクセスが拒否されます。

**対処**:

1. **Terraform v5.3+ を使用している場合**: すでに修正済みです。以下で確認してください:
```bash
cd /opt/onprem-infra-system/project-root-infra/services/mailserver/terraform
terraform plan
# 出力に変更がなければ、すでに正しい設定です
```

2. **Terraform v5.2 以前を使用している場合**: 以下の手順で修正してください:

```bash
cd /opt/onprem-infra-system/project-root-infra/services/mailserver/terraform

# main.tf を編集: data "aws_caller_identity" を追加
# (line 33 付近)
# data "aws_caller_identity" "current" {}

# IAM policy の Resource を修正 (line 282-283)
# arn:aws:secretsmanager:${var.aws_region}:*:secret:...
# ↓
# arn:aws:secretsmanager:${var.aws_region}:${data.aws_caller_identity.current.account_id}:secret:...

# Terraform apply
terraform plan
terraform apply
```

3. **IAM ポリシー検証**:
```bash
aws iam get-role-policy \
  --role-name mailserver-execution-role \
  --policy-name mailserver-execution-secrets-access \
  --query 'PolicyDocument.Statement[0].Resource' \
  --output json

# 期待される出力 (account ID が明示的に設定されている):
# [
#   "arn:aws:secretsmanager:ap-northeast-1:552927148143:secret:mailserver/tailscale/fargate-auth-key-*",
#   "arn:aws:secretsmanager:ap-northeast-1:552927148143:secret:mailserver/sendgrid/api-key-*"
# ]
```

4. **ECS Service 再起動** (IAM ポリシー更新後):
```bash
# ECS は自動的に新しいタスクを起動します
# 1-2分待機後、タスク状態を確認
aws ecs describe-tasks \
  --cluster mailserver-cluster \
  --tasks $(aws ecs list-tasks --cluster mailserver-cluster --service-name mailserver-mx-service --query 'taskArns[0]' --output text) \
  --query 'tasks[0].{Status:lastStatus,Containers:containers[].{Name:name,Status:lastStatus,Health:healthStatus}}' \
  --output table
```

**成功基準**:
- Task Status: `RUNNING`
- Postfix Health: `HEALTHY`
- Tailscale Status: `RUNNING` (Health: UNKNOWN は正常)
```

### 3. セクション 3.1 (Terraform) への注記追加
**ファイル**: `04_installation.md`
**場所**: 220行目以降 (IAM Role の説明後)

```markdown
**⚠️ 重要**: Terraform v5.3 以降では、IAM Execution Role の Secrets Manager ポリシーに AWS アカウント ID が自動的に設定されます。v5.2 以前のバージョンからアップグレードする場合は、`terraform apply` で IAM ポリシーを更新してください。
```

---

## 🚀 次のステップ

### 即座のアクション
1. ✅ Terraform 設定の更新と適用
2. ✅ ECS タスクの正常起動
3. ⏳ 文書更新 (バージョンアップ、トラブルシューティングセクション)
4. ⏳ Fargate パブリック IP への SMTP 接続テスト
5. ⏳ Fargate と Dell 間の Tailscale VPN 接続検証

### テストチェックリスト
- [ ] 外部メールサーバーからの SMTP ポート 25 接続テスト
- [ ] Tailscale VPN トンネル確立の検証
- [ ] Fargate から Dell への LMTP リレー (ポート 2525)
- [ ] エンドツーエンドのメールフロー テスト (外部 → Fargate → Dell → Maildir)

---

## 📊 インフラストラクチャ概要

### AWS リソース (Terraform管理)
| リソースタイプ | 名前/ID | ステータス |
|---------------|---------|-----------|
| VPC | `vpc-02c5ed03375f21811` | ✅ Active |
| サブネット | `subnet-03ab1f9a5121c1594` (1a)<br>`subnet-066ab3c495a6cd9ec` (1c) | ✅ Active |
| セキュリティグループ | `sg-0fd8c512a93aac2b6` | ✅ Active |
| Elastic IP | `43.207.242.167` (`eipalloc-04e838a5b1c9c7dde`) | ✅ 割り当て済み |
| ECS クラスター | `mailserver-cluster` | ✅ Active |
| IAM Execution Role | `mailserver-execution-role` | ✅ Active (ポリシー修正済み) |
| IAM Task Role | `mailserver-task-role` | ✅ Active |

### Secrets Manager
| シークレット名 | ARN | ステータス |
|-------------|-----|-----------|
| `mailserver/tailscale/fargate-auth-key` | `...secret:...fargate-auth-key-j83uJT` | ✅ Active |

### ECS Service
| サービス名 | タスク定義 | 期待数 | 実行数 | ステータス |
|-----------|------------|--------|--------|-----------|
| `mailserver-mx-service` | `mailserver-mx-task:1` | 1 | 1 | ✅ Active |

---

## 📝 学んだ教訓

1. **IAM ポリシーの明示性**: AWS Secrets Manager は IAM リソース ARN で明示的なアカウント ID を要求します。ワイルドカードは権限拒否を引き起こします。

2. **Terraform データソース**: ハードコードやワイルドカードの代わりに `data "aws_caller_identity"` を使用してアカウント ID を動的に取得します。

3. **変数展開の検証**: AWS API 呼び出しの前に、テンプレート変数が適切に展開されていることを常に検証します。マニュアルの検証チェック付き `envsubst` アプローチが正しいです。

4. **ECS タスク失敗診断**: `aws ecs describe-tasks` を `stopCode` と `stoppedReason` フィールドとともに使用して、IAM/ネットワーク問題を迅速に特定します。

---

## 🔗 関連ファイル

- Terraform 設定: `/opt/onprem-infra-system/project-root-infra/services/mailserver/terraform/main.tf`
- Task Definition: `/opt/onprem-infra-system/project-root-infra/services/mailserver/fargate-task-definition.json`
- インストールマニュアル: `/opt/onprem-infra-system/project-root-infra/Docs/application/mailserver/04_installation.md`

---

**レポート作成日**: 2025-11-03 16:52 JST
**作成者**: DevOps Architect Agent (Claude Code)
