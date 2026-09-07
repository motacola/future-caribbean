"""Tests for the news-image enrichment stage (fixture-based, no network).

The stage exists because none of the configured feeds carry imagery: every
one is a Google News search or the CDB RSS, and neither emits media:content,
media:thumbnail or an enclosure. It is also what refreshes the two deployable
snapshots, so the pipeline wiring is part of what these tests protect.
"""
import sys
from datetime import datetime, timedelta, timezone
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from scripts.enrich_news_images import (  # noqa: E402
    CACHE_RETENTION_DAYS,
    apply_metadata,
    enrich_payload,
    prune_cache,
    select_image,
)

NOW = datetime(2026, 9, 6, tzinfo=timezone.utc)


def _stamp(days_ago: int) -> str:
    return (NOW - timedelta(days=days_ago)).isoformat()


def test_pipeline_runs_enrichment_after_the_poller():
    """A snapshot refresh that only ever ran by hand is not a pipeline stage."""
    script = (ROOT / "run_pipeline.sh").read_text(encoding="utf-8")
    assert "enrich_news_images.py" in script
    assert script.index("regional_news_poller.py") < script.index("enrich_news_images.py")


def test_enrichment_failure_cannot_fail_the_cycle():
    """Microlink is a third party; losing it must not block publication."""
    script = (ROOT / "run_pipeline.sh").read_text(encoding="utf-8")
    optional = next(line for line in script.splitlines() if line.startswith("OPTIONAL_STEPS="))
    assert "|News Images|" in optional


def test_cached_metadata_is_applied_without_any_lookup(monkeypatch):
    def _explode(url):  # pragma: no cover - must never be called
        raise AssertionError(f"unexpected network lookup for {url}")

    monkeypatch.setattr("scripts.enrich_news_images.resolve_metadata", _explode)
    monkeypatch.setattr(
        "scripts.enrich_news_images._read_json",
        lambda path, fallback: {
            "https://news.google.com/a": {
                "image_url": "https://cdn.example.com/story.jpg",
                "image_kind": "publisher",
                "checked_at": _stamp(1),
            }
        },
    )
    payload = {"items": [{"title": "Guyana port expansion", "url": "https://news.google.com/a"}]}
    enriched, _ = enrich_payload(payload)
    assert enriched["items"][0]["image_url"] == "https://cdn.example.com/story.jpg"
    assert enriched["image_enrichment"]["with_images"] == 1


def test_an_item_without_imagery_still_publishes():
    """No thumbnail is a fallback in the UI, never a dropped story."""
    item = {"title": "Belize logistics corridor", "url": "https://news.google.com/b"}
    merged = apply_metadata(item, {"publisher_domain": "example.com", "image_url": None})
    assert merged["title"] == item["title"]
    assert "image_url" not in merged


def test_logos_and_undersized_assets_are_not_thumbnails():
    assert select_image({"image": {"url": "https://example.com/logo.png", "width": 900, "height": 600}}) is None
    assert select_image({"image": {"url": "https://example.com/a.svg", "type": "svg"}}) is None
    assert select_image({"image": {"url": "https://example.com/a.jpg", "width": 120, "height": 90}}) is None
    good = select_image({"image": {"url": "https://example.com/story.jpg", "width": 1200, "height": 630}})
    assert good and good["image_kind"] == "publisher"


def test_cache_keeps_live_and_recent_entries_and_drops_the_rest():
    """Google News mints a new URL per article, so stale keys can never be hit."""
    cache = {
        "https://news.google.com/live": {"checked_at": _stamp(400)},
        "https://news.google.com/recent": {"checked_at": _stamp(CACHE_RETENTION_DAYS - 1)},
        "https://news.google.com/expired": {"checked_at": _stamp(CACHE_RETENTION_DAYS + 1)},
        "https://news.google.com/undated": {"image_url": "https://cdn.example.com/x.jpg"},
    }
    kept = prune_cache(cache, {"https://news.google.com/live"}, now=NOW)
    assert set(kept) == {"https://news.google.com/live", "https://news.google.com/recent"}
