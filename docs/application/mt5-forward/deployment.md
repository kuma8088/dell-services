# デプロイ設計 - mt5-forward (deployment)

**対象**: Dell ワークステーション (Rocky Linux 9.6)
**作成日**: 2026-06-18
**ステータス**: 設計（レビュー待ち・実装前）
**前提**: [architecture.md](./architecture.md) の構成判断

> 本書は「どう構築・起動するか」の設計。コードブロックは**実装時の雛形**であり、
> 承認後に `services/mt5-forward/` へ実ファイルとして作成する。
> インフラ変更の鉄則に従い、適用は **テスト（単一トラック）→ 確認 → 本番常駐** の順で行う。

---

## 1. ディレクトリ構成（実装時に作成）

```
services/mt5-forward/
├─ docker-compose.yml          # トラックを YAML anchor で定義
├─ Dockerfile                  # gmag11/metatrader5_vnc:1.1 ベースの薄いラッパ
├─ .gitignore                  # 既存（.env*/config/*.ini/data/*.ex5/tracks/*.env 等を除外）
├─ README.md                   # サービス概要（実装時に追記）
├─ tracks/
│   └─ tentei-himo.env         # 初版トラック定義（gitignore）
├─ secrets/
│   └─ titanfx_demo1_password  # broker master パスワード（gitignore, 0600）
├─ artifacts/
│   └─ tentei-himo/            # 凍結 .ex5 / .tpl（gitignore）
│       ├─ TenteiHimo_Live.ex5
│       ├─ TenteiHimo_Signals.ex5
│       └─ usdjpy_m5.tpl
├─ data/
│   └─ tentei-himo/            # 取引CSV/Logs（gitignore, 還流元）
└─ scripts/
    ├─ sync-results.sh         # data/<track> を git commit/push
    ├─ health-watch.sh         # broker切断 / EA detach 検知
    └─ new-track.sh            # トラック追加ウィザード（MT-008）
```

> **重要（critical-rules §6 ファイル安全）**: 上記は新規パスへの作成のみ。既存ファイルの上書きは行わない。

---

## 2. Dockerfile（雛形・薄いラッパ）

```dockerfile
# MQL5専用・軽量版をベース（約600MB, Python不要）
FROM gmag11/metatrader5_vnc:1.1

# タイムゾーン UTC 固定（NF-005: ロールオーバー/週末フラット判定が時刻依存）
ENV TZ=UTC

# EA/インジ/テンプレは volume(ro) でマウントするため COPY しない（MT-007: 再ビルド不要差し替え）
# 起動時に /artifacts の .ex5 を MT5 の MQL5/Experts・Indicators へ反映する初期化フックのみ追加
COPY entrypoint-hook.sh /opt/mt5-forward/entrypoint-hook.sh
RUN chmod +x /opt/mt5-forward/entrypoint-hook.sh

# ベースイメージの起動シーケンスを尊重しつつ、フックでEA配置→自動アタッチを行う
# （ベースの supervisord/s6 起動を壊さないよう、フックは init スクリプトとして登録する）
```

> ベースイメージの起動方式（KasmVNC + Wine 起動）を壊さないことが最優先。
> entrypoint を完全置換せず、**ベースの拡張ポイント（init.d 相当）にフックを足す**方針。
> 具体的な拡張ポイントはベースイメージの README/構造を実装時に確認して合わせる（推測で上書きしない）。

### 2.1 EA配置と CSV/ログ出力の配線（entrypoint-hook.sh の責務, MT-004/007）

Wine 配下の MT5 実体パスは `/config/.wine/drive_c/Program Files/MetaTrader 5/MQL5/`（`/config` 永続化）。
EAの入出力を host の `artifacts/`・`data/` に橋渡しするのがフックの役割。`entrypoint-hook.sh` は
**MT5 起動前に1回**実行し、以下を行う:

