"""Tests for what the desk does when a cycle collects nothing.

Regression under test: every upstream source was unreachable, so the merger
produced zero composite signals. `packagers/regional_thesis.py` crashed with
KeyError: 'conflicted_countries' — its empty-cycle early return omitted a key
the writer always reads — and the pipeline declared an ESSENTIAL failure and
refused to publish. A cycle with no data must still publish a thesis that
says so.

Also covers the freshness contract for a run that failed: a watcher that
collected nothing records ok=false, and that snapshot must not reset the
staleness clock by standing in for a real refresh.
"""
from __future__ import annotations

import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from packagers import regional_thesis, source_health  # noqa: E402


def test_empty_cycle_thesis_has_the_keys_the_writer_reads():
    """The empty-cycle return must carry every key write_thesis_output touches."""
    empty = regional_thesis.build_regional_thesis([])
    populated_keys = {
        "thesis", "capital_momentum", "risk_flags",
        "conflicted_countries", "timing", "recommendations",
    }
    assert populated_keys <= set(empty), (
        f"empty-cycle thesis is missing {populated_keys - set(empty)} — "
        "write_thesis_output indexes these directly and will raise KeyError"
    )


def test_empty_cycle_writes_a_thesis_instead_of_crashing(tmp_path, monkeypatch):
    """A cycle with no signals still publishes, and says so plainly."""
    monkeypatch.setattr(regional_thesis, "ROOT", tmp_path)
    path = regional_thesis.write_thesis_output([], None, None)
    assert path.exists()
    text = path.read_text(encoding="utf-8")
    assert "No enriched signals available this cycle." in text


def test_failed_snapshot_does_not_reset_the_freshness_clock(tmp_path):
    """A watcher run that collected nothing must not read as a fresh refresh."""
    snapshot_dir = tmp_path / "data" / "world_bank"
    snapshot_dir.mkdir(parents=True)
    (snapshot_dir / "latest.json").write_text(json.dumps({
        "fetched_at": "2026-09-05T19:08:00+00:00",
        "ok": False,
        "errors": ["GY/NY.GDP.MKTP.CD: 403 Forbidden"],
        "observations": [],
    }), encoding="utf-8")

    previous = {"world_bank": {"fetched_at": "2026-09-01T00:00:00+00:00", "ok": True}}
    health = source_health.build_health(root=tmp_path, previous=previous)

    entry = health["world_bank"]
    assert entry["fetched_at"] == "2026-09-01T00:00:00+00:00", (
        "the failed run's timestamp was published as if it were a refresh"
    )
    assert entry["carried_forward"] is True


def test_successful_snapshot_is_reported_as_collected(tmp_path):
    """The carry-forward rule must not swallow a run that did collect data."""
    snapshot_dir = tmp_path / "data" / "noaa"
    snapshot_dir.mkdir(parents=True)
    (snapshot_dir / "latest.json").write_text(json.dumps({
        "fetched_at": "2026-09-05T19:08:00+00:00",
        "ok": True,
        "alerts": [{"id": "x"}],
    }), encoding="utf-8")

    health = source_health.build_health(root=tmp_path, previous={})
    entry = health["noaa"]
    assert entry["fetched_at"] == "2026-09-05T19:08:00+00:00"
    assert entry["ok"] is True
    assert not entry.get("carried_forward")
