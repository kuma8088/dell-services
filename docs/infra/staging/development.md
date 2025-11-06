# Staging Environment Development Progress

**最終更新**: 2025-11-06
**現在フェーズ**: Phase 1 完了 → Phase 2 準備中

## 📊 構築フェーズ全体像

```
Phase 1: Dell Staging環境構築         ✅ 完了 (2025-11-06)
  ├─ 設定ファイル作成
  ├─ ディレクトリ作成
  ├─ Docker Compose起動
  └─ ログ確認・検証

Phase 2: EC2 Staging環境構築          🔲 未実施
  ├─ Terraform workspace作成
  ├─ EC2インスタンス起動
  ├─ Tailscale設定
  └─ Postfix MX Gateway設定

Phase 3: 統合テスト                    🔲 未実施
  ├─ Dell ↔ EC2 LMTP中継確認
  ├─ メール受信フロー検証
  └─ 認証・暗号化確認

Phase 4: 本番比較テスト                🔲 未実施
  ├─ 設定ファイル比較
  ├─ 動作差分検証
  └─ パフォーマンステスト
```

---

## Phase 1: Dell Staging環境構築 ✅

**実施日**: 2025-11-06
**担当**: Claude Code
**状態**: 完了

### 1.1 実施内容

#### 設定ファイル作成
- ✅ `docker-compose.staging.yml` - 本番オーバーレイ設定
- ✅ `config-staging/postfix/main.cf.tmpl` - 3層メール送信防御
- ✅ `config-staging/dovecot/dovecot.conf` - IMAP/POP3設定
- ✅ `config-staging/mariadb/readonly.cnf` - Read-Onlyモード
- ✅ `config-staging/nginx/nginx.conf` - リバースプロキシ
- ✅ `config-staging/rspamd/` - スパムフィルタ設定
- ✅ `config-staging/clamav/` - ウイルススキャン設定
- ✅ `config-staging/roundcube/` - Webメール設定
- ✅ `.env.staging` - 環境変数（独立パスワード）

#### ディレクトリ作成
```bash
data-staging/
  ├── mail/        # メールボックスデータ
  ├── db/          # MariaDBデータ
  ├── rspamd/      # Rspamdデータ
  └── clamav/      # ClamAVデータ

logs-staging/
  ├── postfix/
  ├── dovecot/
  ├── rspamd/
  ├── clamav/
  ├── roundcube/
  ├── nginx/
  └── usermgmt/
```

#### Docker Compose起動
```bash
docker compose -p staging \
  -f docker-compose.yml \
  -f docker-compose.staging.yml \
  --env-file .env.staging \
  up -d
```

**コンテナ状態**:
```
mailserver-staging-postfix     ✅ healthy
mailserver-staging-dovecot     ✅ healthy
mailserver-staging-nginx       ✅ healthy
mailserver-staging-roundcube   ✅ healthy
mailserver-staging-rspamd      ✅ healthy
mailserver-staging-usermgmt    ✅ healthy
mailserver-staging-mariadb     ✅ healthy
mailserver-staging-clamav      ✅ healthy
```

### 1.2 解決した技術課題

#### 課題1: Docker Composeポート競合

**問題**:
- 本番環境（993:993）とstaging環境（3993:993）のポートマッピングがマージされる
- Docker Composeの配列マージ動作により、両方のポートが割り当てられてエラー

**解決策**:
```yaml
# docker-compose.staging.yml
dovecot:
  ports: !override []  # YAMLタグで明示的に上書き
```

**効果**:
- ホストポート公開を完全に無効化
- 内部ネットワーク（172.21.0.0/24）のみでアクセス
- Tailscale/SSHトンネル経由で外部アクセス
- セキュリティ向上（攻撃面縮小）

#### 課題2: MariaDB `super_read_only` 非対応

**問題**:
- MariaDB 10.11.7は`super_read_only`パラメータ非対応
- `--super-read-only=ON`でコンテナが起動失敗

**解決策**:
```bash
# docker-compose.staging.yml
command:
  - --read-only=ON
  # super-read-only削除
```

```cnf
# config-staging/mariadb/readonly.cnf
read_only = 1
# super_read_only = 1  # 削除
```

**効果**:
- MariaDB正常起動
- Read-Onlyモード有効（データ変更防止）

#### 課題3: MariaDB設定ディレクトリ権限

**問題**:
- `/etc/mysql/conf.d/` に対する権限エラー
- 初期ディレクトリ作成時の権限が700（read-only）

**解決策**:
```bash
chmod -R 755 config-staging/mariadb/
```

