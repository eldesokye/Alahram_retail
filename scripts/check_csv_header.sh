#!/bin/bash
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
cd "$SCRIPT_DIR/.."
docker compose exec -T odoo head -n 5 /usr/lib/python3/dist-packages/odoo/addons/stock/security/ir.access.csv

