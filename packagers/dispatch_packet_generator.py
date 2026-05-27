#!/usr/bin/env python3
"""Dispatch Packet Generator — writes persona-specific dispatch packets.

Reads outbox/opportunity_dispatches.json, groups dispatches by persona_key,
and writes one markdown packet per persona under outbox/dispatch_packets/.

Each packet includes:
  - persona name and decision job
  - top routed dispatches for that persona
  - action checklist
  - feedback options
  - source/evidence references

Usage:
  python3 packagers/dispatch_packet_generator.py
"""

from __future__ import annotations

import json
from datetime import datetime, timezone
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
DISPATCHES_FILE = ROOT / "outbox" / "opportunity_dispatches.json"
PACKETS_DIR = ROOT / "outbox" / "dispatch_packets"

# Persona metadata for packet headers
PERSONA_META: dict[str, dict[str, str]] = {
    "diaspora_investor": {
        "label": "Diaspora Investor",
        "decision_job": "Capital deployment screening and market entry assessment",
        "channel_hint": "Email brief + Telegram",
    },
    "founder_operator": {
        "label": "Regional Founder/Operator",
        "decision_job": "Competitive positioning and capability mapping",
        "channel_hint": "Telegram",
    },
    "ecosystem_builder": {
        "label": "Ecosystem Builder",
        "decision_job": "Founder matching and ecosystem support prioritisation",
        "channel_hint": "Telegram",
    },
    "regional_operator": {
        "label": "Regional Operator",
        "decision_job": "Operational readiness and bid pipeline assessment",
        "channel_hint": "Telegram",
    },
    "procurement_watcher": {
        "label": "Procurement Watcher",
        "decision_job": "Project pipeline tracking and expression of interest preparation",
        "channel_hint": "Email brief",
    },
    "policy_media": {
        "label": "Policy/Media",
        "decision_job": "Briefing input and narrative lead sourcing",
        "channel_hint": "Telegram digest",
    },
    "tourism_logistics_operator": {
        "label": "Tourism/Logistics Operator",
        "decision_job": "Capacity planning and demand trajectory assessment",
        "channel_hint": "Telegram",
    },
    "operator_resilience": {
        "label": "Operations/Resilience",
        "decision_job": "Immediate operational readiness and response",
        "channel_hint": "Telegram/SMS alert",
    },
}


def generate_packet(persona_key: str, dispatches: list[dict]) -> str:
    """Generate a markdown dispatch packet for one persona."""
    meta = PERSONA_META.get(persona_key, {
        "label": persona_key.replace("_", " ").title(),
        "decision_job": "Review actionable intelligence",
        "channel_hint": "Telegram",
    })

    lines: list[str] = []
    lines.append(f"# Dispatch Packet — {meta['label']}")
    lines.append("")
    lines.append(f"**Decision job:** {meta['decision_job']}")
    lines.append(f"**Delivery channel:** {meta['channel_hint']}")
    lines.append(f"**Generated:** {datetime.now(timezone.utc).strftime('%b %d, %Y at %H:%M UTC')}")
    lines.append(f"**Dispatches in this packet:** {len(dispatches)}")
    lines.append("")
    lines.append("---")
    lines.append("")

    if not dispatches:
        lines.append("_No active dispatches for this persona this cycle._")
        lines.append("")
        return "\n".join(lines)

    lines.append(f"## Dispatches ({len(dispatches)})")
    lines.append("")

    for i, d in enumerate(dispatches, 1):
        title = d.get("title", "Untitled")
        dispatch_id = d.get("dispatch_id", "")
        country = d.get("country_cluster", "")
        confidence = d.get("confidence_display", "")
        action = d.get("recommended_action", "")
        evidence = d.get("evidence_summary", "")
        detail = d.get("detail", "")
        grade = d.get("evidence_grade", "")
        freshness = d.get("freshness", "")
        status = d.get("feedback_status", "awaiting")
        risk_flags = d.get("risk_flags", [])
        channel = d.get("channel", "")
        action_window = d.get("action_window", "")
        decision_influence = d.get("decision_influence", "")
        rationale = d.get("routing_rationale", "")

        lines.append(f"### {i}. {title}")
        lines.append("")
        lines.append(f"**ID:** `{dispatch_id}` | **Country:** {country} | **Confidence:** {confidence}")
        lines.append(f"**Channel:** {channel} | **Window:** {action_window} | **Freshness:** {freshness}")
        lines.append(f"**Feedback status:** {status}")
        lines.append("")
        lines.append(f"**Evidence:** {evidence}")
        lines.append(f"**Detail:** {detail}")
        lines.append(f"**Grade:** {grade}")
        lines.append("")
        lines.append(f"**Recommended action:** {action}")
        if decision_influence:
            lines.append(f"**Decision to influence:** {decision_influence}")
        if rationale:
            lines.append(f"**Routing rationale:** {rationale}")
        if risk_flags:
            lines.append(f"**Risk flags:** {'; '.join(risk_flags)}")
        lines.append("")

    lines.append("---")
    lines.append("")
    lines.append("## Action Checklist")
    lines.append("")
    lines.append("- [ ] Review each dispatch and validate evidence")
    lines.append("- [ ] Prioritise by confidence score (higher = more actionable)")
    lines.append("- [ ] Take recommended action or route to relevant contact")
    lines.append("- [ ] Provide feedback: forwarded, replied, opened, or ignored")
    lines.append("")

    lines.append("## Feedback Options")
    lines.append("")
    lines.append("Each dispatch accepts feedback via the intake system:")
    lines.append("")
    lines.append("```bash")
    lines.append("python3 packagers/feedback_intake.py --dispatch-id <ID> --status forwarded|replied|opened|ignored --note \"...\"")
    lines.append("```")
    lines.append("")
    lines.append("Feedback affects next-cycle ranking: forwarded (+8), replied (+5),")
    lines.append("opened (+2), ignored (-2).")
    lines.append("")

    lines.append("## Sources")
    lines.append("")
    lines.append("Dispatches in this packet are sourced from:")
    lines.append("")
    lines.append("- World Bank FDI indicators (net inflows)")
    lines.append("- IDB Open Data (Caribbean datasets)")
    lines.append("- NOAA NWS (weather alerts)")
    lines.append("- NDBC Buoys (marine conditions)")
    lines.append("- CARICOM Statistics (WordPress REST API)")
    lines.append("- CDB (procurement notices via RSS)")
    lines.append("- NHC (storm tracking)")
    lines.append("")
    lines.append("Cross-source merger validates signals across multiple sources")
    lines.append("before dispatch generation.")
    lines.append("")

    return "\n".join(lines)


