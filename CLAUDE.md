# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Project Overview

This is a KVM-based AWS simulation infrastructure project on Dell WorkStation running Rocky Linux 9.6. The project creates a phased learning environment that simulates AWS VPC architecture for local development and testing, with eventual migration to AWS using Terraform and AWS MGN.

**Key Philosophy**: Build progressively from minimal KVM setup (Phase 1) → AWS-equivalent virtual networking (Phase 2) → container orchestration (Phase 3+), documenting each phase through AI-generated procedure documents.

### Repository Nature

**This is a documentation-first infrastructure repository**, not a software development project:
- **Primary Deliverable**: Step-by-step procedural documentation for infrastructure setup
- **No Application Code**: No Python/Node.js/etc. application code to build, test, or deploy
- **Infrastructure as Documentation**: The "code" is bash commands in markdown procedures
- **Validation Method**: Procedures are validated by executing them on actual infrastructure
- **Version Control**: Git tracks documentation iterations and infrastructure configuration files

**AGENTS.md Context**: The AGENTS.md file references a separate AI procedure generator project that was used to create some of the initial procedures in this repository. It is not directly applicable to this infrastructure documentation project.

## Hardware Constraints

**Dell WorkStation Specifications**:
- CPU: 6 cores/12 threads (x86_64)
- Memory: 32GB RAM
- Storage: 3.6TB HDD (/data) + 390GB SSD (/home) + 70GB SSD (/)

**Resource Allocation Strategy**:
- Host OS reserves: 2 cores, 8GB RAM
- VM pool: 4 physical cores → max 8 vCPU (1:2 overcommit), 24GB RAM (70% max usage)
- Max concurrent VMs: 8 instances
- Storage: High-speed VMs on SSD (/var/lib/libvirt/images), large VMs on HDD (/data/kvm/images)

## Network Architecture

### Phase 1 (Testing - Temporary)
- `default` network (192.168.122.0/24) - LibVirt default for initial VM testing
- **Important**: This network is decommissioned in Phase 2

### Phase 2+ (Production - AWS VPC Equivalent)
All networks use libvirt type=nat with built-in dnsmasq for DNS/DHCP:

| Segment    | CIDR        | Gateway  | DHCP Range      | SSH Ports | Domain     |
|------------|-------------|----------|-----------------|-----------|------------|
| Management | 10.0.0.0/24 | 10.0.0.1 | 10.0.0.10-50    | 2201-2210 | lab.local  |
| Public     | 10.0.1.0/24 | 10.0.1.1 | 10.0.1.100-200  | 2211-2230 | lab.local  |
| Private    | 10.0.2.0/24 | 10.0.2.1 | 10.0.2.100-200  | 2231-2250 | lab.local  |
| Database   | 10.0.3.0/24 | 10.0.3.1 | Static IP only  | 2251-2260 | lab.local  |
| Container  | 10.0.4.0/24 | 10.0.4.1 | 10.0.4.100-200  | 2261-2280 | lab.local  |

**Critical Network Rules**:
- Management → All segments (full access)
- Public → Private, Database, Container
- Private → Database, Container
- Database → **NO outbound** to other segments (security isolation)
- All segments → Internet via NAT

**SSH Configuration**: Never use port 22. Always use segment-specific port ranges (2201-2280).

## Key Development Commands

### KVM/LibVirt Operations

```bash
# Network management
sudo virsh net-list --all              # List all networks
sudo virsh net-info <network-name>     # Network details
sudo virsh net-start <network-name>    # Start network
sudo virsh net-autostart <network-name> # Enable autostart

# VM management
sudo virsh list --all                  # List all VMs
sudo virsh dominfo <vm-name>           # VM details
sudo virsh start <vm-name>             # Start VM
sudo virsh shutdown <vm-name>          # Graceful shutdown
sudo virsh console <vm-name>           # Console access (Ctrl+] to exit)

# VM network interface management
sudo virsh domiflist <vm-name>                                    # List interfaces
sudo virsh detach-interface <vm-name> --type bridge --mac <MAC> --config
sudo virsh attach-interface --domain <vm-name> --type network \
  --source <network-name> --model virtio --config

# Storage management
sudo virsh pool-list --all             # List storage pools
sudo virsh vol-list default            # List volumes
sudo qemu-img create -f qcow2 <path> <size>  # Create disk image
sudo qemu-img info <image-path>        # Image details
```

