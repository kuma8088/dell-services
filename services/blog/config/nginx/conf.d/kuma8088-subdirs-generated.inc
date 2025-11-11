    # Subdirectory site: cameramanual
    # Static files (wp-content, wp-includes)
    location ~ ^/cameramanual/(wp-content|wp-includes)/(.*)$ {
        alias /var/www/html/kuma8088-cameramanual/$1/$2;

        expires max;
        access_log off;
    }

    location /cameramanual {
        alias /var/www/html/kuma8088-cameramanual;
        index index.php index.html;

        location ~ \.php$ {
            include fastcgi_params;
            fastcgi_pass wordpress:9000;
            fastcgi_index index.php;
            fastcgi_param SCRIPT_FILENAME $request_filename;
            fastcgi_param HTTPS on;
            fastcgi_param HTTP_X_FORWARDED_PROTO https;
        }

        try_files $uri $uri/ @cameramanual;
    }

    location @cameramanual {
        rewrite /cameramanual/(.*)$ /cameramanual/index.php?/$1 last;
    }

    # Subdirectory site: elementordemo1
    # Static files (wp-content, wp-includes)
    location ~ ^/elementordemo1/(wp-content|wp-includes)/(.*)$ {
        alias /var/www/html/kuma8088-elementordemo1/$1/$2;

        expires max;
        access_log off;
    }

    location /elementordemo1 {
        alias /var/www/html/kuma8088-elementordemo1;
        index index.php index.html;

        location ~ \.php$ {
            include fastcgi_params;
            fastcgi_pass wordpress:9000;
            fastcgi_index index.php;
            fastcgi_param SCRIPT_FILENAME $request_filename;
            fastcgi_param HTTPS on;
            fastcgi_param HTTP_X_FORWARDED_PROTO https;
        }

        try_files $uri $uri/ @elementordemo1;
    }

    location @elementordemo1 {
        rewrite /elementordemo1/(.*)$ /elementordemo1/index.php?/$1 last;
    }

    # Subdirectory site: elementordemo02
    # Static files (wp-content, wp-includes)
    location ~ ^/elementordemo02/(wp-content|wp-includes)/(.*)$ {
        alias /var/www/html/kuma8088-elementordemo02/$1/$2;

        expires max;
        access_log off;
    }

    location /elementordemo02 {
        alias /var/www/html/kuma8088-elementordemo02;
        index index.php index.html;

        location ~ \.php$ {
            include fastcgi_params;
            fastcgi_pass wordpress:9000;
            fastcgi_index index.php;
            fastcgi_param SCRIPT_FILENAME $request_filename;
            fastcgi_param HTTPS on;
            fastcgi_param HTTP_X_FORWARDED_PROTO https;
        }

        try_files $uri $uri/ @elementordemo02;
    }

    location @elementordemo02 {
        rewrite /elementordemo02/(.*)$ /elementordemo02/index.php?/$1 last;
    }

    # Subdirectory site: elementor-demo-03
    # Static files (wp-content, wp-includes)
    location ~ ^/elementor-demo-03/(wp-content|wp-includes)/(.*)$ {
        alias /var/www/html/kuma8088-elementor-demo-03/$1/$2;

        expires max;
        access_log off;
    }

    location /elementor-demo-03 {
        alias /var/www/html/kuma8088-elementor-demo-03;
        index index.php index.html;

        location ~ \.php$ {
            include fastcgi_params;
            fastcgi_pass wordpress:9000;
            fastcgi_index index.php;
            fastcgi_param SCRIPT_FILENAME $request_filename;
            fastcgi_param HTTPS on;
            fastcgi_param HTTP_X_FORWARDED_PROTO https;
        }

        try_files $uri $uri/ @elementor_demo_03;
    }

    location @elementor_demo_03 {
        rewrite /elementor-demo-03/(.*)$ /elementor-demo-03/index.php?/$1 last;
    }

    # Subdirectory site: elementor-demo-04
    # Static files (wp-content, wp-includes)
    location ~ ^/elementor-demo-04/(wp-content|wp-includes)/(.*)$ {
        alias /var/www/html/kuma8088-elementor-demo-04/$1/$2;

        expires max;
        access_log off;
    }

    location /elementor-demo-04 {
        alias /var/www/html/kuma8088-elementor-demo-04;
        index index.php index.html;

        location ~ \.php$ {
            include fastcgi_params;
            fastcgi_pass wordpress:9000;
            fastcgi_index index.php;
            fastcgi_param SCRIPT_FILENAME $request_filename;
            fastcgi_param HTTPS on;
            fastcgi_param HTTP_X_FORWARDED_PROTO https;
        }

        try_files $uri $uri/ @elementor_demo_04;
    }

    location @elementor_demo_04 {
        rewrite /elementor-demo-04/(.*)$ /elementor-demo-04/index.php?/$1 last;
    }

    # Subdirectory site: ec02test
    # Static files (wp-content, wp-includes)
    location ~ ^/ec02test/(wp-content|wp-includes)/(.*)$ {
        alias /var/www/html/kuma8088-ec02test/$1/$2;

        expires max;
        access_log off;
    }

    location /ec02test {
        alias /var/www/html/kuma8088-ec02test;
        index index.php index.html;

        location ~ \.php$ {
            include fastcgi_params;
            fastcgi_pass wordpress:9000;
            fastcgi_index index.php;
            fastcgi_param SCRIPT_FILENAME $request_filename;
            fastcgi_param HTTPS on;
            fastcgi_param HTTP_X_FORWARDED_PROTO https;
        }

        try_files $uri $uri/ @ec02test;
    }

    location @ec02test {
        rewrite /ec02test/(.*)$ /ec02test/index.php?/$1 last;
    }

    # Subdirectory site: test
    # Static files (wp-content, wp-includes)
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

# Generated on: 2025-11-11 16:16:23
