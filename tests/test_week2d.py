"""Tests for Phase 2D: Validation Pack UI, Verdict Filter, Cycle Countdown."""

import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

import server
from server import AppHandler
import pytest


def test_validation_packs_endpoint_returns_verdict_field(tmp_path):
    """Test that /api/validation-packs includes verdict field in each pack."""
    # Set up minimal data structure
    outbox = tmp_path / "outbox" / "validation_packs"
    outbox.mkdir(parents=True)

    # Create index.json
    index = {
        "generated_at": "2026-06-10T00:00:00+00:00",
        "packs": [
            {"signal_id": "test-signal-1", "file": "test-signal-1.json", "country": "Guyana", "recommendation": "advance", "confidence_score": 90},
            {"signal_id": "test-signal-2", "file": "test-signal-2.json", "country": "Belize", "recommendation": "hold", "confidence_score": 75},
        ]
    }
    (outbox / "index.json").write_text(json.dumps(index))

    # Create pack files with verdict field
    pack1 = {
        "signal_id": "test-signal-1",
        "country": "Guyana",
        "advance_or_reject_recommendation": "advance",
        "recommendation_reason": "Test reason",
    }
    pack2 = {
        "signal_id": "test-signal-2",
        "country": "Belize",
        "advance_or_reject_recommendation": "hold",
        "recommendation_reason": "Test reason",
    }
    (outbox / "test-signal-1.json").write_text(json.dumps(pack1))
    (outbox / "test-signal-2.json").write_text(json.dumps(pack2))

    # Test index endpoint
    original_root = server.APP_DIR
    server.APP_DIR = tmp_path
    httpd = server.http.server.ThreadingHTTPServer(("127.0.0.1", 0), server.AppHandler)
    import threading
    thread = threading.Thread(target=httpd.serve_forever, daemon=True)
    thread.start()

    try:
        import urllib.request
        with urllib.request.urlopen(f"http://127.0.0.1:{httpd.server_port}/api/validation-packs", timeout=5) as response:
            assert response.status == 200
            data = json.loads(response.read().decode("utf-8"))
            assert "packs" in data
            assert len(data["packs"]) == 2

            # Check verdict field exists in each pack
            for pack in data["packs"]:
                assert "recommendation" in pack, f"Pack missing recommendation field: {pack}"
                assert pack["recommendation"] in ("advance", "hold", "reject"), f"Invalid verdict: {pack['recommendation']}"
    finally:
        httpd.shutdown()
        httpd.server_close()
        server.APP_DIR = original_root


def test_dashboard_renders_verdict_filter_and_expandable_packs():
    """Test that the Astro dashboard page contains verdict filter and expandable validation sections."""
    template = Path(ROOT / "src" / "pages" / "index.astro").read_text()
    assert "verdict-filter" in template, "Verdict filter not in index.astro"
    assert "sig-expand" in template, "Expand button not in index.astro"
    assert "sig-validation" in template, "Validation section not in index.astro"
    assert "cycle-clock" in template, "Cycle clock not in index.astro"
    assert "next-cycle" in template, "Next cycle element not in index.astro"
    assert "last-cycle" in template, "Last cycle element not in index.astro"
    assert "data-verdict" in template, "data-verdict attribute not in index.astro"

    # Verdict counting logic lives in the Astro data layer now
    data_layer = Path(ROOT / "src" / "lib" / "data.ts").read_text()
    combined = template + data_layer
    for verdict in ("advance", "hold", "reject"):
        assert verdict in combined, f"verdict '{verdict}' not in Astro sources"


