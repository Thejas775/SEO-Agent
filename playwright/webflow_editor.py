#!/usr/bin/env python3
"""
Webflow CMS automation via the Webflow REST API.
Uses the API (not browser automation) for reliability.
Falls back to Playwright for UI operations not available in the API.
"""

import argparse
import json
import os
import sys

import requests


class WebflowClient:
    BASE = "https://api.webflow.com/v2"

    def __init__(self, api_token: str):
        self.headers = {
            "Authorization": f"Bearer {api_token}",
            "Content-Type": "application/json",
            "accept": "application/json",
        }

    def get(self, path: str) -> dict:
        resp = requests.get(f"{self.BASE}{path}", headers=self.headers, timeout=30)
        resp.raise_for_status()
        return resp.json()

    def post(self, path: str, data: dict) -> dict:
        resp = requests.post(f"{self.BASE}{path}", headers=self.headers, json=data, timeout=30)
        resp.raise_for_status()
        return resp.json()

    def patch(self, path: str, data: dict) -> dict:
        resp = requests.patch(f"{self.BASE}{path}", headers=self.headers, json=data, timeout=30)
        resp.raise_for_status()
        return resp.json()

    def get_sites(self) -> list:
        return self.get("/sites").get("sites", [])

    def get_collections(self, site_id: str) -> list:
        return self.get(f"/sites/{site_id}/collections").get("collections", [])

    def create_item(self, collection_id: str, fields: dict, publish: bool = True) -> dict:
        payload = {
            "fieldData": fields,
            "isDraft": not publish,
            "isArchived": False,
        }
        return self.post(f"/collections/{collection_id}/items", payload)

    def update_item(self, collection_id: str, item_id: str, fields: dict) -> dict:
        return self.patch(f"/collections/{collection_id}/items/{item_id}", {"fieldData": fields})

    def publish_items(self, collection_id: str, item_ids: list[str]) -> dict:
        return self.post(f"/collections/{collection_id}/items/publish", {"itemIds": item_ids})


def get_article_from_db(article_id: int) -> dict:
    import subprocess
    result = subprocess.run(
        ["python3", os.path.expanduser("~/.openclaw/workspace/seo/tools/db.py"),
         "get_article", "--id", str(article_id)],
        capture_output=True, text=True
    )
    return json.loads(result.stdout.strip())


def action_publish(args):
    api_token = args.api_token or os.environ.get("WEBFLOW_API_TOKEN", "")
    if not api_token:
        sys.exit("ERROR: WEBFLOW_API_TOKEN required")

    article = get_article_from_db(int(args.article_id))
    client = WebflowClient(api_token)

    # Resolve site and collection
    sites = client.get_sites()
    if not sites:
        sys.exit("No Webflow sites found for this token")

    site_id = os.environ.get("WEBFLOW_SITE_ID") or sites[0]["id"]
    collections = client.get_collections(site_id)

    # Find blog collection (usually named "Blog Posts" or "Articles")
    blog_collection = None
    for col in collections:
        if any(name in col.get("displayName", "").lower()
               for name in ["blog", "article", "post", "news"]):
            blog_collection = col
            break

    if not blog_collection:
        sys.exit(f"Could not find blog collection. Available: {[c['displayName'] for c in collections]}")

    collection_id = blog_collection["id"]
    print(f"Using collection: {blog_collection['displayName']} ({collection_id})")

    # Build slug from title
    import re
    slug = re.sub(r"[^a-z0-9-]", "-", article["title"].lower())
    slug = re.sub(r"-+", "-", slug).strip("-")[:80]

    fields = {
        "name": article["title"],
        "slug": slug,
        "post-body": article["content"],
        "post-summary": article.get("meta_description", ""),
        "seo-title": article.get("meta_title", article["title"]),
        "seo-description": article.get("meta_description", ""),
    }

    # Create and publish
    created = client.create_item(collection_id, fields, publish=False)
    item_id = created.get("id")
    print(f"Item created: {item_id}")

    client.publish_items(collection_id, [item_id])
    live_url = f"https://{sites[0].get('shortName', '')}.webflow.io/{slug}"
    print(f"Published: {live_url}")

    # Update DB
    import subprocess
    subprocess.run([
        "python3", os.path.expanduser("~/.openclaw/workspace/seo/tools/db.py"),
        "update_article_status",
        "--id", str(args.article_id),
        "--status", "published",
        "--published-url", live_url,
    ], check=True)


def action_update_seo(args):
    api_token = args.api_token or os.environ.get("WEBFLOW_API_TOKEN", "")
    client = WebflowClient(api_token)

    fields = {}
    if args.meta_title:
        fields["seo-title"] = args.meta_title
    if args.meta_description:
        fields["seo-description"] = args.meta_description

    if not fields:
        sys.exit("No fields to update")

    result = client.update_item(args.collection_id, args.item_id, fields)
    print(f"Updated Webflow item {args.item_id}: {result.get('id')}")


def main():
    parser = argparse.ArgumentParser(description="Webflow API Editor")
    parser.add_argument("--action", required=True, choices=["publish", "update_seo"])
    parser.add_argument("--article-id")
    parser.add_argument("--collection-id")
    parser.add_argument("--item-id")
    parser.add_argument("--api-token")
    parser.add_argument("--cms-url")
    parser.add_argument("--meta-title")
    parser.add_argument("--meta-description")
    args = parser.parse_args()

    if args.action == "publish":
        action_publish(args)
    elif args.action == "update_seo":
        action_update_seo(args)


if __name__ == "__main__":
    main()
