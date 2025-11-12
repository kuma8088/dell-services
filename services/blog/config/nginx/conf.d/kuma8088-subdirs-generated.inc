    # Redirect /cameramanual to https://camera.kuma8088.com
    location ^~ /cameramanual {
        return 301 https://camera.kuma8088.com;
    }

    # Redirect /elementordemo02 to https://demo2.kuma8088.com
    location ^~ /elementordemo02 {
        return 301 https://demo2.kuma8088.com;
    }

    # Redirect /elementor-demo-03 to https://demo3.kuma8088.com
    location ^~ /elementor-demo-03 {
        return 301 https://demo3.kuma8088.com;
    }

    # Redirect /elementor-demo-04 to https://demo4.kuma8088.com
    location ^~ /elementor-demo-04 {
        return 301 https://demo4.kuma8088.com;
    }

    # Redirect /ec02test to https://ec-test.kuma8088.com
    location ^~ /ec02test {
        return 301 https://ec-test.kuma8088.com;
    }

    # Redirect /test remains served locally (legacy)
    location ~ ^/test/(wp-content|wp-includes)/(.*)$ {
        alias /var/www/html/kuma8088-test/$1/$2;

        expires max;
        access_log off;
    }

    location /test {
        alias /var/www/html/kuma8088-test;
        index index.php index.html;

        location ~ \.php$ {
            include fastcgi_params;
            fastcgi_pass wordpress:9000;
            fastcgi_index index.php;
            fastcgi_param SCRIPT_FILENAME $request_filename;
            fastcgi_param HTTPS on;
            fastcgi_param HTTP_X_FORWARDED_PROTO https;
        }

        try_files $uri $uri/ @test;
    }

    location @test {
        rewrite /test/(.*)$ /test/index.php?/$1 last;
    }

# Generated on: 2025-11-12 02:39:00
