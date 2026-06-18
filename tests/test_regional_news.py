"""Tests for regional news RSS poller (fixture-based, no network)."""
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from watchers.regional_news_poller import infer_countries, normalize_article, parse_rss  # noqa: E402

SAMPLE_RSS = """<?xml version="1.0" encoding="UTF-8"?>
<rss version="2.0">
  <channel>
    <title>Test Feed</title>
    <item>
      <title>Guyana oil infrastructure investment grows</title>
      <link>https://example.com/guyana-oil</link>
      <pubDate>Wed, 18 Jun 2026 10:00:00 GMT</pubDate>
      <description>Offshore energy sector expansion in Guyana continues.</description>
    </item>
  </channel>
</rss>
"""


def test_parse_rss_fixture():
    items = parse_rss(SAMPLE_RSS)
    assert len(items) == 1
    assert "Guyana" in items[0]["title"]


def test_normalize_article_tags_country():
    feed = {"slug": "test", "label": "Test", "scope": "Guyana"}
    article = normalize_article({
        "title": "Guyana infrastructure projects announced",
        "url": "https://example.com/a",
        "published": "2026-06-18",
        "summary": "Construction in Guyana accelerates",
    }, feed)
    assert "Guyana" in article["countries"]


def test_infer_countries_from_text():
    found = infer_countries("Belize tourism and logistics corridor expands", "regional")
    assert "Belize" in found
