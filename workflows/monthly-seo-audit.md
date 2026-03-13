---
description: "Monthly full technical SEO audit — crawl, detect all issues, auto-fix eligible ones, generate audit report"
schedule: "0 6 1 * *"
agent: seo-auditor
---

# Monthly Technical SEO Audit

Runs on the 1st of every month at 06:00. Full crawl + issue detection + auto-fix + audit report.

## Phase 1 — Full Site Crawl

### Step 1.1 — Run Crawler

```bash
python3 ~/.openclaw/workspace/seo/tools/site_crawler.py \
  --url "$AUDIT_TARGET_URL" \
  --max-pages 1000 \
  --respect-robots true \
  --follow-external false \
  --timeout 30 \
  --output /tmp/crawl_$(date +%Y%m).json
```

This produces a full site map with for every URL:
- HTTP status code
- Meta title (present/missing/length)
- Meta description (present/missing/length)
- H1 count
- Image alt text coverage
- Canonical tag
- Robots meta
- Redirect chain length
- Internal/external link counts

### Step 1.2 — Check Broken Links

```bash
python3 ~/.openclaw/workspace/seo/tools/site_crawler.py \
  --url "$AUDIT_TARGET_URL" \
  --check broken-links \
  --include-external true \
  --output /tmp/broken_links_$(date +%Y%m).json
```

### Step 1.3 — Measure Core Web Vitals

Sample the top 20 pages by traffic (from DB):
```bash
python3 ~/.openclaw/workspace/seo/tools/db.py get_top_pages \
  --limit 20 \
  --output /tmp/top_pages.txt
```

Run CWV checks on sampled pages:
```bash
python3 ~/.openclaw/workspace/seo/playwright/cwv_checker.py \
  --urls-file /tmp/top_pages.txt \
  --device both \
  --output /tmp/cwv_$(date +%Y%m).json
```

## Phase 2 — Aggregate and Score Issues

```bash
python3 ~/.openclaw/workspace/seo/tools/site_crawler.py \
  --mode aggregate \
  --crawl /tmp/crawl_$(date +%Y%m).json \
  --broken-links /tmp/broken_links_$(date +%Y%m).json \
  --cwv /tmp/cwv_$(date +%Y%m).json \
  --output /tmp/all_issues_$(date +%Y%m).json
```

Save audit results to DB:
```bash
python3 ~/.openclaw/workspace/seo/tools/db.py save_audit \
  --crawl /tmp/crawl_$(date +%Y%m).json \
  --issues /tmp/all_issues_$(date +%Y%m).json \
  --audit-type monthly \
  --date $(date +%Y-%m-%d)
```

## Phase 3 — Auto-Fix Eligible Issues

### 3.1 — Get fixable issues

```bash
python3 ~/.openclaw/workspace/seo/tools/db.py get_fixable_issues \
  --severity critical,high,medium \
  --types missing_meta_title,missing_meta_description,missing_alt_text \
  --limit 50 \
  --output /tmp/fixable_$(date +%Y%m).json
```

### 3.2 — Generate fixes

For each fixable issue, generate the correct fix content:

**Missing meta descriptions**: Read the page content via Playwright, summarize into a 150-160 char description.

**Missing alt text on images**: Fetch each image URL, use Claude vision to generate descriptive alt text.

**Meta titles that are too long (>60 chars)**: Truncate intelligently at the last word boundary before 60 chars.

Save proposed fixes:
```bash
python3 ~/.openclaw/workspace/seo/tools/db.py save_fixes \
  --file /tmp/fixable_$(date +%Y%m).json \
  --status proposed
```

### 3.3 — Apply auto-fixes

Spawn `seo-executor` with:
"Apply all proposed fixes from the audit run for $(date +%Y-%m). File: /tmp/fixable_$(date +%Y%m).json"

## Phase 4 — Compare with Previous Month

```bash
python3 ~/.openclaw/workspace/seo/tools/db.py compare_audits \
  --current $(date +%Y-%m) \
  --previous $(date -d 'last month' +%Y-%m) \
  --output /tmp/audit_delta_$(date +%Y%m).json
```

Shows:
- Issues resolved since last month
- New issues introduced
- Overall health score change (0–100)

## Phase 5 — Generate Monthly Audit Report

Spawn `seo-reporter` with:
"Generate the monthly technical SEO audit report for $(date +%Y-%m). Include full issue breakdown, auto-fixes applied, comparison with last month, and top 10 manual action items. Output to /tmp/monthly_audit_$(date +%Y%m).html"

## Phase 6 — Archive Results

```bash
python3 ~/.openclaw/workspace/seo/tools/db.py save_report \
  --file /tmp/monthly_audit_$(date +%Y%m).html \
  --period monthly \
  --date $(date +%Y-%m-%d)
```

## Completion Summary

```
🔬 Monthly Audit Complete — [date]
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
Pages crawled:   [N]
🔴 Critical:     [N]
🟠 High:         [N]
🟡 Medium:       [N]
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
Auto-fixed:      [N] issues
Needs review:    [N] issues
Health score:    [X]/100 (was [Y] last month)
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
Report: /tmp/monthly_audit_[date].html
Next audit: [1st of next month]
```
