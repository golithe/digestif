#!/bin/bash
echo "=== Running script at $(date) ==="

# Source environment variables (written at container startup)
set -a
source /etc/environment
set +a
echo "Environment variables loaded"

# The pipeline parses untrusted web content, so it runs as nobody; root only
# reads /etc/environment (chmod 600) and keeps cron's stdout redirect open.
exec setpriv --reuid=nobody --regid=nogroup --init-groups --no-new-privs \
    /app/.venv/bin/python -u /app/src/main.py 2>&1