def generate_packets(dispatches: list[dict]) -> dict[str, int]:
    """Group dispatches by persona_key and write one packet per persona.

    Returns: {persona_key: dispatch_count}
    """
    PACKETS_DIR.mkdir(parents=True, exist_ok=True)

    # Group by persona_key
    groups: dict[str, list[dict]] = {}
    for d in dispatches:
        pk = d.get("persona_key", "unknown")
        groups.setdefault(pk, []).append(d)

    # Sort each group by confidence descending
    for pk in groups:
        groups[pk].sort(key=lambda x: x.get("confidence_score", 0), reverse=True)

    persona_counts: dict[str, int] = {}
    for persona_key in sorted(groups.keys()):
        pk_dispatches = groups[persona_key]
        packet_text = generate_packet(persona_key, pk_dispatches)
        safe_name = persona_key.replace("/", "-").replace(" ", "_")
        packet_path = PACKETS_DIR / f"{safe_name}.md"
        packet_path.write_text(packet_text, encoding="utf-8")
        persona_counts[persona_key] = len(pk_dispatches)
        print(f"  Wrote {packet_path} ({len(pk_dispatches)} dispatches)")

    # Also update a manifest-style index
    index_path = PACKETS_DIR / "README.md"
    index_lines = [
        "# Dispatch Packets",
        "",
        f"Generated: {datetime.now(timezone.utc).strftime('%b %d, %Y at %H:%M UTC')}",
        f"Total personas: {len(persona_counts)}",
        f"Total dispatches across all packets: {sum(persona_counts.values())}",
        "",
        "| Persona | Dispatches | Packet |",
        "|---------|-----------|--------|",
    ]
    for pk in sorted(persona_counts.keys()):
        safe_name = pk.replace("/", "-").replace(" ", "_")
        label = PERSONA_META.get(pk, {}).get("label", pk)
        index_lines.append(f"| {label} | {persona_counts[pk]} | `{safe_name}.md` |")
    index_lines.append("")
    index_path.write_text("\n".join(index_lines) + "\n", encoding="utf-8")
    print(f"  Wrote {index_path}")

    return persona_counts


def main() -> None:
    if not DISPATCHES_FILE.exists():
        print("No dispatches file found. Run opportunity_dispatch.py first.")
        return

    data = json.loads(DISPATCHES_FILE.read_text(encoding="utf-8"))
    dispatches = data.get("dispatches", [])
    if not dispatches:
        print("No dispatches found in opportunity_dispatches.json.")
        return

    print(f"Generating dispatch packets from {len(dispatches)} dispatches...")
    counts = generate_packets(dispatches)
    print(f"Done: {len(counts)} persona packets written to {PACKETS_DIR}")


if __name__ == "__main__":
    main()