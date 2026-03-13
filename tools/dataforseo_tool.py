#!/usr/bin/env python3
"""
DataForSEO API tool for the SEO AI Employee.
Covers: SERP, keyword data, keyword suggestions, keyword gaps,
competitor keywords, and backlink data.
"""

import argparse
import json
import os
import sys
import time
from base64 import b64encode

import requests


class DataForSEOClient:
    BASE = "https://api.dataforseo.com/v3"

    def __init__(self, login: str, password: str, sandbox: bool = False):
        creds = b64encode(f"{login}:{password}".encode()).decode()
        self.headers = {
            "Authorization": f"Basic {creds}",
            "Content-Type": "application/json",
        }
        if sandbox:
            self.BASE = "https://sandbox.dataforseo.com/v3"

    def post(self, endpoint: str, payload: list[dict]) -> dict:
        url = f"{self.BASE}/{endpoint}"
        resp = requests.post(url, headers=self.headers, json=payload, timeout=60)
        resp.raise_for_status()
        return resp.json()

    def get(self, endpoint: str) -> dict:
        url = f"{self.BASE}/{endpoint}"
        resp = requests.get(url, headers=self.headers, timeout=60)
        resp.raise_for_status()
        return resp.json()

    def wait_for_task(self, task_id: str, endpoint: str, max_wait: int = 120) -> dict:
        """Poll a task until it completes."""
        waited = 0
        while waited < max_wait:
            time.sleep(5)
            waited += 5
            result = self.get(f"{endpoint}/{task_id}")
            tasks = result.get("tasks", [])
            if tasks and tasks[0].get("status_code") == 20000:
                return result
            if tasks and tasks[0].get("status_code", 0) >= 40000:
                raise RuntimeError(f"Task failed: {tasks[0].get('status_message')}")
        raise TimeoutError(f"Task {task_id} did not complete within {max_wait}s")

    # ── SERP ────────────────────────────────────────────────────────────
    def serp(self, keyword: str, location_code: int, language_code: str, depth: int = 10) -> list[dict]:
        payload = [{
            "keyword": keyword,
            "location_code": location_code,
            "language_code": language_code,
            "depth": depth,
            "calculate_rectangles": False,
        }]
        resp = self.post("serp/google/organic/live/advanced", payload)
        tasks = resp.get("tasks", [])
        if not tasks or tasks[0].get("status_code") != 20000:
            raise RuntimeError(f"SERP error: {tasks[0].get('status_message') if tasks else 'no tasks'}")
        items = tasks[0].get("result", [{}])[0].get("items", [])
        return [
            {
                "rank": item.get("rank_absolute"),
                "url": item.get("url"),
                "title": item.get("title"),
                "description": item.get("description"),
                "domain": item.get("domain"),
            }
            for item in items
            if item.get("type") == "organic"
        ]

    # ── KEYWORD DATA ─────────────────────────────────────────────────────
    def keyword_data(self, keywords: list[str], location_code: int = 2840, language_code: str = "en") -> list[dict]:
        payload = [{
            "keywords": keywords,
            "location_code": location_code,
            "language_code": language_code,
        }]
        resp = self.post("keywords_data/google_ads/search_volume/live", payload)
        tasks = resp.get("tasks", [])
        if not tasks or tasks[0].get("status_code") != 20000:
            raise RuntimeError(f"Keyword data error: {tasks[0].get('status_message')}")
        return tasks[0].get("result", [])

    # ── KEYWORD SUGGESTIONS ───────────────────────────────────────────────
    def keyword_suggestions(self, seed: str, location_code: int = 2840, language_code: str = "en", limit: int = 100) -> list[dict]:
        payload = [{
            "keyword": seed,
            "location_code": location_code,
            "language_code": language_code,
            "limit": limit,
            "filters": [["keyword_info.search_volume", ">", 100]],
            "order_by": ["keyword_info.search_volume,desc"],
        }]
        resp = self.post("dataforseo_labs/google/keyword_suggestions/live", payload)
        tasks = resp.get("tasks", [])
        if not tasks or tasks[0].get("status_code") != 20000:
            raise RuntimeError(f"Keyword suggestions error: {tasks[0].get('status_message')}")
        items = tasks[0].get("result", [{}])[0].get("items", [])
        return [
            {
                "keyword": item.get("keyword"),
                "volume": item.get("keyword_info", {}).get("search_volume"),
                "cpc": item.get("keyword_info", {}).get("cpc"),
                "competition": item.get("keyword_info", {}).get("competition"),
                "kd": item.get("keyword_properties", {}).get("keyword_difficulty"),
            }
            for item in items
        ]

    # ── COMPETITOR KEYWORDS ───────────────────────────────────────────────
    def competitor_keywords(self, domain: str, location_code: int = 2840, language_code: str = "en", limit: int = 200) -> list[dict]:
        payload = [{
            "target": domain,
            "location_code": location_code,
            "language_code": language_code,
            "limit": limit,
            "order_by": ["metrics.organic.etv,desc"],
        }]
        resp = self.post("dataforseo_labs/google/ranked_keywords/live", payload)
        tasks = resp.get("tasks", [])
        if not tasks or tasks[0].get("status_code") != 20000:
            raise RuntimeError(f"Competitor keywords error: {tasks[0].get('status_message')}")
        items = tasks[0].get("result", [{}])[0].get("items", [])
        return [
            {
                "keyword": item.get("keyword_data", {}).get("keyword"),
                "volume": item.get("keyword_data", {}).get("keyword_info", {}).get("search_volume"),
                "position": item.get("ranked_serp_element", {}).get("serp_item", {}).get("rank_absolute"),
                "url": item.get("ranked_serp_element", {}).get("serp_item", {}).get("url"),
                "kd": item.get("keyword_data", {}).get("keyword_properties", {}).get("keyword_difficulty"),
            }
            for item in items
        ]

    # ── KEYWORD GAP ───────────────────────────────────────────────────────
    def keyword_gap(self, our_domain: str, competitors: list[str], location_code: int = 2840, language_code: str = "en") -> list[dict]:
        targets = [{"target": c, "type": "organic"} for c in competitors]
        payload = [{
            "targets": targets,
            "exclude_targets": [{"target": our_domain, "type": "organic"}],
            "location_code": location_code,
            "language_code": language_code,
            "limit": 500,
            "order_by": ["keyword_data.keyword_info.search_volume,desc"],
        }]
        resp = self.post("dataforseo_labs/google/competitors_domain/live", payload)
        tasks = resp.get("tasks", [])
        if not tasks or tasks[0].get("status_code") != 20000:
            raise RuntimeError(f"Keyword gap error: {tasks[0].get('status_message')}")
        items = tasks[0].get("result", [{}])[0].get("items", [])
        return [
            {
                "domain": item.get("domain"),
                "metrics": item.get("metrics", {}).get("organic", {}),
            }
            for item in items
        ]

    # ── BACKLINKS ─────────────────────────────────────────────────────────
    def backlinks(self, domain: str, limit: int = 100) -> dict:
        payload = [{"target": domain, "limit": limit, "order_by": ["rank,desc"]}]
        resp = self.post("backlinks/backlinks/live", payload)
        tasks = resp.get("tasks", [])
        if not tasks or tasks[0].get("status_code") != 20000:
            raise RuntimeError(f"Backlinks error: {tasks[0].get('status_message')}")
        return tasks[0].get("result", [{}])[0]


