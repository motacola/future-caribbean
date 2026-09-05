#!/usr/bin/env python3
"""Extract new signals since last run and output them for delivery.

Connects the watcher (which always writes latest.md) to distribution
(which should only send what's genuinely new). Tracks sent signal
fingerprints in .sent_signals.json so repeated runs are idempotent.

Usage:
    # After poller runs, pipe output to a file:
    python3 distributors/delta_signals.py > /tmp/new_signals.md

    # Cron-mode: outputs nothing to stdout if nothing new
    python3 distributors/delta_signals.py
"""

from __future__ import annotations

import json
import re
import sys
from datetime import datetime, timezone
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
SIGNAL_FILE = ROOT / "signals" / "world_bank" / "latest.md"
STATE_FILE = ROOT / "data" / "world_bank" / ".sent_signals.json"


def extract_signals(text: str) -> list[str]:
    """Parse signal lines from the markdown brief's ## Signals section."""
    lines = text.splitlines()
    in_signals = False
    signals: list[str] = []
    for line in lines:
        if line.strip() == "## Signals":
            in_signals = True
            continue
        if in_signals:
            if line.startswith("## "):
                break
            if line.startswith("- ") and line[2:].strip():
                signals.append(line[2:].strip())
    return signals


def load_state() -> set[str]:
    if STATE_FILE.exists():
        return set(json.loads(STATE_FILE.read_text(encoding="utf-8")))
    return set()


def save_state(signals: set[str]) -> None:
    STATE_FILE.parent.mkdir(parents=True, exist_ok=True)
    STATE_FILE.write_text(
        json.dumps(sorted(signals), indent=2) + "\n", encoding="utf-8"
    )


def fingerprint(signal_text: str) -> str:
    """Collapse whitespace and lowercase for stable fingerprinting."""
    return re.sub(r"\s+", " ", signal_text).strip().lower()


def main() -> int:
    if not SIGNAL_FILE.exists():
        print("No signal file yet. Run the poller first.", file=sys.stderr)
        return 1

    text = SIGNAL_FILE.read_text(encoding="utf-8")
    current_signals = extract_signals(text)
    if not current_signals:
        print("No signals found in latest.md", file=sys.stderr)
        return 1

    sent = load_state()
    current_fingerprints = {fingerprint(s) for s in current_signals}
    new_fingerprints = current_fingerprints - sent

    if not new_fingerprints:
        return 0  # quiet exit — nothing new

    new_signals = [s for s in current_signals if fingerprint(s) in new_fingerprints]

    # Output in Telegram-friendly markdown
    fetched_at = datetime.now(timezone.utc).strftime("%b %d, %Y at %H:%M UTC")
    print(f"*Caribbean Signal Brief — {fetched_at}*")
    print()
    print("*New signals detected:*")
    print()
    for sig in new_signals:
        print(f"• {sig}")
    print()
    print("— Abeng • World Bank watcher")

    # Update sent state with ALL current signals, not just new ones
    save_state(current_fingerprints)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())