# MariaDB Staging環境設定

## 概要

Staging環境のMariaDBは**read-onlyモード**で稼働します。本番DBからのデータコピーによりデータを取得し、読み取り専用として動作します。

## ファイル構成

```
config-staging/mariadb/
├── readonly.cnf          # Read-Only設定とパフォーマンス最適化
└── README.md            # 本ファイル
```

## Read-Onlyモードの仕組み

### 設定内容

`readonly.cnf`で以下の設定を有効化：

```ini
read_only = 1
super_read_only = 1
```

- **`read_only`**: 通常ユーザーによる書き込みを禁止
- **`super_read_only`**: rootを含むすべてのユーザーによる書き込みを禁止

### データコピー方法

本番DBからstaging DBへのデータコピーは以下の手順で実行：

```bash
# 1. 本番DBからダンプ取得
docker exec mailserver-mariadb mysqldump \
  -u root -p \
  --databases roundcube_mailserver mailserver_usermgmt \
  > /tmp/production_dump.sql

# 2. Staging DBへ一時的にread-onlyを無効化してインポート
docker exec -i mailserver-staging-mariadb mysql \
  -u root -pStagingRoot2024! \
  -e "SET GLOBAL read_only=OFF; SET GLOBAL super_read_only=OFF;"

docker exec -i mailserver-staging-mariadb mysql \
  -u root -pStagingRoot2024! \
  < /tmp/production_dump.sql

# 3. Read-onlyモードを再有効化
docker exec -i mailserver-staging-mariadb mysql \
  -u root -pStagingRoot2024! \
  -e "SET GLOBAL read_only=ON; SET GLOBAL super_read_only=ON;"

# 4. データベース名変更（staging専用名へ）
docker exec -i mailserver-staging-mariadb mysql \
  -u root -pStagingRoot2024! \
  -e "RENAME TABLE roundcube_mailserver.* TO roundcube_mailserver_staging.*;"

docker exec -i mailserver-staging-mariadb mysql \
  -u root -pStagingRoot2024! \
  -e "RENAME TABLE mailserver_usermgmt.* TO mailserver_usermgmt_staging.*;"
```

## 定期データ同期

Staging環境のデータを定期的に更新する場合は、上記のコピー手順をcronジョブとして設定：

```bash
# crontabエントリ例（毎日午前3時に実行）
0 3 * * * /opt/onprem-infra-system/project-root-infra/services/mailserver/scripts/sync-staging-db.sh
```

## トラブルシューティング

### Read-Onlyエラーが発生する場合

```sql
ERROR 1290 (HY000): The MariaDB server is running with the --read-only option so it cannot execute this statement
```

**原因**: Read-Onlyモードが有効なため、データ変更が禁止されています。

**対処**: これはstagingの正常な動作です。データ変更が必要な場合は本番環境で実行してください。

### データコピーが失敗する場合

1. **権限確認**:
   ```bash
   docker exec mailserver-staging-mariadb mysql -u root -pStagingRoot2024! -e "SHOW GRANTS;"
   ```

2. **Read-Only状態確認**:
   ```bash
   docker exec mailserver-staging-mariadb mysql -u root -pStagingRoot2024! -e "SHOW VARIABLES LIKE 'read_only';"
   docker exec mailserver-staging-mariadb mysql -u root -pStagingRoot2024! -e "SHOW VARIABLES LIKE 'super_read_only';"
   ```

3. **一時的にread-onlyを無効化してリトライ**（前述の手順を参照）

## セキュリティノート

- Read-Onlyモードは**第2層防御**として機能します
- 第1層: Postfixの無効なrelayhost設定
- 第3層: sasl_passwdの無効な認証情報

これにより、staging環境からの誤った本番データ変更やメール送信を防止します。
