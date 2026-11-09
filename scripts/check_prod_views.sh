#!/bin/bash
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
cd "$SCRIPT_DIR/.."
docker compose exec -T db psql -U odoo -d odoo20 -c "SELECT name FROM ir_model_data WHERE model = 'ir.ui.view' AND name LIKE 'product_template%tree%';"

