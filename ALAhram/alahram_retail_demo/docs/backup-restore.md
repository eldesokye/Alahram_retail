# Odoo 20 Enterprise - Backup and Restore Operations

This guide covers verified procedures for backing up and restoring databases and the filestore in this environment.

---

## 1. Quick Backup

### Method A: Web Interface (Recommended for Development)
1. Open `http://localhost:8070/web/database/manager`.
2. Enter your master password (`ODOO_ADMIN_PASSWORD` from `.env`).
3. Click **Backup** next to your database.
4. Select format: **zip (includes filestore)**.
5. Save the `.zip` file locally into `backups/`.

### Method B: Command Line (Automated / Scripted)
```bash
# Set database name
DB_NAME="odoo20_dev"
BACKUP_DATE=$(date +%Y%m%d_%H%M%S)

# 1. Dump PostgreSQL database
docker compose exec -T db pg_dump -U odoo -Fc "$DB_NAME" > "backups/${DB_NAME}_${BACKUP_DATE}.dump"

# 2. Archive filestore
docker compose exec -T odoo tar -czf - -C /var/lib/odoo/filestore "$DB_NAME" > "backups/${DB_NAME}_filestore_${BACKUP_DATE}.tar.gz"
```

---

## 2. Quick Restore

### Method A: Web Interface
1. Open `http://localhost:8070/web/database/manager`.
2. Enter master password (`ODOO_ADMIN_PASSWORD`).
3. Click **Restore Database**.
4. Select the `.zip` file and enter a target database name.
5. Choose **This database is a copy** to prevent UUID clashes with production.

### Method B: Command Line
```bash
DB_NAME="odoo20_dev"
BACKUP_FILE="backups/odoo20_dev_20261030.dump"
FILESTORE_ARCHIVE="backups/odoo20_dev_filestore_20261030.tar.gz"

# 1. Create database in PostgreSQL
docker compose exec -T db createdb -U odoo "$DB_NAME"

# 2. Restore PostgreSQL schema & records
docker compose exec -T db pg_restore -U odoo -d "$DB_NAME" < "$BACKUP_FILE"

# 3. Restore filestore
docker compose exec -T odoo mkdir -p "/var/lib/odoo/filestore/$DB_NAME"
docker compose exec -i odoo tar -xzf - -C "/var/lib/odoo/filestore/$DB_NAME" < "$FILESTORE_ARCHIVE"
```
