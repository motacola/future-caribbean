"""Procurement Outcome Resolver contracts.

The product claim these tests protect: Signal Fabric detected a tender
before close and later recorded what happened to it. That claim is only
worth something if amendments and awards attach to the tender that was
detected, a missing award stays missing, and a source is never allowed to
corroborate itself.

Contract numbering follows CLAUDE_HANDOVER_2026-08-15 §6.
"""
from __future__ import annotations

import json
from datetime import date
from pathlib import Path

import pytest

from packagers import procurement_outcomes as pub
from resolvers import procurement as proc

ROOT = Path(__file__).resolve().parents[1]


def _notice(title, *, agency="Ministry of Works", country="Jamaica",
            source="Jamaica GOJEP (opened bids)", status="Bid submission",
            closing=None, ref="REF-1", published=None, url="https://portal/x",
            **extra):
    rec = {
        "id": ref, "title": title, "country": country, "agency": agency,
        "source": source, "url": url, "status": status,
        "closing_date": closing, "published": published,
        "category": "Open", "method": "Open",
    }
    rec.update(extra)
    return rec


def _award(title, **kw):
    kw.setdefault("source", "Jamaica GOJEP (contract award)")
    kw.setdefault("status", "awarded")
    kw.setdefault("ref", f"award-{title[:60]}")
    return _notice(title, **kw)


# ── identity (contract 5) ───────────────────────────────────────────────

def test_identity_survives_the_formatting_differences_between_feeds():
    """An award notice and its opened-bid record must land on the same
    tender. GOJEP award notices carry no reference id, so title+buyer is
    the only join available."""
    opened = proc.canonical_id("Jamaica", "Ministry of Works", "Supply of Two (2) Generators")
    award = proc.canonical_id("jamaica", "Ministry of Works ", "supply of two (2)  generators")
    assert opened == award


def test_identity_separates_genuinely_different_tenders():
    a = proc.canonical_id("Guyana", "NPTA", "Rehabilitation of Hinterland Airstrips Lots 1-4")
    b = proc.canonical_id("Guyana", "NPTA", "Code 4E Municipal Airport at Lethem")
    assert a != b


def test_identity_separates_same_title_from_different_buyers():
    a = proc.canonical_id("Jamaica", "Ministry of Health", "Supply of Printers")
    b = proc.canonical_id("Jamaica", "Ministry of Works", "Supply of Printers")
    assert a != b


def test_identity_is_stable_across_runs():
    args = ("Jamaica", "Ministry of Works", "Supply of Printers")
    assert proc.canonical_id(*args) == proc.canonical_id(*args)


# ── amendments attach to the original tender (contract 1) ───────────────

def test_closing_date_change_is_an_amendment_not_a_new_tender():
    title = "Procurement of Refreshment"
    corpus = proc.observe([_notice(title, closing="2026-07-03")], observed_at="2026-07-01T00:00:00+00:00")
    corpus = proc.observe([_notice(title, closing="2026-07-13")], corpus, observed_at="2026-07-13T00:00:00+00:00")

    assert len(corpus["tenders"]) == 1
    entry = next(iter(corpus["tenders"].values()))
    assert entry["original_closing_date"] == "2026-07-03"
    assert entry["current_closing_date"] == "2026-07-13"
    assert len(entry["amendments"]) == 1
    assert entry["amendments"][0]["from"] == "2026-07-03"
    assert entry["amendments"][0]["to"] == "2026-07-13"


def test_award_attaches_to_the_tender_that_was_detected():
    title = "Supply and Delivery of Kyocera Printer"
    corpus = proc.observe([_notice(title, closing="2026-07-03")], observed_at="2026-06-20T00:00:00+00:00")
    corpus = proc.observe([_award(title, published="2026-07-24")], corpus, observed_at="2026-07-24T00:00:00+00:00")

    assert len(corpus["tenders"]) == 1, "an award must not create a second opportunity"
    entry = next(iter(corpus["tenders"].values()))
    assert entry["lifecycle_state"] == proc.STATE_AWARDED
    assert entry["resolution"]["resolved_at"] == "2026-07-24"
    assert entry["resolution"]["resolves_prior_detection"] is True


