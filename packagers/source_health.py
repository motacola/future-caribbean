#!/usr/bin/env python3
"""Publish source freshness to api/source-health-data.json.

Why this exists
---------------
`.gitignore` excludes `data/*/latest.json` and `.vercelignore` excludes
`data/*`, so the per-source snapshots the watchers write never reach the
deployed functions. `api/status.py` therefore falls back to the committed
bundle `api/source-health-data.json` for every source, on every request,
in production.

Nothing regenerated that bundle. It was last written by hand on
2026-08-13 and stayed frozen through 24 consecutive green pipeline runs,
so `/api/status` kept reporting `6/6 sources ok` while the ages it served
counted up past six days. A dead collector and a healthy one looked
identical from outside.

This packager closes the loop: every cycle it reads the snapshots the
watchers just wrote and republishes the bundle, so the committed artefact
tracks the data the site actually collected.

Freshness is cadence-relative (see CLAUDE_HANDOVER_2026-08-15 §3): each
source declares how often a new snapshot is expected, and `api/status.py`
compares against that at request time rather than against a universal
number of days.
"""
from __future__ import annotations

import json
from datetime import datetime, timezone
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
BUNDLE = ROOT / "api" / "source-health-data.json"

# key -> minutes between expected snapshots. A source is reported stale
# once its snapshot is older than twice this (one missed refresh of grace).
# The pipeline cadence is 4h, so nothing here is below 240.
REFRESH_MINUTES = {
    "world_bank": 1440,   # annual indicators, polled daily
    "idb": 1440,          # CKAN project datasets, polled daily
    "noaa": 240,          # active hazard alerts, every cycle
    "ndbc": 240,          # marine conditions, every cycle
    "tier2": 1440,        # CARICOM statistics + CDB procurement notices
}


def _read_json(path: Path) -> dict | None:
    try:
        return json.loads(path.read_text(encoding="utf-8"))
    except (FileNotFoundError, json.JSONDecodeError, OSError):
        return None


def build_health(root: Path = ROOT, previous: dict | None = None) -> dict:
    """Build the bundle from the snapshots on disk.

    A source with no snapshot does not erase what was last known: the
    previous entry is carried forward and flagged, so its age keeps
    growing and the staleness check fires instead of the source silently
    disappearing from the response.
    """
    if previous is None:
        previous = _read_json(BUNDLE) or {}

    health: dict = {}
    for key, refresh in REFRESH_MINUTES.items():
        snapshot = _read_json(root / "data" / key / "latest.json")
        # A snapshot that declares its own run failed (every request errored,
        # nothing collected) is treated as no snapshot at all: its timestamp
        # must not reset the freshness clock, or a dead collector reads as
        # healthy for as long as it keeps failing on schedule.
        if snapshot is not None and snapshot.get("ok") is False:
            snapshot = None
        fetched_at = (snapshot or {}).get("fetched_at")
        entry = {
            "ok": bool(fetched_at),
            "fetched_at": fetched_at,
            "refresh_minutes": refresh,
        }
        if not fetched_at:
            prior = previous.get(key) or {}
            if prior.get("fetched_at"):
                # Snapshot is gone but we know when it last succeeded.
                # Report that, not silence.
                entry["fetched_at"] = prior["fetched_at"]
                entry["ok"] = True
                entry["carried_forward"] = True
            else:
                entry["carried_forward"] = False
        health[key] = entry
    return health


def source_freshness(root: Path = ROOT, keys: dict[str, str] | None = None) -> dict:
    """Per-source freshness for a status surface, judged one way everywhere.

    `keys` maps display name -> source key; it defaults to every source this
    module tracks. Each entry reports whether the source has a usable snapshot,
    when it was last collected, how old that is, the age at which it counts as
    stale, and whether the timestamp was carried forward from a previous run.

    This exists because four surfaces — server.py, api/status.py,
    cli/abengctl.py and mcp_adapter/desk_server.py — each carried their own
    copy of the check, and the copies drifted: three of them decided a source
    was live from `path.exists()` alone, so a collector whose every request
    failed still read as healthy, and a snapshot that had not been refreshed
    in days read as current.
    """
    if keys is None:
        keys = {k.replace("_", " ").title(): k for k in REFRESH_MINUTES}

    bundle = _read_json(root / "api" / "source-health-data.json") or {}
    now = datetime.now(timezone.utc)

    out: dict = {}
    for name, key in keys.items():
        snapshot = _read_json(root / "data" / key / "latest.json") or {}
        # A run that collected nothing must not stand in for a refresh.
        fetched_at = "" if snapshot.get("ok") is False else (snapshot.get("fetched_at") or "")
        entry = bundle.get(key) or {}
        carried_forward = False
        if not fetched_at:
            fetched_at = entry.get("fetched_at") or ""
            carried_forward = bool(fetched_at)

        age_minutes = None
        if fetched_at:
            try:
                dt = datetime.fromisoformat(fetched_at.replace("Z", "+00:00"))
                age_minutes = int((now - dt).total_seconds() / 60)
            except ValueError:
                age_minutes = None

        try:
            refresh = int(entry.get("refresh_minutes") or REFRESH_MINUTES.get(key, 1440))
        except (TypeError, ValueError):
            refresh = REFRESH_MINUTES.get(key, 1440)
        max_age_minutes = max(refresh, 1) * 2

        stale = age_minutes is not None and age_minutes > max_age_minutes
        out[key] = {
            "name": name,
            # `has_data` is "we hold a snapshot for this source at all";
            # `ok` is the stricter, user-facing reading — we hold one and it
            # is current. A six-day-old snapshot has data and is not ok.
            "has_data": bool(fetched_at),
            "ok": bool(fetched_at) and not stale,
            "fetched_at": fetched_at,
            "age_minutes": age_minutes,
            "max_age_minutes": max_age_minutes,
            "stale": stale,
            "carried_forward": carried_forward or bool(entry.get("carried_forward")),
        }
    return out


def main() -> int:
    health = build_health()
    health["generated_at"] = datetime.now(timezone.utc).isoformat()
    BUNDLE.parent.mkdir(parents=True, exist_ok=True)
    BUNDLE.write_text(json.dumps(health, indent=2) + "\n", encoding="utf-8")

    live = [k for k, v in health.items() if isinstance(v, dict) and v.get("ok") and not v.get("carried_forward")]
    carried = [k for k, v in health.items() if isinstance(v, dict) and v.get("carried_forward")]
    missing = [k for k, v in health.items() if isinstance(v, dict) and not v.get("ok")]
    print(f"Source health -> {BUNDLE.relative_to(ROOT)}")
    print(f"  fresh snapshot:  {', '.join(live) or 'none'}")
    if carried:
        print(f"  carried forward: {', '.join(carried)} (no snapshot this run)")
    if missing:
        print(f"  never collected: {', '.join(missing)}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
