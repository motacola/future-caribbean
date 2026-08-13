"""Fixture-based tests for the deterministic Caribbean Market Watch collector."""
from datetime import datetime, timezone

from watchers import market_watch_poller as market_watch


NOW = datetime(2026, 7, 24, 16, 0, tzinfo=timezone.utc)


def test_extracts_dated_official_exchange_observations():
    fixtures = {
        "jamaica": "Market Open 2026-07-24 IPCL at 11:53:59",
        "trinidad_tobago": "Activity for 24 Jul 2026 AGL AHL AMBL",
        "barbados": "Market open 2026-07-23 BHL BBD $4.50",
        "bahamas": "Market Open GMT-4 24 Jul 2026 07:11 AM Change: 0",
        "eastern_caribbean": "ECSE Daily Trade Report and Financial Tip – 23 July 2026",
    }
    expected = {
        "jamaica": "2026-07-24",
        "trinidad_tobago": "2026-07-24",
        "barbados": "2026-07-23",
        "bahamas": "2026-07-24",
        "eastern_caribbean": "2026-07-23",
    }
    for market_id, text in fixtures.items():
        observed, summary = market_watch.extract_observation(market_id, text)
        assert observed is not None
        assert observed.date().isoformat() == expected[market_id]
        assert summary


def test_observation_freshness_is_derived_from_official_date():
    assert market_watch.observation_state(datetime(2026, 7, 24, tzinfo=timezone.utc), NOW) == ("current", 0)
    assert market_watch.observation_state(datetime(2026, 7, 20, tzinfo=timezone.utc), NOW) == ("delayed", 4)
    assert market_watch.observation_state(datetime(2026, 7, 1, tzinfo=timezone.utc), NOW) == ("stale", 23)
    assert market_watch.observation_state(None, NOW) == ("source_checked_no_dated_observation", None)


def test_collect_market_never_invents_a_dated_observation(monkeypatch):
    monkeypatch.setattr(
        market_watch,
        "fetch_page",
        lambda _url: ("<html><h1>Daily Trading Summary</h1><p>No trades available.</p></html>", {"date": "Fri, 24 Jul 2026 16:00:00 GMT"}),
    )
    row = market_watch.collect_market(
        {"id": "cayman", "country": "Cayman Islands", "exchange": {"code": "CSX", "name": "CSX", "url": "https://example.test"}},
        NOW,
    )
    assert row["fetch_status"] == "ok"
    assert row["observation_at"] is None
    assert row["freshness_state"] == "source_checked_no_dated_observation"


def test_failed_refresh_preserves_only_a_previous_dated_observation():
    failed = {
        "id": "jamaica",
        "fetch_status": "failed",
        "freshness_state": "unavailable",
        "attempted_at": NOW.isoformat(),
        "error": "TimeoutError: timed out",
    }
    previous = {
        "id": "jamaica",
        "fetch_status": "ok",
        "freshness_state": "current",
        "observation_at": "2026-07-23",
        "observation_age_days": 0,
        "summary": "Market Open 2026-07-23",
    }
    preserved = market_watch.preserve_failed_market(failed, previous)
    assert preserved["observation_at"] == "2026-07-23"
    assert preserved["fetch_status"] == "fallback_cached"
    assert preserved["freshness_state"] == "stale_fallback"
    assert "previous dated official observation" in preserved["summary"]
    assert market_watch.preserve_failed_market(failed, None) == failed


def test_proxy_market_is_explicit_and_does_not_fetch(monkeypatch):
    monkeypatch.setattr(market_watch, "fetch_page", lambda _url: (_ for _ in ()).throw(AssertionError("must not fetch")))
    row = market_watch.collect_market(
        {"id": "guyana", "country": "Guyana", "exchange": {"code": "NO_DOMESTIC_EXCHANGE", "name": "No domestic exchange", "url": None}},
        NOW,
    )
    assert row["fetch_status"] == "not_applicable"
    assert row["freshness_state"] == "proxy_watch"
    assert row["observation_at"] is None


def test_bisx_public_page_keeps_its_official_delay_disclosure(monkeypatch):
    monkeypatch.setattr(
        market_watch,
        "fetch_page",
        lambda _url: ("Market Open GMT-4 24 Jul 2026 07:11 AM Change: 0", {}),
    )
    row = market_watch.collect_market(
        {"id": "bahamas", "country": "Bahamas", "exchange": {"code": "BISX", "name": "BISX", "url": "https://www.bisxbahamas.com"}},
        NOW,
    )
    assert row["freshness_state"] == "current"
    assert row["machine_readable_feed"] is False
    assert row["source_format"] == "public_html"
    assert row["timing_disclosure"] == "Official BISX homepage data is delayed by 30 minutes."
