#!/usr/bin/env python3
"""Community Brief Renderer — plain-language Caribbean Opportunity Brief.

For WhatsApp, Instagram, X, and community channels.
No jargon. No "signal clusters" or "persona routes." Just what matters
for builders, business owners, and everyday Caribbean people.

Anya's gap: "simplify language for broader local reach"
"""

from __future__ import annotations

import json
import sys
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parents[1]
DESK_JSON = ROOT / "outbox" / "dispatch_desk.json"
OUTBOX_DIR = ROOT / "outbox"
BRIEF_FILE = OUTBOX_DIR / "community_brief.md"
MAX_BRIEF_CHARS = 4000  # ~3 WhatsApp messages worth


def load_json(path: Path, fallback: Any) -> Any:
    if not path.exists():
        return fallback
    try:
        return json.loads(path.read_text(encoding="utf-8"))
    except (json.JSONDecodeError, OSError):
        return fallback


def ensure_desk() -> dict[str, Any]:
    desk = load_json(DESK_JSON, {})
    if desk:
        return desk
    sys.path.insert(0, str(ROOT))
    from packagers.dispatch_desk import build, write_outputs  # noqa: PLC0415

    desk = build()
    write_outputs(desk)
    return desk


# ── Plain-language mappings ────────────────────────────────────

KIND_TO_PLAIN = {
    "enhanced_investment": "money flowing in from multiple sources — verified opportunity",
    "investment_signal": "foreign investment spiking — worth watching",
    "development_pipeline": "government/bank projects open for bidding",
    "food_security": "food supply chains shifting — agri/logistics opportunity",
    "economic_vulnerability": "economic stress rising — proceed with caution",
    "tourism_impact": "tourism economy growing — demand for services rising",
    "cyclone_risk": "storm risk elevated — prepare operations",
    "maritime_hazard": "rough seas alert — shipping/fishing affected",
    "active_storm": "named storm active — immediate precautions needed",
    "tropical_development": "storm brewing — watch and prepare",
    "supply_chain_signal": "supply chain corridor opening — logistics/procurement opportunity",
}


RISK_PLAIN = {
    "St. Vincent and the Grenadines also has vulnerability — validate before committing": (
        "⚠️ This island also shows economic stress — do extra homework before committing."
    ),
    "Elevated economic stress in St. Vincent and the Grenadines": (
        "⚠️ High unemployment — local purchasing power may be limited."
    ),
    "Elevated economic stress in Suriname": (
        "⚠️ High inflation — costs rising fast for locals and businesses."
    ),
}


