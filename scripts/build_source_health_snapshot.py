#!/usr/bin/env python3
"""Build the lightweight source-health + feedback snapshots bundled with the hosted API.

These two files exist so api/status.py can show real source freshness and
feedback totals on Vercel — data/* is .vercelignore'd, so data/source-health
or data/feedback/state.json aren't available at request time.
"""
from __future__ import annotations

import json
from collections import Counter
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
SOURCE_HEALTH_OUTPUT = ROOT / "api" / "source-health-data.json"
FEEDBACK_OUTPUT = ROOT / "api" / "feedback-data.json"

SOURCES = {
    "world_bank": ROOT / "data" / "world_bank" / "latest.json",
    "idb": ROOT / "data" / "idb" / "latest.json",
    "noaa": ROOT / "data" / "noaa" / "latest.json",
    "ndbc": ROOT / "data" / "ndbc" / "latest.json",
    "tier2": ROOT / "data" / "tier2" / "latest.json",
}

FEEDBACK_STATE = ROOT / "data" / "feedback" / "state.json"


def build_source_snapshot() -> dict:
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


def build_feedback_snapshot() -> dict:
    try:
        state = json.loads(FEEDBACK_STATE.read_text(encoding="utf-8"))
    except (FileNotFoundError, json.JSONDecodeError, OSError):
        return {"history": [], "boosts": {}, "actions": {}, "total_responses": 0}
    hist = state.get("history", []) or []
    boosts = state.get("boosts", {}) or {}
    actions = Counter(e.get("feedback_status", "unknown") for e in hist)
    return {
        "history": hist,
        "boosts": boosts,
        "actions": dict(actions),
        "total_responses": len(hist),
        "fetched_at": state.get("fetched_at"),
    }


def main() -> None:
    SOURCE_HEALTH_OUTPUT.write_text(
        json.dumps(build_source_snapshot(), indent=2) + "\n", encoding="utf-8"
    )
    print(f"source health: wrote {SOURCE_HEALTH_OUTPUT.relative_to(ROOT)}")
    FEEDBACK_OUTPUT.write_text(
        json.dumps(build_feedback_snapshot(), indent=2, ensure_ascii=False) + "\n",
        encoding="utf-8",
    )
    print(f"feedback data: wrote {FEEDBACK_OUTPUT.relative_to(ROOT)}")


if __name__ == "__main__":
    main()
