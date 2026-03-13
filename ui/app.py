#!/usr/bin/env python3
"""
SEO AI Employee — Web UI Backend
FastAPI + WebSockets. Orchestrates all SEO agents and streams live updates.
Run: uvicorn ui.app:app --reload --port 8000
"""

import asyncio
import json
import os
import subprocess
import sys
import uuid
from datetime import datetime
from pathlib import Path
from typing import AsyncGenerator

import anthropic
from fastapi import FastAPI, WebSocket, WebSocketDisconnect
from fastapi.responses import HTMLResponse, JSONResponse, FileResponse
from fastapi.staticfiles import StaticFiles

# ── paths ─────────────────────────────────────────────────────────────────────
ROOT = Path(__file__).parent.parent
TOOLS = ROOT / "tools"
PLAYWRIGHT = ROOT / "playwright"
REPORTS_DIR = Path(os.path.expanduser("~/.openclaw/workspace/seo/reports"))
REPORTS_DIR.mkdir(parents=True, exist_ok=True)

# ── load .env ─────────────────────────────────────────────────────────────────
env_file = Path.home() / ".openclaw" / ".env"
if env_file.exists():
    for line in env_file.read_text().splitlines():
        line = line.strip()
        if line and not line.startswith("#") and "=" in line:
            k, v = line.split("=", 1)
            os.environ.setdefault(k.strip(), v.strip())

app = FastAPI(title="SEO AI Employee")
app.mount("/static", StaticFiles(directory=ROOT / "ui" / "static"), name="static")

# ── in-memory run store ────────────────────────────────────────────────────────
runs: dict[str, dict] = {}  # run_id → {status, phases, report_path, site_url, started_at}
connections: dict[str, list[WebSocket]] = {}  # run_id → [websockets]


# ── helpers ───────────────────────────────────────────────────────────────────

async def broadcast(run_id: str, event: dict):
    """Send a JSON event to all WebSocket clients watching this run."""
    msg = json.dumps(event)
    dead = []
    for ws in connections.get(run_id, []):
        try:
            await ws.send_text(msg)
        except Exception:
            dead.append(ws)
    for ws in dead:
        connections[run_id].remove(ws)


def run_tool(args: list[str], env_extra: dict | None = None) -> tuple[int, str, str]:
    """Run a Python tool synchronously, return (returncode, stdout, stderr)."""
    env = {**os.environ, **(env_extra or {})}
    result = subprocess.run(
        [sys.executable] + args,
        capture_output=True, text=True, env=env, timeout=300
    )
    return result.returncode, result.stdout, result.stderr


async def run_tool_async(args: list[str], env_extra: dict | None = None) -> tuple[int, str, str]:
    loop = asyncio.get_event_loop()
    return await loop.run_in_executor(None, run_tool, args, env_extra)


async def emit(run_id: str, phase: str, status: str, message: str, data: dict | None = None):
    """Emit a structured progress event."""
    event = {
        "type": "progress",
        "phase": phase,
        "status": status,   # running | done | error | info
        "message": message,
        "data": data or {},
        "ts": datetime.now().isoformat(),
    }
    if run_id in runs:
        runs[run_id]["events"].append(event)
    await broadcast(run_id, event)


# ── MAIN PIPELINE ─────────────────────────────────────────────────────────────

