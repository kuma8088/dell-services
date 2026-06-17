# 要件定義 - MT5 フォワードトレード常駐ホスト (mt5-forward)

**依頼者**: kuma8088（投資部門 R&D / EdgeVault workspace 側）
**対象**: Dell ワークステーション (Rocky Linux 9.6) 上の Docker サービス新設
**作成日**: 2026-06-16
**ステータス**: 要件提示（構築設計は Dell 側で実施）

> このドキュメントは「何を・なぜ・どの制約で」を伝える要件定義です。Dockerfile / compose /
> 自動起動などの**構築設計（HOW）は Dell 側に委ねます**。設計後 `architecture.md` /
> `deployment.md` / `operations.md` を本ディレクトリに追加してください。

---

## 1. プロジェクト背景と目的

### 1.1 解決すべき課題

FX 戦略「天底紐理論」の検証済みEA（`TenteiHimo_Live` v0.5→v0.6）を、現在 **Mac + Parallels の
MT5** でフォワードテスト（TitanFX デモ口座）している。この構成に以下の課題がある。

| 課題 | 詳細 | 影響 |
|-----|------|-----|
| 母艦が寝る | Mac/Parallels は夜間スリープ・回線断が頻発（実測: 06-15 夜〜06-16 朝に約24h オフライン） | フォワード中の発火を取りこぼし、成績が下振れ＝**検出器の真の性能を過小評価** |
| 黙ったデータ欠落 | 旧EA は再接続時に最新足1本しか取り込まず、欠落区間を復旧できなかった（投資部門 DETECTION_LOG 続報28） | フォワード統計の信頼性が損なわれる |
| 監視と運用の同居 | 1台の MT5 でチャート閲覧とEA稼働が混在 | 誤操作リスク・視認性低下 |

### 1.2 目的

1. **24時間常駐**: 常時起動の Dell 上でEAを動かし、母艦スリープ起因の機会損失をゼロにする
2. **Mac から閲覧**: チャート・建玉・フォワード成績を Mac から確認できる（後述の二系統）
3. **成績の自動還流**: EAが出力する取引CSV/ログを Mac（git）側で読める形に同期する
4. **複数検証の並列運用（重要）**: 戦略・パラメータ違いを**独立した検証トラックとして同時に**回せる。
   初版は tentei-himo 単一で立ち上げるが、**設計は最初から N トラックへ水平拡張できる**こと（後述 §2.1）

> 注: EA 側の堅牢化（再接続時の gap-fill 全バー復旧 = "D1a"）は **EdgeVault 投資部門側で別途実施**し、
> 凍結済み `.ex5` として本サービスに引き渡す。本サービスの責務は「EAを正しく常駐実行する器」。

---

## 2. 想定アーキテクチャ（推奨。最終判断は Dell 側）

### 2.1 基本単位 = 「1検証トラック = 1コンテナ = 1デモ口座」

MT5 は **1端末が同時にログインできる口座は1つ**（口座切替＝前口座から切断）。よって複数検証を
**並列・独立**に回す唯一クリーンな方法は端末を分けること = **Docker コンテナを分けること**。
本サービスは「トラックをパラメータで定義し、N コンテナを起動する」テンプレ構成とする。

```
Dell (Rocky 9.6, 常時起動)
└─ Docker: mt5-forward （トラックごとに1コンテナ）
   ├─ mt5-tentei-himo   ← デモ口座#1, TenteiHimo_Live.ex5,  magic=26060801, 出力 data/tentei-himo/
   ├─ mt5-wemof         ← デモ口座#2, Wemof EA,             magic=…,        出力 data/wemof/
   └─ mt5-himo-variantB ← デモ口座#3, パラメータ違い,        magic=…,        出力 data/himo-variantB/
        各コンテナ共通:
          ├─ MT5 端末 (Wine) ← 各自のデモ口座に master ログイン
          │    ├─ Experts/    : <strategy>.ex5（master=自動売買 ON）
          │    └─ Indicators/ : TenteiHimo_Signals.ex5（可視化・任意）
          ├─ noVNC (ブラウザ) ← Tailscale 経由で Mac から GUI 閲覧（トラックごとに別ポート）
          └─ volume: MQL5/Files/(取引CSV), Logs/ を host の data/<track>/ にマウント
               └─ host 側 cron/timer が git commit/push → Mac は git pull
```

各コンテナは**資金曲線・建玉・記録・障害が完全に独立**。1トラックのDDが他に影響せず、性能比較が公平。

### 2.2 トラック内の複数通貨は同居でよい

