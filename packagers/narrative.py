#!/usr/bin/env python3
"""Shared narrative title generator for Caribbean Signal OS.

Extracted from opportunity_dispatch.py so all channel packagers and
editorial enrichment can produce the same editorial-quality titles.

Every function here is self-contained — no imports from other packagers.
"""

from __future__ import annotations

import re


def narrative_title(
    kind: str,
    country: str,
    detail: str,
    score: int = 50,
    band: str = "monitor",
    n_sources: int = 0,
    is_regional: bool = False,
    regional_count: int = 0,
) -> str:
    """Generate editorial-quality dispatch title instead of raw merger summary.

    Each title answers 'why this matters this week' with varied language
    across signals to avoid the same boilerplate repeating.
    """
    # Normalise band (may come in as title-cased _band_label)
    band = band.lower().strip() if isinstance(band, str) else "monitor"
    # Extract magnitude percentage from detail string
    pct_match = re.search(r"([\d.]+)%", detail)
    pct = pct_match.group(1) if pct_match else ""

    # ── Regional titles (aggregated across countries) ─────
    if is_regional:
        if kind == "enhanced_investment":
            return (
                f"Capital convergence: {regional_count} Caribbean economies "
                f"showing multi-source investment momentum"
            )
        if kind == "investment_signal":
            return (
                f"Regional FDI snapshot: {regional_count} countries "
                f"with active capital movement"
            )
        if kind == "tourism_impact":
            return (
                f"Tourism demand broadening: {regional_count} economies "
                f"showing growth indicators"
            )
        return (
            f"Regional signal cluster: {regional_count} countries — "
            f"{kind.replace('_', ' ')}"
        )

    # ── Per-country titles ─────────────────────────────────
    if kind == "enhanced_investment":
        # "multi-source" is only true when more than one source actually
        # confirms this country. n_sources counts corroborating sources, not
        # regional datasets that happen to exist this cycle.
        corroborated = n_sources > 1
        if band == "immediate":
            if pct and float(pct) >= 300:
                if corroborated:
                    return f"{country}: +{pct}% multi-source capital surge — market entry window open"
                return f"{country}: +{pct}% capital surge on a single official source — market entry window open"
            if corroborated:
                return f"{country}: +{pct}% multi-source investment validated — opportunity active"
            return f"{country}: +{pct}% investment movement, one source — needs corroboration"
        if band == "validation":
            src = f" across {n_sources} sources" if n_sources > 1 else ""
            return f"{country}: +{pct}% FDI momentum validated{src} — cross-reference before deploying"
        return f"{country}: +{pct}% early capital convergence — tracking next cycle"

    if kind == "investment_signal":
        if band in ("immediate", "validation"):
            return f"{country}: FDI trending at +{pct}% — screening trigger active"
        return f"{country}: FDI movement at +{pct}% — needs further validation"

    if kind == "development_pipeline":
        c = re.search(r"(\d+)", detail)
        count = c.group(1) if c else ""
        return f"{country}: {count} active procurements — bidding window open"

    if kind == "economic_vulnerability":
        return f"{country}: economic stress indicators rising — portfolio review recommended"

    if kind == "tourism_impact":
        return f"{country}: GDP growth signals expanding tourist economy"

    if kind == "food_security":
        return f"{country}: food supply indicators shifting — supply chain implications"

    # Operational alerts — keep concise
    if kind in ("active_storm", "cyclone_risk", "tropical_development", "maritime_hazard"):
        return f"{country}: {detail}"

    # Fallback: clean editorial line
    clipped = (detail[:117] + "...") if len(detail) > 120 else detail
    return f"{country}: {clipped}"