#!/bin/bash
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
cd "$SCRIPT_DIR/.."
docker compose exec -T db psql -U odoo -d odoo20 -c "SELECT column_name FROM information_schema.columns WHERE table_name = 'stock_location' AND column_name LIKE '%scrap%';"