「同一戦略を7通貨で」のような場合は**1トラック（1口座・1コンテナ）内に複数チャート**で足りる
（口座を増やす必要はない）。同口座内の複数EA/通貨は **symbol + magic number** で記録・管理を分離する。
TitanFX デモは **hedging**（同一通貨で複数建玉可・観測済み）なので、L3ラダーも複数EAも共存できる。

### 2.3 実証済みパターン

EA は **純 MQL5（Python 依存なし）**。Wine + Xvfb + noVNC で MT5 をブラウザ操作する Docker
イメージは確立されており、MQL5-only bot 用途では `gmag11/MetaTrader5-Docker`（`metatrader5_vnc` 系）が
定番。これをベースにするか自前 Dockerfile にするかは Dell 側判断。出典は README 参照。

---

## 3. 機能要件

| 要件ID | 要件 | 優先度 | 判断理由 |
|--------|-----|--------|---------|
| MT-001 | MT5 端末を Docker コンテナで常駐起動し、Dell 再起動後も自動復帰する | 必須 | 常時稼働が本プロジェクトの主目的。systemd / compose `restart: always` |
| MT-002 | TitanFX デモ口座に **master** でログインし、`TenteiHimo_Live.ex5` を USDJPY M5 チャートに自動アタッチ・AutoTrading ON で起動する | 必須 | 人手の再アタッチなしで稼働継続するため |
| MT-003 | `TenteiHimo_Signals.ex5`（可視化インジ）を同チャートに適用する | 推奨 | 発火マークをチャートで確認するため。EAとは独立 |
| MT-004 | EA が出力する `MQL5/Files/himo_live_trades.csv` と `MQL5/Logs/*.log` を host 側ディレクトリへ永続化する | 必須 | フォワード成績の保全と Mac 還流の元データ |
| MT-005 | 上記CSV/ログを Mac から読める形に同期する（git commit/push 推奨。rsync over Tailscale も可） | 必須 | 「移行先の成績を Mac で確認」を満たす。EdgeVault の "Dell が書く→Mac が git pull" 既存運用に整合 |
| MT-006 | ブラウザ(noVNC) で MT5 GUI を Tailscale 経由で閲覧できる | 必須 | Mac からチャート・建玉をリアルタイム確認（投資家パスワード方式の代替/併用） |
| MT-007 | EA・インジの `.ex5` 差し替え（バージョン更新）が再ビルドなしの volume 差し替え + 再起動で可能 | 推奨 | EA は EdgeVault 側で更新され凍結受け渡しされるため |
| MT-008 | **検証トラックをパラメータ（口座情報・EAセット・magic・noVNCポート・出力先）で定義し、追加トラックはコンテナを1つ増やすだけで起動できる** | 必須 | 複数検証の並列運用（目的4）。初版は1トラックでも、設計は N トラック前提 |
| MT-009 | トラックごとに出力先を分離する（例 `data/<track>/himo_live_trades.csv`）。トラック間でCSV/ログが混ざらない | 必須 | 検証ごとの成績を独立に照合するため |
| MT-010 | 同一口座内に複数EA/通貨を同居させる場合、各注文は magic number + symbol で分離される | 必須 | パターンA（1戦略・多通貨）を1コンテナで扱うため |

---

## 4. 非機能要件

| 要件ID | 要件 | 優先度 | 判断理由 |
|--------|-----|--------|---------|
| NF-001 | 外部公開しない。管理アクセス（noVNC/SSH）は **Tailscale 経由のみ** | 必須 | 既存インフラのセキュリティ方針に整合。取引端末を公開しない |
| NF-002 | broker 認証情報（master パスワード）は **コミットしない**。env_file / Docker secret で注入 | 必須 | 機密。リポジトリ汚染防止 |
| NF-003 | リソース上限を設定（compose `deploy.resources.limits`）。目安 cpus 2.0 / mem 2G | 推奨 | 他サービス（メール・WP・ポータル）と同居のため |
| NF-004 | ログローテーション（json-file, max-size/max-file） | 推奨 | 既存サービス慣習に整合 |
| NF-005 | コンテナ時刻は UTC 固定。EA はサーバー時刻→UTC 変換に依存 | 必須 | ロールオーバー/週末フラット判定が時刻依存（EA仕様） |
| NF-006 | 可用性は「ベストエフォート 24/7」。EA が落ちても建玉の SL/TP は broker サーバー側で有効 | 必須 | 検証用途。Dell 障害時もポジション保護は broker 側に依存 |

---

## 5. インターフェース / 受け渡し仕様

### 5.1 EdgeVault 投資部門 → Dell（入力）

