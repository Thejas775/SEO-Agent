---
name: postgres-seo
description: "Read and write SEO data (keywords, articles, rankings, audit issues) to the PostgreSQL database"
metadata:
  {
    "openclaw": {
      "emoji": "🗄️",
      "primaryEnv": "DATABASE_URL",
      "requires": {
        "bins": ["python3", "psql"],
        "env": ["DATABASE_URL"]
      },
      "install": [
        {
          "id": "uv",
          "kind": "uv",
          "module": "psycopg2-binary",
          "label": "Install psycopg2"
        }
      ]
    }
  }
---

# PostgreSQL SEO Database Skill

All SEO data is persisted in PostgreSQL. All agents read from and write to this shared database.

## Database Interface

```bash
# Universal DB CLI
python3 ~/.openclaw/workspace/seo/tools/db.py [command] [options]
```

## Key Commands

```bash
# Keyword data
db.py save_keywords --clusters FILE
db.py get_keyword --keyword "..."
db.py get_cached_keyword_data --keyword "..." --max-age-days 7

# Articles
db.py save_article --title "..." --content FILE --status draft
db.py get_article --id N
db.py update_article_status --id N --status published
db.py find_internal_links --keywords "..."

# Rankings
db.py save_rankings --data FILE
db.py get_ranking_changes --days 7

# Audit
db.py save_audit --crawl FILE --issues FILE
db.py get_fixable_issues --severity high,medium
db.py resolve_issue --id N

# Reports
db.py save_report --file FILE --period weekly
db.py get_priorities --limit 5

# Analysis
db.py save_analysis --file FILE --agent seo-analyst
```

## Core Tables

- `keywords` — keyword research data with volume, difficulty, CPC
- `keyword_clusters` — grouped keyword clusters with intent labels
- `content_calendar` — planned and published content schedule
- `articles` — content drafts and published articles
- `rankings` — daily/weekly ranking snapshots
- `audit_issues` — technical SEO issues with severity and status
- `audit_runs` — audit run history
- `reports` — generated report files
- `gsc_data` — raw Google Search Console performance data

## Schema

Full schema at: `~/.openclaw/workspace/seo/db/schema.sql`

## Connection

DATABASE_URL format: `postgresql://user:password@host:5432/seo_db`
