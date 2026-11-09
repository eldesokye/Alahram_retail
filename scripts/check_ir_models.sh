#!/bin/bash
cd /mnt/d/WORK/Odoo20-interbrise
docker compose exec -T db psql -U odoo -d odoo20 -c "SELECT model, name FROM ir_model WHERE model LIKE 'ir.%';"

