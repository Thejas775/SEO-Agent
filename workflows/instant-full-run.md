---
description: "Instant full SEO run — given a website URL, immediately runs analysis, keyword research, content creation, technical audit, and generates a report. No waiting for scheduled runs."
agent: seo-reporter
---

# Instant Full SEO Run

You are the coordinator agent. The user has given you a website URL and wants a complete SEO analysis and action plan run right now.

**Target site:** `{{ SITE_URL }}`

Work through all phases below in order. Spawn sub-agents for parallel work where noted.

---

## Phase 1 — Setup & Site Discovery (5 min)

### 1.1 — Set environment for this run
```bash
export TARGET_URL="{{ SITE_URL }}"
export GSC_SITE_URL="{{ SITE_URL }}"
export AUDIT_TARGET_URL="{{ SITE_URL }}"
```

### 1.2 — Extract the domain
```python3
from urllib.parse import urlparse
domain = urlparse("{{ SITE_URL }}").netloc
print(domain)
```
Store the domain — you'll need it for competitor lookups.

### 1.3 — Quick site health check
```bash
python3 ~/.openclaw/workspace/seo/playwright/cwv_checker.py \
  --url "{{ SITE_URL }}" \
  --device both \
  --output /tmp/instant_cwv.json
```

---

## Phase 2 — Parallel Intelligence Gathering (10 min)

Spawn all three of these simultaneously using `sessions_spawn`. Do not wait for one before starting the next.

### Spawn A — SEO Analyst
Message: "Fetch and analyze Google Search Console data for {{ SITE_URL }} for the last 90 days. Find ranking drops, CTR opportunities, and quick wins. Save to database. Output results to /tmp/instant_gsc_analysis.json"

### Spawn B — SEO Auditor
Message: "Run a full technical SEO audit on {{ SITE_URL }}. Crawl up to 200 pages. Check broken links, missing meta tags, missing alt text, redirect chains, canonical tags. Save all issues to database. Output to /tmp/instant_audit.json"

### Spawn C — Keyword Strategist
Message: "Find the top 2 organic competitors for the domain extracted from {{ SITE_URL }} using DataForSEO. Then run a keyword gap analysis. Cluster the top 30 gap keywords by intent. Generate a content calendar for 4 articles. Save to database. Output clusters to /tmp/instant_keyword_clusters.json and calendar to /tmp/instant_calendar.json"

Wait for all three to complete before continuing to Phase 3.

---

## Phase 3 — Content Creation (15 min)

Once keyword clusters are ready at `/tmp/instant_keyword_clusters.json`:

Spawn `seo-writer` for the **top 2 highest-priority articles** from the calendar:
- Pass the cluster data
- Pass the competitor URLs found in Phase 2
- Instruction: "Write a full SEO article. Save to database as draft. Then spawn seo-executor to publish."

The writer will cascade to the executor automatically.

---

## Phase 4 — Quick Wins Execution (5 min)

Once GSC analysis is complete at `/tmp/instant_gsc_analysis.json`:

Read the CTR opportunities:
```python3
import json
data = json.load(open('/tmp/instant_gsc_analysis.json'))
wins = [p for p in data.get('ctr_opportunities', []) if p['position'] <= 10][:5]
json.dump(wins, open('/tmp/instant_quick_wins.json', 'w'))
print(f"{len(wins)} quick wins found")
```

If wins exist, spawn `seo-executor`:
"Update meta titles and descriptions for the pages in /tmp/instant_quick_wins.json. Generate improved metadata for each page and apply to the CMS."

---

## Phase 5 — Auto-Fix Technical Issues (5 min)

Once audit is complete:
```bash
python3 ~/.openclaw/workspace/seo/tools/db.py get_fixable_issues \
  --severity critical,high \
  --types missing_meta_description,missing_alt_text,meta_title_too_long \
  --limit 20 \
  --output /tmp/instant_fixable.json
```

If fixable issues exist, spawn `seo-executor`:
"Apply the auto-fixable technical SEO issues from /tmp/instant_fixable.json to the CMS."

---

## Phase 6 — Generate Full Report (5 min)

Once all phases are complete, generate the full report:

```bash
python3 ~/.openclaw/workspace/seo/tools/report_generator.py \
  --period weekly \
  --output /tmp/instant_seo_report_$(date +%Y%m%d).html
```

Save to database:
```bash
python3 ~/.openclaw/workspace/seo/tools/db.py save_report \
  --file /tmp/instant_seo_report_$(date +%Y%m%d).html \
  --period instant \
  --date $(date +%Y-%m-%d)
```

---

## Phase 7 — Final Summary

Print this summary in chat when everything is done:

```
✅ Full SEO Run Complete — {{ SITE_URL }}
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
⏱  Total time: [X min]

📊 ANALYSIS
  Ranking drops detected:    [N]
  CTR opportunities:         [N]
  Quick wins (pos 11-20):    [N]

🔬 TECHNICAL AUDIT
  Pages crawled:             [N]
  Critical issues:           [N]
  High issues:               [N]
  Auto-fixed:                [N]

🔍 KEYWORD RESEARCH
  Keyword gaps found:        [N]
  Clusters created:          [N]
  Articles planned:          [N]

✍️  CONTENT
  Articles written:          [N]
  Articles published:        [N]
  Meta updates applied:      [N]

📈 REPORT
  Saved to: /tmp/instant_seo_report_[date].html
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
Top 3 actions still needed:
  1. [action]
  2. [action]
  3. [action]
```
