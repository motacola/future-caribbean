#!/usr/bin/env python3
"""Editorial calendar context for Abeng.

Provides 'why now?' context per dispatch kind and country, based on
seasonal windows and upcoming events from config/editorial_calendar.json.
"""

from __future__ import annotations

import json
from datetime import date, timedelta
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parents[1]
CALENDAR_PATH = ROOT / "config" / "editorial_calendar.json"


def load_calendar() -> dict[str, Any]:
    """Load the editorial calendar config."""
    if not CALENDAR_PATH.exists():
        return {"seasons": [], "events": []}
    try:
        return json.loads(CALENDAR_PATH.read_text(encoding="utf-8"))
    except (json.JSONDecodeError, OSError):
        return {"seasons": [], "events": []}


def _current_seasons(
    calendar: dict[str, Any],
    now: date | None = None,
) -> list[dict[str, Any]]:
    """Return all season entries active on *now*."""
    if now is None:
        now = date.today()
    active: list[dict[str, Any]] = []
    for s in calendar.get("seasons", []):
        start = s.get("start", "")
        end = s.get("end", "")
        if not start or not end:
            continue
        try:
            sd = date(now.year, *map(int, start.split("-")))
            ed = date(now.year, *map(int, end.split("-")))
        except (ValueError, IndexError):
            continue
        # Handle year-crossing seasons (e.g., Dec 15 → Apr 15)
        if ed < sd:
            if now >= sd or now <= ed:
                active.append(s)
        else:
            if sd <= now <= ed:
                active.append(s)
    return active


def _upcoming_events(
    calendar: dict[str, Any],
    now: date | None = None,
    max_days_ahead: int = 30,
) -> list[dict[str, Any]]:
    """Return events within *max_days_ahead* of *now*."""
    if now is None:
        now = date.today()
    upcoming: list[dict[str, Any]] = []
    for ev in calendar.get("events", []):
        ev_date_str = ev.get("date", "")
        notice_days = ev.get("advance_notice_days", 14)
        if not ev_date_str:
            continue
        try:
            ev_date = date.fromisoformat(ev_date_str)
        except ValueError:
            continue
        window_start = ev_date - timedelta(days=notice_days)
        if window_start <= now <= ev_date:
            up = dict(ev)
            days_until = (ev_date - now).days
            up["days_until"] = days_until
            upcoming.append(up)
        elif now > ev_date and (now - ev_date).days <= 3:
            # Just happened — relevant for 3 days after
            up = dict(ev)
            up["days_until"] = 0
            up["just_happened"] = True
            upcoming.append(up)
    return upcoming


def get_why_now_context(
    now: date | None = None,
) -> dict[str, Any]:
    """Get active 'why now?' context for the current date.

    Returns:
    {
        "active_seasons": [...],
        "upcoming_events": [...],
        "headline": "Hurricane season in 6 days — operational alerts prioritized",
        "context_items": [...],  # formatted strings
        "per_kind": {kind: [context_strings]},  # sorted by urgency
    }
    """
    if now is None:
        now = date.today()
    calendar = load_calendar()

    seasons = _current_seasons(calendar, now)
    events = _upcoming_events(calendar, now)

    # Per-signal-kind context
    per_kind: dict[str, list[str]] = {}
    for s in seasons:
        for k in s.get("signal_kinds", []):
            per_kind.setdefault(k, []).append(
                f"{s['label']}: {s['relevance']}"
            )
    for ev in events:
        for k in ev.get("signal_kinds", []):
            days_str = f" in {ev['days_until']} days" if ev.get("days_until") else " (ongoing)"
            per_kind.setdefault(k, []).append(
                f"{ev['label']}{days_str}: {ev['relevance']}"
            )

    # Build headline
    headline_parts: list[str] = []
    for s in sorted(seasons, key=lambda x: x.get("urgency", "low") == "high", reverse=True):
        if s.get("urgency") == "high":
            headline_parts.append(f"{s['label']} active")
    for ev in events:
        if ev.get("urgency") == "high":
            headline_parts.append(f"{ev['label']} in {ev.get('days_until', '?')} days")
    if not headline_parts:
        headline_parts.append("No urgent seasonal context this cycle")
    headline = " — ".join(headline_parts[:3])

    return {
        "run_date": now.isoformat(),
        "active_seasons": seasons,
        "upcoming_events": events,
        "headline": headline,
        "per_kind": per_kind,
    }


def get_dispatch_why_now(
    signal_kind: str,
    country: str,
    why_now: dict[str, Any] | None = None,
) -> str:
    """Get a 'why now?' sentence for a specific dispatch kind + country."""
    if why_now is None:
        why_now = get_why_now_context()

    items = why_now.get("per_kind", {}).get(signal_kind, [])
    if not items:
        return ""

    # Take the most urgent item
    best = items[0]
    return f"Context: {best}"


def format_why_now_block(why_now: dict[str, Any]) -> list[str]:
    """Format the why-now context as display lines."""
    lines = []
    for s in why_now.get("active_seasons", []):
        emoji = "🔴" if s.get("urgency") == "high" else "🟡" if s.get("urgency") == "medium" else "🟢"
        action = s.get("action", "")
        lines.append(f"{emoji} **{s['label']}** — {s['relevance'][:120]}")
        if action:
            lines.append(f"   → {action}")
    for ev in why_now.get("upcoming_events", []):
        emoji = "🔴" if ev.get("urgency") == "high" else "🟡" if ev.get("urgency") == "medium" else "🟢"
        d = ev.get("days_until", 0)
        action = ev.get("action", "")
        if d == 0:
            lines.append(f"{emoji} **{ev['label']}** just happened — {ev['relevance'][:120]}")
        else:
            lines.append(f"{emoji} **{ev['label']}** in {d} days — {ev['relevance'][:120]}")
        if action:
            lines.append(f"   → {action}")
    return lines


def main() -> None:
    """CLI entry: print why-now context as markdown."""
    why_now = get_why_now_context()
    lines = [
        "# Why Now? Editorial Calendar Context",
        "",
        f"Run date: {why_now['run_date']}",
        "",
    ]
    lines.extend(format_why_now_block(why_now))
    outbox = ROOT / "outbox" / "why_now.md"
    outbox.parent.mkdir(parents=True, exist_ok=True)
    outbox.write_text("\n".join(lines).rstrip() + "\n", encoding="utf-8")
    print(f"Wrote {outbox}")


if __name__ == "__main__":
    main()
