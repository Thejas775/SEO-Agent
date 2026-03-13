#!/usr/bin/env python3
"""
Keyword clustering using TF-IDF + k-means.
Groups semantically related keywords by search intent.
"""

import argparse
import json
import re
import sys

import numpy as np
from sklearn.cluster import KMeans
from sklearn.feature_extraction.text import TfidfVectorizer
from sklearn.metrics import silhouette_score


INTENT_SIGNALS = {
    "informational": ["how", "what", "why", "when", "who", "guide", "tutorial",
                      "learn", "understand", "explain", "tips", "best", "top"],
    "commercial": ["best", "top", "review", "vs", "compare", "alternatives",
                   "pros", "cons", "worth", "recommend"],
    "transactional": ["buy", "price", "cheap", "deal", "discount", "coupon",
                      "order", "purchase", "shop", "cost", "pricing"],
    "navigational": ["login", "sign in", "account", "dashboard", "official"],
}

CONTENT_TYPE_MAP = {
    "informational": "blog_post",
    "commercial": "comparison_page",
    "transactional": "landing_page",
    "navigational": "homepage",
}


def detect_intent(keyword: str) -> str:
    kw_lower = keyword.lower()
    scores = {intent: 0 for intent in INTENT_SIGNALS}
    for intent, signals in INTENT_SIGNALS.items():
        for signal in signals:
            if re.search(r'\b' + signal + r'\b', kw_lower):
                scores[intent] += 1
    best = max(scores, key=lambda x: scores[x])
    return best if scores[best] > 0 else "informational"


def estimate_word_count(intent: str, volume: int) -> int:
    base = {"informational": 1800, "commercial": 2200, "transactional": 1200, "navigational": 800}
    count = base.get(intent, 1500)
    if volume > 10000:
        count += 500
    return count


def cluster_keywords(keywords: list[dict], n_clusters: int | None = None) -> list[dict]:
    if len(keywords) < 3:
        # Too few to cluster — put all in one cluster
        primary = max(keywords, key=lambda x: x.get("volume") or 0)
        intent = detect_intent(primary["keyword"])
        return [{
            "cluster_id": 0,
            "primary_keyword": primary["keyword"],
            "primary_volume": primary.get("volume", 0),
            "supporting_keywords": [k["keyword"] for k in keywords if k["keyword"] != primary["keyword"]],
            "intent": intent,
            "content_type": CONTENT_TYPE_MAP[intent],
            "target_word_count": estimate_word_count(intent, primary.get("volume", 0)),
            "avg_kd": sum(k.get("kd", 0) or 0 for k in keywords) / max(len(keywords), 1),
            "total_volume": sum(k.get("volume", 0) or 0 for k in keywords),
        }]

    texts = [k["keyword"] for k in keywords]
    vectorizer = TfidfVectorizer(ngram_range=(1, 2), min_df=1, max_features=5000)
    X = vectorizer.fit_transform(texts)

    # Auto-detect optimal k if not provided
    if n_clusters is None:
        best_k = 2
        best_score = -1.0
        max_k = min(20, len(keywords) // 3)
        for k in range(2, max_k + 1):
            km = KMeans(n_clusters=k, random_state=42, n_init=10)
            labels = km.fit_predict(X)
            try:
                score = silhouette_score(X, labels, sample_size=min(1000, len(keywords)))
                if score > best_score:
                    best_score = score
                    best_k = k
            except Exception:
                pass
        n_clusters = best_k

    km = KMeans(n_clusters=n_clusters, random_state=42, n_init=10)
    labels = km.fit_predict(X)

    clusters: dict[int, list[dict]] = {}
    for idx, label in enumerate(labels):
        clusters.setdefault(int(label), []).append(keywords[idx])

    result = []
    for cluster_id, members in clusters.items():
        # Primary keyword = highest volume in cluster
        primary = max(members, key=lambda x: x.get("volume") or 0)
        supporting = [k["keyword"] for k in members if k["keyword"] != primary["keyword"]]
        intent = detect_intent(primary["keyword"])
        total_vol = sum(k.get("volume", 0) or 0 for k in members)
        avg_kd = sum(k.get("kd", 0) or 0 for k in members) / len(members)

        result.append({
            "cluster_id": cluster_id,
            "primary_keyword": primary["keyword"],
            "primary_volume": primary.get("volume", 0),
            "supporting_keywords": supporting[:10],
            "intent": intent,
            "content_type": CONTENT_TYPE_MAP[intent],
            "target_word_count": estimate_word_count(intent, primary.get("volume", 0)),
            "avg_kd": round(avg_kd, 1),
            "total_volume": total_vol,
            "member_count": len(members),
        })

    # Sort by total volume descending
    result.sort(key=lambda x: x["total_volume"], reverse=True)
    return result


def main():
    parser = argparse.ArgumentParser(description="Keyword Clusterer")
    parser.add_argument("--input", required=True, help="JSON file with keyword list")
    parser.add_argument("--output", required=True)
    parser.add_argument("--clusters", type=int, help="Force number of clusters")
    parser.add_argument("--key", default="suggestions",
        help="Key in input JSON that contains the keyword array (default: suggestions)")
    args = parser.parse_args()

    with open(args.input) as f:
        data = json.load(f)

    # Support multiple input formats
    if isinstance(data, list):
        keywords = data
    elif args.key in data:
        keywords = data[args.key]
    elif "keywords" in data:
        keywords = data["keywords"]
    elif "gaps" in data:
        keywords = data["gaps"]
    else:
        sys.exit(f"Cannot find keyword array in input. Keys: {list(data.keys())}")

    if not keywords:
        sys.exit("ERROR: No keywords found in input")

    print(f"Clustering {len(keywords)} keywords...")
    clusters = cluster_keywords(keywords, n_clusters=args.clusters)
    print(f"Created {len(clusters)} clusters")

    output = {
        "total_keywords": len(keywords),
        "total_clusters": len(clusters),
        "clusters": clusters,
    }
    with open(args.output, "w") as f:
        json.dump(output, f, indent=2)
    print(f"Output saved: {args.output}")


if __name__ == "__main__":
    main()