**効果**:
- MariaDBコンテナが設定ファイルを読み込み可能
- 正常に初期化・起動

### 1.3 セキュリティ確認

#### 3層メール送信防止（Dell Staging）
```
Layer 1: Postfix transport設定
  default_transport = error:5.7.1 External delivery is disabled
  relay_transport = error:5.7.1 External relay is disabled
  → 最も強力な防御

Layer 2: SMTP認証無効化
  smtp_sasl_auth_enable = no
  → SendGrid認証を無効化

Layer 3: 無効なRelayhost
  POSTFIX_RELAYHOST=[127.0.0.1]:9999
  → 存在しないSMTPサーバー
```

#### Read-Onlyモード（MariaDB）
```
Layer 1: MySQL設定ファイル
  read_only = 1

Layer 2: コマンドラインフラグ
  --read-only=ON
```

### 1.4 ネットワークアクセス

#### 内部ネットワーク構成
| サービス | 内部IP | ポート | 用途 |
|---------|---------|--------|------|
| nginx | 172.21.0.10 | 80, 443 | リバースプロキシ |
| postfix | 172.21.0.20 | 2525, 587 | LMTP, Submission |
| dovecot | 172.21.0.30 | 2525, 993, 995 | LMTP, IMAPS, POP3S |
| roundcube | 172.21.0.40 | 80 | Webメール |
| mariadb | 172.21.0.60 | 3306 | データベース |
| rspamd | 172.21.0.70 | 11332-11334 | スパムフィルタ |
| clamav | 172.21.0.80 | 3310 | ウイルススキャン |
| usermgmt | 172.21.0.90 | 5000 | ユーザー管理 |

#### アクセス方法

**Dell ホストから直接**:
```bash
# MariaDB接続
mysql -h 172.21.0.60 -u root -pStagingRoot2024!

# Nginx HTTPアクセス
curl http://172.21.0.10/
```

**外部からSSHトンネル**:
```bash
# IMAPS（Dovecot 993）
ssh -L 3993:172.21.0.30:993 user@dell-workstation.tail67811d.ts.net

# Submission（Postfix 587）
ssh -L 3587:172.21.0.20:587 user@dell-workstation.tail67811d.ts.net

# メールクライアントで localhost:3993 に接続
```

**コンテナ内で直接操作**:
```bash
# Dovecotユーザー一覧
docker exec mailserver-staging-dovecot doveadm user '*'

# MariaDB接続
docker exec -it mailserver-staging-mariadb mysql -u root -pStagingRoot2024!

# Postfixキュー確認
docker exec mailserver-staging-postfix postqueue -p
```

### 1.5 次フェーズへの引き継ぎ事項

#### 完了タスク
- ✅ Docker Composeプロジェクト名分離（`-p staging`）
- ✅ 内部ネットワーク化（ポート競合解消）
- ✅ 3層メール送信防御の実装
- ✅ MariaDB Read-Onlyモード設定
- ✅ 全コンテナ起動確認（healthy状態）

#### 検証済み項目
- ✅ Postfix設定テンプレート適用
- ✅ Dovecot起動（IMAP/POP3デーモン）
- ✅ MariaDB初期化・read_only有効化
- ✅ Nginx設定テンプレート適用
- ✅ Usermgmt Gunicorn起動

#### Phase 2への前提条件
- ✅ Dell Staging環境が正常稼働中
- ✅ Tailscale接続が有効（100.110.222.53）
- ✅ Postfix LMTP受信ポート準備完了（内部2525）
- ⚠️ Phase 2でEC2からLMTP接続テスト必要

---

## Phase 2: EC2 Staging環境構築 🔲

**予定日**: TBD
**担当**: TBD
**状態**: 未実施

### 2.1 実施予定

#### Terraform Workspace作成
```bash
cd services/mailserver/terraform
terraform workspace new staging
terraform workspace select staging
```

#### 環境変数設定
- `.tfvars.staging` 作成
- EC2インスタンスタイプ: t3.micro（本番: t3.small）
- セキュリティグループ: staging専用
- Elastic IP: 新規割り当て

#### Terraformリソース作成
```bash
terraform plan -var-file=.tfvars.staging
terraform apply -var-file=.tfvars.staging
```

**作成リソース**:
- EC2インスタンス: `mailserver-mx-staging`
- Elastic IP: staging専用
- セキュリティグループ: SMTP(25), SSH, Tailscale許可
- IAMロール: CloudWatch Logs書き込み

