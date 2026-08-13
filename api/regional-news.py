"""Vercel serverless function: ranked regional news with country/topic filters."""
import json
import re
from collections import Counter
from datetime import datetime, timezone
from email.utils import parsedate_to_datetime
from http.server import BaseHTTPRequestHandler
from pathlib import Path
from urllib.parse import parse_qs, urlparse

ROOT = Path(__file__).resolve().parents[1]


def _published_datetime(value):
    if not value:
        return None
    try:
        parsed = parsedate_to_datetime(value)
    except (TypeError, ValueError):
        try:
            parsed = datetime.fromisoformat(str(value).replace("Z", "+00:00"))
        except ValueError:
            return None
    return (parsed.replace(tzinfo=timezone.utc) if parsed.tzinfo is None else parsed).astimezone(timezone.utc)


def _refresh_freshness(item, now=None):
    now = now or datetime.now(timezone.utc)
    published = _published_datetime(item.get("published") or item.get("last_updated"))
    if not published:
        return {**item, "age_hours": None, "freshness_state": "unknown"}
    age_hours = max(0, int((now - published).total_seconds() // 3600))
    state = "breaking" if age_hours < 6 else "fresh" if age_hours <= 24 else "recent" if age_hours <= 72 else "background" if age_hours <= 720 else "archive"
    return {**item, "age_hours": age_hours, "freshness_state": state}


def ranked_articles(items, country=None, topic=None, limit=30, freshness=None, source_type=None, direct_only=False, platform=None):
    """Filter the already-enriched committed feed without runtime pipeline imports."""
    filtered = [_refresh_freshness(item) for item in items]
    if country:
        filtered = [item for item in filtered if country in item.get("countries", [])]
    if topic:
        filtered = [item for item in filtered if topic in item.get("topics", [])]
    if freshness:
        filtered = [item for item in filtered if item.get("freshness_state") == freshness]
    if source_type:
        filtered = [item for item in filtered if item.get("source_type") == source_type]
    if platform:
        filtered = [item for item in filtered if item.get("source_platform") == platform]
    if direct_only:
        filtered = [item for item in filtered if item.get("direct_country_coverage")]
    deduped = {}
    for item in filtered:
        key = re.sub(r"[^a-z0-9]+", " ", item.get("title", "").lower()).strip()
        if key and (key not in deduped or item.get("relevance_score", 0) > deduped[key].get("relevance_score", 0)):
            deduped[key] = item
    ordered = sorted(
        deduped.values(),
        key=lambda item: (item.get("relevance_score", 0), item.get("published") or ""),
        reverse=True,
    )
    selected, publishers, countries = [], Counter(), Counter()
    for item in ordered:
        publisher = item.get("publisher_name") or item.get("publisher_domain") or item.get("source") or "unknown"
        primary_country = item.get("primary_country") or "regional"
        if publishers[publisher] >= 2 or countries[primary_country] >= 3:
            continue
        selected.append(item)
        publishers[publisher] += 1
        countries[primary_country] += 1
        if len(selected) >= limit:
            break
    return selected


def payload_health(payload, items):
    health = dict(payload.get("health") or {})
    fetched = _published_datetime(payload.get("fetched_at"))
    snapshot_age = max(0, int((datetime.now(timezone.utc) - fetched).total_seconds() // 3600)) if fetched else None
    health.update({
        "snapshot_age_hours": snapshot_age,
        "fresh_items": sum(item.get("freshness_state") in {"breaking", "fresh", "recent"} for item in items),
        "stale": snapshot_age is None or snapshot_age > 8,
    })
    return health


def single_item_clusters(items, platform):
    """Expose filtered discovery items even when they were below the main cluster shelf."""
    clusters = []
    for index, item in enumerate(items):
        article_url = item.get("canonical_url") or item.get("social_post_url") or item.get("url")
        clusters.append({
            "cluster_id": f"{platform or 'news'}-{item.get('id') or index}",
            "title": item.get("title") or "Newsroom discovery",
            "primary_country": item.get("primary_country"),
            "affected_markets": item.get("countries", []),
            "topics": item.get("topics", []),
            "freshness_state": item.get("freshness_state"),
            "age_hours": item.get("age_hours"),
            "source_count": 1,
            "publisher_count": 1,
            "source_platform": platform,
            "articles": [item],
            "citations": [{
                "publisher": item.get("publisher_name") or item.get("publisher_domain"),
                "url": article_url,
                "source_type": item.get("source_type"),
                "source_platform": item.get("source_platform"),
            }],
        })
    return clusters


class handler(BaseHTTPRequestHandler):
    def do_OPTIONS(self):
        self.send_response(200)
        self.send_header("Access-Control-Allow-Origin", "*")
        self.send_header("Access-Control-Allow-Methods", "GET, OPTIONS")
        self.end_headers()

    def do_GET(self):
        query = parse_qs(urlparse(self.path).query)
        sources = (
            Path(__file__).with_name("regional-news-data.json"),
            ROOT / "public" / "regional_news.json",
            ROOT / "data" / "regional_news" / "latest.json",
        )
        source = next((candidate for candidate in sources if candidate.exists()), None)
        try:
            payload = json.loads(source.read_text(encoding="utf-8")) if source else {"items": []}
            limit = max(1, min(100, int(query.get("limit", [30])[0])))
            items = ranked_articles(
                payload.get("items", []),
                query.get("country", [None])[0],
                query.get("topic", [None])[0],
                limit,
                query.get("freshness", [None])[0],
                query.get("source_type", [None])[0],
                query.get("direct", ["false"])[0].lower() in {"1", "true", "yes"},
                query.get("platform", [None])[0],
            )
            clusters = [_refresh_freshness(cluster) for cluster in payload.get("clusters", [])]
            country = query.get("country", [None])[0]
            topic = query.get("topic", [None])[0]
            platform = query.get("platform", [None])[0]
            if country:
                clusters = [cluster for cluster in clusters if country in cluster.get("affected_markets", [])]
            if topic:
                clusters = [cluster for cluster in clusters if topic in cluster.get("topics", [])]
            if platform:
                clusters = [cluster for cluster in clusters if any(article.get("source_platform") == platform for article in cluster.get("articles", []))]
                if not clusters and items:
                    clusters = single_item_clusters(items, platform)
            body = json.dumps({
                "ok": True,
                "fetched_at": payload.get("fetched_at"),
                "count": len(items),
                "cluster_count": len(clusters),
                "health": payload_health(payload, items),
                "social_discovery": payload.get("social_discovery", {}),
                "items": items,
                "clusters": clusters[:limit],
            }, ensure_ascii=False).encode()
            self.send_response(200)
        except Exception as exc:
            body = json.dumps({"ok": False, "error": str(exc)}).encode()
            self.send_response(500)
        self.send_header("Content-Type", "application/json")
        self.send_header("Content-Length", str(len(body)))
        self.send_header("Access-Control-Allow-Origin", "*")
        self.end_headers()
        self.wfile.write(body)
