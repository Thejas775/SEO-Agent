---
name: playwright-seo
description: "Browser automation for CMS login, content publishing, metadata updates, and Core Web Vitals measurement using Playwright"
metadata:
  {
    "openclaw": {
      "emoji": "🎭",
      "requires": {
        "bins": ["python3", "playwright"],
        "env": ["CMS_TYPE", "CMS_URL"]
      },
      "install": [
        {
          "id": "uv",
          "kind": "uv",
          "module": "playwright psycopg2-binary",
          "label": "Install Playwright Python deps"
        },
        {
          "id": "playwright-chromium",
          "kind": "node",
          "package": "playwright install chromium",
          "label": "Download Chromium browser for Playwright"
        }
      ]
    }
  }
---

# Playwright SEO Automation Skill

Provides browser automation capabilities for CMS operations and performance measurement.

## Supported CMS Platforms

- WordPress (admin dashboard + REST API fallback)
- Webflow (CMS API)
- Shopify (admin + Storefront API)

## Script Locations

All Playwright scripts are at:
```
~/.openclaw/workspace/seo/playwright/
├── wordpress_publisher.py   # WordPress publish + meta update
├── webflow_editor.py        # Webflow CMS operations
├── shopify_editor.py        # Shopify blog + product meta
└── cwv_checker.py           # Core Web Vitals measurement
```

## WordPress Operations

```bash
# Publish new post
python3 ~/.openclaw/workspace/seo/playwright/wordpress_publisher.py \
  --action publish \
  --article-id 42

# Update meta title + description on existing page
python3 ~/.openclaw/workspace/seo/playwright/wordpress_publisher.py \
  --action update_meta \
  --post-id 99 \
  --meta-title "New Title" \
  --meta-description "New description"

# Add internal link to existing post
python3 ~/.openclaw/workspace/seo/playwright/wordpress_publisher.py \
  --action add_link \
  --post-id 99 \
  --anchor-text "anchor text" \
  --link-url "https://site.com/target-page"
```

## Core Web Vitals Check

```bash
python3 ~/.openclaw/workspace/seo/playwright/cwv_checker.py \
  --url "https://yoursite.com/page" \
  --device mobile \
  --output /tmp/cwv.json
```

Returns:
- LCP (Largest Contentful Paint)
- CLS (Cumulative Layout Shift)
- FID/INP
- TTFB (Time to First Byte)
- Page load time

## Screenshot Evidence

All CMS actions automatically save before/after screenshots to:
`~/.openclaw/workspace/seo/screenshots/[date]/[action]_[page]_[before|after].png`

## Error Handling Rules

- On login failure: do NOT retry more than 3 times
- On element not found: take a screenshot, log the error, abort
- On successful publish: always verify the live URL responds 200
- Headless mode by default; set `--headed` for debugging