#### EC2初期設定
```bash
# SSHアクセス
ssh -i ~/.ssh/mailserver-staging.pem ec2-user@<staging-eip>

# Tailscaleインストール・認証
curl -fsSL https://tailscale.com/install.sh | sh
sudo tailscale up --authkey=<staging-key>

# Docker/Docker Composeインストール
sudo yum update -y
sudo yum install -y docker
sudo systemctl start docker
sudo systemctl enable docker
```

#### Postfix MX Gateway設定
- `relay_domains` にstaging用ドメイン追加
- `relay_transport = lmtp:[100.110.222.53]:2525` を内部IP変更
  - Dell Staging LMTP: `172.21.0.20:2525`（Tailscale経由）
- SendGrid設定を無効化（staging環境）

### 2.2 前提条件

#### 必要な情報
- [ ] AWS credentials（staging用IAMユーザー）
- [ ] Tailscale authkey（staging用）
- [ ] staging用ドメイン/サブドメイン設定
- [ ] SSH鍵ペア（staging専用）

#### 確認事項
- [ ] Dell Staging環境が稼働中
- [ ] Tailscale mesh networkにDell追加済み
- [ ] Phase 1で作成した内部ネットワークIP確認

### 2.3 期待される成果物

- [ ] EC2インスタンス起動確認
- [ ] Tailscale接続確認（Dell ↔ EC2 Staging）
- [ ] Postfix MX Gateway起動確認
- [ ] Port 25受信可能確認
- [ ] relay_domains設定確認

---

## Phase 3: 統合テスト 🔲

**予定日**: Phase 2完了後
**担当**: TBD
**状態**: 未実施

### 3.1 テストシナリオ

#### 3.1.1 SMTP → LMTP中継テスト

**目的**: EC2 Staging → Dell Staging へのメール中継確認

**手順**:
```bash
# EC2 Stagingから送信
echo "Test mail from EC2 staging" | mail -s "LMTP Test" test@kuma8088.com

# Dell Stagingで受信確認
docker exec mailserver-staging-dovecot doveadm mailbox status -u test@kuma8088.com messages INBOX
```

**期待結果**:
- EC2 Postfix → Dell Postfix（LMTP 2525）
- Dell Dovecot受信トレイに配信
- ログに配信記録

#### 3.1.2 認証テスト

**目的**: Dovecot SQL認証動作確認

**手順**:
```bash
# メールクライアントでIMAP接続
# Host: localhost, Port: 3993 (SSHトンネル経由)
# User: test@kuma8088.com
# Pass: <from usermgmt DB>
```

**期待結果**:
- 認証成功
- INBOXフォルダ表示
- メール一覧取得可能

#### 3.1.3 Read-Only確認

**目的**: MariaDB書き込み防止確認

**手順**:
```bash
# MariaDB接続
docker exec -it mailserver-staging-mariadb mysql -u root -pStagingRoot2024!

# 書き込み試行
USE mailserver_usermgmt_staging;
INSERT INTO users (email, password) VALUES ('test@example.com', 'test');
```

**期待結果**:
- `ERROR 1290 (HY000): The MariaDB server is running with the --read-only option`
- データ変更不可

#### 3.1.4 外部送信防止確認

**目的**: 3層防御が機能していることを確認

**手順**:
```bash
# Dell Stagingから外部メール送信試行
docker exec mailserver-staging-postfix \
  sendmail -f test@kuma8088.com -t external@gmail.com \
  <<< "Subject: Test\n\nTest message"
```

**期待結果**:
- Layer 1: `5.7.1 External delivery is disabled` エラー
- メールキューに残らない
- 外部に送信されない

### 3.2 トラブルシューティング

#### LMTP接続失敗
```bash
# Tailscale接続確認
sudo tailscale status

# Dell Staging Postfixログ確認
docker logs mailserver-staging-postfix

# ファイアウォール確認（Dell）
sudo firewall-cmd --list-all
```

#### 認証失敗
```bash
# Dovecot認証ログ確認
docker logs mailserver-staging-dovecot | grep -i auth

# MariaDB usermgmtテーブル確認
docker exec -it mailserver-staging-mariadb \
  mysql -u root -pStagingRoot2024! \
  -e "SELECT email FROM mailserver_usermgmt_staging.users;"
```

---

## Phase 4: 本番比較テスト 🔲

**予定日**: Phase 3完了後
**担当**: TBD
**状態**: 未実施

### 4.1 設定ファイル比較

#### Postfix設定差分
```bash
# 本番
cat config/postfix/main.cf.tmpl

# Staging
cat config-staging/postfix/main.cf.tmpl

# 差分確認
diff -u config/postfix/main.cf.tmpl config-staging/postfix/main.cf.tmpl
```

