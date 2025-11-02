#!/bin/bash
# /opt/onprem-infra-system/project-root-infra/scripts/load_tailscale_key.sh
# 安全に Tailscale Auth Key を読み込むスクリプト

set -e

echo "🔐 Tailscale Auth Key を含むファイルを用意してください"
echo "例: /tmp/ts_auth.key (パーミッション 600)"
read -p "Auth Key ファイルパス: " TS_KEY_FILE

# ファイル存在チェック
if [ ! -f "$TS_KEY_FILE" ]; then
  echo "❌ ファイルが存在しません: $TS_KEY_FILE"
  exit 1
fi

# ファイルから読み込み
export TS_AUTHKEY=$(cat "$TS_KEY_FILE")
echo "✅ Auth Key 読み込み完了 (環境変数 TS_AUTHKEY に格納済み)"

# 即座にファイル削除
rm -f "$TS_KEY_FILE"
echo "🧹 一時ファイル削除済み"

# シェル履歴削除（現在のセッション分）
history -d $((HISTCMD-1)) 2>/dev/null || true

echo "🔒 セキュリティ保護: 履歴から削除済み"
echo " "
echo "👉 次のコマンドで確認:"
echo "   echo \$TS_AUTHKEY | sed 's/./*/g'"