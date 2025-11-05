# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

---

## ⚠️ このファイルの編集ルール（必読）

**目的**: 新しいClaude instancesが最初の5分で理解すべき最小限の情報を提供する

**編集方針**:
- ✅ **このファイルには詳細を書かない** - ドキュメントへのリンクのみ
- ✅ **コマンド例を書かない** - 各README.mdに記載
- ✅ **設定内容を書かない** - 各ドキュメントに記載
- ✅ **150行以内に収める** - 簡潔さを維持
- ❌ **詳細情報の追加禁止** - 既存ドキュメントを参照させる

**編集が必要な場合**:
1. プロジェクト全体の方針変更
2. 新しい必読ドキュメントの追加
3. 致命的なルールの追加

**詳細情報の追加先**:
- インフラ関連 → [docs/infra/README.md](docs/infra/README.md)
- Mailserver関連 → [docs/application/mailserver/README.md](docs/application/mailserver/README.md)
- トラブルシューティング → [services/mailserver/troubleshoot/README.md](services/mailserver/troubleshoot/README.md)

---

## 📋 プロジェクト概要

**リポジトリタイプ**: ドキュメント駆動型インフラリポジトリ

**目的**: Dell WorkStation (Rocky Linux 9.6) 上でDocker環境を構築し、Mailserverを稼働

**特徴**:
- 実行可能な手順書を管理（アプリケーションコードは含まない）
- フェーズ別構築: Docker基盤 → サービスデプロイ
- 将来的なAWS移行を想定

**現在の構成**:
- ✅ Dell: Docker Compose環境（Mailserver稼働中）
- ✅ EC2: Dockerコンテナ（MX Gateway稼働中）
- 📝 KVM環境: 構築済みだが現在未使用（将来的な仮想化用）

**ハードウェア制約**:
- CPU: 6コア/12スレッド、RAM: 32GB、Storage: 3.6TB HDD + 390GB SSD
- Docker環境: ホストリソースを直接使用

---

## 🚨 絶対にやってはいけないこと

### 1. インフラ変更前の公式ドキュメント確認（必須）

**CRITICAL**: Docker/ネットワーク/ストレージ構成変更時は必ず公式ドキュメント確認

**理由**: 誤設定は本番障害に直結。ポート番号・ネットワークレンジ・サービス動作を仮定しない。

**公式ドキュメント**:
- Docker: https://docs.docker.com/
- Docker Compose: https://docs.docker.com/compose/
- Rocky Linux: https://docs.rockylinux.org/

**確認手順**:
1. WebFetchで公式ドキュメント取得
2. 現在の設定確認: `docker compose config`
3. テスト環境で検証 → 本番適用

### 2. SSH ポート設定

**絶対禁止**: Port 22 の使用

**現在の構成**: Dell/EC2ともにポート22以外を使用（セキュリティのため）

**注**: 以下のセグメント別ポートはKVM仮想ネットワーク用（現在未使用）

| セグメント | SSHポート範囲 | 状態 |
|---------|-------------|------|
| Management | 2201-2210 | 未使用 |
| Public | 2211-2230 | 未使用 |
| Private | 2231-2250 | 未使用 |
| Database | 2251-2260 | 未使用 |
| Container | 2261-2280 | 未使用 |

### 3. 認証情報の混同注意（Mailserver）

**重要**: `.env` の `MYSQL_PASSWORD` と `USERMGMT_DB_PASSWORD` は**異なる**

- ❌ Dovecot SQL認証で `MYSQL_PASSWORD` を使用（間違い）
- ✅ Dovecot SQL認証は `usermgmt` ユーザー + `USERMGMT_DB_PASSWORD` を使用

詳細: [docs/application/mailserver/usermgmt/DEVELOPMENT.md](docs/application/mailserver/usermgmt/DEVELOPMENT.md)

### 4. 手順書実行の原則

- **実行前**: 前提条件・期待出力・ロールバック手順を確認
- **実行中**: 結果を記録、期待値と異なる場合は停止
- **実行後**: バリデーション実施、Git コミット

---

## 📚 必読ドキュメント（最初に読むべきもの）

### 1. インフラドキュメント

**[docs/infra/README.md](docs/infra/README.md)** - 必ず最初に読む

**内容**:
- Docker環境構築手順書（Phase 3）
- ストレージ構成（SSD/HDD分離）
- よく使うコマンド
- よくある問題と対処
- KVM環境手順書（構築済み、現在未使用）

### 2. Mailserverドキュメント

**[docs/application/mailserver/README.md](docs/application/mailserver/README.md)** - Mailserver作業時に必読

**内容**:
- アーキテクチャ（EC2 MX + Dell LMTP + SendGrid）
- サービス構成（Docker Compose）
- Phase 11/11-A: User Management System
- EC2操作ガイド
- Terraform運用

### 3. トラブルシューティング

**[services/mailserver/troubleshoot/README.md](services/mailserver/troubleshoot/README.md)** - 問題発生時に必読