### Network Validation

```bash
# Host-side checks
sudo virsh net-dumpxml <network-name>  # Verify network XML configuration
nmcli device status | grep br-         # Check bridge interfaces
ip addr show | grep br-                # Verify bridge IPs (10.0.x.1)
sudo iptables -S FORWARD | grep 10.0.  # Check routing rules
sysctl net.ipv4.ip_forward             # Must be 1

# VM-side checks (inside guest OS)
ip -4 addr show                        # Verify DHCP-assigned IP
ping -c 3 10.0.x.1                     # Test gateway connectivity
nslookup google.com                    # Test DNS resolution
ping -c 3 8.8.8.8                      # Test internet connectivity
```

### Firewall Configuration

```bash
# View current firewall rules
sudo firewall-cmd --list-all
sudo firewall-cmd --list-rich-rules
sudo firewall-cmd --list-ports

# Reload firewall after changes
sudo firewall-cmd --reload
```

### Docker Operations

```bash
# Docker service management
sudo systemctl status docker              # Check Docker daemon status
sudo systemctl start docker               # Start Docker service
sudo systemctl restart docker             # Restart Docker service
sudo journalctl -u docker -n 50           # View recent Docker daemon logs

# Container management
docker ps                                 # List running containers
docker ps -a                              # List all containers
docker logs <container>                   # View container logs
docker logs -f <container>                # Follow container logs in real-time
docker exec -it <container> bash          # Interactive shell in container
docker stop <container>                   # Stop container gracefully
docker rm <container>                     # Remove stopped container
docker inspect <container>                # Detailed container information

# Image management
docker images                             # List local images
docker pull <image>                       # Pull image from registry
docker rmi <image>                        # Remove image
docker build -t <name> .                  # Build image from Dockerfile
docker system prune -a                    # Clean up unused resources (images, containers, networks)

# Docker Compose operations
docker compose up -d                      # Start services in background
docker compose down                       # Stop and remove services
docker compose ps                         # List compose services
docker compose logs -f <service>          # Follow service logs
docker compose restart <service>          # Restart specific service
docker compose exec <service> bash        # Execute command in service container

# Docker Swarm operations
docker swarm init                         # Initialize swarm (single node)
docker swarm leave --force                # Leave swarm cluster
docker node ls                            # List swarm nodes
docker service ls                         # List swarm services
docker service logs <service>             # View service logs
docker stack deploy -c <file> <stack>     # Deploy stack from compose file
docker stack rm <stack>                   # Remove stack

# Storage and resource management
docker system df                          # Show Docker disk usage
docker volume ls                          # List volumes
docker volume inspect <volume>            # Volume details
docker network ls                         # List networks
docker network inspect <network>          # Network details
```

## Project Structure

```
project-root-infra/
├── Docs/infra/
│   ├── procedures/              # Step-by-step infrastructure setup procedures
│   │   ├── 2-kvm/               # Phase 2: KVM setup procedures
│   │   │   ├── 2.1-rocky-linux-kvm-host-setup.md
│   │   │   └── 2.2-virtual-network-setup.md
│   │   └── 3-docker/            # Phase 3: Docker setup procedures
│   │       ├── 3.1-docker-environment-setup.md
│   │       ├── 3.2-storage-backup-setup.md
│   │       ├── 3.3-monitoring-security-setup.md
│   │       └── 3.4-infrastructure-validation.md
│   ├── infra-specs/             # KVM infrastructure requirements
│   │   └── INFRASTRUCTURE-REQUIREMENTS.md
│   └── docker-specs/            # Docker infrastructure requirements
│       ├── 3.0-DOCKER-INFRASTRUCTURE-REQUIREMENTS.md
│       └── 3.0-DOCKER-INFRASTRUCTURE-DESIGN.md
├── .venv/                       # Python virtual environment (superclaude package only)
├── AGENTS.md                    # Note: References separate AI generator project (not this repo)
├── CLAUDE.md                    # This file - Claude Code guidance
└── README.md                    # Project overview
```

**Note on AGENTS.md**: This file contains development workflow guidelines from a separate AI procedure generator project. It references Python development, testing, and build commands that **do not apply to this infrastructure documentation repository**. It was likely included as reference material during initial procedure generation but is not used for day-to-day work on this infrastructure project.

