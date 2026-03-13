#!/usr/bin/env python3
"""
Content calendar generator.
Takes keyword clusters and schedules them into a weekly publishing plan.
"""

import argparse
import json
from datetime import date, timedelta


DAYS = ["Monday", "Tuesday", "Wednesday", "Thursday", "Friday"]


def score_cluster(cluster: dict) -> float:
    """Score a cluster for prioritization. Higher = publish sooner."""
    volume = cluster.get("total_volume", 0) or 0
    kd = cluster.get("avg_kd", 50) or 50
    intent = cluster.get("intent", "informational")

    # Volume weight
    volume_score = min(volume / 10000, 1.0) * 40

    # Difficulty weight (lower is better)
    kd_score = (1 - kd / 100) * 40

    # Intent weight (transactional > commercial > informational > navigational)
    intent_scores = {"transactional": 20, "commercial": 15, "informational": 10, "navigational": 5}
    intent_score = intent_scores.get(intent, 10)

    return volume_score + kd_score + intent_score


def generate_title(cluster: dict) -> str:
    kw = cluster["primary_keyword"]
    intent = cluster.get("intent", "informational")
    content_type = cluster.get("content_type", "blog_post")

    if intent == "informational":
        templates = [
            f"How to {kw.title()}: Complete Guide",
            f"What is {kw.title()}? Everything You Need to Know",
            f"{kw.title()}: The Ultimate Guide",
        ]
    elif intent == "commercial":
        templates = [
            f"Best {kw.title()} in {date.today().year}: Expert Reviews",
            f"Top {kw.title()} Compared: Which One to Choose?",
        ]
    elif intent == "transactional":
        templates = [
            f"{kw.title()} — Find the Best Deal",
            f"Get {kw.title()} at the Best Price",
        ]
    else:
        templates = [f"{kw.title()}"]

    return templates[0]


def build_calendar(clusters: list[dict], weeks: int = 4, articles_per_week: int = 2) -> list[dict]:
    # Score and sort clusters
    scored = sorted(clusters, key=score_cluster, reverse=True)

    today = date.today()
    # Start from next Monday
    days_until_monday = (7 - today.weekday()) % 7 or 7
    start = today + timedelta(days=days_until_monday)

    calendar = []
    cluster_idx = 0

    for week in range(1, weeks + 1):
        week_start = start + timedelta(weeks=week - 1)
        slots = DAYS[:articles_per_week]

        for day_offset, day_name in enumerate(slots):
            if cluster_idx >= len(scored):
                break

            cluster = scored[cluster_idx]
            publish_date = week_start + timedelta(days=day_offset)

            entry = {
                "week": week,
                "day": day_name,
                "publish_date": str(publish_date),
                "cluster_id": cluster.get("cluster_id"),
                "title": generate_title(cluster),
                "primary_keyword": cluster["primary_keyword"],
                "supporting_keywords": cluster.get("supporting_keywords", [])[:5],
                "intent": cluster.get("intent", "informational"),
                "content_type": cluster.get("content_type", "blog_post"),
                "target_word_count": cluster.get("target_word_count", 1500),
                "estimated_volume": cluster.get("total_volume", 0),
                "avg_kd": cluster.get("avg_kd", 50),
                "priority": "high" if week <= 1 else ("medium" if week <= 2 else "low"),
                "status": "planned",
            }
            calendar.append(entry)
            cluster_idx += 1

    return calendar


def main():
    parser = argparse.ArgumentParser(description="Content Calendar Generator")
    parser.add_argument("--clusters", required=True, help="Keyword clusters JSON file")
    parser.add_argument("--weeks", type=int, default=4)
    parser.add_argument("--per-week", type=int, default=2, help="Articles per week")
    parser.add_argument("--output", required=True)
    args = parser.parse_args()

    with open(args.clusters) as f:
        data = json.load(f)

    clusters = data.get("clusters", data) if isinstance(data, dict) else data
    if not clusters:
        print("ERROR: No clusters found")
        return

    print(f"Generating calendar for {len(clusters)} clusters over {args.weeks} weeks ({args.per_week}/week)...")
    calendar = build_calendar(clusters, args.weeks, args.per_week)
    print(f"Generated {len(calendar)} calendar entries")

    output = {
        "generated_date": str(date.today()),
        "weeks": args.weeks,
        "total_articles": len(calendar),
        "entries": calendar,
    }
    with open(args.output, "w") as f:
        json.dump(output, f, indent=2)
    print(f"Output saved: {args.output}")


if __name__ == "__main__":
    main()