| 成果物 | 内容 | 受け渡し方法（要相談） |
|-------|------|----------------------|
| `TenteiHimo_Live.ex5` | 凍結済みEA（現行 v0.6、causal gap-fill 版） | invest monorepo `dev/invest/strategies/tentei-himo/mt5/` が正。Dell へ checkout or リリース成果物として配置 |
| `TenteiHimo_Signals.ex5` | 可視化インジ | 同上 |
| broker 接続情報 | TitanFX デモ: サーバー名 / 口座番号 / master パスワード | **別経路で安全に共有**（コミット禁止）。Dell 側 secret に登録 |
| チャート前提 | USDJPY, M5, InpRiskPct=1.0（実弾は%リスク） | EA入力パラメータ。デフォルトで可 |

> EA の `.mq5` ソースの正は invest monorepo 側。Dell には**実行用 `.ex5` と運用設定のみ**を置き、
> ロジック改変は行わない（投資部門のステージゲート管轄）。

### 5.2 Dell → Mac（出力）

| 成果物 | 形式 | 同期先 |
|-------|------|--------|
| `data/<track>/himo_live_trades.csv` | 取引記録（signal_time/dir/entry/real_pips/shadow_pips/exit_reason 等）。**トラックごとに分離** | git or rsync → Mac が取得し投資部門が照合 |
| `data/<track>/Logs/` | Experts ログ（`MISSED_OUTAGE` / `GAP_FILL` / `ENTRY` / `SKIP` 等） | 同上。outage 可視化に必須 |
| （任意）日次サマリ | トラック別 markdown/HTML 自動生成 | あると Mac 側確認が楽 |

### 5.3 Mac からの閲覧（二系統）

1. **noVNC（MT5 GUI そのもの）**: Tailscale 経由でブラウザから master セッションのチャート・建玉を閲覧（MT-006）
2. **investor パスワード（読み取り専用）**: Mac の MT5 から同口座へ investor ログインし、ローカルで `Signals` インジを適用してチャート監視。master(Dell) と共存可能。※TitanFX デモでの investor 同時接続可否は移行前に実地確認

---

## 6. 受け入れ基準（Acceptance Criteria）

- [ ] Dell 再起動 → コンテナ自動復帰 → EA が自動アタッチ・AutoTrading ON で稼働再開する
- [ ] Mac のブラウザから Tailscale 経由で noVNC に接続し、USDJPY M5 チャート＋発火マークが見える
- [ ] テスト発注（デモ）が `himo_live_trades.csv` に記録され、そのファイルが Mac 側 git で `git pull` 後に読める
- [ ] コンテナ再起動をまたいで CSV/ログ/MT5プロファイルが永続化される（volume）
- [ ] broker パスワードがリポジトリ内に存在しない（grep で確認）
- [ ] 意図的にコンテナを一定時間停止→再開し、Experts ログに `GAP_FILL`（または欠落区間の記録）が出ることを確認（EA v0.6 の挙動確認。EAが未対応バージョンなら投資部門にフィードバック）

---

## 7. Dell 側で判断・設計してほしい事項（Open Questions）

1. **配置形態**: ホスト直下 Docker か、libvirt の専用VM上か（既存サービスはホスト直下 compose 運用）
2. **ベースイメージ**: `gmag11/MetaTrader5-Docker` 流用か、自前 Dockerfile（Wine+Xvfb+noVNC）か
3. **EA成果物の同期方式**: invest monorepo を Dell に checkout してマウントか、リリース成果物の手動配置か
4. **成績同期の方式**: git push（推奨・既存運用に整合）か rsync over Tailscale か。push 先リポジトリ/認証
5. **MT5自動起動の永続化**: チャートプロファイル + `config/*.ini` でEA自動アタッチをどう固定するか
6. **監視**: コンテナ death / EA detach / broker 切断の検知（healthcheck・通知）をどこまで作るか
7. **トラック定義の持ち方**: compose の複数サービスで列挙するか、`tracks/<name>.env` 的なテンプレ + 生成スクリプトにするか（MT-008 の実現方式）
8. **デモ口座の払い出し**: トラックごとに **TitanFX デモ口座を個別に発行**する運用（口座番号・master/investor パスワードの管理方法）。初版1口座、増設時に追加発行

---

## 8. スコープ

### 初版で動かす範囲
- **tentei-himo 単一トラック**（デモ口座1つ）で常駐・閲覧・成績還流まで通す

### 初版から設計に織り込む範囲（実装は後でも、設計は今）
- **N トラックへの水平拡張**（MT-008/009/010）。トラック追加がコンテナ追加だけで済む構造にしておく

### スコープ外
- EA のロジック改変・最適化（投資部門のステージゲート管轄。Dell は実行環境のみ）
- 実弾（リアルマネー）運用（現段階はデモのフォワード検証のみ。実弾はステージゲート通過後に別途判断）