## Implementation Phases

### Phase 1: Minimal KVM Environment (✅ COMPLETED)
- **Scope**: Single test VM on default network (192.168.122.0/24)
- **Key File**: `procedures/2.1-rocky-linux-kvm-host-setup.md`
- **Goal**: Validate KVM/QEMU/LibVirt installation and basic VM operations
- **Completion Criteria**: test-vm boots, network connectivity established, console access works

### Phase 2: AWS VPC Network Simulation (✅ COMPLETED)
- **Scope**: 5 isolated networks (Management, Public, Private, Database, Container)
- **Key File**: `procedures/2.2-virtual-network-setup.md`
- **Migration Task**: Move test-vm from default → new networks, disable default network
- **Goal**: Replicate AWS VPC segmentation with iptables-based routing rules
- **Completion Criteria**: All segments active, routing verified, default network stopped

### Phase 3: Docker Infrastructure Setup (🔄 IN PROGRESS)
- **Scope**: Docker Engine, Docker Compose, Docker Swarm on Rocky Linux 9.6 (host-direct execution)
- **Key Files**:
  - `Docs/infra/docker-specs/3.0-DOCKER-INFRASTRUCTURE-REQUIREMENTS.md`
  - `Docs/infra/procedures/3-docker/3.1-docker-environment-setup.md`
  - `Docs/infra/procedures/3-docker/3.2-storage-backup-setup.md`
  - `Docs/infra/procedures/3-docker/3.3-monitoring-security-setup.md`
  - `Docs/infra/procedures/3-docker/3.4-infrastructure-validation.md`
- **Architecture**: Single-node Docker Swarm with future multi-node expansion capability
- **Storage Layout**:
  - System data: 50GB on SSD (`/var/lib/docker`)
  - Volumes/Images: 3.6TB on HDD (`/data/docker`)
  - Backup: External HDD with weekly rsync (`/mnt/backup`)
- **Goal**: Container platform for commercial service development and testing
- **Completion Criteria**: Docker operational, storage configured, monitoring/security baseline established, validation tests passed

### Phase 4-5: Resource Management & Terraform
- KVM resource manager (VM/storage automation)
- Terraform state generation and GitHub integration

### Phase 6+: Service Deployment
- Webmail service containerization
- Blog migration to containers
- Commercial service development environment

## Working with Procedures

Procedures in `procedures/` are AI-generated step-by-step guides with:
- **Execution Commands**: Exact bash commands to run
- **Expected Output**: What success looks like
- **Validation Criteria**: How to verify completion
- **Troubleshooting**: Common failure modes and fixes

**When creating new procedures**:
1. Use existing procedures as templates (see `2.1-*` and `2.2-*`)
2. Include prerequisite checks at the start
3. Provide validation steps after each major action
4. Document rollback/cleanup commands
5. Estimate time requirements realistically

### Procedure Validation Workflow

**Before Committing New/Updated Procedures**:

1. **Dry Run Validation** (if possible without destructive changes):
   ```bash
   # Check command syntax without execution
   bash -n <(grep -A1 '```bash' procedure.md | grep -v '```')

   # Verify prerequisite commands exist
   which virsh docker systemctl  # etc.
   ```

2. **Test Execution** (required for new procedures):
   - Execute procedure on a test environment or snapshot
   - Document actual output vs expected output
   - Note any deviations or required adjustments
   - Capture error messages and resolutions

3. **Documentation Review Checklist**:
   - [ ] All commands are copy-paste ready (no placeholders like `<vm-name>`)
   - [ ] Expected outputs match actual execution results
   - [ ] Validation criteria are specific and measurable
   - [ ] Troubleshooting section covers common failures
   - [ ] Time estimates are realistic based on actual execution
   - [ ] Rollback/cleanup commands are provided
   - [ ] Prerequisites are clearly stated
   - [ ] References to other procedures are accurate

4. **Git Commit Message Format**:
   ```
   docs(phase-X): [action] procedure name

   - What changed: Brief description of modifications
   - Validation: Tested on [environment/snapshot]
   - Results: [Success/Partial/Failed - explanation]
   ```

**Example**:
```
docs(phase-3): Update Docker environment setup monitoring section

- What changed: Added fail2ban Docker API jail configuration
- Validation: Tested on Phase 3 Docker host (fresh install)
- Results: Success - all validation steps passed
```

