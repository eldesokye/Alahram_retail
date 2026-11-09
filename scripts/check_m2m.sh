#!/bin/bash
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
cd "$SCRIPT_DIR/.."
docker compose exec -T db psql -U odoo -d odoo20 -c "SELECT table_name FROM information_schema.tables WHERE table_name LIKE '%res_groups%' OR table_name LIKE '%user%group%';"

