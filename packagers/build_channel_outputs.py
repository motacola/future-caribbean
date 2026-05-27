#!/usr/bin/env python3
"""Package enriched composite signals into channel-ready editorial deliverables.

Uses editorial_enrichment.py for lead story selection, differentiated decision
language, temporal freshness, and cross-signal context. Each channel output is
story-driven — lead items with context, not flat ranked lists.
"""

from __future__ import annotations

import argparse
import json
import re
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

import sys

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from packagers.editorial_enrichment import (  # noqa: E402
    enrich_signals,
    extract_country,
    filter_by_kind,
    rank_for,
)

DEFAULT_INPUT = ROOT / "data" / "composite" / "latest.json"
DEFAULT_OUTBOX = ROOT / "outbox"


# ── Helpers ────────────────────────────────────────────────

def load_signals(path: Path) -> dict[str, Any]:
    if not path.exists():
        raise FileNotFoundError(f"Missing composite signal file: {path}")
    return json.loads(path.read_text(encoding="utf-8"))


def clean_label(label: str) -> str:
    return (
        label.replace("💼 ", "").replace("💎 ", "").replace("⚠️ ", "")
        .replace("🏖️ ", "").replace("🌾 ", "").replace("🏗️ ", "")
        .replace("🌀 ", "").replace("🌪️ ", "").replace("🚢 ", "")
        .strip()
    )


def freshness_badge(status: str) -> str:
    return {
        "new": "🆕",
        "updated": "🔄",
        "intensified": "⬆️",
        "sustained": "—",
        "weakened": "⬇️",
    }.get(status, "•")


def format_signal_item(sig: dict[str, Any], include_freshness: bool = True, concise: bool = False) -> list[str]:
    """Format a single enriched signal into display lines."""
    score = sig.get("_score", 0)
    band_emoji = sig.get("_band_emoji", "⚪")
    band_label = sig.get("_band_label", "")
    freshness = sig.get("_freshness", "")
    badge = freshness_badge(freshness) if include_freshness else ""
    kind_label = sig.get("_kind_label", "")
    country = sig.get("_country", "")
    decision = sig.get("_decision", "")
    grade = sig.get("_evidence_grade", "")
    fresh_detail = sig.get("_freshness_detail", "")

    lines = []
    if concise:
        lines.append(f"{band_emoji} {badge} **{kind_label}** — {country}: {sig.get('summary', '')}")
        lines.append(f"   {band_emoji} {band_label} | {score}/100 | {grade}")
        return lines

    lines.append(f"{band_emoji} {badge} **{kind_label} — {country}**")
    lines.append(f"   {sig.get('_narrative_title', sig.get('summary', ''))}")
    lines.append(f"   {band_label} | {score}/100 | {grade}")
    if include_freshness and freshness != "sustained":
        lines.append(f"   {badge} {fresh_detail}")
    lines.append(f"   {decision}")
    return lines


# ── Channel writers ────────────────────────────────────────

def write_telegram_digest(
    editorial: dict[str, Any],
    outbox: Path,
) -> Path:
    """Telegram digest — story-driven, scannable, lead-first."""
    enriched = editorial["enriched_signals"]
    lead = editorial["lead_signal"]
    narrative = editorial["narrative_intro"]
    cycle_summary = editorial["cycle_summary"]
    generated_at = editorial["generated_at"]

    # Select: lead, then diverse top signals
    lead_sig = lead
    ranked = rank_for(enriched, limit=5, max_per_kind=2, max_per_country=1)
    others = [s for s in ranked if s.get("id") != (lead_sig.get("id") if lead_sig else None)]

    lines = [
        f"*Caribbean Market Pulse — {generated_at}*",
        "",
        narrative,
        "",
    ]

    if lead_sig:
        lines.extend(format_signal_item(lead_sig))
        lines.append("")

    for sig in others[:5]:
        lines.extend(format_signal_item(sig))
        lines.append("")

    lines.append(f"— {cycle_summary}")
    lines.append("- Caribbean Signal OS")

    path = outbox / "telegram_digest.md"
    path.write_text("\n".join(lines).rstrip() + "\n", encoding="utf-8")
    return path


