# EC2 Relay Domains 自動同期機能 要件定義書

**文書番号**: MS-SPEC-006
**作成日**: 2025-11-05
**バージョン**: 1.0
**ステータス**: Draft

---

## 📋 **1. 機能概要**

Dell 管理画面（usermgmt）でドメイン追加/削除時、EC2 MX サーバーの `relay_domains` 設定を自動的に同期し、新規ドメインのメール受信を可能にする。

### **背景**

現在、管理画面でドメインを追加しても EC2 側の設定は手動で行う必要があり、以下の問題が発生している：

- **運用負荷**: ドメイン追加のたびに EC2 に SSH して手動設定が必要
- **設定漏れリスク**: EC2 設定を忘れるとメールが受信できない（`Relay access denied` エラー）
- **整合性**: Dell と EC2 の設定が乖離する可能性

### **目的**

- 管理画面でのドメイン追加/削除を EC2 に自動反映
- 運用負荷の削減
- 設定ミスの防止

---

## 🎯 **2. 機能要件**

### **FR-1: ドメインリスト取得**

**要件ID**: FR-001
**優先度**: P0 (必須)

- Dell MariaDB から有効なドメインリストを取得
- **対象テーブル**: `mailserver_usermgmt.domains`
- **取得条件**: `enabled = 1`
- **取得カラム**: `name`
- **クエリ例**:
  ```sql
  SELECT name FROM domains WHERE enabled = 1;
  ```

**成功条件**:
- 有効なドメインリストを正常に取得できる
- DB 接続失敗時は現在の設定を維持し、エラーログを出力

---

### **FR-2: relay_domains 更新**

**要件ID**: FR-002
**優先度**: P0 (必須)

- 取得したドメインリストで EC2 Postfix の `relay_domains` を上書き
- 既存ドメイン（kuma8088.com, m8088.com など）を保持
- 重複排除を行う

**更新方法**:
```bash
postconf -e "relay_domains = domain1.com, domain2.com, ..."
```

**成功条件**:
- DB から取得したドメインがすべて `relay_domains` に含まれる
- 既存ドメインが削除されない
- 重複がない

---

### **FR-3: transport 設定更新**

**要件ID**: FR-003
**優先度**: P0 (必須)

- 新規ドメインを `/etc/postfix/transport` に追加
- **フォーマット**: `<domain> smtp:[100.110.222.53]:2525`
- `postmap /etc/postfix/transport` で .db ファイル生成

**更新ルール**:
- DB に存在するドメインのみを transport に記載
- Dell の Tailscale IP (100.110.222.53) に転送
- Port 2525 (Dell Dovecot LMTP) を指定

**成功条件**:
- すべての有効ドメインが transport に記載される
- postmap が正常に完了し .db ファイルが生成される

---

### **FR-4: Postfix リロード**

**要件ID**: FR-004
**優先度**: P0 (必須)

- 設定変更後に `postfix reload` を実行
- リロード失敗時はロールバック

**リロード方法**:
```bash
postfix reload
```

**成功条件**:
- `postfix reload` が exit code 0 で完了
- リロード中も既存の接続は維持される
- 失敗時は設定をロールバック

---

### **FR-5: 定期実行**

**要件ID**: FR-005
**優先度**: P0 (必須)

- cron で 5 分間隔で実行
- システム起動時にも 1 回実行

**Cron 設定**:
```cron
*/5 * * * * /opt/mailserver/scripts/sync-relay-domains.sh
@reboot sleep 30 && /opt/mailserver/scripts/sync-relay-domains.sh
```

**成功条件**:
- cron が正常に動作し、5分ごとに実行される
- 起動時に 30 秒待機後に 1 回実行される

---

## 🔒 **3. 非機能要件**

### **NFR-1: セキュリティ**

**要件ID**: NFR-001
**優先度**: P0 (必須)

#### **DB 接続**
- **ユーザー**: `relay_sync@'100.70.131.116'` (EC2 Tailscale IP 限定)
- **権限**: `SELECT` のみ (読み取り専用)
- **対象 DB**: `mailserver_usermgmt`
- **対象テーブル**: `domains`

