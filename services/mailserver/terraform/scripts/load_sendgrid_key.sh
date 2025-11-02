#!/usr/bin/env bash
set -euo pipefail

# 安全に SendGrid API Key を読み込むスクリプト
# - 対話シェルで実行することを想定 (history 操作のため)
# - 一時ファイルは事前に作成してパーミッションを 600 にすること

echo "🔐 SendGrid API Key を含むファイルを用意してください"
echo "例: /tmp/sendgrid_api.key (パーミッション 600)"
read -p "API Key ファイルパス: " SG_KEY_FILE

# ファイル存在チェック + パーミッション確認（オプション）
if [ ! -f "$SG_KEY_FILE" ]; then
  echo "❌ ファイルが存在しません: $SG_KEY_FILE" >&2
  exit 1
fi

# 所有者/パーミッションが適切か軽く確認（警告のみ）
perm=$(stat -c '%a' "$SG_KEY_FILE" 2>/dev/null || stat -f '%Lp' "$SG_KEY_FILE" 2>/dev/null || echo "000")
if [ "$perm" != "600" ]; then
  echo "⚠️ 推奨: 一時ファイルのパーミッションは 600 にしてください (現在: $perm)"
fi

# ファイルから読み込み（改行を取り除く）
SENDGRID_API_KEY=$(tr -d '\r\n' < "$SG_KEY_FILE")

# 必要ならここで追加検証（長さ・prefixなど）
if [ -z "${SENDGRID_API_KEY}" ]; then
  echo "❌ 読み込んだ API キーが空です" >&2
  exit 1
fi

# 一時ファイルを直ちに削除
rm -f "$SG_KEY_FILE"
echo "🧹 一時ファイル削除済み"

# 履歴からの削除（対話シェルでのみ有効）
# HISTCMD が存在する（bash interactive）なら直近の入力を削除
if [ -n "${HISTCMD-}" ]; then
  # 最近の3行を削除（read/echo 等の履歴行を想定）
  history -d $((HISTCMD-3)) 2>/dev/null || true
  history -d $((HISTCMD-2)) 2>/dev/null || true
  history -d $((HISTCMD-1)) 2>/dev/null || true
fi

# 環境変数にエクスポート（現在のシェルセッションにのみ有効）
export SENDGRID_API_KEY
echo "✅ SendGrid API Key を環境変数 SENDGRID_API_KEY に格納しました（セッション限定）"

# セキュリティのため中身は表示しないが「存在確認」はマスクで行う例を表示
echo ""
echo "確認 (中身は伏せます):"
echo '  echo $SENDGRID_API_KEY | sed '\''s/./*/g'\'''
echo ""
echo "必要ならこの値を AWS Secrets Manager 等に保存するコマンドを実行できます（下記参照）"
echo "例（AWS CLI が設定済みの場合）:"
echo "  aws secretsmanager create-secret --name mailserver/sendgrid/api-key --secret-string \"\$SENDGRID_API_KEY\" --description \"SendGrid API Key for mailserver\""