# 構成設計 - mt5-forward (architecture)

**対象**: Dell ワークステーション (Rocky Linux 9.6) 上の Docker サービス
**作成日**: 2026-06-18
**ステータス**: 設計（レビュー待ち）
**対応要件**: [requirements.md](./requirements.md) MT-001〜010 / NF-001〜006

> このドキュメントは requirements.md §7 の Open Questions に回答する「構築設計(HOW)」です。
> 実装（Dockerfile / docker-compose.yml）は本設計の承認後に着手します。

---

## 1. 設計判断サマリ（Open Questions への回答）

| # | Open Question | 採用案 | 根拠 / 却下した代替案 |
|---|---------------|--------|----------------------|
| 1 | 配置形態 | **ホスト直下 Docker Compose** | 既存サービス（mailserver/blog/unified-portal）が全てホスト直下 compose 運用。libvirt 専用VMは追加オーバーヘッド（メモリ/管理）に対し隔離メリットが薄く、検証用途には過剰 |
| 2 | ベースイメージ | **`gmag11/metatrader5_vnc:1.1`（MQL5専用・軽量版 約600MB）を利用し、薄い自前 Dockerfile でラップ** | 公式確認済み（Debian+Wine+KasmVNC、`/config`永続化、ブラウザGUI :3000、純MQL5でPython不要、v2.3まで活発保守）。フル自前ビルド（Wine+Xvfb+noVNC）は保守コストが高く却下。Python入りv2(約4GB)はEAが純MQL5のため不要 |
| 3 | EA成果物の同期 | **凍結 `.ex5` を host の `artifacts/<strategy>/` に手動配置 → コンテナへ read-only マウント** | 「本サービスは実行する器、ロジック改変しない」原則と `.gitignore`（`*.ex5`除外）に整合。invest monorepo の Dell checkout マウントは Dell からのアクセス前提が未確定のため初版では非採用（将来オプション） |
| 4 | 成績同期 | **(a) 成績専用リポへ host の systemd timer が `data/<track>/` を git commit/push**（確定） | EdgeVault 既存運用「Dellが書く→Macがgit pull」に整合（MT-005）。本サービスのコード/設計リポ（= 本リポ。ドキュメント駆動型 IaC リポ）に高頻度の取引CSVをコミットして履歴を汚さないよう、成績は**別リポ**に分離。(b)本リポで`data/`追跡解除・(c)rsync over Tailscale は却下（deployment.md §8 にトレードオフ記載）。残: 成績専用リポの URL/認証の払い出し（🟡 起動前） |
| 5 | MT5自動起動の永続化 | **`/config` volume に MT5 プロファイル＋チャートテンプレートを保存し、初回手動セットアップ後は再起動で復元** | KasmVNC版は `/config` に MT5 設定を永続化。EA自動アタッチはプロファイル(`profiles/`)＋テンプレ(`.tpl`)で固定。詳細は deployment.md |
| 6 | 監視 | **初版は軽量に: compose healthcheck（コンテナ生存）＋ ログ監視スクリプト（broker切断/EA detach 検知）** | 検証用途のためベストエフォート 24/7（NF-006）。過剰な監視基盤は作らず、既存の通知経路（メール/SNS）に寄せる |
| 7 | トラック定義 | **`tracks/<name>.env` テンプレ ＋ Compose の YAML anchor で N コンテナ生成** | MT-008（トラック追加＝コンテナ1つ増やすだけ）を満たす。env ファイルで口座情報・EAセット・magic・ポート・出力先を宣言 |
| 8 | デモ口座払い出し | **トラックごとに TitanFX デモ口座を個別発行し、`tracks/<name>.env` ＋ Docker secret で管理** | MT5 は1端末1口座制約のため（§2.1）。初版1口座、増設時に追加発行（運用手順は operations.md） |

---

## 2. 全体構成図

