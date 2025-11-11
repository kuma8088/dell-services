#!/bin/bash
# Nginx サブディレクトリサイト設定生成スクリプト
# 目的: kuma8088.conf の重複を解消し、保守性を向上
# 作成日: 2025-11-11

set -euo pipefail

# サブディレクトリサイト一覧
SITES=(
    "cameramanual"
    "elementordemo1"
    "elementordemo02"
    "elementor-demo-03"
    "elementor-demo-04"
    "ec02test"
    "test"
)

# 各サイト用の設定を生成
for site in "${SITES[@]}"; do
    # サイト名からコンテナ名を生成（ハイフンはそのまま）
    container_name="kuma8088-${site}"
    # named locationのためにハイフンをアンダースコアに変換
    location_name=$(echo "$site" | tr '-' '_')

    cat <<EOF
    # Subdirectory site: ${site}
    # Static files (wp-content, wp-includes)
    location ~ ^/${site}/(wp-content|wp-includes)/(.*)$ {
        alias /var/www/html/${container_name}/\$1/\$2;

        expires max;
        access_log off;
    }

    location /${site} {
        alias /var/www/html/${container_name};
        index index.php index.html;

        location ~ \\.php$ {
            include fastcgi_params;
            fastcgi_pass wordpress:9000;
            fastcgi_index index.php;
            fastcgi_param SCRIPT_FILENAME \$request_filename;
            fastcgi_param HTTPS on;
            fastcgi_param HTTP_X_FORWARDED_PROTO https;
        }

        try_files \$uri \$uri/ @${location_name};
    }

    location @${location_name} {
        rewrite /${site}/(.*)$ /${site}/index.php?/\$1 last;
    }

EOF
done

echo "# Generated on: $(date '+%Y-%m-%d %H:%M:%S')"