def test_award_and_detection_in_the_same_batch_still_link():
    title = "Provision of Fans"
    corpus = proc.observe(
        [_award(title, published="2026-07-10"), _notice(title, closing="2026-06-30")],
        observed_at="2026-07-10T00:00:00+00:00",
    )
    assert len(corpus["tenders"]) == 1


# ── never infer a winner (contract 2) ───────────────────────────────────

def test_supplier_and_value_stay_null_when_the_source_does_not_state_them():
    title = "350 KVA Standby Generator"
    corpus = proc.observe([_notice(title, closing="2026-07-01")], observed_at="2026-06-01T00:00:00+00:00")
    corpus = proc.observe([_award(title)], corpus, observed_at="2026-07-20T00:00:00+00:00")
    res = next(iter(corpus["tenders"].values()))["resolution"]
    assert res["supplier"] is None
    assert res["award_value"] is None


def test_supplier_is_recorded_when_a_source_does_state_it():
    title = "Consultancy Services"
    corpus = proc.observe(
        [_award(title, supplier="Acme Ltd", award_value=125000, award_currency="JMD")],
        observed_at="2026-07-20T00:00:00+00:00",
    )
    res = next(iter(corpus["tenders"].values()))["resolution"]
    assert res["supplier"] == "Acme Ltd"
    assert res["award_value"] == 125000


def test_closed_tender_without_an_award_is_not_quietly_awarded():
    corpus = proc.observe(
        [_notice("Supply of Desks", closing="2026-07-01", status="Evaluation")],
        observed_at="2026-07-02T00:00:00+00:00",
        today=date(2026, 7, 10),
    )
    entry = next(iter(corpus["tenders"].values()))
    assert entry["lifecycle_state"] == proc.STATE_CLOSED
    assert entry["resolution"] is None


def test_a_closed_tender_ages_into_unresolved_rather_than_staying_closed():
    corpus = proc.observe(
        [_notice("Supply of Desks", closing="2026-01-05", status="Evaluation")],
        observed_at="2026-01-06T00:00:00+00:00",
        today=date(2026, 1, 7),
    )
    proc.refresh(corpus, today=date(2026, 12, 1))
    assert next(iter(corpus["tenders"].values()))["lifecycle_state"] == proc.STATE_UNRESOLVED


# ── independence (contracts 3, 10) ──────────────────────────────────────

def test_a_source_cannot_resolve_its_own_claim():
    assert proc.classify_independence(
        ["Jamaica GOJEP (opened bids)"], "Jamaica GOJEP (opened bids)"
    ) == "same_source"


def test_the_same_portal_is_not_independent_corroboration():
    """GOJEP's award listing is a different feed but the same publisher as
    its opened-bid listing. Reporting that as independent would overstate
    the evidence."""
    assert proc.classify_independence(
        ["Jamaica GOJEP (opened bids)"], "Jamaica GOJEP (contract award)"
    ) == "same_publisher"


def test_a_different_publisher_is_independent():
    assert proc.classify_independence(
        ["Jamaica GOJEP (opened bids)"], "Ministry of Finance Contracts Register"
    ) == "independent"


def test_an_award_for_an_undetected_tender_is_not_independence():
    """Absence of a prediction is not corroboration of one."""
    assert proc.classify_independence([], "Jamaica GOJEP (contract award)") == "no_prior_detection"


# ── determinism and non-destructiveness (contracts 5, 7) ────────────────

def test_input_order_does_not_change_the_corpus():
    records = [
        _notice("Supply of Chairs", closing="2026-07-01", ref="A"),
        _notice("Supply of Desks", closing="2026-07-05", ref="B"),
        _award("Supply of Chairs", published="2026-07-20"),
    ]
    a = proc.observe(list(records), observed_at="2026-07-20T00:00:00+00:00", today=date(2026, 7, 21))
    b = proc.observe(list(reversed(records)), observed_at="2026-07-20T00:00:00+00:00", today=date(2026, 7, 21))
    assert json.dumps(a, sort_keys=True) == json.dumps(b, sort_keys=True)


def test_re_observing_the_same_snapshot_is_idempotent():
    records = [_notice("Supply of Chairs", closing="2026-07-01")]
    corpus = proc.observe(records, observed_at="2026-06-20T00:00:00+00:00")
    before = json.dumps(corpus, sort_keys=True)
    corpus = proc.observe(records, corpus, observed_at="2026-06-20T00:00:00+00:00")
    assert json.dumps(corpus, sort_keys=True) == before


