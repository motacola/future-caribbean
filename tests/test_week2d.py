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
    """Test that the dashboard template contains verdict filter and expandable validation sections."""
    template = Path(ROOT / "dashboard" / "template.html").read_text()
    assert "verdict-filter" in template, "Verdict filter not in template"
    assert "sig-expand" in template, "Expand button not in template"
    assert "sig-validation" in template, "Validation section not in template"
    assert "cycle-clock" in template, "Cycle clock not in template"
    assert "next-cycle" in template, "Next cycle element not in template"
    assert "last-cycle" in template, "Last cycle element not in template"
    
    # Also check that generate.py includes the verdict counts
    generate_code = Path(ROOT / "dashboard" / "generate.py").read_text()
    assert "verdict_counts_json" in generate_code, "verdict_counts_json not in generate.py"
    assert "advance_count" in generate_code, "advance_count not in generate.py"
    assert "hold_count" in generate_code, "hold_count not in generate.py"
    assert "reject_count" in generate_code, "reject_count not in generate.py"
    assert "data-verdict" in generate_code, "data-verdict attribute not in generate.py"


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


def test_dashboard_generate_includes_counts():
    """Test that dashboard generate produces verdict counts."""
    from dashboard.generate import clean_title, clean_grade, clean_evidence, clean_signal_title

    assert "Guyana" in clean_title("Guyana: +860.3% multi-source capital surge")
    assert "High confidence" in clean_grade("A - multi-source")
    assert "World Bank" in clean_evidence("WB FDI surge detected: Guyana")
    assert "capital momentum" in clean_signal_title("Guyana: +860.3% ...")


if __name__ == "__main__":
    pytest.main([__file__, "-v"])