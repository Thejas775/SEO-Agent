---
name: dataforseo
description: "Access DataForSEO APIs for keyword research, SERP data, backlink data, and competitor analysis"
metadata:
  {
    "openclaw": {
      "emoji": "📡",
      "primaryEnv": "DATAFORSEO_LOGIN",
      "requires": {
        "bins": ["python3"],
        "env": ["DATAFORSEO_LOGIN", "DATAFORSEO_PASSWORD"]
      },
      "install": [
        {
          "id": "uv",
          "kind": "uv",
          "module": "requests",
          "label": "Install requests for DataForSEO API"
        }
      ]
    }
  }
---

# DataForSEO Skill

Provides access to DataForSEO's REST APIs for keyword data, SERP results, backlink data, and competitor intelligence.

## Authentication

Set `DATAFORSEO_LOGIN` and `DATAFORSEO_PASSWORD` environment variables. Uses HTTP Basic Auth.

## Available API Modes

```bash
# SERP results for a keyword
python3 ~/.openclaw/workspace/seo/tools/dataforseo_tool.py \
  --mode serp \
  --keyword "target keyword" \
  --location_code 2840 \
  --language_code en \
  --top 10 \
  --output /tmp/serp.json

# Keyword search volume and CPC
python3 ~/.openclaw/workspace/seo/tools/dataforseo_tool.py \
  --mode keyword_data \
  --keywords "keyword1,keyword2,keyword3" \
  --output /tmp/kw_data.json

# Keyword suggestions (expand a seed)
python3 ~/.openclaw/workspace/seo/tools/dataforseo_tool.py \
  --mode keyword_suggestions \
  --seed "seed keyword" \
  --limit 100 \
  --output /tmp/suggestions.json

# Keyword gap between domains
python3 ~/.openclaw/workspace/seo/tools/dataforseo_tool.py \
  --mode keyword_gap \
  --our-domain "yourdomain.com" \
  --competitors "comp1.com,comp2.com" \
  --output /tmp/gap.json

# Competitor organic keywords
python3 ~/.openclaw/workspace/seo/tools/dataforseo_tool.py \
  --mode competitor_keywords \
  --domain "competitor.com" \
  --top 200 \
  --output /tmp/comp_kw.json

# Backlink data
python3 ~/.openclaw/workspace/seo/tools/dataforseo_tool.py \
  --mode backlinks \
  --domain "target.com" \
  --output /tmp/backlinks.json
```

## Location Codes

- US: 2840
- UK: 2826
- Canada: 2124
- Australia: 2036
- Global: use location_code 2840 with language_code en

## Cost Management

DataForSEO charges per task. Minimize cost by:
- Caching results in PostgreSQL (results valid for 7 days for volume data)
- Batching keyword requests (up to 1000 per call)
- Using `Sandbox` mode for testing (set `--sandbox true`)

```bash
python3 ~/.openclaw/workspace/seo/tools/db.py get_cached_keyword_data \
  --keyword "target keyword" \
  --max-age-days 7
```