def test_first_detection_is_never_overwritten_by_a_later_sighting():
    title = "Supply of Chairs"
    corpus = proc.observe([_notice(title, closing="2026-07-01")], observed_at="2026-06-01T00:00:00+00:00")
    corpus = proc.observe([_notice(title, closing="2026-07-01")], corpus, observed_at="2026-06-25T00:00:00+00:00")
    entry = next(iter(corpus["tenders"].values()))
    assert entry["first_detected_at"].startswith("2026-06-01")
    assert entry["last_seen_at"].startswith("2026-06-25")


def test_a_second_award_notice_does_not_rewrite_the_first_outcome():
    title = "Supply of Chairs"
    corpus = proc.observe([_notice(title, closing="2026-07-01")], observed_at="2026-06-01T00:00:00+00:00")
    corpus = proc.observe([_award(title, published="2026-07-10")], corpus, observed_at="2026-07-10T00:00:00+00:00")
    corpus = proc.observe([_award(title, published="2026-08-30")], corpus, observed_at="2026-08-30T00:00:00+00:00")
    assert next(iter(corpus["tenders"].values()))["resolution"]["resolved_at"] == "2026-07-10"


def test_raw_notices_are_preserved_as_receipts():
    title = "Supply of Chairs"
    corpus = proc.observe([_notice(title, closing="2026-07-01")], observed_at="2026-06-01T00:00:00+00:00")
    corpus = proc.observe([_notice(title, closing="2026-07-09")], corpus, observed_at="2026-06-20T00:00:00+00:00")
    entry = next(iter(corpus["tenders"].values()))
    assert len(entry["notices"]) == 2
    assert {n["closing_date"] for n in entry["notices"]} == {"2026-07-01", "2026-07-09"}


# ── lead time (contract 4) ──────────────────────────────────────────────

def test_lead_time_is_measured_from_first_detection_to_close():
    corpus = proc.observe(
        [_notice("Supply of Chairs", closing="2026-07-15")],
        observed_at="2026-06-15T00:00:00+00:00",
        today=date(2026, 6, 16),
    )
    entry = next(iter(corpus["tenders"].values()))
    assert entry["lead_time_days"] == 30
    assert entry["detected_before_close"] is True


def test_detection_after_close_is_reported_as_such():
    """GOJEP's opened-bid feed lists tenders whose bids are already open.
    Those must not be presented as early detections."""
    corpus = proc.observe(
        [_notice("Supply of Chairs", closing="2026-06-01")],
        observed_at="2026-06-10T00:00:00+00:00",
        today=date(2026, 6, 11),
    )
    entry = next(iter(corpus["tenders"].values()))
    assert entry["lead_time_days"] == -9
    assert entry["detected_before_close"] is False


# ── malformed and edge fixtures ─────────────────────────────────────────

def test_records_without_a_title_are_dropped():
    corpus = proc.observe([_notice(""), _notice("Real Tender", closing="2026-07-01")],
                          observed_at="2026-06-01T00:00:00+00:00")
    assert len(corpus["tenders"]) == 1


def test_unparseable_dates_do_not_crash_the_resolver():
    corpus = proc.observe([_notice("Supply of Chairs", closing="not-a-date")],
                          observed_at="2026-06-01T00:00:00+00:00")
    entry = next(iter(corpus["tenders"].values()))
    assert entry["lead_time_days"] is None
    assert entry["detected_before_close"] is None


def test_an_unrecognized_portal_status_does_not_invent_a_lifecycle():
    corpus = proc.observe([_notice("Supply of Chairs", status="Under Review Phase 2")],
                          observed_at="2026-06-01T00:00:00+00:00")
    assert next(iter(corpus["tenders"].values()))["lifecycle_state"] == proc.STATE_DETECTED


def test_cancellation_is_a_terminal_outcome_not_an_award():
    title = "Supply of Chairs"
    corpus = proc.observe([_notice(title, closing="2026-07-01")], observed_at="2026-06-01T00:00:00+00:00")
    corpus = proc.observe([_notice(title, status="Cancelled", source="Jamaica GOJEP (cancellation)")],
                          corpus, observed_at="2026-07-05T00:00:00+00:00")
    entry = next(iter(corpus["tenders"].values()))
    assert entry["lifecycle_state"] == proc.STATE_CANCELLED
    assert entry["resolution"]["state"] == proc.STATE_CANCELLED


