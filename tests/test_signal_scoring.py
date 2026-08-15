"""Ranking contract for the editorial scorer.

These cover the failure that shipped: three FDI signals whose structural
properties were identical all clamped to 100, so the lead market was chosen
by list order and a feedback boolean rather than by the size of the movement.
"""
from __future__ import annotations

import pytest

from packagers.dispatch_desk import build_clusters
from packagers.editorial_enrichment import (
    compute_signal_score,
    display_score,
    enrich_signals,
    magnitude_boost,
    signal_magnitude_pct,
)


def _fdi_signal(country: str, evidence: list[str], sid: str | None = None) -> dict:
    """An enhanced_investment signal — the kind that leads the front page."""
    return {
        "id": sid or f"enh-{country.lower()}",
        "kind": "enhanced_investment",
        "priority": "medium",
        "countries": [country],
        "sources": ["World Bank", "CARICOM", "CDB"],
        "evidence": evidence,
        "summary": f"{country}: FDI surge",
    }


# ── Magnitude extraction ───────────────────────────────────

@pytest.mark.parametrize(
    "text,expected",
    [
        ("Guyana: FDI net inflows moved up 860.3% from 2023 to 2024.", 860.3),
        ("Barbados: FDI net inflows moved down 34.8% from 2023 to 2024.", 34.8),
        # Written by _transfer_fdi_magnitudes. Scoring used to miss this
        # format entirely, which silently disabled the whole transfer.
        ("FDI change: 206.0%", 206.0),
        ("Foreign investment net inflows moved +860.3% from 2023 to 2024", 860.3),
        ("206.0% change", 206.0),
    ],
)
def test_magnitude_is_read_from_every_phrasing_we_emit(text, expected):
    assert signal_magnitude_pct({"evidence": [text]}) == pytest.approx(expected)


def test_structured_magnitude_wins_over_prose():
    signal = {"_magnitude_pct": 860.3, "evidence": ["moved up 12.0%"]}
    assert signal_magnitude_pct(signal) == pytest.approx(860.3)


def test_absent_magnitude_is_none_not_zero():
    assert signal_magnitude_pct({"evidence": ["WB FDI surge detected: Guyana"]}) is None


def test_magnitude_bands_are_ordered():
    assert magnitude_boost(860.3) > magnitude_boost(206.0)
    assert magnitude_boost(206.0) > magnitude_boost(34.8)
    assert magnitude_boost(34.8) > magnitude_boost(5.0)
    assert magnitude_boost(None) == 0


# ── Scoring ────────────────────────────────────────────────

def test_score_is_raw_so_strong_signals_stay_separable():
    """The clamp is what made every strong FDI signal tie on 100."""
    big = compute_signal_score(_fdi_signal("Guyana", ["FDI change: 860.3%"]))
    mid = compute_signal_score(_fdi_signal("Suriname", ["FDI change: 206.0%"]))
    small = compute_signal_score(_fdi_signal("Barbados", ["FDI change: 34.8%"]))

    assert big > mid > small
    assert big > 100, "raw scores must not be clamped or ranking ties again"
    assert display_score(big) == 100


def test_display_score_stays_in_range():
    assert display_score(141) == 100
    assert display_score(-12) == 0
    assert display_score(72) == 72


def test_magnitude_separates_otherwise_identical_signals():
    """Same kind, priority, sources and evidence count — only size differs."""
    a = _fdi_signal("Guyana", ["FDI change: 860.3%"])
    b = _fdi_signal("Barbados", ["FDI change: 34.8%"])
    assert compute_signal_score(a) != compute_signal_score(b)


# ── Feedback loop ──────────────────────────────────────────

def test_feedback_boost_is_symmetric(monkeypatch):
    """A signal on 100 used to absorb penalties but discard rewards."""
    import packagers.editorial_enrichment as ee

    monkeypatch.setattr(ee, "load_feedback_boosts", lambda: None)
    monkeypatch.setattr(
        ee, "_FEEDBACK_BOOSTS",
        {"enhanced_investment": {"Guyana": 7, "Barbados": -9}},
    )
    signals = [
        _fdi_signal("Guyana", ["FDI change: 100.0%"]),
        _fdi_signal("Barbados", ["FDI change: 100.0%"]),
    ]
    base = compute_signal_score(signals[0])
    enriched = {
        s["_country"]: s
        for s in ee.enrich_signals([dict(s) for s in signals], "2026-01-01")["enriched_signals"]
    }
    assert enriched["Guyana"]["_score_raw"] == base + 7
    assert enriched["Barbados"]["_score_raw"] == base - 9


# ── Lead selection ─────────────────────────────────────────

@pytest.fixture(autouse=True)
def _isolate_pipeline_state(tmp_path, monkeypatch):
    """enrich_signals reads and rewrites the real editorial state file.
    Point it at a temp path so running the suite cannot rewrite the live
    cycle's `previous_lead_country` with test fixtures."""
    import packagers.editorial_enrichment as ee

    monkeypatch.setattr(ee, "STATE_FILE", tmp_path / "editorial_state.json")
    monkeypatch.setattr(ee, "_FEEDBACK_BOOSTS", {})
    monkeypatch.setattr(ee, "load_feedback_boosts", lambda: None)


def _enrich(signals):
    return enrich_signals([dict(s) for s in signals], "2026-01-01")


