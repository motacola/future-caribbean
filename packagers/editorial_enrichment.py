#!/usr/bin/env python3
"""Editorial enrichment layer for Caribbean Signal OS.

Runs after the cross-source merger, before channel packaging.
Transforms raw composite signals into editorial-grade intelligence:

  - Lead story selection (strongest cross-signal cluster per cycle)
  - Differentiated decision language by score band, not by kind template
  - Cross-signal context enrichment (connects related signals)
  - Temporal freshness tracking (new / sustained / intensified / weakened)
  - Narrative framing (channel intros, cycle summary)

This is the layer that turns enriched telemetry into a product with judgment.
"""

from __future__ import annotations

import logging
import json
import re
from collections import defaultdict
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

LOGGER = logging.getLogger(__name__)

ROOT = Path(__file__).resolve().parents[1]
STATE_FILE = ROOT / "data" / "editorial" / "state.json"

# ── Feedback boost cache ────────────────────────────────────
_FEEDBACK_BOOSTS: dict[str, dict[str, int]] = {}

def load_feedback_boosts() -> None:
    """Load feedback boosts from feedback_loop output."""
    global _FEEDBACK_BOOSTS
    path = ROOT / "data" / "feedback" / "current_boosts.json"
    if path.exists():
        try:
            data = json.loads(path.read_text(encoding="utf-8"))
            _FEEDBACK_BOOSTS = data.get("boosts", {})
        except (json.JSONDecodeError, OSError):
            _FEEDBACK_BOOSTS = {}
    else:
        _FEEDBACK_BOOSTS = {}

# ── Score bands ─────────────────────────────────────────────
SCORE_BANDS: list[tuple[str, int, int]] = [
    ("immediate", 90, 101),
    ("validation", 70, 90),
    ("monitor", 50, 70),
    ("context", 0, 50),
]

# ── Lead selection weights ─────────────────────────────────
# Higher weight = more likely to be selected as the lead story
KIND_LEAD_WEIGHT: dict[str, float] = {
    "enhanced_investment": 1.5,
    "active_storm": 1.5,
    "cyclone_risk": 1.3,
    "tropical_development": 1.3,
    "investment_signal": 1.0,
    "economic_vulnerability": 1.0,
    "development_pipeline": 0.9,
    "food_security": 0.8,
    "maritime_hazard": 0.8,
    "tourism_impact": 0.6,
}

# ── Signal kind display labels ─────────────────────────────
KIND_LABELS: dict[str, str] = {
    "enhanced_investment": "💎 Investment",
    "investment_signal": "💼 Investment",
    "economic_vulnerability": "⚠️ Vulnerability",
    "development_pipeline": "🏗️ Pipeline",
    "food_security": "🌾 Food",
    "tourism_impact": "🏖️ Tourism",
    "cyclone_risk": "🌀 Storm Risk",
    "active_storm": "🌀 Storm",
    "tropical_development": "🌪️ Development",
    "maritime_hazard": "🚢 Maritime",
}