```
Dell WorkStation (Rocky Linux 9.6, 常時起動)
│
├─ Tailscale (tailscale0)                  ← Mac からの唯一の到達経路 (NF-001)
│
└─ Docker Compose project: mt5-forward
   │  network: mt5_network (bridge, 172.23.0.0/24)   ← 新規・他サービスと非衝突
   │
   ├─ service: mt5-tentei-himo  (初版で起動する単一トラック)
   │    image: mt5-forward:local (gmag11/metatrader5_vnc:1.1 ベース)
   │    口座: TitanFX デモ #1 / EA: TenteiHimo_Live.ex5 (magic=26060801)
   │    ports: 127.0.0.1:3001 -> 3000  (KasmVNC, localhost束縛)
   │      └─ host で `tailscale serve --bg localhost:3001` → Tailnet限定で Mac へ公開
   │    限界: cpus 2.0 / mem 2G (NF-003)
   │    volumes:
   │      - ./tracks/tentei-himo/config:/config        (MT5プロファイル永続化, MT-005/MT-007)
   │      - ./artifacts/tentei-himo:/artifacts:ro       (凍結 .ex5 / .tpl, read-only)
   │      - ./data/tentei-himo:/output                  (取引CSV/ログのhost還流先, MT-004/009)
   │    secrets: titanfx_demo1_password
   │
   ├─ service: mt5-<track2>   (将来: tracks/<track2>.env を足すだけ, MT-008)
   └─ service: mt5-<trackN>   …
        各コンテナ完全独立 = 資金曲線/建玉/記録/障害が干渉しない (§2.1)
```

---

## 3. コンポーネント詳細

### 3.1 イメージ（mt5-forward:local）

`gmag11/metatrader5_vnc:1.1` をベースに、以下だけを足す**薄いラッパ**:

- 凍結 EA/インジ（`.ex5`）と チャートテンプレ（`.tpl`）の配置（マウント or COPY）
- 起動時に EA を USDJPY M5 へ自動アタッチ・AutoTrading ON にする初期化（deployment.md §自動起動）
- タイムゾーン UTC 固定（NF-005）

> **リスク注記**: このイメージは MT5 端末を起動時に最新へ自動更新する。フォワード検証の再現性に
> 影響しうるため、operations.md にバージョン固定/監視の運用を記載する。

### 3.2 ネットワーク（mt5_network）

| 項目 | 値 | 根拠 |
|------|----|----|
| driver | bridge | 既存サービス慣習 |
| subnet | **172.23.0.0/24** | 実機の使用中サブネットと非衝突（実測確認）: 172.17/16(bridge), 172.18/16(gwbridge), 172.19/16(deadline-management), 172.20/24(mailserver), 172.22/24(blog)。172.21・172.23 は空き。Swarm ingress は 10.0.0.0/24 |
| 外部公開 | **しない（Tailnet限定）** | NF-001。Docker は `127.0.0.1:300x` で**localhost束縛のみ公開**（公開IPに出さない）。Mac への到達は host の **`tailscale serve --bg localhost:300x`** で Tailnet 限定プロキシして実現する。⚠️ `127.0.0.1` バインド**単体では Tailscale 経由でも到達不可**（Tailscale は `tailscale0`/100.64.0.0/10 に届くため）。`tailscale serve` が必須。公開はあくまで serve 経由で、`tailscale funnel`（公開インターネット）は使わない |
| ポート割当 | トラックごとに 3001, 3002, … | MT-006（トラック別 noVNC ポート）。各ポートを個別に `tailscale serve` で公開 |

### 3.3 ボリューム / 永続化（トラックごと）

| マウント | コンテナ側 | 用途 | 要件 |
|---------|-----------|------|------|
| `tracks/<t>/config` | `/config` | MT5 プロファイル・チャート・端末設定（再起動で復元） | MT-001/005/007 |
| `artifacts/<t>` (ro) | `/artifacts` | 凍結 `.ex5` / `.tpl`（差し替えは再ビルド不要, MT-007） | MT-007 |
| `data/<t>` | `/output` | `himo_live_trades.csv` ＋ `Logs/`（Mac 還流の元データ, トラック分離） | MT-004/009 |

> EA は `MQL5/Files/` にCSVを書く。コンテナ内で `MQL5/Files/`・`MQL5/Logs/` を `/output`（=host `data/<t>/`）へ
> symlink で逃がす（具体的なフック実装と Wine 追従の検証は deployment.md §2.1）。

### 3.4 シークレット

- broker master パスワードは **`docker secret`（compose の `secrets:`）で注入**。env_file には口座番号・サーバー名など非機密のみ（NF-002）
- `.gitignore` で `.env*` / `config/*.ini` / `tracks/*.env` / `*.ex5` / `data/` を除外済み（コミット汚染防止）

