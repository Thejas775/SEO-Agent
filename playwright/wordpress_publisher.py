#!/usr/bin/env python3
"""
WordPress CMS automation via Playwright.
Handles: publish new post, update meta title/description,
add internal links to existing posts.
"""

import argparse
import json
import os
import sys
from datetime import date
from pathlib import Path

from playwright.sync_api import sync_playwright, TimeoutError as PWTimeout

SCREENSHOT_DIR = Path(os.path.expanduser("~/.openclaw/workspace/seo/screenshots"))


def screenshot_path(action: str, target: str, stage: str) -> str:
    day_dir = SCREENSHOT_DIR / str(date.today())
    day_dir.mkdir(parents=True, exist_ok=True)
    safe = target.replace("/", "_").replace(":", "").strip("_")[:40]
    return str(day_dir / f"{action}_{safe}_{stage}.png")


def get_article_from_db(article_id: int) -> dict:
    import subprocess
    result = subprocess.run(
        ["python3", os.path.expanduser("~/.openclaw/workspace/seo/tools/db.py"),
         "get_article", "--id", str(article_id)],
        capture_output=True, text=True
    )
    data = json.loads(result.stdout.strip())
    if not data:
        sys.exit(f"Article {article_id} not found in database")
    return data


def wp_login(page, cms_url: str, username: str, password: str):
    login_url = cms_url.rstrip("/") + "/wp-login.php"
    page.goto(login_url, wait_until="networkidle", timeout=30000)

    for attempt in range(3):
        try:
            page.fill("#user_login", username)
            page.fill("#user_pass", password)
            page.click("#wp-submit")
            page.wait_for_url("**/wp-admin/**", timeout=15000)
            return
        except PWTimeout:
            if attempt == 2:
                raise RuntimeError(f"WordPress login failed after 3 attempts at {login_url}")


def wp_publish_post(page, cms_url: str, article: dict) -> str:
    """Publish a new post via WordPress REST API (faster than Gutenberg UI)."""
    import requests

    wp_api = cms_url.rstrip("/") + "/wp-json/wp/v2/posts"
    auth = (os.environ["CMS_USERNAME"], os.environ["CMS_PASSWORD"])

    # Build post data
    post_data = {
        "title": article["title"],
        "content": article["content"],
        "status": "publish",
        "meta": {
            "_yoast_wpseo_title": article.get("meta_title", ""),
            "_yoast_wpseo_metadesc": article.get("meta_description", ""),
        },
    }

    # Add schema to head if present
    if article.get("schema_markup"):
        schema = article["schema_markup"]
        if isinstance(schema, str):
            schema = json.loads(schema)
        post_data["content"] += f'\n\n<script type="application/ld+json">{json.dumps(schema)}</script>'

    resp = requests.post(wp_api, json=post_data, auth=auth, timeout=30)
    resp.raise_for_status()
    post = resp.json()
    return post.get("link", "")


def wp_update_meta(page, cms_url: str, post_id: int,
                   meta_title: str, meta_description: str):
    """Update meta title/description via WP REST API."""
    import requests

    wp_api = cms_url.rstrip("/") + f"/wp-json/wp/v2/posts/{post_id}"
    auth = (os.environ["CMS_USERNAME"], os.environ["CMS_PASSWORD"])

    data = {
        "meta": {
            "_yoast_wpseo_title": meta_title,
            "_yoast_wpseo_metadesc": meta_description,
        }
    }
    resp = requests.post(wp_api, json=data, auth=auth, timeout=30)
    resp.raise_for_status()
    print(f"Meta updated for post {post_id}")


def verify_live_url(url: str) -> bool:
    import requests
    try:
        resp = requests.get(url, timeout=15, allow_redirects=True)
        return resp.status_code == 200
    except Exception:
        return False


def action_publish(args):
    article = get_article_from_db(int(args.article_id))

    # Pre-publish checks
    if len((article.get("content") or "").split()) < 100:
        sys.exit(f"Article {args.article_id} content too short (< 100 words), aborting")
    if article.get("status") == "published":
        sys.exit(f"Article {args.article_id} already published at {article.get('published_url')}")

    cms_url = args.cms_url or os.environ.get("CMS_URL", "")
    username = args.username or os.environ.get("CMS_USERNAME", "")
    password = args.password or os.environ.get("CMS_PASSWORD", "")

    with sync_playwright() as pw:
        browser = pw.chromium.launch(headless=not args.headed)
        page = browser.new_page()

        try:
            # Login
            wp_login(page, cms_url, username, password)
            print("WordPress login successful")

            # Take before screenshot
            page.screenshot(path=screenshot_path("publish", article["title"], "before"))

            # Publish via REST API
            live_url = wp_publish_post(page, cms_url, article)
            print(f"Published: {live_url}")

            # Verify live
            if not verify_live_url(live_url):
                print(f"WARNING: URL {live_url} did not return 200 — check manually")
            else:
                print(f"Verified live: {live_url}")

            # Take after screenshot
            page.goto(live_url, timeout=30000)
            page.screenshot(path=screenshot_path("publish", article["title"], "after"))

        finally:
            browser.close()

    # Update DB
    import subprocess
    subprocess.run([
        "python3", os.path.expanduser("~/.openclaw/workspace/seo/tools/db.py"),
        "update_article_status",
        "--id", str(args.article_id),
        "--status", "published",
        "--published-url", live_url,
    ], check=True)
    print(f"Article {args.article_id} marked as published in database")


def action_update_meta(args):
    cms_url = args.cms_url or os.environ.get("CMS_URL", "")
    post_id = int(args.post_id)

    with sync_playwright() as pw:
        browser = pw.chromium.launch(headless=not args.headed)
        page = browser.new_page()

        try:
            username = args.username or os.environ.get("CMS_USERNAME", "")
            password = args.password or os.environ.get("CMS_PASSWORD", "")
            wp_login(page, cms_url, username, password)

            # Before screenshot
            page.goto(f"{cms_url}/wp-admin/post.php?post={post_id}&action=edit", timeout=30000)
            page.screenshot(path=screenshot_path("update_meta", str(post_id), "before"))

            wp_update_meta(page, cms_url, post_id, args.meta_title, args.meta_description)

            # After screenshot
            page.screenshot(path=screenshot_path("update_meta", str(post_id), "after"))

        finally:
            browser.close()


def main():
    parser = argparse.ArgumentParser(description="WordPress Playwright Publisher")
    parser.add_argument("--action", required=True, choices=["publish", "update_meta"])
    parser.add_argument("--article-id")
    parser.add_argument("--post-id")
    parser.add_argument("--cms-url")
    parser.add_argument("--username")
    parser.add_argument("--password")
    parser.add_argument("--meta-title")
    parser.add_argument("--meta-description")
    parser.add_argument("--headed", action="store_true")
    args = parser.parse_args()

    if args.action == "publish":
        if not args.article_id:
            sys.exit("--article-id required for publish action")
        action_publish(args)
    elif args.action == "update_meta":
        if not args.post_id:
            sys.exit("--post-id required for update_meta action")
        action_update_meta(args)


if __name__ == "__main__":
    main()
