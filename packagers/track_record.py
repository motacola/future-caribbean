"""Track Record — the desk's receipts.

Writes outbox/track_record.json from feedback history and opportunity dispatches.
"""
from __future__ import annotations

import json
import sys
from datetime import datetime, timezone
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from humanizer import humanize  # noqa: E402


MAX_CYCLES = 8


def parse_cycle_date(cycle_id: str) -> str:
    """Convert cycle_id like '20260611' to '11 Jun 2026'."""
    try:
        dt = datetime.strptime(cycle_id, "%Y%m%d")
        return dt.strftime("%d %b %Y")
    except Exception:
        return cycle_id


def main() -> None:
    # Load feedback state
    state_path = ROOT / "data" / "feedback" / "state.json"
    if not state_path.exists():
        print("track_record: no feedback state, skipping")
        return
    state = json.loads(state_path.read_text())
    history = state.get("history", []) or []
    boosts = state.get("boosts", {}) or {}
    feedback_provenance = state.get("feedback_provenance", "simulated")

    # Group history by cycle
    by_cycle: dict[str, list] = {}
    for entry in history:
        cycle = entry.get("cycle")
        if not cycle:
            continue
        by_cycle.setdefault(cycle, []).append(entry)

    # Load opportunity dispatches for lead signal matching
    dispatches_path = ROOT / "outbox" / "opportunity_dispatches.json"
    dispatch_by_cycle: dict[str, list] = {}
    if dispatches_path.exists():
        dispatches_data = json.loads(dispatches_path.read_text())
        for d in dispatches_data.get("dispatches", []) or []:
            cycle = d.get("cycle_id")
            if cycle:
                dispatch_by_cycle.setdefault(cycle, []).append(d)

    # The current cycle has dispatches but no feedback until recipients
    # respond. Keying the record off feedback alone dropped it entirely, so
    # the receipts page skipped whatever the desk had just published.
    for cycle in dispatch_by_cycle:
        by_cycle.setdefault(cycle, [])

    # Sort cycles newest first, take max MAX_CYCLES
    sorted_cycles = sorted(by_cycle.keys(), reverse=True)[:MAX_CYCLES]

    cycles_out = []
    for cycle_id in sorted_cycles:
        entries = by_cycle[cycle_id]

        # Count feedback status
        counts = {"forwarded": 0, "replied": 0, "opened": 0, "ignored": 0, "decision_changed": 0}
        for e in entries:
            status = e.get("feedback_status", "unknown")
            if status in counts:
                counts[status] += 1

        dispatch_count = len(entries)

        # Unique countries by response volume desc
        country_counts: dict[str, int] = {}
        for e in entries:
            country = e.get("country", "")
            if country:
                country_counts[country] = country_counts.get(country, 0) + 1
        countries = sorted(country_counts.keys(), key=lambda c: -country_counts[c])

        # Lead signal: only if we have dispatches for this cycle
        lead = {"country": "", "title": ""}
        if cycle_id in dispatch_by_cycle:
            cycle_dispatches = dispatch_by_cycle[cycle_id]
            if cycle_dispatches:
                # Highest confidence dispatch
                best = max(cycle_dispatches, key=lambda d: d.get("confidence_score", 0) or 0)
                lead = {
                    "country": best.get("country_cluster", ""),
                    "title": humanize(best.get("title", "")) or "",
                }

        cycles_out.append({
            "cycle_id": cycle_id,
            "responses": counts,
            "dispatch_count": dispatch_count,
            "countries": countries,
            "lead": lead,
        })

    output = {
        "generated_at": datetime.now(timezone.utc).isoformat(),
        "feedback_provenance": feedback_provenance,
        "current_boosts": boosts,
        "cycles": cycles_out,
    }

    dest = ROOT / "outbox" / "track_record.json"
    dest.write_text(json.dumps(output, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print(f"track_record: {len(cycles_out)} cycles -> {dest}")


if __name__ == "__main__":
    main()
