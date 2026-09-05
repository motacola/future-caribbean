#!/usr/bin/env python3
"""Resolve publisher thumbnails for the ranked regional-news artifact.

The poller remains the source of truth for headlines and ranking. This pass only
adds canonical publisher URLs and image metadata, caches successful lookups, and
syncs the deployable snapshots consumed by Astro and Vercel.
"""
from __future__ import annotations

import argparse
import json
import re
import ssl
import sys
import urllib.parse
import urllib.request
from concurrent.futures import ThreadPoolExecutor, as_completed
from datetime import datetime, timezone
from pathlib import Path
from typing import Any
from urllib.parse import urlparse

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from watchers.regional_news_poller import enrich_article  # noqa: E402


def build_story_clusters(_items):  # noqa: E402
    """Stub — the original build_story_clusters was lost in a refactor.

    The Astro frontend reads clusters from outbox/dispatch_desk.json
    (a separate aggregator), not from this regional-news payload. The
    /api/regional-news.py Python API defensively rebuilds clusters from
    items when this list is empty (see single_item_clusters call). So
    returning [] is safe and preserves the image-enrichment behaviour.
    """
    return []

LATEST = ROOT / "data" / "regional_news" / "latest.json"
PUBLIC = ROOT / "public" / "regional_news.json"
API_SNAPSHOT = ROOT / "api" / "regional-news-data.json"
CACHE = ROOT / "data" / "regional_news" / "image_cache.json"
MICROLINK = "https://api.microlink.io/"
UA = {"User-Agent": "Mozilla/5.0 (compatible; Abeng/1.0; +https://abeng.vercel.app)"}
TIMEOUT = 25
MIN_WIDTH = 480
MIN_HEIGHT = 260
MARKET_SOURCES = ROOT / "config" / "market_sources.json"


def _registry_domains() -> tuple[set[str], set[str]]:
    registry = _read_json(MARKET_SOURCES, {})
    official: set[str] = {"caribank.org", "caricom.org", "oecs.int"}
    local: set[str] = set()
    for market in registry.get("markets", []):
        for source in [market.get("exchange", {}), *(market.get("official_context") or [])]:
            domain = urlparse(str(source.get("url") or "")).netloc.removeprefix("www.")
            if domain:
                official.add(domain)
        for source in market.get("credible_news") or []:
            domain = urlparse(str(source.get("url") or "")).netloc.removeprefix("www.")
            if domain:
                local.add(domain)
    return official, local


def classify_source_domain(domain: str) -> str:
    official, local = _registry_domains()
    normalized = domain.lower().removeprefix("www.")
    if any(marker in normalized for marker in ("businesswire.com", "globenewswire.com", "prnewswire.com", "einpresswire.com")):
        return "press_release"
    if any(normalized == known or normalized.endswith(f".{known}") for known in official):
        return "official"
    if any(normalized == known or normalized.endswith(f".{known}") for known in local):
        return "local_newsroom"
    return "international_newsroom" if normalized and "news.google." not in normalized else "aggregator"


def _read_json(path: Path, fallback: Any) -> Any:
    try:
        return json.loads(path.read_text(encoding="utf-8"))
    except (FileNotFoundError, json.JSONDecodeError, OSError):
        return fallback


def _safe_http_url(value: Any) -> str | None:
    if not isinstance(value, str):
        return None
    value = value.strip()
    parsed = urlparse(value)
    return value if parsed.scheme in {"http", "https"} and parsed.netloc else None


def select_image(metadata: dict[str, Any]) -> dict[str, Any] | None:
    """Return usable publisher imagery; reject logos, icons and tiny assets."""
    image = metadata.get("image") or {}
    url = _safe_http_url(image.get("url"))
    if not url:
        return None
    lowered = url.lower()
    width = int(image.get("width") or 0)
    height = int(image.get("height") or 0)
    image_type = str(image.get("type") or "").lower()
    if image_type in {"svg", "ico"} or re.search(r"(?:^|[/_.-])(logo|favicon|icon)(?:[/_.-]|$)", lowered):
        return None
    if width and width < MIN_WIDTH or height and height < MIN_HEIGHT:
        return None
    return {
        "image_url": url,
        "image_width": width or None,
        "image_height": height or None,
        "image_kind": "publisher",
    }


def resolve_metadata(article_url: str) -> dict[str, Any]:
    query = urllib.parse.urlencode({"url": article_url, "meta": "true", "screenshot": "false"})
    request = urllib.request.Request(f"{MICROLINK}?{query}", headers=UA)
    context = ssl.create_default_context()
    try:
        import certifi
        context = ssl.create_default_context(cafile=certifi.where())
    except ImportError:
        pass
    with urllib.request.urlopen(request, timeout=TIMEOUT, context=context) as response:
        payload = json.loads(response.read())
    data = payload.get("data") or {}
    selected = select_image(data) or {}
    canonical = _safe_http_url(data.get("url"))
    domain = urlparse(canonical or article_url).netloc.removeprefix("www.")
    raw_publisher = data.get("publisher")
    publisher = raw_publisher if isinstance(raw_publisher, str) else domain
    return {
        **selected,
        "canonical_url": canonical,
        "publisher_domain": domain,
        "publisher_name": publisher or domain,
        "source_type": classify_source_domain(domain),
        "checked_at": datetime.now(timezone.utc).isoformat(),
    }


