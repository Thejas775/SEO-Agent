# Claude Memory — SEO AI Employee Project

Copy this into your Claude memory on the other PC so it has full context.

---

## What This Project Is

A fully autonomous SEO AI Employee built on the OpenClaw agent framework.
The system runs 24/7, automatically researches keywords, writes SEO articles,
publishes them to the CMS, fixes technical issues, and sends weekly reports —
all without human intervention.

## Project Location

```
~/Desktop/Personal Projects/SEO/
```

## Tech Stack

- **Agent runtime:** OpenClaw (self-hosted, runs as daemon)
- **LLM:** Claude API (claude-sonnet-4-6 primary, claude-haiku-4-5 fallback)
- **Browser automation:** Playwright (Python)
- **Database:** PostgreSQL
- **SEO data:** Google Search Console API + DataForSEO API
- **CMS support:** WordPress, Webflow, Shopify
- **UI:** FastAPI + WebSockets + vanilla HTML/JS frontend
- **Config:** ~/.openclaw/.env for all API keys

## The 6 Agents

| Agent ID | Name | Role |
|---|---|---|
| seo-analyst | Aria | GSC data analysis, ranking drops, CTR opportunities |
| keyword-strategist | Kai | Keyword gaps, clustering, content calendar |
| seo-writer | Nova | Full article writing, meta, schema markup |
| seo-executor | Rex | CMS login, publish articles, update metadata |
| seo-auditor | Scout | Full site crawl, technical issues, CWV |
| seo-reporter | Riley | Weekly/monthly HTML reports (also coordinator) |

## Agent Cascade (how tasks flow automatically)

```
seo-analyst
  → sessions_spawn keyword-strategist  (when keyword gaps found)
      → sessions_spawn seo-writer       (for each calendar entry)
          → sessions_spawn seo-executor  (after article drafted)

seo-analyst → sessions_spawn seo-reporter  (weekly)
seo-auditor → sessions_spawn seo-executor  (auto-fixable issues)
seo-reporter → coordinates the instant full run
```

## Scheduled Pipelines

- **Daily 07:00** — `seo-analyst` runs `workflows/daily-seo-pipeline.md`
  Pull GSC data, find quick wins, update meta titles/descriptions
- **Monday 08:00** — `seo-analyst` runs `workflows/weekly-seo-pipeline.md`
  Competitor research → keyword clusters → write articles → publish → report
- **1st of month 06:00** — `seo-auditor` runs `workflows/monthly-seo-audit.md`
  Full crawl, detect issues, auto-fix, audit report

## Instant Run

User inputs a URL → all phases run immediately (not waiting for schedule):
- `workflows/instant-full-run.md` — the coordinator workflow
- `scripts/run.sh https://yoursite.com` — terminal trigger
- UI input box — browser trigger

## File Structure

```
SEO/
├── openclaw.json5              ← 6 agents defined here
├── skills/
│   ├── seo-analyst/SKILL.md
│   ├── keyword-strategist/SKILL.md
│   ├── seo-writer/SKILL.md
│   ├── seo-executor/SKILL.md
│   ├── seo-auditor/SKILL.md
│   ├── seo-reporter/SKILL.md
│   ├── google-search-console/SKILL.md
│   ├── dataforseo/SKILL.md
│   ├── playwright-seo/SKILL.md
│   └── postgres-seo/SKILL.md
├── workflows/
│   ├── daily-seo-pipeline.md
│   ├── weekly-seo-pipeline.md
│   ├── monthly-seo-audit.md
│   └── instant-full-run.md
├── tools/
│   ├── gsc_tool.py             ← Google Search Console API
│   ├── dataforseo_tool.py      ← DataForSEO API (keywords, SERP, gaps)
│   ├── keyword_clusterer.py    ← TF-IDF + k-means clustering
│   ├── content_calendar.py     ← 4-week content schedule generator
│   ├── site_crawler.py         ← full site crawler + issue detector
│   ├── report_generator.py     ← HTML report with Jinja2
│   └── db.py                   ← unified DB interface (all agents use this)
├── playwright/
│   ├── wordpress_publisher.py  ← publish + meta via WP REST API
│   ├── webflow_editor.py       ← Webflow CMS API
│   ├── shopify_editor.py       ← Shopify Admin API
│   └── cwv_checker.py          ← LCP/CLS/TTFB measurement
├── db/
│   └── schema.sql              ← 12 tables + 3 views
├── ui/
│   ├── app.py                  ← FastAPI backend + WebSocket
│   └── static/index.html       ← Frontend (URL input, live updates, report)
├── config/.env.example         ← all env vars template
├── scripts/
│   ├── setup.sh                ← one-command full install
│   ├── register_crons.sh       ← registers 3 cron jobs with OpenClaw
│   ├── run.sh                  ← instant run from terminal
│   └── start.sh                ← starts OpenClaw + UI together
├── CREDENTIALS_GUIDE.md        ← how to get every API key
├── HOW_TO_RUN.md               ← full setup + run instructions
└── CLAUDE_MEMORY.md            ← this file
```

## Database Tables

```
gsc_data              ← raw GSC performance data
keywords              ← keyword research results
keyword_clusters      ← clustered keyword groups
content_calendar      ← planned + published content schedule
articles              ← drafted and published articles
audit_runs            ← audit run history
audit_issues          ← technical SEO issues with severity
meta_proposals        ← suggested title/description updates
seo_analysis_runs     ← analysis run history
competitor_keywords   ← competitor keyword data
seo_priorities        ← action priority queue
reports               ← generated HTML reports
```

## How to Run

```bash
# Full setup (first time only)
bash scripts/setup.sh

# Fill API keys
nano ~/.openclaw/.env

# Apply DB schema
psql $DATABASE_URL -f db/schema.sql

# Start OpenClaw daemon
openclaw onboard --install-daemon

# Register scheduled pipelines
bash scripts/register_crons.sh

# Start UI
bash scripts/start.sh
# → open http://localhost:8000

# Instant run on any site (terminal)
bash scripts/run.sh https://yoursite.com
```

## Key Things to Know

1. **OpenClaw is required** for autonomous agent behavior. Without it the agents
   cannot spawn sub-agents, make autonomous decisions, or take action on the CMS.

2. **Skills are Markdown files** — they inject instructions into each agent's
   system prompt. To change agent behavior, edit the relevant SKILL.md.

3. **Workflows are Markdown docs** — the LLM reads and follows them step by step.
   They are NOT code — they are instructions the agent interprets.

4. **The db.py tool is the single DB interface** — all agents call it via
   subprocess. Never query PostgreSQL directly from agent code.

5. **Screenshots are saved** for every CMS action at:
   `~/.openclaw/workspace/seo/screenshots/[date]/`

6. **DataForSEO and GSC are optional** — the system still works without them
   (auditor, writer, executor all function). You just lose keyword data + rankings.

7. **The UI talks to OpenClaw's gateway** — it does NOT bypass OpenClaw.
   OpenClaw must be running for the UI's instant run to trigger real agent actions.
