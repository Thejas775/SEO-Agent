#!/usr/bin/env python3
"""
Google Search Console tool for the SEO AI Employee.
Fetches performance data and runs analysis for ranking drops,
CTR opportunities, and quick wins.
"""

import argparse
import json
import os
import sys
from datetime import date, timedelta

from google.oauth2 import service_account
from googleapiclient.discovery import build


SCOPES = ["https://www.googleapis.com/auth/webmasters.readonly"]


def get_gsc_service():
    key_source = os.environ.get("GSC_SERVICE_ACCOUNT_JSON", "")
    if not key_source:
        sys.exit("ERROR: GSC_SERVICE_ACCOUNT_JSON env var not set")

    if key_source.strip().startswith("{"):
        import tempfile
        tmp = tempfile.NamedTemporaryFile(mode="w", suffix=".json", delete=False)
        tmp.write(key_source)
        tmp.flush()
        key_path = tmp.name
    else:
        key_path = key_source

    creds = service_account.Credentials.from_service_account_file(
        key_path, scopes=SCOPES
    )
    return build("searchconsole", "v1", credentials=creds)


def fetch_data(service, site: str, start_date: str, end_date: str, dimensions: list[str]) -> list[dict]:
    request = {
        "startDate": start_date,
        "endDate": end_date,
        "dimensions": dimensions,
        "rowLimit": 25000,
        "startRow": 0,
    }
    rows = []
    while True:
        response = service.searchanalytics().query(siteUrl=site, body=request).execute()
        batch = response.get("rows", [])
        rows.extend(batch)
        if len(batch) < 25000:
            break
        request["startRow"] += 25000
    return rows


def rows_to_records(rows: list[dict], dimensions: list[str]) -> list[dict]:
    records = []
    for row in rows:
        record = dict(zip(dimensions, row.get("keys", [])))
        record.update({
            "clicks": row.get("clicks", 0),
            "impressions": row.get("impressions", 0),
            "ctr": round(row.get("ctr", 0) * 100, 2),
            "position": round(row.get("position", 0), 1),
        })
        records.append(record)
    return records


def analyze(records: list[dict], compare_records: list[dict] | None = None) -> dict:
    # Build lookup for comparison period
    compare_lookup: dict = {}
    if compare_records:
        for r in compare_records:
            key = (r.get("page", ""), r.get("query", ""))
            compare_lookup[key] = r

    ranking_drops = []
    ctr_opportunities = []
    quick_wins = []
    top_pages: dict = {}

    for r in records:
        page = r.get("page", "")
        query = r.get("query", "")
        pos = r.get("position", 100)
        ctr = r.get("ctr", 0)
        impressions = r.get("impressions", 0)
        clicks = r.get("clicks", 0)

        # Aggregate clicks by page
        top_pages[page] = top_pages.get(page, 0) + clicks

        key = (page, query)
        prev = compare_lookup.get(key)

        # Ranking drops
        if prev and (pos - prev["position"]) >= 3 and clicks > 0:
            ranking_drops.append({
                **r,
                "prev_position": prev["position"],
                "position_change": round(pos - prev["position"], 1),
            })

        # CTR opportunities: good position, low CTR, decent impressions
        if 1 <= pos <= 10 and ctr < 3.0 and impressions >= 100:
            ctr_opportunities.append(r)

        # Quick wins: position 11–20
        if 11 <= pos <= 20 and impressions >= 50:
            quick_wins.append(r)

    # Sort
    ranking_drops.sort(key=lambda x: x["position_change"], reverse=True)
    ctr_opportunities.sort(key=lambda x: x["impressions"], reverse=True)
    quick_wins.sort(key=lambda x: x["impressions"], reverse=True)
    top_pages_list = sorted(
        [{"page": p, "clicks": c} for p, c in top_pages.items()],
        key=lambda x: x["clicks"],
        reverse=True,
    )[:20]

    return {
        "ranking_drops": ranking_drops[:50],
        "ctr_opportunities": ctr_opportunities[:50],
        "quick_wins": quick_wins[:50],
        "top_pages": top_pages_list,
        "total_clicks": sum(r.get("clicks", 0) for r in records),
        "total_impressions": sum(r.get("impressions", 0) for r in records),
    }


def main():
    parser = argparse.ArgumentParser(description="Google Search Console Tool")
    parser.add_argument("--mode", choices=["fetch", "analyze", "pages", "queries"], required=True)
    parser.add_argument("--site", default=os.environ.get("GSC_SITE_URL", ""))
    parser.add_argument("--days", type=int, default=28)
    parser.add_argument("--compare-days", type=int, default=0)
    parser.add_argument("--start-date")
    parser.add_argument("--end-date")
    parser.add_argument("--dimensions", default="page,query")
    parser.add_argument("--output", required=True)
    args = parser.parse_args()

    if not args.site:
        sys.exit("ERROR: --site or GSC_SITE_URL required")

    end = date.today() - timedelta(days=3)  # GSC has ~3 day lag
    start = end - timedelta(days=args.days)
    end_str = args.end_date or str(end)
    start_str = args.start_date or str(start)

    dims = [d.strip() for d in args.dimensions.split(",")]

    service = get_gsc_service()
    print(f"Fetching GSC data: {start_str} → {end_str}, dims={dims}")

    rows = fetch_data(service, args.site, start_str, end_str, dims)
    records = rows_to_records(rows, dims)
    print(f"Fetched {len(records)} records")

    if args.mode == "fetch":
        output = {"records": records, "start_date": start_str, "end_date": end_str}
    elif args.mode == "analyze":
        compare_records = None
        if args.compare_days:
            cmp_end = start - timedelta(days=1)
            cmp_start = cmp_end - timedelta(days=args.compare_days)
            cmp_rows = fetch_data(service, args.site, str(cmp_start), str(cmp_end), dims)
            compare_records = rows_to_records(cmp_rows, dims)
        output = analyze(records, compare_records)
        output["start_date"] = start_str
        output["end_date"] = end_str
    elif args.mode == "pages":
        by_page: dict = {}
        for r in records:
            p = r.get("page", "")
            if p not in by_page:
                by_page[p] = {"page": p, "clicks": 0, "impressions": 0, "queries": 0}
            by_page[p]["clicks"] += r.get("clicks", 0)
            by_page[p]["impressions"] += r.get("impressions", 0)
            by_page[p]["queries"] += 1
        output = {"pages": sorted(by_page.values(), key=lambda x: x["clicks"], reverse=True)}
    elif args.mode == "queries":
        by_query: dict = {}
        for r in records:
            q = r.get("query", "")
            if q not in by_query:
                by_query[q] = {**r}
            else:
                by_query[q]["clicks"] += r.get("clicks", 0)
                by_query[q]["impressions"] += r.get("impressions", 0)
        output = {"queries": sorted(by_query.values(), key=lambda x: x["clicks"], reverse=True)}
    else:
        output = {"records": records}

    with open(args.output, "w") as f:
        json.dump(output, f, indent=2)
    print(f"Output saved: {args.output}")


if __name__ == "__main__":
    main()
