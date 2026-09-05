#!/usr/bin/env python3
"""Cross-cluster regional thesis generator for Abeng.

Produces one narrative paragraph per cycle that connects the dots
between investment momentum, risk flags, and timing relevance.

This makes the system feel like intelligence (connected insights),
not a list (independent data points).
"""

from __future__ import annotations

import json
import re
import sys
from datetime import date
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

# ── Helpers ────────────────────────────────────────────────

def _load_enriched(path: Path | None = None) -> list[dict[str, Any]]:
    """Load composite signals; if not available, run enrichment."""
    if path is None:
        path = ROOT / "data" / "composite" / "latest.json"

    from packagers.editorial_enrichment import enrich_signals

    if not path.exists():
        return []

    raw = json.loads(path.read_text(encoding="utf-8"))
    signals = raw if isinstance(raw, list) else raw.get("signals", [])
    if not signals:
        return []

    editorial = enrich_signals(signals, date.today().isoformat())
    return editorial.get("enriched_signals", [])


def _mag_str(detail: str) -> str:
    """Extract and format magnitude from detail string."""
    m = re.search(r"([\d.]+)%", detail)
    return f"+{m.group(1)}%" if m else detail


# ── Thesis construction ────────────────────────────────────

def build_regional_thesis(
    enriched: list[dict[str, Any]],
    why_now_context: dict[str, Any] | None = None,
    lead_signal: dict[str, Any] | None = None,
) -> dict[str, Any]:
    """Build a cross-cluster regional thesis.

    Returns dict with:
    - thesis: narrative paragraph
    - capital_momentum: list of top investment signals
    - risk_flags: list of vulnerability signals
    - timing: seasonal/event context line
    - recommendations: list of actionable next steps
    """
    if not enriched:
        return {
            "thesis": "No enriched signals available this cycle.",
            "capital_momentum": [],
            "risk_flags": [],
            "timing": "",
            "recommendations": [],
        }

    # ── Group by kind ──
    enhanced = sorted(
        [s for s in enriched if s.get("kind") == "enhanced_investment"],
        key=lambda s: s.get("_score", 0), reverse=True,
    )
    regular_invest = sorted(
        [s for s in enriched if s.get("kind") == "investment_signal"],
        key=lambda s: s.get("_score", 0), reverse=True,
    )
    vulnerabilities = [
        s for s in enriched if s.get("kind") == "economic_vulnerability"
    ]
    pipeline = [
        s for s in enriched if s.get("kind") == "development_pipeline"
    ]
    tourism = [s for s in enriched if s.get("kind") == "tourism_impact"]

    # ── Capital momentum ──
    capital_items: list[dict[str, Any]] = []
    for sig in (enhanced + regular_invest):
        capital_items.append({
            "country": sig.get("_country", ""),
            "kind": sig.get("kind", ""),
            "magnitude": _mag_str(sig.get("_detail", "")),
            "score": sig.get("_score", 0),
            "narrative_title": sig.get("_narrative_title", ""),
        })

    # Sort by score desc, then magnitude desc
    def _mag_num(item):
        m = re.search(r"([\d.]+)", item.get("magnitude", ""))
        return float(m.group(1)) if m else 0
    capital_items.sort(key=lambda c: (c.get("score", 0), _mag_num(c)), reverse=True)

    # ── Risk flags ──
    risk_items: list[dict[str, Any]] = []
    for sig in vulnerabilities:
        risk_items.append({
            "country": sig.get("_country", ""),
            "magnitude": _mag_str(sig.get("_detail", "")),
            "score": sig.get("_score", 0),
        })
    # Also flag investment countries that have vulnerability
    sig_countries = {c["country"] for c in capital_items}
    vuln_countries = {r["country"] for r in risk_items}
    conflicted = sig_countries & vuln_countries

    # ── Build narrative thesis ──
    parts: list[str] = []

    # Sentence 1: Capital momentum direction
    if capital_items:
        top = capital_items[:3]
        lead_country = top[0]["country"] if top else ""
        lead_mag = top[0]["magnitude"] if top else ""
        parts.append(
            f"Capital momentum is strongest in {lead_country} ({lead_mag}), "
            f"followed by {', '.join(t['country'] for t in top if t['country'] != lead_country)}. "
        )

    # Sentence 2: Risk + cross-reference
    if conflicted:
        c_list = " and ".join(sorted(conflicted))
        parts.append(
            f"However, {c_list} also carry elevated vulnerability indicators — "
            f"investment signals from these countries require deeper diligence "
            f"before committing capital. "
        )
    elif risk_items:
        r_names = ", ".join(r["country"] for r in risk_items[:3])
        parts.append(
            f"Separately, {r_names} show elevated economic vulnerability — "
            f"relevant for portfolio monitoring and resilience planning. "
        )

    # Sentence 3: Pipeline / tourism context
    if pipeline:
        p = pipeline[0]
        parts.append(
            f"Development pipeline remains active ({p.get('_detail', 'procurements available')}) — "
            f"the bidding window is open for project-based entry."
        )
    if tourism:
        t_names = ", ".join(t.get("_country", "") for t in tourism[:3] if t.get("_country"))
        if t_names:
            parts.append(
                f"Tourism-related growth signals are visible in {t_names} — "
                f"demand-side indicators for capacity planning."
            )

    # Sentence 4: Timing (why now)
    timing_line = ""
    if why_now_context:
        hl = why_now_context.get("headline", "")
        if hl and hl != "No urgent seasonal context this cycle":
            timing_line = hl

    thesis = " ".join(parts)

    # ── Recommendations ──
    recs: list[str] = []
    if capital_items:
        top_rec = capital_items[0]["narrative_title"]
        recs.append(f"Lead signal: {top_rec}")
    if conflicted:
        for c in sorted(conflicted):
            recs.append(f"Cross-reference: {c} investment + vulnerability — validate before deploying capital")
    if pipeline:
        recs.append(f"Procurement: {pipeline[0].get('_narrative_title', 'Review CDB/IDB pipeline')}")
    if timing_line:
        recs.append(f"Timing: {timing_line}")

    return {
        "thesis": thesis.strip(),
        "capital_momentum": capital_items[:6],
        "risk_flags": risk_items,
        "conflicted_countries": sorted(conflicted),
        "timing": timing_line,
        "recommendations": recs,
    }


