# I004: 自動バックアップ不具合修正（緊急）

**関連タスク**: [#004] 自動バックアップの不具合修正（緊急）
**ステータス**: Inbox
**優先度**: Critical ⚠️
**作成日**: 2025-11-10
**担当**: 未割当

---

## 📋 課題概要

Blog Systemの自動バックアップが機能していない。`/mnt/backup-hdd/blog/backups/daily/` および `weekly/` ディレクトリが空の状態。

---

## 🎯 目標

日次・週次バックアップの正常動作を復旧し、データ損失リスクを最小化する。

---

## 📌 現状

### 確認事項
- [ ] cron設定が存在するか
- [ ] バックアップスクリプトが存在するか
- [ ] バックアップ先ディレクトリのパーミッション
- [ ] ディスク容量
- [ ] cron実行ログ

### 現在の状態
```bash
/mnt/backup-hdd/blog/backups/
├── daily/    # 空
└── weekly/   # 空
```

---

## 💡 想定される原因

1. **バックアップスクリプト未作成**
   - `services/blog/scripts/backup.sh` が存在しない
   - 確認コマンド: `ls -la services/blog/scripts/`

2. **cron未設定**
   - Blog用のcronジョブが登録されていない
   - 確認コマンド: `crontab -l | grep blog`

3. **パーミッション問題**
   - バックアップ先ディレクトリへの書き込み権限なし
   - 確認コマンド: `ls -ld /mnt/backup-hdd/blog/backups/`

4. **ディスク容量不足**
   - `/mnt/backup-hdd` の空き容量不足
   - 確認コマンド: `df -h /mnt/backup-hdd`

---

## 🔧 対応手順

### Phase 1: 調査（即時実施）
```bash
# 1. バックアップスクリプト確認
ls -la /opt/onprem-infra-system/project-root-infra/services/blog/scripts/

# 2. cron設定確認
crontab -l | grep -i blog

# 3. パーミッション確認
ls -ld /mnt/backup-hdd/blog/backups/{daily,weekly}

# 4. ディスク容量確認
df -h /mnt/backup-hdd

# 5. 過去のログ確認
ls -la ~/.blog-backup.log
```

### Phase 2: バックアップスクリプト作成
- [ ] Mailserver バックアップスクリプトを参考
- [ ] WordPress サイトファイルバックアップ（rsync）
- [ ] MariaDB ダンプバックアップ（mysqldump）
- [ ] バックアップローテーション（daily 7日, weekly 4週）
- [ ] 実装場所: `services/blog/scripts/backup.sh`
- [ ] 参考: `services/mailserver/scripts/backup/backup.sh`

### Phase 3: cron設定
```bash
# 日次バックアップ: 毎日 3:00
0 3 * * * /opt/onprem-infra-system/project-root-infra/services/blog/scripts/backup.sh daily >> ~/.blog-backup.log 2>&1

# 週次バックアップ: 日曜 4:00
0 4 * * 0 /opt/onprem-infra-system/project-root-infra/services/blog/scripts/backup.sh weekly >> ~/.blog-backup.log 2>&1
```

### Phase 4: 動作確認
- [ ] 手動実行テスト
- [ ] バックアップファイル生成確認
- [ ] ローテーション動作確認
- [ ] cron実行確認（翌日）

---

## 🚧 ブロッカー

なし（即座に対応可能）

---

## 📝 次のステップ

1. 調査フェーズ実施 ✅（プリフライト/AWS_REGION差異を特定）
2. バックアップスクリプト作成／修正 ✅（`AWS_DEFAULT_REGION` 参照に修正）
3. cron設定 ✅（既存設定を維持）
4. 動作確認（手動プリフライト済、S3アップロードは11/14 04:00の定期実行で最終確認）
5. **2025-11-13 暫定対応完了**:
   - ✅ IAM session duration を 7200s (2時間) に延長 (blog 1h10m 対応)
   - ✅ Lifecycle を7日削除に変更
   - ✅ Terraform を `websystem_backup` に統一
   - ⏳ **明日 2025-11-14 4:30 AM の自動実行で最終確認**:
     - `~/.rental-backup.log` で mail/blog S3 アップロード成功確認
     - セッションタイムアウトエラーがないこと確認
     - 成功したら I004 をクローズ

---

## 📚 関連ドキュメント

- `docs/application/01_improvement+issue.md` - タスク#004
- `services/mailserver/scripts/backup/backup.sh` - 参考実装
- `docs/application/mailserver/backup/03_implementation.md` - Mailserver バックアップ仕様
- C001_Xserver-migration-issues.md - Phase 2 Task 2-1/2-2

---

## 📅 更新履歴

- 2025-11-10: Issue作成
