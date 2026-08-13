#!/usr/bin/env python3
"""Build the lightweight source-health snapshot bundled with the hosted API."""
from __future__ import annotations

import json
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
OUTPUT = ROOT / "api" / "source-health-data.json"
SOURCES = {
    "world_bank": ROOT / "data" / "world_bank" / "latest.json",
    "idb": ROOT / "data" / "idb" / "latest.json",
    "noaa": ROOT / "data" / "noaa" / "latest.json",
    "ndbc": ROOT / "data" / "ndbc" / "latest.json",
    "tier2": ROOT / "data" / "tier2" / "latest.json",
}


def build_snapshot() -> dict:
    snapshot = {}
    for key, path in SOURCES.items():
        try:
            payload = json.loads(path.read_text(encoding="utf-8"))
        except (FileNotFoundError, json.JSONDecodeError, OSError):
            snapshot[key] = {"ok": False, "fetched_at": None}
            continue
        snapshot[key] = {
            "ok": True,
            "fetched_at": payload.get("fetched_at"),
        }
    return snapshot


def main() -> None:
    OUTPUT.write_text(json.dumps(build_snapshot(), indent=2) + "\n", encoding="utf-8")
    print(f"source health: wrote {OUTPUT.relative_to(ROOT)}")


if __name__ == "__main__":
    main()
