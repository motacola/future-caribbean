#!/usr/bin/env python3
"""Generate the judge/product-facing Dispatch Desk artifact.

The Dispatch Desk is the primary Open Track presentation layer: it groups routed
persona dispatches into decision-first clusters so a judge or operator can see
what changed, who should care, what action follows, what evidence supports it,
and how feedback changes the next cycle.
"""

from __future__ import annotations

import json
import re
from collections import Counter, defaultdict
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parents[1]
DISPATCH_JSON = ROOT / "outbox" / "opportunity_dispatches.json"
THESIS_MD = ROOT / "outbox" / "regional_thesis.md"
WHY_NOW_MD = ROOT / "outbox" / "why_now.md"
BOOSTS_JSON = ROOT / "data" / "feedback" / "current_boosts.json"
OUT_MD = ROOT / "outbox" / "dispatch_desk.md"
OUT_JSON = ROOT / "outbox" / "dispatch_desk.json"


def load_json(path: Path, fallback: Any) -> Any:
    if not path.exists():
        return fallback
    try:
        return json.loads(path.read_text(encoding="utf-8"))
    except (json.JSONDecodeError, OSError):
        return fallback


def load_text(path: Path) -> str:
    if not path.exists():
        return ""
    try:
        return path.read_text(encoding="utf-8")
    except OSError:
        return ""


def clean(text: Any) -> str:
    return " ".join(str(text or "").split())


def clip(text: Any, limit: int = 170) -> str:
    value = clean(text)
    if len(value) <= limit:
        return value
    return value[: limit - 1].rsplit(" ", 1)[0].rstrip(".,;:") + "…"


def slugish(text: str) -> str:
    return re.sub(r"[^a-z0-9]+", "-", text.lower()).strip("-") or "regional"


def cluster_key(dispatch: dict[str, Any]) -> tuple[str, str]:
    """Group duplicate persona routes into one decision cluster.

    Use the originating signal when available. Regional rollups stay separate
    from country-specific signals, which prevents the desk from hiding useful
    all-region screens behind the top country.
    """
    signal_id = str(dispatch.get("signal_id") or "")
    kind = str(dispatch.get("signal_kind") or "signal")
    country = str(dispatch.get("country_cluster") or "Regional")
    if signal_id:
        return kind, signal_id
    return kind, slugish(country)


def parse_thesis(text: str) -> str:
    for line in text.splitlines():
        line = line.strip()
        if not line or line.startswith("#") or line.startswith("Generated:"):
            continue
        if line.startswith("**") or line.startswith("-"):
            continue
        return clean(line)
    return "Regional thesis unavailable for this cycle."


def parse_why_now(text: str, limit: int = 3) -> list[str]:
    bullets: list[str] = []
    for line in text.splitlines():
        line = line.strip()
        if line.startswith(("🟢", "🟡", "🔴")):
            bullets.append(clean(line))
        if len(bullets) >= limit:
            break
    return bullets


def feedback_sentence(feedback_statuses: Counter[str]) -> str:
    if not feedback_statuses:
        return "No feedback recorded yet; routing is awaiting channel response."
    parts = []
    labels = {
        "forwarded": "forwarded",
        "replied": "replied",
        "decision_changed": "changed a decision",
        "opened": "opened",
        "ignored": "ignored",
        "awaiting": "awaiting feedback",
    }
    for status, count in feedback_statuses.most_common():
        parts.append(f"{count} {labels.get(status, status.replace('_', ' '))}")
    return "Feedback this cycle: " + ", ".join(parts) + "."


