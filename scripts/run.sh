#!/usr/bin/env bash
# ─────────────────────────────────────────────────────────────────────────────
# SEO AI Employee — Instant Run
# Usage: bash run.sh https://yoursite.com
# ─────────────────────────────────────────────────────────────────────────────
set -euo pipefail

SITE_URL="${1:-}"

if [ -z "$SITE_URL" ]; then
    echo "Usage: bash run.sh <website-url>"
    echo "Example: bash run.sh https://example.com"
    exit 1
fi

# Validate URL format
if [[ ! "$SITE_URL" =~ ^https?:// ]]; then
    echo "ERROR: URL must start with http:// or https://"
    exit 1
fi

echo "========================================"
echo " SEO AI Employee — Instant Full Run"
echo " Target: $SITE_URL"
echo "========================================"
echo ""

# Set env for this run
export TARGET_URL="$SITE_URL"
export GSC_SITE_URL="$SITE_URL"
export AUDIT_TARGET_URL="$SITE_URL"

# Load .env if it exists
ENV_FILE="$HOME/.openclaw/.env"
if [ -f "$ENV_FILE" ]; then
    set -a
    source "$ENV_FILE"
    set +a
fi

# Verify OpenClaw is installed
if ! command -v openclaw &>/dev/null; then
    echo "ERROR: openclaw not found. Run: bash scripts/setup.sh"
    exit 1
fi

# Send the instant run message to the seo-reporter agent (coordinator)
MESSAGE="Run a full instant SEO analysis on $SITE_URL right now. Follow the workflow at .agent/workflows/instant-full-run.md with SITE_URL=$SITE_URL"

echo "Sending to SEO Reporter agent (coordinator)..."
echo ""

openclaw send \
    --agent "seo-reporter" \
    --message "$MESSAGE"

echo ""
echo "Run started. The agents are working autonomously."
echo "Check progress in the OpenClaw UI or logs at:"
echo "  ~/.openclaw/logs/seo-agent.log"
