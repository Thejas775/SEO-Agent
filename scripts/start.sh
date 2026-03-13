#!/usr/bin/env bash
# Start everything: OpenClaw daemon + UI
set -euo pipefail

ROOT="$(cd "$(dirname "$0")/.." && pwd)"

# Load .env
ENV_FILE="$HOME/.openclaw/.env"
[ -f "$ENV_FILE" ] && set -a && source "$ENV_FILE" && set +a

echo "Starting SEO AI Employee..."

# Start OpenClaw if not running
if ! openclaw status &>/dev/null; then
    echo "Starting OpenClaw daemon..."
    openclaw start
fi
echo "✓ OpenClaw running"

# Install UI deps if needed
pip install -q -r "$ROOT/ui/requirements.txt"

# Start UI
echo "Starting UI on http://localhost:8000 ..."
cd "$ROOT"
uvicorn ui.app:app --host 0.0.0.0 --port 8000
