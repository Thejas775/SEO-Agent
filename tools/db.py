#!/usr/bin/env python3
"""
Unified database interface for all SEO agents.
Provides save/get/update operations for all SEO data types.
"""

import argparse
import json
import os
import sys
from datetime import date

import psycopg2
import psycopg2.extras


def get_conn():
    db_url = os.environ.get("DATABASE_URL", "")
    if not db_url:
        sys.exit("ERROR: DATABASE_URL env var not set")
    return psycopg2.connect(db_url)


# ── ANALYSIS ──────────────────────────────────────────────────────────────────

def save_analysis(args):
    with open(args.file) as f:
        data = json.load(f)
    conn = get_conn()
    with conn:
        with conn.cursor() as cur:
            cur.execute("""
                INSERT INTO seo_analysis_runs
                    (agent, analysis_date, ranking_drops, ctr_opportunities, quick_wins, raw_data)
                VALUES (%s, %s, %s, %s, %s, %s)
                ON CONFLICT (agent, analysis_date) DO UPDATE SET
                    ranking_drops = EXCLUDED.ranking_drops,
                    ctr_opportunities = EXCLUDED.ctr_opportunities,
                    quick_wins = EXCLUDED.quick_wins,
                    raw_data = EXCLUDED.raw_data
            """, (
                args.agent,
                date.today(),
                len(data.get("ranking_drops", [])),
                len(data.get("ctr_opportunities", [])),
                len(data.get("quick_wins", [])),
                json.dumps(data),
            ))
    conn.close()
    print(f"Analysis saved for agent={args.agent}")


# ── RANKINGS ──────────────────────────────────────────────────────────────────

def save_rankings(args):
    with open(args.data) as f:
        data = json.load(f)
    records = data.get("records", data) if isinstance(data, dict) else data
    conn = get_conn()
    with conn:
        with conn.cursor() as cur:
            for r in records:
                cur.execute("""
                    INSERT INTO gsc_data (page, query, clicks, impressions, ctr, position, recorded_at)
                    VALUES (%s, %s, %s, %s, %s, %s, %s)
                    ON CONFLICT (page, query, recorded_at) DO NOTHING
                """, (
                    r.get("page", ""),
                    r.get("query", ""),
                    r.get("clicks", 0),
                    r.get("impressions", 0),
                    r.get("ctr", 0),
                    r.get("position", 0),
                    args.date or str(date.today()),
                ))
    conn.close()
    print(f"Saved {len(records)} ranking records")


def get_ranking_changes(args):
    conn = get_conn()
    days = int(args.days)
    with conn.cursor(cursor_factory=psycopg2.extras.RealDictCursor) as cur:
        cur.execute("""
            WITH cur AS (
                SELECT page, query, AVG(position) AS pos
                FROM gsc_data WHERE recorded_at >= CURRENT_DATE - INTERVAL '%s days'
                GROUP BY page, query
            ),
            prev AS (
                SELECT page, query, AVG(position) AS pos
                FROM gsc_data
                WHERE recorded_at >= CURRENT_DATE - INTERVAL '%s days'
                  AND recorded_at < CURRENT_DATE - INTERVAL '%s days'
                GROUP BY page, query
            )
            SELECT c.page, c.query, ROUND(p.pos::numeric,1) prev_pos,
                   ROUND(c.pos::numeric,1) cur_pos,
                   ROUND((p.pos-c.pos)::numeric,1) change
            FROM cur c JOIN prev p USING(page,query)
            WHERE ABS(p.pos-c.pos) >= 1
            ORDER BY change DESC LIMIT 50
        """, (days, days * 2, days))
        rows = [dict(r) for r in cur.fetchall()]
    conn.close()
    if args.output:
        with open(args.output, "w") as f:
            json.dump(rows, f, indent=2)
    else:
        print(json.dumps(rows, indent=2))


# ── KEYWORDS ──────────────────────────────────────────────────────────────────