def _tourism_signal(country: str, pct: float) -> dict:
    return {
        "id": f"tour-{country.lower()}",
        "kind": "tourism_impact",
        "priority": "low",
        "countries": [country],
        "sources": ["World Bank"],
        "evidence": [f"{country}: arrivals moved up {pct}%"],
        "summary": f"{country} tourism",
    }


def test_lead_follows_magnitude_not_input_order():
    """Mirrors the shipped cycle: the two biggest movers also carry a weak
    tourism signal, the middle one does not."""
    signals = [
        _fdi_signal("Barbados", ["FDI change: 34.8%"]),
        _tourism_signal("Barbados", 5.5),
        _fdi_signal("Suriname", ["FDI change: 206.0%"]),
        _fdi_signal("Guyana", ["FDI change: 860.3%"]),
        _tourism_signal("Guyana", 9.9),
    ]
    assert _enrich(signals)["lead_signal"]["_country"] == "Guyana"
    assert _enrich(list(reversed(signals)))["lead_signal"]["_country"] == "Guyana"


def test_extra_weak_signal_does_not_cost_a_country_the_lead():
    """Cluster scoring averaged its signals, so breadth of evidence was a
    penalty: the biggest mover lost the lead for also carrying a weak
    tourism signal."""
    strong = _fdi_signal("Guyana", ["FDI change: 860.3%"])
    rival = _fdi_signal("Suriname", ["FDI change: 206.0%"])
    weak = {
        "id": "tour-guyana",
        "kind": "tourism_impact",
        "priority": "low",
        "countries": ["Guyana"],
        "sources": ["World Bank"],
        "evidence": ["Guyana: arrivals moved up 9.9%"],
        "summary": "Guyana tourism",
    }
    assert _enrich([strong, rival])["lead_signal"]["_country"] == "Guyana"
    assert _enrich([strong, rival, weak])["lead_signal"]["_country"] == "Guyana"


# ── Cluster ordering ───────────────────────────────────────

def _dispatch(country: str, raw: int, magnitude: float, personas: int = 3) -> list[dict]:
    return [
        {
            "dispatch_id": f"DSP-{country}-{i}",
            "signal_kind": "enhanced_investment",
            "country_cluster": country,
            "persona_label": f"Persona {i}",
            "confidence_score": min(raw, 100),
            "confidence_raw": raw,
            "magnitude_pct": magnitude,
            "feedback_status": "awaiting",
        }
        for i in range(personas)
    ]


def test_clusters_rank_on_raw_score_then_magnitude():
    dispatches = (
        _dispatch("Barbados", 109, 34.8)
        + _dispatch("Guyana", 141, 860.3)
        + _dispatch("Suriname", 119, 206.0)
    )
    order = [c["country_cluster"] for c in build_clusters(dispatches)]
    assert order[:3] == ["Guyana", "Suriname", "Barbados"]


def test_magnitude_breaks_ties_before_persona_count():
    """Persona count is a routing artefact; it should not outrank evidence."""
    dispatches = _dispatch("Guyana", 120, 860.3, personas=2) + _dispatch(
        "Barbados", 120, 34.8, personas=3
    )
    order = [c["country_cluster"] for c in build_clusters(dispatches)]
    assert order[0] == "Guyana"


# ── Corroboration integrity ────────────────────────────────

def test_regional_context_is_not_counted_as_corroboration():
    """CARICOM/CDB availability is region-wide: it says a dataset exists this
    cycle, not that it confirms a given country. Counting it as a source gave
    every FDI country the same two extras and the three-source bonus."""
    honest = {
        "id": "enh-guyana",
        "kind": "enhanced_investment",
        "priority": "medium",
        "countries": ["Guyana"],
        "sources": ["World Bank", "CARICOM", "CDB"],
        "corroborating_sources": ["World Bank"],
        "context_sources": ["CARICOM", "CDB"],
        "evidence": ["WB FDI surge detected: Guyana", "FDI change: 860.3%"],
        "summary": "Guyana FDI",
    }
    inflated = dict(honest)
    inflated.pop("corroborating_sources")
    inflated.pop("context_sources")

    assert compute_signal_score(honest) < compute_signal_score(inflated)


def test_context_sources_do_not_trigger_the_three_source_bonus():
    import packagers.editorial_enrichment as ee

    signal = {
        "kind": "enhanced_investment",
        "priority": "medium",
        "sources": ["World Bank", "CARICOM", "CDB"],
        "corroborating_sources": ["World Bank"],
        "context_sources": ["CARICOM", "CDB"],
        "evidence": ["x"],
    }
    assert ee.corroborating_sources(signal) == ["World Bank"]
    assert ee.context_sources(signal) == ["CARICOM", "CDB"]
    # Three real sources should outscore one real plus two contextual.
    real_three = dict(signal, corroborating_sources=["World Bank", "IDB", "CDB"], context_sources=[])
    assert compute_signal_score(real_three) > compute_signal_score(signal)


def test_signals_without_the_split_keep_their_old_weighting():
    """Detectors that never separated the two must not silently lose score."""
    legacy = {
        "kind": "investment_signal",
        "priority": "medium",
        "sources": ["World Bank", "IDB"],
        "evidence": ["Guyana: FDI moved up 860.3% from 2023 to 2024."],
    }
    import packagers.editorial_enrichment as ee
    assert ee.corroborating_sources(legacy) == ["World Bank", "IDB"]
    assert compute_signal_score(legacy) > 0
