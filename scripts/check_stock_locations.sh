#!/bin/bash
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
cd "$SCRIPT_DIR/.."
docker compose exec -T db psql -U odoo -d odoo20 -c "SELECT id, complete_name, usage FROM stock_location;"