def save_keywords(args):
    with open(args.clusters) as f:
        data = json.load(f)
    clusters = data.get("clusters", []) if isinstance(data, dict) else data

    conn = get_conn()
    with conn:
        with conn.cursor() as cur:
            for cluster in clusters:
                cur.execute("""
                    INSERT INTO keyword_clusters
                        (primary_keyword, primary_volume, supporting_keywords,
                         intent, content_type, avg_kd, total_volume, created_at)
                    VALUES (%s, %s, %s, %s, %s, %s, %s, NOW())
                    ON CONFLICT (primary_keyword) DO UPDATE SET
                        primary_volume = EXCLUDED.primary_volume,
                        supporting_keywords = EXCLUDED.supporting_keywords,
                        intent = EXCLUDED.intent,
                        avg_kd = EXCLUDED.avg_kd,
                        total_volume = EXCLUDED.total_volume
                    RETURNING id
                """, (
                    cluster["primary_keyword"],
                    cluster.get("primary_volume", 0),
                    json.dumps(cluster.get("supporting_keywords", [])),
                    cluster.get("intent", "informational"),
                    cluster.get("content_type", "blog_post"),
                    cluster.get("avg_kd", 0),
                    cluster.get("total_volume", 0),
                ))

    if args.calendar:
        with open(args.calendar) as f:
            cal_data = json.load(f)
        entries = cal_data.get("entries", []) if isinstance(cal_data, dict) else cal_data
        with conn:
            with conn.cursor() as cur:
                for entry in entries:
                    cur.execute("""
                        INSERT INTO content_calendar
                            (week, day, publish_date, title, primary_keyword,
                             supporting_keywords, intent, content_type,
                             target_word_count, priority, status, created_at)
                        VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s, 'planned', NOW())
                        ON CONFLICT (publish_date, primary_keyword) DO NOTHING
                    """, (
                        entry.get("week"),
                        entry.get("day"),
                        entry.get("publish_date"),
                        entry.get("title"),
                        entry.get("primary_keyword"),
                        json.dumps(entry.get("supporting_keywords", [])),
                        entry.get("intent"),
                        entry.get("content_type"),
                        entry.get("target_word_count", 1500),
                        entry.get("priority", "medium"),
                    ))
    conn.close()
    print(f"Saved {len(clusters)} keyword clusters")


def get_cached_keyword_data(args):
    conn = get_conn()
    max_age = int(args.max_age_days)
    with conn.cursor(cursor_factory=psycopg2.extras.RealDictCursor) as cur:
        cur.execute("""
            SELECT * FROM keyword_clusters
            WHERE primary_keyword = %s
              AND created_at >= NOW() - INTERVAL '%s days'
            LIMIT 1
        """, (args.keyword, max_age))
        row = cur.fetchone()
    conn.close()
    if row:
        print(json.dumps(dict(row), default=str))
    else:
        print("null")


# ── ARTICLES ──────────────────────────────────────────────────────────────────

def save_article(args):
    content = open(args.content).read() if args.content else ""
    schema = json.load(open(args.schema)) if args.schema else {}
    conn = get_conn()
    with conn:
        with conn.cursor() as cur:
            cur.execute("""
                INSERT INTO articles
                    (title, content, meta_title, meta_description, schema_markup,
                     primary_keyword, status, word_count, created_at)
                VALUES (%s, %s, %s, %s, %s, %s, %s, %s, NOW())
                RETURNING id
            """, (
                args.title,
                content,
                args.meta_title,
                args.meta_description,
                json.dumps(schema),
                args.primary_keyword,
                args.status or "draft",
                len(content.split()),
            ))
            article_id = cur.fetchone()[0]
    conn.close()
    print(f"Article saved with ID: {article_id}")
    return article_id


def get_article(args):
    conn = get_conn()
    with conn.cursor(cursor_factory=psycopg2.extras.RealDictCursor) as cur:
        cur.execute("SELECT * FROM articles WHERE id = %s", (args.id,))
        row = cur.fetchone()
    conn.close()
    if row:
        print(json.dumps(dict(row), default=str))
    else:
        print("null")
        sys.exit(f"Article {args.id} not found")


