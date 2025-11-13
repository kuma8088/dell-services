# I005 付随: 旧 S3 バケット削除手順（mailserver-backup-552927148143）

## 目的

I005 の改善作業に先立ち、既存バックアップバケット `mailserver-backup-552927148143` を安全に廃止する。Object Lock (COMPLIANCE) が有効なバケットを削除する際の落とし穴を残さないよう、手順を明文化する。

## 事前準備

- 新しいバックアップバケット（命名例: `rental-backup-prod-<random>`）を作成済みで、最低限以下を設定しておく:
  - バージョニング有効化
  - 必要な Object Lock ポリシー（再設計後に適用）
  - IAM ポリシー/ロールを更新し `mailserver-backup-uploader` などのプロファイルが新バケットへアクセスできること
- `/etc/mailserver-backup/config` など既存スクリプト設定を更新し、新バケット名へ切り替える
- ただちに復元できるよう、新バケット側へのフルバックアップアップロードが完了していることを確認
- CLI 実行環境で `aws configure --profile mailserver-backup-uploader` が利用可能

> **重要:** Object Lock を COMPLIANCE モードで有効化している場合、保持期限が残っているオブジェクトは削除できない。保持解除→オブジェクト削除→バケット削除の順に進める。

## 手順

### 1. 旧バケット参照を完全に停止

1. `crontab -l` / systemd timer などで `mailserver-backup-552927148143` を参照するジョブを一時停止
2. `/etc/mailserver-backup/config` からバケット名・プレフィックスを **新バケット `system-backup-workstation`** に更新  
   ```bash
   sudo sed -i 's/mailserver-backup-552927148143/system-backup-workstation/' /etc/mailserver-backup/config
   ```
3. `backup_rental.sh` `upload_rental_s3.sh` などを手動実行し、新バケットでバックアップが成功することをログ（`~/.rental-backup.log`）で確認

> リポジトリ内のサンプルコマンドおよび Terraform (`services/mailserver/terraform/s3-backup/s3.tf`) は `system-backup-workstation` に置き換え済み。サーバー上の `/etc/mailserver-backup/config` も同名称へ更新すること。

### 2. Object Lock 設定と保持の確認

### 2.1 IAM 権限の一時付与

`mailserver-backup-uploader` ロールには Object Lock 関連 API が付与されていないため、以下のようなインラインポリシーを **削除作業が完了するまで一時的にアタッチ** する。

```json
{
  "Version": "2012-10-17",
  "Statement": [
    {
      "Effect": "Allow",
      "Action": [
        "s3:GetBucketObjectLockConfiguration",
        "s3:PutBucketObjectLockConfiguration",
        "s3:ListBucketVersions",
        "s3:GetObjectRetention",
        "s3:PutObjectRetention",
        "s3:DeleteObject",
        "s3:DeleteObjectVersion",
        "s3:BypassGovernanceRetention"
      ],
      "Resource": [
        "arn:aws:s3:::mailserver-backup-552927148143",
        "arn:aws:s3:::mailserver-backup-552927148143/*"
      ]
    }
  ]
}
```

> `s3:PutObjectRetention` 実行時は `s3:BypassGovernanceRetention` が必須。IAM ポリシーに明示的に含め、アクセス許可ダイアログで承認する。

### 2.2 Object Lock 状態確認

```bash
aws s3api get-object-lock-configuration \
  --bucket mailserver-backup-552927148143 \
  --profile mailserver-backup-uploader
```

- `ObjectLockEnabled: Enabled` かつ `Rule -> DefaultRetention` が表示されれば COMPLIANCE モードが生きている
- 各オブジェクトに個別保持があるかどうかは `HeadObject` で `Retention` を確認する

### 3. オブジェクト個別保持の解除

保持中バージョンの `RetainUntilDate` を確認し、現行値より後ろの日時に更新する。以下の順で実行する。

#### 3.1 バージョン一覧の取得

```bash
aws s3api list-object-versions \
  --bucket mailserver-backup-552927148143 \
  --profile mailserver-backup-uploader \
  --output json > /tmp/mailserver-backup-versions.json
```

確認したいキーと VersionId は `jq` で抽出できる（`Key:`、`VersionId:` のラベル付きで表示するとわかりやすい）。

```bash
jq -r '.Versions[] | "Key: \(.Key)\nVersionId: \(.VersionId)\n"' /tmp/mailserver-backup-versions.json | head -n 6
# 例:
# Key: daily/2025-11-07/backup.log
# VersionId: D.5wRu8k8pYqen1b_jeibN_Wn4HOkt9j
# Key: daily/2025-11-07/checksums.sha256
# VersionId: E.pWMTFafbqeyJwHGcXj2Bwq0HbmaOSO
```

#### 3.2 個別に保持期限を確認する（必要に応じて）

```bash
aws s3api get-object-retention \
  --bucket mailserver-backup-552927148143 \
  --key <Key> \
  --version-id <VersionId-from-list-object-versions> \
  --profile mailserver-backup-uploader
```