# ── Decision language by kind × score band ─────────────────
# Each entry: ("band"): "template with {country}, {detail}, {n_sources}"
DECISIONS: dict[str, dict[str, str]] = {
    "enhanced_investment": {
        "immediate": (
            "Immediate investigation. {country} has multi-source investment "
            "validation ({n_sources} signals converging). Priority: assess market "
            "entry options, identify existing operators."
        ),
        "validation": (
            "Validation priority. Strong multi-source signal from {country}. "
            "Cross-reference with sector data before committing resources."
        ),
        "monitor": (
            "Monitor. {country} showing positive investment trajectory across "
            "{n_sources}. Track next cycle for confirmation. "
            "Escalates if multi-source convergence persists 2+ consecutive cycles."
        ),
        "context": (
            "Supplementary context. {country} investment signals present "
            "but need more evidence before action."
        ),
    },
    "investment_signal": {
        "immediate": (
            "Immediate investigation. {country} FDI signal ({detail}) with "
            "active development datasets. Validate with local market intel."
        ),
        "validation": (
            "Validation priority. {country} FDI movement ({detail}) signals "
            "opportunity. Cross-reference with sector data."
        ),
        "monitor": (
            "Monitor. {country} FDI trend ({detail}). Needs supporting "
            "evidence before committing. "
            "Escalates if FDI velocity sustains above threshold 2nd consecutive cycle."
        ),
        "context": (
            "Context only. {country} FDI data point for broader regional picture."
        ),
    },
    "economic_vulnerability": {
        "validation": (
            "Watch: {country} elevated indicators ({detail}). Deeper context "
            "check needed before expansion or support decisions."
        ),
        "monitor": (
            "Monitor. {country} showing economic stress ({detail}). Track "
            "next cycle. Escalates if additional stress indicators appear or "
            "existing ones worsen."
        ),
        "context": (
            "Context. {country} economic data point for regional awareness."
        ),
    },
    "development_pipeline": {
        "immediate": (
            "Active procurement pipeline: {detail}. Priority: review CDB/IDB "
            "opportunities as lead list for project-based entry."
        ),
        "validation": (
            "Development pipeline active: {detail}. Validate relevance before "
            "engaging."
        ),
        "monitor": (
            "Development activity detected: {detail}. Monitor for new "
            "opportunities. Escalates if procurement notice volume or "
            "project value increases."
        ),
        "context": (
            "Context. Development pipeline data for regional awareness."
        ),
    },
    "food_security": {
        "validation": (
            "Food security monitoring active: {detail}. Relevant for "
            "agriculture, logistics, and policy stakeholders."
        ),
        "monitor": (
            "Food trade data available ({detail}). Watch for emerging "
            "pressure points. Escalates if food import costs or local "
            "inflation accelerates."
        ),
        "context": (
            "Supplementary food security context."
        ),
    },
    "tourism_impact": {
        "validation": (
            "Positive tourism context: {country} GDP growth ({detail}). "
            "Validate with booking and airlift data."
        ),
        "monitor": (
            "Tourism-relevant growth: {country} ({detail}). Track for "
            "confirmation. Escalates if booking or airlift data confirms trajectory."
        ),
        "context": (
            "Context. {country} GDP data point for tourism sector awareness."
        ),
    },
    "cyclone_risk": {
        "immediate": (
            "Immediate operational alert: {detail}. Route to resilience team "
            "and review contingency plans."
        ),
        "monitor": (
            "Weather risk developing: {detail}. Monitor NHC updates closely. "
            "Escalates if probability crosses 50% or watch/warning issued."
        ),
    },
    "active_storm": {
        "immediate": (
            "Active storm in basin: {detail}. Route to operational channels "
            "immediately — timing-sensitive intelligence."
        ),
    },
    "tropical_development": {
        "validation": (
            "Tropical development risk: {detail}. Review preparedness status."
        ),
        "monitor": (
            "Weather system being monitored: {detail}. Track next NHC updates. "
            "Escalates if probability rises or new development areas form."
        ),
    },
    "maritime_hazard": {
        "validation": (
            "Maritime hazard active: {detail}. Relevant for shipping, logistics, "
            "coastal operations."
        ),
    },
}


def _build_fallback_decision(signal_kind: str, band: str, country: str, detail: str) -> str:
    kinds = KIND_LABELS
    label = kinds.get(signal_kind, signal_kind)
    return f"{band.title()} — {country}: {label} ({detail}). Validate locally."


def get_decision(
    signal_kind: str,
    band: str,
    country: str,
    detail: str,
    n_sources: int,
) -> str:
    """Return differentiated decision language for a signal."""
    kind_map = DECISIONS.get(signal_kind, {})
    template = kind_map.get(band)
    if template is None:
        return _build_fallback_decision(signal_kind, band, country, detail)
    return template.format(country=country, detail=detail, n_sources=n_sources)


# ── Score computation ───────────────────────────────────────

KIND_SCORE_WEIGHT: dict[str, int] = {
    "enhanced_investment": 54,
    "development_pipeline": 52,
    "maritime_hazard": 48,
    "cyclone_risk": 48,
    "active_storm": 48,
    "tropical_development": 46,
    "investment_signal": 40,
    "food_security": 42,
    "economic_vulnerability": 36,
    "tourism_impact": 30,
}

SOURCE_SCORE_WEIGHT: dict[str, int] = {
    "World Bank": 10,
    "IDB": 10,
    "CDB": 10,
    "CARICOM": 10,
    "NOAA": 8,
    "NOAA NWS": 8,
    "NDBC": 8,
}


