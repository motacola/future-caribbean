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
from pipeline_util import output_path  # noqa: E402

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
    dest = output_path(ROOT / "outbox" / "track_record.json")
    previous_by_cycle: dict[str, dict] = {}
    if dest.exists():
        try:
            previous = json.loads(dest.read_text())
            previous_by_cycle = {
                str(c.get("cycle_id")): c
                for c in previous.get("cycles", []) or []
                if c.get("cycle_id")
            }
        except (OSError, json.JSONDecodeError):
            previous_by_cycle = {}

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
    # Previously published receipts must also stay candidates: once a cycle
    # ages out of BOTH the rolling dispatch artifact and the capped feedback
    # window it vanishes from by_cycle, and its public record would silently
    # disappear instead of being preserved below.
    for cycle in previous_by_cycle:
        by_cycle.setdefault(cycle, [])

    # Sort cycles newest first, take max MAX_CYCLES
    sorted_cycles = sorted(by_cycle.keys(), reverse=True)[:MAX_CYCLES]

    cycles_out = []
    for cycle_id in sorted_cycles:
        entries = by_cycle[cycle_id]
        cycle_dispatches = dispatch_by_cycle.get(cycle_id, [])

        # Count feedback status
        counts = {"forwarded": 0, "replied": 0, "opened": 0, "ignored": 0, "decision_changed": 0}
        for e in entries:
            status = e.get("feedback_status", "unknown")
            if status in counts:
                counts[status] += 1

        # Published receipts count what the desk actually routed for the
        # cycle — the same number dispatch_desk.json reports. Feedback
        # entries measure who responded, not how much went out; they are
        # already rendered as response pills. Fall back to entry count only
        # when the rolling dispatch artifact no longer holds that cycle.
        # When that rollover happens, preserve the previously PUBLISHED
        # count/markets instead of shrinking the receipt to the capped
        # 50-entry feedback sample (Codex P2 on PR #30) — same principle
        # as the historical lead preservation below.
        previous = previous_by_cycle.get(cycle_id, {})
        if cycle_dispatches:
            dispatch_count = len(cycle_dispatches)
        elif previous.get("dispatch_count") is not None:
            dispatch_count = previous["dispatch_count"]
        else:
            dispatch_count = len(entries)

        # Unique countries by response volume desc. Markets must come from
        # the same source as dispatch_count above: live cycles report the
        # countries the published dispatches actually span (the feedback
        # set is a small sample and understates coverage). Start from the
        # previously published list so rollover preserves it.
        countries: list[str] = list(previous.get("countries") or [])
        if cycle_dispatches:
            country_counts: dict[str, int] = {}
            for e in cycle_dispatches:
                country = e.get("country", "") or e.get("country_cluster", "")
                if country:
                    country_counts[country] = country_counts.get(country, 0) + 1
            countries = sorted(country_counts.keys(), key=lambda c: -country_counts[c])
        elif not previous.get("countries"):
            country_counts = {}
            for e in entries:
                country = e.get("country", "") or e.get("country_cluster", "")
                if country:
                    country_counts[country] = country_counts.get(country, 0) + 1
            countries = sorted(country_counts.keys(), key=lambda c: -country_counts[c])

        # Lead signal: only if we have dispatches for this cycle
        # Historical lead claims are part of the public receipt. Preserve the
        # previously published value when the rolling dispatch artifact no
        # longer contains that old cycle; recompute only when source
        # dispatches for the cycle are available.
        lead = previous_by_cycle.get(cycle_id, {}).get("lead") or {"country": "", "title": ""}
        if cycle_dispatches:
            best = max(
                cycle_dispatches,
                key=lambda d: d.get("confidence_raw", d.get("confidence_score", 0)) or 0,
            )
            lead = {
                "country": best.get("country_cluster", ""),
                "title": humanize(best.get("title", "")) or "",
            }

        # Per-signal-kind response attribution: which signal families earn
        # engagement, cycle over cycle. Feeds the loop — kinds nobody
        # responds to are candidates for downranking in feedback boosts.
        # "Ignored" is sampled feedback, not engagement (Codex P2): a kind
        # with 48 ignores and 1 forward must not read as 49 engagements.
        kind_totals: dict[str, int] = {}
        for e in entries:
            k = e.get("signal_kind", "")
            if k and e.get("feedback_status") != "ignored":
                kind_totals[k] = kind_totals.get(k, 0) + 1
        engagement_by_kind = dict(sorted(kind_totals.items(), key=lambda kv: -kv[1]))

        cycles_out.append({
            "cycle_id": cycle_id,
            "responses": counts,
            "engagement_by_kind": engagement_by_kind,
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

    dest.write_text(json.dumps(output, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print(f"track_record: {len(cycles_out)} cycles -> {dest}")


if __name__ == "__main__":
    main()