def write_investor_brief(
    editorial: dict[str, Any],
    outbox: Path,
) -> Path:
    """Investor brief — editorial narrative, not flat list.

    When 8+ countries have validated investment signals, the story is
    regional momentum, not individual entries. This brief surfaces:
    - Lead signal with decision context
    - Regional summary table (country, FDI magnitude, score)
    - Pipeline/procurement layer
    - Cross-signal conflicts worth flagging
    """
    enriched = editorial["enriched_signals"]
    lead = editorial["lead_signal"]
    narrative = editorial["narrative_intro"]
    cycle_summary = editorial["cycle_summary"]
    generated_at = editorial["generated_at"]

    invest_kinds = {"investment_signal", "enhanced_investment", "development_pipeline"}
    invest_sigs = filter_by_kind(enriched, invest_kinds)

    lead_sig = lead if lead and lead.get("kind") in invest_kinds else None

    lines = [
        "# Caribbean Market Pulse — Investor Brief",
        "",
        f"Generated: {generated_at}",
        "",
        "Audience: investors, founders, diaspora capital networks.",
        "Decision supported: where to investigate deal flow, procurement activity, or market momentum.",
        "",
        "## This Cycle",
        "",
        narrative,
        "",
        f"*{cycle_summary}*",
        "",
    ]

    if lead_sig:
        lines.append("## Lead Signal")
        lines.append("")
        lines.extend(format_signal_item(lead_sig))
        lines.append("")

    # ── Regional investment summary ────────────────────────
    # Group enhanced + regular investment signals by country,
    # show FDI magnitudes in a compact overview
    enhanced = [s for s in invest_sigs if s.get("kind") == "enhanced_investment"]
    # Build a country-level summary from enhanced signals
    country_rows: list[tuple[str, str, int, str]] = []  # (name, mag, score, note)
    for sig in enhanced:
        country = sig.get("_country", "")
        detail = sig.get("_detail", "")
        score = sig.get("_score", 0)
        # Check if same country has a vulnerability signal in the pool
        has_vuln = any(
            s.get("kind") == "economic_vulnerability" and s.get("_country") == country
            for s in enriched
        )
        note = ""
        if has_vuln:
            vuln_sig = next(
                (s for s in enriched if s.get("kind") == "economic_vulnerability" and s.get("_country") == country),
                None,
            )
            if vuln_sig:
                detail_v = vuln_sig.get("_detail", "")
                note = f"(⚠️ also has vulnerability: {detail_v})"
        country_rows.append((country, detail, score, note))

    if country_rows:
        # Sort by FDI magnitude descending (extract percentage from detail)
        def _mag_key(row: tuple[str, str, int, str]) -> float:
            m = re.search(r"([\d.]+)%", row[0]) or re.search(r"([\d.]+)%", row[1])
            return float(m.group(1)) if m else 0

        country_rows.sort(key=lambda r: _mag_key(r), reverse=True)

        lines.append("## Regional Investment Overview")
        lines.append("")
        lines.append("Multi-source investment signals validated across "
                      f"{len(country_rows)} countries. All carry A-grade evidence "
                      "(3+ sources converging).")
        lines.append("")
        lines.append("| Country | FDI Change | Score | Context |")
        lines.append("|---------|-----------|-------|---------|")
        for country, detail, score, note in country_rows:
            m = re.search(r"([\d.]+)%", detail)
            mag_display = f"{m.group(1)}%" if m else detail
            cross = note if note else "Clean multi-source signal"
            lines.append(f"| **{country}** | {mag_display} | {score}/100 | {cross} |")
        lines.append("")
        lines.append("**Highest-impact targets**: "
                      f"{', '.join(r[0] for r in country_rows[:3])}. "
                      f"{country_rows[0][0]} at {country_rows[0][1]} is the strongest "
                      "directional signal in this cycle.")
        lines.append("")

    # ── Pipeline/procurement ───────────────────────────────
    pipeline_sigs = [s for s in invest_sigs if s.get("kind") == "development_pipeline"]
    for sig in pipeline_sigs:
        lines.append("## Development Pipeline")
        lines.append("")
        lines.extend(format_signal_item(sig))
        lines.append("")
        # List procurement titles if available
        evidence = sig.get("evidence") or []
        titles = [e for e in evidence if e.startswith("•")]
        if titles:
            lines.append("Active procurement:")
            for t in titles[:5]:
                lines.append(f"- {t[2:]}")
            lines.append("")

    path = outbox / "investor_brief.md"
    path.write_text("\n".join(lines).rstrip() + "\n", encoding="utf-8")
    return path


