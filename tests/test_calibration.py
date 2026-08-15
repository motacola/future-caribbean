"""Calibration ledger contract.

The point of the ledger is that confidence stops being asserted and starts
being measured. These tests pin the two properties that makes it worth
anything: it must not print a rate it has not earned, and a claim that did not
hold up must count against the band that made it.
"""
from __future__ import annotations

import pytest

from packagers import calibration as cal


@pytest.fixture(autouse=True)
def _isolate_ledger(tmp_path, monkeypatch):
    monkeypatch.setattr(cal, "LEDGER_FILE", tmp_path / "ledger.json")
    monkeypatch.setattr(cal, "REPORT_FILE", tmp_path / "calibration.json")


def _signal(fact: str, score: int, corroborating: int = 1, sid: str = "") -> dict:
    return {
        "id": sid or fact,
        "fact_key": fact,
        "kind": "enhanced_investment",
        "countries": ["Guyana"],
        "_score": score,
        "corroborating_sources": ["World Bank"] * corroborating,
    }


def _run(cycles: list[tuple[str, list[dict]]]) -> dict:
    ledger = {"claims": []}
    for cycle_id, signals in cycles:
        ledger = cal.record_cycle(signals, cycle_id)
        cal.save_ledger(ledger)
        cal.resolve_claims(ledger, cycle_id)
        cal.save_ledger(ledger)
    return ledger


def test_bands_are_assigned_by_score():
    assert cal.band_for(100) == "85-100"
    assert cal.band_for(84) == "70-84"
    assert cal.band_for(60) == "55-69"
    assert cal.band_for(10) == "0-54"


def test_claims_stay_open_inside_the_resolution_window():
    ledger = _run([("20260101", [_signal("guyana|fdi|2024", 100)])])
    assert all(c["outcome"] is None for c in ledger["claims"])
    assert cal.reliability(ledger)["open_claims"] == 1


def test_a_fact_that_persists_with_its_corroboration_is_confirmed():
    fact = "guyana|fdi|2024"
    ledger = _run([(f"2026010{i}", [_signal(fact, 100)]) for i in range(1, 6)])
    first = ledger["claims"][0]
    assert first["outcome"] == "confirmed"


def test_a_fact_that_stops_being_reported_fades():
    """Publishing something that vanishes has to cost the band that ran it."""
    ledger = _run([
        ("20260101", [_signal("guyana|fdi|2024", 100)]),
        ("20260102", [_signal("other|fact|2024", 60)]),
        ("20260103", [_signal("other|fact|2024", 60)]),
        ("20260104", [_signal("other|fact|2024", 60)]),
        ("20260105", [_signal("other|fact|2024", 60)]),
    ])
    vanished = next(c for c in ledger["claims"] if c["fact_key"] == "guyana|fdi|2024")
    assert vanished["outcome"] == "faded"


def test_losing_corroboration_counts_as_faded():
    """A fact still mentioned but with weaker backing did not hold up."""
    fact = "guyana|fdi|2024"
    ledger = _run([
        ("20260101", [_signal(fact, 100, corroborating=2)]),
        ("20260102", [_signal(fact, 100, corroborating=1)]),
        ("20260103", [_signal(fact, 100, corroborating=1)]),
        ("20260104", [_signal(fact, 100, corroborating=1)]),
        ("20260105", [_signal(fact, 100, corroborating=1)]),
    ])
    assert ledger["claims"][0]["outcome"] == "faded"


def test_no_rate_is_published_below_the_minimum_sample():
    """The whole value here is not claiming precision we have not earned."""
    ledger = _run([(f"2026010{i}", [_signal(f"f{i}|x|2024", 100)]) for i in range(1, 6)])
    report = cal.reliability(ledger)
    top = next(b for b in report["bands"] if b["band"] == "85-100")
    if top["resolved"] < cal.MIN_SAMPLE:
        assert top["confirmation_rate"] is None
        assert report["calibrated"] is False


def test_rate_appears_once_the_band_has_enough_resolved_claims():
    cycles = []
    for i in range(1, 12):
        signals = [_signal(f"fact-{j}|x|2024", 100) for j in range(6)]
        cycles.append((f"202601{i:02d}", signals))
    ledger = _run(cycles)
    report = cal.reliability(ledger)
    top = next(b for b in report["bands"] if b["band"] == "85-100")
    assert top["resolved"] >= cal.MIN_SAMPLE
    assert top["confirmation_rate"] is not None
    assert report["calibrated"] is True


