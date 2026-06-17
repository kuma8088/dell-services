# mt5-forward — MT5 フォワードトレード常駐ホスト

FX 戦略「天底紐理論」の検証済みEA（`TenteiHimo_Live`）を Dell 上の Docker で 24時間常駐させ、
TitanFX デモ口座でフォワードテストを継続するサービス。母艦（Mac/Parallels）のスリープ・回線断に
起因するフォワードの取りこぼしを解消することが目的。

## ドキュメント

| ファイル | 内容 | 状態 |
|---------|------|------|
| [requirements.md](./requirements.md) | 要件定義（EdgeVault 投資部門から提示） | ✅ 提示済み |
| architecture.md | 構成設計（コンテナ構成・ネットワーク・volume） | ⬜ Dell 側で作成 |
| deployment.md | デプロイ手順（イメージ・compose・自動起動・secret） | ⬜ Dell 側で作成 |
| operations.md | 運用（監視・EA差し替え・成績同期・障害対応） | ⬜ Dell 側で作成 |

## 位置づけ

- **要件（WHAT/WHY）= EdgeVault 投資部門**（本 PR）
- **構築設計・実装（HOW）= Dell 側**（このあと）
- EA ロジックの正は invest monorepo（`dev/invest/strategies/tentei-himo/`）。本サービスは
  凍結済み `.ex5` を**実行する器**であり、ロジック改変は行わない

実体（Dockerfile / docker-compose.yml / config）は [`services/mt5-forward/`](../../../services/mt5-forward/) に
Dell 側が作成する。
