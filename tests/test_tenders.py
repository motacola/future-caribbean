"""Tests for the tender watcher framework and validation-pack integration."""
import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from watchers.tenders.base import merge_records, validate_record  # noqa: E402
from watchers.tenders.guyana_eprocure import (  # noqa: E402
    GuyanaEprocureAdapter,
    normalize_guyana_record,
    parse_guyana_records,
)
from watchers.tenders.jamaica_gojep import (  # noqa: E402
    JamaicaGojepAdapter,
    parse_award_notices_html,
    parse_gojep_date,
    parse_opened_tenders_html,
)
from packagers.validation_pack_generator import (  # noqa: E402
    apply_freshness_decay,
    build_pack,
    calibrate_confidence,
    corroborate_sector_hypotheses,
    evidence_fingerprint,
    load_operators_from_registry,
    procurement_matches_for,
    unresolved_questions_for,
)

GY_RAW = {
    "project_id": "PROC-2026-00311",
    "project_name": "RFP for Rehabilitation of Hinterland Airstrips",
    "agency": "34-Ministry of Public Utilities and Aviation",
    "procurement_method": "Open Tendered",
    "procurement_nature": "Works",
    "current_state": "Bid Advertised",
    "advertisement_date": "2026-02-19",
    "actual_bid_opening_date": None,
    "projected_bid_opening_date": "2026-06-16",
}

GY_PAYLOAD = {"message": [GY_RAW]}


def test_normalize_guyana_schema():
    n = normalize_guyana_record(GY_RAW)
    assert n["id"] == "PROC-2026-00311"
    assert n["country"] == "Guyana"
    assert n["closing_date"] == "2026-06-16"
    assert n["published"] == "2026-02-19"
    for key in ("title", "source", "url", "category", "fetched_at"):
        assert key in n


def test_parse_guyana_fixture():
    records = parse_guyana_records(GY_PAYLOAD)
    assert len(records) == 1
    assert validate_record(records[0])


def test_merge_dedupes_adapters():
    class A:
        slug = "a"
        def fetch(self):
            return [normalize_guyana_record(GY_RAW)]

    class B:
        slug = "b"
        def fetch(self):
            return [normalize_guyana_record(GY_RAW)]

    merged = merge_records([A(), B()])
    assert len(merged) == 1


def test_jamaica_parse_opened_fixture():
    fixture = ROOT / "tests" / "fixtures" / "gojep-opened-snippet.html"
    html = fixture.read_text(encoding="utf-8")
    records = parse_opened_tenders_html(html)
    assert records
    assert records[0]["country"] == "Jamaica"
    assert records[0]["title"]
    assert records[0]["closing_date"] == "2026-06-17"


def test_jamaica_gojep_date_parser():
    assert parse_gojep_date("Wed Jun 17 11:00:00 COT 2026") == "2026-06-17"


def test_jamaica_live_adapter_when_network_available():
    records = JamaicaGojepAdapter().fetch()
    # Live GOJEP opened-bids page is reachable via plain HTTP as of 2026-06.
    assert isinstance(records, list)


def test_country_tenders_rank_first():
    tier2 = [{"item_type": "procurement", "title": "Belize Quality Infrastructure",
              "description": "", "source": "CDB", "url": "https://caribank.org/p"}]
    tenders = [normalize_guyana_record(GY_RAW)]
    matches = procurement_matches_for("Guyana", tier2, tenders)
    assert matches[0]["match"] == "country"
    assert matches[0]["closing_date"] == "2026-06-16"
    assert any(m["match"] == "regional" for m in matches)


def test_dated_tender_flips_unresolved_question():
    tenders = [normalize_guyana_record(GY_RAW)]
    matches = procurement_matches_for("Guyana", [], tenders)
    qs = unresolved_questions_for("Guyana", [], matches, [])
    assert any("Tender closes 2026-06-16" in q for q in qs)
    assert not any("No live Guyana-specific procurement notice" in q for q in qs)


def test_no_fabrication_when_no_tenders():
    matches = procurement_matches_for("Jamaica", [], [])
    assert matches == []
    qs = unresolved_questions_for("Jamaica", [], [], [])
    assert any("No live Jamaica-specific procurement notice" in q for q in qs)


def test_registry_operators_guyana():
    ops = load_operators_from_registry("Guyana")
    assert len(ops) >= 2
    assert all(op.get("name") and op.get("source_url") for op in ops)


def test_registry_operators_svg_and_barbados():
    for country in ("St. Vincent and the Grenadines", "Barbados"):
        ops = load_operators_from_registry(country)
        assert len(ops) >= 2, country
        assert all(op.get("name") and op.get("source_url") for op in ops)


def test_corroborate_sector_from_news():
    hyps = [{
        "sector": "Oil & gas and offshore support services",
        "basis": "prior",
        "status": "unconfirmed",
    }]
    articles = [{
        "title": "Guyana offshore oil infrastructure investment expands",
        "summary": "New energy sector projects announced in Guyana",
        "url": "https://example.com/guyana-oil",
        "source": "Test News",
        "countries": ["Guyana"],
    }]
    out = corroborate_sector_hypotheses(hyps, articles, "Guyana")
    assert out[0]["status"] == "corroborated"
    assert "example.com" in out[0]["url"]


def test_freshness_decay_downgrades_advance():
    pack = {
        "advance_or_reject_recommendation": "advance",
        "recommendation_reason": "test",
        "sector_hypotheses": [{"status": "corroborated", "sector": "Oil", "url": "https://example.com"}],
        "procurement_matches": [],
        "credible_local_operators": [],
    }
    fp = evidence_fingerprint(pack)
    previous = {"evidence_fingerprint": fp, "stale_cycles": 1}
    out = apply_freshness_decay(pack, previous, "2026-06-18T00:00:00+00:00")
    assert out["advance_or_reject_recommendation"] == "hold"
    assert out["cycles_since_refresh"] == 2


def test_calibrate_confidence_caps_macro_only():
    hyps = [{"sector": "FDI", "status": "macro_signal"}]
    conf, readiness = calibrate_confidence(100, hyps, [], [{"indicator_code": "BX.KLT.DINV.CD.WD"}])
    assert conf <= 68
    assert "low" in readiness or "medium" in readiness