def compute_signal_score(signal: dict[str, Any]) -> int:
    """Score a single composite signal from 0-100.

    Includes magnitude boost for FDI/inflation/unemployment signals where
    the evidence text contains a percentage — bigger moves score higher
    even when the structural properties are identical.
    """
    score = KIND_SCORE_WEIGHT.get(signal.get("kind", ""), 50)
    pb = {"high": 18, "medium": 10, "low": 3}
    score += pb.get(signal.get("priority", "low"), 0)
    score += min(len(signal.get("evidence") or []) * 4, 12)
    score += sum(SOURCE_SCORE_WEIGHT.get(s, 4) for s in signal.get("sources", []))
    if len(signal.get("sources", [])) >= 3:
        score += 8

    # ── Magnitude boost ───────────────────────────────────
    # Heavier weight for signals that show large numeric movements
    # this differentiates Guyana 860% from St Kitts 41%
    evidence = signal.get("evidence") or []
    for ev in evidence:
        m = re.search(r"moved (?:up|down) ([\d.]+)%", ev)
        if m:
            pct = float(m.group(1))
            if pct >= 500:
                score += 20  # exceptional move
            elif pct >= 200:
                score += 14  # major move
            elif pct >= 75:
                score += 8   # significant move
            elif pct >= 30:
                score += 4   # notable move
            break  # one magnitude boost per signal

    return min(score, 100)


def feedback_boost_for(signal: dict[str, Any]) -> int:
    """Get feedback boost for this signal from current cycle's boosts."""
    kind = signal.get("kind", "")
    country = ""
    # Extract country from the signal's countries list or _country field
    countries = signal.get("countries") or []
    country = countries[0] if countries else signal.get("_country", "")
    return _FEEDBACK_BOOSTS.get(kind, {}).get(country, 0)


def resolve_band(score: int) -> str:
    for band, lo, hi in SCORE_BANDS:
        if lo <= score < hi:
            return band
    return "context"


def band_emoji(band: str) -> str:
    return {"immediate": "🔴", "validation": "🟡", "monitor": "🟢", "context": "⚪"}.get(band, "⚪")


# ── Detail extraction ───────────────────────────────────────

def extract_detail(signal: dict[str, Any]) -> str:
    """Extract a concise one-line detail string for decision templates."""
    kind = signal.get("kind", "")
    evidence = signal.get("evidence") or []
    summary = signal.get("summary", "")

    if kind == "enhanced_investment":
        sources = signal.get("sources", [])
        n = sum(1 for s in sources if s in ("World Bank", "CARICOM", "CDB"))
        return f"{n}/3 sources confirm"

    for ev in evidence:
        m = re.search(r"moved (?:up|down) ([\d.]+)%", ev)
        if m:
            return f"{m.group(1)}% change"
        m2 = re.search(r"(\d+\.?\d*)%", ev)
        if m2:
            return f"{m2.group(1)}%"

    m = re.search(r"(\d+\.?\d*%)", summary)
    if m:
        return m.group(1)

    if kind in ("development_pipeline", "food_security"):
        # Extract the key count, not the full summary
        ev = evidence[0] if evidence else summary
        return ev.strip()[:200]
    return "signal detected"


def extract_country(signal: dict[str, Any]) -> str:
    countries = signal.get("countries") or []
    return countries[0] if countries else "Regional"


def evidence_grade(signal: dict[str, Any]) -> str:
    """Evidence grade: A/B/C based on source and evidence count."""
    source_count = len(signal.get("sources", []))
    evidence_count = len(signal.get("evidence") or [])
    if source_count >= 3 and evidence_count >= 2:
        return "A - multi-source"
    if source_count >= 2:
        return "B - cross-source"
    return "C - single-source"


# ── Freshness / temporal tracking ──────────────────────────

def load_editorial_state() -> dict[str, Any]:
    if STATE_FILE.exists():
        try:
            state = json.loads(STATE_FILE.read_text(encoding="utf-8"))
            if isinstance(state, dict):
                return state
        except (json.JSONDecodeError, OSError):
            LOGGER.warning("editorial data file read error")
    return {
        "previous_signal_ids": [],
        "previous_top_scores": {},
        "previous_lead_country": "",
        "previous_summaries": {},
    }


def save_editorial_state(
    lead_country: str,
    signals: list[dict[str, Any]],
    scores: dict[str, int],
) -> None:
    state = {
        "previous_run": datetime.now(timezone.utc).isoformat(),
        "previous_lead_country": lead_country,
        "previous_signal_ids": [s.get("id", "") for s in signals],
        "previous_top_scores": scores,
        "previous_summaries": {s.get("id", ""): s.get("summary", "") for s in signals},
    }
    STATE_FILE.parent.mkdir(parents=True, exist_ok=True)
    STATE_FILE.write_text(json.dumps(state, indent=2) + "\n", encoding="utf-8")


