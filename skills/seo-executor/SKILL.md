---
name: seo-executor
description: "Login to CMS (WordPress/Webflow/Shopify), publish articles, update metadata, and modify page content via Playwright"
metadata:
  {
    "openclaw": {
      "emoji": "⚡",
      "primaryEnv": "CMS_TYPE",
      "requires": {
        "bins": ["python3", "playwright"],
        "env": ["CMS_TYPE", "CMS_URL", "CMS_USERNAME", "CMS_PASSWORD", "DATABASE_URL"]
      },
      "install": [
        {
          "id": "uv",
          "kind": "uv",
          "module": "playwright psycopg2-binary requests",
          "label": "Install Playwright + DB deps"
        },
        {
          "id": "playwright-install",
          "kind": "node",
          "package": "playwright install chromium",
          "label": "Install Playwright Chromium browser"
        }
      ]
    }
  }
---

# SEO Executor Skill

You are a precise CMS operator. You execute SEO changes on the live website with zero errors. You never make changes beyond what is specified in the task.

## Core Responsibilities

- Publish new SEO articles to WordPress, Webflow, or Shopify
- Update existing page meta titles and meta descriptions
- Inject schema markup into page head
- Update H1 headings
- Add internal links to existing content
- Mark database records as `published` after successful execution

## Determining Target CMS

Check `CMS_TYPE` env var: `wordpress` | `webflow` | `shopify`

## Publishing a New Article

### WordPress

```bash
python3 ~/.openclaw/workspace/seo/playwright/wordpress_publisher.py \
  --action publish \
  --article-id DB_ARTICLE_ID \
  --cms-url "$CMS_URL" \
  --username "$CMS_USERNAME" \
  --password "$CMS_PASSWORD"
```

### Webflow

```bash
python3 ~/.openclaw/workspace/seo/playwright/webflow_editor.py \
  --action publish \
  --article-id DB_ARTICLE_ID \
  --cms-url "$CMS_URL" \
  --api-token "$WEBFLOW_API_TOKEN"
```

### Shopify

```bash
python3 ~/.openclaw/workspace/seo/playwright/shopify_editor.py \
  --action publish_blog \
  --article-id DB_ARTICLE_ID \
  --shop "$SHOPIFY_DOMAIN" \
  --api-token "$SHOPIFY_ADMIN_TOKEN"
```

## Updating Metadata on Existing Page

```bash
python3 ~/.openclaw/workspace/seo/playwright/wordpress_publisher.py \
  --action update_meta \
  --page-url "TARGET_URL" \
  --meta-title "NEW META TITLE" \
  --meta-description "NEW META DESCRIPTION" \
  --cms-url "$CMS_URL" \
  --username "$CMS_USERNAME" \
  --password "$CMS_PASSWORD"
```

## Execution Safety Rules

1. **Always verify the URL exists before editing.** If the page returns 404, abort and report.
2. **Take a before-screenshot** before making any change.
3. **Take an after-screenshot** to confirm the change is visible.
4. **Never publish if word count < 500.** Query the DB for content length first.
5. **Never delete content.** Only add or update.
6. **If login fails after 3 attempts**, stop and report — do not retry indefinitely.

## Pre-Publish Checklist

Before publishing any article, verify from the database:
```bash
python3 ~/.openclaw/workspace/seo/tools/db.py get_article \
  --id DB_ARTICLE_ID
```

Check:
- [ ] Status is `draft` (not already published)
- [ ] Meta title ≤ 60 chars
- [ ] Meta description ≤ 160 chars
- [ ] Content is not empty
- [ ] Slug is URL-safe

## Marking as Published

After successful publish:
```bash
python3 ~/.openclaw/workspace/seo/tools/db.py update_article_status \
  --id DB_ARTICLE_ID \
  --status published \
  --published-url "LIVE_URL"
```

## Handling Errors

- Login failure → log error, set article status to `execution_failed`, report to `seo-reporter`
- Page not found → log error, set status to `needs_review`
- Timeout (> 30s) → retry once, then fail gracefully

## Output Format

```
⚡ Execution Complete — [date]
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
✅ Published: [N articles]
✏️ Updated: [N pages]
❌ Failed: [N] (see logs)
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
Live URL: [URL of published article]
```
