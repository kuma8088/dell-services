# 管理ポータル統合設計 - WP Mail SMTP自動設定

**Purpose**: 管理ポータル開発時のWordPressサイト作成フローとWP Mail SMTP自動設定の統合設計

**Author**: Claude Code
**Date**: 2025-11-11
**Status**: Design Phase (実装は将来)

---

## 📋 Overview

管理ポータル開発時に、新規WordPressサイト作成フローにWP Mail SMTP設定を自動的に組み込む設計。手動設定を排除し、設定漏れを防ぐ。

---

## 🎯 Goals

### Primary Goal
新規WordPressサイト作成時に、WP Mail SMTP設定を**完全自動化**し、オペレーターが設定を忘れることを防ぐ

### Secondary Goals
1. 既存サイトの設定管理機能
2. SMTP設定のテンプレート管理
3. メール配信テスト機能の統合
4. 設定変更履歴の記録

---

## 🏗️ Architecture

### System Components

```
┌─────────────────────────────────────────────────────────────┐
│                    管理ポータル (Flask/React)                 │
├─────────────────────────────────────────────────────────────┤
│                                                             │
│  ┌──────────────────┐      ┌─────────────────────────┐    │
│  │ Site Management  │      │  SMTP Config Manager    │    │
│  │    API           │◄────►│                         │    │
│  │  /api/sites      │      │  - Template Engine      │    │
│  └──────────────────┘      │  - Auto Configuration   │    │
│         │                  │  - Test Sender          │    │
│         ▼                  └─────────────────────────┘    │
│  ┌──────────────────┐                                     │
│  │ Provisioning     │                                     │
│  │    Engine        │                                     │
│  │                  │                                     │
│  │ 1. Create DB     │                                     │
│  │ 2. Install WP    │                                     │
│  │ 3. Config SMTP   │◄─── ★ 自動実行ポイント              │
│  │ 4. Setup Nginx   │                                     │
│  │ 5. Config CF     │                                     │
│  └──────────────────┘                                     │
│         │                                                 │
│         ▼                                                 │
│  ┌──────────────────┐                                     │
│  │ Execution Layer  │                                     │
│  │  - wp-cli        │                                     │
│  │  - Docker API    │                                     │
│  │  - File Manager  │                                     │
│  └──────────────────┘                                     │
└─────────────────────────────────────────────────────────────┘
         │
         ▼
┌─────────────────────────────────────────────────────────────┐
│              WordPress Docker Environment                   │
└─────────────────────────────────────────────────────────────┘
```

---

## 📡 API Design

### 1. Site Creation API

**Endpoint**: `POST /api/sites`

**Request**:
```json
{
  "site_path": "kuma8088-new-site",
  "domain": "blog.kuma8088.com/new-site",
  "site_title": "New Site Title",
  "admin_user": "admin",
  "admin_password": "secure_password",
  "admin_email": "admin@example.com",
  "smtp_config": {
    "from_email": "noreply@kuma8088.com",
    "from_name": "WordPress Notification",
    "smtp_host": "dell-workstation.tail67811d.ts.net",
    "smtp_port": 587,
    "auto_detect_domain": true  // true の場合、domainから自動検出
  }
}
```

**Response**:
```json
{
  "status": "success",
  "site_id": "kuma8088-new-site",
  "url": "https://blog.kuma8088.com/new-site",
  "provisioning_steps": {
    "database": "completed",
    "wordpress": "completed",
    "smtp_plugin": "completed",
    "smtp_config": "completed",
    "nginx": "pending",
    "cloudflare": "pending"
  },
  "smtp_status": {
    "plugin_installed": true,
    "plugin_active": true,
    "configured": true,
    "from_email": "noreply@kuma8088.com"
  }
}
```

### 2. SMTP Configuration API

**Endpoint**: `PUT /api/sites/{site_id}/smtp`

**Request**:
```json
{
  "from_email": "noreply@kuma8088.com",
  "from_name": "WordPress Notification",
  "smtp_host": "dell-workstation.tail67811d.ts.net",
  "smtp_port": 587
}
```

**Response**:
```json
{
  "status": "success",
  "site_id": "kuma8088-new-site",
  "smtp_config": {
    "from_email": "noreply@kuma8088.com",
    "smtp_host": "dell-workstation.tail67811d.ts.net",
    "smtp_port": 587,
    "updated_at": "2025-11-11T12:00:00Z"
  }
}
```

