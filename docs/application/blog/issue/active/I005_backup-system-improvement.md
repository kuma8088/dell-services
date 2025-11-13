# I005: バックアップシステム改善・最適化

**関連タスク**: [#005] バックアップシステムの更新
**ステータス**: Inbox
**優先度**: Low
**作成日**: 2025-11-10
**担当**: 未割当
**依存**: I004（バックアップ不具合修正）

---

## 📋 課題概要

Blog System バックアップシステムの改善・最適化を検討する。現在はローカルバックアップのみのため、オフサイトバックアップやリストア自動化等の改善余地がある。

---

## 🎯 目標

データ保護の信頼性向上と運用効率化を実現する。

---

## 📌 現状

### 既存実装（Mailserver参考）
- ローカルバックアップ: `/mnt/backup-hdd/mailserver/`
- S3オフサイトバックアップ: Phase 11-B（完了）
- TDD開発（38テスト）
- マルウェアスキャン（ClamAV + rkhunter）

### Blog System現状
- ローカルバックアップ: 未実装（I004で対応予定）
- S3バックアップ: 未実装
- リストアスクリプト: 未実装

---

## 💡 改善提案

### 案A: Mailserver方式の踏襲
- Mailserverと同じS3バックアップ構成を適用
- メリット: 実績あり、運用ノウハウ活用
- デメリット: Terraform管理が2セット必要

### 案B: 統合バックアップシステム
- Mailserver + Blog を1つのS3バケットで管理
- メリット: 管理コスト削減、コスト最適化
- デメリット: リストア時の複雑性増加

### 案C: 増分バックアップ導入
- rsync --link-dest でディスク効率化
- メリット: ストレージコスト削減
- デメリット: 実装複雑度増加

---

## 📋 改善項目（案）

### 優先度: High
- [ ] S3オフサイトバックアップ実装
- [ ] リストアスクリプト作成
- [ ] バックアップ検証自動化（整合性チェック）

### 優先度: Medium
- [ ] 増分バックアップ導入
- [ ] バックアップ暗号化（at-rest encryption）
- [ ] バックアップメトリクス（成功率、サイズ推移等）

### 優先度: Low
- [ ] リストア訓練自動化
- [ ] バックアップポリシー自動適用
- [ ] コスト最適化（Glacier移行等）

---

## 📋 技術検討事項

### S3バックアップ構成
- **バケット分離 vs 統合**
  - 分離: `blog-backup-bucket` + `mailserver-backup-bucket`
  - 統合: `dell-system-backup/blog/` + `dell-system-backup/mailserver/`

### 暗号化方式
- SSE-S3（AES-256）
- SSE-KMS（独自キー管理）

### ライフサイクルポリシー
- 30日後: Standard-IA移行
- 90日後: Glacier移行
- 365日後: 削除

---

## 🚧 ブロッカー

- I004（バックアップ不具合修正）の完了待ち

---

## 📝 次のステップ

1. I004完了後に改善要件整理
2. Mailserver Phase 11-B実装レビュー
3. Blog用バックアップ戦略策定
4. POC実施
5. 本番ホストで `/etc/mailserver-backup/config` に `S3_BUCKET=system-backup-workstation` を設定し、`mailserver-backup-uploader` プロファイルで `services/mailserver/scripts/backup-to-s3.sh --date <検証日>` を実行後、CloudWatch（S3 Storage/Metrics + CloudTrail PutObject）で転送ログを確認し正式なエビデンスを取得

---

## 🆕 調査ログ

- 2025-11-13: I004のプリフライト修正を実施（S3アップロードは11/14 04:00の定期実行で最終確認予定）。
- 2025-11-13: I005の着手準備として、Mailserver Phase 11-B構成の流用可能性を調査開始。
- 2025-11-13: `rental/scripts/backup_rental.sh`（mail+blog統合バックアップ）および `rental/scripts/upload_rental_s3.sh` を作成。明日朝のcronで統合環境を検証予定。
- 2025-11-13: 新 S3 バケット `system-backup-workstation` を採用し、リポジトリ内の参照を順次置き換え開始（旧 `mailserver-backup-552927148143` は削除対象）。
- 2025-11-13: `/etc/mailserver-backup/config` 相当の設定で `S3_BUCKET=system-backup-workstation` を指定し、`services/mailserver/scripts/backup-to-s3.sh --date 2025-11-12` をモックAWS（スタブCLI）+ダミーデータで実行。`aws s3 sync ... s3://system-backup-workstation/daily/2025-11-12/` が呼ばれ、ログにも Object Lock 有効化まで記録されることを確認。実環境では同設定を投入すれば新バケットへのフルアップロードが動作する。
- 2025-11-13: 本番環境で `/etc/mailserver-backup/config` を新バケットに切替後、`services/mailserver/scripts/backup-to-s3.sh --date 2025-11-13` を `mailserver-backup-uploader` で実行し、`s3://system-backup-workstation/daily/2025-11-13/` へのアップロードが成功した。CloudWatch で PutObject を確認済。ただし Object Lock が `Disabled` で警告が出たため、Terraform (`services/mailserver/terraform/s3-backup/s3.tf`) の `object_lock_enabled` / `aws_s3_bucket_object_lock_configuration` が適用されているか再確認し、必要なら `aws s3api` で有効化するタスクを追加する。
- 2025-11-13: mail 側のローカルバックアップ先を `/mnt/backup-hdd/mailserver` から `RENTAL_ROOT=/mnt/backup-hdd/rental/mail` へ切替。`services/mailserver/scripts/backup-config.sh` の `BACKUP_ROOT` デフォルトを更新し、`test-backup.sh` も新ディレクトリ構造を前提に修正。blog 側と同じ rental 配下で日次/週次バックアップが管理できる状態になった（既存の旧ディレクトリは参照のみ保持）。
- 2025-11-13: blog 側の S3 アップロードを `rental/scripts/upload_rental_s3.sh --date 2025-11-13` で実行。約1h10m かけて `sites/` 一式を送信したが、`aws s3 sync` がエラー詳細を出さず Exit 1 → `S3 upload failed`。IAM ポリシーの AccessDenied は解消済みで、セッション有効期限(1h)切れが濃厚。
- 2025-11-13 **暫定対応完了**:
  - ✅ IAM session duration を 7200s (2時間) に延長: `~/.aws/config` の `duration_seconds=7200` + Terraform `iam.tf` の `max_session_duration=7200` を適用
  - ✅ Lifecycle ポリシーを7日削除に変更 (災害時バックアップ用、必要なら延長可能)
  - ✅ Terraform リソース名を `websystem_backup` に統一 (mail+blog統合を明示)
  - ✅ 旧バケット `mailserver-backup-552927148143` を Terraform 管理から除外 (AWS上にセキュア保持、Object Lock 削除不可)
  - ✅ CloudWatch/SNS を `websystem-s3-backup-*` に改名
  - ⏳ **明日 2025-11-14 4:30 AM の自動実行で最終確認**:
    - `~/.rental-backup.log` で blog S3 アップロード成功確認
    - セッションタイムアウトエラーがないこと確認
    - `s3://system-backup-workstation/daily/2025-11-14/blog/` への完全アップロード確認

---

## 📐 設計仕様（RentalServerFunction 統合案）

### 目的
mailserver/blog を個別ではなく「RentalServerFunction」という共通バックアップ基盤に統合し、スクリプト・S3・リストア手順を一元管理する。

### 1. ディレクトリ/アーティファクト構成

```
/mnt/backup-hdd/rental/
├── daily/
│   ├── mail/
│   └── blog/
└── weekly/
    ├── mail/
    └── blog/
```

- `backup_rental.sh`（新規）から `backup_mail()` と `backup_blog()` を呼び出して同一ログ・ローテーションルールで管理。
- ログは `/home/system-admin/.rental-backup.log` に統合し、既存 `.mailserver-backup.log` から移行。

### 2. S3バケット/キー構造

```
s3://rental-backup-<account-id>/
└── daily/
    ├── mail/<YYYY-MM-DD>/...
    └── blog/<YYYY-MM-DD>/...
```

- Phase 11-B の設定を流用しつつ、`S3_PREFIX=mail`/`blog` を切り替えて同期。
- S3ライフサイクル/オブジェクトロックは共通ポリシーで管理。

### 3. cron/ジョブ設計

```cron
0 3 * * * /opt/.../RentalServerFunction/backup_rental.sh daily
0 4 * * 0 /opt/.../RentalServerFunction/backup_rental.sh weekly
0 4 * * * /opt/.../RentalServerFunction/upload_to_s3.sh daily
```

- 既存 mail 側のジョブを差し替え、blog 分も同じスケジュールに乗せる。

### 4. リストア手順

- `RentalServerFunction/restore.sh --target mail --date YYYY-MM-DD`
- `RentalServerFunction/restore.sh --target blog --date YYYY-MM-DD`
- mail/blog で差分が必要な部分（DB名、マウント先など）はサブルーチン化して切り替える。

### 5. 段階的移行

1. #004最終確認後、`backup_rental.sh` を mail のみで動かし旧構成と整合を取る。
2. blog バックアップ処理を同スクリプトに追加し `/mnt/backup-hdd/blog` から新ディレクトリへ移行。
3. 旧ログ・旧cronを削除し、ドキュメントを `RentalServerFunction` ベースへ更新。

（現システムは構築段階につき、構成変更に伴う互換性リスクは低い前提で進める）

---

## 📚 関連ドキュメント

- `docs/application/01_improvement+issue.md` - タスク#005
- `docs/application/mailserver/backup/07_s3backup_implementation.md` - Mailserver S3バックアップ
- `services/mailserver/terraform/s3-backup/` - Terraform実装
- I004_backup-system-troubleshooting.md

---

## 📅 更新履歴

- 2025-11-10: Issue作成
