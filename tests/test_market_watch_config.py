"""Tests for watchers/market_watch_poller.

Two regressions hit on 2026-08-13:

1. config/market_sources.json was MISSING. load_json silently caught
   FileNotFoundError and returned {}, so build_snapshot produced 0 markets
   and the snapshot file ended up with no rows. The poller still printed
   '0/0 official pages reached' instead of failing loudly. Locked in:
   the config file must exist and contain at least one enabled market.

2. fetch_page had an unused/incorrect bare ssl.create_default_context()
   fallback before the certifi upgrade. Now both paths agree (use certifi
   if available, otherwise default).

These tests don't hit the network — they verify the poller's contract
against the local config + the public-file contract.
"""
from __future__ import annotations

import json
import os
import sys
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
sys.path.insert(0, str(ROOT / "watchers"))

from market_watch_poller import build_snapshot, load_json, CONFIG



# build_snapshot() polls six live exchange pages. That is the collector's job,
# not a gating test's: it made the scheduled pipeline's verify step depend on
# third-party uptime, and the first cycle after the gate went in failed because
# bse.com.bb was down. These contract assertions run against the committed
# snapshot instead — the artefact the site actually serves — so an exchange
# outage can no longer stop the desk publishing. The live poll is still checked,
# under MARKET_WATCH_LIVE=1, by the test at the bottom of this file.
ALLOWED_STATES = {
    "current", "delayed", "stale",
    "source_checked_no_dated_observation", "stale_fallback",
    # A failed fetch becomes stale_fallback only when a previous *dated*
    # observation exists to preserve. Jamaica and Cayman never publish one, so
    # an unreachable source stays "unavailable" for them. That row is still
    # honest — it carries no date — and this contract rejects invented dates,
    # not admissions of failure.
    "unavailable",
}

COMMITTED_SNAPSHOTS = (
    ROOT / "public" / "market_watch.json",
    ROOT / "data" / "market_watch" / "latest.json",
    ROOT / "api" / "market-watch-data.json",
)


def committed_snapshot() -> dict:
    for path in COMMITTED_SNAPSHOTS:
        if path.exists():
            return json.loads(path.read_text(encoding="utf-8"))
    pytest.skip("no committed market-watch snapshot to validate")


def test_config_file_exists():
    """The config must be present — a missing file silently produces 0 markets."""
    assert CONFIG.exists(), (
        f"market_sources.json missing at {CONFIG}. "
        "build_snapshot() will return 0 markets and the snapshot will be empty."
    )


def test_config_has_markets():
    config = load_json(CONFIG, {})
    markets = config.get("markets") or []
    assert len(markets) >= 1, "config must declare at least one market"
    for m in markets:
        assert m.get("id"), f"market missing id: {m}"
        exchange = m.get("exchange") or {}
        assert exchange.get("name"), f"market {m.get('id')} missing exchange.name"
        assert exchange.get("url"), f"market {m.get('id')} missing exchange.url"


def test_config_market_ids_match_poller_patterns():
    """Every market id must have DATE_PATTERNS + STATUS_PATTERNS entries,
    otherwise extract_observation silently returns None and the snapshot
    never says anything about that market.

    This locks in the contract that adding a market to config without
    adding regexes to the poller is a setup error, not a silent no-op.
    """
    import re as _re
    from market_watch_poller import DATE_PATTERNS, STATUS_PATTERNS
    config = load_json(CONFIG, {})
    for m in config.get("markets") or []:
        mid = m.get("id")
        if not m.get("enabled", True):
            continue
        assert mid in DATE_PATTERNS, (
            f"market '{mid}' is enabled in config but has no DATE_PATTERNS entry "
            "in watchers/market_watch_poller.py"
        )
        assert mid in STATUS_PATTERNS, (
            f"market '{mid}' is enabled in config but has no STATUS_PATTERNS entry "
            "in watchers/market_watch_poller.py"
        )
        # Each pattern must compile.
        for pat in DATE_PATTERNS[mid]:
            _re.compile(pat)
        _re.compile(STATUS_PATTERNS[mid])


def test_build_snapshot_with_config_runs():
    """With a valid config the snapshot has markets, even where a page is
    JS-rendered or a regex needs updating. 0 markets is a regression.
    """
    snap = committed_snapshot()
    health = snap["health"]
    configured = health["configured_sources"]
    assert configured >= 1, (
        f"snapshot has 0 configured_sources — likely a missing config or "
        "the config has all markets disabled"
    )
    assert len(snap["markets"]) == configured


def test_snapshot_has_honest_unmatched_states():
    """When a regex doesn't match a real page, the row should say so —
    not manufacture a date. This is the freshness-explicit contract:
    'source_checked_no_dated_observation' is a valid state.
    """
    snap = committed_snapshot()
    states = {row.get("freshness_state") for row in snap["markets"]}
    # All states should be in the documented healthy set; nothing should
    # be invented.
    allowed = ALLOWED_STATES
    for s in states:
        assert s in allowed, f"unexpected freshness_state: {s}"

@pytest.mark.skipif(
    os.environ.get("MARKET_WATCH_LIVE") != "1",
    reason="hits six live exchange pages; set MARKET_WATCH_LIVE=1 to run",
)
def test_live_poll_still_produces_honest_states():
    """The same contract against a real poll. Deliberate, never a release gate:
    a Caribbean exchange being unreachable is news about that exchange, not a
    reason to stop publishing the desk."""
    snap = build_snapshot()
    assert snap["markets"], "live poll returned no markets"
    for row in snap["markets"]:
        assert row.get("freshness_state") in ALLOWED_STATES, row.get("freshness_state")
        if row.get("freshness_state") == "unavailable":
            assert row.get("observation_at") is None, "unavailable row must not carry a date"
