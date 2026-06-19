#!/usr/bin/env bash
# mt5-forward — 軽量監視（O.Q.6）: コンテナ生存 / broker切断 / EA detach / outage 取りこぼし
# 設計: docs/application/mt5-forward/operations.md §2
#
# systemd timer（例: 5分間隔）で実行。異常を検知したら既存のメール/SNS 経路へ通知（新監視基盤は作らない）。
# 引数: トラックのコンテナ名（省略時 mt5-tentei-himo）
#
# ⚠️ 未テスト雛形: 通知関数 notify() は環境の通知経路に合わせて実装すること（初版はログ + メール1通で十分）。
set -euo pipefail

CONTAINER="${1:-mt5-tentei-himo}"
DATA_DIR="/opt/onprem-infra-system/project-root-infra/services/mt5-forward/data/${CONTAINER#mt5-}"
STALE_MIN="${STALE_MIN:-30}"   # CSV/ログが何分無更新なら detach 疑いとするか

notify() { echo "[health-watch][ALERT] $*" >&2; }   # TODO: メール/SNS 経路に接続（operations.md §2.2）

# (1) コンテナ生存 / health
state="$(docker inspect --format '{{.State.Status}}' "$CONTAINER" 2>/dev/null || echo missing)"
health="$(docker inspect --format '{{if .State.Health}}{{.State.Health.Status}}{{else}}none{{end}}' "$CONTAINER" 2>/dev/null || echo missing)"
[ "$state" = "running" ] || notify "$CONTAINER が running でない (state=$state)"
[ "$health" = "unhealthy" ] && notify "$CONTAINER が unhealthy"

# (2) broker 切断（端末/EAログの切断メッセージ）
if [ -d "$DATA_DIR/Logs" ]; then
  if grep -rqiE 'disconnect|no connection|connection lost' "$DATA_DIR/Logs/" 2>/dev/null; then
    notify "$CONTAINER: broker 切断メッセージを検出（Logs 確認）"
  fi
  # (4) outage 取りこぼし（EA v0.6 が記録する MISSED_OUTAGE / GAP_FILL）
  if grep -rqE 'MISSED_OUTAGE' "$DATA_DIR/Logs/" 2>/dev/null; then
    notify "$CONTAINER: MISSED_OUTAGE 検出（取りこぼしの可能性 → 投資部門へ）"
  fi
fi

# (3) EA detach 疑い: 取引CSV/ログが一定時間無更新
newest="$(find "$DATA_DIR" -type f \( -name '*.csv' -o -name '*.log' \) -mmin "-$STALE_MIN" 2>/dev/null | head -1 || true)"
if [ -d "$DATA_DIR" ] && [ -z "$newest" ]; then
  notify "$CONTAINER: 直近 ${STALE_MIN}分 CSV/ログ無更新（EA detach 疑い。:300x で AutoTrading 確認）"
fi

echo "[health-watch] $CONTAINER チェック完了 (state=$state health=$health)"
