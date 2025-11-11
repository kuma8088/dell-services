# データベースエクスポート準備完了

## ✅ 完了事項

### 1. site-map.csv（15サイト）
**ファイル**: `docs/application/blog/claudedocs/site-map.csv`

全15サイトの正しいXserver DB名を設定済み：

| slug | Xserver DB名 | DB User | パスワード |
|------|-------------|---------|----------|
| fx-trader-life | gwpbk492_wp3 | gwpbk492_wp2 | ✅ |
| webmakeprofit | gwpbk492_wt1 | gwpbk492_wt4 | ✅ |
| webmakesprofit | gwpbk492_wt4 | gwpbk492_wt5 | ✅ |
| toyota-phv | gwpbk492_wt5 | gwpbk492_wt6 | ✅ |
| kuma8088-cameramanual | gwpbk492_wp7 | gwpbk492_wp1 | ✅ |
| fx-trader-life-mfkc | gwpbk492_62q47 | gwpbk492_th6h6 | ✅ |
| fx-trader-life-4line | gwpbk492_e1rb6 | gwpbk492_c73vs | ✅ |
| fx-trader-life-lp | gwpbk492_x9a11 | gwpbk492_a2gfg | ✅ |
| webmakeprofit-coconala | gwpbk492_bxb90 | gwpbk492_we38z | ✅ |
| kuma8088-elementordemo1 | gwpbk492_38ogv | gwpbk492_xxuqz | ✅ |
| kuma8088-elementordemo02 | gwpbk492_h2xks | gwpbk492_y717a | ✅ |
| kuma8088-elementor-demo-03 | gwpbk492_rxhlz | gwpbk492_ijim2 | ✅ |
| kuma8088-elementor-demo-04 | gwpbk492_o0vyw | gwpbk492_v8m8y | ✅ |
| kuma8088-ec02test | gwpbk492_koqr9 | gwpbk492_0bqrv | ✅ |
| kuma8088-cameramanual-gwpbk492 | gwpbk492_c51ex | gwpbk492_n489j | ✅ |

### 2. xserver-credentials-export.env
**ファイル**: `docs/application/blog/claudedocs/xserver-credentials-export.env`

全15サイトのMySQL認証情報を設定済み。

### 3. エクスポートスクリプト
**ファイル**: `/tmp/export-all-databases.sh`

CSV駆動の一括エクスポートスクリプト（実行可能）：
- site-map.csvから全サイト自動読み込み
- slug名から環境変数を自動マッピング
- mysqldump → gzip → scp転送を自動化
- 成功/スキップ/エラーのカウント表示

## ⚠️ 実行前に必要な作業（1つのみ）

### XSERVER_DB_HOSTの設定

**現在**: `mysql***.xserver.jp`（プレースホルダー）

**設定方法**:
1. Xserver サーバーパネルにログイン
2. **MySQL設定** → **MySQLホスト名**を確認（例: `mysql1234.xserver.jp`）
3. 以下のコマンドで設定ファイルを編集:
   ```bash
   vi /opt/onprem-infra-system/project-root-infra/docs/application/blog/claudedocs/xserver-credentials-export.env
   ```
4. 9行目を実際のホスト名に変更:
   ```bash
   export XSERVER_DB_HOST="mysql1234.xserver.jp"  # 実際の値に置き換え
   ```

## 🚀 実行手順

### ステップ1: XSERVER_DB_HOSTを設定（必須）

```bash
# Xserver管理画面でMySQLホスト名を確認してから編集
vi /opt/onprem-infra-system/project-root-infra/docs/application/blog/claudedocs/xserver-credentials-export.env
```

### ステップ2: SSH Agentを起動

```bash
eval "$(ssh-agent -s)"
ssh-add ~/.ssh/xserver-dell.key
```

### ステップ3: エクスポート実行

```bash
/tmp/export-all-databases.sh
```

**期待される結果**:
```
=========================================
Xserver データベース一括エクスポート
MySQL Host: mysql1234.xserver.jp
=========================================

==== fx-trader-life (gwpbk492_wp3) ====
✅ SUCCESS: fx-trader-life

==== webmakeprofit (gwpbk492_wt1) ====
✅ SUCCESS: webmakeprofit

... (全15サイト)

=========================================
エクスポート完了
成功: 15サイト
スキップ: 0サイト
エラー: 0サイト
=========================================

ダンプファイル保存先: /tmp/xserver-dumps
-rw-r--r-- 1 system-admin system-admin  8.5M gwpbk492_wp3.sql.gz
-rw-r--r-- 1 system-admin system-admin  95M  gwpbk492_wt1.sql.gz
...
```

## 📁 出力先

- **ダンプファイル**: `/tmp/xserver-dumps/*.sql.gz`
- **ファイル名形式**: `{xserver_db_name}.sql.gz`（例: `gwpbk492_wp3.sql.gz`）

## 🔍 トラブルシューティング

### エラー: "XSERVER_DB_HOSTが設定されていません"
→ xserver-credentials-export.envの9行目を実際のMySQLホスト名に変更

### エラー: "SSH Agent not running"
→ `eval "$(ssh-agent -s)"` と `ssh-add ~/.ssh/xserver-dell.key` を実行

### エラー: "mysqldump失敗（認証エラーの可能性）"
→ パスワードが間違っている可能性。xserver-credentials-export.envを再確認

### エラー: "scp転送失敗"
→ ディスク容量確認: `df -h /tmp`

## 📋 次のステップ（Phase A-1 続き）

1. ✅ **2-3. 一括rsync実行** - 完了（15サイト成功）
2. ✅ **3-1. DB一括エクスポート** - 準備完了（XSERVER_DB_HOST設定のみ）← **現在ここ**
3. ⏳ **3-2. Dell MariaDBへインポート**
4. ⏳ **4. wp-config.php修正**（DB接続情報更新）
5. ⏳ **5. URL置換**（domain → blog.domain）
6. ⏳ **6. Cloudflare Tunnel設定**（5サブドメイン追加）
