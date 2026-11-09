# Odoo 20 Enterprise - Deployment Troubleshooting & Error Recovery Guide

This document records known startup behaviors, diagnostic procedures, and recovery paths for the local Odoo 20 Enterprise Docker environment.

---

## 1. Diagnostic Decision Tree

```
Issue Detected
  │
  ├── Port Conflict (8070 already bound)
  │     └── Run: Get-NetTCPConnection -LocalPort 8070
  │     └── Resolution: Change ODOO_PORT in .env to another port (e.g., 8071).
  │
  ├── Database Connection Refused
  │     └── Check: docker compose logs db
  │     └── Verify: db container is running and healthy: docker compose ps db
  │     └── Verify credentials match between .env and config/odoo.conf
  │
  ├── Odoo Container Exits Immediately
  │     └── Check: docker compose logs odoo
  │     └── Verify permissions on config/odoo.conf and /var/lib/odoo
  │     └── Check for Python syntax error in mounted custom_addons
  │
  └── Module Not Found / Addon Path Error
        └── Verify addons_path in config/odoo.conf includes:
            /mnt/enterprise, /usr/lib/python3/dist-packages/addons, /usr/lib/python3/dist-packages/odoo/addons, /mnt/extra-addons
```

---

## 2. Common Errors and Resolutions

### A. "FATAL: password authentication failed for user 'odoo'"
- **Cause**: The PostgreSQL container volume was created with an earlier password, or credentials in `.env` and `config/odoo.conf` are out of sync.
- **Fix**: Never delete the database volume if data exists. Instead, update `config/odoo.conf` `db_password` to match the PostgreSQL user password, or change the user's password inside PostgreSQL:
  ```bash
  docker compose exec db psql -U odoo -d postgres -c "ALTER USER odoo WITH PASSWORD 'your_password';"
  ```

### B. "Could not execute wkhtmltopdf: [Errno 2] No such file or directory"
- **Cause**: Missing PDF renderer in image.
- **Status**: Pre-installed in `Dockerfile` using `apt-get install wkhtmltopdf`.

### C. File permissions on Windows mounts (/mnt/d/...)
- **Cause**: Windows WSL filesystem permissions can sometimes conflict with container non-root users.
- **Fix**: The image creates `/var/lib/odoo` as a Docker named volume (`odoo20_enterprise_odoo_data`), keeping native Linux POSIX ownership (`odoo:odoo`), completely bypassing Windows filesystem permission bottlenecks.

### D. Service Startup Failures During Image Build
- **Cause**: The Debian package's `postinst` script invokes `invoke-rc.d odoo start`, which fails in Docker build stages.
- **Fix**: The `Dockerfile` injects `/usr/sbin/policy-rc.d` returning code `101` before package installation, then removes it cleanly afterwards.
