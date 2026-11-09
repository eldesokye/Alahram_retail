# Al Ahram Cookware - Smart Bridal Package POS Release and Rollback Guide

## 1. Release Identification & Pre-Deployment Checklist

- **Target Module**: `alahram_retail_demo` (within directory `ALAhram/alahram_retail_demo`)
- **Target Platform**: Odoo 20 Enterprise (WSL/Docker Ubuntu Linux host)
- **Database**: `odoo20`
- **Port**: Web interface on port `8070` (container internal `8069`)

### Pre-Deployment Verification Checklist:
- [x] All 65 unit and integration tests passing (`test_bridal_package_pos.py` & `test_pos_branch_reservation.py`).
- [x] Odoo ORM fields verified for Odoo 20 compatibility (`res.users` uses `group_ids`, not `groups_id`).
- [x] Database snapshot / pg_dump completed prior to upgrade.
- [x] No orphaned processes holding table locks on `alahram_bridal_configurator` or `stock_quant`.
- [x] Production POS sessions closed or warned before applying module upgrade.

---

## 2. Production Deployment Steps

### Step 1: Pre-Upgrade Database Backup
Execute a PostgreSQL dump before applying module changes:
```bash
docker exec -t odoo20_enterprise_db pg_dump -U odoo -d odoo20 -F c -b -v -f /var/lib/postgresql/data/odoo20_pre_bridal_release_$(date +%Y%m%d_%H%M%S).dump
```

### Step 2: Deploy Code Changes
Ensure the updated module directory `ALAhram/alahram_retail_demo` is synchronized to the container's addons path (`/mnt/extra-addons/alahram_retail_demo`).

### Step 3: Upgrade Module in Odoo 20
Run the module upgrade command inside the Odoo application container:
```bash
docker exec -i odoo20_enterprise_app odoo -c /etc/odoo/odoo.conf -d odoo20 -u alahram_retail_demo --stop-after-init
```

### Step 4: Restart Odoo Service Container
Restart the application container to refresh worker threads and asset bundles:
```bash
docker restart odoo20_enterprise_app
```

### Step 5: Post-Deployment Smoke Verification
1. Verify container status:
   ```bash
   docker ps --filter "name=odoo20_enterprise_app"
   ```
2. Verify HTTP 200 response on web login:
   ```bash
   curl -I http://localhost:8070/web/login
   ```
3. Open Point of Sale on a test terminal:
   - Verify **باكدج العروسة الذكي** button is rendered on the top action bar.
   - Open dialog, verify product suggestion, alternatives lookup, branch sourcing, and budget variance calculations.

---

## 3. Rollback Procedures

If an unforeseen operational issue occurs post-release, follow either the Hotfix Rollback or the Full Snapshot Rollback:

### Option A: Module Downgrade / Patch Rollback (Soft Rollback)
If the database schema has not been corrupted and only code regression is identified:
1. Revert `ALAhram/alahram_retail_demo` code to the previous Git commit tag:
   ```bash
   git checkout tags/pre-bridal-pos-integration -- ALAhram/alahram_retail_demo
   ```
2. Re-run module update:
   ```bash
   docker exec -i odoo20_enterprise_app odoo -c /etc/odoo/odoo.conf -d odoo20 -u alahram_retail_demo --stop-after-init
   docker restart odoo20_enterprise_app
   ```

### Option B: Full Database Restore (Hard Rollback)
If data corruption occurred:
1. Stop the application container to terminate active connections:
   ```bash
   docker stop odoo20_enterprise_app
   ```
2. Terminate active database sessions and restore snapshot:
   ```bash
   docker exec -i odoo20_enterprise_db psql -U odoo -d postgres -c "SELECT pg_terminate_backend(pid) FROM pg_stat_activity WHERE datname = 'odoo20' AND pid <> pg_backend_pid();"
   docker exec -i odoo20_enterprise_db dropdb -U odoo odoo20
   docker exec -i odoo20_enterprise_db createdb -U odoo -O odoo odoo20
   docker exec -i odoo20_enterprise_db pg_restore -U odoo -d odoo20 -v /var/lib/postgresql/data/<SNAPSHOT_FILE>.dump
   ```
3. Start the application container:
   ```bash
   docker start odoo20_enterprise_app
   ```
4. Verify system recovery at `http://localhost:8070/web/login`.

---

## 4. Maintenance and Monitoring

### Log Monitoring
To monitor real-time POS bridal package operations and cross-branch reservations:
```bash
docker logs -f --tail 200 odoo20_enterprise_app | grep -E "bridal|branch.reservation"
```

### PostgreSQL Performance Query
Monitor lock acquisition times on reservation tables:
```sql
SELECT pid, relation::regclass, mode, granted, query 
FROM pg_locks 
JOIN pg_stat_activity USING (pid) 
WHERE relation::regclass::text LIKE '%alahram%';
```

