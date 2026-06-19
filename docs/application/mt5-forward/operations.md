# 運用設計 - mt5-forward (operations)

**対象**: Dell ワークステーション (Rocky Linux 9.6)
**作成日**: 2026-06-18
**ステータス**: 設計（レビュー待ち）
**前提**: [architecture.md](./architecture.md) / [deployment.md](./deployment.md)

> 監視・EA差し替え・成績同期・障害対応・トラック増設の運用手順。検証用途のため
> 「ベストエフォート 24/7」（NF-006）。建玉の SL/TP は broker サーバー側で有効なため、
> Dell 障害時もポジション保護は broker に依存する。

---

## 1. 日常運用コマンド

```bash
cd /opt/onprem-infra-system/project-root-infra/services/mt5-forward

# 稼働確認
docker compose ps
docker stats --no-stream mt5-tentei-himo

# ログ確認（Docker ログを使う。journalctl ではない）
docker compose logs -f mt5-tentei-himo

# EA の取引/イベントログ（host 還流先）
tail -f data/tentei-himo/Logs/*.log
tail -f data/tentei-himo/himo_live_trades.csv

# 再起動
docker compose restart mt5-tentei-himo
```

---

## 2. 監視（O.Q.6 — 軽量方針）

### 2.1 コンテナ生存（compose healthcheck）

- `healthcheck` が `terminal64.exe` プロセスを監視（deployment.md §4）。`unhealthy` で異常検知。
- 確認: `docker inspect --format '{{.State.Health.Status}}' mt5-tentei-himo`

### 2.2 broker 切断 / EA detach 検知（health-watch.sh）

`scripts/health-watch.sh` を systemd timer（例: 5分間隔）で起動し、以下を検知して通知:

| 検知対象 | 判定方法 |
|---------|---------|
| コンテナ down / unhealthy | `docker inspect` の State / Health |
| broker 切断 | EA/端末ログの切断メッセージ（`disconnected` / `no connection`）を grep |
| EA detach（自動売買停止） | 取引ログの更新停止（一定時間 CSV/ログが無更新）＋ AutoTrading 状態 |
| outage 取りこぼし | Experts ログの `MISSED_OUTAGE` / `GAP_FILL` 出現（EA v0.6 が記録） |

- **通知経路**: 新しい監視基盤は作らず、**既存のメール/SNS 経路に寄せる**（mailserver 経由のメール通知 or
  既存 CloudWatch/SNS と同等の軽量通知）。初版は「異常時にローカルログ＋メール1通」で十分。

### 2.3 リソース監視（NF-003 / メモリ増強判断）

- 「現状 NF-003(2G/コンテナ)のまま開始 → 使いながら増強判断」の方針。
- 週次で `docker stats` のピークメモリを記録。トラック増設で host available（実測 ~23GiB）を圧迫し始めたら
  `deploy.resources.limits` を見直す。判断材料は推測でなく実測（`docker stats` / `free -h`）。

---

## 3. EA / インジの差し替え（MT-007）

EA は EdgeVault 投資部門で更新され、凍結 `.ex5` として受け渡される。**再ビルド不要**:

```bash
cd services/mt5-forward
# 1. 新しい凍結 .ex5 を artifacts に配置（投資部門から受領）
cp /path/to/TenteiHimo_Live_v0.7.ex5 artifacts/tentei-himo/TenteiHimo_Live.ex5
# 2. コンテナ再起動で反映（/artifacts は ro マウント → 起動フックが MQL5/Experts へ反映）
docker compose restart mt5-tentei-himo
# 3. ブラウザ(:3001)で EA バージョン・AutoTrading ON を確認
```

> ロジックの正は invest monorepo。Dell 側で `.mq5` の改変・再コンパイルは**行わない**
> （投資部門のステージゲート管轄）。バージョンは投資部門の指示に従い記録する。

---

## 4. MT5 端末バージョン固定（再現性リスク対策）

ベースイメージ `gmag11/metatrader5_vnc` は MT5 端末を起動時に最新へ自動更新する。フォワード検証の
再現性に影響しうるため:

- 通常運用は自動更新を許容（broker 互換性のため）。ただし**更新で挙動が変わったら記録**する。
- 検証期間中に端末を固定したい場合は、ベースイメージを**特定タグにピン留め**して再ビルド
  （`FROM gmag11/metatrader5_vnc:1.1` のように固定。`latest` は使わない）。
- 端末更新と EA 挙動変化の因果を切り分けるため、更新検知時は health-watch のログにバージョンを残す。

---

## 5. 成績の Mac 還流（MT-005, O.Q.4）

