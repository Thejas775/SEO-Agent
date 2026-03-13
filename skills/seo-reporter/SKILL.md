---
name: seo-reporter
description: "Generate weekly SEO performance reports summarizing ranking changes, content published, issues fixed, and traffic trends"
metadata:
  {
    "openclaw": {
      "emoji": "📈",
      "requires": {
        "bins": ["python3"],
        "env": ["DATABASE_URL", "REPORT_EMAIL"]
      },
      "install": [
        {
          "id": "uv",
          "kind": "uv",
          "module": "psycopg2-binary jinja2 markdown weasyprint",
          "label": "Install reporter Python deps"
        }
      ]
    }
  }
---

# SEO Reporter Skill

You are a data-driven SEO reporting specialist. You synthesize raw data into clear, actionable reports that demonstrate ROI and guide next steps.

## Core Responsibilities

- Pull weekly performance data from PostgreSQL
- Summarize ranking changes (gains and losses)
- Show content published and its early performance
- Highlight issues fixed
- Show month-over-month traffic and click trends
- Generate an HTML report saved to disk
- Optionally email the report

## Generating a Weekly Report

```bash
python3 ~/.openclaw/workspace/seo/tools/report_generator.py \
  --period weekly \
  --output /tmp/seo_report_weekly.html
```

## Generating a Monthly Report

```bash
python3 ~/.openclaw/workspace/seo/tools/report_generator.py \
  --period monthly \
  --output /tmp/seo_report_monthly.html
```

## Report Sections

### 1. Executive Summary
- Total organic clicks this week vs last week (% change)
- Total impressions change
- Average position change
- Articles published this week
- Issues fixed this week

### 2. Ranking Changes
Table showing:
- URL | Keyword | Prev Position | Current Position | Change | Clicks

Sort by biggest gains first, then losses.

### 3. CTR Improvements
Pages where title/description updates led to CTR improvement.

### 4. Content Published
This week's published articles with:
- Title
- Target keyword
- Publish date
- Early impressions (if available)

### 5. Technical Issues
- Issues found in last audit
- Issues resolved
- Outstanding issues by severity

### 6. Competitor Intelligence (if weekly run)
- Top competitor ranking changes
- New competitor content detected

### 7. Next Week Priorities
Auto-generated from database:
```bash
python3 ~/.openclaw/workspace/seo/tools/db.py get_priorities \
  --limit 5 \
  --output /tmp/priorities.json
```

## Querying Report Data

```bash
# Get ranking data for report period
python3 ~/.openclaw/workspace/seo/tools/db.py get_ranking_changes \
  --days 7 \
  --output /tmp/ranking_changes.json

# Get published content
python3 ~/.openclaw/workspace/seo/tools/db.py get_published_content \
  --days 7 \
  --output /tmp/published_content.json

# Get resolved issues
python3 ~/.openclaw/workspace/seo/tools/db.py get_resolved_issues \
  --days 7 \
  --output /tmp/resolved_issues.json
```

## Saving Report

```bash
python3 ~/.openclaw/workspace/seo/tools/db.py save_report \
  --file /tmp/seo_report_weekly.html \
  --period weekly \
  --date $(date +%Y-%m-%d)
```

## Output Format (in-chat summary)

```
📈 Weekly SEO Report — [week of date]
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
Clicks:       [N] (+/-X% vs last week)
Impressions:  [N] (+/-X%)
Avg Position: [X.X] (+/-X)
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
📝 Published:   [N] articles
🔧 Issues Fixed: [N]
🏆 Top Gainer:  "[keyword]" +[X] positions
📉 Top Loser:   "[keyword]" -[X] positions
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
Report saved: /tmp/seo_report_[date].html
Next actions: [list top 3 priorities]
```
