#!/usr/bin/env bash
# ─────────────────────────────────────────────────────────────────────────────
# SEO AI Employee — Setup Script
# Run this once on a fresh Linux VPS or macOS machine.
# ─────────────────────────────────────────────────────────────────────────────
set -euo pipefail

WORKSPACE_DIR="$HOME/.openclaw/workspace/seo"
SEO_PROJECT_DIR="$(cd "$(dirname "$0")/.." && pwd)"

echo "========================================"
echo " SEO AI Employee — Setup"
echo "========================================"
echo "Project: $SEO_PROJECT_DIR"
echo "Workspace: $WORKSPACE_DIR"
echo ""

# ── 1. Install OpenClaw ───────────────────────────────────────────────────────
echo "[1/7] Installing OpenClaw..."
if ! command -v openclaw &>/dev/null; then
    npm install -g openclaw@latest
    echo "  ✓ openclaw installed"
else
    echo "  ✓ openclaw already installed ($(openclaw --version 2>/dev/null || echo 'version unknown'))"
fi

# ── 2. Install uv (Python package manager) ────────────────────────────────────
echo "[2/7] Installing uv..."
if ! command -v uv &>/dev/null; then
    curl -LsSf https://astral.sh/uv/install.sh | sh
    export PATH="$HOME/.cargo/bin:$PATH"
    echo "  ✓ uv installed"
else
    echo "  ✓ uv already installed"
fi

# ── 3. Install Python dependencies ────────────────────────────────────────────
echo "[3/7] Installing Python dependencies..."
uv pip install --system \
    google-auth \
    google-auth-httplib2 \
    google-auth-oauthlib \
    google-api-python-client \
    requests \
    psycopg2-binary \
    playwright \
    beautifulsoup4 \
    lxml \
    scikit-learn \
    pandas \
    numpy \
    jinja2 \
    anthropic
echo "  ✓ Python deps installed"

# ── 4. Install Playwright browsers ────────────────────────────────────────────
echo "[4/7] Installing Playwright Chromium..."
python3 -m playwright install chromium
echo "  ✓ Chromium installed"

# ── 5. Set up workspace ───────────────────────────────────────────────────────
echo "[5/7] Setting up OpenClaw workspace..."
mkdir -p "$WORKSPACE_DIR"/{tools,playwright,screenshots,reports}

# Symlink or copy project files into workspace
for dir in tools playwright; do
    if [ ! -L "$WORKSPACE_DIR/$dir" ]; then
        if [ -d "$SEO_PROJECT_DIR/$dir" ]; then
            cp -r "$SEO_PROJECT_DIR/$dir/." "$WORKSPACE_DIR/$dir/"
            echo "  ✓ Copied $dir/ to workspace"
        fi
    fi
done

# Copy skills
SKILLS_TARGET="$HOME/.openclaw/workspace/skills"
mkdir -p "$SKILLS_TARGET"
for skill_dir in "$SEO_PROJECT_DIR/skills"/*/; do
    skill_name=$(basename "$skill_dir")
    cp -r "$skill_dir" "$SKILLS_TARGET/$skill_name"
done
echo "  ✓ Skills installed to $SKILLS_TARGET"

# Copy workflows
WORKFLOW_TARGET="$HOME/.openclaw/workspace/.agent/workflows"
mkdir -p "$WORKFLOW_TARGET"
cp "$SEO_PROJECT_DIR/workflows/"*.md "$WORKFLOW_TARGET/"
echo "  ✓ Workflows installed"

# ── 6. Set up OpenClaw config ─────────────────────────────────────────────────
echo "[6/7] Configuring OpenClaw..."
OPENCLAW_CONFIG="$HOME/.openclaw/openclaw.json5"
if [ ! -f "$OPENCLAW_CONFIG" ]; then
    cp "$SEO_PROJECT_DIR/openclaw.json5" "$OPENCLAW_CONFIG"
    echo "  ✓ openclaw.json5 installed"
else
    echo "  ! openclaw.json5 already exists — manually merge if needed"
    echo "    Source: $SEO_PROJECT_DIR/openclaw.json5"
fi

# Copy .env
ENV_FILE="$HOME/.openclaw/.env"
if [ ! -f "$ENV_FILE" ]; then
    cp "$SEO_PROJECT_DIR/config/.env.example" "$ENV_FILE"
    echo "  ✓ .env created at $ENV_FILE — EDIT THIS with your API keys"
else
    echo "  ! .env already exists at $ENV_FILE"
fi

# ── 7. Set up PostgreSQL ──────────────────────────────────────────────────────
echo "[7/7] PostgreSQL setup..."
if command -v psql &>/dev/null; then
    if [ -n "${DATABASE_URL:-}" ]; then
        psql "$DATABASE_URL" -f "$SEO_PROJECT_DIR/db/schema.sql" && \
            echo "  ✓ Schema applied to database" || \
            echo "  ! Schema apply failed — run manually: psql \$DATABASE_URL -f db/schema.sql"
    else
        echo "  ! DATABASE_URL not set — skipping schema apply"
        echo "    Run manually: psql \$DATABASE_URL -f $SEO_PROJECT_DIR/db/schema.sql"
    fi
else
    echo "  ! psql not found — install PostgreSQL and run schema manually"
fi

echo ""
echo "========================================"
echo " Setup complete!"
echo "========================================"
echo ""
echo "Next steps:"
echo "  1. Edit $ENV_FILE with your API keys"
echo "  2. Run: openclaw doctor  (verify setup)"
echo "  3. Run: openclaw onboard --install-daemon  (start the agent daemon)"
echo ""
echo "To register cron jobs (daily/weekly/monthly pipelines):"
echo "  Run: bash $SEO_PROJECT_DIR/scripts/register_crons.sh"
echo ""
