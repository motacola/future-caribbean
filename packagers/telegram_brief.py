#!/usr/bin/env python3
"""Generate the cron-delivered Telegram notification for Dispatch Desk.

Telegram is a delivery channel, not the product. This adapter summarizes the
current Dispatch Desk clusters so the recipient knows which decision routes are
ready and where to open the deeper product artifact.
"""

from __future__ import annotations

import json
import sys
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parents[1]
DESK_JSON = ROOT / "outbox" / "dispatch_desk.json"
DESK_MD = ROOT / "outbox" / "dispatch_desk.md"
OUTBOX_DIR = ROOT / "outbox"
BRIEF_FILE = OUTBOX_DIR / "telegram_brief.md"
MAX_BRIEF_CHARS = 3800


def load_json(path: Path, fallback: Any) -> Any:
    if not path.exists():
        return fallback
    try:
        return json.loads(path.read_text(encoding="utf-8"))
    except (json.JSONDecodeError, OSError):
        return fallback


def shorten(text: Any, limit: int = 145) -> str:
    cleaned = " ".join(str(text or "").split())
    if len(cleaned) <= limit:
        return cleaned
    return cleaned[: limit - 1].rsplit(" ", 1)[0].rstrip(".,;:") + "…"


def ensure_desk() -> dict[str, Any]:
    desk = load_json(DESK_JSON, {})
    if desk:
        return desk
    # Build the desk on demand if opportunity dispatches already exist.
    sys.path.insert(0, str(ROOT))
    from packagers.dispatch_desk import build, write_outputs  # noqa: PLC0415

    desk = build()
    write_outputs(desk)
    return desk


def format_cluster(idx: int, cluster: dict[str, Any]) -> list[str]:
    personas = cluster.get("personas", []) or []
    persona_labels = []
    for route in personas[:3]:
        label = str(route.get("persona", "persona"))
        action = shorten(route.get("action", "Review dispatch."), 78)
        persona_labels.append(f"   → {label}: {action}")

    feedback = shorten(cluster.get("feedback_summary", "No feedback yet."), 115)
    lines = [
        f"{idx}) *{shorten(cluster.get('title'), 82)}*",
        f"   Decision: {shorten(cluster.get('decision'), 110)}",
        f"   Evidence: {shorten(cluster.get('evidence'), 95)} · {cluster.get('evidence_grade', 'grade n/a')}",
        f"   Confidence: {cluster.get('confidence_score', 0)}/100 · {cluster.get('freshness', 'freshness n/a')}",
    ]
    lines.extend(persona_labels)
    if len(personas) > 3:
        lines.append(f"   → +{len(personas) - 3} more persona route(s)")
    lines.append(f"   Loop: {feedback}")
    return lines


def build_brief() -> str:
    desk = ensure_desk()
    generated_at = desk.get("generated_at") or datetime.now(timezone.utc).strftime("%Y-%m-%d %H:%M UTC")
    cycle_id = desk.get("cycle_id") or datetime.now(timezone.utc).strftime("%Y%m%d")
    clusters = desk.get("clusters", []) or []
    top_clusters = clusters[:3]

    lines = [
        "🌴 *Signal Fabric — Decision Routes Ready*",
        f"Cycle: `{cycle_id}` · {generated_at}",
        "",
        "*What this is:*",
        "A Dispatch Desk notification. The product is the decision route: signal → persona → action → feedback. Telegram is only the delivery channel.",
        "",
        "*Open Track coordination chain this cycle*",
        f"Data → {desk.get('cluster_count', 0)} signal clusters → {desk.get('dispatch_count', 0)} persona routes → {desk.get('persona_count', 0)} personas → action/capital decisions",
        "",
        "*Priority decision clusters*",
    ]

    if top_clusters:
        for idx, cluster in enumerate(top_clusters, 1):
            lines.extend(format_cluster(idx, cluster))
            lines.append("")
    else:
        lines.append("No decision-ready clusters generated this cycle.")
        lines.append("")

    boost_lines = desk.get("boost_lines", []) or []
    lines.extend([
        "*Feedback-adjusted priority*",
    ])
    if boost_lines:
        lines.extend(f"• {shorten(line, 95)}" for line in boost_lines[:4])
    else:
        lines.append("• No active feedback boosts this cycle.")

    lines.extend([
        "",
        "*Open the product surface*",
        "• `outbox/dispatch_desk.md` — judge/user-facing decision desk",
        "• `dashboard.html` — product view + operator audit console",
        "• `outbox/dispatch_packets/` — persona-ready packets",
        "• `outbox/delivery_manifest.json` — channel handoff manifest",
        "",
        "No changed desk = no message.",
        "- Signal Fabric",
    ])

    text = "\n".join(lines).rstrip() + "\n"
    if len(text) > MAX_BRIEF_CHARS:
        text = text[: MAX_BRIEF_CHARS - 60].rsplit("\n", 1)[0] + "\n\n…trimmed for Telegram\n"
    return text


def main() -> int:
    OUTBOX_DIR.mkdir(parents=True, exist_ok=True)
    text = build_brief()
    BRIEF_FILE.write_text(text, encoding="utf-8")
    print(f"Wrote {BRIEF_FILE.relative_to(ROOT)} ({len(text)} chars)")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
