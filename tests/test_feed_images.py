"""Image extraction from RSS itself (fixture-based, no network).

Every feed configured today is a Google News search or the CDB RSS, and neither
carries imagery — which is why the only thumbnails came from fetching the
article page. Direct publisher feeds do carry it, in four different places
depending on the platform, and reading it there costs nothing per article.
"""
import sys
import xml.etree.ElementTree as ET
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from watchers.regional_news_poller import extract_feed_image, normalize_article, parse_rss  # noqa: E402

FEED = """<?xml version="1.0" encoding="UTF-8"?>
<rss version="2.0"
     xmlns:media="http://search.yahoo.com/mrss/"
     xmlns:content="http://purl.org/rss/1.0/modules/content/">
  <channel>
    <item>
      <title>Media RSS carries the picture</title>
      <link>https://example.com/a</link>
      <media:content url="https://cdn.example.com/a.jpg" medium="image" width="1200" height="630"/>
    </item>
    <item>
      <title>Only a thumbnail here</title>
      <link>https://example.com/b</link>
      <media:thumbnail url="https://cdn.example.com/b.jpg" width="800" height="450"/>
    </item>
    <item>
      <title>An enclosure, podcast style</title>
      <link>https://example.com/c</link>
      <enclosure url="https://cdn.example.com/c.jpg" type="image/jpeg" length="12345"/>
    </item>
    <item>
      <title>WordPress puts it in the body</title>
      <link>https://example.com/d</link>
      <content:encoded><![CDATA[<p>Lead paragraph.</p><img src="https://site.example/wp-content/uploads/2026/08/photo.jpg" alt=""/>]]></content:encoded>
    </item>
    <item>
      <title>Nothing but words</title>
      <link>https://example.com/e</link>
      <description>Plain summary with no image at all.</description>
    </item>
  </channel>
</rss>"""


def _item(title_fragment: str) -> ET.Element:
    channel = ET.fromstring(FEED).find("channel")
    return next(i for i in channel.findall("item") if title_fragment in (i.findtext("title") or ""))


def test_each_place_a_feed_can_put_an_image_is_read():
    assert extract_feed_image(_item("Media RSS")) == "https://cdn.example.com/a.jpg"
    assert extract_feed_image(_item("thumbnail")) == "https://cdn.example.com/b.jpg"
    assert extract_feed_image(_item("enclosure")) == "https://cdn.example.com/c.jpg"
    assert extract_feed_image(_item("WordPress")).endswith("/2026/08/photo.jpg")


def test_an_item_with_no_image_yields_nothing_rather_than_a_guess():
    assert extract_feed_image(_item("Nothing but words")) == ""


def test_parse_rss_attaches_the_image_and_marks_where_it_came_from():
    items = {i["title"]: i for i in parse_rss(FEED)}
    assert items["Media RSS carries the picture"]["image_url"] == "https://cdn.example.com/a.jpg"
    assert items["Media RSS carries the picture"]["image_kind"] == "feed"
    assert "image_url" not in items["Nothing but words"]


def test_normalize_keeps_the_image_it_was_given():
    """normalize_article rebuilds the record field by field; the image must survive."""
    article = {"title": "T", "url": "https://example.com/x", "published": "", "summary": "",
               "image_url": "https://cdn.example.com/x.jpg", "image_kind": "feed"}
    out = normalize_article(article, {"slug": "s", "label": "L", "scope": "Guyana"})
    assert out["image_url"] == "https://cdn.example.com/x.jpg"
    assert out["image_kind"] == "feed"


def test_logos_trackers_and_icons_are_not_article_images():
    noise = """<?xml version="1.0"?><rss version="2.0" xmlns:media="http://search.yahoo.com/mrss/"><channel>
      <item><title>logo</title><link>https://e.com/1</link>
        <media:content url="https://e.com/assets/site-logo.png" medium="image"/></item>
      <item><title>tracker</title><link>https://e.com/2</link>
        <media:content url="https://e.com/p.jpg" medium="image" width="1" height="1"/></item>
      <item><title>vector</title><link>https://e.com/3</link>
        <media:content url="https://e.com/brand.svg" medium="image"/></item>
      <item><title>relative</title><link>https://e.com/4</link>
        <content:encoded xmlns:content="http://purl.org/rss/1.0/modules/content/"><![CDATA[<img src="/local/path.jpg">]]></content:encoded></item>
    </channel></rss>"""
    channel = ET.fromstring(noise).find("channel")
    assert [extract_feed_image(i) for i in channel.findall("item")] == ["", "", "", ""]


def test_a_video_enclosure_is_not_mistaken_for_a_thumbnail():
    feed = """<?xml version="1.0"?><rss version="2.0"><channel><item>
      <title>v</title><link>https://e.com/v</link>
      <enclosure url="https://e.com/clip.mp4" type="video/mp4" length="99"/>
    </item></channel></rss>"""
    assert extract_feed_image(ET.fromstring(feed).find("channel").find("item")) == ""


def test_every_configured_feed_is_well_formed():
    """A malformed entry fails at poll time, in a step that is allowed to fail
    quietly — so the shape is worth asserting here instead."""
    import json
    config = json.loads((ROOT / "config" / "regional_news_sources.json").read_text(encoding="utf-8"))
    feeds = config["feeds"]
    assert feeds, "no feeds configured"
    slugs = [f["slug"] for f in feeds]
    assert len(slugs) == len(set(slugs)), "duplicate feed slug"
    for feed in feeds:
        assert feed["url"].startswith("https://"), feed["slug"]
        assert feed.get("label") and feed.get("scope"), feed["slug"]
        assert feed.get("kind") in {"aggregator", "publisher"}, feed["slug"]


def test_the_desk_is_not_sourced_only_from_one_aggregator():
    """Google News redirects carry no imagery and resolve poorly: 7 of the 25
    cached lookups never got past news.google.com, none with an image."""
    import json
    config = json.loads((ROOT / "config" / "regional_news_sources.json").read_text(encoding="utf-8"))
    publishers = [f for f in config["feeds"] if f.get("kind") == "publisher"]
    assert len(publishers) >= 2, "the mix has collapsed back to aggregator-only"
