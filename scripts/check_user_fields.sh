#!/bin/bash
cd /mnt/d/WORK/Odoo20-interbrise
docker compose exec -T db psql -U odoo -d odoo20 -c "SELECT name, ttype, relation FROM ir_model_fields WHERE model = 'res.users' AND relation = 'res.groups';"

