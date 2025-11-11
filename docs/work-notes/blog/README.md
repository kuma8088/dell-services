# Xserver調査スクリプト使用手順

このディレクトリには、Xserver環境調査用のスクリプトとテンプレートがあります。

## ⚠️ セキュリティ警告

- **全てのファイルが `.gitignore` で保護済み**
- **実際のパスワードは絶対にGitコミットしないこと**
- **調査完了後は速やかに削除すること**

---

## 📁 ファイル構成

| ファイル | 用途 | Git管理 |
|---------|------|---------|
| `xserver-credentials.env` | 認証情報（環境変数）| ❌ 管理外 |
| `xserver-investigation-template.sh` | 調査スクリプト | ❌ 管理外 |
| `xserver-investigation-results.txt` | 調査結果（実行後生成） | ❌ 管理外 |
| `README.md` | この使用手順 | ✅ 管理対象 |

---

## 🔧 使用手順

### ステップ 1: 認証情報の設定

```bash
# xserver-credentials.env を編集
vi docs/application/blog/claudedocs/xserver-credentials.env

# 以下のプレースホルダーを実際の値に置き換え:
# <Xserver管理画面で確認> → 実際のパスワード
```

**確認すべき情報** (Xserver管理画面):
- MySQL設定 → データベースパスワード（5サイト分）
- SSH設定 → ホスト名、ユーザー名
- アカウント設定 → ポート番号（通常10022）

### ステップ 2: 環境変数の読み込み

```bash
# ローカルPC上で環境変数を読み込み
source docs/application/blog/claudedocs/xserver-credentials.env

# 確認
echo $XSERVER_KUMA8088_DB_USER  # gwpbk492_wt3 が表示されるはず
```

### ステップ 3: Xserverへスクリプト転送

```bash
# スクリプトをXserverへSCP転送
scp -P 10022 \
  docs/application/blog/claudedocs/xserver-investigation-template.sh \
  <xserver-user>@<xserver-host>:~/investigation.sh

# パスワード入力: SSH/FTPパスワード
```

### ステップ 4: Xserverで環境変数を設定

```bash
# Xserver SSH接続
ssh -p 10022 <xserver-user>@<xserver-host>

# 環境変数を手動エクスポート
export XSERVER_KUMA8088_DB_NAME="gwpbk492_wt3"
export XSERVER_KUMA8088_DB_USER="gwpbk492_wt3"
export XSERVER_KUMA8088_DB_PASS="<実際のパスワード>"

export XSERVER_FX_DB_NAME="gwpbk492_wp2"
export XSERVER_FX_DB_USER="gwpbk492_wp2"
export XSERVER_FX_DB_PASS="<実際のパスワード>"

export XSERVER_TOYOTA_DB_NAME="gwpbk492_wt6"
export XSERVER_TOYOTA_DB_USER="gwpbk492_wt6"
export XSERVER_TOYOTA_DB_PASS="<実際のパスワード>"

export XSERVER_WEBMAKEPROFIT_DB_NAME="gwpbk492_wt4"
export XSERVER_WEBMAKEPROFIT_DB_USER="gwpbk492_wt4"
export XSERVER_WEBMAKEPROFIT_DB_PASS="<実際のパスワード>"

export XSERVER_WEBMAKESPROFIT_DB_NAME="gwpbk492_wt5"
export XSERVER_WEBMAKESPROFIT_DB_USER="gwpbk492_wt5"
export XSERVER_WEBMAKESPROFIT_DB_PASS="<実際のパスワード>"
```

### ステップ 5: スクリプト実行

```bash
# Xserver上で実行
bash ~/investigation.sh > ~/xserver-investigation-results.txt

# 実行時間: 約1-2分
# 進捗は画面に表示されます
```

### ステップ 6: 結果ファイルをローカルへダウンロード

```bash
# ローカルPCで実行
scp -P 10022 \
  <xserver-user>@<xserver-host>:~/xserver-investigation-results.txt \
  ~/Downloads/xserver-investigation-results.txt

# 権限設定
chmod 600 ~/Downloads/xserver-investigation-results.txt
```

### ステップ 7: Xserver上の一時ファイル削除

```bash
# Xserver上で実行
shred -u ~/investigation.sh
shred -u ~/xserver-investigation-results.txt

# 環境変数クリア
unset XSERVER_KUMA8088_DB_PASS
unset XSERVER_FX_DB_PASS
unset XSERVER_TOYOTA_DB_PASS
unset XSERVER_WEBMAKEPROFIT_DB_PASS
unset XSERVER_WEBMAKESPROFIT_DB_PASS

# ログアウト
exit
```

### ステップ 8: ローカルPC上の環境変数クリア

```bash
# ローカルPCで実行
unset XSERVER_KUMA8088_DB_PASS
unset XSERVER_FX_DB_PASS
unset XSERVER_TOYOTA_DB_PASS
unset XSERVER_WEBMAKEPROFIT_DB_PASS
unset XSERVER_WEBMAKESPROFIT_DB_PASS
```

---

## 📊 調査結果の内容

`xserver-investigation-results.txt` には以下が含まれます：

- ✅ システム情報（OS、カーネル、ホスト名）
- ✅ PHP/MySQL バージョン
- ✅ WordPress バージョン（5サイト分）
- ⚠️ **データベース接続情報（機密）**
- ✅ データベースサイズ（圧縮後）
- ✅ ディレクトリサイズ
- ⚠️ **.htaccess 内容（セキュリティルール含む）**
- ✅ インストール済みプラグイン
- ✅ インストール済みテーマ

---

## 🔐 セキュリティ対策

### 移行期間中の保管方法

```bash
# 1. 一時保管ディレクトリ作成
mkdir -p ~/Documents/blog-migration-temp
chmod 700 ~/Documents/blog-migration-temp

# 2. 調査結果を移動
mv ~/Downloads/xserver-investigation-results.txt ~/Documents/blog-migration-temp/
chmod 600 ~/Documents/blog-migration-temp/*

# 3. Git管理外であることを確認
git status --ignored | grep xserver-investigation
# → "!!" が表示されればGit管理外（正常）
```

### 移行完了後の削除（Phase F）

```bash
# 完全削除（復元不可）
shred -u ~/Documents/blog-migration-temp/xserver-investigation-results.txt
shred -u docs/application/blog/claudedocs/xserver-credentials.env

# ディレクトリ削除
rm -rf ~/Documents/blog-migration-temp/
```

---

## 🆘 トラブルシューティング

### Q1: 環境変数が設定されていないエラー

```
エラー: 環境変数が設定されていません
実行前に: source xserver-credentials.env
```

**対処**: ステップ2を実行してください。

### Q2: MySQL接続エラー

```
ERROR 1045 (28000): Access denied for user 'gwpbk492_wt3'@'localhost'
```

**対処**: `xserver-credentials.env` のパスワードが正しいか確認してください。

### Q3: SCPでパーミッションエラー

```
Permission denied (publickey,password).
```

**対処**:
1. Xserver管理画面でSSHパスワードを確認
2. ポート番号が10022であることを確認
3. ユーザー名とホスト名が正しいか確認

---

## 📚 参照ドキュメント

- **詳細手順**: [../04_migration.md - Phase A-0 Step 10](../04_migration.md)
- **セキュリティ対策**: [../04_migration.md - Phase A-0-X 問題3](../04_migration.md)
- **移行優先モード**: [../04_migration.md - Phase A-0-Y](../04_migration.md)
- **本番後セキュリティ**: [../04_migration.md - Phase F](../04_migration.md)
