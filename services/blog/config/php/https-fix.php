<?php
/**
 * HTTPS detection for Cloudflare reverse proxy
 * This file is auto-prepended to all PHP scripts via php.ini
 *
 * Cloudflare sends X-Forwarded-Proto header to indicate HTTPS
 * Without this, WordPress thinks it's HTTP and causes mixed content errors
 */

if (isset($_SERVER['HTTP_X_FORWARDED_PROTO']) && $_SERVER['HTTP_X_FORWARDED_PROTO'] === 'https') {
    $_SERVER['HTTPS'] = 'on';
    $_SERVER['SERVER_PORT'] = 443;
}

if (isset($_SERVER['HTTP_X_FORWARDED_HOST'])) {
    $_SERVER['HTTP_HOST'] = $_SERVER['HTTP_X_FORWARDED_HOST'];
}
