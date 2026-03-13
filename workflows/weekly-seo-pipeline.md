---
description: "Weekly SEO pipeline — competitor research, keyword clustering, article generation, publishing, and weekly report"
schedule: "0 8 * * 1"
agent: seo-analyst
---

# Weekly SEO Pipeline

Runs every Monday at 08:00. Full pipeline: research → write → publish → report.

## Phase 1 — Competitive Intelligence (seo-analyst)

### Step 1.1 — Pull Weekly GSC Summary

```bash
python3 ~/.openclaw/workspace/seo/tools/gsc_tool.py \
  --mode analyze \
  --site "$GSC_SITE_URL" \
  --days 28 \
  --output /tmp/weekly_gsc.json
```

### Step 1.2 — Fetch Competitor Keyword Data

Run competitor keyword fetches in parallel. Spawn sub-agents for each competitor to speed this up:

```bash
python3 ~/.openclaw/workspace/seo/tools/dataforseo_tool.py \
  --mode competitor_keywords \
  --domain "$COMPETITOR_1" \
  --top 300 \
  --output /tmp/comp1_keywords.json
```

```bash
python3 ~/.openclaw/workspace/seo/tools/dataforseo_tool.py \
  --mode competitor_keywords \
  --domain "$COMPETITOR_2" \
  --top 300 \
  --output /tmp/comp2_keywords.json
```

### Step 1.3 — Find Keyword Gaps

```bash
python3 ~/.openclaw/workspace/seo/tools/dataforseo_tool.py \
  --mode keyword_gap \
  --our-domain "$GSC_SITE_URL" \
  --competitors "$COMPETITOR_1,$COMPETITOR_2" \
  --output /tmp/keyword_gaps.json
```

Save everything to DB:
```bash
python3 ~/.openclaw/workspace/seo/tools/db.py save_analysis \
  --file /tmp/weekly_gsc.json \
  --agent seo-analyst
```

## Phase 2 — Keyword Strategy (spawn keyword-strategist)

Use `sessions_spawn` to spawn `keyword-strategist` with this message:
"Process keyword gaps from /tmp/keyword_gaps.json. Cluster them by intent, score by priority, and generate a 4-article content calendar for this week. Save to database and then spawn seo-writer for each article."

Wait for `keyword-strategist` to confirm calendar is saved.

## Phase 3 — Content Creation (keyword-strategist spawns seo-writer)

`keyword-strategist` will spawn `seo-writer` for each article on the calendar.
`seo-writer` will save each article to the database with status `draft`.
`seo-writer` will then spawn `seo-executor` for each article.

This cascades automatically — no manual intervention needed.

## Phase 4 — Monitor Execution

Poll the database every 10 minutes to check article publish status:

```bash
python3 ~/.openclaw/workspace/seo/tools/db.py get_articles \
  --status draft,publishing \
  --week $(date +%Y-%W) \
  --output /tmp/article_status.json
```

Continue when all articles are `published` or `failed`.

## Phase 5 — Generate Weekly Report (spawn seo-reporter)

Use `sessions_spawn` to spawn `seo-reporter` with message:
"Generate the weekly SEO report for the week ending $(date +%Y-%m-%d). Include ranking changes, articles published, issues fixed, and top 5 priorities for next week."

## Phase 6 — Send Report Summary

After reporter completes, print the summary in chat and save report path to DB.

## Error Recovery

- If Phase 2 fails (keyword strategy): log error, skip content creation, still run report on available data
- If individual article fails to publish: mark as `failed`, continue with others, include in report
- If reporter fails: log error, generate minimal text summary inline

## Completion Message

```
✅ Weekly Pipeline Complete — [date]
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
📊 Analysis: done
🔍 Keyword clusters: [N]
📝 Articles written: [N]
⚡ Articles published: [N/N]
📈 Report: /tmp/seo_report_[date].html
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
Next run: [next Monday at 08:00]
```
