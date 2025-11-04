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

## Project Structure

```
project-root-infra/
├── Docs/                        # Documentation root
│   ├── infra/                   # Infrastructure documentation
│   │   ├── procedures/          # Step-by-step setup procedures (see procedures/README.md)
│   │   ├── infra-specs/         # KVM infrastructure requirements
│   │   └── docker-specs/        # Docker infrastructure requirements
│   └── application/             # Application service documentation
│       └── mailserver/          # Mailserver application (see mailserver/README.md)
├── services/                    # Service implementations
│   └── mailserver/              # Mailserver Docker Compose + Terraform (see services/mailserver/README.md)
├── AGENTS.md                    # Note: References separate AI generator project (not this repo)
├── CLAUDE.md                    # This file - Claude Code guidance
└── README.md                    # Project overview
```

**Documentation References**: For detailed operational procedures, troubleshooting, and command references:
- **Infrastructure Procedures**: See `Docs/infra/procedures/README.md`
- **Mailserver Application**: See `Docs/application/mailserver/README.md` and `services/mailserver/README.md`
- **Terraform Operations**: See `services/mailserver/terraform/README.md`

**Note on AGENTS.md**: This file contains development workflow guidelines from a separate AI procedure generator project. It is not applicable to this infrastructure documentation repository.

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
- Webmail service containerization (🔄 IN PROGRESS - see Mailserver Application below)
- Blog migration to containers
- Commercial service development environment

## Application Services

### Mailserver Application (🔄 IN PROGRESS)

**Current Version**: v6.0 (EC2-based MX Gateway)

**Architecture**: Hybrid Cloud Mail Server (AWS EC2 + Dell On-Premises + SendGrid)
- v6.0 (EC2): Active - Host-level Tailscale integration
- v5.1 (Fargate): Deprecated due to VPN network isolation issues

**Cost Estimate**: ~$4.81/month AWS

**Key Documentation**:
- **Architecture & Setup**: `Docs/application/mailserver/README.md`
- **EC2 Implementation**: `Docs/application/mailserver/04_EC2Server.md`
- **Service Configuration**: `services/mailserver/README.md`
- **Terraform Operations**: `services/mailserver/terraform/README.md`
- **Troubleshooting**: `services/mailserver/troubleshoot/INBOUND_MAIL_FAILURE_2025-11-03.md`

**Migration Context**: Fargate → EC2 migration resolved Tailscale VPN networking constraints (see troubleshooting docs for details)

## Working with Procedures

**Procedure characteristics**:
- AI-generated step-by-step guides with execution commands, expected output, validation criteria, and troubleshooting
- Located in `Docs/infra/procedures/` organized by phase

**For detailed procedure authoring, validation, and commit workflows**: See `Docs/infra/procedures/README.md`

## Docker Storage Configuration

**Storage Layout**:
- **System data** (`/var/lib/docker`): 50GB on SSD for performance-critical operations
  - Docker daemon metadata, container layers, runtime data
- **Volumes/Images** (`/data/docker`): 3.6TB HDD for capacity-intensive storage
  - Docker images, persistent volumes, build cache
- **Backup destination** (`/mnt/backup`): External HDD with weekly automated rsync
  - Full backup of volumes, images, and docker-compose configurations

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

**Security Principles**:
- **SSH**: Public key auth only, non-standard ports (2201-2280), fail2ban protection
- **Docker**: SELinux enforcing, API protection, non-root access, automatic security updates
- **Containers**: Unprivileged by default, secrets management, minimal capabilities

**For detailed security configurations and best practices**: See respective service README.md files in `Docs/infra/procedures/` and `services/`

## Common Pitfalls and Solutions

**Representative Issues**:
- **Network Migration**: VMs on default network fail after migration → Plan detachment/attachment before disabling
- **iptables Routing**: Isolation rules not working → Check rule order (ACCEPT before DROP)
- **Resource Exhaustion**: VM start failures → Enforce 70% memory, 1:2 CPU overcommit limits
- **Docker Storage Conflicts**: Daemon won't start → Validate daemon.json, check permissions, SELinux context

**For comprehensive troubleshooting guides**: See respective README.md files in `Docs/infra/procedures/` and `services/`

## Testing Strategy

**Testing Principles**:
1. Validate prerequisites before proceeding
2. Test incrementally (one change → validate → next)
3. Document actual vs expected outcomes
4. Preserve rollback capability (backup configs before changes)

**For detailed testing procedures**: See validation sections in respective procedure documents

## Monitoring and Logging

**Key Log Locations**:
- Docker daemon: `sudo journalctl -u docker`
- Container logs: `docker logs <container>`
- Security: fail2ban, SELinux audit logs
- System: `/var/log/messages`

**Monitoring Approach**: Daily log reviews, weekly disk usage checks, backup verification

**For detailed monitoring and alerting configurations**: See `Docs/infra/procedures/3-docker/3.3-monitoring-security-setup.md`

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

**Procedure Lifecycle**: Identify need → Draft → Test → Commit → Document lessons learned

**For detailed workflow steps and git commit formats**: See `Docs/infra/procedures/README.md`

## Repository Workflow

**Standard Workflow**:
1. **Before**: Check phase status, review procedures, verify prerequisites, check git status
2. **During**: Follow procedures, document deviations, capture outputs
3. **After**: Run validation, document lessons, update procedures, commit changes

**For detailed workflow guidance**: See `Docs/infra/procedures/README.md`

## Support Resources

**Official Documentation**:
- LibVirt: https://libvirt.org/docs.html
- KVM: https://www.linux-kvm.org/page/Documents
- Rocky Linux: https://docs.rockylinux.org/
- Terraform LibVirt Provider: https://registry.terraform.io/providers/dmacvicar/libvirt/latest/docs

**Project References**: Procedure troubleshooting sections, specification documents in `Docs/infra/specs/`
