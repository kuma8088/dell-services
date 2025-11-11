# WP Mail SMTP Setup Guide

**Purpose**: Install and configure WP Mail SMTP plugin for all 16 WordPress sites with domain-specific email addresses

**Author**: Claude Code
**Date**: 2025-11-11
**Status**: Ready for execution

---

## 📋 Overview

This guide provides step-by-step instructions for deploying WP Mail SMTP plugin to all 16 WordPress sites in the blog system. Each site will be configured with:

- **SMTP relay**: dell-workstation.tail67811d.ts.net:587 (TLS)
- **Domain-specific from addresses**: noreply@{domain}
- **No authentication**: Internal trusted relay
- **Automatic backup**: Settings backed up before changes

---

## 🎯 Objectives

1. Install WP Mail SMTP plugin on all 16 sites
2. Configure domain-specific sender addresses
3. Eliminate spam/deliverability issues
4. Enable DKIM/SPF validation via Postfix relay

---

## 📊 Site Configuration Matrix

| Site Path | Domain | From Email |
|-----------|--------|------------|
| fx-trader-life | fx-trader-life.com | noreply@fx-trader-life.com |
| fx-trader-life-4line | fx-trader-life.com/4line | noreply@fx-trader-life.com |
| fx-trader-life-lp | fx-trader-life.com/lp | noreply@fx-trader-life.com |
| fx-trader-life-mfkc | mfkc.fx-trader-life.com | noreply@fx-trader-life.com |
| kuma8088 | kuma8088.com | noreply@kuma8088.com |
| kuma8088-cameramanual | blog.kuma8088.com/cameramanual | noreply@kuma8088.com |
| kuma8088-ec02test | blog.kuma8088.com/ec02test | noreply@kuma8088.com |
| kuma8088-elementordemo02 | blog.kuma8088.com/elementordemo02 | noreply@kuma8088.com |
| kuma8088-elementor-demo-03 | blog.kuma8088.com/elementor-demo-03 | noreply@kuma8088.com |
| kuma8088-elementor-demo-04 | blog.kuma8088.com/elementor-demo-04 | noreply@kuma8088.com |
| kuma8088-elementordemo1 | demo1.kuma8088.com | noreply@kuma8088.com |
| kuma8088-test | blog.kuma8088.com/test | noreply@kuma8088.com |
| toyota-phv | toyota-phv.com | noreply@toyota-phv.com |
| webmakeprofit | webmakeprofit.com | noreply@webmakeprofit.com |
| webmakeprofit-coconala | webmakeprofit.com/coconala | noreply@webmakeprofit.com |
| webmakesprofit | webmakesprofit.com | noreply@webmakesprofit.com |

---

## 🚀 Execution Steps

### Step 1: Pre-execution Checks

```bash
# Navigate to blog service directory
cd /opt/onprem-infra-system/project-root-infra/services/blog

# Verify Docker containers are running
docker compose ps

# Expected output: wordpress, nginx, mariadb, cloudflared all "Up"
```

### Step 2: Dry-Run (Recommended First)

```bash
# Run in dry-run mode to preview changes
./scripts/setup-wp-mail-smtp.sh --dry-run
```

**Expected output**:
- Preflight checks pass
- Shows what would be done for each site
- No actual changes made

### Step 3: Execute Setup

```bash
# Execute the actual setup
./scripts/setup-wp-mail-smtp.sh
```

**What happens**:
1. Preflight checks (Docker, wp-cli availability)
2. For each site:
   - Backup current WP Mail SMTP settings to `~/.wp-mail-smtp-backups/`
   - Install `wp-mail-smtp` plugin if not present
   - Activate the plugin
   - Configure SMTP settings via wp-cli
   - Verify configuration
3. Display summary report

**Duration**: ~5-10 minutes for 16 sites

### Step 4: Verify Configuration

```bash
# Verify all sites are configured correctly
./scripts/setup-wp-mail-smtp.sh --verify
```

**Expected output**:
- Shows current configuration for each site
- Validates from_email matches expected domain
- Validates SMTP host/port settings

### Step 5: Send Test Emails

```bash
# Send test emails from all sites
./scripts/setup-wp-mail-smtp.sh --test-email naoya.iimura@gmail.com
```

**What happens**:
- Sends test email from each site
- Uses WordPress `wp_mail()` function
- Logs success/failure for each site

**Important**: Check your inbox (and spam folder) for 16 test emails

---

## 📁 Files and Locations

### Script Location
```
/opt/onprem-infra-system/project-root-infra/services/blog/scripts/setup-wp-mail-smtp.sh
```

### Log Files
```
~/.wp-mail-smtp-setup.log          # Detailed execution log
~/.wp-mail-smtp-backups/           # Backup directory for settings
```