def build_clusters(dispatches: list[dict[str, Any]]) -> list[dict[str, Any]]:
    grouped: dict[tuple[str, str], list[dict[str, Any]]] = defaultdict(list)
    for dispatch in dispatches:
        grouped[cluster_key(dispatch)].append(dispatch)

    clusters: list[dict[str, Any]] = []
    for (_, _), items in grouped.items():
        items = sorted(
            items,
            key=lambda d: (d.get("confidence_raw", d.get("confidence_score", 0)), d.get("persona_label", "")),
            reverse=True,
        )
        lead = items[0]
        personas = []
        for item in items:
            personas.append({
                "persona": item.get("persona_label", "Unknown persona"),
                "channel": item.get("channel", "Unknown channel"),
                "action": item.get("recommended_action", "No action recorded."),
                "rationale": item.get("routing_rationale", "Matches signal profile."),
                "ranking_rationale": item.get("ranking_rationale", ""),
                "dispatch_id": item.get("dispatch_id", ""),
                "feedback_status": item.get("feedback_status", "awaiting"),
            })

        feedback_counts = Counter(str(i.get("feedback_status", "awaiting")) for i in items)
        risk_flags = []
        for item in items:
            for flag in item.get("risk_flags", []) or []:
                if flag not in risk_flags:
                    risk_flags.append(flag)

        cluster = {
            "cluster_id": f"CL-{slugish(str(lead.get('signal_kind', 'signal')))}-{slugish(str(lead.get('country_cluster', 'regional')))}",
            "title": lead.get("title", "Untitled dispatch cluster"),
            "country_cluster": lead.get("country_cluster", "Regional"),
            "signal_kind": lead.get("signal_kind", "signal"),
            "decision": lead.get("decision_influence", "Decision not recorded."),
            "evidence": lead.get("evidence_summary", "Evidence summary unavailable."),
            "detail": lead.get("detail", ""),
            "confidence_score": int(lead.get("confidence_score", 0) or 0),
            "confidence_raw": int(lead.get("confidence_raw", lead.get("confidence_score", 0)) or 0),
            "magnitude_pct": float(lead.get("magnitude_pct") or 0.0),
            "confidence_display": lead.get("confidence_display", ""),
            "evidence_grade": lead.get("evidence_grade", ""),
            "freshness": lead.get("freshness", ""),
            "risk_flags": risk_flags,
            "personas": personas,
            "feedback_counts": dict(feedback_counts),
            "feedback_summary": feedback_sentence(feedback_counts),
            "ranking_rationale": lead.get("ranking_rationale", ""),
        }
        clusters.append(cluster)

    # Rank on the unclamped score first, then on the size of the movement.
    # Ranking on the clamped score alone put every strong FDI signal on 100,
    # so the lead was decided by persona count — a routing artefact — and
    # then by list order. Magnitude now breaks the tie before either.
    clusters.sort(
        key=lambda c: (
            c["confidence_raw"],
            c["magnitude_pct"],
            len(c["personas"]),
            1 if c["feedback_counts"].get("forwarded") or c["feedback_counts"].get("decision_changed") else 0,
        ),
        reverse=True,
    )
    return clusters


def boost_lines(boosts: dict[str, Any], limit: int = 5) -> list[str]:
    rows = []
    for kind, countries in (boosts.get("boosts", {}) or {}).items():
        if not isinstance(countries, dict):
            continue
        for country, value in countries.items():
            if value == 0:
                continue
            direction = "upranked" if value > 0 else "downranked"
            rows.append((abs(int(value)), f"{country} {kind.replace('_', ' ')} {direction} {int(value):+d}"))
    rows.sort(reverse=True)
    return [row for _, row in rows[:limit]]


