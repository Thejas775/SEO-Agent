#!/usr/bin/env bash
# Register the three SEO pipeline cron jobs with OpenClaw's cron system.
# Run after setup.sh and after OpenClaw daemon is running.
set -euo pipefail

WORKSPACE="$HOME/.openclaw/workspace"

echo "Registering SEO pipeline cron jobs..."

# Daily pipeline — 07:00 every day
openclaw cron create \
  --name "seo-daily-pipeline" \
  --schedule "0 7 * * *" \
  --agent "seo-analyst" \
  --message "Run the daily SEO pipeline. Follow the workflow at .agent/workflows/daily-seo-pipeline.md" \
  --description "Daily: pull GSC data, detect quick wins, update metadata"

echo "  ✓ Daily pipeline registered (07:00 daily)"

# Weekly pipeline — 08:00 every Monday
openclaw cron create \
  --name "seo-weekly-pipeline" \
  --schedule "0 8 * * 1" \
  --agent "seo-analyst" \
  --message "Run the weekly SEO pipeline. Follow the workflow at .agent/workflows/weekly-seo-pipeline.md" \
  --description "Weekly: competitor research, keyword clustering, article generation, report"

echo "  ✓ Weekly pipeline registered (08:00 Mondays)"

# Monthly audit — 06:00 on the 1st of each month
openclaw cron create \
  --name "seo-monthly-audit" \
  --schedule "0 6 1 * *" \
  --agent "seo-auditor" \
  --message "Run the monthly technical SEO audit. Follow the workflow at .agent/workflows/monthly-seo-audit.md" \
  --description "Monthly: full site crawl, detect issues, auto-fix, audit report"

echo "  ✓ Monthly audit registered (06:00, 1st of month)"

echo ""
echo "All cron jobs registered. View with: openclaw cron list"
