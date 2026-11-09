#!/bin/bash
cd /mnt/d/WORK/Odoo20-interbrise
docker compose exec -T db psql -U odoo -d odoo20 -c "SELECT table_name FROM information_schema.tables WHERE table_name LIKE '%res_groups%' OR table_name LIKE '%user%group%';"