def write_outputs(payload: dict[str, Any]) -> None:
    OUT_JSON.write_text(json.dumps(payload, indent=2, sort_keys=True) + "\n", encoding="utf-8")

    clusters = payload["clusters"]
    lines = [
        f"# Dispatch Desk — Cycle {payload['cycle_id']}",
        "",
        f"Generated: {payload['generated_at']}",
        "",
        "Signal Fabric turns fragmented regional data into decision-ready routes. This is the primary product surface; Telegram/email are delivery channels and the dashboard is the operator/audit view.",
        "",
        "## Open Track Coordination Chain",
        "",
        "Fragmented public data → Agentic signal pipeline → Routed decisions → Feedback → Faster regional action",
        "",
        "| Stage | This cycle proof |",
        "|---|---|",
        f"| Data | {payload['source_count']} source families represented |",
        f"| Signal | {payload['cluster_count']} decision clusters from {payload['dispatch_count']} persona routes |",
        f"| Packaging | Persona actions, evidence grades, risk flags, and action windows attached |",
        f"| Distribution | {payload['persona_count']} personas across {payload['channel_count']} channel types |",
        f"| Action | Every route names the decision it should influence |",
        f"| Capital | Investor/operator/procurement routes identify where to investigate, bid, pause, or partner |",
        "",
        "## Regional Read",
        "",
        payload["regional_thesis"],
        "",
        "## Why This Cycle Matters",
        "",
    ]
    if payload["why_now"]:
        lines.extend(f"- {item}" for item in payload["why_now"])
    else:
        lines.append("- No seasonal trigger recorded this cycle.")

    lines.extend([
        "",
        "## Decision Clusters",
        "",
    ])

    for idx, cluster in enumerate(clusters[:8], 1):
        lines.extend([
            f"### {idx}. {cluster['title']}",
            "",
            f"- **Decision:** {cluster['decision']}",
            f"- **Evidence:** {cluster['evidence']} ({cluster['evidence_grade']})",
            f"- **Confidence:** {cluster['confidence_score']}/100 · {cluster.get('freshness') or 'freshness unknown'}",
        ])
        if cluster.get("detail"):
            lines.append(f"- **Signal detail:** {cluster['detail']}")
        if cluster.get("risk_flags"):
            lines.append(f"- **Risk flags:** {'; '.join(cluster['risk_flags'])}")
        lines.extend([
            f"- **Why ranked here:** {cluster.get('ranking_rationale') or 'Ranking uses confidence, source coverage, evidence count, magnitude, and feedback.'}",
            f"- **Feedback effect:** {cluster['feedback_summary']}",
            "",
            "| Persona | Channel | Next action | Feedback |",
            "|---|---|---|---|",
        ])
        for route in cluster["personas"]:
            lines.append(
                f"| {route['persona']} | {route['channel']} | {clip(route['action'], 135)} | {route['feedback_status']} (`{route['dispatch_id']}`) |"
            )
        lines.append("")

    lines.extend([
        "## Feedback-Adjusted Priority",
        "",
    ])
    if payload["boost_lines"]:
        lines.extend(f"- {line}" for line in payload["boost_lines"])
    else:
        lines.append("- No active boosts this cycle.")

    lines.extend([
        "",
        "## Supporting Artifacts",
        "",
        "- `outbox/opportunity_dispatches.json` — canonical persona routes",
        "- `outbox/dispatch_packets/` — persona-ready delivery packets",
        "- `outbox/delivery_manifest.json` — channel handoff manifest",
        "- `outbox/feedback_review.md` — feedback and next-cycle learning",
        "- `dist/index.html` (served at `/`) — operator/audit console",
        "",
    ])

    OUT_MD.write_text("\n".join(lines).rstrip() + "\n", encoding="utf-8")


def build() -> dict[str, Any]:
    dispatch_payload = load_json(DISPATCH_JSON, {})
    dispatches = dispatch_payload.get("dispatches", []) if isinstance(dispatch_payload, dict) else []
    dispatches = [d for d in dispatches if isinstance(d, dict)]
    clusters = build_clusters(dispatches)
    generated_at = datetime.now(timezone.utc).strftime("%Y-%m-%d %H:%M UTC")
    cycle_id = "unknown"
    if dispatches:
        cycle_id = str(dispatches[0].get("cycle_id") or "unknown")

    personas = {d.get("persona_key") or d.get("persona_label") for d in dispatches}
    channels = {d.get("channel") for d in dispatches}
    sources = set()
    for d in dispatches:
        evidence = str(d.get("evidence_summary", ""))
        if evidence.startswith("WB"):
            sources.add("World Bank")
        if "CDB" in evidence:
            sources.add("CDB")
        if "IDB" in evidence:
            sources.add("IDB")
        if not sources and evidence:
            sources.add("Composite")

    payload = {
        "generated_at": generated_at,
        "cycle_id": cycle_id,
        "dispatch_count": len(dispatches),
        "cluster_count": len(clusters),
        "persona_count": len([p for p in personas if p]),
        "channel_count": len([c for c in channels if c]),
        "source_count": max(len(sources), 1 if dispatches else 0),
        "regional_thesis": parse_thesis(load_text(THESIS_MD)),
        "why_now": parse_why_now(load_text(WHY_NOW_MD)),
        "boost_lines": boost_lines(load_json(BOOSTS_JSON, {})),
        "clusters": clusters,
    }
    return payload


def main() -> int:
    if not DISPATCH_JSON.exists():
        raise FileNotFoundError(f"Missing {DISPATCH_JSON}; run packagers/opportunity_dispatch.py first")
    payload = build()
    write_outputs(payload)
    print(f"Wrote {OUT_MD.relative_to(ROOT)} and {OUT_JSON.relative_to(ROOT)}")
    print(f"Clusters: {payload['cluster_count']} from {payload['dispatch_count']} persona routes")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