**期待される差分**:
- `default_transport` / `relay_transport`（staging: error）
- `mynetworks`（staging: 172.21.0.0/24）
- `smtp_sasl_auth_enable`（staging: no）

#### Dovecot設定差分
```bash
diff -u config/dovecot/dovecot.conf config-staging/dovecot/dovecot.conf
```

**期待される差分**:
- リスニングアドレス（本番: 0.0.0.0, staging: 172.21.0.30）
- データディレクトリパス

### 4.2 動作比較

#### メール配信フロー
```
本番:
  Internet (Port 25)
  → EC2 Prod Postfix
  → Tailscale (LMTP 2525)
  → Dell Prod Postfix
  → Dell Prod Dovecot

Staging:
  EC2 Staging Postfix (手動送信)
  → Tailscale (LMTP 2525)
  → Dell Staging Postfix
  → Dell Staging Dovecot
```

#### パフォーマンス比較
```bash
# 本番環境
time docker exec mailserver-dovecot doveadm user '*'

# Staging環境
time docker exec mailserver-staging-dovecot doveadm user '*'
```

### 4.3 検証項目チェックリスト

- [ ] Postfix設定の整合性
- [ ] Dovecot設定の整合性
- [ ] MariaDBスキーマの整合性
- [ ] Rspamd/ClamAV設定の整合性
- [ ] Nginx設定の整合性
- [ ] TLS証明書の有効性（Tailscale証明書）
- [ ] ログローテーション設定
- [ ] リソース制限（CPU/Memory）

---

## 📝 開発ログ

### 2025-11-06: Phase 1 完了

**実施者**: Claude Code
**作業時間**: 約2時間

#### タイムライン
1. **設定ファイル作成** (30分)
   - docker-compose.staging.yml作成
   - config-staging/ 配下の各種設定ファイル作成
   - .env.staging作成

2. **ディレクトリ作成** (5分)
   - data-staging/配下4ディレクトリ
   - logs-staging/配下7ディレクトリ

3. **初回起動試行・失敗** (15分)
   - ポート競合エラー（993, 2525, 3306）
   - Docker Compose配列マージ動作を確認

4. **ポート競合解決** (30分)
   - `ports: !override []` 試行
   - docker-compose.staging.yml全サービス修正
   - architecture.md/env.staging更新

5. **MariaDB起動問題解決** (30分)
   - `super_read_only`非対応確認
   - readonly.cnf修正
   - ディレクトリ権限修正（755）

6. **最終起動・検証** (15分)
   - 全コンテナ正常起動確認
   - ヘルスチェック確認
   - ログ確認

#### 学んだこと
- Docker Composeの配列マージは`ports: []`では上書きできない
- `!override`タグが必要
- MariaDB 10.11.7は`super_read_only`非対応
- 設定ディレクトリの権限は755必須（MariaDBコンテナ）

#### 残課題
- MariaDB rootパスワードでのログインに失敗（権限設定要確認）
- ClamAVウイルス定義の初回ダウンロードに時間がかかる
- Roundcube初回アクセス時の初期化が必要

---

## 🚀 次のアクション

### 短期（Phase 2準備）
1. [ ] Terraform staging workspace作成
2. [ ] staging用`.tfvars`ファイル作成
3. [ ] Tailscale authkey取得（staging用）
4. [ ] AWS credentials確認（staging環境用）

### 中期（Phase 2-3実施）
1. [ ] EC2 Staging インスタンス起動
2. [ ] Tailscale設定・Dell接続確認
3. [ ] Postfix MX Gateway設定
4. [ ] LMTP中継テスト実施

### 長期（Phase 4実施・運用）
1. [ ] 本番比較テスト実施
2. [ ] パフォーマンスベンチマーク
3. [ ] ドキュメント最終化
4. [ ] CI/CDパイプライン統合

---

## 📚 参考ドキュメント

- [architecture.md](./architecture.md) - Staging環境設計書
- [setup-guide.md](./setup-guide.md) - セットアップ手順（Phase 1-2）
- [testing-guide.md](./testing-guide.md) - テスト・検証手順（Phase 3-4）
- [../../application/mailserver/README.md](../../application/mailserver/README.md) - Mailserver全体ドキュメント
- [../../../services/mailserver/troubleshoot/README.md](../../../services/mailserver/troubleshoot/README.md) - トラブルシューティング

---

## 🔄 変更履歴

| 日付 | フェーズ | 変更内容 | 担当 |
|------|---------|---------|------|
| 2025-11-06 | Phase 1 | Dell Staging環境構築完了 | Claude Code |
| 2025-11-06 | Phase 1 | development.md新規作成 | Claude Code |