# ── published view ──────────────────────────────────────────────────────

def test_published_summary_does_not_overstate_independence():
    corpus = proc.observe([_notice("Supply of Chairs", closing="2026-07-01")], observed_at="2026-06-01T00:00:00+00:00")
    corpus = proc.observe([_award("Supply of Chairs", published="2026-07-10")], corpus, observed_at="2026-07-10T00:00:00+00:00")
    payload = pub.build(corpus)
    assert payload["summary"]["resolved_outcomes"] == 1
    assert payload["summary"]["outcomes_resolving_a_prior_detection"] == 1
    assert payload["summary"]["independently_resolved"] == 0
    assert payload["summary"]["resolution_independence"] == {"same_publisher": 1}


def test_published_view_keeps_citations():
    corpus = proc.observe([_notice("Supply of Chairs", closing="2026-07-01", url="https://portal/abc")],
                          observed_at="2026-06-01T00:00:00+00:00")
    entry = pub.build(corpus)["tenders"][0]
    assert entry["urls"] == ["https://portal/abc"]
    assert entry["generating_sources"] == ["Jamaica GOJEP (opened bids)"]
    assert entry["notice_count"] == 1


def test_published_view_counts_unnamed_suppliers_explicitly():
    corpus = proc.observe([_award("Supply of Chairs", published="2026-07-10")], observed_at="2026-07-10T00:00:00+00:00")
    s = pub.build(corpus)["summary"]
    assert s["outcomes_with_named_supplier"] == 0
    assert s["outcomes_without_named_supplier"] == 1


# ── the shipped corpus ──────────────────────────────────────────────────

def test_shipped_corpus_has_no_duplicate_canonical_ids():
    corpus = proc.load_corpus()
    if not corpus.get("tenders"):
        pytest.skip("canonical corpus not built yet")
    ids = list(corpus["tenders"])
    assert len(ids) == len(set(ids))
    for tid, entry in corpus["tenders"].items():
        assert entry["tender_id"] == tid


def test_shipped_corpus_normalizes_at_least_ten_tenders():
    corpus = proc.load_corpus()
    if not corpus.get("tenders"):
        pytest.skip("canonical corpus not built yet")
    assert len(corpus["tenders"]) >= 10


def test_shipped_corpus_never_publishes_a_circular_resolution():
    """Contract 10, checked against the real corpus rather than fixtures."""
    corpus = proc.load_corpus()
    if not corpus.get("tenders"):
        pytest.skip("canonical corpus not built yet")
    for entry in corpus["tenders"].values():
        res = entry.get("resolution")
        if not res:
            continue
        assert res["independence"] != "same_source", (
            f"{entry['tender_id']} is resolved by the source that generated it"
        )


# ── HTTP surface ────────────────────────────────────────────────────────

def _load_endpoint():
    import importlib.util
    spec = importlib.util.spec_from_file_location("procurement_outcomes_api", ROOT / "api" / "procurement-outcomes.py")
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    return mod


def test_endpoint_serves_the_same_artefact_the_page_reads():
    """Acceptance check: the API and the page must render the same
    canonical records, so they read one file, not two."""
    api = _load_endpoint()
    page_source = (ROOT / "src" / "pages" / "opportunity-resolution.astro").read_text()
    for path in api.CANDIDATES:
        assert path.name in page_source, f"page does not read {path.name}"


def test_endpoint_filters_by_country_state_and_resolution():
    api = _load_endpoint()
    tenders = [
        {"country": "Guyana", "lifecycle_state": "closed", "resolution": None},
        {"country": "Jamaica", "lifecycle_state": "awarded", "resolution": {"state": "awarded"}},
    ]
    assert len(api.filter_tenders(tenders, {"country": ["Guyana"]})) == 1
    assert len(api.filter_tenders(tenders, {"state": ["awarded"]})) == 1
    assert len(api.filter_tenders(tenders, {"resolved": ["true"]})) == 1
    assert len(api.filter_tenders(tenders, {"country": ["Guyana"], "resolved": ["true"]})) == 0


def test_endpoint_limit_is_bounded_and_survives_junk():
    api = _load_endpoint()
    assert api._int_param({"limit": ["9999"]}, "limit", 100, 500) == 500
    assert api._int_param({"limit": ["not-a-number"]}, "limit", 100, 500) == 100
    assert api._int_param({}, "limit", 100, 500) == 100


