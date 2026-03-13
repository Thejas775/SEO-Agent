# Credentials Setup Guide

Step-by-step instructions to get every API key and credential needed.

---

## 1. Anthropic API Key

**Used for:** All AI writing, analysis, and agent reasoning.

1. Go to [console.anthropic.com](https://console.anthropic.com)
2. Sign up or log in
3. Click **API Keys** in the left sidebar
4. Click **Create Key**
5. Name it `seo-ai-employee`
6. Copy the key (starts with `sk-ant-...`)

```env
ANTHROPIC_API_KEY=sk-ant-...
```

---

## 2. Google Search Console API

**Used for:** Pulling clicks, impressions, rankings, CTR data.

### Step 1 — Enable the API
1. Go to [console.cloud.google.com](https://console.cloud.google.com)
2. Create a new project (or use existing) — name it `seo-ai-employee`
3. Go to **APIs & Services → Library**
4. Search for **"Google Search Console API"**
5. Click **Enable**

### Step 2 — Create a Service Account
1. Go to **APIs & Services → Credentials**
2. Click **Create Credentials → Service Account**
3. Name: `seo-agent`, click **Create and Continue**
4. Role: skip (click Continue), click **Done**
5. Click the service account you just created
6. Go to **Keys** tab → **Add Key → Create new key → JSON**
7. A `.json` file downloads — save it as `gsc-service-account.json`

### Step 3 — Add Service Account to GSC
1. Go to [search.google.com/search-console](https://search.google.com/search-console)
2. Select your property
3. Go to **Settings → Users and permissions**
4. Click **Add user**
5. Enter the service account email (looks like `seo-agent@your-project.iam.gserviceaccount.com`)
6. Set permission to **Full**
7. Click **Add**

```env
GSC_SERVICE_ACCOUNT_JSON=/path/to/gsc-service-account.json
GSC_SITE_URL=https://yoursite.com/
```

> **Note:** Use the exact URL format as shown in GSC (with or without trailing slash, http vs https must match).

---

## 3. DataForSEO

**Used for:** Keyword research, SERP data, competitor keywords, keyword gaps.

1. Go to [dataforseo.com](https://dataforseo.com)
2. Sign up for an account
3. You get **$1 free credit** on signup to test
4. Go to **Dashboard → API Access**
5. Your login is your **email address**
6. Your password is your **DataForSEO account password**

```env
DATAFORSEO_LOGIN=your@email.com
DATAFORSEO_PASSWORD=your_password
```

> **Pricing:** Pay-as-you-go. Keyword data costs ~$0.002 per keyword. A full weekly run costs roughly $0.50–$2.

---

## 4. PostgreSQL Database

**Used for:** Storing all SEO data — rankings, articles, audit issues, reports.

### Option A — Local (development)
```bash
# macOS
brew install postgresql@15
brew services start postgresql@15
createdb seo_db
createuser seo_user --pwprompt
psql seo_db -c "GRANT ALL ON DATABASE seo_db TO seo_user;"
```

### Option B — Supabase (free hosted, recommended)
1. Go to [supabase.com](https://supabase.com)
2. Click **New Project**
3. Name: `seo-ai-employee`, set a strong password
4. Wait for project to provision (~2 min)
5. Go to **Settings → Database**
6. Copy the **Connection string (URI)** under **Connection pooling**

### Option C — Railway (free tier)
1. Go to [railway.app](https://railway.app)
2. New Project → **PostgreSQL**
3. Go to **Variables** tab
4. Copy the `DATABASE_URL`

```env
DATABASE_URL=postgresql://seo_user:password@host:5432/seo_db
```

After setting `DATABASE_URL`, run the schema:
```bash
psql $DATABASE_URL -f db/schema.sql
```

---

## 5. WordPress Credentials

**Used for:** Publishing articles, updating meta titles/descriptions.

You need:
- The WordPress site URL
- An admin username
- The password (or better: an **Application Password**)

### Creating an Application Password (recommended)
1. Log into WordPress admin
2. Go to **Users → Profile**
3. Scroll to **Application Passwords**
4. Name: `seo-agent`
5. Click **Add New Application Password**
6. Copy the generated password

```env
CMS_TYPE=wordpress
CMS_URL=https://yoursite.com
CMS_USERNAME=admin
CMS_PASSWORD=xxxx xxxx xxxx xxxx xxxx xxxx
```

> **Plugin required for meta tags:** Install **Yoast SEO** or **RankMath** — the executor writes meta tags via their custom fields.

---

## 6. Webflow Credentials (if using Webflow)

**Used for:** Publishing CMS items, updating SEO fields.

1. Log into [webflow.com](https://webflow.com)
2. Go to your site → **Site Settings → Integrations**
3. Scroll to **API Access**
4. Click **Generate API Token**
5. Copy the token
6. Go to **Site Settings → General** and copy the **Site ID**

```env
CMS_TYPE=webflow
WEBFLOW_API_TOKEN=your_token
WEBFLOW_SITE_ID=your_site_id
```

---

## 7. Shopify Credentials (if using Shopify)

**Used for:** Publishing blog articles, updating page SEO metadata.

1. Go to your Shopify admin → **Apps → Develop apps**
2. Click **Create an app** → name it `seo-agent`
3. Click **Configure Admin API scopes**
4. Enable:
   - `write_content` (blog articles)
   - `read_content`
   - `write_online_store_pages`
   - `read_online_store_pages`
5. Click **Install app**
6. Copy the **Admin API access token**
7. Your shop domain is `yourstore.myshopify.com`

```env
CMS_TYPE=shopify
SHOPIFY_DOMAIN=yourstore.myshopify.com
SHOPIFY_ADMIN_TOKEN=shpat_...
SHOPIFY_BLOG_ID=12345678
```

> **To find your Blog ID:** Go to Shopify admin → Online Store → Blog Posts → click a blog → the number in the URL is the Blog ID.

---

## 8. Competitors

Just the domain names of 1–2 competitors (no https://):

```env
COMPETITOR_1=competitor1.com
COMPETITOR_2=competitor2.com
```

---

## Final .env File

Once all credentials are gathered, your `~/.openclaw/.env` should look like:

```env
# LLM
ANTHROPIC_API_KEY=sk-ant-...

# Database
DATABASE_URL=postgresql://seo_user:password@host:5432/seo_db

# Google Search Console
GSC_SERVICE_ACCOUNT_JSON=/path/to/gsc-service-account.json
GSC_SITE_URL=https://yoursite.com/

# DataForSEO
DATAFORSEO_LOGIN=your@email.com
DATAFORSEO_PASSWORD=your_password

# CMS (pick one)
CMS_TYPE=wordpress
CMS_URL=https://yoursite.com
CMS_USERNAME=admin
CMS_PASSWORD=your_app_password

# Target site + competitors
AUDIT_TARGET_URL=https://yoursite.com
COMPETITOR_1=competitor1.com
COMPETITOR_2=competitor2.com
```

---

## Quick Checklist

- [ ] Anthropic API key created
- [ ] GSC API enabled + service account created + added to GSC property
- [ ] DataForSEO account created
- [ ] PostgreSQL database running + schema applied
- [ ] CMS credentials configured (WordPress / Webflow / Shopify)
- [ ] Competitors added
- [ ] `.env` file saved to `~/.openclaw/.env`
- [ ] `bash scripts/setup.sh` run successfully
- [ ] `bash scripts/register_crons.sh` run successfully
