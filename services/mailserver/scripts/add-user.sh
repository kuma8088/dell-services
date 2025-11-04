#!/bin/bash
# メールユーザー追加スクリプト

EMAIL=$1
PASSWORD=$2

if [ -z "$EMAIL" ] || [ -z "$PASSWORD" ]; then
    echo "Usage: $0 <email> <password>"
    exit 1
fi

DOMAIN=$(echo $EMAIL | cut -d@ -f2)
USER=$(echo $EMAIL | cut -d@ -f1)

# Dovecot users ファイルにユーザー追加
HASH=$(docker run --rm -it dovecot/dovecot doveadm pw -s SHA512-CRYPT -p $PASSWORD | tr -d '\r')
echo "$EMAIL:$HASH:5000:5000::/var/mail/vhosts/$DOMAIN/$USER::" \
  >> /opt/onprem-infra-system/project-root-infra/services/mailserver/config/dovecot/users

# メールディレクトリ作成
mkdir -p /opt/onprem-infra-system/project-root-infra/services/mailserver/data/mail/$DOMAIN/$USER/{cur,new,tmp}
chown -R 5000:5000 /opt/onprem-infra-system/project-root-infra/services/mailserver/data/mail/$DOMAIN/$USER

# サービス再起動
docker compose restart dovecot postfix

echo "User $EMAIL added successfully"