def write_thesis_output(
    enriched: list[dict[str, Any]] | None = None,
    why_now_context: dict[str, Any] | None = None,
    lead_signal: dict[str, Any] | None = None,
) -> Path:
    """Build and write the regional thesis to outbox."""
    if enriched is None:
        enriched = _load_enriched()

    thesis = build_regional_thesis(enriched, why_now_context, lead_signal)

    from datetime import datetime, timezone

    lines: list[str] = [
        "# Regional Thesis — Abeng",
        "",
        f"Generated: {datetime.now(timezone.utc).strftime('%Y-%m-%d %H:%M UTC')}",
        "",
        thesis["thesis"],
        "",
    ]

    if thesis["timing"]:
        lines.append(f"**Why now:** {thesis['timing']}")
        lines.append("")

    if thesis["recommendations"]:
        lines.append("## Recommended Actions")
        lines.append("")
        for r in thesis["recommendations"]:
            lines.append(f"- {r}")
        lines.append("")

    if thesis["capital_momentum"]:
        lines.append("## Capital Momentum (Top Signals)")
        lines.append("")
        for item in thesis["capital_momentum"]:
            lines.append(f"- **{item['country']}**: {item['narrative_title']} ({item['score']}/100)")
        lines.append("")

    if thesis["conflicted_countries"]:
        lines.append("## ⚠️ Conflict Flags (Investment + Vulnerability)")
        lines.append("")
        for c in thesis["conflicted_countries"]:
            lines.append(f"- **{c}**: cross-reference investment and vulnerability signals")
        lines.append("")

    if thesis["risk_flags"]:
        lines.append("## Vulnerability Monitoring")
        lines.append("")
        for r in thesis["risk_flags"]:
            lines.append(f"- **{r['country']}**: {r['magnitude']} ({r['score']}/100)")
        lines.append("")

    path = ROOT / "outbox" / "regional_thesis.md"
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text("\n".join(lines).rstrip() + "\n", encoding="utf-8")
    return path


def main() -> None:
    """CLI entry point."""
    from packagers.editorial_calendar import get_why_now_context

    why_now = get_why_now_context()
    enriched = _load_enriched()
    lead = enriched[0] if enriched else None

    path = write_thesis_output(enriched, why_now, lead)
    print(f"Wrote {path}")


if __name__ == "__main__":
    main()