## Docker Storage Configuration

**Storage Layout**:
- **System data** (`/var/lib/docker`): 50GB on SSD for performance-critical operations
  - Docker daemon metadata, container layers, runtime data
- **Volumes/Images** (`/data/docker`): 3.6TB HDD for capacity-intensive storage
  - Docker images, persistent volumes, build cache
- **Backup destination** (`/mnt/backup`): External HDD with weekly automated rsync
  - Full backup of volumes, images, and docker-compose configurations

**Key Configuration** (`/etc/docker/daemon.json`):
```json
{
  "data-root": "/data/docker",
  "storage-driver": "overlay2",
  "log-driver": "json-file",
  "log-opts": {
    "max-size": "10m",
    "max-file": "3"
  },
  "default-address-pools": [
    {
      "base": "172.17.0.0/16",
      "size": 24
    }
  ]
}
```

**Storage Management Commands**:
```bash
# Check Docker disk usage
docker system df                          # Overview of images, containers, volumes
docker system df -v                       # Detailed breakdown

# Verify storage configuration
docker info | grep -E "Storage Driver|Docker Root Dir"
cat /etc/docker/daemon.json | jq          # Validate daemon.json syntax

# Check available space
df -h /var/lib/docker                     # System data on SSD
df -h /data/docker                        # Volumes/images on HDD
df -h /mnt/backup                         # Backup destination

# Storage cleanup
docker system prune -a --volumes          # Remove all unused data (CAUTION)
docker image prune -a                     # Remove unused images only
docker volume prune                       # Remove unused volumes only

# Backup operations
sudo rsync -av /data/docker/ /mnt/backup/docker/  # Manual backup
ls -lh /mnt/backup/docker/                        # Verify backup contents
```

