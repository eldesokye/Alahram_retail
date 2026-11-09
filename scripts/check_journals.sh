#!/bin/bash
cd /mnt/d/WORK/Odoo20-interbrise
docker compose exec -T db psql -U odoo -d odoo20 -c "SELECT id, name, code, type FROM account_journal;"