def test_endpoint_is_registered_in_the_tool_manifest():
    from api_manifest import TOOLS_MANIFEST
    paths = {t["path"] for t in TOOLS_MANIFEST["tools"]}
    assert "/api/procurement-outcomes" in paths


def test_published_artefact_matches_the_corpus():
    corpus = proc.load_corpus()
    published = ROOT / "outbox" / "procurement_outcomes.json"
    if not corpus.get("tenders") or not published.exists():
        pytest.skip("corpus or published view not built yet")
    payload = json.loads(published.read_text())
    assert payload["summary"]["tenders"] == len(corpus["tenders"])
    assert {t["tender_id"] for t in payload["tenders"]} == set(corpus["tenders"])


# ── second publisher: IDB ───────────────────────────────────────────────

IDB_CSV = (
    "noticeid,type,countryname,projectnumber,proyecturl,loannumber,noticetitle,ezshareid,"
    "documenturl,projectname,publicationyear,publicationdate,deadline,sector,sectorenglnm,"
    "projectstatus,procurement_id,process_id,category_nm,prcrmnt_mthd_engl_nm,process_nm,process_desc\n"
    "1,SPECIFIC,GUYANA,GY-L1081,https://p/1,GY-L1081,Upgrade of the East Bank Public Road,EZ-1,"
    "https://doc/1,Road Programme,2026,2026-06-09T00:00,7/21/2026,NULL,TRANSPORTATION,NULL,NULL,NULL,NULL,ICB,NULL,NULL\n"
    "2,AWARD,GUYANA,GY-L1081,https://p/1,GY-L1081,Upgrade of the East Bank Public Road,EZ-2,"
    "https://doc/2,Road Programme,2026,2026-08-01T00:00,NULL,NULL,TRANSPORTATION,NULL,NULL,NULL,NULL,ICB,NULL,NULL\n"
    "3,GENERAL,GUYANA,GY-L1081,https://p/1,GY-L1081,General Procurement Notice,EZ-3,"
    "https://doc/3,Road Programme,2026,2026-05-01T00:00,NULL,NULL,TRANSPORTATION,NULL,NULL,NULL,NULL,NULL,NULL,NULL\n"
    "4,SPECIFIC,URUGUAY,UR-L1174,https://p/4,UR-L1174,Out of region,EZ-4,"
    "https://doc/4,Other,2026,2026-06-01T00:00,7/1/2026,NULL,NULL,NULL,NULL,NULL,NULL,ICB,NULL,NULL\n"
    "5,SPECIFIC,GUYANA,GY-OLD,https://p/5,GY-OLD,Ancient notice nobody can resolve,EZ-5,"
    "https://doc/5,Old Programme,2012,2012-06-01T00:00,7/1/2012,NULL,NULL,NULL,NULL,NULL,NULL,ICB,NULL,NULL\n"
)


def test_idb_parser_splits_opportunities_from_outcomes():
    from watchers.tenders.idb_procurement import AWARD_SOURCE, NOTICE_SOURCE, parse_idb_notices
    recs = parse_idb_notices(IDB_CSV)
    by_source = {r["source"] for r in recs}
    assert by_source == {NOTICE_SOURCE, AWARD_SOURCE}
    notice = next(r for r in recs if r["source"] == NOTICE_SOURCE)
    assert notice["closing_date"] == "2026-07-21", "M/D/YYYY deadline must parse"
    assert notice["country"] == "Guyana"
    award = next(r for r in recs if r["source"] == AWARD_SOURCE)
    assert award["status"] == "awarded"


def test_idb_parser_drops_out_of_region_and_programme_level_notices():
    from watchers.tenders.idb_procurement import parse_idb_notices
    titles = {r["title"] for r in parse_idb_notices(IDB_CSV)}
    assert "Out of region" not in titles, "Caribbean-only scope"
    assert "General Procurement Notice" not in titles, "programme notices are not tenders"