def signal_freshness(
    signal_id: str,
    previous_ids: set[str],
    prev_scores: dict[str, int],
    score: int,
    prev_summaries: dict[str, str],
    summary: str,
) -> tuple[str, str]:
    """Determine if a signal is new, sustained, intensified, or weakened.
    Returns (status, human-readable detail)."""
    if signal_id not in previous_ids:
        return ("new", "New this cycle")

    # Content changed (new summary text)
    if prev_summaries.get(signal_id, "") != summary:
        return ("updated", "Content updated this cycle")

    prev = prev_scores.get(signal_id, 0)
    diff = score - prev
    if abs(diff) < 5:
        return ("sustained", "Unchanged from last cycle")
    if diff >= 5:
        return ("intensified", f"Strengthened (+{diff} pts)")
    return ("weakened", f"Weakened ({diff} pts)")


# ── Lead story selection ────────────────────────────────────

def select_lead(
    enriched: list[dict[str, Any]],
    scores: dict[str, int],
) -> tuple[dict[str, Any] | None, list[dict[str, Any]], str]:
    """Pick the strongest country-level narrative as the editorial lead.

    Returns (lead_signal, remaining_supporting_signals, rationale).
    """
    if not enriched:
        return None, [], "No signals generated this cycle."

    # Group by country
    by_country: dict[str, list[dict[str, Any]]] = defaultdict(list)
    for sig in enriched:
        countries = sig.get("countries") or ["Regional"]
        for c in countries:
            by_country[c].append(sig)

    # Regional clusters can't lead unless there's no country-specific signal
    regional_clusters = {"CARICOM", "Regional", "Caribbean", "Caribbean/Atlantic"}
    country_specific = {k: v for k, v in by_country.items() if k not in regional_clusters}

    clusters_to_score = country_specific if country_specific else by_country

    best_country = None
    best_cluster_score = -1.0
    best_rationale = ""

    for country, sigs in clusters_to_score.items():
        n_signals = len(sigs)
        unique_sources: set[str] = set()
        weighted_sum = 0.0

        for sig in sigs:
            base_score = scores.get(sig.get("id", ""), 50)
            kw = KIND_LEAD_WEIGHT.get(sig.get("kind", ""), 1.0)
            weighted_sum += base_score * kw
            unique_sources.update(sig.get("sources", []))

        n_sources = len(unique_sources)
        cross_signal_bonus = min(n_signals * 5, 20)
        cross_source_bonus = min(n_sources * 10, 30)
        cluster_score = (weighted_sum / max(len(sigs), 1)) + cross_signal_bonus + cross_source_bonus

        if cluster_score > best_cluster_score:
            best_cluster_score = cluster_score
            best_country = country
            best_rationale = (
                f"{country}: {n_signals} signal(s), {n_sources} source(s) — "
                f"{' / '.join(s.get('kind', '') for s in sigs)}"
            )

    if not best_country:
        return None, enriched, "No strong country-level cluster detected."

    # Lead is the highest-scored signal for the winning country
    country_sigs = sorted(
        [s for s in by_country[best_country]],
        key=lambda s: scores.get(s.get("id", ""), 0),
        reverse=True,
    )
    lead = country_sigs[0] if country_sigs else None
    # Supporting = everything except the lead
    supporting_cluster = country_sigs[1:] if lead else []
    other = [s for s in enriched if s.get("id") not in {sig.get("id") for sig in country_sigs}]
    supporting = other + supporting_cluster

    return lead, supporting, best_rationale


# ── Cross-signal context enrichment ────────────────────────

def find_related_signals(
    signal: dict[str, Any],
    all_enriched: list[dict[str, Any]],
) -> list[dict[str, Any]]:
    """Find signals that relate to the same country or sector."""
    country = extract_country(signal)
    kind = signal.get("kind", "")
    related = [
        s for s in all_enriched
        if s.get("id") != signal.get("id")
        and (
            extract_country(s) == country
            or (
                kind in ("cyclone_risk", "maritime_hazard", "tropical_development", "active_storm")
                and s.get("kind") in ("cyclone_risk", "maritime_hazard", "tropical_development", "active_storm")
            )
        )
    ]
    return related