### 3. SMTP Test Email API

**Endpoint**: `POST /api/sites/{site_id}/smtp/test`

**Request**:
```json
{
  "to_email": "test@example.com",
  "subject": "Test Email",
  "message": "This is a test email"
}
```

**Response**:
```json
{
  "status": "success",
  "sent": true,
  "timestamp": "2025-11-11T12:00:00Z",
  "smtp_log": "250 OK: queued as ABC123"
}
```

### 4. Bulk SMTP Configuration API

**Endpoint**: `POST /api/sites/smtp/bulk-configure`

**Request**:
```json
{
  "site_ids": ["site1", "site2", "site3"],
  "smtp_config": {
    "smtp_host": "dell-workstation.tail67811d.ts.net",
    "smtp_port": 587
  }
}
```

**Response**:
```json
{
  "status": "success",
  "total": 3,
  "success": 3,
  "failed": 0,
  "results": [
    {"site_id": "site1", "status": "success"},
    {"site_id": "site2", "status": "success"},
    {"site_id": "site3", "status": "success"}
  ]
}
```

---

## 🗃️ Database Schema

### sites テーブル

```sql
CREATE TABLE sites (
    id VARCHAR(255) PRIMARY KEY,
    site_path VARCHAR(255) UNIQUE NOT NULL,
    domain VARCHAR(255) NOT NULL,
    site_title VARCHAR(255),
    db_name VARCHAR(255) NOT NULL,
    db_prefix VARCHAR(50) NOT NULL,
    status ENUM('provisioning', 'active', 'disabled') DEFAULT 'provisioning',
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,
    INDEX idx_status (status),
    INDEX idx_created_at (created_at)
);
```

### smtp_configs テーブル

```sql
CREATE TABLE smtp_configs (
    id INT AUTO_INCREMENT PRIMARY KEY,
    site_id VARCHAR(255) NOT NULL,
    from_email VARCHAR(255) NOT NULL,
    from_name VARCHAR(255) DEFAULT 'WordPress Notification',
    smtp_host VARCHAR(255) NOT NULL,
    smtp_port INT NOT NULL DEFAULT 587,
    encryption ENUM('none', 'ssl', 'tls') DEFAULT 'tls',
    auth_required BOOLEAN DEFAULT FALSE,
    configured_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,
    FOREIGN KEY (site_id) REFERENCES sites(id) ON DELETE CASCADE,
    INDEX idx_site_id (site_id)
);
```

### smtp_test_logs テーブル

```sql
CREATE TABLE smtp_test_logs (
    id INT AUTO_INCREMENT PRIMARY KEY,
    site_id VARCHAR(255) NOT NULL,
    to_email VARCHAR(255) NOT NULL,
    status ENUM('success', 'failed') NOT NULL,
    error_message TEXT,
    tested_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    FOREIGN KEY (site_id) REFERENCES sites(id) ON DELETE CASCADE,
    INDEX idx_site_id (site_id),
    INDEX idx_tested_at (tested_at)
);
```

---

## 💻 Implementation Plan

### Phase 1: Core API Implementation

**Duration**: 2-3 days

**Tasks**:
1. Implement Site Creation API
2. Implement SMTP Configuration API
3. Add database migrations
4. Write unit tests

**Deliverables**:
- REST API endpoints
- Database schema
- API documentation

### Phase 2: Provisioning Engine

**Duration**: 3-4 days

**Tasks**:
1. Develop provisioning workflow
2. Integrate wp-cli commands
3. Add error handling and rollback
4. Implement progress tracking

**Deliverables**:
- Provisioning engine
- Rollback mechanism
- Status monitoring

### Phase 3: Frontend Integration

**Duration**: 2-3 days

**Tasks**:
1. Create site creation form
2. Add SMTP configuration UI
3. Implement test email sender
4. Add status dashboard

**Deliverables**:
- React components
- Form validation
- Status visualization

### Phase 4: Testing & Documentation

**Duration**: 2 days

**Tasks**:
1. Integration testing
2. User acceptance testing
3. Documentation
4. Training materials

**Deliverables**:
- Test reports
- User guide
- API documentation

---

## 🔧 Implementation Details

### SMTP Configuration Template

**Location**: `services/blog/config/smtp-templates/`