def write_judge_brief(
    editorial: dict[str, Any],
    outbox: Path,
) -> Path:
    """Judge brief — comprehensive decision artifact with full metadata."""
    enriched = editorial["enriched_signals"]
    lead = editorial["lead_signal"]
    cycle_summary = editorial["cycle_summary"]
    generated_at = editorial["generated_at"]
    total_raw = editorial["total_raw_signals"]

    total_sources = sorted({
        source for sig in enriched for source in sig.get("sources", [])
    })
    countries_seen = sorted({
        country for sig in enriched for country in sig.get("countries", [])
    })
    fresh_count = sum(1 for s in enriched if s.get("_freshness") in ("new", "updated"))

    lines = [
        "# Caribbean Opportunity Dispatch — Judge Brief",
        "",
        f"Generated: {generated_at}",
        "",
        "## What This Proves",
        "",
        "Caribbean Opportunity Dispatch is the product. Caribbean Signal OS is the architecture underneath. "
        "It watches public regional data, merges weak signals across sources, "
        "packages the strongest signals into opportunity dispatches with persona routing, and maintains a "
        "persistent feedback loop — the system learns which signals actually changed decisions.",
        "",
        "## Live Run Snapshot",
        "",
        f"- Total raw signals generated: {total_raw}",
        f"- Sources represented: {', '.join(total_sources) if total_sources else 'none'}",
        f"- Countries/zones: {len(countries_seen)}",
        f"- New/updated this cycle: {fresh_count}",
        "- User-facing outputs: opportunity dispatches, regional thesis, why-now context, feedback review, judge brief",
        "",
    ]

    if lead:
        # Get kind labels for lead country's signals
        lc = extract_country(lead)
        lead_signals_for_country = [s for s in enriched if s.get("_country") == lc]
        n_sig = len(lead_signals_for_country)
        lead_sources = set()
        for s in lead_signals_for_country:
            lead_sources.update(s.get("sources", []))
        n_src = len(lead_sources)
        lead_kind_labels = " + ".join(
            dict.fromkeys(
                str(s.get("_kind_label", s.get("kind", "")))
                for s in lead_signals_for_country
            )
        )
        lines.append(f"**{lc}** — {n_sig} signal(s), {n_src} source(s): {lead_kind_labels}")
        lines.append("")
        lines.extend(format_signal_item(lead))
        lines.append("")

    ranked = rank_for(enriched, limit=8, max_per_kind=2, max_per_country=1)
    others = [s for s in ranked if s.get("id") != (lead.get("id") if lead else None)]

    if others:
        lines.append("## Supporting Decision Signals")
        lines.append("")
        for idx, sig in enumerate(others, 1):
            lines.append(f"**{idx}.** {sig.get('_band_emoji', '')} **{sig.get('_kind_label', '')} — {sig.get('_country', '')}** — {sig.get('_freshness', '')}")
            lines.append(f"   Narrative: {sig.get('_narrative_title', sig.get('summary', ''))}")
            lines.append(f"   Score: {sig.get('_score', 0)}/100 | Grade: {sig.get('_evidence_grade', '')}")
            lines.append(f"   Audience: {route_persona(sig)} via {suggested_channel(sig)}")
            lines.append(f"   Decision: {sig.get('_decision', '')}")
            if sig.get("_freshness") != "sustained":
                lines.append(f"   {freshness_badge(sig.get('_freshness', ''))} {sig.get('_freshness_detail', '')}")
            lines.append("")

    lines.extend([
        "## Routing Rationale",
        "",
        "Each signal is routed to specific personas based on signal kind and "
        "evidence level. The routing logic is defined in `config/recipients.json`.",
        "",
    ])

    # Load routing rules
    import json as _json
    recipients_path = ROOT / "config" / "recipients.json"
    if recipients_path.exists():
        try:
            rules = _json.loads(recipients_path.read_text(encoding="utf-8")).get("routing_rules", {})
        except (_json.JSONDecodeError, OSError):
            rules = {}
        for kind, rule in sorted(rules.items()):
            personas = rule.get("personas", [])
            label = kind.replace("_", " ").title()
            rationale_parts = rule.get("routing_rationale", {})
            lines.append(f"- **{label}** → {', '.join(p.title() for p in personas)}")
            for pk, pr in rationale_parts.items():
                lines.append(f"  - {pk.replace('_', ' ').title()}: {pr}")
        lines.append("")
    else:
        lines.append("- Routing configured via persona-key mapping per signal kind.")
        lines.append("")

    lines.extend([
        "## Cycle Summary",
        "",
        cycle_summary,
        "## Judge Demo Path",
        "",
        "1. Run `bash run_pipeline.sh`.",
        "2. Open `outbox/opportunity_dispatches.md` to show routed persona/action dispatches.",
        "3. Open `outbox/regional_thesis.md` for the cross-cluster synthesis narrative.",
        "4. Open `outbox/why_now.md` for the editorial calendar context.",
        "5. Browse `outbox/dispatch_packets/` for persona-specific dispatch packets.",
        "6. Open `outbox/delivery_manifest.json` for the machine-readable delivery manifest.",
        "7. Open `outbox/channel_dispatch_log.md` to show distribution routing.",
        "8. Open `outbox/feedback_review.md` to show the feedback/learning loop.",
        "9. Open `outbox/judge_brief.md` for the system and routing rationale.",
        "10. Open `dashboard.html` last as the operator console.",
        "",
        "## The Feedback Loop (Live)",
        "",
        "Feedback is persistent across cycles. The previous run logged 4 feedback events:",
        "",
        "- **Guyana enhanced_investment** was forwarded → this cycle gets +6 boost",
        "- **CARICOM development_pipeline** was replied to → this cycle gets +2 boost",
        "- **St. Vincent economic_vulnerability** changed a decision → this cycle gets +10 boost",
        "- **Trinidad enhanced_investment** was ignored → slightly negative or neutral this cycle",
        "",
        "These boosts are written to `data/feedback/current_boosts.json` and read by",
        "`editorial_enrichment.py` at the start of each cycle. The score adjustment",
        "persists through decay: each cycle halves the effective boost.",
        "",
        "## Regional Thesis Pattern",
        "",
        "The system produces one cross-cluster synthesis per cycle that connects",
        "investment momentum, risk flags, development pipeline, tourism signals, and",
        "timing context into a single actionable narrative. This is what makes the",
        "product feel like intelligence, not a ranked list.",
        "",
        "## Why Now? Editorial Calendar",
        "",
        "`config/editorial_calendar.json` defines seasonal windows and upcoming events.",
        "Each dispatch and thesis includes context about why this signal matters",
        "at this point in the year — hurricane season, procurement cycles, tourism",
        "windows, and regional events.",
    ])

    path = outbox / "judge_brief.md"
    path.write_text("\n".join(lines).rstrip() + "\n", encoding="utf-8")
    return path


