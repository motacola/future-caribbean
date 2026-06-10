"""Tests for the Opportunity Validation Pack generator."""
import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from packagers.validation_pack_generator import (  # noqa: E402
    build_pack, recommend, select_lead_dispatches,
)

DISPATCH = {
    "signal_id": "enhanced-invest-guyana",
    "dispatch_id": "DSP-TEST-001",
    "country_cluster": "Guyana",
    "title": "Guyana: +860.3% multi-source capital surge",
    "confidence_score": 100,
    "evidence_grade": "A - multi-source",
}

WB = {
    "observations": [
        {
            "country_name": "Guyana",
            "indicator_code": "BX.KLT.DINV.CD.WD",
            "indicator_label": "FDI net inflows",
            "delta_pct": 860.3,
            "previous_year": 2023,
            "year": 2024,
        }
    ]
}

IDB = {
    "datasets": [
        {"title": "Productivity Survey Guyana", "description": "", "url": "https://data.iadb.org/x", "topics": ["economy"]},
        {"title": "Unrelated Brazil dataset", "description": "", "url": "https://data.iadb.org/y", "topics": []},
    ]
}

TIER2 = {
    "items": [
        {"item_type": "country_data", "title": "Guyana Value added|GDP by industries", "description": "", "source": "CARICOM Statistics", "url": "https://statistics.caricom.org/g"},
        {"item_type": "procurement", "title": "Belize Quality Infrastructure", "description": "", "source": "CDB", "url": "https://caribank.org/p"},
    ]
}


def test_build_pack_has_required_fields():
    pack = build_pack(DISPATCH, WB, IDB, TIER2, "2026-06-10T00:00:00+00:00")
    for field in [
        "signal_id", "country", "sector_hypotheses", "supporting_projects",
        "procurement_matches", "credible_local_operators", "relevant_institutions",
        "source_links", "unresolved_questions", "recommended_intro_targets",
        "advance_or_reject_recommendation", "recommendation_reason", "last_validated_at",
    ]:
        assert field in pack, f"missing field: {field}"
    assert pack["country"] == "Guyana"
    assert pack["advance_or_reject_recommendation"] in ("advance", "hold", "reject")


def test_guyana_pack_advances_with_evidence():
    pack = build_pack(DISPATCH, WB, IDB, TIER2, "2026-06-10T00:00:00+00:00")
    assert pack["advance_or_reject_recommendation"] == "advance"
    # Country-matched project found, Brazil dataset excluded
    titles = [p["title"] for p in pack["supporting_projects"]]
    assert "Productivity Survey Guyana" in titles
    assert "Unrelated Brazil dataset" not in titles
    # Regional procurement carried with explicit non-country tag
    assert pack["procurement_matches"][0]["match"] == "regional"
    # GDP-by-industry dataset surfaces as a verifiable sector basis
    assert any(h.get("status") == "data_available" for h in pack["sector_hypotheses"])
    # Operators are never fabricated
    assert pack["credible_local_operators"] == []
    assert any("operator" in q.lower() for q in pack["unresolved_questions"])


def test_low_confidence_no_evidence_rejects():
    decision, reason = recommend(20, [], [], [], [])
    assert decision == "reject"
    assert reason


def test_select_lead_dispatches_dedupes_by_signal():
    dispatches = [
        {"signal_id": "a", "confidence_score": 50},
        {"signal_id": "a", "confidence_score": 90},
        {"signal_id": "b", "confidence_score": 70},
    ]
    leads = select_lead_dispatches(dispatches)
    assert [d["signal_id"] for d in leads] == ["a", "b"]
    assert leads[0]["confidence_score"] == 90


def test_generated_pack_files_are_valid_json():
    out_dir = ROOT / "outbox" / "validation_packs"
    index_path = out_dir / "index.json"
    if not index_path.exists():
        return  # generator has not run in this checkout
    index = json.loads(index_path.read_text())
    assert index["packs"], "index exists but lists no packs"
    for entry in index["packs"]:
        pack = json.loads((out_dir / entry["file"]).read_text())
        assert pack["advance_or_reject_recommendation"] == entry["recommendation"]
