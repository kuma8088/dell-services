# WP Mail SMTP Setup - Quick Start Guide

**For Dell WorkStation Execution Only**

---

## 🚀 Quick Start (5 minutes)

### Step 1: Navigate to Blog Directory

```bash
cd /opt/onprem-infra-system/project-root-infra/services/blog
```

### Step 2: Verify Prerequisites

```bash
# Check Docker containers
docker compose ps

# Expected: wordpress, nginx, mariadb, cloudflared all "Up"
```

### Step 3: Dry-Run (Preview Changes)

```bash
./scripts/setup-wp-mail-smtp.sh --dry-run
```

### Step 4: Execute Setup

```bash
./scripts/setup-wp-mail-smtp.sh
```

**Duration**: ~5-10 minutes

### Step 5: Verify Configuration

```bash
# Quick status check
./scripts/check-wp-mail-smtp.sh

# Expected output:
#   Installed: 16/16
#   Active:    16/16
#   Configured correctly: 16/16
```

### Step 6: Send Test Emails

```bash
./scripts/setup-wp-mail-smtp.sh --test-email naoya.iimura@gmail.com
```

**Check your inbox for 16 test emails** (may take 5 minutes)

---

## ✅ Success Indicators

- ✓ All sites show "✓" for Installed and Active
- ✓ All sites display correct noreply@{domain} email
- ✓ Test emails received with proper sender
- ✓ No errors in `~/.wp-mail-smtp-setup.log`

---

## 🔍 Quick Commands

```bash
# Status overview
./scripts/check-wp-mail-smtp.sh

# Detailed view
./scripts/check-wp-mail-smtp.sh --detailed

# JSON output (for scripting)
./scripts/check-wp-mail-smtp.sh --json

# View setup log
tail -f ~/.wp-mail-smtp-setup.log

# List backups
ls -lah ~/.wp-mail-smtp-backups/
```

---

## 🆘 Quick Troubleshooting

### Plugin installation fails
```bash
docker compose exec wordpress chown -R www-data:www-data /var/www/html/wp-content/plugins/
```

### Test emails not received
```bash
# Check Postfix logs
docker compose -f /opt/onprem-infra-system/project-root-infra/services/mailserver/docker-compose.yml logs -f postfix
```

### Need to rollback a site
```bash
# Find backup
ls ~/.wp-mail-smtp-backups/ | grep "demo1.kuma8088"

# Restore (replace {timestamp} with actual value)
docker compose exec wordpress wp option update wp_mail_smtp "$(cat ~/.wp-mail-smtp-backups/demo1.kuma8088.com_{timestamp}.json)" --format=json --allow-root --url=https://demo1.kuma8088.com
```

---

## 📚 Full Documentation

For detailed documentation, see:
- [Full Setup Guide](../../../docs/application/blog/guides/WP-MAIL-SMTP-SETUP.md)
- [Blog README](../../../docs/application/blog/README.md)

---

**Last Updated**: 2025-11-11
