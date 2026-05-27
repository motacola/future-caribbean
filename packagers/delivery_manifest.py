#!/usr/bin/env python3
"""Delivery Manifest Generator — converts opportunity dispatches into a channel-ready manifest.

Reads outbox/opportunity_dispatches.json and writes outbox/delivery_manifest.json
with one delivery object per dispatch.

Each delivery entry includes:
  - dispatch_id
  - title
  - persona_key
  - persona_label
  - channel
  - delivery_status
  - action_window
  - feedback_prompt
  - target_artifact_path

Usage:
  python3 packagers/delivery_manifest.py
"""

from __future__ import annotations

import json
from datetime import datetime, timezone
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
DISPATCHES_FILE = ROOT / "outbox" / "opportunity_dispatches.json"
MANIFEST_FILE = ROOT / "outbox" / "delivery_manifest.json"


def generate_manifest(dispatches: list[dict]) -> list[dict]:
    """Convert dispatches into a channel-delivery manifest."""
    deliveries: list[dict] = []
    for d in dispatches:
        persona_key = d.get("persona_key", "unknown")
        safe_name = persona_key.replace("/", "-").replace(" ", "_")
        delivery = {
            "dispatch_id": d.get("dispatch_id", ""),
            "title": d.get("title", ""),
            "persona_key": persona_key,
            "persona_label": d.get("persona_label", persona_key),
            "channel": d.get("channel", "Telegram"),
            "delivery_status": d.get("delivery_status", "queued"),
            "action_window": d.get("action_window", "14 days"),
            "feedback_prompt": d.get(
                "feedback_prompt",
                "Did this dispatch trigger a follow-up, get forwarded, or change a decision?",
            ),
            "target_artifact_path": f"outbox/dispatch_packets/{safe_name}.md",
            "cycle_id": d.get("cycle_id", ""),
            "country_cluster": d.get("country_cluster", ""),
            "confidence_score": d.get("confidence_score", 0),
            "signal_kind": d.get("signal_kind", ""),
        }
        deliveries.append(delivery)

    return deliveries


def main() -> None:
    if not DISPATCHES_FILE.exists():
        print("No dispatches file found. Run opportunity_dispatch.py first.")
        return

    data = json.loads(DISPATCHES_FILE.read_text(encoding="utf-8"))
    dispatches = data.get("dispatches", [])
    if not dispatches:
        print("No dispatches found.")
        return

    deliveries = generate_manifest(dispatches)

    # Group by persona for the manifest structure
    from collections import Counter
    persona_counts = Counter(d["persona_key"] for d in deliveries)
    channel_counts = Counter(d["channel"] for d in deliveries)
    status_counts = Counter(d["delivery_status"] for d in deliveries)

    manifest = {
        "generated_at": datetime.now(timezone.utc).isoformat(),
        "cycle_id": dispatches[0].get("cycle_id", ""),
        "total_deliveries": len(deliveries),
        "summary": {
            "personas": len(persona_counts),
            "channels": len(channel_counts),
            "by_persona": dict(persona_counts.most_common()),
            "by_channel": dict(channel_counts.most_common()),
            "by_status": dict(status_counts.most_common()),
        },
        "deliveries": deliveries,
    }

    MANIFEST_FILE.parent.mkdir(parents=True, exist_ok=True)
    MANIFEST_FILE.write_text(
        json.dumps(manifest, indent=2, ensure_ascii=False) + "\n",
        encoding="utf-8",
    )
    print(f"Delivery manifest written: {MANIFEST_FILE}")
    print(f"  {len(deliveries)} deliveries, {len(persona_counts)} personas, {len(channel_counts)} channels")


if __name__ == "__main__":
    main()