#### **パスワード管理**
- **方式**: 環境変数または設定ファイル
- **推奨**: AWS Secrets Manager (将来対応)
- **ファイルパーミッション**: `0600` (root のみ読み取り可能)

#### **通信経路**
- **必須**: Tailscale VPN 経由のみ (100.110.222.53)
- **ポート**: 3306 (MySQL)
- **暗号化**: MySQL 接続は TLS 推奨（初期は平文も許可）

#### **スクリプト実行権限**
- **実行ユーザー**: root
- **スクリプトパーミッション**: `0700`

---

### **NFR-2: 性能**

**要件ID**: NFR-002
**優先度**: P1 (重要)

| 処理 | 目標時間 | 最大許容時間 |
|------|----------|--------------|
| DB クエリ | < 1秒 | 3秒 |
| relay_domains 更新 | < 1秒 | 2秒 |
| transport 更新 | < 1秒 | 2秒 |
| postmap 実行 | < 1秒 | 3秒 |
| postfix reload | < 3秒 | 5秒 |
| **合計実行時間** | **< 5秒** | **10秒** |

**パフォーマンス要件**:
- ドメイン数 100 件以下では 5 秒以内に完了
- DB クエリは適切なインデックスを使用
- 不必要な処理を避ける（変更がない場合は早期リターン）

---

### **NFR-3: 可用性**

**要件ID**: NFR-003
**優先度**: P1 (重要)

#### **障害時影響**
| 障害 | 影響 | 対応 |
|------|------|------|
| DB 接続失敗 | なし | 現在の設定を維持、次回リトライ |
| DB クエリ失敗 | なし | 現在の設定を維持、エラーログ |
| 設定ファイル書き込み失敗 | なし | ロールバック、エラーログ |
| postfix reload 失敗 | **重大** | ロールバック、アラート送信 |

#### **ダウンタイム**
- Postfix reload 中もメール受信は継続（既存接続は維持される）
- 最大ダウンタイム: 0 秒（無停止リロード）

#### **リトライポリシー**
- DB 接続失敗: リトライなし（次回 cron 実行まで待機）
- 理由: 5分間隔で自動実行されるため、即座のリトライは不要

---

### **NFR-4: 保守性**

**要件ID**: NFR-004
**優先度**: P1 (重要)

#### **ログ出力**
- **ログファイル**: `/var/log/mailserver/relay-sync.log`
- **ローテーション**: 日次、30日間保持、gzip 圧縮
- **ログレベル**: INFO, ERROR
- **必須ログ項目**:
  - 実行開始・終了時刻
  - 取得したドメインリスト
  - 追加・削除されたドメイン
  - エラー詳細（スタックトレース含む）

#### **設定ファイル**
- **設定ファイルパス**: `/opt/mailserver/config/relay-sync.conf`
- **フォーマット**: key=value 形式
- **必須項目**:
  ```ini
  DB_HOST=100.110.222.53
  DB_PORT=3306
  DB_NAME=mailserver_usermgmt
  DB_USER=relay_sync
  DB_PASSWORD=<password>
  DELL_RELAY_IP=100.110.222.53
  DELL_RELAY_PORT=2525
  LOG_FILE=/var/log/mailserver/relay-sync.log
  ```

#### **バックアップ**
- **対象**: `relay_domains` 設定、`transport` ファイル
- **保存先**: `/opt/mailserver/backup/`
- **保持世代**: 直近 5 世代
- **ファイル名形式**: `relay_domains.YYYYMMDD-HHMMSS.bak`

---

## 🏗️ **4. システム構成**

### **Dell 側（データソース）**

| 項目 | 値 |
|------|-----|
| **MariaDB IP** | 172.20.0.60 (Docker network) / 100.110.222.53 (Tailscale) |
| **Database** | `mailserver_usermgmt` |
| **Table** | `domains (id, name, enabled, default_quota, created_at, updated_at)` |
| **接続ユーザー** | `relay_sync@'100.70.131.116'` |
| **権限** | `SELECT` on `mailserver_usermgmt.domains` |

