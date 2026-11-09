#!/bin/bash
cd /mnt/d/WORK/Odoo20-interbrise
docker compose exec -T db psql -U odoo -d odoo20 -c "SELECT name FROM ir_model_data WHERE model = 'res.groups' AND name LIKE '%sale%';"

