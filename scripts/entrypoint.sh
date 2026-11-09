#!/bin/bash
set -e

# Wait for database if HOST is set
if [ -n "$HOST" ]; then
    echo "Waiting for PostgreSQL at ${HOST}:${PORT:-5432}..."
    while ! pg_isready -h "$HOST" -p "${PORT:-5432}" -U "${USER:-odoo}" -q; do
        sleep 1
    done
    echo "PostgreSQL is ready."
fi

exec "$@"
