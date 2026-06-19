#!/usr/bin/env bash
# mt5-forward — トラック追加ウィザード（MT-008: 並列検証の水平展開）
# 設計: docs/application/mt5-forward/operations.md §7
#
# 「1検証トラック = 1コンテナ = 1デモ口座」のスケルトンを生成する。
# 生成後の手順（手動）:
#   1. artifacts/<name>/ に凍結 .ex5 を配置
#   2. secrets/titanfx_demo<N>_password を作成（0600）
#   3. tracks/<name>.env を実値で編集（口座番号・サーバー名など。master パスワードは secret 側）
#   4. docker-compose.yml に anchor 差分1ブロック追加（port は未使用の 300N）
#   5. docker compose up -d mt5-<name> → ブラウザ(:300N)で master ログイン → 自動起動セットアップ
set -euo pipefail

NAME="${1:?使い方: new-track.sh <track-name>}"
ROOT="$(cd "$(dirname "$0")/.." && pwd)"

for d in "tracks/$NAME/config" "artifacts/$NAME" "data/$NAME/Logs"; do
  mkdir -p "$ROOT/$d"
  touch "$ROOT/$d/.gitkeep"
done

ENV_FILE="$ROOT/tracks/$NAME.env"
if [ -e "$ENV_FILE" ]; then
  echo "[new-track] $ENV_FILE は既に存在。上書きしない（手動で確認）"
else
  sed "s/^TRACK_NAME=.*/TRACK_NAME=$NAME/" "$ROOT/tracks/tentei-himo.env.example" > "$ENV_FILE"
  echo "[new-track] $ENV_FILE を雛形から生成。口座番号/サーバー名/MAGIC/EA_FILE を編集すること"
fi

echo "[new-track] 生成完了: tracks/$NAME/  artifacts/$NAME/  data/$NAME/"
echo "[new-track] 次: ヘッダコメントの手順 1〜5 を実施（operations.md §7）"