```bash
#!/usr/bin/env bash
set -euo pipefail
MQL5="/config/.wine/drive_c/Program Files/MetaTrader 5/MQL5"
mkdir -p "$MQL5/Experts" "$MQL5/Indicators" "$MQL5/Files" "$MQL5/Logs"

# (1) EA/インジ反映: /artifacts(ro) の凍結 .ex5 を MT5 配下へコピー（差し替えは再ビルド不要, MT-007）
cp -f /artifacts/*.ex5 "$MQL5/Experts/"      2>/dev/null || true
# ※ Signals 等インジは Indicators/ へ振り分け（命名規約 or サブフォルダで判別。実装時に確定）

# (2) CSV/ログを host data/<track>(=/output) に出す配線（MT-004/009）:
#     EA は MQL5/Files/ 配下に書くため、Files/ と Logs/ の実体を /output 側に向ける（bind mount は
#     /config 永続化と二重マウントになり扱いづらいので、symlink で /output に逃がす方式を採用）
ln -sfn /output            "$MQL5/Files"     # himo_live_trades.csv → /output/ 直下に出力
ln -sfn /output/Logs       "$MQL5/Logs"      # Experts ログ → /output/Logs/
mkdir -p /output/Logs
```

> ⚠️ 実装時に要検証: ① MT5(Wine) が `Files`/`Logs` の symlink を正しく追従するか（Wine の挙動依存。
> 追従しない場合は MT5 標準の「`MQL5/Files` 実ディレクトリ → 起動後に rsync で /output へ反映する
> サイドカー or 定期コピー」にフォールバック）。② EA の CSV 出力先がカスタムパスを取る入力を持つなら、
> `tracks/*.env` の `OUTPUT_DIR` で直接 `/output` を指す方が確実。EA の `.mq5` 仕様（投資部門）を確認のうえ確定する。

---

## 3. MT5 自動起動・EA自動アタッチの永続化（O.Q.5）

**方針**: 「初回だけ人手でセットアップ → `/config` に焼き付け → 以降は無人復元」。

| ステップ | 内容 |
|---------|------|
| 1. 初回起動 | コンテナ起動 → ブラウザ(:3001)で MT5 にデモ口座 master ログイン |
| 2. EA配置 | `/artifacts/*.ex5` を MQL5/Experts・Indicators に反映（フックが自動 or 手動コピー） |
| 3. チャート構成 | USDJPY M5 を開き、`TenteiHimo_Live` EA（AutoTrading ON, InpRiskPct=1.0）と `Signals` インジを適用 |
| 4. プロファイル保存 | この状態を MT5 プロファイル＋テンプレ(`.tpl`)として保存 → `/config` に永続化 |
| 5. 永続化確認 | コンテナ再起動 → 同チャート・EA・AutoTrading が**無人で**復元されることを確認（受け入れ基準） |

> MT5 は「終了時に開いていたチャート/プロファイルを次回起動時に自動復元」する。`/config` が
> volume 永続化されていれば、ステップ4の状態が再起動後も保持される。AutoTrading は端末オプション
> 「起動時に自動売買を許可」を有効化して固定する。

---

## 4. docker-compose.yml（雛形・トラックテンプレ MT-008）

```yaml
# mt5-forward — MT5 フォワード常駐ホスト
# Network: 172.23.0.0/24 (実測の使用中サブネット 172.17-20/22 と非衝突。172.21/23 は空き)
networks:
  mt5_network:
    driver: bridge
    ipam:
      config:
        - subnet: 172.23.0.0/24
          gateway: 172.23.0.1

secrets:
  titanfx_demo1_password:
    file: ./secrets/titanfx_demo1_password

# 全トラック共通定義（差分のみ各サービスで上書き）
x-track-base: &track-base
  build: .
  image: mt5-forward:local
  restart: always                 # MT-001: 再起動後 自動復帰
  networks: [mt5_network]
  deploy:                          # NF-003
    resources:
      limits:   { cpus: '2.0', memory: 2G }
      reservations: { cpus: '1.0', memory: 1G }
  logging:                         # NF-004
    driver: json-file
    options: { max-size: "10m", max-file: "3" }
  healthcheck:                     # 監視（軽量）
    test: ["CMD-SHELL", "pgrep -f terminal64.exe || exit 1"]
    interval: 60s
    timeout: 10s
    retries: 3
    start_period: 360s             # MT5 初回インストール~5分を考慮し 6分確保（初回中の誤unhealthy回避）

services:
  mt5-tentei-himo:
    <<: *track-base
    container_name: mt5-tentei-himo
    env_file: ./tracks/tentei-himo.env
    ports:
      - "127.0.0.1:3001:3000"      # localhost束縛のみ。Tailnet公開は host の `tailscale serve`（§7.1）で行う
    volumes:
      - ./tracks/tentei-himo/config:/config
      - ./artifacts/tentei-himo:/artifacts:ro
      - ./data/tentei-himo:/output
    secrets: [titanfx_demo1_password]

  # === 追加トラックはこのブロックを複製し env/port/volume/secret を差し替えるだけ ===
  # mt5-<track2>:
  #   <<: *track-base
  #   container_name: mt5-<track2>
  #   env_file: ./tracks/<track2>.env
  #   ports: ["127.0.0.1:3002:3000"]
  #   volumes: [...]
  #   secrets: [titanfx_demo2_password]
```

