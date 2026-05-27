#!/usr/bin/env python3
"""Extract new Tier 2 items since last delivery.
"""
from __future__ import annotations

import json
from datetime import datetime, timezone
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
DATA_FILE = ROOT / "data" / "tier2" / "latest.json"
STATE_FILE = ROOT / "data" / "tier2" / ".sent_deltas.json"


def load_state() -> set[str]:
    if STATE_FILE.exists():
        return set(json.loads(STATE_FILE.read_text(encoding="utf-8")))
    return set()


def save_state(ids: set[str]) -> None:
    STATE_FILE.parent.mkdir(parents=True, exist_ok=True)
    STATE_FILE.write_text(json.dumps(sorted(ids), indent=2) + "\n", encoding="utf-8")


def main() -> int:
    if not DATA_FILE.exists():
        return 0

    data = json.loads(DATA_FILE.read_text(encoding="utf-8"))
    items = data.get("items", [])
    if not items:
        return 0

    state = load_state()
    new_items = [i for i in items if i.get("id") and f"{i['source_slug']}:{i['id']}" not in state]

    if not new_items:
        return 0

    now = datetime.now(timezone.utc).strftime("%b %d, %Y at %H:%M UTC")
    print(f"*Tier 2 Caribbean Data — {now}*")
    print()
    print("New data from CARICOM Statistics and CDB:")
    print()

    type_labels = {"country_data": "📊", "publications": "📄",
                   "procurement": "📋", "evaluation": "📊", "news": "📰"}

    for item in sorted(new_items, key=lambda x: x.get("modified", ""), reverse=True)[:20]:
        icon = type_labels.get(item.get("item_type", ""), "•")
        title = item.get("title", "?")[:80]
        source = item.get("source", "?")
        files = item.get("data_files", [])
        file_info = f" 📁 {len(files)} file(s)" if files else ""
        print(f"{icon} **{title}**{file_info}")
        print(f"   {source} · {item.get('modified', '?')[:10]}")
        print()

    # Update state
    all_ids = {f"{i['source_slug']}:{i['id']}" for i in items if i.get("id")}
    save_state(all_ids)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