### **EC2 側（同期先）**

| 項目 | 値 |
|------|-----|
| **OS** | Amazon Linux 2023 |
| **Postfix Container** | `mailserver-postfix` |
| **スクリプトパス** | `/opt/mailserver/scripts/sync-relay-domains.sh` |
| **設定ファイル** | `/opt/mailserver/config/relay-sync.conf` |
| **ログファイル** | `/var/log/mailserver/relay-sync.log` |
| **バックアップディレクトリ** | `/opt/mailserver/backup/` |

---

## 🔄 **5. データフロー**

```
┌─────────────────────────────────────────────────────────────────┐
│ Cron (*/5 * * * *)                                              │
└────────────────────┬────────────────────────────────────────────┘
                     │
                     ▼
┌─────────────────────────────────────────────────────────────────┐
│ sync-relay-domains.sh                                           │
├─────────────────────────────────────────────────────────────────┤
│ 1. Load config from /opt/mailserver/config/relay-sync.conf     │
│ 2. Connect to Dell MariaDB (100.110.222.53:3306)               │
│ 3. SELECT name FROM domains WHERE enabled=1                    │
│ 4. Get current relay_domains from Postfix                      │
│ 5. Compare: DB domains vs Current domains                      │
└────────────────────┬────────────────────────────────────────────┘
                     │
                     ▼
              ┌──────┴──────┐
              │ Changed?    │
              └──────┬──────┘
                     │
        ┌────────────┴────────────┐
        │ NO                      │ YES
        ▼                         ▼
┌───────────────┐      ┌──────────────────────────┐
│ Log: No change│      │ 6. Backup current config │
│ Exit          │      │ 7. Update relay_domains  │
└───────────────┘      │ 8. Update transport      │
                       │ 9. Run postmap           │
                       │ 10. Reload Postfix       │
                       └──────────┬───────────────┘
                                  │
                       ┌──────────┴──────────┐
                       │ Reload OK?          │
                       └──────────┬──────────┘
                                  │
                     ┌────────────┴────────────┐
                     │ YES                     │ NO
                     ▼                         ▼
            ┌─────────────────┐    ┌──────────────────┐
            │ Log: Success    │    │ Rollback config  │
            │ Exit            │    │ Send alert       │
            └─────────────────┘    │ Log: Failure     │
                                   │ Exit             │
                                   └──────────────────┘
```

---

## ⚠️ **6. エラーハンドリング**

### **エラー分類と対応**

| エラー | 重大度 | 対応 | 影響 |
|--------|--------|------|------|
| **DB 接続失敗** | Low | ログ記録、現状維持 | なし（次回リトライ） |
| **DB クエリ失敗** | Low | ログ記録、現状維持 | なし |
| **transport 書き込み失敗** | Medium | ロールバック、エラーログ | 設定変更なし |
| **postmap 失敗** | Medium | ロールバック、エラーログ | 設定変更なし |
| **postfix reload 失敗** | **Critical** | ロールバック、アラート送信 | **手動対応必要** |

### **ロールバック手順**

```bash
# 1. バックアップから復元
cp /opt/mailserver/backup/relay_domains.$(date +%Y%m%d).bak /tmp/main.cf.backup
cp /opt/mailserver/backup/transport.$(date +%Y%m%d).bak /etc/postfix/transport

# 2. relay_domains を復元
postconf -e "relay_domains = $(cat /tmp/main.cf.backup)"

# 3. transport を再生成
postmap /etc/postfix/transport

# 4. Postfix をリロード
postfix reload
```

---

## 📊 **7. ログ要件**

### **ログフォーマット**

```
[YYYY-MM-DD HH:MM:SS] [LEVEL] [MESSAGE]
```

### **ログレベル**

- **INFO**: 通常の処理フロー
- **ERROR**: エラー発生時