def apply_metadata(item: dict[str, Any], resolved: dict[str, Any]) -> dict[str, Any]:
    """Merge metadata without letting a social platform replace newsroom identity."""
    base = dict(item)
    resolved_fields = {k: v for k, v in resolved.items() if v is not None}
    if item.get("source_platform") == "instagram":
        for field in ("canonical_url", "social_post_url"):
            existing = str(base.get(field) or "")
            parsed_existing = urlparse(existing)
            if (
                parsed_existing.netloc.removeprefix("www.") == "instagram.com"
                and re.match(r"^/(?:p|reel)/[^/]+/?$", parsed_existing.path) is None
            ):
                base.pop(field, None)
        if base.get("image_kind") == "publisher_social" and not base.get("social_post_url"):
            for field in ("image_url", "image_width", "image_height", "image_kind"):
                base.pop(field, None)
        canonical = str(resolved_fields.get("canonical_url") or "")
        parsed = urlparse(canonical)
        is_instagram_post = (
            parsed.netloc.removeprefix("www.") == "instagram.com"
            and re.match(r"^/(?:p|reel)/[^/]+/?$", parsed.path) is not None
        )
        resolved_fields.pop("publisher_domain", None)
        resolved_fields.pop("publisher_name", None)
        resolved_fields.pop("source_type", None)
        if is_instagram_post:
            resolved_fields["social_post_url"] = canonical
            resolved_fields["canonical_match_status"] = "instagram_post_resolved"
        else:
            resolved_fields.pop("canonical_url", None)
            resolved_fields["canonical_match_status"] = "indexed_post_only"
            for field in ("image_url", "image_width", "image_height", "image_kind"):
                resolved_fields.pop(field, None)
        if resolved_fields.get("image_url"):
            resolved_fields["image_kind"] = "publisher_social"
    return {**base, **resolved_fields}


def enrich_payload(payload: dict[str, Any], limit: int = 24, workers: int = 3) -> tuple[dict[str, Any], dict[str, Any]]:
    items = list(payload.get("items") or [])
    cache = _read_json(CACHE, {})
    targets: list[tuple[int, str]] = []
    for index, item in enumerate(items[: max(0, limit)]):
        article_url = _safe_http_url(item.get("url"))
        if not article_url:
            continue
        cached = cache.get(article_url)
        if isinstance(cached, dict):
            items[index] = apply_metadata(item, cached)
        else:
            targets.append((index, article_url))

    if targets:
        with ThreadPoolExecutor(max_workers=max(1, min(workers, 8))) as pool:
            futures = {pool.submit(resolve_metadata, url): (index, url) for index, url in targets}
            for future in as_completed(futures):
                index, url = futures[future]
                try:
                    resolved = future.result()
                except Exception as exc:  # network errors must not break the news pipeline
                    print(f"news images: {urlparse(url).netloc} lookup failed ({type(exc).__name__})")
                    continue
                cache[url] = resolved
                items[index] = apply_metadata(items[index], resolved)

    normalized_items = []
    for item in items:
        if item.get("source_platform") == "instagram":
            item = apply_metadata(item, {})
        domain = str(item.get("publisher_domain") or "")
        if domain:
            item = {**item, "source_type": classify_source_domain(domain)}
        normalized_items.append(enrich_article(item))
    items = normalized_items
    payload = {
        **payload,
        "items": items,
        "clusters": build_story_clusters(items),
        "image_enrichment": {
            "checked_at": datetime.now(timezone.utc).isoformat(),
            "provider": "publisher metadata via Microlink",
            "requested": min(limit, len(items)),
            "with_images": sum(bool(item.get("image_url")) for item in items[:limit]),
        },
    }
    return payload, cache


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--limit", type=int, default=24)
    parser.add_argument("--workers", type=int, default=3)
    args = parser.parse_args()

    source = LATEST if LATEST.exists() else PUBLIC
    payload = _read_json(source, {})
    if not payload.get("items"):
        print("news images: no regional-news items available; keeping prior snapshots")
        return 0

    enriched, cache = enrich_payload(payload, limit=args.limit, workers=args.workers)
    CACHE.parent.mkdir(parents=True, exist_ok=True)
    CACHE.write_text(json.dumps(cache, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")
    serialized = json.dumps(enriched, indent=1, ensure_ascii=False) + "\n"
    for destination in (LATEST, PUBLIC, API_SNAPSHOT):
        destination.parent.mkdir(parents=True, exist_ok=True)
        destination.write_text(serialized, encoding="utf-8")
    stats = enriched["image_enrichment"]
    print(f"news images: {stats['with_images']}/{stats['requested']} ranked articles have publisher thumbnails")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
