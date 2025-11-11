# データベースエクスポート準備状況

## ✅ 完了事項

### 1. 認証情報ファイル作成
- **ファイル**: `docs/application/blog/claudedocs/xserver-credentials-export.env`
- **形式**: slug-based変数名（マニュアル要件に準拠）
- **パスワード取得済み**: 10サイト

### 2. エクスポートスクリプト作成
- **ファイル**: `/tmp/export-xserver-databases.sh`
- **機能**: 10サイト分のmysqldump + 圧縮 + scp転送
- **状態**: 実行可能（chmod +x済み）

### 3. site-map.csv整備
- **ファイル**: `docs/application/blog/claudedocs/site-map.csv`
- **内容**: 15サイト全てのマッピング情報
- **カラム**: xserver_db_name追加済み

## ⚠️ 未完了事項（実行前に必要）

### 1. XSERVER_DB_HOST設定
**現在**: `mysql***.xserver.jp`（プレースホルダー）

**取得方法**:
1. Xserver サーバーパネルにログイン
2. MySQL設定 → MySQLホスト名を確認
3. `xserver-credentials-export.env`の9行目を編集:
   ```bash
   export XSERVER_DB_HOST="mysql1234.xserver.jp"  # 実際の値に置き換え
   ```

### 2. kuma8088 test sites（6サイト）のパスワード

**対象サイト**:
- kuma8088-elementordemo1 (gwpbk492_el1)
- kuma8088-elementordemo02 (gwpbk492_el2)
- kuma8088-elementor-demo-03 (gwpbk492_el3)
- kuma8088-elementor-demo-04 (gwpbk492_el4)
- kuma8088-ec02test (gwpbk492_ec2)
- kuma8088-cameramanual-gwpbk492 (gwpbk492_ct1)

**取得方法**:
1. Xserver サーバーパネル → MySQL設定
2. 各データベースユーザーのパスワード確認/リセット
3. `xserver-credentials-export.env`の該当行を編集（現在は `********`）

**注**: これらはtestサイトのため、本番移行には不要な可能性あり

## 📋 認証情報マッピング（現在の状態）

### ✅ パスワード取得済み（10サイト）

| slug | Xserver DB名 | DB User | パスワード |
|------|-------------|---------|----------|
| fx-trader-life | gwpbk492_wp3 | gwpbk492_wp2 | ✅ |
| webmakeprofit | gwpbk492_wt4 | gwpbk492_wt4 | ✅ |
| webmakesprofit | gwpbk492_wt5 | gwpbk492_wt5 | ✅ |
| toyota-phv | gwpbk492_wt6 | gwpbk492_wt6 | ✅ |
| kuma8088-cameramanual | gwpbk492_wp1 | gwpbk492_wp1 | ✅ |
| fx-trader-life-mfkc | gwpbk492_th6h6 | gwpbk492_th6h6 | ✅ |
| fx-trader-life-4line | gwpbk492_c73vs | gwpbk492_c73vs | ✅ |
| fx-trader-life-lp | gwpbk492_a2gfg | gwpbk492_a2gfg | ✅ |
| webmakeprofit-coconala | gwpbk492_we38z | gwpbk492_we38z | ✅ |
| unknown-p3ca6 | gwpbk492_socwr | gwpbk492_socwr | ✅ |

### ❌ パスワード未設定（6サイト）

| slug | Xserver DB名 | DB User | パスワード |
|------|-------------|---------|----------|
| kuma8088-elementordemo1 | gwpbk492_el1 | gwpbk492_el1 | ❌ |
| kuma8088-elementordemo02 | gwpbk492_el2 | gwpbk492_el2 | ❌ |
| kuma8088-elementor-demo-03 | gwpbk492_el3 | gwpbk492_el3 | ❌ |
| kuma8088-elementor-demo-04 | gwpbk492_el4 | gwpbk492_el4 | ❌ |
| kuma8088-ec02test | gwpbk492_ec2 | gwpbk492_ec2 | ❌ |
| kuma8088-cameramanual-gwpbk492 | gwpbk492_ct1 | gwpbk492_ct1 | ❌ |

## 🚀 実行手順

### パターンA: 10サイトのみエクスポート（testサイト除外）

```bash
# 1. XSERVER_DB_HOSTを設定（必須）
vi /opt/onprem-infra-system/project-root-infra/docs/application/blog/claudedocs/xserver-credentials-export.env

# 2. SSH Agentを起動（必須）
eval "$(ssh-agent -s)"
ssh-add ~/.ssh/xserver-dell.key

# 3. エクスポート実行
/tmp/export-xserver-databases.sh

# 結果: 成功10サイト、スキップ6サイト（testサイト）
```

### パターンB: 全16サイトエクスポート（testサイト含む）

```bash
# 1. XSERVER_DB_HOSTを設定（必須）
vi /opt/onprem-infra-system/project-root-infra/docs/application/blog/claudedocs/xserver-credentials-export.env

# 2. kuma8088 test sitesのパスワードを追加
# 行41-56の ******** を実際のパスワードに置き換え

# 3. スクリプトに6サイト分のエクスポートコードを追加（要修正）

# 4. SSH Agentを起動
eval "$(ssh-agent -s)"
ssh-add ~/.ssh/xserver-dell.key

# 5. エクスポート実行
/tmp/export-xserver-databases.sh

# 結果: 成功16サイト、スキップ0サイト
```

## 📁 出力先

- **ダンプファイル**: `/tmp/xserver-dumps/*.sql.gz`
- **ファイル名形式**: `gwpbk492_wp3.sql.gz`（Xserver DB名ベース）

## 🔍 トラブルシューティング

### エラー: "XSERVER_DB_HOSTが設定されていません"
→ xserver-credentials-export.envの9行目を実際のMySQLホスト名に変更

### エラー: "SSH Agent not running"
→ `eval "$(ssh-agent -s)"` と `ssh-add ~/.ssh/xserver-dell.key` を実行

### エラー: "Access denied for user 'gwpbk492_wp2'"
→ パスワードが間違っている可能性。Xserver管理画面で再確認

## 次のステップ（Phase A-1 続き）

1. ✅ **3-1. DB一括エクスポート** ← 現在ここ（準備完了、実行待ち）
2. ⏳ 3-2. Dell MariaDBへインポート
3. ⏳ 4. wp-config.php修正
4. ⏳ 5. URL置換（domain → blog.domain）
5. ⏳ 6. Cloudflare Tunnel設定