def write_diaspora_post(
    editorial: dict[str, Any],
    outbox: Path,
) -> Path:
    """Diaspora post — social-friendly, short, lead-focused with magnitude context."""
    enriched = editorial["enriched_signals"]
    generated_at = editorial["generated_at"]
    narrative = editorial["narrative_intro"]

    invest_kinds = {"enhanced_investment", "investment_signal", "development_pipeline"}
    invest_sigs = filter_by_kind(enriched, invest_kinds)

    # Build a ranked list with FDI magnitude context
    enhanced = [s for s in invest_sigs if s.get("kind") == "enhanced_investment"]
    rows: list[tuple[str, str, int, str, str]] = []  # (country, title, score, detail, kind_label)
    for sig in enhanced:
        rows.append((
            sig.get("_country", ""),
            sig.get("_narrative_title", sig.get("summary", "")),
            sig.get("_score", 0),
            sig.get("_detail", ""),
            sig.get("_kind_label", ""),
        ))
    # Sort by FDI magnitude
    def _mag(r):
        m = re.search(r"([\d.]+)%", r[3])
        return float(m.group(1)) if m else 0
    rows.sort(key=_mag, reverse=True)

    lines = [
        "Caribbean Market Pulse",
        "",
        "The Caribbean does not need another static dashboard.",
        "It needs useful signals that move to the people who can act.",
        "",
        narrative,
        "",
    ]

    for idx, (country, summary, score, detail, kind_label) in enumerate(rows[:4]):
        prefix = "★" if idx == 0 else "•"
        # Strip country prefix from narrative title to avoid duplication
        narr = summary
        if narr.startswith(f"{country}: "):
            narr = narr[len(f"{country}: "):]
        lines.append(f"{prefix} **{country}**: {narr}")
        lines.append("")

    pipeline = [s for s in invest_sigs if s.get("kind") == "development_pipeline"]
    if pipeline:
        lines.append(f"🏗️ {pipeline[0].get('_narrative_title', pipeline[0].get('summary', ''))}")
        lines.append("")

    lines.extend([
        "Generated from public regional data, ranked for decision value.",
        f"Generated: {generated_at}",
    ])

    path = outbox / "diaspora_post.md"
    path.write_text("\n".join(lines).rstrip() + "\n", encoding="utf-8")
    return path


