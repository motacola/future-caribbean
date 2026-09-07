"""Regional news RSS poller and deterministic country/finance ranking."""
from __future__ import annotations

import json
import os
import re
import ssl
import urllib.request
import xml.etree.ElementTree as ET
from datetime import datetime, timezone
from email.utils import parsedate_to_datetime
from html import unescape
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parents[1]
CONFIG = ROOT / "config" / "regional_news_sources.json"
OUT = ROOT / "data" / "regional_news" / "latest.json"
RAW = ROOT / "data" / "regional_news" / "raw"
UA = {"User-Agent": "Mozilla/5.0 (compatible; Abeng/1.0)"}
TIMEOUT = 20

# macOS + Homebrew Python environments often ship without a default CA bundle
# (Homebrew python 3.12+ has no system openssl.cafile wired in, and pip certs
# live in certifi). Provide a robust SSL context resolver that prefers, in
# order: explicit env, certifi, well-known Homebrew paths, macOS system certs.
def _ssl_context() -> ssl.SSLContext:
    cafile = os.environ.get("SSL_CERT_FILE")
    candidates: list[str] = []
    if cafile:
        candidates.append(cafile)
    try:
        import certifi  # type: ignore
        candidates.append(certifi.where())
    except ImportError:
        pass
    candidates += [
        "/opt/homebrew/etc/openssl@3/cert.pem",
        "/usr/local/etc/openssl@3/cert.pem",
        "/opt/homebrew/etc/openssl/cert.pem",
        "/usr/local/etc/openssl/cert.pem",
        "/etc/ssl/cert.pem",
        "/private/etc/ssl/cert.pem",
    ]
    for path in candidates:
        if path and Path(path).exists():
            return ssl.create_default_context(cafile=path)
    # Last resort: trust the system defaults (this is what urllib.request
    # does when no context is passed); if the env is broken the poller
    # falls back to its prior behaviour of logging and keeping prior data.
    return ssl.create_default_context()

COUNTRY_NAMES = [
    "Guyana", "Jamaica", "Belize", "Barbados", "Trinidad & Tobago", "Bahamas",
    "Suriname", "Haiti", "Dominican Republic", "Puerto Rico", "Dominica", "Grenada",
    "St Lucia", "St Vincent & the Grenadines", "St Kitts & Nevis", "Antigua & Barbuda",
    "Cayman Islands", "Turks & Caicos", "Montserrat", "Anguilla",
    "British Virgin Islands", "US Virgin Islands", "Cuba",
]
COUNTRY_ALIASES = {
    "trinidad and tobago": "Trinidad & Tobago", "antigua and barbuda": "Antigua & Barbuda",
    "saint lucia": "St Lucia", "st. lucia": "St Lucia",
    "saint kitts and nevis": "St Kitts & Nevis", "st. kitts and nevis": "St Kitts & Nevis",
    "saint vincent and the grenadines": "St Vincent & the Grenadines",
    "st. vincent and the grenadines": "St Vincent & the Grenadines",
    "turks and caicos": "Turks & Caicos", "u.s. virgin islands": "US Virgin Islands",
}
TOPICS = {
    "finance": ("bank", "finance", "currency", "exchange", "credit", "interest rate", "inflation", "investment", "fdi", "fund"),
    "energy": ("oil", "gas", "energy", "renewable", "electricity", "solar"),
    "tourism": ("tourism", "hotel", "visitor", "airlift", "cruise"),
    "trade": ("trade", "export", "import", "port", "shipping", "logistics", "supply chain"),
    "procurement": ("procurement", "tender", "contract", "project", "infrastructure"),
    "climate": ("climate", "storm", "hurricane", "flood", "drought", "weather"),
}
NOISE_TERMS = ("royal caribbean cruises ltd", "second passport", "citizenship by investment guide")


def load_config() -> dict[str, Any]:
    return json.loads(CONFIG.read_text(encoding="utf-8"))


def strip_html(text: str) -> str:
    return re.sub(r"\s+", " ", unescape(re.sub(r"<[^>]+>", " ", text or ""))).strip()


def fetch_feed(url: str) -> str:
    req = urllib.request.Request(url, headers=UA)
    with urllib.request.urlopen(req, timeout=TIMEOUT, context=_ssl_context()) as response:
        return response.read().decode("utf-8", errors="replace")


MEDIA_NS = "{http://search.yahoo.com/mrss/}"
CONTENT_NS = "{http://purl.org/rss/1.0/modules/content/}"

