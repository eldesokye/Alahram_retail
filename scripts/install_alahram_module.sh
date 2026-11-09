#!/bin/bash
cd /mnt/d/WORK/Odoo20-interbrise
docker compose exec -T odoo /usr/bin/odoo -c /etc/odoo/odoo.conf -d odoo20 -i alahram_retail_demo --stop-after-init