### tracks/tentei-himo.env（雛形・非機密のみ）

```ini
# 非機密のみ。master パスワードは docker secret で注入（NF-002）
# 注: CUSTOM_USER は KasmVNC のブラウザ認証ユーザー名。broker の investor ログイン(§5.3)とは別概念のため
#     紛らわしい "investor" は使わず webui とする
CUSTOM_USER=webui
TRACK_NAME=tentei-himo
MT5_SERVER=TitanFX-Demo
MT5_LOGIN=<デモ口座番号>
SYMBOL=USDJPY
TIMEFRAME=M5
MAGIC=26060801
EA_FILE=TenteiHimo_Live.ex5
INP_RISK_PCT=1.0
```

> `PASSWORD`（KasmVNC のブラウザ認証）と broker master パスワードは別物。前者は secret/env、
> 後者は `titanfx_demo1_password` secret から MT5 ログインへ渡す。混同しない。

---

## 5. シークレット運用（NF-002）

```bash
# secrets ディレクトリは 0700、ファイルは 0600。git管理外（.gitignore済み）
install -d -m 700 services/mt5-forward/secrets
printf '%s' '<TitanFX_master_password>' > services/mt5-forward/secrets/titanfx_demo1_password
chmod 600 services/mt5-forward/secrets/titanfx_demo1_password

# コミット前チェック（受け入れ基準）: 平文パスワード/秘匿ファイルが追跡されていないこと
# 注: 単純な `git grep password` は compose 内の secret 名（titanfx_demo1_password）に
#     必ずマッチして偽陽性になる。検査対象は「秘匿ファイルが git 管理下に入っていないか」。

# (a) 秘匿ファイルが追跡対象に含まれていないこと（含まれていたら NG）
if git ls-files services/mt5-forward/ | grep -E 'secrets/|/tracks/.*\.env$|\.ex5$'; then
  echo "NG: 秘匿ファイルが追跡されている（.gitignore を確認）"; else echo "OK: 秘匿ファイル非追跡"; fi

# (b) 追跡ファイル内に平文パスワード代入が無いこと（secret 名参照は除外）
#     PASSWORD=xxx / password: xxx 形式の“値付き”代入を検出。secret 宣言/参照行は誤検知しない
git grep -nIE '(PASSWORD|password)\s*[:=]\s*\S' -- services/mt5-forward/ \
  | grep -vE 'titanfx_demo[0-9]+_password|secret|<.*>' \
  && echo "NG: 平文パスワードの疑い（上記行を確認）" || echo "OK: 平文パスワード代入なし"
```

---

## 6. デプロイ手順（テスト→本番の段階適用）

```bash
cd /opt/onprem-infra-system/project-root-infra/services/mt5-forward

# 0. 前提: artifacts/tentei-himo に凍結 .ex5 配置、tracks/tentei-himo.env と secret 作成済み

# 1. ビルド
docker compose build

# 2. 単一トラックでテスト起動（フォアグラウンド観察）
docker compose up mt5-tentei-himo        # 初回 MT5 自動インストール ~5分

# 3. Tailnet 公開（127.0.0.1束縛のままだと Tailscale でも到達不可のため必須）
sudo tailscale serve --bg localhost:3001
tailscale serve status                   # 公開URLを確認

# 4. ブラウザ確認: tailscale serve status が示す https://<dell>.<tailnet>.ts.net/ へ Mac から接続
#    → デモ口座 master ログイン → §3 の自動起動セットアップ実施

# 5. 永続化テスト: 再起動して無人復元を確認
docker compose down && docker compose up -d mt5-tentei-himo
#    → チャート/EA/AutoTrading が自動復元されること（tailscale serve --bg は再起動後も持続）

# 6. 本番常駐（restart: always 済み）
docker compose ps
```

