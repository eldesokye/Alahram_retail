#!/bin/bash
cd /mnt/d/WORK/Odoo20-interbrise
docker compose exec -T odoo /usr/bin/odoo -c /etc/odoo/odoo.conf -d odoo20 -i point_of_sale,purchase,stock --stop-after-init