ACTION_PLAIN = {
    "enhanced_investment": {
        "diaspora_investor": "If you deploy capital in the region, this is a top-tier lead — talk to local operators now.",
        "founder_operator": "New money = new competition AND new customers. Map your advantage before they arrive.",
        "ecosystem_builder": "Connect founders to this momentum. The window is open.",
        "default": "Serious money moving in. If you're building or investing here, pay attention.",
    },
    "investment_signal": {
        "diaspora_investor": "Early signal — not a green light yet. Start digging, don't deploy.",
        "founder_operator": "Investment noise in your market. Could mean competitors coming or demand growing.",
        "default": "Investment ticked up. Worth a screening call, not a wire transfer.",
    },
    "development_pipeline": {
        "regional_operator": "Real contracts up for grabs. If you can deliver, bid early.",
        "procurement_watcher": "CDB/IDB money on the table. Track the tenders.",
        "founder_operator": "Gov/bank spending direction = where the next opportunities are.",
        "default": "Government and development bank projects open. Service providers: this is your lane.",
    },
    "food_security": {
        "ecosystem_builder": "Food supply gaps = agri-tech and logistics opportunities. Back local founders here.",
        "policy_media": "Food prices and availability are stability signals. Track before crisis.",
        "default": "Regional food trade shifting. If you're in agri, logistics, or supply chain — look closer.",
    },
    "economic_vulnerability": {
        "diaspora_investor": "Risk flag. Reassess exposure. Don't double down without local eyes.",
        "policy_media": "Economic stress drives policy and headlines. Context for your reporting.",
        "default": "Economy showing strain. If you have money or operations here, review your position.",
    },
    "tourism_impact": {
        "tourism_logistics_operator": "Demand growing. Plan capacity — rooms, transport, experiences.",
        "founder_operator": "More tourists = more local spending. Build for that demand.",
        "default": "Tourism economy expanding. Hospitality, transport, experiences — demand is rising.",
    },
    "cyclone_risk": {
        "operator_resilience": "Pressure dropping + marine alert = mobilize now. 48-hour window.",
        "tourism_logistics_operator": "Storm risk = booking hits and route changes. Activate contingencies.",
        "default": "Bad weather likely. Secure assets, check comms, warn crews.",
    },
    "maritime_hazard": {
        "operator_resilience": "High winds confirmed. Adjust routes, secure vessels.",
        "tourism_logistics_operator": "Ferry/cargo delays likely. Communicate early with guests and suppliers.",
        "default": "Rough seas. Small craft stay in. Shipping: expect delays.",
    },
    "active_storm": {
        "operator_resilience": "Named storm. 24-hour response window. Deploy plan now.",
        "default": "Storm is real. Follow official emergency channels. Safety first.",
    },
    "tropical_development": {
        "operator_resilience": "System forming. 72-hour watch. Prep staged, don't panic.",
        "default": "Something brewing. Monitor NHC. Ready supplies and comms.",
    },
    "supply_chain_signal": {
        "regional_operator": "Real supply chain corridor open. Procurement active + seas calm = move now.",
        "procurement_watcher": "CDB projects aligned with stable shipping lanes. Corridor viable for logistics.",
        "founder_operator": "Supply chain gap + procurement pipeline = build warehousing, transport, or last-mile here.",
        "default": "Supply chain corridor opening. Logistics, warehousing, transport — real opportunity.",
    },
}


def plain_country(country: str) -> str:
    """Make country names feel local."""
    return country


def plain_action(kind: str, personas: list[dict]) -> str:
    """Extract the most relatable action for a regular person."""
    mapping = ACTION_PLAIN.get(kind, {})
    # Prefer founder/operator or default perspective for community brief
    for key in ("founder_operator", "default", "diaspora_investor", "ecosystem_builder"):
        if key in mapping:
            return mapping[key]
    return "Pay attention — something real is happening."


def plain_risk(risk_flags: list[str]) -> str | None:
    if not risk_flags:
        return None
    # Use first risk flag, translated
    for flag in risk_flags:
        if flag in RISK_PLAIN:
            return RISK_PLAIN[flag]
    return f"⚠️ {risk_flags[0]}"


def extract_magnitude(detail: str) -> str | None:
    """Pull out the % change number for context."""
    import re
    m = re.search(r"([\d.]+)%", detail)
    if m:
        return f"{m.group(1)}%"
    return None


