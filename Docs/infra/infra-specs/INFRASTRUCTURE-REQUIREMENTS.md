
for archive in "$BACKUP_DIR"/*.tar.gz; do
    volume_name=$(basename "$archive" .tar.gz)
    docker volume create "$volume_name"
    docker run --rm \
        -v "$volume_name":/data \
        -v "$BACKUP_DIR":/backup \
        alpine tar xzf "/backup/${volume_name}.tar.gz" -C /data
done
```
- 目標: 10分以内

**3. 完全インフラ再構築**
```bash
cd /data/terraform/environments/dev
terraform init
terraform apply
```
- 目標: 30分以内

---

## 10. 運用手順書

### 10.1 手順書の方針

**基本原則**:
- エンジニアがコマンドで実行できるレベルで記載
- テストスクリプトはClaude Code等で生成
- すべてGit管理下に配置
- 手順書は随時更新・改善

**手順書の配置**:
```
project-root-infra/Docs/procedures/
├── 01-initial-setup.md            # 初期セットアップ
├── 02-terraform-basics.md         # Terraform基本操作
├── 03-container-deployment.md     # コンテナデプロイ
├── 04-backup-restore.md           # バックアップ・リストア
├── 05-monitoring-setup.md         # 監視セットアップ
├── 06-vscode-remote-ssh.md        # VSCode Remote SSH設定
└── 07-troubleshooting.md          # トラブルシューティング
```

### 10.2 必須手順書リスト

| 手順書 | 概要 | 優先度 | 作成状況 |
|--------|------|--------|---------|
| **01-initial-setup.md** | 初期セットアップ（ディレクトリ作成、Terraform初期化） | 高 | 要作成 |
| **02-terraform-basics.md** | Terraform基本操作（plan, apply, destroy等） | 高 | 要作成 |
| **03-container-deployment.md** | コンテナデプロイ手順 | 高 | 要作成 |
| **04-backup-restore.md** | バックアップ・リストア手順 | 中 | 要作成 |
| **05-monitoring-setup.md** | 監視セットアップ手順 | 中 | 要作成 |
| **06-vscode-remote-ssh.md** | VSCode Remote SSH設定手順 | 中 | 要作成 |
| **07-troubleshooting.md** | トラブルシューティングガイド | 中 | 要作成 |

### 10.3 自動化スクリプト

#### 生成ツール
- **Claude Code**: テストスクリプト、統合テストスクリプト生成
- **GitHub Copilot**: 補助的なコード生成・補完

#### スクリプト構成

```bash
# scripts/setup/initial-setup.sh
#!/bin/bash
# 初期セットアップスクリプト
set -e

echo "=== Dell WorkStation 基盤 初期セットアップ ==="

# 1. ディレクトリ作成
echo "[1/5] ディレクトリ構造作成中..."
mkdir -p /data/{docker/volumes,terraform,backups,logs,ci-cd}

# 2. Terraform初期化
echo "[2/5] Terraform初期化中..."
cd /data/terraform/environments/dev
terraform init

# 3. Dockerネットワーク作成
echo "[3/5] Dockerネットワーク作成中..."
terraform apply -target=module.network -auto-approve

# 4. 監視スタックデプロイ
echo "[4/5] 監視スタックデプロイ中..."
terraform apply -target=module.monitoring -auto-approve

# 5. ヘルスチェック
echo "[5/5] ヘルスチェック実行中..."
/data/scripts/monitoring/health-check.sh

echo "=== セットアップ完了 ==="
```

#### テストスクリプト（Claude Code生成想定）

```bash
# scripts/test/network-test.sh
#!/bin/bash
# Dockerネットワーク疎通テスト
# 生成: Claude Code

echo "=== Dockerネットワーク疎通テスト ==="

# Managementネットワークテスト
docker run --rm --network management alpine ping -c 3 10.0.0.1

# Publicネットワークテスト
docker run --rm --network public alpine ping -c 3 10.0.1.1

# Privateネットワーク隔離テスト
docker run --rm --network private alpine ping -c 3 8.8.8.8 2>&1 | grep -q "Network is unreachable" && echo "PASS: Private network isolated" || echo "FAIL: Private network not isolated"

echo "=== テスト完了 ==="
```

---

## 11. CI/CDパイプライン

### 11.1 推奨ツール

**軽量構成（推奨）**:
- **Gitea** + **Gitea Actions**
  - GitHub Actions互換
  - リソース消費: 1コア、1GB
  - セルフホスト可能

**代替構成**:
- **GitLab CE**
  - フル機能（CI/CD、Container Registry等）
  - リソース消費: 2コア、4GB（重め）

### 11.2 パイプライン構成

```
MacBook Air M4 (VSCode Remote SSH)
    ↓ コード編集・Git Push
GitHub / Gitea
    ↓ Webhook
Dell WorkStation (CI/CD)
    ↓ Terraform Plan (自動)
    ↓ レビュー・承認
    ↓ Terraform Apply (手動 or 自動)
    ↓ テスト実行
Dell WorkStation (ステージング環境)
    ↓ 統合テスト
    ↓ 検証OK
AWS Fargate (本番環境) ※将来
```

### 11.3 CI/CDワークフロー例

```yaml
# .github/workflows/terraform.yml (参考)
name: Terraform CI/CD

on:
  push:
    branches: [main]
    paths:
      - 'terraform/**'
  pull_request:
    branches: [main]
    paths:
      - 'terraform/**'

jobs:
  terraform:
    runs-on: self-hosted  # Dell WorkStation
    steps:
      - uses: actions/checkout@v3
      
      - name: Terraform Format Check
        run: terraform fmt -check -recursive
        working-directory: terraform
      
      - name: Terraform Init
        run: terraform init
        working-directory: terraform/environments/dev
      
      - name: Terraform Validate
        run: terraform validate
        working-directory: terraform/environments/dev
      
      - name: Terraform Plan
        run: terraform plan -out=tfplan
        working-directory: terraform/environments/dev
      
      - name: Terraform Apply (on main branch only)
        if: github.ref == 'refs/heads/main'
        run: terraform apply -auto-approve tfplan
        working-directory: terraform/environments/dev
```

---

## 12. AWS移行を見据えた設計原則

### 12.1 12 Factor App の実践

| 原則 | 実装方針 | 確認方法 |
|------|---------|---------|
| **Codebase** | Git管理 | すべてのコードがGitHub管理下 |
| **Dependencies** | Dockerfile で明示 | requirements.txt, package.json等 |
| **Config** | 環境変数 | .env, terraform.tfvars |
| **Backing services** | 外部サービス化 | DB, Redis等をコンテナ分離 |
| **Build, release, run** | CI/CD分離 | Terraform + Docker |
| **Processes** | ステートレス | コンテナ再起動可能 |
| **Port binding** | コンテナポート公開 | Dockerネットワーク経由 |
| **Concurrency** | 水平スケール対応 | レプリカ数増減可能 |
| **Disposability** | 高速起動・停止 | < 10秒起動目標 |
| **Dev/prod parity** | 環境差異最小化 | 同一Dockerイメージ使用 |
| **Logs** | 標準出力 | docker logs で確認可能 |
| **Admin processes** | 一時コンテナで実行 | docker run --rm |

### 12.2 コンテナ最適化

**マルチステージビルド**
```dockerfile
FROM node:18 AS builder
WORKDIR /app
COPY package*.json ./
RUN npm ci --only=production
COPY . .
RUN npm run build

FROM node:18-alpine
WORKDIR /app
COPY --from=builder /app/dist ./dist
COPY --from=builder /app/node_modules ./node_modules
EXPOSE 3000
HEALTHCHECK --interval=30s --timeout=3s \
  CMD wget --no-verbose --tries=1 --spider http://localhost:3000/health || exit 1
CMD ["node", "dist/main.js"]
```

**ヘルスチェック実装**
```dockerfile
HEALTHCHECK --interval=30s --timeout=3s --start-period=40s --retries=3 \
  CMD curl -f http://localhost:3000/health || exit 1
```

**リソース制限（Terraform）**
```hcl
resource "docker_container" "app" {
  name  = "app"
  image = docker_image.app.image_id
  
  # リソース制限
  cpu_shares = 1024  # 相対値
  memory     = 2048  # MB
  
  # ヘルスチェック
  healthcheck {
    test     = ["CMD", "curl", "-f", "http://localhost:3000/health"]
    interval = "30s"
    timeout  = "3s"
    retries  = 3
  }
  
  # 再起動ポリシー
  restart = "unless-stopped"
}
```

---

## 13. 開発フロー

### 13.1 日常的な開発フロー

```
【朝の起動】
1. MacBook でVSCode起動
2. Remote SSH接続（Tailscale経由で自動接続）
   → Command Palette: "Remote-SSH: Connect to Host"
   → dell-workstation 選択

【開発作業】
3. Dell WorkStation上でコード編集
   - /data/terraform/ (インフラコード)
   - /data/docker/ (アプリケーションコード)

4. Terraform変更の場合
   $ cd /data/terraform/environments/dev
   $ terraform fmt
   $ terraform validate
   $ terraform plan
   $ terraform apply

5. 動作確認
   - Tailscale経由でブラウザアクセス
   - docker logs でログ確認
   - Grafanaダッシュボード確認

【コミット】
6. Git操作
   $ git add .
   $ git commit -m "feat: add new feature"
   $ git push origin main

【終業時】
7. VSCode接続切断（自動でOK）
```

### 13.2 環境の使い分け

| 環境 | 用途 | 実装場所 | データ分離 |
|------|------|---------|-----------|
| **開発環境** | 機能開発・検証 | Dell (dev) | /data/terraform/environments/dev |
| **ステージング** | 本番前検証 | Dell (staging) | /data/terraform/environments/staging |
| **本番環境** | サービス提供 | AWS Fargate | AWS (将来) |

### 13.3 Terraformワークフロー

```bash
# 【パターンA】新規リソース追加
cd /data/terraform/environments/dev
terraform plan -out=tfplan
# 確認後
terraform apply tfplan

# 【パターンB】既存リソース変更
terraform plan -target=module.monitoring
# 確認後
terraform apply -target=module.monitoring

# 【パターンC】リソース削除（慎重に！）
terraform plan -destroy -target=module.test
# 確認後
terraform destroy -target=module.test

# 【パターンD】状態確認
terraform state list
terraform state show docker_network.management
terraform show

# 【パターンE】リソースのインポート
terraform import docker_network.existing <network_id>
```

---

## 14. 運用手順

### 14.1 日次運用

```bash
# 1. ヘルスチェック
$ /data/scripts/monitoring/health-check.sh

# 2. リソース使用率確認
$ docker stats --no-stream
$ df -h /data

# 3. ログエラー確認
$ grep -i error /data/logs/**/*.log | tail -50
$ docker logs --tail 100 $(docker ps -q)