def test_status_endpoint_returns_cycle_timing(tmp_path):
    """Test that /api/status returns next_cycle_in and last_cycle_ago fields."""
    # Set up minimal data
    data = tmp_path / "data"
    data.mkdir(parents=True)
    (tmp_path / "outbox").mkdir(parents=True)

    # cycle count with last_run
    (data / ".cycle_count.json").write_text(json.dumps({
        "count": 46,
        "last_run": "2026-06-10T16:38:19.526790+00:00"
    }))

    # dispatch desk
    desk = {
        "cycle_id": "CYCLE-046",
        "dispatch_count": 13,
        "clusters": [],
        "generated_at": "2026-06-10T16:38:19.526790+00:00"
    }
    (tmp_path / "outbox" / "dispatch_desk.json").write_text(json.dumps(desk))

    # source data
    for key in ["world_bank", "idb", "noaa", "ndbc", "tier2"]:
        d = data / key
        d.mkdir(parents=True)
        (d / "latest.json").write_text(json.dumps({"fetched_at": "2026-06-10T16:38:19.526790+00:00"}))

    # feedback
    (data / "feedback").mkdir(parents=True)
    (data / "feedback" / "state.json").write_text(json.dumps({"history": [], "boosts": {}}))

    # composite
    (data / "composite").mkdir(parents=True)
    (data / "composite" / "latest.json").write_text(json.dumps({"signals": []}))

    # Test status endpoint
    original_root = server.APP_DIR
    server.APP_DIR = tmp_path
    httpd = server.http.server.ThreadingHTTPServer(("127.0.0.1", 0), server.AppHandler)
    import threading
    thread = threading.Thread(target=httpd.serve_forever, daemon=True)
    thread.start()

    try:
        import urllib.request
        with urllib.request.urlopen(f"http://127.0.0.1:{httpd.server_port}/api/status", timeout=5) as response:
            assert response.status == 200
            data = json.loads(response.read().decode("utf-8"))
            assert "next_cycle_in" in data, "Missing next_cycle_in field"
            assert "last_cycle_ago" in data, "Missing last_cycle_ago field"
            assert isinstance(data["next_cycle_in"], (int, type(None))), "next_cycle_in should be int or null"
            assert isinstance(data["last_cycle_ago"], (int, type(None))), "last_cycle_ago should be int or null"
    finally:
        httpd.shutdown()
        httpd.server_close()
        server.APP_DIR = original_root


def test_astro_data_includes_ported_label_cleaners():
    """The Astro data loader owns the label-cleaning rules formerly in dashboard/generate.py."""
    data_source = Path(ROOT / "src" / "lib" / "data.ts").read_text()
    dashboard_path = ROOT / "dist" / "index.html"
    if not dashboard_path.exists():
        pytest.skip("dist/index.html not built — run `pnpm build` first")
    dashboard = dashboard_path.read_text()

    assert "function cleanTitle" in data_source
    assert "function cleanGrade" in data_source
    assert "function cleanEvidence" in data_source
    assert "function cleanSignalTitle" in data_source
    # Lead label is derived at build time from outbox/dispatch_desk.json
    # (clusters[0].country_cluster). The headline must name the lead country,
    # and may only claim consensus when the evidence grade says more than one
    # source corroborates it — a single-source lead gets the weaker phrasing.
    desk = json.loads((ROOT / "outbox" / "dispatch_desk.json").read_text())
    lead = (desk.get("clusters") or [{}])[0]
    lead_country = lead.get("country_cluster", "")
    grade = str(lead.get("evidence_grade", ""))
    assert lead_country, "dispatch_desk.json has no lead cluster"

    corroborated = grade.startswith(("A", "B")) or "source" in grade.lower() and "single" not in grade.lower()
    consensus = f"All signals point to {lead_country}." in dashboard
    watchful = f"{lead_country} is the one to watch." in dashboard
    assert consensus or watchful, (
        f"dashboard should render a lead headline naming {lead_country} (grade={grade})"
    )
    assert not (consensus and not corroborated), (
        f"headline claims consensus for {lead_country} on a single-source grade ({grade})"
    )
    # Lead confidence band must match the grade the desk actually assigned.
    assert ("Solid: several sources agree" in dashboard
            or "Promising: more than one source" in dashboard
            or "Early: one source so far" in dashboard), (
        "dashboard should render the lead's cleaned grade label"
    )
    assert "World Bank" in dashboard
    assert "money on the move" in dashboard


if __name__ == "__main__":
    pytest.main([__file__, "-v"])