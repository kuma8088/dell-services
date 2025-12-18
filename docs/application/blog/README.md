# ブログシステム構築プロジェクト

**作成者**: kuma8088（AWS認定ソリューションアーキテクト、ITストラテジスト）

Docker Compose環境で複数WordPress サイトをホスティングするプロジェクトドキュメント

---

## 📋 ドキュメント構成

| ドキュメント | 内容 |
|------------|------|
| [requirements.md](requirements.md) | 要件定義・トレードオフ分析 |
| [architecture.md](architecture.md) | システム設計・アーキテクチャ図 |
| [deployment.md](deployment.md) | デプロイ戦略・Docker Compose設定 |
| [operations.md](operations.md) | 運用設計・監視・バックアップ |

---

## 🛠️ 技術スタック

| カテゴリ | 技術 |
|---------|------|
| **構築環境** | Rocky Linux 9.6 |
| **コンテナ** | Docker, Docker Compose |
| **Web** | Nginx, WordPress, PHP-FPM |
| **DB** | MariaDB 10.11 |
| **Cache** | Redis |
| **クラウド** | Cloudflare (Tunnel, CDN, WAF) |
| **メール** | WP Mail SMTP + SendGrid |

---

## 🎯 Project Overview

### Objectives

**Primary Goal**: Host multiple WordPress sites on self-managed infrastructure with cost reduction and data sovereignty

**Technical Goals**:
- ✅ Docker Compose environment setup
- ✅ Cloudflare Tunnel integration (dynamic IP support)
- ✅ Co-existence with existing infrastructure
- 🔄 Integration with backup system (planned)

### Scope

**In Scope**:
- WordPress environment setup (Docker Compose) ✅ Complete
- Cloudflare Tunnel configuration ✅ Complete
- Data migration from existing hosting ✅ Complete
- Backup & restore functionality 📝 Planned

**Out of Scope**:
- Design changes
- New feature additions (to be considered after migration)
- Cloud migration (future phases)

---

## 🏗️ System Architecture

### Container Composition

```
blog_network (Docker Bridge)
├── wordpress (PHP-FPM 8.2 + wp-cli)
├── nginx (HTTP reverse proxy)
├── mariadb (10.11.7)
└── cloudflared (Cloudflare Tunnel)
```

### Network Flow

```
[User] → [Cloudflare Edge] → [Tunnel] → [nginx:8080] → [WordPress]
          ↓                    ↓
       DDoS protection    outbound-only connection
       SSL/TLS auto       (no port forwarding required)
       CDN
```

### Storage Design

| Data Type | Location | Device | Reason |
|-----------|----------|--------|--------|
| **MariaDB** | Docker volumes | SSD | High-performance DB |
| **Logs** | Docker volumes | SSD | Fast log writing |
| **WordPress files** | Data volume | HDD | Large media storage |
| **Backups** | Backup volume | HDD | Long-term storage |

---

## 📊 Technology Stack

| Layer | Technology | Version | Notes |
|-------|------------|---------|-------|
| **OS** | Linux | - | Server OS |
| **Container** | Docker + Compose | 24.0.x + 2.x | Container runtime |
| **Web Server** | Nginx | 1.26.3 | Reverse proxy |
| **Application** | WordPress | 6.4+ | CMS platform |
| **PHP** | PHP-FPM | 8.2.25 | WordPress recommended |
| **Database** | MariaDB | 10.11.7 | Relational database |
| **Tunnel** | cloudflared | latest | Cloudflare official |
| **SSL/TLS** | Cloudflare certificates | - | Auto-managed |

---

## 🚀 Current Status (Production Operation)

### ✅ Completed Work

1. **Docker Compose Environment**
   - 4-container composition (nginx, wordpress, mariadb, cloudflared)
   - Internal ports configured
   - Isolated network bridge

2. **Multi-Site WordPress Migration**
   - Multiple databases imported
   - Large file transfer completed (rsync)
   - Configuration files updated (wp-config.php)
   - URL replacement completed (thousands of replacements)