### **ログ出力例**

#### **正常実行**
```
[2025-11-05 18:30:00] INFO: ===== Relay Domains Sync Started =====
[2025-11-05 18:30:01] INFO: Connected to Dell MariaDB (100.110.222.53)
[2025-11-05 18:30:01] INFO: Retrieved 4 domains from DB: kuma8088.com, m8088.com, webmakesprofit.com, fx-trader-life.com
[2025-11-05 18:30:01] INFO: Current relay_domains: kuma8088.com, m8088.com, webmakesprofit.com
[2025-11-05 18:30:01] INFO: Domain changes detected: +1, -0
[2025-11-05 18:30:01] INFO: Added domain: fx-trader-life.com
[2025-11-05 18:30:02] INFO: Backup created: /opt/mailserver/backup/relay_domains.20251105-183002.bak
[2025-11-05 18:30:02] INFO: Updated relay_domains: kuma8088.com, m8088.com, webmakesprofit.com, fx-trader-life.com
[2025-11-05 18:30:02] INFO: Updated transport file: added 1 entry
[2025-11-05 18:30:02] INFO: Postmap successful: /etc/postfix/transport.db
[2025-11-05 18:30:03] INFO: Postfix reloaded successfully
[2025-11-05 18:30:03] INFO: ===== Sync completed in 3 seconds =====
```

#### **変更なし**
```
[2025-11-05 18:35:00] INFO: ===== Relay Domains Sync Started =====
[2025-11-05 18:35:01] INFO: Connected to Dell MariaDB (100.110.222.53)
[2025-11-05 18:35:01] INFO: Retrieved 4 domains from DB: kuma8088.com, m8088.com, webmakesprofit.com, fx-trader-life.com
[2025-11-05 18:35:01] INFO: Current relay_domains: kuma8088.com, m8088.com, webmakesprofit.com, fx-trader-life.com
[2025-11-05 18:35:01] INFO: No changes detected, skipping update
[2025-11-05 18:35:01] INFO: ===== Sync completed in 1 seconds =====
```

#### **エラー発生**
```
[2025-11-05 18:40:00] INFO: ===== Relay Domains Sync Started =====
[2025-11-05 18:40:01] ERROR: Failed to connect to MariaDB: Connection timeout (100.110.222.53:3306)
[2025-11-05 18:40:01] ERROR: MySQL Error: ERROR 2003 (HY000): Can't connect to MySQL server
[2025-11-05 18:40:01] INFO: Keeping current configuration
[2025-11-05 18:40:01] INFO: ===== Sync failed in 1 seconds =====
```

```
[2025-11-05 18:45:00] INFO: ===== Relay Domains Sync Started =====
[2025-11-05 18:45:01] INFO: Connected to Dell MariaDB (100.110.222.53)
[2025-11-05 18:45:01] INFO: Retrieved 5 domains from DB: ...
[2025-11-05 18:45:02] INFO: Updated relay_domains: ...
[2025-11-05 18:45:02] INFO: Updated transport file
[2025-11-05 18:45:02] INFO: Postmap successful
[2025-11-05 18:45:03] ERROR: Postfix reload failed: exit code 1
[2025-11-05 18:45:03] ERROR: Postfix output: postfix: fatal: ...
[2025-11-05 18:45:04] INFO: Rolling back to previous configuration
[2025-11-05 18:45:05] INFO: Rollback successful
[2025-11-05 18:45:05] ERROR: CRITICAL: Manual intervention required
[2025-11-05 18:45:05] INFO: ===== Sync failed in 5 seconds =====
```

### **ログローテーション**

```
/var/log/mailserver/relay-sync.log {
    daily
    rotate 30
    compress
    delaycompress
    missingok
    notifempty
    create 0640 root root
}
```

---

## ✅ **8. テスト要件**

### **単体テスト**

