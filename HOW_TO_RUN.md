# How to Run — SEO AI Employee

Complete guide from zero to running autonomous SEO agents.

---

## Prerequisites (install these manually first)

### Node.js 22+
```bash
# macOS
brew install node@22
echo 'export PATH="/opt/homebrew/opt/node@22/bin:$PATH"' >> ~/.zshrc
source ~/.zshrc

# Linux VPS (Ubuntu/Debian)
curl -fsSL https://deb.nodesource.com/setup_22.x | sudo bash -
sudo apt install -y nodejs
```

### Python 3.11+
```bash
# macOS
brew install python@3.11

# Linux
sudo apt install -y python3.11 python3.11-pip python3-venv
```

### PostgreSQL
```bash
# macOS
brew install postgresql@15
brew services start postgresql@15

# Linux
sudo apt install -y postgresql postgresql-contrib
sudo systemctl start postgresql
sudo systemctl enable postgresql
```

Verify everything:
```bash
node --version    # should be v22+
python3 --version # should be 3.11+
psql --version    # should be 15+
```

---

## Step 1 — Clone / Navigate to Project

```bash
cd ~/Desktop/Personal\ Projects/SEO
```

---

## Step 2 — Fill in API Keys

```bash
cp config/.env.example ~/.openclaw/.env
nano ~/.openclaw/.env
```

Fill in every value. See `CREDENTIALS_GUIDE.md` for how to get each one.

Minimum required to get started:
```env
ANTHROPIC_API_KEY=sk-ant-...
DATABASE_URL=postgresql://user:pass@localhost:5432/seo_db
CMS_TYPE=wordpress
CMS_URL=https://yoursite.com
CMS_USERNAME=admin
CMS_PASSWORD=your_app_password
AUDIT_TARGET_URL=https://yoursite.com
```

Optional (adds GSC data and keyword research):
```env
GSC_SERVICE_ACCOUNT_JSON=/path/to/gsc-service-account.json
GSC_SITE_URL=https://yoursite.com/
DATAFORSEO_LOGIN=your@email.com
DATAFORSEO_PASSWORD=your_password
COMPETITOR_1=competitor1.com
COMPETITOR_2=competitor2.com
```

---

## Step 3 — Run Setup Script

```bash
bash scripts/setup.sh
```

This installs:
- OpenClaw (the agent runtime)
- All Python dependencies (uv)
- Playwright + Chromium browser
- Copies skills, workflows into OpenClaw workspace
- Copies `openclaw.json5` to `~/.openclaw/`

---

## Step 4 — Create the Database

```bash
# Create DB and user (if not using Supabase/Railway)
psql postgres -c "CREATE USER seo_user WITH PASSWORD 'your_password';"
psql postgres -c "CREATE DATABASE seo_db OWNER seo_user;"

# Apply schema
psql $DATABASE_URL -f db/schema.sql
```

Verify:
```bash
psql $DATABASE_URL -c "\dt"
# Should list: articles, audit_issues, audit_runs, content_calendar, etc.
```

---

## Step 5 — Start OpenClaw Daemon

```bash
openclaw onboard --install-daemon
```

This starts OpenClaw as a background service that runs permanently.
The 6 SEO agents are now live and ready.

Verify it's running:
```bash
openclaw doctor
```

---

## Step 6 — Register Scheduled Pipelines

```bash
bash scripts/register_crons.sh
```

This registers:
- **Daily 07:00** — pull GSC data, detect quick wins, update metadata
- **Monday 08:00** — competitor research, keyword clustering, write + publish articles
- **1st of month 06:00** — full technical SEO audit, auto-fix issues

Verify:
```bash
openclaw cron list
```

---

## Step 7 — Start the UI

```bash
cd ~/Desktop/Personal\ Projects/SEO
pip install -r ui/requirements.txt
uvicorn ui.app:app --host 0.0.0.0 --port 8000
```

Open in browser: **http://localhost:8000**

---

## Running an Instant SEO Analysis

### Via UI (recommended)
1. Open http://localhost:8000
2. Paste any website URL
3. Click **Run SEO Analysis**
4. Watch live agent updates
5. View full report when done

### Via Terminal
```bash
bash scripts/run.sh https://yoursite.com
```

---

## Starting Everything After a Reboot

OpenClaw daemon starts automatically (installed as a system service).
You only need to restart the UI:

```bash
cd ~/Desktop/Personal\ Projects/SEO
uvicorn ui.app:app --host 0.0.0.0 --port 8000
```

Or run both with one command:
```bash
bash scripts/start.sh
```

---

## Checking Logs

```bash
# OpenClaw agent logs
tail -f ~/.openclaw/logs/seo-agent.log

# UI logs
# shown directly in terminal where uvicorn is running
```

---

## Folder Reference

```
SEO/
├── openclaw.json5          ← agent config (6 agents)
├── skills/                 ← agent instructions (SKILL.md files)
├── workflows/              ← pipelines agents follow
├── tools/                  ← Python tools (GSC, DataForSEO, DB, etc.)
├── playwright/             ← CMS automation scripts
├── db/schema.sql           ← PostgreSQL schema
├── ui/                     ← Web UI (FastAPI + frontend)
├── config/.env.example     ← API key template
├── scripts/setup.sh        ← one-command installer
├── scripts/register_crons.sh ← registers scheduled runs
├── scripts/run.sh          ← instant run from terminal
├── CREDENTIALS_GUIDE.md    ← how to get every API key
└── HOW_TO_RUN.md           ← this file
```

---

## Troubleshooting

**OpenClaw not found after install**
```bash
export PATH="$HOME/.npm-global/bin:$PATH"
# or
export PATH="$(npm root -g)/.bin:$PATH"
```

**Database connection refused**
```bash
# macOS — start PostgreSQL
brew services start postgresql@15

# Linux
sudo systemctl start postgresql
```

**Playwright browser missing**
```bash
python3 -m playwright install chromium
```

**GSC returns no data**
- Make sure the service account email is added to your GSC property as Full user
- Data has a 3-day lag in GSC — use `--days 7` minimum

**Agent not responding**
```bash
openclaw doctor
openclaw restart
```