async def run_seo_pipeline(run_id: str, site_url: str):
    run = runs[run_id]
    run["status"] = "running"
    tmp = Path(f"/tmp/seo_run_{run_id}")
    tmp.mkdir(exist_ok=True)
    client = anthropic.Anthropic(api_key=os.environ.get("ANTHROPIC_API_KEY", ""))

    try:
        # ── PHASE 1: Site Discovery ─────────────────────────────────────────
        await emit(run_id, "discovery", "running", f"Checking site health for {site_url}...")

        rc, out, err = await run_tool_async([
            str(PLAYWRIGHT / "cwv_checker.py"),
            "--url", site_url,
            "--device", "desktop",
            "--output", str(tmp / "cwv.json"),
        ])
        if rc == 0:
            cwv = json.loads((tmp / "cwv.json").read_text())
            r = cwv["results"][0] if cwv.get("results") else {}
            await emit(run_id, "discovery", "done", "Site health check complete", {
                "lcp_ms": r.get("lcp_ms"),
                "cls": r.get("cls"),
                "ttfb_ms": r.get("ttfb_ms"),
                "passes_cwv": r.get("passes_cwv"),
            })
        else:
            await emit(run_id, "discovery", "info", "CWV check skipped (Playwright not available)")

        # ── PHASE 2A: Technical Audit ───────────────────────────────────────
        await emit(run_id, "audit", "running", "Crawling website for technical issues...")

        rc, out, err = await run_tool_async([
            str(TOOLS / "site_crawler.py"),
            "--url", site_url,
            "--max-pages", "150",
            "--output", str(tmp / "crawl.json"),
        ])

        audit_summary = {}
        if rc == 0 and (tmp / "crawl.json").exists():
            crawl = json.loads((tmp / "crawl.json").read_text())
            audit_summary = crawl.get("summary", {})
            await emit(run_id, "audit", "done", f"Audit complete — {crawl.get('pages_crawled', 0)} pages crawled", audit_summary)
        else:
            await emit(run_id, "audit", "error", "Audit failed — check site URL", {"stderr": err[:300]})

        # ── PHASE 2B: GSC Analysis ──────────────────────────────────────────
        await emit(run_id, "gsc", "running", "Pulling Google Search Console data...")

        gsc_available = bool(os.environ.get("GSC_SERVICE_ACCOUNT_JSON"))
        gsc_summary = {}

        if gsc_available:
            rc, out, err = await run_tool_async([
                str(TOOLS / "gsc_tool.py"),
                "--mode", "analyze",
                "--site", site_url,
                "--days", "28",
                "--output", str(tmp / "gsc.json"),
            ])
            if rc == 0:
                gsc = json.loads((tmp / "gsc.json").read_text())
                gsc_summary = {
                    "ranking_drops": len(gsc.get("ranking_drops", [])),
                    "ctr_opportunities": len(gsc.get("ctr_opportunities", [])),
                    "quick_wins": len(gsc.get("quick_wins", [])),
                    "total_clicks": gsc.get("total_clicks", 0),
                    "total_impressions": gsc.get("total_impressions", 0),
                }
                await emit(run_id, "gsc", "done", "GSC analysis complete", gsc_summary)
            else:
                await emit(run_id, "gsc", "error", "GSC fetch failed", {"error": err[:300]})
        else:
            await emit(run_id, "gsc", "info", "GSC not configured — skipping (add GSC_SERVICE_ACCOUNT_JSON to .env)")

        # ── PHASE 2C: Keyword Research ──────────────────────────────────────
        await emit(run_id, "keywords", "running", "Researching keywords and competitors...")

        dfs_available = bool(os.environ.get("DATAFORSEO_LOGIN"))
        keyword_summary = {}

        if dfs_available:
            from urllib.parse import urlparse
            domain = urlparse(site_url).netloc

            # Keyword suggestions from domain
            rc, out, err = await run_tool_async([
                str(TOOLS / "dataforseo_tool.py"),
                "--mode", "keyword_suggestions",
                "--seed", domain.replace("www.", "").split(".")[0],
                "--limit", "50",
                "--output", str(tmp / "kw_suggestions.json"),
            ])

            if rc == 0:
                # Cluster them
                rc2, out2, err2 = await run_tool_async([
                    str(TOOLS / "keyword_clusterer.py"),
                    "--input", str(tmp / "kw_suggestions.json"),
                    "--output", str(tmp / "clusters.json"),
                ])
                if rc2 == 0:
                    clusters = json.loads((tmp / "clusters.json").read_text())
                    # Generate calendar
                    await run_tool_async([
                        str(TOOLS / "content_calendar.py"),
                        "--clusters", str(tmp / "clusters.json"),
                        "--weeks", "4",
                        "--per-week", "2",
                        "--output", str(tmp / "calendar.json"),
                    ])
                    keyword_summary = {
                        "total_keywords": clusters.get("total_keywords", 0),
                        "clusters": clusters.get("total_clusters", 0),
                        "top_keyword": clusters["clusters"][0]["primary_keyword"] if clusters.get("clusters") else "",
                        "top_volume": clusters["clusters"][0].get("primary_volume", 0) if clusters.get("clusters") else 0,
                    }
                    await emit(run_id, "keywords", "done", f"Found {clusters.get('total_clusters', 0)} keyword clusters", keyword_summary)
        else:
            await emit(run_id, "keywords", "info", "DataForSEO not configured — skipping (add DATAFORSEO_LOGIN to .env)")

        # ── PHASE 3: AI Content Strategy & Writing ──────────────────────────
        await emit(run_id, "writing", "running", "Generating SEO content strategy with Claude...")

        # Build context for Claude
        audit_text = ""
        if (tmp / "crawl.json").exists():
            s = audit_summary
            audit_text = f"""
Technical Audit Results:
- Pages crawled: {s.get('pages_crawled', 'N/A')}
- Broken links: {s.get('broken_links', 0)}
- Missing meta titles: {s.get('missing_meta_title', 0)}
- Missing meta descriptions: {s.get('missing_meta_description', 0)}
- Images missing alt text: {s.get('missing_alt_text', 0)}
"""

        gsc_text = ""
        if gsc_summary:
            gsc_text = f"""
GSC Performance (last 28 days):
- Total clicks: {gsc_summary.get('total_clicks', 0)}
- Impressions: {gsc_summary.get('total_impressions', 0)}
- Ranking drops: {gsc_summary.get('ranking_drops', 0)}
- CTR opportunities: {gsc_summary.get('ctr_opportunities', 0)}
- Quick wins (pos 11-20): {gsc_summary.get('quick_wins', 0)}
"""

        kw_text = ""
        if keyword_summary:
            kw_text = f"""
Keyword Research:
- Keywords analyzed: {keyword_summary.get('total_keywords', 0)}
- Clusters found: {keyword_summary.get('clusters', 0)}
- Top opportunity: "{keyword_summary.get('top_keyword', '')}" ({keyword_summary.get('top_volume', 0)}/mo)
"""

        prompt = f"""You are a senior SEO strategist. Analyze this website and provide a complete SEO action plan.

Website: {site_url}

{audit_text}
{gsc_text}
{kw_text}

Provide:

## 1. Executive Summary
2-3 sentence overview of the site's SEO health.

## 2. Critical Issues (fix this week)
List the top 5 most urgent SEO issues with specific fix instructions.

## 3. Quick Win Opportunities
List 5 specific pages/keywords where small changes will have fast impact. Include exact suggested meta titles and descriptions.

## 4. Content Strategy
Recommend 4 specific article topics with:
- Target keyword
- Estimated monthly search volume (your best estimate)
- Content angle that would outrank competitors
- Suggested H1, meta title, meta description

## 5. Technical Fixes Roadmap
Prioritized list of technical fixes (30-day plan).

## 6. 90-Day SEO Forecast
What results should be expected if these recommendations are followed.

Be specific, actionable, and data-driven. Reference actual numbers from the audit data above."""

        # Stream Claude response
        article_content = ""
        await emit(run_id, "writing", "running", "Claude is analyzing and writing strategy...")

        with client.messages.stream(
            model="claude-sonnet-4-6",
            max_tokens=4000,
            messages=[{"role": "user", "content": prompt}]
        ) as stream:
            chunks = []
            for text in stream.text_stream:
                chunks.append(text)
                # Emit chunks every ~200 chars for smooth streaming
                if sum(len(c) for c in chunks) > 200:
                    chunk_text = "".join(chunks)
                    await broadcast(run_id, {
                        "type": "stream",
                        "phase": "writing",
                        "text": chunk_text,
                        "ts": datetime.now().isoformat(),
                    })
                    chunks = []

            if chunks:
                await broadcast(run_id, {
                    "type": "stream",
                    "phase": "writing",
                    "text": "".join(chunks),
                    "ts": datetime.now().isoformat(),
                })

            article_content = stream.get_final_message().content[0].text

        (tmp / "strategy.md").write_text(article_content)
        await emit(run_id, "writing", "done", "SEO strategy and content plan complete")

        # ── PHASE 4: Generate HTML Report ───────────────────────────────────
        await emit(run_id, "report", "running", "Generating full SEO report...")

        report_html = build_html_report(
            site_url=site_url,
            run_id=run_id,
            audit_summary=audit_summary,
            gsc_summary=gsc_summary,
            keyword_summary=keyword_summary,
            strategy=article_content,
            cwv_data=json.loads((tmp / "cwv.json").read_text()) if (tmp / "cwv.json").exists() else {},
        )

        report_path = REPORTS_DIR / f"report_{run_id}.html"
        report_path.write_text(report_html)
        run["report_path"] = str(report_path)

        await emit(run_id, "report", "done", "Report generated", {"report_id": run_id})

        # ── DONE ────────────────────────────────────────────────────────────
        run["status"] = "done"
        await broadcast(run_id, {
            "type": "complete",
            "run_id": run_id,
            "site_url": site_url,
            "ts": datetime.now().isoformat(),
        })

    except Exception as e:
        run["status"] = "error"
        await broadcast(run_id, {
            "type": "error",
            "message": str(e),
            "ts": datetime.now().isoformat(),
        })
        raise