def format_brief_item(cluster: dict[str, Any], idx: int) -> list[str]:
    """One plain-language paragraph per signal."""
    kind = cluster.get("signal_kind", "")
    country = cluster.get("country_cluster", "Caribbean")
    title = cluster.get("title", "")
    detail = cluster.get("detail", "")
    risk_flags = cluster.get("risk_flags", [])
    confidence = cluster.get("confidence_score", 0)
    freshness = cluster.get("freshness", "")
    evidence_grade = cluster.get("evidence_grade", "")

    # Skip Caribwide/regional rollups for community brief — focus on specific islands
    if country in ("Caribwide", "CARICOM", "Regional"):
        return []

    # Build the plain paragraph
    kind_plain = KIND_TO_PLAIN.get(kind, kind.replace("_", " "))
    magnitude = extract_magnitude(detail)
    action = plain_action(kind, cluster.get("personas", []))
    risk = plain_risk(risk_flags)

    # Confidence cue (very rough)
    conf_cue = ""
    if confidence >= 90:
        conf_cue = "🔴 High confidence — multiple sources agree"
    elif confidence >= 70:
        conf_cue = "🟡 Solid signal — some corroboration"
    elif confidence >= 50:
        conf_cue = "🟢 Early signal — worth watching"
    else:
        conf_cue = "⚪ Weak signal — low priority"

    # Freshness cue
    fresh_cue = ""
    if freshness == "new":
        fresh_cue = " (just picked up)"
    elif freshness == "weakened":
        fresh_cue = " (fading)"
    elif freshness == "sustained":
        fresh_cue = " (holding steady)"

    lines = []

    # Headline: Country + what's happening
    headline = f"**{plain_country(country)}**: {kind_plain}"
    if magnitude:
        headline += f" — {magnitude} movement"
    lines.append(f"{idx}. {headline}")

    # The "so what" in one sentence
    lines.append(f"   {action}{fresh_cue}")

    # Confidence + risk
    cue_line = f"   {conf_cue}"
    if risk:
        cue_line += f" | {risk}"
    lines.append(cue_line)

    # Light touch: evidence grade translated
    if "A" in evidence_grade:
        lines.append("   📊 Backed by multiple independent data sources")
    elif "B" in evidence_grade:
        lines.append("   📊 Cross-source validation")
    elif "C" in evidence_grade:
        lines.append("   📊 Single-source indicator — verify locally")

    lines.append("")  # spacer
    return lines


def build_community_brief() -> str:
    desk = ensure_desk()
    generated_at = desk.get("generated_at") or datetime.now(timezone.utc).strftime("%d %b %Y, %H:%M UTC")
    cycle_id = desk.get("cycle_id") or datetime.now(timezone.utc).strftime("%Y%m%d")
    clusters = desk.get("clusters", []) or []

    # Filter to country-specific signals only (skip regional rollups)
    country_clusters = [
        c for c in clusters
        if c.get("country_cluster") not in ("Caribwide", "CARICOM", "Regional")
    ]

    # Sort by confidence desc, then by magnitude desc
    def sort_key(c):
        mag = extract_magnitude(c.get("detail", "") or "")
        mag_val = float(mag.replace("%", "")) if mag else 0
        return (c.get("confidence_score", 0), mag_val)

    country_clusters.sort(key=sort_key, reverse=True)

    # Top 6 for community brief (fits in ~3 WhatsApp messages)
    top_clusters = country_clusters[:6]

    lines = [
        "🌴 **Caribbean Opportunity Brief** — what's moving this week",
        f"Cycle {cycle_id} • {generated_at}",
        "",
        "Plain-language signals for builders, business owners, and community leaders.",
        "No jargon. Just what matters for your next move.",
        "",
        "---",
        "",
    ]

    if top_clusters:
        for idx, cluster in enumerate(top_clusters, 1):
            lines.extend(format_brief_item(cluster, idx))
    else:
        lines.append("No country-specific signals this cycle.")
        lines.append("")

    # Why now — translated
    why_now = desk.get("why_now", [])
    if why_now:
        lines.extend([
            "---",
            "",
            "**Why this week matters:**",
        ])
        for item in why_now[:3]:
            # Strip emoji/markdown for plain text
            clean = item.replace("🔴 ", "").replace("🟡 ", "").replace("🟢 ", "")
            clean = clean.replace("**", "").replace("  —", " —")
            lines.append(f"• {clean}")
        lines.append("")

    # Footer
    lines.extend([
        "---",
        "",
        "**Want the full picture?**",
        "• Technical desk: `abeng.vercel.app` (judge/investor view)",
        "• Validation packs: pre-assembled diligence for each opportunity",
        "• Telegram: @caribbean_opportunity_dispatch (daily brief)",
        "",
        "Reply **STOP** to unsubscribe. Built by Future Caribbean Abeng.",
        "",
    ])

    text = "\n".join(lines).rstrip() + "\n"

    if len(text) > MAX_BRIEF_CHARS:
        text = text[:MAX_BRIEF_CHARS - 80].rsplit("\n", 1)[0] + "\n\n…trimmed for chat\n"

    return text