**Template Format** (YAML):
```yaml
templates:
  - name: "kuma8088-domain"
    pattern: "*.kuma8088.com"
    from_email: "noreply@kuma8088.com"
    smtp_host: "dell-workstation.tail67811d.ts.net"
    smtp_port: 587

  - name: "fx-trader-life-domain"
    pattern: "*.fx-trader-life.com"
    from_email: "noreply@fx-trader-life.com"
    smtp_host: "dell-workstation.tail67811d.ts.net"
    smtp_port: 587

  - name: "default"
    pattern: "*"
    from_email: "noreply@{base_domain}"
    smtp_host: "dell-workstation.tail67811d.ts.net"
    smtp_port: 587
```

### Auto-Detection Logic

```python
def detect_smtp_config(domain: str) -> dict:
    """
    ドメインから適切なSMTP設定を自動検出

    Examples:
        blog.kuma8088.com/test -> noreply@kuma8088.com
        new-site.com           -> noreply@new-site.com
    """
    # Extract base domain
    domain_only = domain.split('/')[0]
    parts = domain_only.split('.')
    base_domain = '.'.join(parts[-2:]) if len(parts) >= 2 else domain_only

    # Load templates
    templates = load_smtp_templates()

    # Match pattern
    for template in templates:
        if fnmatch.fnmatch(domain_only, template['pattern']):
            return {
                'from_email': template['from_email'].replace('{base_domain}', base_domain),
                'smtp_host': template['smtp_host'],
                'smtp_port': template['smtp_port']
            }

    # Default fallback
    return {
        'from_email': f'noreply@{base_domain}',
        'smtp_host': 'dell-workstation.tail67811d.ts.net',
        'smtp_port': 587
    }
```

### Provisioning Workflow

```python
class SiteProvisioner:
    def create_site(self, site_config: dict) -> dict:
        """
        新規サイトを作成し、SMTP設定を自動構成
        """
        try:
            # Step 1: Database creation
            self.create_database(site_config)

            # Step 2: WordPress installation
            self.install_wordpress(site_config)

            # Step 3: SMTP configuration (automatic)
            smtp_config = detect_smtp_config(site_config['domain'])
            self.configure_smtp(site_config['site_path'], smtp_config)

            # Step 4: Nginx configuration
            self.generate_nginx_config(site_config)

            # Step 5: Cloudflare Tunnel setup
            self.update_cloudflare_tunnel(site_config)

            # Log success
            self.log_provisioning_success(site_config)

            return {'status': 'success', 'site_id': site_config['site_path']}

        except Exception as e:
            # Rollback on error
            self.rollback_site_creation(site_config)
            raise ProvisioningError(f"Site creation failed: {str(e)}")

    def configure_smtp(self, site_path: str, smtp_config: dict):
        """
        WP Mail SMTPプラグインを自動設定
        """
        # Install plugin
        self.wp_cli(f"plugin install wp-mail-smtp --activate", site_path)

        # Configure SMTP
        smtp_json = json.dumps({
            'mail': {
                'from_email': smtp_config['from_email'],
                'from_name': 'WordPress Notification',
                'mailer': 'smtp',
                'return_path': True
            },
            'smtp': {
                'host': smtp_config['smtp_host'],
                'port': smtp_config['smtp_port'],
                'encryption': 'tls',
                'autotls': True,
                'auth': False
            }
        })

        self.wp_cli(f"option update wp_mail_smtp '{smtp_json}' --format=json", site_path)

        # Verify configuration
        self.verify_smtp_config(site_path, smtp_config['from_email'])
```

---

## 🧪 Testing Strategy

### Unit Tests

```python
def test_smtp_config_detection():
    """Test SMTP config auto-detection"""
    assert detect_smtp_config('blog.kuma8088.com/test')['from_email'] == 'noreply@kuma8088.com'
    assert detect_smtp_config('new-site.com')['from_email'] == 'noreply@new-site.com'
    assert detect_smtp_config('fx-trader-life.com/lp')['from_email'] == 'noreply@fx-trader-life.com'

def test_site_provisioning():
    """Test complete site provisioning workflow"""
    config = {
        'site_path': 'test-site',
        'domain': 'test.kuma8088.com',
        'site_title': 'Test Site'
    }

    provisioner = SiteProvisioner()
    result = provisioner.create_site(config)

    assert result['status'] == 'success'
    assert verify_smtp_installed(config['site_path'])
    assert verify_smtp_configured(config['site_path'], 'noreply@kuma8088.com')
```