def test_label_refuses_to_imply_probability_before_calibration():
    uncalibrated = {"bands": [{"band": "85-100", "confirmation_rate": None}]}
    label = cal.calibrated_label(100, uncalibrated)
    assert "not yet calibrated" in label
    assert "%" not in label

    calibrated = {"bands": [{"band": "85-100", "confirmation_rate": 0.61}]}
    assert "61%" in cal.calibrated_label(100, calibrated)


def test_recording_the_same_cycle_twice_does_not_duplicate_claims():
    signals = [_signal("guyana|fdi|2024", 100)]
    cal.save_ledger(cal.record_cycle(signals, "20260101"))
    ledger = cal.record_cycle(signals, "20260101")
    assert len(ledger["claims"]) == 1


def test_two_signal_kinds_for_one_fact_create_one_claim():
    """Fact identity, not detector count, defines a calibration observation."""
    fact = "Guyana|BX.KLT.DINV.CD.WD|2024"
    base = _signal(fact, 75, sid="invest-guyana")
    base["kind"] = "investment_signal"
    base["corroborating_sources"] = ["World Bank", "IDB"]

    enhanced = _signal(fact, 91, sid="enhanced-invest-guyana")
    enhanced["kind"] = "enhanced_investment"
    enhanced["corroborating_sources"] = ["World Bank"]
    enhanced["context_sources"] = ["CARICOM", "CDB"]

    ledger = cal.record_cycle([base, enhanced], "20260101")

    assert len(ledger["claims"]) == 1
    claim = ledger["claims"][0]
    assert claim["signal_id"] == "enhanced-invest-guyana"
    assert claim["score"] == 91
    assert claim["corroborating_at_claim"] == 2
    assert claim["source_names"] == ["CARICOM", "CDB", "IDB", "World Bank"]


def test_same_fact_collapse_is_stable_under_input_reordering(monkeypatch):
    fact = "Guyana|BX.KLT.DINV.CD.WD|2024"
    low = _signal(fact, 75, sid="invest-guyana")
    high = _signal(fact, 91, sid="enhanced-invest-guyana")
    monkeypatch.setattr(cal, "_now", lambda: "2026-01-01T00:00:00+00:00")

    forward = cal.record_cycle([low, high], "20260101")["claims"][0]
    reverse = cal.record_cycle([high, low], "20260101")["claims"][0]

    assert forward == reverse


def test_calibration_uses_the_score_published_after_fdi_transfer(monkeypatch):
    """A base-only recomputation recorded 91 while the desk showed 100."""
    import packagers.editorial_enrichment as ee

    monkeypatch.setattr(ee, "load_feedback_boosts", lambda: None)
    monkeypatch.setattr(ee, "_FEEDBACK_BOOSTS", {})
    fact = "Guyana|BX.KLT.DINV.CD.WD|2024"
    base = _signal(fact, 0, sid="invest-guyana")
    base.update({
        "kind": "investment_signal",
        "priority": "medium",
        "evidence": ["Guyana: FDI moved up 860.3% from 2023 to 2024."],
        "sources": ["World Bank", "IDB"],
    })
    enhanced = _signal(fact, 0, sid="enhanced-invest-guyana")
    enhanced.update({
        "kind": "enhanced_investment",
        "priority": "medium",
        "evidence": ["WB FDI surge detected: Guyana"],
        "sources": ["World Bank", "CARICOM", "CDB"],
        "corroborating_sources": ["World Bank"],
        "context_sources": ["CARICOM", "CDB"],
    })

    scored = {s["id"]: s for s in cal.score_published_signals([base, enhanced])}

    assert scored["enhanced-invest-guyana"]["_magnitude_pct"] == pytest.approx(860.3)
    assert scored["enhanced-invest-guyana"]["_score_raw"] > 100
    assert scored["enhanced-invest-guyana"]["_score"] == 100


# ── Outcome-based resolution ───────────────────────────────

def _news(country: str, topic: str, published: str, domain: str) -> dict:
    return {
        "countries": [country],
        "topics": [topic],
        "published": published,
        "publisher_domain": domain,
    }


def _claimed(fact: str = "guyana|fdi|2024", sources=("World Bank",)) -> dict:
    return {
        "fact_key": fact,
        "kind": "enhanced_investment",
        "country": "Guyana",
        "recorded_at": "2026-01-01T00:00:00+00:00",
        "source_names": list(sources),
        "corroborating_at_claim": len(sources),
    }