def build_social_snippets() -> dict[str, str]:
    """Generate platform-specific snippets from the brief."""
    desk = ensure_desk()
    clusters = desk.get("clusters", []) or []
    country_clusters = [
        c for c in clusters
        if c.get("country_cluster") not in ("Caribwide", "CARICOM", "Regional")
    ]

    def sort_key(c):
        mag = extract_magnitude(c.get("detail", "") or "")
        mag_val = float(mag.replace("%", "")) if mag else 0
        return (c.get("confidence_score", 0), mag_val)

    country_clusters.sort(key=sort_key, reverse=True)
    top3 = country_clusters[:3]

    # X/Twitter thread (280 chars each)
    thread = []
    thread.append("🌴 Caribbean Opportunity Brief — this week's signals for builders:\n")
    for i, c in enumerate(top3, 1):
        country = c.get("country_cluster", "")
        kind = KIND_TO_PLAIN.get(c.get("signal_kind", ""), "")
        mag = extract_magnitude(c.get("detail", "") or "")
        action = plain_action(c.get("signal_kind", ""), c.get("personas", []))
        tweet = f"{i}. {country}: {kind}"
        if mag:
            tweet += f" ({mag})"
        tweet += f" — {action[:160]}"
        thread.append(tweet)
    thread.append("\nFull brief: abeng.vercel.app #CaribbeanTech #FutureCaribbean")

    # Instagram caption
    ig_lines = [
        "🌴 This week in Caribbean opportunity:",
        "",
    ]
    for c in top3:
        country = c.get("country_cluster", "")
        kind = KIND_TO_PLAIN.get(c.get("signal_kind", ""), "")
        mag = extract_magnitude(c.get("detail", "") or "")
        line = f"• {country}: {kind}"
        if mag:
            line += f" — {mag}"
        ig_lines.append(line)
    ig_lines.extend([
        "",
        "Full breakdown in bio link 🔗",
        "#CaribbeanTech #FutureCaribbean #CaribbeanBusiness #InvestCaribbean #BuildInCaribbean",
    ])

    # WhatsApp forward (concise)
    wa_lines = [
        "🌴 *Caribbean Opportunity Brief*",
        "",
    ]
    for c in top3:
        country = c.get("country_cluster", "")
        kind = KIND_TO_PLAIN.get(c.get("signal_kind", ""), "")
        mag = extract_magnitude(c.get("detail", "") or "")
        action = plain_action(c.get("signal_kind", ""), c.get("personas", []))
        line = f"• *{country}*: {kind}"
        if mag:
            line += f" ({mag})"
        line += f" — {action[:120]}"
        wa_lines.append(line)
    wa_lines.extend([
        "",
        "Full: abeng.vercel.app",
        "Reply STOP to unsub",
    ])

    return {
        "x_thread": "\n\n".join(thread),
        "instagram_caption": "\n".join(ig_lines),
        "whatsapp_forward": "\n".join(wa_lines),
    }


def main() -> int:
    OUTBOX_DIR.mkdir(parents=True, exist_ok=True)

    # Main brief
    brief = build_community_brief()
    BRIEF_FILE.write_text(brief, encoding="utf-8")
    print(f"Wrote {BRIEF_FILE.relative_to(ROOT)} ({len(brief)} chars)")

    # Social snippets
    snippets = build_social_snippets()
    for name, content in snippets.items():
        snippet_file = OUTBOX_DIR / f"community_brief_{name}.md"
        snippet_file.write_text(content, encoding="utf-8")
        print(f"  → {snippet_file.name} ({len(content)} chars)")

    return 0


if __name__ == "__main__":
    raise SystemExit(main())