3. **Nginx Configuration**
   - Multiple virtual host configurations
   - Support for root domain and subdirectory sites
   - Alias configuration optimized

4. **Cloudflare Tunnel Configuration**
   - Public hostnames registered
   - HTTPS automatic certificate provisioning
   - DNS automatic configuration

5. **Operational Verification**
   - ✅ Sites operational
   - 🔒 Password-protected sites (as configured)
   - ⚠️ Known issues (documented below)

---

## ⚠️ Known Issues (Deferred Resolution)

### ✅ Resolved: Elementor Cache Issue
- **Symptom**: Images not displaying on pages (visible in Elementor editor)
- **Cause**: Elementor cache
- **Resolution**: ✅ Resolved via cache clearing

### ✅ Resolved: HTTPS Detection Issue
- **Symptom**: Elementor preview and static files (CSS/JS/images) not loading properly
- **Root Cause**: Missing Nginx HTTPS detection parameters → WordPress HTTP detection → mixed content errors
- **Solution**: Added `fastcgi_param HTTPS on;` and `HTTP_X_FORWARDED_PROTO https;` parameters
- **Result**: ✅ All sites operational, Elementor editing functionality restored

### PHP Compatibility Issues
- **Symptom**: HTTP 500 errors on specific sites
- **Cause**: Theme using deprecated `create_function()` (deprecated in PHP 7.2, removed in 8.0)
- **Resolution Options**:
  - Update theme code
  - Switch to alternative theme
- **Priority**: 🟡 MEDIUM

---

## 📂 Directory Structure (Implemented)

```
/path/to/blog/
├── docker-compose.yml        # Docker Compose definition
├── .env                       # Environment variables (Git ignored)
├── config/
│   ├── nginx/
│   │   ├── nginx.conf        # Nginx main configuration
│   │   └── conf.d/           # Virtual host configurations
│   ├── php/
│   │   └── php.ini           # PHP configuration
│   └── mariadb/
│       ├── my.cnf            # MariaDB configuration
│       └── init/
│           └── 01-create-databases.sql  # DB initialization SQL
└── (Data mounted from external volumes)
```

### Data Layout

```
/data/blog/
├── sites/                    # WordPress files
│   ├── site1/
│   ├── site2/
│   └── ... (all sites)
└── backups/                  # Backups (planned)
```

---

## 🔧 Operational Commands

### Docker Operations

```bash
cd /path/to/blog

# Check container status
docker compose ps

# Check logs
docker compose logs -f nginx
docker compose logs -f wordpress

# Restart services
docker compose restart nginx

# Container shell access
docker compose exec wordpress bash
docker compose exec nginx sh
```

### WordPress Operations

```bash
# wp-cli command execution
docker compose exec -T wordpress wp --help --allow-root

# Bulk URL replacement (example)
docker compose exec -T wordpress wp search-replace \
  "https://old-domain.com" "https://new-domain.com" \
  --path=/var/www/html/site-name \
  --allow-root \
  --skip-columns=guid
```

---

## 💾 Backup Specification (Planned)

### Backup Schedule (Planned)

| Type | Schedule | Retention | Destination |
|------|----------|-----------|-------------|
| **Daily** | AM 3:30 | 7 generations | Local backup volume |
| **Weekly** | Sunday AM 2:30 | 4 generations | Local backup volume |
| **S3 Sync** | AM 4:30 | 30 days | S3 bucket (future integration) |

### Backup Targets (Planned)

- WordPress databases (MariaDB dump) × multiple sites
- WordPress files (data volume)
- Nginx configuration
- Docker Compose configuration

---

## 🔒 Security Measures

### Implemented

- ✅ **Communication encryption**: Cloudflare certificates (HTTPS automatic)
- ✅ **Database**: Docker internal network only (non-public ports)
- ✅ **File permissions**: www-data ownership configured
- ✅ **Credential management**: `.env` file excluded from Git

### Future Measures (Planned)

- [ ] **WordPress admin**: IP restriction or basic authentication
- [ ] **Regular updates**: WordPress/plugin monthly updates
- [ ] **Backup**: Daily automatic backup

