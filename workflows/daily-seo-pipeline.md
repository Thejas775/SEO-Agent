---
description: "Daily SEO pipeline — pull ranking data, detect quick wins, update titles/descriptions"
schedule: "0 7 * * *"
agent: seo-analyst
---

# Daily SEO Pipeline

Runs every day at 07:00. Pulls fresh GSC data, identifies quick wins, and dispatches metadata updates.

## Step 1 — Pull Google Search Console Data

Fetch the last 7 days of performance data for the site:

```bash
python3 ~/.openclaw/workspace/seo/tools/gsc_tool.py \
  --mode fetch \
  --site "$GSC_SITE_URL" \
  --days 7 \
  --dimensions page,query \
  --output /tmp/gsc_daily.json
```

Save to database:
```bash
python3 ~/.openclaw/workspace/seo/tools/db.py save_rankings \
  --data /tmp/gsc_daily.json \
  --source gsc \
  --date $(date +%Y-%m-%d)
```

## Step 2 — Run Analysis

Analyze the data for drops, opportunities, and quick wins:

```bash
python3 ~/.openclaw/workspace/seo/tools/gsc_tool.py \
  --mode analyze \
  --site "$GSC_SITE_URL" \
  --days 7 \
  --compare-days 14 \
  --output /tmp/daily_analysis.json
```

Save analysis findings:
```bash
python3 ~/.openclaw/workspace/seo/tools/db.py save_analysis \
  --file /tmp/daily_analysis.json \
  --agent seo-analyst
```

## Step 3 — Identify Quick Wins

From the analysis, extract:

**CTR Quick Wins** — pages with position 1–10 but CTR below 2%:
These need new meta titles/descriptions. Extract them:

```bash
python3 -c "
import json
data = json.load(open('/tmp/daily_analysis.json'))
wins = [p for p in data['ctr_opportunities'] if p['position'] <= 10]
json.dump(wins[:10], open('/tmp/ctr_wins.json', 'w'))
print(f'Found {len(wins)} CTR quick wins')
"
```

**Ranking Quick Wins** — keywords at position 11–20 (close to page 1):
```bash
python3 -c "
import json
data = json.load(open('/tmp/daily_analysis.json'))
wins = [p for p in data.get('quick_wins', []) if 11 <= p['position'] <= 20]
json.dump(wins[:10], open('/tmp/ranking_wins.json', 'w'))
print(f'Found {len(wins)} ranking quick wins')
"
```

## Step 4 — Generate New Metadata for CTR Wins

If there are CTR quick wins (list is non-empty):

For each page in `/tmp/ctr_wins.json`, generate improved meta title and meta description.

**For each page:**
1. Fetch the current meta title and description from the DB
2. Generate a new meta title that:
   - Includes the primary keyword
   - Has a compelling value proposition
   - Is exactly 50–60 characters
3. Generate a new meta description that:
   - Answers the search intent directly
   - Includes a call to action
   - Is exactly 140–160 characters
4. Save the proposed changes to the database with status `pending_review`

```bash
python3 ~/.openclaw/workspace/seo/tools/db.py save_meta_proposals \
  --file /tmp/ctr_wins.json \
  --status pending_review
```

## Step 5 — Auto-Apply High-Confidence Updates

For pages where the current meta title is:
- Missing entirely, OR
- Below 30 characters (too short), OR
- Above 70 characters (too long)

These are safe to auto-apply. Spawn `seo-executor` to update them:

```bash
python3 ~/.openclaw/workspace/seo/tools/db.py get_meta_proposals \
  --status pending_review \
  --confidence high \
  --output /tmp/auto_apply.json
```

If `/tmp/auto_apply.json` is non-empty:
Use `sessions_spawn` to spawn `seo-executor` with message:
"Apply metadata updates from /tmp/auto_apply.json to the CMS"

## Step 6 — Log and Summarize

Print the daily summary in the standard format:
```
📊 Daily SEO — [date]
━━━━━━━━━━━━━━━━━━━━━
🔴 Ranking Drops: [N]
🟡 CTR Wins: [N]
🟢 Quick Wins: [N]
⚡ Auto-updates queued: [N]
```

## Error Handling

- If GSC fetch fails (API error), log the error and exit. Do not proceed with stale data.
- If the analysis finds 0 results, confirm GSC connectivity and log a warning.
- If `seo-executor` spawn fails, log the failure but do not retry — will be picked up in next run.
