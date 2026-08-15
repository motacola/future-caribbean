"""Tests for validation pack v2 — corroboration, registries, freshness."""
import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from packagers.validation_pack_generator import (  # noqa: E402
    build_pack,
    recommend,
    select_lead_dispatches,
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

TENDER = {
    "id": "PROC-2026-00311",
    "title": "RFP for Rehabilitation of Hinterland Airstrips",
    "country": "Guyana",
    "source": "Guyana eProcure (NPTA)",
    "url": "https://eprocure.gov.gy/",
    "published": "2026-02-19",
    "closing_date": "2026-06-23",
    "category": "Works",
}

NEWS = [{
    "title": "Guyana infrastructure and construction investment accelerates",
    "summary": "Major construction projects expand across Guyana energy corridor",
    "url": "https://example.com/guyana-build",
    "source": "Test Feed",
    "countries": ["Guyana"],
}]


def test_build_pack_has_required_fields():
    pack = build_pack(DISPATCH, WB, IDB, TIER2, "2026-06-10T00:00:00+00:00")
    for field in [
        "signal_id", "country", "sector_hypotheses", "supporting_projects",
        "procurement_matches", "credible_local_operators", "relevant_institutions",
        "source_links", "unresolved_questions", "recommended_intro_targets",
        "advance_or_reject_recommendation", "recommendation_reason", "last_validated_at",
        "action_readiness", "evidence_freshness", "cycles_since_refresh", "coordination_path",
    ]:
        assert field in pack, f"missing field: {field}"
    assert pack["country"] == "Guyana"
    assert pack["advance_or_reject_recommendation"] in ("advance", "hold", "reject")


def test_guyana_pack_with_tender_and_news_can_advance():
    pack = build_pack(
        DISPATCH, WB, IDB, TIER2, "2026-06-10T00:00:00+00:00",
        tenders=[TENDER], news_articles=NEWS,
    )
    assert pack["procurement_matches"][0]["match"] == "country"
    assert pack["procurement_matches"][0]["closing_date"] == "2026-06-23"
    assert any(h.get("status") == "corroborated" for h in pack["sector_hypotheses"])
    assert len(pack["credible_local_operators"]) >= 2
    assert pack["advance_or_reject_recommendation"] == "advance"
    assert pack["confidence_score"] <= 100


def test_macro_only_without_tender_stays_hold_or_lower_confidence():
    pack = build_pack(DISPATCH, WB, IDB, TIER2, "2026-06-10T00:00:00+00:00")
    assert pack["confidence_score"] < 100
    assert pack["advance_or_reject_recommendation"] in ("hold", "reject")


def test_pack_preserves_unclamped_ranking_score_separately():
    dispatch = {**DISPATCH, "confidence_score": 100, "confidence_raw": 114}
    pack = build_pack(dispatch, WB, IDB, TIER2, "2026-06-10T00:00:00+00:00")

    assert pack["raw_confidence_score"] == 114
    assert pack["confidence_score"] <= 100


def test_pack_includes_matching_coordination_path():
    path = {
        "trigger_signal_id": DISPATCH["signal_id"],
        "coordination_score": 72,
        "demand_countries": ["Guyana"],
        "contributing_nodes": [{"country": "Barbados", "matched_capabilities": [{"id": "project_finance"}]}],
        "minimum_next_action": "Validate eligibility.",
    }
    pack = build_pack(
        DISPATCH, WB, IDB, TIER2, "2026-06-10T00:00:00+00:00",
        coordination_opportunities=[path],
    )
    assert pack["coordination_path"]["coordination_score"] == 72


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
        return
    index = json.loads(index_path.read_text())
    assert index["packs"], "index exists but lists no packs"
    for entry in index["packs"]:
        pack_file = out_dir / entry["file"]
        assert pack_file.exists(), f"Pack file missing: {entry['file']}"
        pack = json.loads(pack_file.read_text())
        assert pack["advance_or_reject_recommendation"] == entry["recommendation"]