def _transfer_fdi_magnitudes(enriched: list[dict[str, Any]]) -> None:
    """Cross-reference enhanced_investment signals with matching investment_signal
    evidence to carry FDI percentage data through to higher-tier signals.

    Enhanced signals don't include the raw percentage in their evidence
    ('WB FDI surge detected: Barbados' vs 'Barbados: FDI moved up 34.8%').
    This function finds the matching regular signal, extracts the pct, and
    updates the enhanced signal so the magnitude boost applies to both.
    """
    # Build lookup: country -> percentage from investment_signal evidence
    fdi_pct_by_country: dict[str, float] = {}
    for sig in enriched:
        if sig.get("kind") == "investment_signal":
            country = sig.get("_country", "")
            for ev in sig.get("evidence") or []:
                m = re.search(r"moved (?:up|down) ([\d.]+)%", ev)
                if m:
                    fdi_pct_by_country[country] = float(m.group(1))
                    break

    if not fdi_pct_by_country:
        return

    # Apply percentage as additional evidence + re-score enhanced signals
    for sig in enriched:
        if sig.get("kind") == "enhanced_investment":
            country = sig.get("_country", "")
            pct = fdi_pct_by_country.get(country)
            if pct is not None:
                # Append percentage to evidence
                evidence = list(sig.get("evidence") or [])
                pct_line = f"FDI change: {pct:.1f}%"
                if pct_line not in evidence:
                    evidence.append(pct_line)
                    sig["evidence"] = evidence

                # Update detail
                sig["_detail"] = f"{pct:.1f}% change"

                # Recompute score with magnitude
                new_score = compute_signal_score(sig)
                sig["_score"] = new_score

                # Update band (same module — no import needed)
                sig["_band"] = resolve_band(new_score)
                sig["_band_label"] = sig["_band"].replace("_", " ").title()
                sig["_band_emoji"] = band_emoji(sig["_band"])

                # Update decision for the new band
                n_sources = len(sig.get("sources", []))
                sig["_decision"] = get_decision(
                    sig.get("kind", ""), sig["_band"], country,
                    sig["_detail"], n_sources,
                )


# ── Cycle summary ──────────────────────────────────────────

def build_cycle_summary(
    enriched: list[dict[str, Any]],
    state: dict[str, Any],
    current_lead_country: str = "",
) -> str:
    """Build a one-line summary of what happened this cycle."""
    fresh = sum(1 for s in enriched if s.get("_freshness") == "new")
    sustained = sum(1 for s in enriched if s.get("_freshness") == "sustained")
    intensified = sum(1 for s in enriched if s.get("_freshness") == "intensified")
    updated = sum(1 for s in enriched if s.get("_freshness") == "updated")
    total = len(enriched)

    parts = [f"{total} composite signal(s)"]
    if fresh:
        parts.append(f"{fresh} new")
    if updated:
        parts.append(f"{updated} updated")
    if intensified:
        parts.append(f"{intensified} intensified")
    if sustained:
        parts.append(f"{sustained} persistent")

    lead_country = current_lead_country or state.get("previous_lead_country", "")
    if lead_country:
        parts.insert(0, f"Lead: {lead_country}")

    return " · ".join(parts)


# ── Main: enrich all signals ───────────────────────────────