def main():
    parser = argparse.ArgumentParser(description="DataForSEO Tool")
    parser.add_argument("--mode", required=True,
        choices=["serp", "keyword_data", "keyword_suggestions", "competitor_keywords", "keyword_gap", "backlinks"])
    parser.add_argument("--keyword")
    parser.add_argument("--keywords")
    parser.add_argument("--seed")
    parser.add_argument("--domain")
    parser.add_argument("--our-domain")
    parser.add_argument("--competitors")
    parser.add_argument("--top", type=int, default=10)
    parser.add_argument("--limit", type=int, default=100)
    parser.add_argument("--location-code", type=int, default=2840)
    parser.add_argument("--language-code", default="en")
    parser.add_argument("--sandbox", action="store_true")
    parser.add_argument("--output", required=True)
    args = parser.parse_args()

    login = os.environ.get("DATAFORSEO_LOGIN", "")
    password = os.environ.get("DATAFORSEO_PASSWORD", "")
    if not login or not password:
        sys.exit("ERROR: DATAFORSEO_LOGIN and DATAFORSEO_PASSWORD required")

    client = DataForSEOClient(login, password, sandbox=args.sandbox)

    if args.mode == "serp":
        if not args.keyword:
            sys.exit("ERROR: --keyword required for serp mode")
        result = client.serp(args.keyword, args.location_code, args.language_code, args.top)
        output = {"keyword": args.keyword, "results": result}

    elif args.mode == "keyword_data":
        if not args.keywords:
            sys.exit("ERROR: --keywords required (comma-separated)")
        kw_list = [k.strip() for k in args.keywords.split(",")]
        result = client.keyword_data(kw_list, args.location_code, args.language_code)
        output = {"keywords": result}

    elif args.mode == "keyword_suggestions":
        if not args.seed:
            sys.exit("ERROR: --seed required")
        result = client.keyword_suggestions(args.seed, args.location_code, args.language_code, args.limit)
        output = {"seed": args.seed, "suggestions": result}

    elif args.mode == "competitor_keywords":
        if not args.domain:
            sys.exit("ERROR: --domain required")
        result = client.competitor_keywords(args.domain, args.location_code, args.language_code, args.top)
        output = {"domain": args.domain, "keywords": result}

    elif args.mode == "keyword_gap":
        if not args.our_domain or not args.competitors:
            sys.exit("ERROR: --our-domain and --competitors required")
        comps = [c.strip() for c in args.competitors.split(",")]
        result = client.keyword_gap(args.our_domain, comps, args.location_code, args.language_code)
        output = {"our_domain": args.our_domain, "competitors": comps, "gaps": result}

    elif args.mode == "backlinks":
        if not args.domain:
            sys.exit("ERROR: --domain required")
        result = client.backlinks(args.domain, args.limit)
        output = {"domain": args.domain, "backlinks": result}

    else:
        sys.exit(f"Unknown mode: {args.mode}")

    with open(args.output, "w") as f:
        json.dump(output, f, indent=2)
    print(f"Output saved: {args.output}")


if __name__ == "__main__":
    main()
