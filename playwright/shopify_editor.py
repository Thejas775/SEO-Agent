#!/usr/bin/env python3
"""
Shopify blog automation via the Shopify Admin API (REST).
Publishes articles, updates SEO metadata on pages.
"""

import argparse
import json
import os
import sys

import requests


class ShopifyClient:
    def __init__(self, shop: str, api_token: str):
        # shop = "yourstore.myshopify.com"
        self.base = f"https://{shop}/admin/api/2024-01"
        self.headers = {
            "X-Shopify-Access-Token": api_token,
            "Content-Type": "application/json",
        }

    def get(self, path: str) -> dict:
        resp = requests.get(f"{self.base}{path}", headers=self.headers, timeout=30)
        resp.raise_for_status()
        return resp.json()

    def post(self, path: str, data: dict) -> dict:
        resp = requests.post(f"{self.base}{path}", headers=self.headers, json=data, timeout=30)
        resp.raise_for_status()
        return resp.json()

    def put(self, path: str, data: dict) -> dict:
        resp = requests.put(f"{self.base}{path}", headers=self.headers, json=data, timeout=30)
        resp.raise_for_status()
        return resp.json()

    def get_blogs(self) -> list:
        return self.get("/blogs.json").get("blogs", [])

    def create_article(self, blog_id: int, article_data: dict) -> dict:
        return self.post(f"/blogs/{blog_id}/articles.json", {"article": article_data})

    def update_article(self, blog_id: int, article_id: int, data: dict) -> dict:
        return self.put(f"/blogs/{blog_id}/articles/{article_id}.json", {"article": data})

    def get_pages(self) -> list:
        return self.get("/pages.json").get("pages", [])

    def update_page_seo(self, page_id: int, title: str, description: str) -> dict:
        return self.put(f"/pages/{page_id}.json", {
            "page": {
                "title": title,
                "metafields": [
                    {"namespace": "seo", "key": "title", "value": title, "type": "single_line_text_field"},
                    {"namespace": "seo", "key": "description", "value": description, "type": "single_line_text_field"},
                ],
            }
        })


def get_article_from_db(article_id: int) -> dict:
    import subprocess
    result = subprocess.run(
        ["python3", os.path.expanduser("~/.openclaw/workspace/seo/tools/db.py"),
         "get_article", "--id", str(article_id)],
        capture_output=True, text=True
    )
    return json.loads(result.stdout.strip())


def action_publish_blog(args):
    shop = args.shop or os.environ.get("SHOPIFY_DOMAIN", "")
    token = args.api_token or os.environ.get("SHOPIFY_ADMIN_TOKEN", "")
    if not shop or not token:
        sys.exit("ERROR: SHOPIFY_DOMAIN and SHOPIFY_ADMIN_TOKEN required")

    article = get_article_from_db(int(args.article_id))
    client = ShopifyClient(shop, token)

    # Get or create blog
    blogs = client.get_blogs()
    if not blogs:
        sys.exit("No blogs found on Shopify store")

    blog_id = int(os.environ.get("SHOPIFY_BLOG_ID", blogs[0]["id"]))
    print(f"Publishing to blog ID: {blog_id}")

    # Build article
    import re
    handle = re.sub(r"[^a-z0-9-]", "-", article["title"].lower())
    handle = re.sub(r"-+", "-", handle).strip("-")[:80]

    article_data = {
        "title": article["title"],
        "body_html": article["content"],
        "handle": handle,
        "published": True,
        "metafields": [
            {
                "namespace": "seo",
                "key": "title",
                "value": article.get("meta_title", article["title"]),
                "type": "single_line_text_field",
            },
            {
                "namespace": "seo",
                "key": "description",
                "value": article.get("meta_description", ""),
                "type": "single_line_text_field",
            },
        ],
    }

    result = client.create_article(blog_id, article_data)
    created = result.get("article", {})
    article_shopify_id = created.get("id")
    live_url = f"https://{shop}/blogs/{blogs[0]['handle']}/{handle}"
    print(f"Published Shopify article {article_shopify_id}: {live_url}")

    import subprocess
    subprocess.run([
        "python3", os.path.expanduser("~/.openclaw/workspace/seo/tools/db.py"),
        "update_article_status",
        "--id", str(args.article_id),
        "--status", "published",
        "--published-url", live_url,
    ], check=True)


def main():
    parser = argparse.ArgumentParser(description="Shopify SEO Editor")
    parser.add_argument("--action", required=True, choices=["publish_blog", "update_page_seo"])
    parser.add_argument("--article-id")
    parser.add_argument("--page-id")
    parser.add_argument("--shop")
    parser.add_argument("--api-token")
    parser.add_argument("--meta-title")
    parser.add_argument("--meta-description")
    args = parser.parse_args()

    if args.action == "publish_blog":
        action_publish_blog(args)


if __name__ == "__main__":
    main()