**Important Notes**:
- Docker bridge network uses 172.17.0.0/16 (no conflict with KVM's 10.0.x.0/24 networks)
- Custom Docker networks should avoid 10.0.0.0/16 and 192.168.122.0/24 ranges
- Weekly automated backups scheduled via cron (see `3.2-storage-backup-setup.md`)

## Infrastructure Configuration Best Practices

**CRITICAL RULE**: Before making ANY infrastructure configuration recommendations (KVM, libvirt, networking, storage):

1. **Consult Official Documentation**: Use WebFetch to retrieve official docs
   - LibVirt XML format: https://libvirt.org/formatnetwork.html
   - KVM networking: https://wiki.libvirt.org/Networking.html
   - Rocky Linux docs: https://docs.rockylinux.org/

2. **Verify Current Setup**: Always check existing configuration first
   ```bash
   sudo virsh net-dumpxml <network>  # Network configs
   sudo virsh dumpxml <vm>           # VM configs
   nmcli connection show             # NetworkManager state
   ```

3. **Never Assume Defaults**: Different environments have different configurations
   - Rocky 9 uses NetworkManager (not bridge-utils)
   - LibVirt networks may use different bridge names
   - iptables rules vary by firewalld configuration

**Rationale**: Infrastructure misconfiguration causes production outages. Assumptions about port numbers, network ranges, or service behavior lead to failed deployments.

## Security Configuration

**SSH Hardening**:
- **Public key authentication only**: Password authentication disabled
- **Non-standard port range**: 2201-2280 (segment-specific, never use port 22)
- **fail2ban protection**: Automated blocking of brute force attacks
- **Key management**: ~/.ssh/authorized_keys for allowed public keys

**Docker Security**:
- **SELinux Enforcing mode**: Maintained for mandatory access control
- **Docker API protection**: fail2ban monitoring for unauthorized access attempts
- **Non-root user access**: Users in docker group can run Docker commands without sudo
- **Automatic security updates**: dnf-automatic configured for weekly security patching
- **Container isolation**: Unprivileged containers by default, privileged mode only when necessary

**Security Validation Commands**:
```bash
# SELinux status check
getenforce                                # Must show "Enforcing"
sudo sestatus                             # Detailed SELinux status

# fail2ban status
sudo systemctl status fail2ban
sudo fail2ban-client status sshd          # SSH jail status
sudo fail2ban-client status docker-auth   # Docker API jail status

# SSH configuration verification
sudo sshd -T | grep -E "pubkeyauthentication|passwordauthentication"
# Expected: PubkeyAuthentication yes, PasswordAuthentication no

# Docker group membership
groups | grep docker                      # Current user should be in docker group
id -nG $USER | grep docker                # Alternative verification

# Automatic updates status
sudo systemctl status dnf-automatic
sudo dnf-automatic --timer                # Show next scheduled update

# Security audit
sudo ausearch -m avc -ts recent           # Check recent SELinux denials
sudo journalctl -u fail2ban --since "1 hour ago"  # Recent fail2ban actions
```

**Security Best Practices**:
- Regularly review fail2ban logs for attack patterns
- Keep SSH keys secure and rotate periodically
- Review SELinux audit logs for policy violations
- Monitor security update status weekly
- Use docker compose secrets for sensitive data (not environment variables)
- Run security-sensitive containers with read-only root filesystem when possible
- Limit container capabilities using --cap-drop/--cap-add flags

## Common Pitfalls and Solutions

### Network Migration from default → Custom Networks
**Problem**: VMs attached to default network won't work after default is stopped
**Solution**: Before disabling default network:
1. Identify VMs using default: `sudo virsh net-info default`
2. Detach from default: `sudo virsh detach-interface <vm> --type bridge --mac <MAC> --config`
3. Attach to new network: `sudo virsh attach-interface --domain <vm> --type network --source <new-network> --config`
4. Verify inside VM: `ip -4 addr show` should show new subnet IP

### iptables Routing Conflicts
**Problem**: Segment isolation rules not working as expected
**Solution**: Check rule order with `sudo iptables -L FORWARD --line-numbers`
- ACCEPT rules must come before DROP rules
- More specific rules should precede general rules
- Verify with: `sudo iptables -S FORWARD | grep 10.0.`

### Resource Exhaustion
**Problem**: Cannot start new VMs due to resource constraints
**Solution**:
- Check current usage: `virsh nodeinfo` and `free -h`
- Review VM allocation: `for vm in $(virsh list --all --name); do virsh dominfo $vm | grep -E "CPU|memory"; done`
- Enforce limits: Never exceed 70% memory usage, 1:2 CPU overcommit max

### DHCP Not Assigning IPs
**Problem**: VM boots but gets no IP address
**Solution**:
1. Check network is active: `sudo virsh net-list`
2. Verify DHCP range in XML: `sudo virsh net-dumpxml <network>`
3. Check lease table: `sudo virsh net-dhcp-leases <network>`
4. Restart VM's network: Inside VM, run `sudo systemctl restart NetworkManager`

### Docker Storage Driver Conflicts
**Problem**: Docker fails to start after storage configuration changes
**Solution**:
1. Stop Docker: `sudo systemctl stop docker`
2. Backup existing data: `sudo mv /var/lib/docker /var/lib/docker.backup`
3. Verify daemon.json syntax: `cat /etc/docker/daemon.json | jq`
4. Create new data directory: `sudo mkdir -p /data/docker`
5. Set permissions: `sudo chown root:root /data/docker && sudo chmod 710 /data/docker`
6. Start Docker: `sudo systemctl start docker`
7. Check logs: `sudo journalctl -u docker -n 50`
8. Verify configuration: `docker info | grep -E "Storage Driver|Docker Root Dir"`

### Container Network Conflicts with KVM
**Problem**: Docker bridge network conflicts with libvirt networks (10.0.x.0/24)
**Solution**:
- Docker default bridge uses 172.17.0.0/16 (no conflict by default)
- Custom networks should avoid 10.0.0.0/16 and 192.168.122.0/24 ranges
- Verify network ranges: `docker network ls && docker network inspect bridge`
- Set custom address pools in daemon.json (see Docker Storage Configuration section)
- Restart Docker after daemon.json changes: `sudo systemctl restart docker`

### Docker Daemon Won't Start
**Problem**: systemctl start docker fails with permission or configuration errors
**Solution**:
1. Check systemd status: `sudo systemctl status docker`
2. View full logs: `sudo journalctl -xeu docker`
3. Validate daemon.json: `cat /etc/docker/daemon.json | jq` (must be valid JSON)
4. Check directory permissions:
   - `/var/lib/docker`: `sudo ls -ld /var/lib/docker`
   - `/data/docker`: `sudo ls -ld /data/docker`
5. SELinux context check: `ls -Z /var/lib/docker /data/docker`
6. Restore SELinux context if needed: `sudo restorecon -Rv /var/lib/docker /data/docker`
7. Check for port conflicts: `sudo netstat -tulpn | grep 2375` (Docker API port)

### Container Fails to Start
**Problem**: docker compose up or docker run fails with various errors
**Solution**:
1. Check container logs: `docker logs <container>`
2. Inspect container state: `docker inspect <container>`
3. Verify image exists: `docker images | grep <image>`
4. Check resource limits: `docker stats` (CPU/memory constraints)
5. SELinux denials: `sudo ausearch -m avc -c <container-name>`
6. Network connectivity: `docker network inspect <network>`
7. Volume permissions: `ls -lZ <volume-path>` (check SELinux labels)

## Testing Strategy

When implementing changes:

1. **Always validate prerequisites** before proceeding
   ```bash
   # Example: Before creating network
   sudo systemctl is-active libvirtd  # Must be active
   sysctl net.ipv4.ip_forward         # Must be 1
   ```

2. **Test incrementally** - don't batch multiple major changes
   - Create one network → validate → proceed to next
   - Start one VM → verify connectivity → add more VMs

3. **Document actual vs expected** in validation sections
   - Expected: "Network shows active with autostart=yes"
   - Actual: Run `sudo virsh net-info <network>` and compare

4. **Preserve rollback capability**
   ```bash
   # Before destructive changes
   sudo virsh net-dumpxml <network> > /tmp/network-backup.xml
   sudo virsh dumpxml <vm> > /tmp/vm-backup.xml
   ```

## Monitoring and Logging

**Log Locations**:
- **Docker daemon logs**: `sudo journalctl -u docker` (systemd journal)
- **Container logs**:
  - Individual: `docker logs <container>`
  - All containers: `/var/log/docker/containers/` (if configured)
- **Backup logs**: `/var/log/docker-backup/` (automated backup operations)
- **System logs**: `sudo journalctl` or `/var/log/messages` (Rocky Linux system events)
- **Security logs**:
  - fail2ban: `sudo journalctl -u fail2ban`
  - SELinux: `sudo ausearch -m avc` or `/var/log/audit/audit.log`
- **Network logs**: `/var/log/firewalld` (firewall events)

**Daily Health Checks**:
```bash
# System resource usage
free -h                                   # Memory usage (should be <70%)
df -h                                     # Disk usage (monitor /data/docker)
docker system df                          # Docker-specific disk usage

# Service health
sudo systemctl status docker              # Docker daemon status
sudo systemctl status libvirtd            # KVM/libvirt status
docker ps --filter "health=unhealthy"     # Unhealthy containers

# Recent errors
sudo journalctl -u docker --since "1 hour ago" -p err
sudo journalctl -u libvirtd --since "1 hour ago" -p err
sudo journalctl --since "1 hour ago" | grep -i error | head -20

# Performance metrics
uptime                                    # System load average
docker stats --no-stream                  # Container resource usage snapshot
virsh list --all                          # VM status overview
```

**Weekly Maintenance Checks**:
```bash
# Backup verification
ls -lh /mnt/backup/docker/                # Check backup timestamp and size
cat /var/log/docker-backup/backup-*.log | tail -50  # Review recent backup logs

# Security updates
sudo dnf check-update                     # Available updates
sudo journalctl -u dnf-automatic --since "7 days ago"  # Recent auto-updates

# Log rotation status
sudo journalctl --disk-usage              # Check journal disk usage
ls -lh /var/log/docker-backup/            # Verify log rotation

# fail2ban statistics
sudo fail2ban-client status sshd          # SSH attack attempts
sudo fail2ban-client status docker-auth   # Docker API attack attempts
```

**Alerting Configuration**:
- **Critical errors**: Email notifications via logwatch (daily summary)
- **Security incidents**: Discord webhook for SSH brute force, fail2ban triggers
- **Resource thresholds**: Manual monitoring (future: Prometheus/Grafana integration)
- **Backup failures**: Log analysis required (`/var/log/docker-backup/`)

**Log Management**:
```bash
# Log rotation settings
sudo cat /etc/logrotate.d/docker          # Docker log rotation config

# Manual log cleanup (if needed)
sudo journalctl --vacuum-time=30d         # Keep last 30 days of systemd logs
docker system prune -a --volumes          # Clean Docker logs and unused resources

# Search logs for specific events
sudo journalctl -u docker --grep="error"  # Docker daemon errors
sudo journalctl -u fail2ban --grep="Ban"  # fail2ban actions
docker logs --since 1h <container>        # Container logs from last hour
```

**Monitoring Best Practices**:
- Review logs daily for critical errors and security events
- Monitor disk usage weekly (especially `/data/docker` and `/var/log`)
- Verify backup success every Sunday (automated backup day)
- Check fail2ban stats for unusual attack patterns
- Review SELinux audit logs for policy violations
- Track container resource usage trends with `docker stats`

## AI-Generated Procedure Guidelines

This project uses AI tools (Kiro/Claude/Codex) to generate procedural documentation. When reviewing or creating procedures:

- **Human Review Required**: All AI-generated procedures must be validated before execution
- **Version Control**: Track procedure iterations in Git with clear version markers
- **Feedback Loop**: Document execution results to improve future procedure generation
- **Safety Checks**: Always include rollback steps and validation criteria
- **Context Preservation**: Maintain system state information across procedure updates

## Migration to AWS (Future)

The infrastructure is designed for eventual AWS migration using:
- **Terraform**: All KVM resources will be exported as Terraform configs
- **AWS MGN**: Application Migration Service for VM migration
- **Phased Approach**: Development (Dell) → Staging (AWS Single-AZ) → Production (AWS Multi-AZ)

When working on Terraform configs:
- Keep AWS provider compatibility in mind
- Use data sources instead of hardcoded values
- Tag all resources with environment metadata
- Maintain separate state files per environment

## Documentation Workflow

### When Creating or Updating Procedures

**Step 1: Identify Need**
- New phase implementation requires new procedure
- Existing procedure has errors or outdated information
- Infrastructure changes require procedure updates

**Step 2: Draft Procedure**
```bash
# Create new procedure file
touch Docs/infra/procedures/<phase>/<phase-number>-<procedure-name>.md

# Use existing procedures as templates
cat Docs/infra/procedures/2-kvm/2.1-rocky-linux-kvm-host-setup.md
```

**Step 3: Test and Validate**
- Execute procedure on test environment or VM snapshot
- Document actual outputs and any deviations
- Update procedure based on test results
- Repeat until procedure executes successfully

**Step 4: Review and Commit**
```bash
# Check git status
git status

# Review changes
git diff Docs/infra/procedures/<phase>/<file>.md

# Stage changes
git add Docs/infra/procedures/<phase>/<file>.md

# Commit with structured message
git commit -m "docs(phase-X): [add/update] procedure name

- What changed: Brief description
- Validation: Tested on [environment]
- Results: Success/Partial/Notes"

# Push to remote (if configured)
git push origin main
```

**Step 5: Document Lessons Learned**
- Update troubleshooting sections based on issues encountered
- Add validation criteria that weren't obvious initially
- Document time estimates based on actual execution
- Update related specification documents if architecture changed

### Current Work Status Tracking

Before making changes, check the current modified files:
```bash
# See what's currently being worked on
git status --short

# View recent changes
git log --oneline -10

# See uncommitted changes in detail
git diff Docs/infra/procedures/
```

**Modified Files**: The git status shows which procedures are currently being edited. Complete work on these before starting new procedures to avoid context switching.

## Repository Workflow

**Before Starting Work**:
1. Check current implementation phase status (git log, procedure completion markers)
2. Review relevant procedure in `procedures/`
3. Verify prerequisites are met
4. Check for uncommitted changes: `git status`

**During Implementation**:
1. Follow procedure steps exactly as documented
2. Document any deviations or issues encountered
3. Capture actual command output for validation
4. Take notes for procedure updates

**After Completion**:
1. Run comprehensive validation tests
2. Document lessons learned
3. Update procedure if needed based on actual execution
4. Commit procedure updates with validation notes
5. Mark phase complete if all procedures validated

## Support Resources

- **LibVirt Documentation**: https://libvirt.org/docs.html
- **KVM Documentation**: https://www.linux-kvm.org/page/Documents
- **Rocky Linux Docs**: https://docs.rockylinux.org/
- **Terraform LibVirt Provider**: https://registry.terraform.io/providers/dmacvicar/libvirt/latest/docs

**When stuck**: Check `.kiro/specs/*/design.md` for architectural context and `procedures/*.md` troubleshooting sections for common issues.
