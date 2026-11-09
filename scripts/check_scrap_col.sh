#!/bin/bash
cd /mnt/d/WORK/Odoo20-interbrise
docker compose exec -T db psql -U odoo -d odoo20 -c "SELECT column_name FROM information_schema.columns WHERE table_name = 'stock_location' AND column_name LIKE '%scrap%';"

