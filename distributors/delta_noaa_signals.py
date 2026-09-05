#!/usr/bin/env python3
"""Extract new NOAA weather alerts since last delivery.

Same pattern as other delta scripts but reads from signals/noaa/latest.md
and tracks by alert fingerprint (event + area + sent time).
"""

from __future__ import annotations

import json
import re
from datetime import datetime, timezone
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
SIGNAL_FILE = ROOT / "signals" / "noaa" / "latest.md"
STATE_FILE = ROOT / "data" / "noaa" / ".sent_deltas.json"


def extract_alert_blocks(text: str) -> list[str]:
    """Parse the ## New Weather Alerts section for individual alert blocks."""
    lines = text.splitlines()
    in_section = False
    blocks: list[str] = []
    buffer: list[str] = []
    for line in lines:
        if line.strip() == "## New Weather Alerts":
            in_section = True
            continue
        if in_section:
            if line.startswith("## "):
                break
            if line.startswith("🟢") or line.startswith("🟡") or line.startswith("🟠") or line.startswith("🔴"):
                if buffer:
                    blocks.append("\n".join(buffer))
                buffer = [line]
            elif line.strip() and buffer:
                buffer.append(line.strip())
    if buffer:
        blocks.append("\n".join(buffer))
    return blocks


def load_state() -> set[str]:
    if STATE_FILE.exists():
        return set(json.loads(STATE_FILE.read_text(encoding="utf-8")))
    return set()


def save_state(fingerprints: set[str]) -> None:
    STATE_FILE.parent.mkdir(parents=True, exist_ok=True)
    STATE_FILE.write_text(json.dumps(sorted(fingerprints), indent=2) + "\n", encoding="utf-8")


def fingerprint(block: str) -> str:
    """Stable fingerprint from the alert block."""
    lines = block.strip().split("\n")
    if not lines:
        return ""
    # Extract event name after the icon: "🟡 Moderate 🏝️ **Rip Current Statement**"
    m = re.search(r"\*\*([^*]+)\*\*", lines[0])
    event = m.group(1).strip().lower() if m else ""
    # Extract area from second line
    area = ""
    if len(lines) > 1:
        area_m = re.search(r"Areas:\s*(.+)", lines[1])
        if area_m:
            area = area_m.group(1).strip().lower()[:40]
    return f"{event}|{area}"


def main() -> int:
    if not SIGNAL_FILE.exists():
        return 0

    text = SIGNAL_FILE.read_text(encoding="utf-8")

    # If the signal says no new alerts, we're done
    if "New alerts since last check: 0" in text:
        return 0

    blocks = extract_alert_blocks(text)
    if not blocks:
        return 0

    state = load_state()
    new_blocks: list[str] = []
    new_fingerprints: set[str] = set()

    for block in blocks:
        fp = fingerprint(block)
        if fp not in state:
            new_fingerprints.add(fp)
            new_blocks.append(block)

    if not new_blocks:
        return 0

    now = datetime.now(timezone.utc).strftime("%b %d, %Y at %H:%M UTC")
    print(f"*Caribbean Weather Alert — {now}*")
    print()
    print("New active weather alerts for the Caribbean region:")
    print()
    for block in new_blocks:
        print(block)
        print()
    print("— Abeng • NOAA watcher")
    print("*Check latest.md for full alert summary*")

    # Update state
    all_blocks = extract_alert_blocks(
        open(SIGNAL_FILE).read()
    )
    all_fingerprints = {fingerprint(b) for b in all_blocks}
    save_state(state | all_fingerprints)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