def update_article_status(args):
    conn = get_conn()
    with conn:
        with conn.cursor() as cur:
            if args.status == "published":
                cur.execute("""
                    UPDATE articles SET status = %s, published_url = %s, published_at = NOW()
                    WHERE id = %s
                """, (args.status, args.published_url or "", args.id))
            else:
                cur.execute("UPDATE articles SET status = %s WHERE id = %s", (args.status, args.id))
    conn.close()
    print(f"Article {args.id} status → {args.status}")


def find_internal_links(args):
    conn = get_conn()
    keywords = [k.strip() for k in args.keywords.split(",")]
    with conn.cursor(cursor_factory=psycopg2.extras.RealDictCursor) as cur:
        cur.execute("""
            SELECT title, published_url, primary_keyword
            FROM articles
            WHERE status = 'published'
              AND (
                primary_keyword = ANY(%s)
                OR title ILIKE ANY(%s)
              )
            LIMIT %s
        """, (keywords, [f"%{k}%" for k in keywords], int(args.limit or 5)))
        rows = [dict(r) for r in cur.fetchall()]
    conn.close()
    print(json.dumps(rows, indent=2))


# ── AUDIT ─────────────────────────────────────────────────────────────────────

def save_audit(args):
    with open(args.issues) as f:
        issues = json.load(f)
    if isinstance(issues, dict):
        issues = issues.get("issues", [])

    conn = get_conn()
    with conn:
        with conn.cursor() as cur:
            # Create audit run
            cur.execute("""
                INSERT INTO audit_runs (audit_type, audit_date, pages_crawled, total_issues)
                VALUES (%s, %s, %s, %s) RETURNING id
            """, (args.audit_type or "manual", date.today(), 0, len(issues)))
            run_id = cur.fetchone()[0]

            for issue in issues:
                cur.execute("""
                    INSERT INTO audit_issues
                        (audit_run_id, url, issue_type, severity, details, status, created_at)
                    VALUES (%s, %s, %s, %s, %s, 'open', NOW())
                    ON CONFLICT (url, issue_type) DO UPDATE SET
                        severity = EXCLUDED.severity,
                        details = EXCLUDED.details,
                        status = 'open'
                """, (
                    run_id,
                    issue.get("url"),
                    issue.get("issue_type"),
                    issue.get("severity", "low"),
                    issue.get("details", ""),
                ))
    conn.close()
    print(f"Audit saved: run_id={run_id}, {len(issues)} issues")


def get_fixable_issues(args):
    severities = [s.strip() for s in (args.severity or "high,medium").split(",")]
    fixable_types = [
        "missing_meta_description",
        "missing_meta_title",
        "missing_alt_text",
        "meta_title_too_long",
        "meta_description_too_long",
    ]
    if args.types:
        fixable_types = [t.strip() for t in args.types.split(",")]

    conn = get_conn()
    with conn.cursor(cursor_factory=psycopg2.extras.RealDictCursor) as cur:
        cur.execute("""
            SELECT * FROM audit_issues
            WHERE status = 'open'
              AND severity = ANY(%s)
              AND issue_type = ANY(%s)
            ORDER BY
                CASE severity WHEN 'critical' THEN 1 WHEN 'high' THEN 2 WHEN 'medium' THEN 3 ELSE 4 END,
                created_at DESC
            LIMIT %s
        """, (severities, fixable_types, int(args.limit or 50)))
        rows = [dict(r) for r in cur.fetchall()]
    conn.close()

    if args.output:
        with open(args.output, "w") as f:
            json.dump(rows, f, indent=2, default=str)
    else:
        print(json.dumps(rows, indent=2, default=str))


# ── REPORTS ───────────────────────────────────────────────────────────────────