def test_idb_parser_drops_programme_notices_even_when_typed_as_specific():
    """One such row typed itself SPECIFIC and carried its loan operation's
    horizon as a deadline, producing a 1,032-day detection lead time."""
    from watchers.tenders.idb_procurement import parse_idb_notices
    csv_text = IDB_CSV + (
        "6,SPECIFIC,SURINAME,SU-L1,https://p/6,SU-L1,General Procurement Notice - Urban Rehabilitation,EZ-6,"
        "https://doc/6,Urban Programme,2026,2026-06-01T00:00,6/17/2029,NULL,NULL,NULL,NULL,NULL,NULL,ICB,NULL,NULL\n"
    )
    titles = {r["title"] for r in parse_idb_notices(csv_text)}
    assert not any(t.lower().startswith("general procurement notice") for t in titles)


def test_idb_parser_drops_notices_older_than_the_recency_window():
    """A 2012 notice can never be resolved by this desk; keeping it would
    only pad the corpus with permanent `unresolved` records."""
    from watchers.tenders.idb_procurement import parse_idb_notices
    titles = {r["title"] for r in parse_idb_notices(IDB_CSV)}
    assert "Ancient notice nobody can resolve" not in titles


def test_idb_recency_window_is_relative_to_the_file_not_the_clock():
    """Replaying the same snapshot must always yield the same corpus."""
    from watchers.tenders.idb_procurement import parse_idb_notices
    assert len(parse_idb_notices(IDB_CSV)) == len(parse_idb_notices(IDB_CSV))


def test_idb_award_resolves_its_own_notice_as_same_publisher_not_independent():
    """The bug this pins: reading 'IDB Procurement Notices' and 'IDB
    Contract Award Notifications' as two publishers manufactured 68
    independent resolutions out of one institution resolving itself."""
    from watchers.tenders.idb_procurement import parse_idb_notices
    corpus = proc.observe(parse_idb_notices(IDB_CSV), observed_at="2026-08-20T00:00:00+00:00")
    resolved = [t for t in corpus["tenders"].values() if t.get("resolution")]
    assert len(resolved) == 1
    assert resolved[0]["resolution"]["independence"] == "same_publisher"


def test_publisher_registry_covers_every_wired_feed():
    from watchers.tenders.idb_procurement import AWARD_SOURCE, NOTICE_SOURCE
    for source in (NOTICE_SOURCE, AWARD_SOURCE,
                   "Jamaica GOJEP (opened bids)", "Jamaica GOJEP (contract award)",
                   "Guyana eProcure (NPTA)"):
        assert source in proc.PUBLISHERS, f"{source} must declare its publisher"


def test_a_national_portal_award_independently_resolves_a_multilateral_notice():
    """The point of wiring a second publisher: when two institutions cover
    the same tender, one's award notice resolves the other's detection."""
    from watchers.tenders.idb_procurement import NOTICE_SOURCE
    title = "Upgrade of the East Bank Public Road"
    corpus = proc.observe(
        [_notice(title, country="Guyana", agency="", source=NOTICE_SOURCE, closing="2026-07-21")],
        observed_at="2026-06-09T00:00:00+00:00",
    )
    corpus = proc.observe(
        [_award(title, country="Guyana", agency="Ministry of Public Works",
                source="Guyana eProcure (NPTA)", published="2026-08-01")],
        corpus, observed_at="2026-08-01T00:00:00+00:00",
    )
    assert len(corpus["tenders"]) == 1, "the award must attach to the IDB detection"
    entry = next(iter(corpus["tenders"].values()))
    assert entry["resolution"]["independence"] == "independent"
    assert entry["buyer"] == "Ministry of Public Works", "the named buyer fills in the blank one"


def test_alias_matching_refuses_an_ambiguous_merge():
    """Two buyers running a same-titled tender must not be collapsed into
    one record just because a third feed omitted the buyer."""
    from watchers.tenders.idb_procurement import NOTICE_SOURCE
    title = "Supply of Printers"
    corpus = proc.observe([
        _notice(title, country="Jamaica", agency="Ministry of Health", closing="2026-07-01"),
        _notice(title, country="Jamaica", agency="Ministry of Works", closing="2026-07-01"),
    ], observed_at="2026-06-01T00:00:00+00:00")
    corpus = proc.observe(
        [_notice(title, country="Jamaica", agency="", source=NOTICE_SOURCE, closing="2026-07-01")],
        corpus, observed_at="2026-06-02T00:00:00+00:00",
    )
    assert len(corpus["tenders"]) == 3, "an ambiguous match must stay separate"