---

## 📈 Performance Requirements

| Item | Target | Current Status |
|------|--------|----------------|
| **Page load time** | < 3 seconds | ✅ Verified |
| **Concurrent users** | 10-50 users | Initial estimate |
| **Uptime** | > 99% (monthly) | Monitoring planned |
| **DB response** | < 100ms | High-speed via SSD |

---

## ⚠️ Infrastructure Co-existence

### Resource Allocation

| Item | Service A | Service B | Total | Status |
|------|-----------|-----------|-------|--------|
| **RAM** | ~11GB | ~4GB | 15GB / 32GB | ✅ Sufficient |
| **SSD** | [Service A] | 20GB | - / 390GB | ✅ Sufficient |
| **HDD** | <1GB | 95GB | ~96GB / 3.4TB | ✅ Sufficient |

### Port Conflict Avoidance

| Service | Port A | Port B | Conflict |
|---------|--------|--------|----------|
| **Nginx HTTP** | - | 8080 (internal) | ✅ Avoided |
| **Nginx HTTPS** | 443 (external) | Tunnel-based | ✅ Avoided |
| **MariaDB** | 3306 (internal) | 3307 (internal) | ✅ Avoided |

### Docker Networks

- **Service A**: `network_a`
- **Service B**: `blog_network` (newly created)
- ✅ Network isolation complete

---

## 📝 Migration Process

### ✅ Phase A-1: Bulk Migration (Complete)

**Implementation**:
1. ✅ WordPress database backup & import for multiple sites
2. ✅ WordPress files transfer (large volume rsync)
3. ✅ wp-config.php batch update (database connection settings)
4. ✅ URL batch replacement (thousands of replacements)
5. ✅ Nginx configuration (multiple sites)
6. ✅ Cloudflare Tunnel configuration (multiple public hostnames)
7. ✅ Operational verification (sites operational)

### 📝 Phase A-2: Backup System Setup (Planned)

1. [ ] Backup script creation
2. [ ] Restore script creation
3. [ ] Cron automation configuration
4. [ ] S3 integration consideration

### 📝 Phase B: Production Readiness (Planned)

1. [ ] Known issue resolution (Elementor, PHP compatibility)
2. [ ] Monitoring & alerting setup
3. [ ] Operations manual creation

### 📝 Phase C: Parallel Operation (Planned)

1. [ ] 2-week parallel operation
2. [ ] Performance monitoring
3. [ ] Issue resolution

---

## 📞 Reference Information

### Technical Reference Links

**WordPress Official**:
- [WordPress Requirements](https://wordpress.org/about/requirements/)
- [Installing WordPress](https://wordpress.org/support/article/how-to-install-wordpress/)

**Docker Official**:
- [Docker Hub - WordPress](https://hub.docker.com/_/wordpress)
- [Docker Hub - MariaDB](https://hub.docker.com/_/mariadb)

**Cloudflare Tunnel Official**:
- [Cloudflare Tunnel Documentation](https://developers.cloudflare.com/cloudflare-one/connections/connect-networks/)

---

## 🆘 Troubleshooting

### WordPress Access Issues

```bash
# Check container status
cd /path/to/blog
docker compose ps

# Check Nginx logs
docker compose logs nginx | tail -50

# Check Cloudflare Tunnel logs
docker compose logs cloudflared | tail -50
```

### Database Connection Errors

```bash
# Check MariaDB logs
docker compose logs mariadb | tail -50

# Verify WordPress configuration
docker compose exec wordpress cat /var/www/html/site-name/wp-config.php | grep DB_
```

### Image Display Issues

```bash
# Check permissions
docker compose exec wordpress ls -la /var/www/html/site-name/wp-content/uploads/

# Check ownership
docker compose exec wordpress stat -c "%u:%g %a %n" /var/www/html/site-name/wp-config.php
# Expected: www-data ownership
```

---

**Version**: 3.0 (Sanitized Public Version)
**Current Phase**: Production operation

