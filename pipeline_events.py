"""Typed pipeline events, history persistence, and replay helpers."""
from __future__ import annotations

import json
import time
from datetime import datetime, timezone
from pathlib import Path

from map_data import build_map_data

SOURCE_STEPS = {
    "World Bank": "World Bank",
    "IDB CKAN": "IDB",
    "Tier 2 (CARICOM + CDB)": "CARICOM / CDB",
    "NOAA NWS": "NOAA",
    "NDBC Buoys": "NDBC",
    "NHC Storms": "NHC",
}


def event(event_type: str, **data) -> dict:
    return {"event": event_type, "data": {**data, "ts": data.get("ts", time.time())}}


def source_event_from_line(line: str) -> dict | None:
    if line.startswith("--- ") and line.endswith(" ---"):
        label = line[4:-4]
        if label in SOURCE_STEPS:
            return event("source_check", source=SOURCE_STEPS[label], status="polling")
    if line.lstrip().startswith("✓ "):
        label = line.strip()[2:]
        if label in SOURCE_STEPS:
            return event("source_check", source=SOURCE_STEPS[label], status="complete")
    return None


def _read_json(path: Path) -> dict:
    try:
        return json.loads(path.read_text())
    except (FileNotFoundError, json.JSONDecodeError, OSError):
        return {}


def cycle_number(root: Path) -> int:
    state = _read_json(root / "data" / ".cycle_count.json")
    return int(state.get("count", 0) or 0) + 1


def outbox_events(root: Path, cycle: int | None = None) -> list[dict]:
    """Build typed signal, dispatch, and completion events from current outputs."""
    events: list[dict] = []
    for item in build_map_data(root):
        if item["confidence"] <= 0:
            continue
        events.append(event(
            "signal_found",
            country=item["country"],
            kind=item["kind"],
            confidence=item["confidence"],
            summary=item["top_signal_summary"],
        ))

    dispatch_data = _read_json(root / "outbox" / "opportunity_dispatches.json")
    for dispatch in dispatch_data.get("dispatches", []) or []:
        events.append(event(
            "dispatch_routed",
            dispatch_id=dispatch.get("dispatch_id", ""),
            country=dispatch.get("country_cluster", "Caribbean"),
            recipient=dispatch.get("persona_label", "Decision-maker"),
        ))

    signal_count = sum(1 for item in build_map_data(root) if item["confidence"] > 0)
    events.append(event("cycle_complete", cycle=cycle or cycle_number(root), signals=signal_count))
    return events


def synthetic_events(root: Path) -> list[dict]:
    """Build a complete offline demo sequence from current local files."""
    events = [
        event("source_check", source=source, status="complete")
        for source in SOURCE_STEPS.values()
    ]
    events.extend(outbox_events(root))
    return events


def append_history(root: Path, events: list[dict], day: str | None = None) -> Path:
    history_dir = root / "data" / "history"
    history_dir.mkdir(parents=True, exist_ok=True)
    day = day or datetime.now(timezone.utc).date().isoformat()
    path = history_dir / f"{day}.jsonl"
    with path.open("a", encoding="utf-8") as handle:
        for item in events:
            handle.write(json.dumps(item, ensure_ascii=False) + "\n")
    return path


def latest_history(root: Path) -> list[dict]:
    history_dir = root / "data" / "history"
    files = sorted(history_dir.glob("????-??-??.jsonl"), reverse=True) if history_dir.exists() else []
    if not files:
        return []
    events = []
    for line in files[0].read_text(encoding="utf-8", errors="replace").splitlines():
        try:
            item = json.loads(line)
            if item.get("event") and isinstance(item.get("data"), dict):
                events.append(item)
        except json.JSONDecodeError:
            continue
    return events


def record_cycle_events(root: Path) -> Path:
    """Persist a synthetic cycle snapshot; useful for offline cycles and tests."""
    return append_history(root, synthetic_events(root))
