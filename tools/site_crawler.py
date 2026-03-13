#!/usr/bin/env python3
"""
SEO site crawler for technical audits.
Crawls a website and detects: broken links, missing meta tags,
missing alt text, duplicate titles, redirect chains.
"""

import argparse
import json
import os
import sys
import time
from collections import deque
from urllib.parse import urljoin, urlparse

import requests
from bs4 import BeautifulSoup


class SiteCrawler:
    def __init__(self, base_url: str, max_pages: int = 500, timeout: int = 15):
        self.base_url = base_url.rstrip("/")
        self.base_domain = urlparse(base_url).netloc
        self.max_pages = max_pages
        self.timeout = timeout
        self.session = requests.Session()
        self.session.headers["User-Agent"] = "SEO-Auditor-Bot/1.0 (audit)"
        self.visited: set[str] = set()
        self.queue: deque[str] = deque([base_url])
        self.pages: list[dict] = []
        self.issues: list[dict] = []

    def is_internal(self, url: str) -> bool:
        parsed = urlparse(url)
        return parsed.netloc == "" or parsed.netloc == self.base_domain

    def normalize(self, url: str, base: str) -> str | None:
        url = url.strip()
        if not url or url.startswith(("mailto:", "tel:", "javascript:", "#")):
            return None
        full = urljoin(base, url)
        parsed = urlparse(full)
        # Drop fragment
        return parsed._replace(fragment="").geturl()

    def fetch(self, url: str) -> tuple[int, dict, str]:
        """Returns (status_code, headers, html_content)"""
        try:
            resp = self.session.get(url, timeout=self.timeout, allow_redirects=True)
            # Check for redirect chain
            chain_length = len(resp.history)
            return resp.status_code, {
                "content_type": resp.headers.get("content-type", ""),
                "redirect_chain": chain_length,
                "final_url": resp.url,
            }, resp.text if resp.status_code == 200 else ""
        except requests.exceptions.Timeout:
            return 408, {"error": "timeout"}, ""
        except requests.exceptions.ConnectionError:
            return 0, {"error": "connection_error"}, ""
        except Exception as e:
            return 0, {"error": str(e)}, ""

    def parse_page(self, url: str, status: int, meta: dict, html: str) -> dict:
        page: dict = {
            "url": url,
            "status": status,
            "redirect_chain": meta.get("redirect_chain", 0),
            "final_url": meta.get("final_url", url),
            "meta_title": None,
            "meta_title_length": 0,
            "meta_description": None,
            "meta_description_length": 0,
            "h1_count": 0,
            "h1_text": None,
            "canonical": None,
            "robots_meta": None,
            "images_total": 0,
            "images_missing_alt": 0,
            "internal_links": 0,
            "external_links": 0,
            "issues": [],
        }

        if status != 200 or not html:
            return page

        soup = BeautifulSoup(html, "lxml")

        # Meta title
        title_tag = soup.find("title")
        if title_tag:
            page["meta_title"] = title_tag.get_text(strip=True)
            page["meta_title_length"] = len(page["meta_title"])
        else:
            page["issues"].append("missing_meta_title")

        # Meta description
        desc_tag = soup.find("meta", attrs={"name": "description"})
        if desc_tag:
            page["meta_description"] = desc_tag.get("content", "")
            page["meta_description_length"] = len(page["meta_description"])
        else:
            page["issues"].append("missing_meta_description")

        # H1
        h1s = soup.find_all("h1")
        page["h1_count"] = len(h1s)
        if h1s:
            page["h1_text"] = h1s[0].get_text(strip=True)
        if len(h1s) == 0:
            page["issues"].append("missing_h1")
        elif len(h1s) > 1:
            page["issues"].append("multiple_h1")

        # Canonical
        canon = soup.find("link", rel="canonical")
        if canon:
            page["canonical"] = canon.get("href")
        else:
            page["issues"].append("missing_canonical")

        # Robots meta
        robots = soup.find("meta", attrs={"name": "robots"})
        if robots:
            page["robots_meta"] = robots.get("content", "")

        # Images
        imgs = soup.find_all("img")
        page["images_total"] = len(imgs)
        missing_alt = [img for img in imgs if not img.get("alt", "").strip()]
        page["images_missing_alt"] = len(missing_alt)
        if missing_alt:
            page["issues"].append("missing_alt_text")
            page["images_missing_alt_urls"] = [img.get("src", "") for img in missing_alt[:10]]

        # Title length checks
        if page["meta_title"] and page["meta_title_length"] > 60:
            page["issues"].append("meta_title_too_long")
        if page["meta_title"] and page["meta_title_length"] < 30:
            page["issues"].append("meta_title_too_short")
        if page["meta_description"] and page["meta_description_length"] > 160:
            page["issues"].append("meta_description_too_long")
        if page["meta_description"] and page["meta_description_length"] < 50:
            page["issues"].append("meta_description_too_short")

        # Redirect chain
        if page["redirect_chain"] >= 3:
            page["issues"].append("redirect_chain_too_long")

        # Collect internal links for crawling
        links = []
        for a in soup.find_all("a", href=True):
            normalized = self.normalize(a["href"], url)
            if normalized:
                if self.is_internal(normalized):
                    page["internal_links"] += 1
                    links.append(normalized)
                else:
                    page["external_links"] += 1

        page["_links"] = links
        return page

    def crawl(self, check: str = "all") -> dict:
        print(f"Starting crawl: {self.base_url} (max {self.max_pages} pages)")
        start_time = time.time()

        while self.queue and len(self.pages) < self.max_pages:
            url = self.queue.popleft()
            if url in self.visited:
                continue
            self.visited.add(url)

            status, meta, html = self.fetch(url)
            page = self.parse_page(url, status, meta, html)
            self.pages.append(page)

            if len(self.pages) % 50 == 0:
                print(f"  Crawled {len(self.pages)} pages...")

            # Enqueue discovered internal links
            if check in ("all", "broken-links"):
                for link in page.pop("_links", []):
                    if link not in self.visited:
                        self.queue.append(link)
            else:
                page.pop("_links", None)

            # Rate limit
            time.sleep(0.2)

        elapsed = round(time.time() - start_time, 1)
        print(f"Crawl complete: {len(self.pages)} pages in {elapsed}s")

        # Build issues list
        all_issues = []
        for page in self.pages:
            for issue_type in page.get("issues", []):
                all_issues.append({
                    "url": page["url"],
                    "issue_type": issue_type,
                    "severity": self._severity(issue_type),
                    "details": self._details(issue_type, page),
                })

        # Detect duplicate meta titles
        seen_titles: dict = {}
        for page in self.pages:
            t = page.get("meta_title")
            if t:
                seen_titles.setdefault(t, []).append(page["url"])
        for title, urls in seen_titles.items():
            if len(urls) > 1:
                for url in urls:
                    all_issues.append({
                        "url": url,
                        "issue_type": "duplicate_meta_title",
                        "severity": "high",
                        "details": f"Title shared with {len(urls) - 1} other page(s)",
                    })

        return {
            "base_url": self.base_url,
            "pages_crawled": len(self.pages),
            "crawl_time_seconds": elapsed,
            "pages": self.pages,
            "issues": all_issues,
            "summary": {
                "total_issues": len(all_issues),
                "by_severity": self._count_by_severity(all_issues),
                "broken_links": len([p for p in self.pages if p["status"] >= 400]),
                "missing_meta_title": len([p for p in self.pages if not p.get("meta_title")]),
                "missing_meta_description": len([p for p in self.pages if not p.get("meta_description")]),
                "missing_alt_text": sum(p.get("images_missing_alt", 0) for p in self.pages),
            },
        }

    def _severity(self, issue_type: str) -> str:
        severity_map = {
            "missing_meta_title": "high",
            "missing_meta_description": "high",
            "duplicate_meta_title": "high",
            "missing_h1": "medium",
            "multiple_h1": "medium",
            "missing_alt_text": "medium",
            "redirect_chain_too_long": "medium",
            "missing_canonical": "medium",
            "meta_title_too_long": "low",
            "meta_title_too_short": "low",
            "meta_description_too_long": "low",
            "meta_description_too_short": "low",
        }
        return severity_map.get(issue_type, "low")

    def _details(self, issue_type: str, page: dict) -> str:
        if issue_type == "meta_title_too_long":
            return f"Length: {page.get('meta_title_length')} chars (max 60)"
        if issue_type == "meta_description_too_long":
            return f"Length: {page.get('meta_description_length')} chars (max 160)"
        if issue_type == "missing_alt_text":
            return f"{page.get('images_missing_alt', 0)} image(s) missing alt text"
        if issue_type == "redirect_chain_too_long":
            return f"Chain length: {page.get('redirect_chain', 0)}"
        return ""

    def _count_by_severity(self, issues: list[dict]) -> dict:
        counts: dict = {}
        for issue in issues:
            sev = issue.get("severity", "low")
            counts[sev] = counts.get(sev, 0) + 1
        return counts


def main():
    parser = argparse.ArgumentParser(description="SEO Site Crawler")
    parser.add_argument("--url", required=True)
    parser.add_argument("--max-pages", type=int, default=500)
    parser.add_argument("--timeout", type=int, default=15)
    parser.add_argument("--check", default="all",
        choices=["all", "broken-links", "meta-tags", "image-alt"])
    parser.add_argument("--output", required=True)
    parser.add_argument("--save-to-db", action="store_true")
    args = parser.parse_args()

    crawler = SiteCrawler(args.url, max_pages=args.max_pages, timeout=args.timeout)
    result = crawler.crawl(check=args.check)

    with open(args.output, "w") as f:
        json.dump(result, f, indent=2)
    print(f"Output saved: {args.output}")

    # Print summary
    s = result["summary"]
    print(f"\nSummary:")
    print(f"  Pages: {result['pages_crawled']}")
    print(f"  Issues: {s['total_issues']}")
    print(f"  Broken links: {s['broken_links']}")
    print(f"  Missing meta title: {s['missing_meta_title']}")
    print(f"  Missing meta desc: {s['missing_meta_description']}")
    print(f"  Missing alt text (images): {s['missing_alt_text']}")


if __name__ == "__main__":
    main()