def build_html_report(site_url, run_id, audit_summary, gsc_summary, keyword_summary, strategy, cwv_data) -> str:
    import markdown as md_lib

    strategy_html = md_lib.markdown(strategy, extensions=["tables", "fenced_code"])

    cwv_results = cwv_data.get("results", [{}])[0] if cwv_data.get("results") else {}
    lcp = cwv_results.get("lcp_ms", "N/A")
    cls = cwv_results.get("cls", "N/A")
    ttfb = cwv_results.get("ttfb_ms", "N/A")
    lcp_status = cwv_results.get("lcp_status", "unknown")

    def score_badge(status):
        colors = {"good": "#10b981", "needs_improvement": "#f59e0b", "poor": "#ef4444", "unknown": "#6b7280"}
        return f'<span style="color:{colors.get(status,colors["unknown"])};font-weight:700">{status.replace("_"," ").upper()}</span>'

    return f"""<!DOCTYPE html>
<html lang="en">
<head>
<meta charset="UTF-8">
<meta name="viewport" content="width=device-width, initial-scale=1">
<title>SEO Report — {site_url}</title>
<style>
  * {{ box-sizing: border-box; margin: 0; padding: 0; }}
  body {{ font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', sans-serif; background: #f8fafc; color: #1e293b; }}
  .header {{ background: linear-gradient(135deg, #1e40af, #7c3aed); color: white; padding: 40px 48px; }}
  .header h1 {{ font-size: 2em; font-weight: 800; }}
  .header p {{ opacity: 0.85; margin-top: 8px; font-size: 1.05em; }}
  .container {{ max-width: 1100px; margin: 0 auto; padding: 40px 24px; }}
  .grid {{ display: grid; grid-template-columns: repeat(auto-fit, minmax(200px, 1fr)); gap: 16px; margin: 24px 0; }}
  .card {{ background: white; border-radius: 12px; padding: 24px; box-shadow: 0 1px 3px rgba(0,0,0,.08); }}
  .card-value {{ font-size: 2.2em; font-weight: 800; color: #1e40af; }}
  .card-label {{ color: #64748b; font-size: 0.88em; margin-top: 4px; }}
  .card-sub {{ font-size: 0.82em; margin-top: 8px; }}
  .section {{ background: white; border-radius: 12px; padding: 32px; box-shadow: 0 1px 3px rgba(0,0,0,.08); margin: 24px 0; }}
  .section h2 {{ font-size: 1.3em; font-weight: 700; color: #1e293b; margin-bottom: 20px; padding-bottom: 12px; border-bottom: 2px solid #e2e8f0; }}
  .badge {{ display: inline-block; padding: 3px 10px; border-radius: 20px; font-size: 0.78em; font-weight: 600; }}
  .badge-red {{ background: #fee2e2; color: #991b1b; }}
  .badge-yellow {{ background: #fef3c7; color: #92400e; }}
  .badge-green {{ background: #d1fae5; color: #065f46; }}
  .badge-blue {{ background: #dbeafe; color: #1e40af; }}
  .strategy-content h2 {{ font-size: 1.15em; color: #1e40af; margin: 24px 0 10px; border: none; padding: 0; }}
  .strategy-content h3 {{ font-size: 1em; color: #374151; margin: 16px 0 8px; }}
  .strategy-content ul, .strategy-content ol {{ padding-left: 20px; margin: 8px 0; }}
  .strategy-content li {{ margin: 6px 0; line-height: 1.6; }}
  .strategy-content p {{ line-height: 1.7; margin: 10px 0; }}
  .strategy-content strong {{ color: #1e293b; }}
  .strategy-content table {{ width: 100%; border-collapse: collapse; margin: 12px 0; }}
  .strategy-content th {{ background: #f1f5f9; padding: 8px 12px; text-align: left; font-size: 0.88em; }}
  .strategy-content td {{ padding: 8px 12px; border-bottom: 1px solid #e2e8f0; font-size: 0.88em; }}
  .footer {{ text-align: center; color: #94a3b8; font-size: 0.85em; padding: 32px; }}
  .cwv-row {{ display: flex; gap: 16px; flex-wrap: wrap; }}
  .cwv-item {{ flex: 1; min-width: 120px; background: #f8fafc; border-radius: 8px; padding: 16px; text-align: center; }}
  .cwv-val {{ font-size: 1.6em; font-weight: 700; }}
  .cwv-label {{ font-size: 0.8em; color: #64748b; margin-top: 4px; }}
</style>
</head>
<body>
<div class="header">
  <h1>SEO Analysis Report</h1>
  <p>{site_url} &nbsp;·&nbsp; Generated {datetime.now().strftime('%B %d, %Y at %H:%M')}</p>
</div>

<div class="container">

  <!-- Metrics Grid -->
  <div class="grid">
    <div class="card">
      <div class="card-value">{audit_summary.get('pages_crawled', audit_summary.get('total_issues', '—'))}</div>
      <div class="card-label">Pages Crawled</div>
    </div>
    <div class="card">
      <div class="card-value" style="color:#ef4444">{audit_summary.get('broken_links', 0)}</div>
      <div class="card-label">Broken Links</div>
    </div>
    <div class="card">
      <div class="card-value" style="color:#f59e0b">{audit_summary.get('missing_meta_title', 0)}</div>
      <div class="card-label">Missing Meta Titles</div>
    </div>
    <div class="card">
      <div class="card-value" style="color:#f59e0b">{audit_summary.get('missing_meta_description', 0)}</div>
      <div class="card-label">Missing Meta Desc.</div>
    </div>
    <div class="card">
      <div class="card-value">{gsc_summary.get('total_clicks', '—')}</div>
      <div class="card-label">GSC Clicks (28d)</div>
    </div>
    <div class="card">
      <div class="card-value">{keyword_summary.get('clusters', '—')}</div>
      <div class="card-label">Keyword Clusters</div>
    </div>
  </div>

  <!-- Core Web Vitals -->
  {"" if not cwv_results else f'''
  <div class="section">
    <h2>Core Web Vitals</h2>
    <div class="cwv-row">
      <div class="cwv-item">
        <div class="cwv-val" style="color:{"#10b981" if lcp_status=="good" else "#f59e0b" if lcp_status=="needs_improvement" else "#ef4444"}">{lcp}ms</div>
        <div class="cwv-label">LCP</div>
        <div style="margin-top:6px;font-size:0.78em">{score_badge(lcp_status)}</div>
      </div>
      <div class="cwv-item">
        <div class="cwv-val">{cls}</div>
        <div class="cwv-label">CLS</div>
      </div>
      <div class="cwv-item">
        <div class="cwv-val">{ttfb}ms</div>
        <div class="cwv-label">TTFB</div>
      </div>
    </div>
  </div>
  '''}

  <!-- GSC Summary -->
  {f'''
  <div class="section">
    <h2>Search Console Overview (Last 28 Days)</h2>
    <div class="grid" style="margin:0">
      <div class="card" style="box-shadow:none;background:#f8fafc">
        <div class="card-value">{gsc_summary.get("total_clicks","—")}</div>
        <div class="card-label">Total Clicks</div>
      </div>
      <div class="card" style="box-shadow:none;background:#f8fafc">
        <div class="card-value">{gsc_summary.get("total_impressions","—")}</div>
        <div class="card-label">Impressions</div>
      </div>
      <div class="card" style="box-shadow:none;background:#f8fafc">
        <div class="card-value" style="color:#ef4444">{gsc_summary.get("ranking_drops","—")}</div>
        <div class="card-label">Ranking Drops</div>
      </div>
      <div class="card" style="box-shadow:none;background:#f8fafc">
        <div class="card-value" style="color:#10b981">{gsc_summary.get("quick_wins","—")}</div>
        <div class="card-label">Quick Wins</div>
      </div>
    </div>
  </div>
  ''' if gsc_summary else ''}

  <!-- AI Strategy -->
  <div class="section">
    <h2>AI SEO Strategy & Action Plan</h2>
    <div class="strategy-content">
      {strategy_html}
    </div>
  </div>

</div>
<div class="footer">Generated by SEO AI Employee &nbsp;·&nbsp; Run ID: {run_id}</div>
</body>
</html>"""


