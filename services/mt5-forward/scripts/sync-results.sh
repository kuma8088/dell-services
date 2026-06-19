#!/usr/bin/env bash
# mt5-forward — 成績の Mac 還流（MT-005, O.Q.4 = (a) 成績専用リポ）
# 設計: docs/application/mt5-forward/deployment.md §8
#
# systemd timer（例: 15分間隔）で実行。data/<track>/ を成績専用リポへ rsync→commit→push する。
# RESULTS_REPO（成績専用リポのローカル clone パス）は起動前に clone & git 認証設定しておくこと。
#   例) export RESULTS_REPO=/opt/onprem-infra-system/results-mt5-forward
#
# ⚠️ 未テスト雛形: 成績専用リポの URL/認証（デプロイキー or PAT）払い出し後に有効化する。
set -euo pipefail

RESULTS_REPO="${RESULTS_REPO:?成績専用リポ(O.Q.4=a)のローカルcloneパスを設定すること}"
SRC="/opt/onprem-infra-system/project-root-infra/services/mt5-forward/data"

[ -d "$SRC" ] || { echo "[sync-results] $SRC が無い。先に compose を起動すること"; exit 1; }
[ -d "$RESULTS_REPO/.git" ] || { echo "[sync-results] $RESULTS_REPO は git リポではない"; exit 1; }

# data/<track>/ を成績専用リポへ差分反映
mkdir -p "$RESULTS_REPO/data"
rsync -a --delete "$SRC/" "$RESULTS_REPO/data/"

cd "$RESULTS_REPO"
git add -A
if git diff --cached --quiet; then
  echo "[sync-results] 変更なし"
else
  git commit -m "chore(mt5): forward results $(date -u +%FT%TZ)"
  git push
  echo "[sync-results] push 完了"
fi
