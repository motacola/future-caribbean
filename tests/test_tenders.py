"""Tests for the tender watcher and its validation-pack integration."""
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from watchers.tenders_poller import normalize_guyana  # noqa: E402
from packagers.validation_pack_generator import (  # noqa: E402
    procurement_matches_for, unresolved_questions_for,
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


def test_normalize_guyana_schema():
    n = normalize_guyana(GY_RAW)
    assert n["id"] == "PROC-2026-00311"
    assert n["country"] == "Guyana"
    assert n["closing_date"] == "2026-06-16"
    assert n["published"] == "2026-02-19"
    for key in ("title", "source", "url", "category"):
        assert key in n


def test_country_tenders_rank_first():
    tier2 = [{"item_type": "procurement", "title": "Belize Quality Infrastructure",
              "description": "", "source": "CDB", "url": "https://caribank.org/p"}]
    tenders = [normalize_guyana(GY_RAW)]
    matches = procurement_matches_for("Guyana", tier2, tenders)
    assert matches[0]["match"] == "country"
    assert matches[0]["closing_date"] == "2026-06-16"
    # regional CDB item still present, after the live tender
    assert any(m["match"] == "regional" for m in matches)


def test_dated_tender_flips_unresolved_question():
    tenders = [normalize_guyana(GY_RAW)]
    matches = procurement_matches_for("Guyana", [], tenders)
    qs = unresolved_questions_for("Guyana", [], matches, [])
    assert any("Tender closes 2026-06-16" in q for q in qs)
    assert not any("No live Guyana-specific procurement notice" in q for q in qs)


def test_no_fabrication_when_no_tenders():
    matches = procurement_matches_for("Jamaica", [], [])
    assert matches == []
    qs = unresolved_questions_for("Jamaica", [], [], [])
    assert any("No live Jamaica-specific procurement notice" in q for q in qs)
