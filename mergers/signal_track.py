"""Deterministic Opportunity vs Dislocation/Risk track for a signal kind.

Signal Fabric's composite signals carry a ``kind`` (e.g. ``investment_signal``,
``cyclone_risk``, ``food_security``). The product surface should let a reader
separate **opportunities** (capital, demand, capacity, market movement worth
acting on) from **dislocations / risks** (hazards, vulnerability, shocks) without
reclassifying or re-deriving the underlying signal.

This module is the single source of truth for that mapping. It is purely a
function of ``kind`` and changes only when a new detector is added — it never
invents a track for an unknown kind and never flips a known one without intent.

Track vocabulary (product language, not demo language):
  opportunity  — a move worth making; capital, demand, capacity, or market signal
  risk         — a hazard, vulnerability, or shock to be mitigated
"""

from __future__ import annotations

from typing import Iterable

# Kinds that represent a move worth making.
OPPORTUNITY_KINDS = {
    "investment_signal",
    "enhanced_investment",
    "development_pipeline",
    "tourism_impact",
    "supply_chain_signal",
    "port_activity_surge",
    "shipping_corridor",
    "ccrif_payout",          # a payout is a realised resilience outcome, not a hazard
    "eccb_credit_surge",
    "eccb_deposit_growth",
}

# Kinds that represent a hazard, vulnerability, or shock.
RISK_KINDS = {
    "cyclone_risk",
    "maritime_hazard",
    "economic_vulnerability",
    "food_security",
    "tropical_development",
    "active_storm",
    "port_congestion",
}

TRACK_OPPORTUNITY = "opportunity"
TRACK_RISK = "risk"


def track_for_kind(kind: str | None) -> str | None:
    """Map a signal kind to its track.

    Returns ``None`` for an unknown/missing kind so callers can surface
    "track not classified" rather than guessing. Every kind emitted by
    cross_source_merger is mapped; a new detector must be added here.
    """
    k = (kind or "").strip().lower()
    if k in OPPORTUNITY_KINDS:
        return TRACK_OPPORTUNITY
    if k in RISK_KINDS:
        return TRACK_RISK
    return None


def track_label(track: str | None) -> str:
    return {
        TRACK_OPPORTUNITY: "Opportunity",
        TRACK_RISK: "Dislocation / Risk",
    }.get(track or "", "Unclassified")


def annotated_kinds() -> dict[str, str | None]:
    """Every known kind → track, for tests and self-audits."""
    out: dict[str, str | None] = {}
    for k in OPPORTUNITY_KINDS:
        out[k] = TRACK_OPPORTUNITY
    for k in RISK_KINDS:
        out[k] = TRACK_RISK
    return out


def counts_by_track(kinds: Iterable[str]) -> dict[str, int]:
    out = {TRACK_OPPORTUNITY: 0, TRACK_RISK: 0, "unclassified": 0}
    for k in kinds:
        t = track_for_kind(k)
        if t is None:
            out["unclassified"] += 1
        else:
            out[t] += 1
    return out