### Integration Tests

```python
@pytest.mark.integration
def test_api_site_creation():
    """Test site creation via API"""
    response = requests.post('http://localhost:5000/api/sites', json={
        'site_path': 'integration-test',
        'domain': 'test.kuma8088.com',
        'admin_user': 'admin',
        'admin_password': 'password123',
        'admin_email': 'admin@example.com'
    })

    assert response.status_code == 201
    data = response.json()
    assert data['smtp_status']['configured'] == True
    assert data['smtp_status']['from_email'] == 'noreply@kuma8088.com'

@pytest.mark.integration
def test_smtp_test_email():
    """Test email sending functionality"""
    response = requests.post('http://localhost:5000/api/sites/test-site/smtp/test', json={
        'to_email': 'test@example.com'
    })

    assert response.status_code == 200
    assert response.json()['sent'] == True
```

---

## 📊 Monitoring & Logging

### Metrics to Track

1. **Provisioning Success Rate**
   - Total sites created
   - Success vs. failure rate
   - Average provisioning time

2. **SMTP Configuration Status**
   - Sites with SMTP configured
   - Configuration errors
   - Test email success rate

3. **Error Tracking**
   - Plugin installation failures
   - Configuration errors
   - Rollback events

### Log Format

```json
{
  "timestamp": "2025-11-11T12:00:00Z",
  "level": "INFO",
  "component": "provisioner",
  "action": "site_creation",
  "site_id": "kuma8088-new-site",
  "status": "success",
  "steps": {
    "database": {"status": "success", "duration_ms": 150},
    "wordpress": {"status": "success", "duration_ms": 5000},
    "smtp": {"status": "success", "duration_ms": 2000}
  },
  "total_duration_ms": 7500
}
```

---

## 🔒 Security Considerations

### API Authentication

- JWT tokens for API access
- Role-based access control (RBAC)
- Rate limiting on API endpoints

### SMTP Credentials

- Store credentials in environment variables
- Never log passwords
- Use secret management service (HashiCorp Vault, AWS Secrets Manager)

### Input Validation

- Sanitize all user inputs
- Validate email addresses
- Check domain format
- Prevent SQL injection

---

## 📚 Documentation Requirements

### User Documentation

1. **Site Creation Guide**
   - Step-by-step instructions
   - Screenshots
   - Common issues

2. **SMTP Configuration Guide**
   - Template management
   - Domain-specific settings
   - Troubleshooting

### Developer Documentation

1. **API Reference**
   - Endpoint documentation
   - Request/response examples
   - Error codes

2. **Architecture Documentation**
   - System design
   - Database schema
   - Integration points

---

## 🚀 Migration Plan

### Migrating Existing Sites

**Option 1: Bulk Migration**
```bash
# Use existing script to configure all sites
./scripts/setup-wp-mail-smtp.sh

# Import configuration to portal database
python manage.py import-smtp-configs --from-sites
```

**Option 2: Gradual Migration**
- New sites use portal automatically
- Existing sites migrate on demand
- Manual override available

---

## ✅ Success Criteria

The portal integration is successful when:

1. ✅ 100% of new sites have SMTP configured automatically
2. ✅ Zero manual SMTP configuration steps required
3. ✅ Configuration errors < 1%
4. ✅ Average provisioning time < 30 seconds
5. ✅ Test email success rate > 99%
6. ✅ Complete audit trail of all configurations

---

## 📅 Timeline Estimate

| Phase | Duration | Dependencies |
|-------|----------|--------------|
| Design & Planning | 1 week | - |
| Core API Development | 2 weeks | Design approval |
| Provisioning Engine | 2 weeks | Core API |
| Frontend Development | 2 weeks | Core API |
| Testing & QA | 1 week | All components |
| Documentation | 1 week | Testing complete |
| **Total** | **9 weeks** | - |

---

## 🔗 Related Documentation

- [WP Mail SMTP Setup Guide](../guides/WP-MAIL-SMTP-SETUP.md)
- [Site Creation Script](../../../../services/blog/scripts/create-new-wp-site.sh)
- [Blog System Architecture](../02_design.md)

---

**Last Updated**: 2025-11-11
**Status**: Ready for implementation when portal development begins
