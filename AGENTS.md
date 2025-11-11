# Repository Guidelines

## Project Structure & Module Organization
Operational code sits in `services/`. `services/mailserver/` bundles Docker Compose stacks, AWS Terraform modules, Flask-based `usermgmt/`, and S3 backup scripts/tests. Blog migration tooling lives in `services/blog/`. Architecture, ops guides, and troubleshooting playbooks reside in `docs/` (`docs/infra` for environments, `docs/application` for workloads). Planning notes and audits stay in `specs/`. Consult these sources before adding new modules.

## Build, Test, and Development Commands
- `pip install -r services/mailserver/usermgmt/requirements.txt` — bootstrap the Flask admin environment.  
- `pytest services/mailserver/usermgmt/tests -v --cov=app` — run unit/integration tests with coverage.  
- `bash services/mailserver/tests/s3-backup/test_framework.sh` — verify backup retention and Object Lock scripts.  
- `docker compose -f services/mailserver/docker-compose.yml up -d` — start the on-prem mail stack; swap in `docker-compose.staging.yml` for tunnel validation.  
- `terraform -chdir=services/mailserver/terraform plan` — review AWS diffs before apply.

## Coding Style & Naming Conventions
Target Python 3.9+, enforce Black (4 spaces, 88 chars) and keep flake8 clean. Use snake_case for modules/functions, PascalCase for classes, and UPPER_SNAKE_CASE constants. Shell utilities in `services/mailserver/tests/` should begin with `#!/usr/bin/env bash` plus `set -euo pipefail`. Terraform must pin provider versions and keep variables lowercase_with_underscores. Store environment-specific values in `.env` files or AWS profiles shared by Compose/Terraform.

## Testing Guidelines
Pytest files live beside the code they exercise and follow `test_<topic>.py`. Share fixtures via `services/mailserver/usermgmt/conftest.py`, and gate IMAP/SMTP tests with `@pytest.mark.skipif` so CI stays deterministic. Keep coverage above 80% for user management and routing helpers, and extend the Bash backup suite whenever lifecycle or encryption logic changes. For new services, add pytest or Bash smoke checks against container health endpoints.

## Commit & Pull Request Guidelines
Adopt Conventional Commits (`feat:`, `fix:`, `docs:`) with imperative phrasing and list the main verification command in the body. Pull requests should summarize infrastructure impact, mention affected docs, and link issues. Attach logs/screenshots when altering monitoring or UI flows, and flag reviewers when Terraform state, IAM policies, or mail routing tables change.

## Security & Configuration Tips
Do not commit secrets—load AWS credentials, SendGrid tokens, and Roundcube passwords via environment variables or secret stores referenced by Compose overrides. Validate external input inside `usermgmt/app/` using SQLAlchemy binding and CSRF enforcement. Keep IAM policies under `services/mailserver/terraform/iam/` least-privilege, verify Object Lock via the backup harness, and follow `docs/infra` when rotating certificates, tunnels, or session-manager packages.