**内容**:
- 問題別クイックリファレンス
- 認証失敗対処（Dovecot SQL）
- メール受信失敗対処（relay_domains）
- 緊急対応フロー
- 診断コマンド一覧

---

## 🌐 ネットワーク構成

**現在の構成**: Dell/EC2ともにホストネットワークを直接使用

**KVM仮想ネットワーク（構築済み、現在未使用）**:

AWS VPC相当の5セグメント（libvirt type=nat + dnsmasq）:

| セグメント | CIDR | Gateway | 状態 |
|---------|------|---------|------|
| Management | 10.0.0.0/24 | 10.0.0.1 | 未使用 |
| Public | 10.0.1.0/24 | 10.0.1.1 | 未使用 |
| Private | 10.0.2.0/24 | 10.0.2.1 | 未使用 |
| Database | 10.0.3.0/24 | 10.0.3.1 | 未使用 |
| Container | 10.0.4.0/24 | 10.0.4.1 | 未使用 |

**注**: 将来的な仮想化用に構築済み。詳細: [docs/infra/README.md](docs/infra/README.md)

---

## 📂 リポジトリ構造

```
project-root-infra/
├── docs/
│   ├── infra/                    # インフラ構築ドキュメント
│   │   ├── README.md            # ★必読: インフラ全体ガイド
│   │   ├── procedures/          # Phase別手順書
│   │   └── *.md                 # 要件・設計ドキュメント
│   └── application/
│       └── mailserver/          # Mailserverドキュメント
│           ├── README.md        # ★必読: Mailserverガイド
│           ├── usermgmt/        # User Management (Phase 11/11-A)
│           └── *.md             # 仕様書
├── services/
│   └── mailserver/              # Mailserver実装
│       ├── README.md            # サービス構成とコマンド
│       ├── docker-compose.yml   # Docker Compose構成
│       ├── config/              # 設定ファイル
│       ├── usermgmt/            # Flask User Management App
│       ├── terraform/           # EC2 Terraform構成
│       └── troubleshoot/        # トラブルシューティング
│           └── README.md        # ★必読: 問題対処ガイド
├── CLAUDE.md                    # 本ファイル
└── README.md                    # プロジェクト概要
```

---

## 🔧 よく使うコマンド

**詳細は各README.mdを参照してください。ここには記載しません。**

- Docker操作 → [services/mailserver/README.md](services/mailserver/README.md)
- EC2診断 → [services/mailserver/troubleshoot/README.md](services/mailserver/troubleshoot/README.md)
- テスト実行 → [docs/application/mailserver/usermgmt/DEVELOPMENT.md](docs/application/mailserver/usermgmt/DEVELOPMENT.md)
- インフラ操作 → [docs/infra/README.md](docs/infra/README.md)

---

## 🔒 セキュリティ原則

- **SSH**: 公開鍵認証のみ、非標準ポート（2201-2280）、fail2ban保護
- **Docker**: SELinux enforcing、非root、自動セキュリティ更新
- **コンテナ**: デフォルト非特権、シークレット管理

詳細: 各サービスのREADME.md参照

---

## ⚠️ よくある落とし穴

| 問題 | 原因 | 対処先 |
|-----|------|--------|
| 認証失敗 | 認証情報混同（MYSQL_PASSWORD vs USERMGMT_DB_PASSWORD） | [troubleshoot/README.md](services/mailserver/troubleshoot/README.md) |
| メール受信失敗 | EC2の relay_domains未登録 | [troubleshoot/README.md](services/mailserver/troubleshoot/README.md) |
| Dockerコンテナ起動失敗 | ストレージ/パーミッション問題 | [docs/infra/README.md](docs/infra/README.md) |
| リソース枯渇 | メモリ/CPU/ディスク不足 | [docs/infra/README.md](docs/infra/README.md) |

詳細なトラブルシューティング: [services/mailserver/troubleshoot/README.md](services/mailserver/troubleshoot/README.md)

---

## 🌩️ 将来のAWS移行

- **Terraform**: Dockerリソース/インフラをTerraform構成化
- **AWS ECS/Fargate**: コンテナをAWSへ移行
- **段階的移行**: 開発(Dell) → ステージング(AWS) → 本番(Multi-AZ)

詳細: [docs/infra/README.md](docs/infra/README.md)

---

## 📝 AI生成手順書ガイドライン

本プロジェクトはAIツールで手順書を生成します：

- **人間レビュー必須**: 実行前に検証
- **バージョン管理**: Gitで追跡
- **フィードバックループ**: 実行結果を記録
- **安全性**: ロールバック手順必須

---

**Repository Nature**: ドキュメント駆動型インフラリポジトリ
**Main Deliverables**: 実行可能な手順書（Bashコマンド）
**Validation**: 実際のインフラ上での実行

**AGENTS.md Note**: AGENTS.mdは別プロジェクトの参照であり、本リポジトリとは無関係