# 4. バックアップ成功確認
$ ls -lh /data/backups/daily/$(date +%Y%m%d)
```

### 14.2 週次運用

```bash
# 1. セキュリティアップデート
$ sudo dnf update -y
$ sudo reboot  # 必要に応じて

# 2. ディスククリーンアップ
$ docker system prune -a --volumes -f
$ find /data/logs -type f -mtime +30 -delete

# 3. パフォーマンスレビュー
$ docker stats --no-stream > /data/logs/weekly-stats-$(date +%Y%m%d).log
$ df -h /data > /data/logs/disk-usage-$(date +%Y%m%d).log

# 4. バックアップテスト
$ /data/scripts/backup/restore-test.sh
```

### 14.3 月次運用

```bash
# 1. 容量計画見直し
$ df -h /data
$ du -sh /data/docker/volumes/*

# 2. Terraformステート確認
$ cd /data/terraform/environments/dev
$ terraform state list | wc -l
$ terraform show > /data/logs/terraform-state-$(date +%Y%m).txt

# 3. ドキュメント更新
$ cd ~/Develop/project-root-infra
$ git status
$ git log --since="1 month ago" --oneline

# 4. DR（災害復旧）訓練
$ /data/scripts/test/disaster-recovery-drill.sh
```

---

## 15. 制約事項・前提条件

### 15.1 制約事項

| 制約 | 影響 | 受容理由 |
|------|------|---------|
| Dell WorkStationは単一障害点（SPOF） | 高 | 開発環境のため許容 |
| ハードウェア障害時のダウンタイム | 中 | 日次バックアップで復旧可能 |
| 本番レベルの冗長性なし | 低 | 本番はAWSで実現 |
| インターネット接続必須 | 中 | 外部依存最小化で緩和 |
| Terraformステート管理が単一ファイル | 低 | バックアップで対応 |

### 15.2 前提条件

| 項目 | 状態 | 確認方法 |
|------|------|---------|
| Rocky Linux 9.6正常動作 | ✅ | `cat /etc/redhat-release` |
| Docker動作確認 | ✅ | `docker --version` |
| Terraform動作確認 | ⬜ | `terraform --version` |
| Tailscale接続確立 | ✅ | `tailscale status` |
| 3.6TB データ領域利用可能 | ✅ | `df -h /data` |
| MacBook SSH接続可能 | ✅ | `ssh dell-workstation` |

### 15.3 リスクと対策

| リスク | 発生確率 | 影響度 | 対策 | 復旧時間目標 |
|--------|---------|--------|------|-------------|
| ハードウェア故障 | 低 | 高 | 日次バックアップ、復旧手順整備 | 4時間 |
| ディスク容量枯渇 | 中 | 中 | 監視アラート、自動クリーンアップ | 1時間 |
| ネットワーク障害 | 低 | 中 | Tailscale冗長性、外部依存最小化 | 30分 |
| Terraform設定ミス | 中 | 低 | Plan確認、Git管理、State バックアップ | 15分 |
| Docker Engine障害 | 低 | 中 | 自動再起動設定、監視アラート | 10分 |
| データ破損 | 低 | 高 | 日次バックアップ、複数世代保持 | 2時間 |

---

## 16. 次のステップ

### 16.1 フェーズ1: 基盤構築（現在）

**目標期間**: 1-2週間

- [ ] 要件定義書の承認（本ドキュメント）
- [ ] Terraformプロジェクト構造作成
- [ ] ディレクトリ構造の作成（Terraform管理）
- [ ] Dockerネットワークの構築（Terraform管理）
- [ ] 監視スタックのセットアップ
- [ ] 運用手順書の作成（7本）
- [ ] テストスクリプトの作成（Claude Code）

**完了条件**:
- Terraform apply で全リソース作成可能
- Grafanaダッシュボードで監視可能
- バックアップスクリプトが正常動作
- 手順書が整備されている

### 16.2 フェーズ2: ウェブメール開発

**目標期間**: 2-4週間

- [ ] ウェブメールサービスの要件定義（別プロジェクト）
- [ ] Dockerfile作成
- [ ] Terraformコード作成（コンテナ定義）
- [ ] デプロイテスト
- [ ] 動作確認・負荷テスト

**完了条件**:
- ウェブメールサービスが稼働
- Tailscale経由でアクセス可能
- メール送受信が正常動作

### 16.3 フェーズ3: ブログシステム

**目標期間**: 1-2週間

- [ ] 既存WordPressデータのエクスポート
- [ ] Dockerイメージ作成
- [ ] Terraformコード作成
- [ ] データ移行
- [ ] 動作確認

### 16.4 フェーズ4: 商用システム開発

**目標期間**: 個別に設定

- [ ] 学習システム
- [ ] メール配信システム
- [ ] マーケティングシステム
- [ ] 締切管理システム
- [ ] 統合システム

### 16.5 フェーズ5: AWS移行準備

**目標期間**: 本番稼働後6ヶ月以降

- [ ] AWS環境設計
- [ ] Terraformコード作成（AWS版）
- [ ] 段階的移行計画策定
- [ ] コスト試算
- [ ] 移行テスト

---

## 17. 付録

### 17.1 参考コマンド集

#### Terraform

```bash
# 初期化
terraform init
terraform init -upgrade  # Provider更新

# 計画・適用
terraform plan
terraform plan -out=tfplan
terraform apply
terraform apply tfplan
terraform apply -auto-approve

# 状態管理
terraform state list
terraform state show <resource>
terraform state mv <source> <destination>
terraform state rm <resource>

# リソース管理
terraform import <resource> <id>
terraform taint <resource>
terraform untaint <resource>

# その他
terraform fmt -recursive
terraform validate
terraform output
terraform graph | dot -Tpng > graph.png
```

#### Docker

```bash
# コンテナ管理
docker ps
docker ps -a
docker logs <container>
docker logs -f <container>  # follow
docker exec -it <container> /bin/sh
docker stop <container>
docker start <container>
docker restart <container>
docker rm <container>

# イメージ管理
docker images
docker pull <image>
docker build -t <tag> .
docker rmi <image>

# ネットワーク
docker network ls
docker network inspect <network>
docker network create <network>
docker network rm <network>

# ボリューム
docker volume ls
docker volume inspect <volume>
docker volume create <volume>
docker volume rm <volume>

# システム
docker system df
docker system prune -a
docker info
```

#### 監視・診断

```bash
# リソース監視
docker stats
docker stats --no-stream
top
htop
free -h
df -h

# ログ確認
journalctl -u docker
journalctl -f
tail -f /var/log/messages

# ネットワーク診断
ip addr
ip route
ss -tulpn
netstat -tulpn
ping <host>
traceroute <host>
```

### 17.2 トラブルシューティングFAQ

| 問題 | 原因 | 解決方法 |
|------|------|---------|
| Terraform applyが失敗 | Provider接続エラー | `docker ps` でDockerが起動しているか確認 |
| コンテナが起動しない | ポート競合 | `docker ps` で使用ポート確認 |
| ディスク容量不足 | ログ肥大化 | `docker system prune -a` |
| ネットワーク接続不可 | Tailscale切断 | `tailscale status` 確認・再接続 |
| VSCode接続エラー | SSH設定ミス | `~/.ssh/config` 確認 |

### 17.3 用語集

| 用語 | 説明 |
|------|------|
| **IaC** | Infrastructure as Code - インフラをコードで管理 |
| **Terraform** | HashiCorp製のIaCツール |
| **Tailscale** | WireGuardベースのVPNサービス |
| **12 Factor App** | モダンアプリケーション設計の12原則 |
| **Docker Compose** | 複数コンテナを定義・実行するツール |
| **Fargate** | AWSのサーバーレスコンテナ実行環境 |

---

## 18. 承認

| 役割 | 氏名 | 承認日 | 署名 |
|------|------|--------|------|
| プロジェクトオーナー | - | - | - |
| インフラ担当 | - | - | - |
| セキュリティレビュー | - | - | - |

---

**END OF DOCUMENT**
