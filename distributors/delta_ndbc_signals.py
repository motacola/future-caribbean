#!/usr/bin/env python3
"""Extract new NDBC buoy signals since last delivery.
"""

from __future__ import annotations

import json
from datetime import datetime, timezone
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
SIGNAL_FILE = ROOT / "signals" / "ndbc" / "latest.md"
STATE_FILE = ROOT / "data" / "ndbc" / ".sent_deltas.json"


def extract_signal_lines(text: str) -> list[str]:
    """Parse the ## Marine Signals section."""
    lines = text.splitlines()
    in_section = False
    signals: list[str] = []
    for line in lines:
        if line.strip() == "## Marine Signals":
            in_section = True
            continue
        if in_section:
            if line.startswith("## ") or line.startswith("**"):
                break
            if line.startswith("- ") and line[2:].strip():
                signals.append(line[2:].strip())
    return signals


def extract_current_conditions(text: str) -> list[str]:
    """Parse ## Current Conditions to get station snapshots."""
    lines = text.splitlines()
    in_section = False
    conditions: list[str] = []
    buffer: list[str] = []
    for line in lines:
        if line.strip() == "## Current Conditions":
            in_section = True
            continue
        if in_section:
            if line.startswith("**") and "**" in line[2:]:
                if buffer:
                    conditions.append("\n".join(buffer))
                buffer = [line.strip(" *")]
            elif line.strip().startswith("  ") and buffer:
                buffer.append(line.strip())
    if buffer:
        conditions.append("\n".join(buffer))
    return conditions


def load_state() -> set[str]:
    if STATE_FILE.exists():
        return set(json.loads(STATE_FILE.read_text(encoding="utf-8")))
    return set()


def save_state(fingerprints: set[str]) -> None:
    STATE_FILE.parent.mkdir(parents=True, exist_ok=True)
    STATE_FILE.write_text(json.dumps(sorted(fingerprints), indent=2) + "\n", encoding="utf-8")


def main() -> int:
    if not SIGNAL_FILE.exists():
        return 0

    text = SIGNAL_FILE.read_text(encoding="utf-8")

    signals = extract_signal_lines(text)
    if not signals:
        return 0

    state = load_state()
    new_signals: list[str] = []
    new_fingerprints: set[str] = set()

    for sig in signals:
        fp = sig.strip().lower()[:60]
        if fp not in state:
            new_fingerprints.add(fp)
            new_signals.append(sig)

    if not new_signals:
        return 0

    now = datetime.now(timezone.utc).strftime("%b %d, %Y at %H:%M UTC")
    print(f"*Caribbean Marine Conditions — {now}*")
    print()
    print("Marine signals detected:")
    print()
    for sig in new_signals:
        print(f"  • {sig}")
    print()
    print("— Caribbean Signal OS • NDBC buoy watcher")
    print("*Full buoy data in signals/ndbc/latest.md*")

    save_state(state | new_fingerprints)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
