#!/usr/bin/env bash
# startup.sh — run before the API server starts on Render.com
# Initialises the DB tables and starts the API.
# Qdrant vectors are already in Qdrant Cloud (uploaded once from local).

set -e

echo "=== CyberSense startup ==="

# 1. Ensure SQLite tables exist
python -c "
import asyncio
from cybersense.db.session import init_db
asyncio.run(init_db())
print('DB tables ready.')
"

# 2. Start the API
exec uvicorn cybersense.api.main:app --host 0.0.0.0 --port "${PORT:-8000}"
