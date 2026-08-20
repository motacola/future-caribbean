"""Tests for the source-health bundle and its staleness contract.

Regression under test: api/source-health-data.json is the only source
freshness signal that reaches production (data/*/latest.json is gitignored
and .vercelignore'd). Nothing regenerated it, so it stayed frozen at
2026-08-13 while /api/status kept reporting 6/6 sources ok with ages past
six days. These tests lock in that the bundle is published from real
snapshots and that a silent source reads as stale rather than healthy.
"""
from __future__ import annotations

import importlib.util
import json
import sys
from datetime import datetime, timedelta, timezone
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from packagers import source_health  # noqa: E402


def _load_status_module():
    spec = importlib.util.spec_from_file_location("status", ROOT / "api" / "status.py")
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    return mod


def _write_snapshot(root: Path, key: str, fetched_at: str) -> None:
    d = root / "data" / key
    d.mkdir(parents=True, exist_ok=True)
    (d / "latest.json").write_text(json.dumps({"fetched_at": fetched_at}), encoding="utf-8")


def test_build_health_reports_every_known_source(tmp_path):
    now = datetime.now(timezone.utc).isoformat()
    for key in source_health.REFRESH_MINUTES:
        _write_snapshot(tmp_path, key, now)

    health = source_health.build_health(root=tmp_path, previous={})

    assert set(health) == set(source_health.REFRESH_MINUTES)
    for key, entry in health.items():
        assert entry["ok"] is True
        assert entry["fetched_at"] == now
        assert entry["refresh_minutes"] == source_health.REFRESH_MINUTES[key]


def test_missing_snapshot_carries_forward_last_known_fetch(tmp_path):
    """A source that stops producing snapshots keeps its last known
    timestamp and is flagged, so its age keeps growing instead of the
    source vanishing from the response."""
    previous = {"noaa": {"ok": True, "fetched_at": "2026-08-13T16:29:34+00:00"}}

    health = source_health.build_health(root=tmp_path, previous=previous)

    assert health["noaa"]["fetched_at"] == "2026-08-13T16:29:34+00:00"
    assert health["noaa"]["carried_forward"] is True


def test_never_collected_source_is_not_ok(tmp_path):
    health = source_health.build_health(root=tmp_path, previous={})
    assert health["noaa"]["ok"] is False
    assert health["noaa"]["fetched_at"] is None


def test_staleness_threshold_is_cadence_relative():
    mod = _load_status_module()
    # A four-hourly source and a daily source must not share a threshold.
    fast = mod._max_age_minutes({"refresh_minutes": 240})
    slow = mod._max_age_minutes({"refresh_minutes": 1440})
    assert fast < slow
    assert fast == 480
    assert slow == 2880


def test_staleness_threshold_survives_a_missing_or_broken_interval():
    mod = _load_status_module()
    assert mod._max_age_minutes({}) == mod._DEFAULT_REFRESH_MINUTES * 2
    assert mod._max_age_minutes({"refresh_minutes": "nonsense"}) == mod._DEFAULT_REFRESH_MINUTES * 2


def test_status_marks_a_silent_source_stale():
    """The defect in production: fetched_at existed, so ok was True and
    nothing said the snapshot was six days old."""
    mod = _load_status_module()
    six_days_ago = (datetime.now(timezone.utc) - timedelta(days=6)).isoformat()
    age = mod._age_minutes(six_days_ago)
    assert age > mod._max_age_minutes({"refresh_minutes": 240})


def test_published_bundle_has_refresh_intervals():
    """The committed bundle must carry the cadence metadata /api/status
    needs, or every source silently falls back to the daily default."""
    path = ROOT / "api" / "source-health-data.json"
    if not path.exists():
        import pytest
        pytest.skip("api/source-health-data.json missing — pipeline hasn't built it yet")
    payload = json.loads(path.read_text())
    assert "generated_at" in payload, "bundle must record when it was published"
    for key in source_health.REFRESH_MINUTES:
        assert key in payload, f"bundle missing source: {key}"
        assert "refresh_minutes" in payload[key], f"{key} missing refresh_minutes"


def test_status_payload_exposes_staleness_counts():
    src = (ROOT / "api" / "status.py").read_text()
    assert '"n_sources_stale": n_sources_stale' in src
    assert '"stale": stale' in src
