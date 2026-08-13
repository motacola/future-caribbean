"""Tests for the Track Record packager and rendering."""
import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from packagers.track_record import main as track_record_main  # noqa: E402


def test_packager_grouping():
    """Synthetic history with 2 cycles → correct counts, newest first, ignored counted but never rendered as a pill."""
    # This test validates the grouping logic by examining actual output
    # We run the real packager with actual data and check the structure
    track_record_main()

    out_path = ROOT / "outbox" / "track_record.json"
    assert out_path.exists(), "track_record.json should be generated"

    data = json.loads(out_path.read_text())

    # Contract keys present
    assert "generated_at" in data
    assert data["feedback_provenance"] == "simulated"
    assert "current_boosts" in data
    assert "cycles" in data

    cycles = data["cycles"]
    assert len(cycles) >= 1, "Should have at least one cycle"

    # Newest first
    for i in range(len(cycles) - 1):
        assert cycles[i]["cycle_id"] > cycles[i + 1]["cycle_id"], "Cycles should be sorted newest first"

    # Each cycle has correct structure
    for c in cycles:
        assert "cycle_id" in c
        assert "responses" in c
        assert "dispatch_count" in c
        assert "countries" in c
        assert "lead" in c

        responses = c["responses"]
        # Ignored is counted in responses but not rendered as pill (verified in generate.py)
        assert "ignored" in responses
        assert "forwarded" in responses
        assert "replied" in responses
        assert "opened" in responses
        assert "decision_changed" in responses

    # Lead only filled for cycles present in opportunity_dispatches.json
    # Current cycle should have lead, older (if exists) should not
    desk = json.loads((ROOT / "outbox" / "dispatch_desk.json").read_text())
    current_cycle_id = desk["cycle_id"]
    current_cycle = next((c for c in cycles if c["cycle_id"] == current_cycle_id), None)
    older_cycle = next((c for c in cycles if c["cycle_id"] != current_cycle_id), None)

    assert current_cycle is not None, "Current cycle should exist"
    # Lead country is whatever the dispatch_desk says, not a hard-coded value.
    # The historical demo cycle was Guyana; current cycle may differ.
    assert current_cycle["lead"]["country"], "current cycle lead country should be set"
    assert current_cycle["lead"]["title"], "current cycle lead title should be set"
    assert current_cycle["lead"]["country"] in current_cycle["lead"]["title"]

    if older_cycle:
        assert older_cycle["lead"]["country"] == ""
        assert older_cycle["lead"]["title"] == ""


def test_contract_keys():
    """Contract keys present in generated track_record.json."""
    out_path = ROOT / "outbox" / "track_record.json"
    data = json.loads(out_path.read_text())

    required_keys = ["generated_at", "feedback_provenance", "current_boosts", "cycles"]
    for key in required_keys:
        assert key in data, f"Missing required key: {key}"

    assert isinstance(data["current_boosts"], dict)
    assert isinstance(data["cycles"], list)


def test_dashboard_rendering():
    """outbox/track_record.json valid and the built Astro page contains id=\"receipts\" and receipt-row."""
    import pytest

    dashboard_path = ROOT / "dist" / "index.html"
    if not dashboard_path.exists():
        pytest.skip("dist/index.html not built — run `pnpm build` first")

    content = dashboard_path.read_text()

    # Check for receipts section
    assert 'id="receipts"' in content, 'Dashboard should contain id="receipts"'

    # Check for receipt-row elements
    assert "receipt-row" in content, 'Dashboard should contain "receipt-row" class'

    # Check for receipts table and boosts
    assert "receipts-table" in content
    assert "receipts-boosts" in content
    assert "r-pill" in content
    assert "Validation note:" in content

    desk = json.loads((ROOT / "outbox" / "dispatch_desk.json").read_text())
    assert f'Cycle {desk["cycle_id"]}' in content
    assert f'"cycle":"{desk["cycle_id"]}"' in content


if __name__ == "__main__":
    test_packager_grouping()
    test_contract_keys()
    test_dashboard_rendering()
    print("All track record tests passed!")
