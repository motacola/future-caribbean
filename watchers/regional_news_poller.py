"""Regional news RSS poller — sector corroboration input for validation packs.

Fetches configured RSS feeds and normalizes articles for keyword matching
against sector hypotheses. Output: data/regional_news/latest.json
"""
from __future__ import annotations

import json
import re
import urllib.request
import xml.etree.ElementTree as ET
from datetime import datetime, timezone
from html import unescape
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parents[1]
CONFIG = ROOT / "config" / "regional_news_sources.json"
OUT = ROOT / "data" / "regional_news" / "latest.json"
RAW = ROOT / "data" / "regional_news" / "raw"

UA = {"User-Agent": "Mozilla/5.0 (compatible; CaribbeanSignalOS/1.0)"}
TIMEOUT = 20

COUNTRY_NAMES = [
    "Guyana", "Jamaica", "Belize", "Barbados", "Trinidad and Tobago",
    "Bahamas", "Suriname", "Haiti", "Dominica", "Grenada", "Saint Lucia",
    "St. Vincent and the Grenadines", "St. Kitts and Nevis", "Antigua and Barbuda",
]


def load_config() -> dict[str, Any]:
    return json.loads(CONFIG.read_text(encoding="utf-8"))


def strip_html(text: str) -> str:
    text = unescape(re.sub(r"<[^>]+>", " ", text or ""))
    return re.sub(r"\s+", " ", text).strip()


def fetch_feed(url: str) -> str:
    req = urllib.request.Request(url, headers=UA)
    with urllib.request.urlopen(req, timeout=TIMEOUT) as resp:
        return resp.read().decode("utf-8", errors="replace")


def parse_rss(xml_text: str) -> list[dict[str, str]]:
    root = ET.fromstring(xml_text)
    channel = root.find("channel")
    if channel is None:
        channel = root
    items: list[dict[str, str]] = []
    for item in channel.findall("item"):
        title = strip_html(item.findtext("title", "") or "")
        link = (item.findtext("link", "") or "").strip()
        pub = (item.findtext("pubDate", "") or item.findtext("{http://purl.org/dc/elements/1.1/}date", "") or "").strip()
        desc = strip_html(item.findtext("description", "") or item.findtext("{http://purl.org/rss/1.0/modules/content/}encoded", "") or "")
        if title and link:
            items.append({"title": title, "url": link, "published": pub, "summary": desc})
    return items


def infer_countries(text: str, scope: str) -> list[str]:
    blob = text.lower()
    found = [c for c in COUNTRY_NAMES if c.lower() in blob]
    if scope and scope != "regional" and scope not in found:
        found.insert(0, scope)
    return found or ([scope] if scope and scope != "regional" else [])


def normalize_article(article: dict[str, str], feed: dict[str, Any]) -> dict[str, Any]:
    text = f"{article['title']} {article.get('summary', '')}"
    countries = infer_countries(text, feed.get("scope", "regional"))
    return {
        "id": re.sub(r"[^a-z0-9]+", "-", article["url"].lower())[:120],
        "title": article["title"],
        "url": article["url"],
        "published": article.get("published") or None,
        "summary": article.get("summary", "")[:500],
        "source": feed.get("label", feed.get("slug", "rss")),
        "feed_slug": feed.get("slug", ""),
        "countries": countries,
        "fetched_at": datetime.now(timezone.utc).isoformat(),
    }


def poll_feed(feed: dict[str, Any], max_items: int) -> list[dict[str, Any]]:
    url = feed["url"]
    try:
        xml_text = fetch_feed(url)
    except Exception as exc:
        print(f"regional_news: {feed.get('slug', url)} unreachable ({exc})")
        return []
    RAW.mkdir(parents=True, exist_ok=True)
    stamp = datetime.now(timezone.utc).strftime("%Y%m%d")
    (RAW / f"{feed.get('slug', 'feed')}-{stamp}.xml").write_text(xml_text[:500_000], encoding="utf-8")
    articles = []
    for raw in parse_rss(xml_text)[:max_items]:
        articles.append(normalize_article(raw, feed))
    print(f"regional_news: {feed.get('slug')} -> {len(articles)} articles")
    return articles


def main() -> None:
    cfg = load_config()
    per_feed = int(cfg.get("max_items_per_feed", 25))
    cap = int(cfg.get("max_total_items", 120))
    items: list[dict[str, Any]] = []
    seen: set[str] = set()
    for feed in cfg.get("feeds", []):
        for article in poll_feed(feed, per_feed):
            key = article.get("url", "")
            if not key or key in seen:
                continue
            seen.add(key)
            items.append(article)
            if len(items) >= cap:
                break
        if len(items) >= cap:
            break
    OUT.parent.mkdir(parents=True, exist_ok=True)
    OUT.write_text(json.dumps({
        "fetched_at": datetime.now(timezone.utc).isoformat(),
        "source": "regional_news",
        "total": len(items),
        "items": items,
    }, indent=1, ensure_ascii=False) + "\n", encoding="utf-8")
    print(f"regional_news: {len(items)} articles -> {OUT}")


if __name__ == "__main__":
    main()