### Configuration Files
```
services/blog/docker-compose.yml   # WordPress container definition
```

---

## 🔍 Verification Checklist

After execution, verify:

- [ ] All 16 sites show plugin as "Active" in WordPress admin
- [ ] `--verify` command shows correct from_email for each site
- [ ] Test emails received successfully
- [ ] Test emails show correct sender (noreply@domain)
- [ ] Email headers show proper DKIM/SPF authentication
- [ ] No errors in log file

---

## 🛠️ Troubleshooting

### Issue: Plugin installation fails

**Symptoms**:
```
Error: Could not create directory.
```

**Solution**:
```bash
# Check file permissions in WordPress container
docker compose exec wordpress ls -la /var/www/html/wp-content/plugins/

# Fix permissions if needed
docker compose exec wordpress chown -R www-data:www-data /var/www/html/wp-content/plugins/
```

### Issue: wp-cli command fails

**Symptoms**:
```
Error: Error establishing a database connection
```

**Solution**:
```bash
# Verify MariaDB container is running
docker compose ps mariadb

# Check database connectivity
docker compose exec wordpress wp db check --allow-root
```

### Issue: Configuration not saving

**Symptoms**:
- Configuration appears to save but `--verify` shows old settings

**Solution**:
```bash
# Check WordPress option directly
docker compose exec wordpress wp option get wp_mail_smtp --format=json --allow-root --url=https://demo1.kuma8088.com

# Force update if needed
docker compose exec wordpress wp option update wp_mail_smtp '{"mail":{"from_email":"noreply@kuma8088.com",...}}' --format=json --allow-root --url=https://demo1.kuma8088.com
```

### Issue: Test emails not received

**Symptoms**:
- Script reports success but no emails arrive

**Solution**:
```bash
# Check Postfix logs on host
docker compose -f /opt/onprem-infra-system/project-root-infra/services/mailserver/docker-compose.yml logs -f postfix

# Check WordPress container logs
docker compose logs -f wordpress

# Verify ssmtp configuration
docker compose exec wordpress cat /etc/ssmtp/ssmtp.conf
```

---

## 📊 SMTP Configuration Details

All sites use the following SMTP configuration:

```json
{
  "mail": {
    "from_email": "noreply@{domain}",
    "from_name": "WordPress Notification",
    "mailer": "smtp",
    "return_path": true
  },
  "smtp": {
    "host": "dell-workstation.tail67811d.ts.net",
    "port": 587,
    "encryption": "tls",
    "autotls": true,
    "auth": false
  }
}
```

**Rationale**:
- **No authentication**: Postfix on dell-workstation uses mynetworks trust
- **Port 587**: Standard submission port with STARTTLS
- **return_path: true**: Enable bounce handling

---

## 🔄 Rollback Procedure

If issues arise, rollback to previous configuration:

```bash
# List available backups
ls -lah ~/.wp-mail-smtp-backups/

# Identify backup to restore (format: {site}_{timestamp}.json)
BACKUP_FILE=~/.wp-mail-smtp-backups/demo1.kuma8088.com_20251111_120000.json

# Restore configuration
docker compose exec wordpress wp option update wp_mail_smtp "$(cat $BACKUP_FILE)" --format=json --allow-root --url=https://demo1.kuma8088.com

# Verify restoration
./scripts/setup-wp-mail-smtp.sh --verify
```

---

## 📈 Success Criteria

The setup is considered successful when:

1. ✅ All 16 sites have WP Mail SMTP plugin active
2. ✅ Each site configured with correct domain-specific from_email
3. ✅ SMTP host set to dell-workstation.tail67811d.ts.net:587
4. ✅ Test emails sent successfully from all sites
5. ✅ Test emails received with proper DKIM/SPF headers
6. ✅ No errors in setup log file

---

## 🔗 Related Documentation

- [Blog System README](../README.md)
- [WordPress SMTP Integration](../phases/PHASE-A1-COMPLETION-REPORT.md)
- [Mailserver Configuration](../../mailserver/README.md)

---

## 📝 Notes

- **Current Status**: demo1.kuma8088.com already configured with noreply@kuma8088.com (as of Phase A-1)
- **Remaining Sites**: 15 sites need configuration update
- **PHP Compatibility**: Some sites may have PHP 8.x incompatibility warnings (safe to ignore for this operation)
- **Execution Time**: Allow 2 seconds per site for plugin installation and configuration

---

## ✅ Post-Deployment Actions

After successful deployment:

1. Monitor email deliverability for 24-48 hours
2. Check spam folder rates
3. Verify DKIM/SPF authentication in email headers
4. Update documentation if any issues encountered
5. Commit changes to Git repository
6. Notify stakeholders of completion

---

**Last Updated**: 2025-11-11
**Next Review**: After first production deployment