---

## 4. トラック水平展開モデル（MT-008/009/010）

「1検証トラック = 1コンテナ = 1デモ口座」を**テンプレ化**する。

```
services/mt5-forward/
├─ docker-compose.yml          # YAML anchor (&track-base) で共通定義、トラックは差分のみ
├─ tracks/
│   ├─ tentei-himo.env         # 口座#1: ACCOUNT/SERVER/MAGIC/VNC_PORT/EA_FILE/OUTPUT_DIR
│   └─ <track2>.env            # 口座#2: … (足すだけで増える)
├─ artifacts/<track>/          # 凍結 .ex5 / .tpl  (gitignore)
└─ data/<track>/               # 取引CSV / Logs   (gitignore, 還流元)
```

- **トラック追加手順** = ①TitanFXデモ口座発行 → ②`tracks/<name>.env` 作成 → ③`artifacts/<name>/` にEA配置 → ④compose に anchor 差分1ブロック追加 → ⑤`docker compose up -d <svc>`
- 同一戦略・多通貨（パターンA）は **1トラック内の複数チャート**で対応（口座を増やさない）。注文分離は `symbol + magic`（MT-010）

---

## 5. データフロー

```
[EdgeVault invest monorepo]
   凍結 TenteiHimo_Live.ex5 / Signals.ex5
        │ (手動配置 or リリース成果物)
        ▼
[Dell] artifacts/<track>/*.ex5  ──(ro mount)──▶ コンテナ MQL5/Experts, MQL5/Indicators
                                                      │ EA稼働(AutoTrading ON)
                                                      ▼
                                          MQL5/Files/himo_live_trades.csv, MQL5/Logs/*.log
                                                      │ (bind)
                                                      ▼
[Dell] data/<track>/  ──(systemd timer: git commit/push)──▶ 成績専用リポ (O.Q.4=(a) 確定)
                                                      │
                                                      ▼
[Mac] git pull ──▶ 投資部門が成績照合 / noVNC(:300x, tailscale serve)でGUI閲覧
```

---

## 6. 受け入れ基準との対応

| 受け入れ基準 (requirements §6) | 本設計での実現箇所 |
|-------------------------------|-------------------|
| 再起動→コンテナ自動復帰→EA自動アタッチ | `restart: always` ＋ `/config` 永続プロファイル（§3.3, deployment.md §自動起動） |
| Mac から Tailscale 経由 noVNC で M5 チャート＋発火マーク | §3.2 ポート 300x ＋ Signals インジ（MT-003） |
| テスト発注が CSV 記録され Mac git で読める | §5 データフロー ＋ systemd timer git push（O.Q.4） |
| 再起動をまたいで CSV/ログ/プロファイル永続化 | §3.3 volume 3種 |
| broker パスワードがリポジトリに存在しない | §3.4 docker secret ＋ `.gitignore` |
| 停止→再開で `GAP_FILL` ログ確認 | operations.md の障害テスト手順で検証（EA v0.6 挙動確認） |

---

## 7. 未確定・要確認事項（実装前に詰める）

🔴 = 実装着手のブロッカー（確定するまで設計は閉じない） / 🟡 = 起動前までに確定 / ✅ = 確定済み

1. ✅ **成績還流方式（O.Q.4 / MT-005 必須）= (a) 成績専用リポ で確定**（2026-06-20）。
   方式は決定済みのため設計は閉じた。残タスクは 🟡 成績専用リポの **URL/認証（push 先）の払い出し**（起動前。
   `scripts/sync-results.sh` の `RESULTS_REPO` に設定）。(b)/(c) は却下（deployment.md §8）
2. 🟡 **invest monorepo → Dell の EA 受け渡し経路**（手動配置で初版確定。将来 checkout マウントするなら Dell からのアクセス権が必要）
3. 🟡 **TitanFX デモの investor 同時接続可否**（requirements §5.3）— 移行前に実地確認。不可なら noVNC 一本に倒す
4. 🟡 **EA `.ex5` の現物**（v0.6, causal gap-fill 版）と **デモ口座** の受領（= 実起動はこれ待ち）
5. 🟡 **EA の CSV 出力先仕様**（カスタムパス入力の有無）— `MQL5/Files` symlink 方式の確定に必要（deployment.md §2.1）
