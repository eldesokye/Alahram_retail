#!/bin/bash
cd /mnt/d/WORK/Odoo20-interbrise
docker compose exec -T db psql -U odoo -d odoo20 -c "SELECT name, state FROM ir_module_module WHERE name IN ('point_of_sale', 'sale_management', 'purchase', 'stock', 'account', 'account_accountant');"

