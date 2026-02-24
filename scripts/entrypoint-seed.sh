#!/bin/sh
# Entrypoint that seeds the database then starts the app.
# Used by docker-compose.seed.yml.

set -e

echo "Running database seed..."
python -c "from scripts.seed import seed_database; seed_database()"

echo "Starting application..."
exec uvicorn app.main:app --host 0.0.0.0 --port 8000