`--version-id` には `list-object-versions` で得た正確な ID を指定する。誤った ID を渡すと `Invalid version id specified` で失敗する。戻り値 `RetainUntilDate` 以降の日時に更新する必要がある。

#### 3.3 全オブジェクトの保持期限を延長（+1分）して削除可能にする

```bash
jq -r '.Versions[] | select(.VersionId != null) | [.Key, .VersionId] | @tsv' /tmp/mailserver-backup-versions.json \
  | while IFS=$'\t' read -r key version_id; do
      CURRENT=$(aws s3api get-object-retention \
        --bucket mailserver-backup-552927148143 \
        --key "$key" \
        --version-id "$version_id" \
        --profile mailserver-backup-uploader \
        --query 'Retention.RetainUntilDate' \
        --output text 2>/dev/null)
      EXPIRY=$(date -u -d "${CURRENT:-now}+1 minute" --iso-8601=seconds)
      aws s3api put-object-retention \
        --bucket mailserver-backup-552927148143 \
        --key "$key" \
        --version-id "$version_id" \
        --retention "Mode=COMPLIANCE,RetainUntilDate=${EXPIRY}" \
        --bypass-governance-retention \
        --profile mailserver-backup-uploader || {
          echo "Retention update failed for ${key} (${version_id})"
          exit 1
        }
    done
```

> COMPLIANCE モードでは保持期限を短縮できないため、`RetainUntilDate` は**常に現行値以上**を指定する。上記ループでは `get-object-retention` で既存日時を取得し、+1 分延長した値を設定している。`select(.VersionId != null)` で DeleteMarker を除外し、失敗した場合は即座に `exit 1` して無限ループ化を防ぐ。

COMPLIANCE モードでも `RetainUntilDate` が過去になれば削除可能になる。保持解除をスクリプト化する際は誤操作を防ぐため dry-run を用意する。

### 4. バケットの Object Lock 構成を無効化

全オブジェクトの保持解除が完了したら、バケット全体の設定を無効化する。

```bash
aws s3api put-object-lock-configuration \
  --bucket mailserver-backup-552927148143 \
  --object-lock-configuration '{}'
  --profile mailserver-backup-uploader
```

`get-object-lock-configuration` で `ObjectLockEnabled` が表示されないことを再確認する。

### 5. バージョン付きオブジェクトの完全削除

1. すべてのオブジェクト＋削除マーカーを消す:
   ```bash
   aws s3api delete-objects \
     --bucket mailserver-backup-552927148143 \
     --delete file://<(jq '{Objects: [.Versions[] | {Key: .Key, VersionId: .VersionId}], Quiet: true}' /tmp/mailserver-backup-versions.json) \
     --profile mailserver-backup-uploader
   ```
2. `aws s3api list-object-versions` を再実行し、`Versions` / `DeleteMarkers` が空であることを確認

### 6. バケット削除

```bash
aws s3api delete-bucket \
  --bucket mailserver-backup-552927148143 \
  --profile mailserver-backup-uploader
```

削除後に `aws s3 ls` またはコンソールで対象バケットが表示されないことを確認する。

### 7. 監査ログ更新

- `~/.rental-backup.log` / `~/.rental-backup-error.log` に旧バケット削除の記録を追記
- `docs/application/blog/issue/active/I005_backup-system-improvement.md` の「現状」「次のステップ」を更新し、旧バケット廃止済みである旨を明記

## 注意事項

- COMPLIANCE モードのバケットを削除する際は、保持設定解除 → オブジェクト削除 → Object Lock 無効化 → バケット削除の順序を崩さないこと
- バケット名にアカウント ID を含めると外部公開時に内部構成が露出するため、以後は乱数や用途プレフィックスを組み合わせた命名規則を採用する
- 旧バケット削除後、Terraform や shell script、ドキュメント内のハードコードを速やかに置換する（`rg mailserver-backup-552927148143` で漏れ確認）
- Object Lock 解除のために追加した IAM ポリシーは、作業完了後に必ずロールから削除し最小権限状態へ戻す

---

## 🆕 対応状況

**2025-11-13 暫定対応完了**:

- ✅ **新バケット移行完了**: `system-backup-workstation` へ完全移行
- ✅ **Terraform 更新完了**:
  - リソース名を `websystem_backup` に統一
  - 旧バケット `mailserver-backup-552927148143` を Terraform 管理から除外（`terraform state rm` 実行済み）
  - 新バケットには Object Lock を設定しない方針
  - Lifecycle を7日削除に変更（災害時バックアップ用）
- ✅ **AWS 設定**:
  - IAM session duration を 7200s (2時間) に延長
  - CloudWatch/SNS を `websystem-s3-backup-*` に改名
- ⏳ **旧バケット削除**:
  - **当面不要** - Object Lock COMPLIANCE モードで削除不可
  - AWS上にセキュア保持（Public Access Block + Encryption 有効）
  - 将来的に保持期限が切れた際に本手順で削除を検討
- ⏳ **明日 2025-11-14 4:30 AM の自動実行で最終確認**:
  - `~/.rental-backup.log` で新バケットへの S3 アップロード成功確認
  - セッションタイムアウトエラーがないこと確認