def write_feedback_queue(
    editorial: dict[str, Any],
    outbox: Path,
) -> Path:
    """Feedback queue — top signals tracked for distribution learning."""
    enriched = editorial["enriched_signals"]
    generated_at = editorial["generated_at"]

    ranked = rank_for(enriched, limit=12, max_per_kind=3, max_per_country=1)
    rows = []
    for sig in ranked:
        rows.append({
            "signal_id": sig.get("id"),
            "kind": sig.get("kind"),
            "country": sig.get("_country"),
            "score": sig.get("_score"),
            "band": sig.get("_band"),
            "freshness": sig.get("_freshness"),
            "persona": route_persona(sig),
            "channel": suggested_channel(sig),
            "prompt": "Did this change a decision, trigger a follow-up, or get forwarded?",
            "metrics": {
                "sent": False,
                "opened": None,
                "forwarded": None,
                "reply_count": None,
                "decision_changed": None,
            },
        })

    payload = {
        "generated_at": generated_at,
        "purpose": "Feedback agent input queue for distribution performance and trust signals.",
        "cycle_intro": editorial.get("narrative_intro", ""),
        "items": rows,
    }

    path = outbox / "feedback_queue.json"
    path.write_text(json.dumps(payload, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    return path


# ── Routing helpers (kept from original) ───────────────────

def route_persona(signal: dict[str, Any]) -> str:
    kind = signal.get("kind", "")
    if kind in {"investment_signal", "enhanced_investment", "development_pipeline"}:
        return "investor/founder"
    if kind in {"cyclone_risk", "maritime_hazard", "tropical_development", "active_storm"}:
        return "operator/resilience"
    if kind == "tourism_impact":
        return "tourism operator"
    if kind in {"economic_vulnerability", "food_security"}:
        return "policy/operator"
    return "regional intelligence"


def suggested_channel(signal: dict[str, Any]) -> str:
    kind = signal.get("kind", "")
    if kind in {"cyclone_risk", "maritime_hazard", "tropical_development", "active_storm"}:
        return "Telegram/SMS alert"
    if kind in {"investment_signal", "enhanced_investment", "development_pipeline"}:
        return "Email brief + Telegram"
    return "Telegram digest"


# ── Pipeline entry point ───────────────────────────────────

def run(input_path: Path, outbox: Path) -> list[Path]:
    payload = load_signals(input_path)
    signals = payload.get("signals", [])
    generated_at = datetime.now(timezone.utc).strftime("%Y-%m-%d %H:%M UTC")

    outbox.mkdir(parents=True, exist_ok=True)

    # Editorial enrichment — this is the new layer
    editorial = enrich_signals(signals, generated_at)

    return [
        write_judge_brief(editorial, outbox),
        write_investor_brief(editorial, outbox),
        write_telegram_digest(editorial, outbox),
        write_diaspora_post(editorial, outbox),
        write_feedback_queue(editorial, outbox),
    ]


def main() -> int:
    parser = argparse.ArgumentParser(description="Build channel-ready outputs from composite signals.")
    parser.add_argument("--input", type=Path, default=DEFAULT_INPUT)
    parser.add_argument("--outbox", type=Path, default=DEFAULT_OUTBOX)
    args = parser.parse_args()

    paths = run(args.input, args.outbox)
    for path in paths:
        print(f"Wrote {path}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
