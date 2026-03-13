---
name: google-search-console
description: "Authenticate with Google Search Console API and fetch search performance data (clicks, impressions, CTR, position)"
metadata:
  {
    "openclaw": {
      "emoji": "🔎",
      "primaryEnv": "GSC_SERVICE_ACCOUNT_JSON",
      "requires": {
        "bins": ["python3"],
        "env": ["GSC_SERVICE_ACCOUNT_JSON", "GSC_SITE_URL"]
      },
      "install": [
        {
          "id": "uv",
          "kind": "uv",
          "module": "google-auth google-auth-httplib2 google-api-python-client",
          "label": "Install Google API Python client"
        }
      ]
    }
  }
---

# Google Search Console Skill

Provides authenticated access to the Google Search Console Search Analytics API.

## Authentication

Uses a service account JSON key. Set `GSC_SERVICE_ACCOUNT_JSON` to the path of your service account JSON file, or the JSON string itself.

The service account must be added as a **Full user** in GSC for the target property.

## Fetching Performance Data

```bash
python3 ~/.openclaw/workspace/seo/tools/gsc_tool.py \
  --mode fetch \
  --site "$GSC_SITE_URL" \
  --start-date 2024-01-01 \
  --end-date 2024-01-28 \
  --dimensions page,query \
  --output /tmp/gsc_data.json
```

Available dimensions: `query`, `page`, `country`, `device`, `searchAppearance`

## Available Modes

- `fetch` — raw data export
- `analyze` — run full analysis (drops, CTR opportunities, quick wins)
- `pages` — page-level performance only
- `queries` — query-level performance only
- `compare` — compare two date ranges

## Understanding the Data

- **Clicks** — actual visits from Google search
- **Impressions** — how many times your page appeared in results
- **CTR** — clicks ÷ impressions (target > 3% for position 1–3)
- **Position** — average ranking position (lower = better)

## Key Thresholds

| Metric | Target | Action if below |
|---|---|---|
| CTR at position 1–3 | > 5% | Rewrite meta title/description |
| CTR at position 4–10 | > 2% | A/B test title variants |
| Position trending up | - | Investigate cause, reinforce |
| Position drop > 5 | < 20 | Content refresh or backlink audit |
