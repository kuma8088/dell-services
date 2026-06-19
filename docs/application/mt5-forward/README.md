# mt5-forward — MT5 フォワードトレード常駐ホスト

FX 戦略「天底紐理論」の検証済みEA（`TenteiHimo_Live`）を Dell 上の Docker で 24時間常駐させ、
TitanFX デモ口座でフォワードテストを継続するサービス。母艦（Mac/Parallels）のスリープ・回線断に
起因するフォワードの取りこぼしを解消することが目的。

## ドキュメント

| ファイル | 内容 | 状態 |
|---------|------|------|
| [requirements.md](./requirements.md) | 要件定義（EdgeVault 投資部門から提示） | ✅ 提示済み |
| [architecture.md](./architecture.md) | 構成設計（コンテナ構成・ネットワーク・volume） | ✅ 設計（レビュー反映済み） |
| [deployment.md](./deployment.md) | デプロイ手順（イメージ・compose・自動起動・secret） | ✅ 設計（レビュー反映済み） |
| [operations.md](./operations.md) | 運用（監視・EA差し替え・成績同期・障害対応） | ✅ 設計（レビュー反映済み） |

> ✅ **成績還流方式 確定（O.Q.4 = (a) 成績専用リポ, 2026-06-20）**: `data/` を本リポでは追跡せず、別の
> 成績専用リポへ push する（[deployment.md §8](./deployment.md)）。設計のブロッカーは解消済み。
> 起動に残る外部依存は 🟡 **EA `.ex5`(v0.6) / TitanFX デモ口座 / 成績専用リポの URL・認証** の払い出し。

## 位置づけ

- **要件（WHAT/WHY）= EdgeVault 投資部門**（本 PR）
- **構築設計・実装（HOW）= Dell 側**（このあと）
- EA ロジックの正は invest monorepo（`dev/invest/strategies/tentei-himo/`）。本サービスは
  凍結済み `.ex5` を**実行する器**であり、ロジック改変は行わない

実体（Dockerfile / docker-compose.yml / config）は [`services/mt5-forward/`](../../../services/mt5-forward/) に
Dell 側が作成する。