---

## 7. 自動起動 / 公開の永続化（Dell 再起動耐性 MT-001 / MT-006）

### 7.1 Tailnet 公開（tailscale serve）

- Docker の `127.0.0.1:300x` 束縛は**公開IPに出さない**だけで、それ単体では Mac から到達できない。
  Tailnet への公開は **`tailscale serve --bg localhost:300x`** で行う（公式確認済み: Tailnet限定。
  公開インターネット向けの `tailscale funnel` は使わない）。
- `--bg` 指定により serve 設定は**ホスト再起動後も持続**する。トラックごとに 3001, 3002… を個別に serve。
- 確認/停止: `tailscale serve status` / 撤去時は該当公開を off。

### 7.2 コンテナ自動復帰

- Docker デーモンは systemd で起動済み（既存サービスと同様）。`restart: always` によりホスト再起動で
  コンテナ自動復帰。
- 既存サービスが compose を systemd unit 化しているかは実装時に確認し、**同じ方式に合わせる**
  （単独方式を新設しない）。未導入なら `restart: always` ＋ Docker の `live-restore` で要件を満たす。

---

## 8. 成績同期ジョブ（MT-005, O.Q.4）— ✅ (a) 成績専用リポ で確定

> **確定（2026-06-20）**: MT-005「成績を Mac の git で読める」の還流方式は **(a) 成績専用リポ** を採用。
> 本リポ（ドキュメント駆動型 IaC リポ）に 15分間隔の取引CSVをコミットすると履歴が肥大・汚染するため、
> 成績は**別 git リポに分離**する。`data/` を本リポの `.gitignore` 除外のまま保ち、成績専用リポへ push する。

採用案と却下案:

| 案 | 内容 | 判定 |
|----|------|------|
| **(a) 成績専用リポ** | `data/<track>/` を**別 git リポ**にし push。本サービスの設計リポは汚さない | ✅ **採用**（最もクリーン・既存「Dellが書く→Macがpull」git運用に整合） |
| (b) 追跡方針変更 | 本リポで `data/**/*.csv`・`Logs/` のみ `.gitignore` 除外解除して追跡 | ❌ 却下（IaCリポに高頻度CSV→履歴汚染・肥大） |
| (c) rsync over Tailscale | git を使わず `rsync` で Mac へ同期 | ❌ 却下（バージョン履歴が残らず、git運用とズレる） |

**残タスク（🟡 起動前）**: 成績専用リポの **URL/認証の払い出し**。確定したら `scripts/sync-results.sh` の
`RESULTS_REPO` に設定する（デプロイ host のデプロイキー or PAT を git 認証に使用）。

`scripts/sync-results.sh`（成績専用リポへの push。`RESULTS_REPO` 未設定なら即時失敗）:

```bash
#!/usr/bin/env bash
set -euo pipefail
# (a) 成績専用リポのローカル clone パス。起動前に clone & 認証設定しておく
RESULTS_REPO="${RESULTS_REPO:?成績専用リポ(O.Q.4=a)のローカルcloneパスを設定すること}"
SRC="/opt/onprem-infra-system/project-root-infra/services/mt5-forward/data"

# data/<track>/ の内容を成績専用リポへ反映（rsync で差分コピー → commit → push）
rsync -a --delete "$SRC/" "$RESULTS_REPO/data/"
cd "$RESULTS_REPO"
git add -A
git diff --cached --quiet || git commit -m "chore(mt5): forward results $(date -u +%FT%TZ)"
git push
```

> 還流リポ未開通の間も成績は **volume 永続化（`data/<track>/`）で保全**され失われない。Mac 還流だけが未開通の状態。

---

## 9. ロールバック

- 問題時は `docker compose down`（建玉の SL/TP は broker サーバー側で有効: NF-006、ポジションは保護）
- `/config`・`data/` は volume 永続化のため compose down で消えない
- イメージ起因の不具合は `gmag11/metatrader5_vnc` の特定タグへ固定して再ビルド（operations.md §バージョン固定）