| テストID | テスト項目 | 手順 | 期待結果 |
|----------|-----------|------|----------|
| UT-001 | DB 接続成功 | 正常な DB 接続情報で実行 | 接続成功、ドメインリスト取得 |
| UT-002 | DB 接続失敗 | 誤った IP で実行 | エラーログ、現状維持 |
| UT-003 | DB クエリ失敗 | 存在しないテーブルを指定 | エラーログ、現状維持 |
| UT-004 | ドメイン追加 | DB に新規ドメイン追加 | relay_domains に反映 |
| UT-005 | ドメイン削除 | DB からドメイン削除（無効化） | relay_domains から削除 |
| UT-006 | 変更なし | DB に変更なし | 早期リターン、ログ出力 |
| UT-007 | transport 更新 | 新規ドメイン追加 | transport に正しく記載 |
| UT-008 | postmap 実行 | transport 更新後に実行 | .db ファイル生成 |
| UT-009 | postfix reload 成功 | 正常な設定で reload | exit code 0 |
| UT-010 | postfix reload 失敗 | 誤った設定で reload | ロールバック実行 |
| UT-011 | ロールバック | 意図的に失敗させる | バックアップから復元 |
| UT-012 | バックアップ作成 | 設定変更前 | バックアップファイル作成 |

### **結合テスト**

| テストID | テスト項目 | 手順 | 期待結果 |
|----------|-----------|------|----------|
| IT-001 | Dell → EC2 同期（追加） | Dell で新規ドメイン追加 → 5分待機 | EC2 relay_domains に反映 |
| IT-002 | Dell → EC2 同期（削除） | Dell でドメイン無効化 → 5分待機 | EC2 から削除 |
| IT-003 | Dell → EC2 同期（複数変更） | Dell で 3ドメイン追加・2削除 → 5分待機 | すべて正しく反映 |
| IT-004 | DB 停止時の動作 | Dell MariaDB 停止 → cron 実行 | エラーログ、設定維持 |
| IT-005 | Tailscale 切断時 | VPN 切断 → cron 実行 | エラーログ、設定維持 |
| IT-006 | 起動時実行 | EC2 再起動 | 30秒後にスクリプト実行 |

### **運用テスト**

| テストID | テスト項目 | 手順 | 期待結果 |
|----------|-----------|------|----------|
| OT-001 | エンドツーエンド | Dell でドメイン追加 → Gmail から送信 | Dell で受信確認 |
| OT-002 | Postfix reload 中の受信 | reload 中にメール受信 | 受信成功（既存接続維持） |
| OT-003 | ログローテーション | 30日経過後 | 古いログ削除、圧縮 |
| OT-004 | 大量ドメイン | 100ドメイン同期 | 10秒以内に完了 |
| OT-005 | 長時間運用 | 1週間連続動作 | エラーなし、メモリリークなし |

---

## 🔧 **9. 運用要件**

### **監視**

| 監視項目 | 監視方法 | アラート条件 | 対応 |
|---------|---------|-------------|------|
| スクリプト実行失敗 | journalctl / CloudWatch Logs | exit code != 0 | 調査・手動対応 |
| Postfix reload 失敗 | ログファイル監視 | "CRITICAL" 文字列 | **即座に対応** |
| ログファイル肥大化 | ディスク使用量監視 | > 1GB | ログローテーション確認 |
| DB 接続失敗 | ログファイル監視 | 連続 3 回失敗 | Tailscale/DB 状態確認 |

### **アラート送信**

**重大エラー時**:
- Postfix reload 失敗
- 連続 5 回スクリプト実行失敗

**送信方法**:
- AWS SNS (推奨)
- メール送信（Dell Postfix 経由）

### **バックアップ**

| 対象 | 頻度 | 保持期間 | 保存先 |
|------|------|---------|--------|
| 設定ファイル（relay-sync.conf） | 日次 | 30日 | S3 |
| ロールバック用バックアップ | 更新時 | 5世代 | ローカル |
| ログファイル | 日次 | 30日 | ローカル（圧縮） |

### **メンテナンス**