def test_independent_publisher_counts_as_external_corroboration():
    found = cal.external_publishers_for(
        _claimed(),
        [_news("Guyana", "finance", "2026-01-05T00:00:00+00:00", "stabroeknews.com")],
    )
    assert found == ["stabroeknews.com"]


def test_the_signals_own_source_cannot_corroborate_itself():
    """A World Bank signal is not confirmed by the World Bank."""
    found = cal.external_publishers_for(
        _claimed(sources=("World Bank",)),
        [_news("Guyana", "finance", "2026-01-05T00:00:00+00:00", "worldbank.org")],
    )
    assert found == []


def test_coverage_before_the_claim_does_not_count():
    found = cal.external_publishers_for(
        _claimed(),
        [_news("Guyana", "finance", "2025-12-01T00:00:00+00:00", "stabroeknews.com")],
    )
    assert found == []


def test_unrelated_country_or_topic_does_not_count():
    items = [
        _news("Barbados", "finance", "2026-01-05T00:00:00+00:00", "nationnews.com"),
        _news("Guyana", "tourism", "2026-01-05T00:00:00+00:00", "traveltrade.com"),
    ]
    assert cal.external_publishers_for(_claimed(), items) == []


def test_rfc2822_published_dates_are_understood():
    """Regional news carries RFC-2822 dates, not ISO."""
    found = cal.external_publishers_for(
        _claimed(),
        [_news("Guyana", "finance", "Mon, 05 Jan 2026 17:29:36 +0000", "stabroeknews.com")],
    )
    assert found == ["stabroeknews.com"]


def test_a_later_indicator_release_that_gives_back_the_move_fades():
    claim = _claimed(fact="Guyana|BX.KLT.DINV.CD.WD|2024")
    later = [{"country_name": "Guyana", "indicator_code": "BX.KLT.DINV.CD.WD",
              "year": 2025, "delta_pct": -80.0}]
    assert cal.indicator_verdict(claim, later) == "faded"


def test_a_later_indicator_release_that_holds_confirms():
    claim = _claimed(fact="Guyana|BX.KLT.DINV.CD.WD|2024")
    later = [{"country_name": "Guyana", "indicator_code": "BX.KLT.DINV.CD.WD",
              "year": 2025, "delta_pct": 12.0}]
    assert cal.indicator_verdict(claim, later) == "confirmed"


def test_older_or_same_year_releases_are_not_an_outcome():
    claim = _claimed(fact="Guyana|BX.KLT.DINV.CD.WD|2024")
    same = [{"country_name": "Guyana", "indicator_code": "BX.KLT.DINV.CD.WD",
             "year": 2024, "delta_pct": 900.0}]
    assert cal.indicator_verdict(claim, same) is None


def test_external_evidence_beats_internal_persistence():
    """The whole upgrade: outside agreement outranks our own repetition."""
    fact = "guyana|fdi|2024"
    ledger = {"claims": []}
    for i in range(1, 6):
        ledger = cal.record_cycle([_signal(fact, 100)], f"2026010{i}")
        cal.save_ledger(ledger)
    cal.resolve_claims(
        ledger, "20260105",
        news_items=[_news("Guyana", "finance", "2030-01-01T00:00:00+00:00", "stabroeknews.com")],
    )
    first = ledger["claims"][0]
    assert first["outcome"] == "confirmed"
    assert first["resolved_by"] == cal.RESOLVER_EXTERNAL

    report = cal.reliability(ledger)
    assert report["externally_resolved"] >= 1
    assert report["external_share"] is not None


def test_internal_persistence_is_recorded_as_the_weakest_verdict():
    fact = "guyana|fdi|2024"
    ledger = {"claims": []}
    for i in range(1, 6):
        ledger = cal.record_cycle([_signal(fact, 100)], f"2026010{i}")
        cal.save_ledger(ledger)
    cal.resolve_claims(ledger, "20260105", news_items=[], observations=[])
    assert ledger["claims"][0]["resolved_by"] == cal.RESOLVER_INTERNAL
    assert cal.reliability(ledger)["externally_resolved"] == 0


# ── Tamper-evidence ────────────────────────────────────────

def test_a_fresh_ledger_chain_verifies():
    ledger = _run([(f"2026010{i}", [_signal(f"f{i}|x|2024", 100)]) for i in range(1, 4)])
    intact, broken_at = cal.verify_chain(ledger)
    assert intact is True and broken_at is None


