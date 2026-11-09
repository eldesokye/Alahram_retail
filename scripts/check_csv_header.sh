#!/bin/bash
cd /mnt/d/WORK/Odoo20-interbrise
docker compose exec -T odoo head -n 5 /usr/lib/python3/dist-packages/odoo/addons/stock/security/ir.access.csv

