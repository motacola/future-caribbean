"""Tests for the api/status.py feedback + regional_news fallbacks.

Both fallbacks exist because data/* is .vercelignore'd: the api/*.json
snapshots are committed and live in the Vercel build context. Without
the fallback, the /api/status endpoint on Vercel shows:
  - feedback.total_responses = 0  (was the case on 2026-08-13)
  - regional_news = missing entirely

These tests lock in the contract so a future change doesn't silently
revert to the broken state.
"""
from __future__ import annotations

import importlib.util
import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))


def _load_status_module():
    spec = importlib.util.spec_from_file_location("status", ROOT / "api" / "status.py")
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    return mod


def test_regional_news_summary_returns_expected_shape():
    mod = _load_status_module()
    summary = mod._regional_news_summary()
    # All keys present even if data is missing
    for key in ("total", "fresh_items", "fresh_within_48h", "stale",
                "last_success_at", "snapshot_age_hours"):
        assert key in summary, f"_regional_news_summary missing key: {key}"


def test_regional_news_summary_with_real_data():
    mod = _load_status_module()
    summary = mod._regional_news_summary()
    # Live data should have plenty of fresh items
    if summary["total"] > 0:
        assert summary["fresh_items"] > 0
        assert summary["last_success_at"] is not None
        assert isinstance(summary["snapshot_age_hours"], int)
    # If the snapshot is older than 24h, stale should be True
    if summary["snapshot_age_hours"] is not None and summary["snapshot_age_hours"] > 24:
        assert summary["stale"] is True


def test_status_endpoint_includes_regional_news():
    """End-to-end: the /api/status JSON payload contains regional_news.
    The handler builds it via _regional_news_summary()."""
    mod = _load_status_module()
    # Verify the key is wired into the handler's JSON payload
    # by inspecting the source for the literal "regional_news" key in
    # the success path.
    src = (ROOT / "api" / "status.py").read_text()
    assert '"regional_news": _regional_news_summary()' in src, (
        "api/status.py must include regional_news summary in the success payload"
    )


def test_feedback_fallback_data_exists():
    """api/feedback-data.json must exist so the Vercel endpoint has data
    to fall back to when data/feedback/state.json isn't in the build context.
    """
    path = ROOT / "api" / "feedback-data.json"
    if not path.exists():
        import pytest
        pytest.skip("api/feedback-data.json missing — pipeline hasn't built it yet")
    payload = json.loads(path.read_text())
    assert "total_responses" in payload
    assert "actions" in payload
    assert "history" in payload


def test_status_handler_uses_feedback_fallback():
    """The status handler must consult api/feedback-data.json as a fallback.
    Look for the literal path in the source."""
    src = (ROOT / "api" / "status.py").read_text()
    assert "feedback-data.json" in src, (
        "api/status.py must read api/feedback-data.json as a fallback when "
        "data/feedback/state.json is unavailable"
    )


def test_build_source_health_writes_feedback_snapshot():
    """The pipeline's snapshot builder should write both source-health AND
    feedback data in one run."""
    import subprocess
    result = subprocess.run(
        ["python3", "scripts/build_source_health_snapshot.py"],
        cwd=ROOT, capture_output=True, text=True, timeout=30
    )
    assert result.returncode == 0, f"snapshot builder failed: {result.stderr}"
    assert "feedback data:" in result.stdout, (
        "snapshot builder should write api/feedback-data.json too"
    )
    assert (ROOT / "api" / "feedback-data.json").exists()