# ── ROUTES ────────────────────────────────────────────────────────────────────

@app.get("/", response_class=HTMLResponse)
async def index():
    return FileResponse(ROOT / "ui" / "static" / "index.html")


@app.post("/api/run")
async def start_run(body: dict):
    site_url = body.get("url", "").strip()
    if not site_url:
        return JSONResponse({"error": "URL required"}, status_code=400)
    if not site_url.startswith(("http://", "https://")):
        site_url = "https://" + site_url

    run_id = str(uuid.uuid4())[:8]
    runs[run_id] = {
        "run_id": run_id,
        "site_url": site_url,
        "status": "queued",
        "started_at": datetime.now().isoformat(),
        "events": [],
        "report_path": None,
    }
    connections[run_id] = []

    # Start pipeline in background
    asyncio.create_task(run_seo_pipeline(run_id, site_url))
    return {"run_id": run_id}


@app.get("/api/runs")
async def list_runs():
    return [
        {k: v for k, v in r.items() if k != "events"}
        for r in reversed(list(runs.values()))
    ]


@app.get("/api/run/{run_id}")
async def get_run(run_id: str):
    if run_id not in runs:
        return JSONResponse({"error": "Not found"}, status_code=404)
    return runs[run_id]


@app.get("/api/report/{run_id}", response_class=HTMLResponse)
async def get_report(run_id: str):
    if run_id not in runs or not runs[run_id].get("report_path"):
        return HTMLResponse("<p>Report not ready yet.</p>", status_code=404)
    return HTMLResponse(Path(runs[run_id]["report_path"]).read_text())


@app.websocket("/ws/{run_id}")
async def websocket_endpoint(websocket: WebSocket, run_id: str):
    await websocket.accept()
    if run_id not in connections:
        connections[run_id] = []
    connections[run_id].append(websocket)

    # Replay past events for reconnects
    if run_id in runs:
        for event in runs[run_id].get("events", []):
            await websocket.send_text(json.dumps(event))

        if runs[run_id]["status"] in ("done", "error"):
            await websocket.send_text(json.dumps({"type": "complete", "run_id": run_id}))

    try:
        while True:
            await websocket.receive_text()  # keep alive
    except WebSocketDisconnect:
        if run_id in connections and websocket in connections[run_id]:
            connections[run_id].remove(websocket)


if __name__ == "__main__":
    import uvicorn
    uvicorn.run("ui.app:app", host="0.0.0.0", port=8000, reload=True)
