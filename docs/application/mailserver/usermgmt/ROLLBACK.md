# Mailserver Usermgmt Rollback Procedures

**Phase 9: Production Deployment Preparation**

## 📋 Overview

This document provides comprehensive rollback procedures for the mailserver usermgmt system in case of deployment issues or production incidents.

**Risk Levels**:
- 🟢 **Low**: Configuration changes only, no data migration
- 🟡 **Medium**: Service restarts required, potential brief downtime
- 🔴 **High**: Database changes, potential data loss risk

---

## 🚨 Emergency Rollback (Quick Reference)

**If you need to rollback immediately**, execute these commands:

```bash
cd /opt/onprem-infra-system/project-root-infra/services/mailserver

# 1. Stop all services
docker compose down

# 2. Restore configurations
cp docker-compose.yml.phase8.backup docker-compose.yml
cp .env.phase8.backup .env

# 3. Restart services
docker compose up -d

# 4. Verify services
docker compose ps
docker compose logs -f usermgmt
```

**Validation**: Verify email send/receive functionality and web interface access.

---

## 📦 Rollback Procedures by Component

### 1. Docker Compose Configuration Rollback

**Scenario**: Issues with docker-compose.yml changes
**Risk Level**: 🟡 Medium (requires service restart)
**Downtime**: 10-30 seconds

```bash
# Navigate to project directory
cd /opt/onprem-infra-system/project-root-infra/services/mailserver

# Stop services
docker compose down

# Restore backup
cp docker-compose.yml.phase8.backup docker-compose.yml

# Restart services
docker compose up -d

# Verify
docker compose ps
```

**Validation Checklist**:
- [ ] All containers running: `docker compose ps`
- [ ] No restart loops: `docker compose logs -f`
- [ ] Healthchecks passing: `docker inspect mailserver-usermgmt | jq '.[0].State.Health'`

---

### 2. Environment Variables Rollback

**Scenario**: Issues with .env configuration
**Risk Level**: 🟡 Medium (requires service restart)
**Downtime**: 10-30 seconds

```bash
cd /opt/onprem-infra-system/project-root-infra/services/mailserver

# Stop affected service
docker compose stop usermgmt

# Restore .env
cp .env.phase8.backup .env

# Restart service
docker compose up -d usermgmt

# Verify
docker compose logs -f usermgmt
```

**Validation Checklist**:
- [ ] Usermgmt container running
- [ ] Database connection successful (check logs)
- [ ] Web interface accessible: `curl http://localhost:5000/health`

---

### 3. Usermgmt Application Code Rollback

**Scenario**: Issues with usermgmt application code
**Risk Level**: 🟡 Medium (requires rebuild)
**Downtime**: 1-2 minutes

```bash
cd /opt/onprem-infra-system/project-root-infra/services/mailserver

# Restore from backup (if backup exists)
BACKUP_FILE="/opt/backups/mailserver/latest/config/usermgmt_app.tar.gz"

if [[ -f "${BACKUP_FILE}" ]]; then
    # Extract backup
    tar -xzf "${BACKUP_FILE}" -C ./

    # Rebuild container
    docker compose build usermgmt
    docker compose up -d usermgmt
else
    # Revert to specific git commit (example)
    cd usermgmt
    git checkout <previous-commit-hash>
    cd ..

    docker compose build usermgmt
    docker compose up -d usermgmt
fi

# Verify
docker compose logs -f usermgmt
```

**Validation Checklist**:
- [ ] Container rebuilt successfully
- [ ] Application starts without errors
- [ ] Login functionality works
- [ ] User CRUD operations functional

---

### 4. Database Schema Rollback

**Scenario**: Database migration issues
**Risk Level**: 🔴 High (data integrity risk)
**Downtime**: 5-10 minutes

⚠️ **WARNING**: Always create database backup before schema changes!

