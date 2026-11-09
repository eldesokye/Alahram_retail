#!/bin/bash
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
cd "$SCRIPT_DIR/.."
docker compose exec -T odoo /usr/bin/odoo -c /etc/odoo/odoo.conf -d odoo20 -i point_of_sale,purchase,stock --stop-after-init