def save_report(args):
    content = open(args.file, "rb").read()
    conn = get_conn()
    with conn:
        with conn.cursor() as cur:
            cur.execute("""
                INSERT INTO reports (period, report_date, file_path, content_html, created_at)
                VALUES (%s, %s, %s, %s, NOW())
            """, (args.period, args.date or str(date.today()), args.file, content.decode("utf-8", errors="replace")))
    conn.close()
    print(f"Report saved: {args.file}")


def get_priorities(args):
    conn = get_conn()
    with conn.cursor(cursor_factory=psycopg2.extras.RealDictCursor) as cur:
        cur.execute("""
            SELECT action, reason, priority, created_at
            FROM seo_priorities
            WHERE completed_at IS NULL
            ORDER BY
                CASE priority WHEN 'high' THEN 1 WHEN 'medium' THEN 2 ELSE 3 END,
                created_at DESC
            LIMIT %s
        """, (int(args.limit or 5),))
        rows = [dict(r) for r in cur.fetchall()]
    conn.close()

    if args.output:
        with open(args.output, "w") as f:
            json.dump(rows, f, indent=2, default=str)
    else:
        print(json.dumps(rows, indent=2, default=str))


def get_top_pages(args):
    conn = get_conn()
    with conn.cursor(cursor_factory=psycopg2.extras.RealDictCursor) as cur:
        cur.execute("""
            SELECT page, SUM(clicks) AS total_clicks
            FROM gsc_data
            WHERE recorded_at >= CURRENT_DATE - INTERVAL '28 days'
            GROUP BY page
            ORDER BY total_clicks DESC
            LIMIT %s
        """, (int(args.limit or 20),))
        rows = [r["page"] for r in cur.fetchall()]
    conn.close()

    if args.output:
        with open(args.output, "w") as f:
            f.write("\n".join(rows))
    else:
        print("\n".join(rows))


# ── DISPATCH ──────────────────────────────────────────────────────────────────

COMMANDS = {
    "save_analysis": save_analysis,
    "save_rankings": save_rankings,
    "get_ranking_changes": get_ranking_changes,
    "save_keywords": save_keywords,
    "get_cached_keyword_data": get_cached_keyword_data,
    "save_article": save_article,
    "get_article": get_article,
    "update_article_status": update_article_status,
    "find_internal_links": find_internal_links,
    "save_audit": save_audit,
    "get_fixable_issues": get_fixable_issues,
    "save_report": save_report,
    "get_priorities": get_priorities,
    "get_top_pages": get_top_pages,
}


def main():
    if len(sys.argv) < 2 or sys.argv[1] not in COMMANDS:
        print("Usage: db.py <command> [options]")
        print("Commands:", ", ".join(COMMANDS.keys()))
        sys.exit(1)

    command = sys.argv[1]
    parser = argparse.ArgumentParser(prog=f"db.py {command}")

    # Add all possible args — each command uses what it needs
    parser.add_argument("--file"); parser.add_argument("--agent")
    parser.add_argument("--data"); parser.add_argument("--date")
    parser.add_argument("--days", default="7"); parser.add_argument("--output")
    parser.add_argument("--clusters"); parser.add_argument("--calendar")
    parser.add_argument("--keyword"); parser.add_argument("--keywords")
    parser.add_argument("--max-age-days", default="7")
    parser.add_argument("--title"); parser.add_argument("--content")
    parser.add_argument("--meta-title"); parser.add_argument("--meta-description")
    parser.add_argument("--schema"); parser.add_argument("--primary-keyword")
    parser.add_argument("--status"); parser.add_argument("--id")
    parser.add_argument("--published-url"); parser.add_argument("--limit")
    parser.add_argument("--issues"); parser.add_argument("--crawl")
    parser.add_argument("--audit-type"); parser.add_argument("--severity")
    parser.add_argument("--types"); parser.add_argument("--period")
    parser.add_argument("--source")

    args = parser.parse_args(sys.argv[2:])
    COMMANDS[command](args)


if __name__ == "__main__":
    main()
