#!/usr/bin/env python3
"""Extract new composite signals since last delivery for Telegram.
"""

from __future__ import annotations

import json
from datetime import datetime, timezone
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
SIGNAL_FILE = ROOT / "data" / "composite" / "latest.json"
STATE_FILE = ROOT / "data" / "composite" / ".sent_deltas.json"


def load_state() -> set[str]:
    if STATE_FILE.exists():
        return set(json.loads(STATE_FILE.read_text(encoding="utf-8")))
    return set()


def save_state(ids: set[str]) -> None:
    STATE_FILE.parent.mkdir(parents=True, exist_ok=True)
    STATE_FILE.write_text(json.dumps(sorted(ids), indent=2) + "\n", encoding="utf-8")


def main() -> int:
    if not SIGNAL_FILE.exists():
        return 0

    data = json.loads(SIGNAL_FILE.read_text(encoding="utf-8"))
    signals = data.get("signals", [])

    if not signals:
        return 0

    state = load_state()
    priority_order = {"high": 0, "medium": 1, "low": 2}

    new_signals = [s for s in signals if s.get("id") not in state]

    if not new_signals:
        return 0

    now = datetime.now(timezone.utc).strftime("%b %d, %Y at %H:%M UTC")
    print(f"*Caribbean Composite Intelligence — {now}*")
    print()
    print("Cross-source signals combining World Bank, IDB, NOAA, and NDBC data:")
    print()

    for sig in sorted(new_signals, key=lambda s: priority_order.get(s.get("priority", "low"), 99)):
        icon_map = {
            "cyclone_risk": "🌀", "maritime_hazard": "🚢",
            "investment_signal": "💼", "economic_vulnerability": "⚠️",
            "tourism_impact": "🏖️",
        }
        icon = icon_map.get(sig.get("kind", ""), "•")
        badge = {"high": "🔴", "medium": "🟡", "low": "🟢"}.get(sig.get("priority", "low"), "⚪")
        print(f"{badge} {icon} **{sig.get('label', 'Signal')}**")
        print(f"   {sig.get('summary', '')}")
        for ev in sig.get("evidence", [])[:1]:
            print(f"   • {ev}")
        print()

    print("— Caribbean Signal OS • Cross-source merger")

    # Update state
    all_ids = {s.get("id") for s in signals if s.get("id")}
    save_state(state | all_ids)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