```bash
cd /opt/onprem-infra-system/project-root-infra/services/mailserver

# 1. Stop usermgmt service
docker compose stop usermgmt

# 2. Restore database from backup
BACKUP_FILE="/opt/backups/mailserver/latest/database/mailserver_usermgmt.sql.gz"

if [[ -f "${BACKUP_FILE}" ]]; then
    # Restore database
    gunzip -c "${BACKUP_FILE}" | \
        docker exec -i mailserver-mariadb mysql \
            -u root \
            -p"${MYSQL_ROOT_PASSWORD}" \
            mailserver_usermgmt
else
    echo "ERROR: Database backup not found!"
    exit 1
fi

# 3. Restart usermgmt
docker compose up -d usermgmt

# 4. Verify
docker compose logs -f usermgmt
```

**Validation Checklist**:
- [ ] Database restored successfully
- [ ] Usermgmt connects to database
- [ ] Existing users can login
- [ ] User list displays correctly

---

### 5. Full System Rollback (All Components)

**Scenario**: Complete system failure or critical issues
**Risk Level**: 🔴 High (full system restore)
**Downtime**: 10-15 minutes

```bash
cd /opt/onprem-infra-system/project-root-infra/services/mailserver

# 1. Stop all services
docker compose down

# 2. Restore all configurations
cp docker-compose.yml.phase8.backup docker-compose.yml
cp .env.phase8.backup .env

# 3. Restore database
BACKUP_DIR="/opt/backups/mailserver/latest"

# Restore mailserver_usermgmt database
gunzip -c "${BACKUP_DIR}/database/mailserver_usermgmt.sql.gz" | \
    docker exec -i mailserver-mariadb mysql \
        -u root \
        -p"${MYSQL_ROOT_PASSWORD}" \
        mailserver_usermgmt

# Restore roundcube database (if needed)
gunzip -c "${BACKUP_DIR}/database/roundcube.sql.gz" | \
    docker exec -i mailserver-mariadb mysql \
        -u root \
        -p"${MYSQL_ROOT_PASSWORD}" \
        roundcube

# 4. Restore configurations
tar -xzf "${BACKUP_DIR}/config/dovecot_config.tar.gz" -C ./config
tar -xzf "${BACKUP_DIR}/config/postfix_config.tar.gz" -C ./config
tar -xzf "${BACKUP_DIR}/config/nginx_config.tar.gz" -C ./config
tar -xzf "${BACKUP_DIR}/config/usermgmt_app.tar.gz" -C ./

# 5. Rebuild usermgmt container
docker compose build usermgmt

# 6. Start all services
docker compose up -d

# 7. Monitor startup
docker compose logs -f
```

**Validation Checklist**:
- [ ] All containers running: `docker compose ps`
- [ ] No errors in logs: `docker compose logs`
- [ ] Email send/receive working
- [ ] Webmail accessible
- [ ] Usermgmt web interface accessible
- [ ] User authentication working

---

## 🔍 Troubleshooting Common Issues

### Issue: Usermgmt Container Fails to Start

**Symptoms**:
```
mailserver-usermgmt | Error: Unable to connect to database
mailserver-usermgmt | sqlalchemy.exc.OperationalError: (2003, "Can't connect to MySQL server")
```

**Solution**:
```bash
# 1. Check MariaDB is running
docker compose ps mariadb

# 2. Verify database credentials in .env
grep USERMGMT_DB_ .env

# 3. Test database connection
docker exec -it mailserver-mariadb mysql \
    -u usermgmt \
    -p"${USERMGMT_DB_PASSWORD}" \
    -h 172.20.0.60 \
    mailserver_usermgmt

# 4. If connection fails, restore .env
cp .env.phase8.backup .env
docker compose restart usermgmt
```

---

### Issue: Nginx Cannot Proxy to Usermgmt

**Symptoms**:
```
nginx | 502 Bad Gateway
nginx | upstream: "http://172.20.0.90:5000" failed
```

**Solution**:
```bash
# 1. Check usermgmt is running and healthy
docker inspect mailserver-usermgmt | jq '.[0].State'

# 2. Verify network connectivity
docker exec mailserver-nginx ping -c 3 172.20.0.90

# 3. Check usermgmt healthcheck endpoint
docker exec mailserver-nginx curl http://172.20.0.90:5000/health

# 4. If healthcheck fails, check usermgmt logs
docker compose logs usermgmt

# 5. Restart usermgmt
docker compose restart usermgmt
```

---

### Issue: Database Migration Failures

**Symptoms**:
```
alembic.util.exc.CommandError: Can't locate revision identified by 'abc123'
```