- `scripts/sync-results.sh` を systemd timer（例: 15分間隔）で実行し `data/<track>/` を**成績専用リポ**へ同期。
- ✅ **還流方式確定（O.Q.4 = (a) 成績専用リポ）**: `data/` は本リポでは `.gitignore` 除外のまま、別の
  成績専用リポへ rsync→commit→push する（deployment.md §8）。残タスクは 🟡 成績専用リポの URL/認証の
  払い出しで、`RESULTS_REPO` に設定する。確定までは volume 永続化でローカル保全され、成績は失われない。
- Mac 側は成績専用リポを `git pull` → 投資部門が `himo_live_trades.csv` を照合。

---

## 6. 障害対応

| 事象 | 対応 |
|------|------|
| コンテナが落ちた | `restart: always` で自動復帰。復帰しない場合 `docker compose up -d`。建玉は broker 側 SL/TP で保護（NF-006） |
| EA が detach（自動売買OFF） | ブラウザ(:300x)で AutoTrading を再ON。頻発するなら `/config` プロファイルを再保存 |
| broker 切断が続く | 口座情報・サーバー名・ネットワークを確認。TitanFX デモのメンテ時間も確認 |
| outage で取りこぼし | EA v0.6 の `GAP_FILL` で復旧されるはず。されなければ投資部門にフィードバック（EAの責務） |
| Dell 再起動後に未復帰 | Docker デーモン起動と `restart: always` を確認（deployment.md §7） |
| メモリ逼迫 | `docker stats` で犯人特定 → limits 見直し or トラック一時停止 |

### 障害テスト（受け入れ基準の検証）

```bash
# 意図的にコンテナを一定時間停止 → 再開し、GAP_FILL（欠落区間記録）が出るか確認
docker compose stop mt5-tentei-himo
sleep 1800                         # 30分 outage を作る
docker compose start mt5-tentei-himo
grep -E 'GAP_FILL|MISSED_OUTAGE' data/tentei-himo/Logs/*.log
# → 出れば EA v0.6 の gap-fill が機能。出なければ投資部門へフィードバック
```

---

## 7. トラック増設手順（MT-008 — 並列検証の追加）

```bash
cd services/mt5-forward
# 1. TitanFX デモ口座を新規発行（口座番号・master/investor パスワード入手）
# 2. トラック定義作成（ウィザード or 手動）
./scripts/new-track.sh <track-name>          # tracks/<name>.env と data/<name>/ artifacts/<name>/ を生成
# 3. 凍結 .ex5 を artifacts/<name>/ に配置
# 4. secret 作成（master パスワード, 0600）
printf '%s' '<password>' > secrets/titanfx_demo<N>_password && chmod 600 secrets/titanfx_demo<N>_password
# 5. docker-compose.yml に anchor 差分1ブロック追加（port は 300N、env/volume/secret 差し替え）
# 6. 起動
docker compose up -d mt5-<track-name>
# 7. ブラウザ(:300N)で master ログイン → 自動起動セットアップ（deployment.md §3）
```

- 各トラックは**完全独立**（資金曲線/建玉/記録/障害が干渉しない）。出力は `data/<track>/` に分離（MT-009）。
- 同一戦略・多通貨は1トラック内の複数チャートで対応（`symbol + magic` で分離, MT-010）。

---

## 8. 定期メンテナンス

| 周期 | 作業 |
|------|------|
| 日次 | `docker compose ps` / 取引ログ更新確認 / 成績同期の成功確認 |
| 週次 | `docker stats` ピークメモリ記録（増強判断）/ broker 切断回数の集計 |
| EA更新時 | §3 差し替え手順 / バージョン記録 / 投資部門と整合 |
| 端末更新検知時 | §4 バージョン記録 / 挙動変化の有無を確認 |

---

## 9. セキュリティ運用（NF-001/002）

- noVNC/SSH は **Tailscale 経由のみ**。KasmVNC ポートは `127.0.0.1:300x` で localhost 束縛し、
  host の `tailscale serve --bg localhost:300x` で **Tailnet 限定**プロキシして公開する
  （`127.0.0.1` 束縛単体では Tailscale でも到達不可、`tailscale serve` が必須）。`tailscale funnel`（公開）は使わない。
  - 公開状態の確認: `tailscale serve status`
  - トラック撤去時は `tailscale serve --https=443 off` 等で該当公開も停止する
- broker パスワードは docker secret。リポジトリに平文を置かない（コミット前チェックは deployment.md §5 の方法を使う）。
- `.gitignore` 対象（`secrets/`・`tracks/*.env`・`*.ex5`・`data/`・`config/*.ini`）を誤って追跡しないこと。
