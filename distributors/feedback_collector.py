#!/usr/bin/env python3
"""Feedback collector — tracks signal delivery history and basic engagement.

After distribution, this script:
  1. Reads the latest feedback_queue.json
  2. Checks which signals were actually delivered (via outbox delta state)
  3. Updates the feedback queue with delivery status
  4. Builds a simple engagement log

Outputs nothing to stdout (runs silently as part of the pipeline).
"""

from __future__ import annotations

import logging
import json
from datetime import datetime, timezone
from pathlib import Path

LOGGER = logging.getLogger(__name__)
ROOT = Path(__file__).resolve().parents[1]
OUTBOX_DIR = ROOT / "outbox"
FEEDBACK_LOG = ROOT / "data" / "feedback" / "delivery_log.jsonl"
DELIVERY_STATE = ROOT / "data" / "outbox" / ".sent_digests.json"


def load_state(path: Path) -> dict:
    if path.exists():
        try:
            return json.loads(path.read_text(encoding="utf-8"))
        except (json.JSONDecodeError, OSError):
            LOGGER.warning("feedback state file read error")
    return {}


def write_log_entry(entry: dict) -> None:
    FEEDBACK_LOG.parent.mkdir(parents=True, exist_ok=True)
    with open(FEEDBACK_LOG, "a", encoding="utf-8") as f:
        f.write(json.dumps(entry) + "\n")


def run() -> int:
    # Check if any deliveries happened
    sent_state = load_state(DELIVERY_STATE)
    if not sent_state:
        return 0  # No deliveries tracked yet — first run

    now = datetime.now(timezone.utc).isoformat()

    # Read the latest feedback queue
    queue_path = OUTBOX_DIR / "feedback_queue.json"
    if not queue_path.exists():
        return 0

    try:
        queue = json.loads(queue_path.read_text(encoding="utf-8"))
    except (json.JSONDecodeError, OSError):
        return 0

    # Log which signals had delivery
    sent_count = 0
    for item in queue.get("items", []):
        signal_id = item.get("signal_id")
        if not signal_id:
            continue

        # Only mark sent if this specific signal_id appears in the delivery state
        if signal_id in sent_state:
            metrics = item.setdefault("metrics", {})
            metrics["sent"] = True
            sent_count += 1

    # Write the delivery log
    if sent_count > 0:
        entry = {
            "timestamp": now,
            "signals_sent": sent_count,
            "outbox_delivered": list(sent_state.keys()),
        }
        write_log_entry(entry)

    return 0


if __name__ == "__main__":
    raise SystemExit(run())