# Feed imagery is routinely a site logo, a share icon, or a 1x1 tracking pixel
# dressed as an article image. None of those belong on a news card.
IMAGE_NOISE = re.compile(
    r"(?:^|[/_.-])(logo|logotype|favicon|icon|avatar|banner|badge|spacer|pixel|blank|placeholder|default)(?:[/_.-]|$)",
    re.I,
)
IMAGE_EXT_REJECT = (".svg", ".ico", ".gif")


def _usable_image(url: str, width: str | int | None = None, height: str | int | None = None) -> str:
    """Return the URL if it looks like real article imagery, else ''."""
    url = (url or "").strip()
    if not url.lower().startswith(("http://", "https://")):
        return ""
    path = url.split("?", 1)[0].lower()
    if path.endswith(IMAGE_EXT_REJECT) or IMAGE_NOISE.search(path):
        return ""
    try:
        # A declared size is a stronger signal than the filename: trackers
        # advertise themselves as 1x1.
        if width and int(width) < 200:
            return ""
        if height and int(height) < 150:
            return ""
    except (TypeError, ValueError):
        pass
    return url


def extract_feed_image(item: ET.Element) -> str:
    """Pull an article image out of an RSS item, if the feed carries one.

    Four places, in descending order of how deliberate they are:
    media:content and media:thumbnail (Media RSS, what most publishing
    platforms emit), an image enclosure, and finally the first <img> inside
    content:encoded or description — which is where WordPress puts it, and
    WordPress is what most of the region's newsrooms run.
    """
    for element in item.findall(f"{MEDIA_NS}content"):
        medium = (element.get("medium") or "").lower()
        mime = (element.get("type") or "").lower()
        if medium and medium != "image":
            continue
        if mime and not mime.startswith("image/"):
            continue
        found = _usable_image(element.get("url", ""), element.get("width"), element.get("height"))
        if found:
            return found

    for element in item.findall(f"{MEDIA_NS}thumbnail"):
        found = _usable_image(element.get("url", ""), element.get("width"), element.get("height"))
        if found:
            return found

    for element in item.findall("enclosure"):
        if (element.get("type") or "").lower().startswith("image/"):
            found = _usable_image(element.get("url", ""))
            if found:
                return found

    body = (item.findtext(f"{CONTENT_NS}encoded", "") or "") + (item.findtext("description", "") or "")
    for match in re.finditer(r"<img[^>]+src=[\"']([^\"']+)[\"']", unescape(body), re.I):
        found = _usable_image(match.group(1))
        if found:
            return found
    return ""


def parse_rss(xml_text: str) -> list[dict[str, str]]:
    root = ET.fromstring(xml_text)
    channel = root.find("channel")
    if channel is None:
        channel = root
    items = []
    for item in channel.findall("item"):
        title = strip_html(item.findtext("title", "") or "")
        link = (item.findtext("link", "") or "").strip()
        published = (item.findtext("pubDate", "") or item.findtext("{http://purl.org/dc/elements/1.1/}date", "") or "").strip()
        summary = strip_html(item.findtext("description", "") or item.findtext("{http://purl.org/rss/1.0/modules/content/}encoded", "") or "")
        if title and link:
            entry = {"title": title, "url": link, "published": published, "summary": summary}
            image = extract_feed_image(item)
            if image:
                entry["image_url"] = image
                entry["image_kind"] = "feed"
            items.append(entry)
    return items


def infer_countries(text: str, scope: str) -> list[str]:
    blob = text.lower()
    found = [country for country in COUNTRY_NAMES if country.lower() in blob]
    for alias, canonical in COUNTRY_ALIASES.items():
        if alias in blob and canonical not in found:
            found.append(canonical)
    if scope and scope != "regional" and scope not in found:
        found.insert(0, scope)
    return found or ([scope] if scope and scope != "regional" else [])


def parse_published(value: str | None) -> datetime | None:
    if not value:
        return None
    try:
        parsed = parsedate_to_datetime(value)
    except (TypeError, ValueError):
        try:
            parsed = datetime.fromisoformat(value.replace("Z", "+00:00"))
        except ValueError:
            return None
    return (parsed.replace(tzinfo=timezone.utc) if parsed.tzinfo is None else parsed).astimezone(timezone.utc)


def classify_topics(text: str) -> list[str]:
    blob = text.lower()
    return [topic for topic, terms in TOPICS.items() if any(term in blob for term in terms)]