def test_editing_a_historical_claim_breaks_the_chain():
    """A track record you can quietly rewrite is worth nothing."""
    ledger = _run([(f"2026010{i}", [_signal(f"f{i}|x|2024", 100)]) for i in range(1, 4)])
    ledger["claims"][0]["score"] = 12          # rewrite history
    intact, broken_at = cal.verify_chain(ledger)
    assert intact is False
    assert broken_at == 0


def test_deleting_a_claim_breaks_the_chain():
    ledger = _run([(f"2026010{i}", [_signal(f"f{i}|x|2024", 100)]) for i in range(1, 4)])
    del ledger["claims"][1]
    assert cal.verify_chain(ledger)[0] is False


def test_resolution_does_not_break_the_chain():
    """Outcomes are written after the fact, so they must not be hashed."""
    ledger = _run([(f"2026010{i}", [_signal(f"f{i}|x|2024", 100)]) for i in range(1, 7)])
    assert any(c["outcome"] is not None for c in ledger["claims"])
    assert cal.verify_chain(ledger)[0] is True


# ── Probabilistic scoring ──────────────────────────────────

def test_forecast_starts_naive_and_becomes_calibrated():
    ledger = {"claims": []}
    p, basis = cal.forecast_probability(100, ledger)
    assert basis == "naive" and p == pytest.approx(0.95)   # clamped from 1.0

    for i in range(1, 12):
        ledger = cal.record_cycle([_signal(f"fact-{j}|x|2024", 100) for j in range(6)],
                                  f"202601{i:02d}")
        cal.save_ledger(ledger)
        cal.resolve_claims(ledger, f"202601{i:02d}")
    _, basis_after = cal.forecast_probability(100, ledger)
    assert basis_after == "calibrated"


def test_probabilities_are_never_zero_or_one():
    """Log-loss is undefined at the extremes, and certainty is never honest."""
    assert cal.forecast_probability(0, {"claims": []})[0] >= cal.PROBABILITY_FLOOR
    assert cal.forecast_probability(100, {"claims": []})[0] <= cal.PROBABILITY_CEILING


def test_brier_rewards_accuracy():
    confident_right = cal.brier_score([(0.9, 1), (0.9, 1)])
    confident_wrong = cal.brier_score([(0.9, 0), (0.9, 0)])
    assert confident_right < confident_wrong
    assert cal.brier_score([]) is None


def test_log_loss_punishes_confident_errors_harder_than_brier():
    assert cal.log_loss([(0.95, 0)]) > cal.log_loss([(0.55, 0)])


def test_report_measures_itself_against_the_naive_baseline():
    """The product implicitly claims score/100 is a probability. Beating that
    is the value the ledger adds, and it has to be measurable."""
    ledger = {"claims": []}
    for i in range(1, 12):
        ledger = cal.record_cycle([_signal(f"fact-{j}|x|2024", 100) for j in range(6)],
                                  f"202601{i:02d}")
        cal.save_ledger(ledger)
        cal.resolve_claims(ledger, f"202601{i:02d}")
    report = cal.reliability(ledger)
    assert report["brier"] is not None
    assert report["brier_naive_baseline"] is not None
    assert report["brier_improvement_over_naive"] is not None


# ── Public pre-commitment ──────────────────────────────────

def test_commitments_are_pending_before_their_day_and_never_silently_pass():
    report = cal.reliability(_run([("20260101", [_signal("a|x|2024", 100)])]))
    assert report["committed_at"] == cal.COMMITMENT_MADE_AT
    assert [c["status"] for c in report["commitments"]] == ["pending"] * len(cal.COMMITMENTS)


def test_a_due_gate_with_too_few_claims_reads_as_missed(monkeypatch):
    """Gates must be judged from the commitment date, not from today —
    otherwise every gate is trivially passable forever."""
    monkeypatch.setattr(cal, "COMMITMENT_MADE_AT", "2020-01-01")
    report = cal.reliability(_run([("20260101", [_signal("a|x|2024", 100)])]))
    assert all(c["due"] for c in report["commitments"])
    assert all(c["status"] == "missed" for c in report["commitments"])


def test_report_exposes_chain_integrity():
    report = cal.reliability(_run([("20260101", [_signal("a|x|2024", 100)])]))
    assert report["chain_intact"] is True


def test_scheduled_pipeline_persists_the_cumulative_ledger():
    workflow = (cal.ROOT / ".github" / "workflows" / "pipeline.yml").read_text()
    assert "git add" in workflow
    assert "data/calibration/" in workflow