| 作業 | 頻度 | 内容 |
|------|------|------|
| ログファイル削除 | 自動（日次） | 30日以上前のログを削除 |
| DB パスワード変更 | 手動（90日ごと） | relay_sync ユーザーのパスワード変更 |
| スクリプト更新 | 必要時 | バージョン管理（Git） |
| 動作確認 | 手動（月次） | テストメール送信・受信確認 |

---

## 📝 **10. 制約事項**

- Dell MariaDB が停止中は同期不可（エラーログのみ、次回リトライ）
- 最大 5 分の遅延が発生（リアルタイム反映ではない）
- Tailscale VPN が切断中は同期不可
- EC2 再起動時は起動後 30 秒待機してから初回実行
- ドメイン数が 100 件を超える場合、性能劣化の可能性
- transport ファイルは完全上書き（手動追加行は削除される）

---

## ✅ **11. 前提条件**

- Dell と EC2 が Tailscale VPN で接続済み
- Dell MariaDB に `relay_sync` ユーザーが作成済み（`SELECT` 権限）
- EC2 に Docker と Postfix コンテナが稼働中
- EC2 から Dell MariaDB (100.110.222.53:3306) に接続可能
- EC2 に `/opt/mailserver/` ディレクトリが存在
- cron が正常に動作

---

## 📅 **12. 実装スケジュール**

| フェーズ | 作業 | 担当 | 期間 | 成果物 |
|---------|------|------|------|--------|
| **Phase 1** | 要件定義 | Claude | 完了 | 本ドキュメント |
| **Phase 2** | Dell DB ユーザー作成 | 管理者 | 30分 | `relay_sync` ユーザー |
| **Phase 3** | スクリプト実装 | Claude | 2時間 | `sync-relay-domains.sh` |
| **Phase 4** | 単体テスト | 管理者 | 1時間 | テスト結果 |
| **Phase 5** | 結合テスト | 管理者 | 1時間 | テスト結果 |
| **Phase 6** | 本番デプロイ | 管理者 | 30分 | cron 設定 |
| **Phase 7** | 運用テスト | 管理者 | 1週間 | 動作確認 |

---

## 🎯 **13. 成功基準**

- [ ] Dell 管理画面でドメイン追加後、5分以内に EC2 に反映
- [ ] Gmail から新規ドメインへのメール送信が成功
- [ ] DB 接続失敗時もメール受信は継続（既存ドメイン）
- [ ] 1週間連続動作でエラー発生なし
- [ ] ログに必要な情報がすべて記録される
- [ ] Postfix reload 失敗時に正常にロールバック

---

## 🚀 **14. 実装優先度**

| 項目 | 優先度 | 理由 |
|------|--------|------|
| DB 接続・ドメイン取得 | **P0** | コア機能 |
| relay_domains 更新 | **P0** | コア機能 |
| transport 更新 | **P0** | コア機能 |
| エラーハンドリング | **P1** | 安定性 |
| ロギング | **P1** | 運用性 |
| ロールバック機能 | **P2** | 障害対応 |
| 監視・アラート | **P2** | 運用性 |
| AWS Secrets Manager 統合 | **P3** | セキュリティ強化（将来対応） |

---

## 📚 **15. 参考資料**

- [Postfix Configuration Parameters](http://www.postfix.org/postconf.5.html)
- [Postfix Transport Table](http://www.postfix.org/transport.5.html)
- [Tailscale Documentation](https://tailscale.com/kb/)
- [MariaDB GRANT Statement](https://mariadb.com/kb/en/grant/)

---

## 📝 **変更履歴**

| バージョン | 日付 | 変更内容 | 変更者 |
|-----------|------|---------|--------|
| 1.0 | 2025-11-05 | 初版作成 | Claude |

---

## ✍️ **承認**

| 役割 | 氏名 | 承認日 | 署名 |
|------|------|--------|------|
| 要件定義者 | Claude | 2025-11-05 | - |
| レビュアー | - | - | - |
| 承認者 | - | - | - |

---

**END OF DOCUMENT**