**Solution**:
```bash
# 1. Stop usermgmt
docker compose stop usermgmt

# 2. Restore database from backup (see Database Schema Rollback above)

# 3. Reset alembic migration state (if needed)
docker exec -it mailserver-mariadb mysql \
    -u root \
    -p"${MYSQL_ROOT_PASSWORD}" \
    mailserver_usermgmt \
    -e "DROP TABLE IF EXISTS alembic_version;"

# 4. Restart usermgmt (will reinitialize schema)
docker compose up -d usermgmt
```

---

## 📊 Post-Rollback Validation

After completing any rollback procedure, execute this comprehensive validation:

```bash
#!/bin/bash
# Post-Rollback Validation Script

cd /opt/onprem-infra-system/project-root-infra/services/mailserver

echo "=== Container Status ==="
docker compose ps

echo -e "\n=== Healthcheck Status ==="
for service in mariadb postfix dovecot roundcube usermgmt nginx; do
    echo "Checking ${service}..."
    docker inspect "mailserver-${service}" | \
        jq '.[0].State.Health.Status' || echo "No healthcheck"
done

echo -e "\n=== Database Connectivity ==="
docker exec mailserver-mariadb mysql \
    -u usermgmt \
    -p"${USERMGMT_DB_PASSWORD}" \
    -e "SELECT COUNT(*) FROM users;" \
    mailserver_usermgmt

echo -e "\n=== Usermgmt Web Interface ==="
curl -s http://localhost/usermgmt/auth/login | grep -q "login" && \
    echo "✓ Usermgmt accessible" || \
    echo "✗ Usermgmt NOT accessible"

echo -e "\n=== Roundcube Web Interface ==="
curl -s http://localhost/ | grep -q "Roundcube" && \
    echo "✓ Roundcube accessible" || \
    echo "✗ Roundcube NOT accessible"

echo -e "\n=== Email Service Ports ==="
nc -zv localhost 587 2>&1 | grep -q succeeded && echo "✓ SMTP (587) listening" || echo "✗ SMTP NOT listening"
nc -zv localhost 993 2>&1 | grep -q succeeded && echo "✓ IMAPS (993) listening" || echo "✗ IMAPS NOT listening"
nc -zv localhost 995 2>&1 | grep -q succeeded && echo "✓ POP3S (995) listening" || echo "✗ POP3S NOT listening"
```

**Expected Results**:
- ✓ All containers in "Up" state
- ✓ All healthchecks "healthy"
- ✓ Database query returns user count
- ✓ Usermgmt web interface accessible
- ✓ Roundcube web interface accessible
- ✓ All email ports listening

---

## 🔐 Backup Before Changes

**CRITICAL**: Always create backups before making changes!

```bash
# Quick backup before changes
cd /opt/onprem-infra-system/project-root-infra/services/mailserver

# Run backup script
./scripts/backup-mailserver.sh

# Or manual backup
cp docker-compose.yml docker-compose.yml.backup.$(date +%Y%m%d_%H%M%S)
cp .env .env.backup.$(date +%Y%m%d_%H%M%S)
```

---

## 📞 Escalation Path

If rollback procedures fail:

1. **Check Backup Integrity**: Verify backup files exist and are not corrupted
   ```bash
   ls -lh /opt/backups/mailserver/latest/
   gunzip -t /opt/backups/mailserver/latest/database/*.sql.gz
   ```

2. **Review Logs**: Comprehensive log analysis
   ```bash
   docker compose logs --tail=100 > /tmp/mailserver_error_logs.txt
   ```

3. **Consult Documentation**: Review DEVELOPMENT.md phases for context

4. **Disaster Recovery**: If all else fails, restore from external backup or rebuild from scratch using DEVELOPMENT.md phases

---

## 📚 Related Documentation

- [DEVELOPMENT.md](DEVELOPMENT.md) - Development phases and implementation details
- [README.md](README.md) - Architecture and setup overview
- [Backup Script](../../services/mailserver/scripts/backup-mailserver.sh) - Automated backup script

---

**Document Version**: 1.0
**Last Updated**: 2025-11-05
**Phase**: Phase 9 - Production Deployment Preparation
