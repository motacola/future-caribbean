#!/usr/bin/env python3
"""Feedback Intake CLI — appends manual feedback events to data/feedback/available.json.

Accepts structured feedback from operators, CLI, or Telegram listeners and
merges it into the available feedback pool. The existing feedback_loop.py apply
phase reads this file and incorporates entries into the persistent state.

Usage:
  python3 packagers/feedback_intake.py --dispatch-id DSP-20260526-023 --status forwarded --note "Investor forwarded to partner"
  python3 packagers/feedback_intake.py --dispatch-id DSP-20260526-001 --status opened --note "Read by diaspora network lead"
  python3 packagers/feedback_intake.py --dispatch-id DSP-TEST --status ignored --note "No action taken"
"""

from __future__ import annotations

import logging
import json
import sys
import argparse
from datetime import datetime, timezone
from pathlib import Path

LOGGER = logging.getLogger(__name__)
ROOT = Path(__file__).resolve().parents[1]
AVAILABLE_FILE = ROOT / "data" / "feedback" / "available.json"

VALID_STATUSES = {"forwarded", "replied", "opened", "ignored", "decision_changed", "delivered"}


def load_available() -> list[dict]:
    """Load existing available feedback events."""
    if AVAILABLE_FILE.exists():
        try:
            data = json.loads(AVAILABLE_FILE.read_text(encoding="utf-8"))
            if isinstance(data, list):
                return data
        except (json.JSONDecodeError, OSError):
            LOGGER.warning("feedback intake file read error")
    return []


def save_available(items: list[dict]) -> None:
    """Persist available feedback events."""
    AVAILABLE_FILE.parent.mkdir(parents=True, exist_ok=True)
    AVAILABLE_FILE.write_text(
        json.dumps(items, indent=2, ensure_ascii=False) + "\n",
        encoding="utf-8",
    )


def add_feedback(
    dispatch_id: str,
    status: str,
    note: str = "",
    source: str = "",
) -> dict:
    """Create a feedback entry and append to available.json.

    Returns the created entry.
    """
    items = load_available()

    # Check for duplicates by dispatch_id
    existing_ids = {e.get("dispatch_id", "") for e in items}
    if dispatch_id in existing_ids:
        print(f"Warning: dispatch_id '{dispatch_id}' already exists in available.json", file=sys.stderr)

    entry = {
        "dispatch_id": dispatch_id,
        "feedback_status": status,
        "feedback_detail": note,
        "source": source or "manual_cli",
        "collected_at": datetime.now(timezone.utc).isoformat(),
    }
    items.append(entry)
    save_available(items)
    return entry


def list_feedback() -> None:
    """Display current available feedback entries."""
    items = load_available()
    if not items:
        print("No feedback entries in available.json.")
        return
    print(f"Available feedback entries: {len(items)}")
    print("")
    for i, item in enumerate(items, 1):
        print(f"  {i}. {item.get('dispatch_id', '?')} — {item.get('feedback_status', '?')}")
        if item.get("feedback_detail"):
            print(f"     Note: {item['feedback_detail']}")
        print(f"     {item.get('collected_at', '')[:19]}")


def main() -> int:
    parser = argparse.ArgumentParser(description="Intake feedback events for Caribbean Signal OS.")
    parser.add_argument("--dispatch-id", help="Dispatch ID (e.g. DSP-20260526-023)")
    parser.add_argument("--status", choices=sorted(VALID_STATUSES),
                        help="Feedback status: forwarded/replied/opened/ignored/decision_changed")
    parser.add_argument("--note", default="", help="Free-text note about the feedback")
    parser.add_argument("--source", default="", help="Source channel (telegram, email, manual)")
    parser.add_argument("--list", action="store_true", help="List current available feedback")

    args = parser.parse_args()

    if args.list:
        list_feedback()
        return 0

    if not args.dispatch_id or not args.status:
        parser.print_help()
        print("")
        print("Error: --dispatch-id and --status are required (or use --list)")
        return 1

    entry = add_feedback(
        dispatch_id=args.dispatch_id,
        status=args.status,
        note=args.note,
        source=args.source,
    )

    print(f"Feedback recorded for {entry['dispatch_id']}: {entry['feedback_status']}")
    if entry["feedback_detail"]:
        print(f"  Note: {entry['feedback_detail']}")
    print(f"  Source: {entry['source']}")
    print(f"  Total entries in available.json: {len(load_available())}")

    # Remind that feedback_loop.py apply will pick this up
    print("")
    print("Next cycle: run 'python3 packagers/feedback_loop.py apply' to incorporate this feedback.")

    return 0


if __name__ == "__main__":
    raise SystemExit(main())