def enrich_signals(
    signals: list[dict[str, Any]],
    generated_at: str,
) -> dict[str, Any]:
    """Main entry point. Returns a full editorial package dict."""
    load_feedback_boosts()
    scores = {s.get("id", ""): compute_signal_score(s) for s in signals}
    # Apply feedback boosts from previous cycles
    for sig in signals:
        sid = sig.get("id", "")
        if sid in scores:
            scores[sid] = min(scores[sid] + feedback_boost_for(sig), 100)
    state = load_editorial_state()
    previous_ids = set(state.get("previous_signal_ids", []))
    prev_scores = state.get("previous_top_scores", {})
    prev_summaries = state.get("previous_summaries", {})

    # Enrich each signal
    enriched: list[dict[str, Any]] = []
    for sig in signals:
        sid = sig.get("id", "") or ""
        country = extract_country(sig)
        detail = extract_detail(sig)
        score = scores.get(sid, 50)
        band = resolve_band(score)
        n_sources = len(sig.get("sources", []))
        fresh, fresh_detail = signal_freshness(
            sid, previous_ids, prev_scores, score, prev_summaries,
            sig.get("summary", ""),
        )

        enriched_sig = dict(sig)
        enriched_sig["_score"] = score
        enriched_sig["_band"] = band
        enriched_sig["_band_label"] = band.replace("_", " ").title()
        enriched_sig["_band_emoji"] = band_emoji(band)
        enriched_sig["_decision"] = get_decision(
            sig.get("kind", ""), band, country, detail, n_sources,
        )
        enriched_sig["_freshness"] = fresh
        enriched_sig["_freshness_detail"] = fresh_detail
        enriched_sig["_country"] = country
        enriched_sig["_detail"] = detail
        enriched_sig["_n_sources"] = n_sources
        enriched_sig["_evidence_grade"] = evidence_grade(sig)
        enriched_sig["_kind_label"] = KIND_LABELS.get(sig.get("kind", ""), sig.get("kind", ""))
        enriched.append(enriched_sig)

    # Cross-reference: carry FDI magnitude to enhanced signals before
    # selecting the lead, otherwise structurally similar FDI signals tie too
    # often and the editorial lead ignores magnitude.
    _transfer_fdi_magnitudes(enriched)
    scores = {s.get("id", ""): int(s.get("_score", compute_signal_score(s))) for s in enriched}

    # Stamp narrative title on every enriched signal
    from packagers.narrative import narrative_title as _narrative_title
    for sig in enriched:
        sig["_narrative_title"] = _narrative_title(
            kind=sig.get("kind", ""),
            country=sig.get("_country", ""),
            detail=sig.get("_detail", ""),
            score=sig.get("_score", 0),
            band=sig.get("_band", "monitor"),
            n_sources=sig.get("_n_sources", 0),
        )

    # Select lead story
    lead_signal, supporting, lead_rationale = select_lead(enriched, scores)

    # Build narrative intro
    run_date = generated_at.split(" ")[0] if " " in generated_at else generated_at
    if lead_signal:
        lc = extract_country(lead_signal)
        l_signals = [s for s in enriched if extract_country(s) == lc]
        l_sources = set()
        for s in l_signals:
            l_sources.update(s.get("sources", []))
        narrative_intro = (
            f"Lead: {lc}. "
            f"{len(l_signals)} converging signal(s) across {len(l_sources)} source(s). "
        )
        # Add kind labels for the cluster
        kind_labels = list(dict.fromkeys(
            str(KIND_LABELS.get(s.get("kind", ""), s.get("kind", "")))
            for s in l_signals
        ))
        if kind_labels:
            narrative_intro += f"Signals: {' + '.join(kind_labels)}."
    else:
        narrative_intro = "No strong country lead this cycle."
        lc = ""

    # Persist editorial state
    save_editorial_state(lc, enriched, scores)

    # Cycle summary
    cycle_summary = build_cycle_summary(enriched, state, lc)

    # Cross-signal context
    for sig in enriched:
        sig["_related"] = find_related_signals(sig, enriched)

    return {
        "enriched_signals": enriched,
        "lead_signal": lead_signal,
        "supporting_signals": supporting,
        "lead_rationale": lead_rationale,
        "narrative_intro": narrative_intro,
        "cycle_summary": cycle_summary,
        "generated_at": generated_at,
        "run_date": run_date,
        "total_raw_signals": len(signals),
        "state": state,
    }


# ── Convenience functions for channel packagers ────────────

def filter_by_kind(
    signals: list[dict[str, Any]],
    kinds: set[str],
) -> list[dict[str, Any]]:
    return [s for s in signals if s.get("kind") in kinds]


def rank_for(
    signals: list[dict[str, Any]],
    limit: int = 6,
    max_per_kind: int = 0,
    max_per_country: int = 0,
) -> list[dict[str, Any]]:
    """Rank and optionally diversify enriched signals."""
    ranked = sorted(signals, key=lambda s: s.get("_score", 0), reverse=True)
    if limit <= 0:
        return ranked
    if max_per_kind <= 0 and max_per_country <= 0:
        return ranked[:limit]

    selected: list[dict[str, Any]] = []
    kind_counts: dict[str, int] = defaultdict(int)
    country_counts: dict[str, int] = defaultdict(int)

    for sig in ranked:
        kind = sig.get("kind", "unknown")
        country = sig.get("_country", "Regional")
        if max_per_kind > 0 and kind_counts[kind] >= max_per_kind:
            continue
        if max_per_country > 0 and country_counts[country] >= max_per_country:
            continue
        selected.append(sig)
        kind_counts[kind] += 1
        country_counts[country] += 1
        if len(selected) >= limit:
            return selected

    # Fill remaining slots
    for sig in ranked:
        if sig not in selected and len(selected) < limit:
            selected.append(sig)
    return selected