def normalize_article(article: dict[str, str], feed: dict[str, Any]) -> dict[str, Any]:
    text = f"{article['title']} {article.get('summary', '')}"
    return {
        "id": re.sub(r"[^a-z0-9]+", "-", article["url"].lower())[:120],
        "title": article["title"], "url": article["url"],
        "published": article.get("published") or None, "summary": article.get("summary", "")[:500],
        "source": feed.get("label", feed.get("slug", "rss")), "feed_slug": feed.get("slug", ""),
        "countries": infer_countries(text, feed.get("scope", "regional")),
        "fetched_at": datetime.now(timezone.utc).isoformat(),
        # normalize_article rebuilds the record field by field, so anything the
        # feed gave us has to be carried across explicitly or it is dropped here.
        **({"image_url": article["image_url"], "image_kind": article.get("image_kind", "feed")}
           if article.get("image_url") else {}),
    }


def enrich_article(article: dict[str, Any], now: datetime | None = None) -> dict[str, Any]:
    now = now or datetime.now(timezone.utc)
    text = f"{article.get('title', '')} {article.get('summary', '')}"
    topics = classify_topics(text)
    published = parse_published(article.get("published"))
    age_hours = max(0, int((now - published).total_seconds() // 3600)) if published else None
    slug = article.get("feed_slug", "")
    source_tier = 1 if slug == "cdb-rss" else 3 if slug.startswith("google-news") else 2
    score = 25 + (4 - source_tier) * 8 + min(24, len(topics) * 6) + min(18, len(article.get("countries", [])) * 6)
    if age_hours is not None:
        score += 28 if age_hours <= 24 else 18 if age_hours <= 72 else 8 if age_hours <= 168 else 0
    if any(term in text.lower() for term in NOISE_TERMS):
        score -= 35
    return {**article, "topics": topics or ["regional"], "source_tier": source_tier,
            "age_hours": age_hours, "relevance_score": max(0, min(100, score)),
            "finance_relevant": bool(set(topics) & {"finance", "energy", "trade", "procurement", "tourism"})}


def ranked_articles(items: list[dict[str, Any]], country: str | None = None, topic: str | None = None, limit: int = 30) -> list[dict[str, Any]]:
    enriched = [enrich_article(item) for item in items]
    if country:
        enriched = [item for item in enriched if country in item.get("countries", [])]
    if topic:
        enriched = [item for item in enriched if topic in item.get("topics", [])]
    deduped: dict[str, dict[str, Any]] = {}
    for item in enriched:
        key = re.sub(r"[^a-z0-9]+", " ", item.get("title", "").lower()).strip()
        if key and (key not in deduped or item["relevance_score"] > deduped[key]["relevance_score"]):
            deduped[key] = item
    return sorted(deduped.values(), key=lambda item: (item["relevance_score"], item.get("published") or ""), reverse=True)[:limit]


def poll_feed(feed: dict[str, Any], max_items: int) -> list[dict[str, Any]]:
    try:
        xml_text = fetch_feed(feed["url"])
    except Exception as exc:
        print(f"regional_news: {feed.get('slug', feed['url'])} unreachable ({exc})")
        return []
    RAW.mkdir(parents=True, exist_ok=True)
    stamp = datetime.now(timezone.utc).strftime("%Y%m%d")
    (RAW / f"{feed.get('slug', 'feed')}-{stamp}.xml").write_text(xml_text[:500_000], encoding="utf-8")
    articles = [enrich_article(normalize_article(raw, feed)) for raw in parse_rss(xml_text)[:max_items]]
    print(f"regional_news: {feed.get('slug')} -> {len(articles)} articles")
    return articles


def main() -> None:
    config = load_config()
    items, seen = [], set()
    for feed in config.get("feeds", []):
        for article in poll_feed(feed, int(config.get("max_items_per_feed", 25))):
            if article["url"] not in seen:
                seen.add(article["url"]); items.append(article)
            if len(items) >= int(config.get("max_total_items", 120)):
                break
    OUT.parent.mkdir(parents=True, exist_ok=True)
    # Non-destructive: if we collected nothing but prior good data exists, keep it
    # so a network failure (e.g. build sandbox) never deploys an empty section.
    if not items and OUT.exists():
        try:
            prior = json.loads(OUT.read_text(encoding="utf-8")).get("items", [])
        except Exception:
            prior = []
        if prior:
            print(f"regional_news: 0 fresh articles, keeping {len(prior)} prior items")
            return
    OUT.write_text(json.dumps({"fetched_at": datetime.now(timezone.utc).isoformat(), "source": "regional_news",
                               "total": len(items), "items": ranked_articles(items, limit=len(items))},
                              indent=1, ensure_ascii=False) + "\n", encoding="utf-8")
    print(f"regional_news: {len(items)} articles -> {OUT}")


if __name__ == "__main__":
    main()
