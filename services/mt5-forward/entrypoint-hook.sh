#!/usr/bin/env bash
# mt5-forward — EA配置 + CSV/ログ配線の初期化フック
# 設計: docs/application/mt5-forward/deployment.md §2.1
#
# 役割（MT5 起動前に1回実行）:
#   (1) /artifacts(ro) の凍結 .ex5 を MT5 の MQL5/Experts・Indicators へ反映（MT-007）
#   (2) MQL5/Files・MQL5/Logs を /output(=host data/<track>/) へ symlink で逃がす（MT-004/009）
#
# ⚠️ 未テスト雛形:
#   - Wine が Files/Logs の symlink を追従するかは実装時に要検証（deployment.md §2.1 の注記）。
#     追従しない場合は「実ディレクトリ + 定期 rsync で /output へ反映」へフォールバック。
#   - インジ(Signals)と EA の振り分けは命名規約で判別（実装時に確定）。
set -euo pipefail

MQL5="/config/.wine/drive_c/Program Files/MetaTrader 5/MQL5"
mkdir -p "$MQL5/Experts" "$MQL5/Indicators"
mkdir -p /output/Logs

# (1) EA/インジ反映: Signals* はインジ、それ以外の .ex5 は Expert として配置
if compgen -G "/artifacts/*.ex5" > /dev/null; then
  for f in /artifacts/*.ex5; do
    base="$(basename "$f")"
    case "$base" in
      *Signals*|*Indicator*) cp -f "$f" "$MQL5/Indicators/" ;;
      *)                      cp -f "$f" "$MQL5/Experts/" ;;
    esac
  done
fi

# (2) CSV/ログ配線: EA は MQL5/Files/ に書く → /output 側へ逃がす
ln -sfn /output      "$MQL5/Files"
ln -sfn /output/Logs "$MQL5/Logs"

echo "[mt5-forward] entrypoint-hook 完了: EA配置 + Files/Logs → /output 配線"
