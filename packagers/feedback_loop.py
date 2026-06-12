#!/usr/bin/env python3
"""Persistent feedback loop for Caribbean Signal OS.

Maintains a feedback state file across cycles. Each cycle:
1. Reads previous feedback → computes boosts per signal kind + country
2. Writes current_boosts.json for editorial_enrichment to consume
3. After dispatch generation, saves new dispatch history + seed feedback

This makes the feedback loop real: forwarded/replied dispatches
actually change rankings in the next cycle.
"""

from __future__ import annotations

import json
import os
import sys
import tempfile
from datetime import datetime, timezone
from pathlib import Path
from typing import Any
import logging

LOGGER = logging.getLogger(__name__)

ROOT = Path(__file__).resolve().parents[1]
STATE_FILE = ROOT / "data" / "feedback" / "state.json"
BOOSTS_FILE = ROOT / "data" / "feedback" / "current_boosts.json"
FEEDBACK_LOG = ROOT / "data" / "feedback" / "delivery_log.jsonl"
AVAILABLE_FILE = ROOT / "data" / "feedback" / "available.json"

# Boost weights per feedback status
FEEDBACK_BOOST: dict[str, int] = {
    "forwarded": 8,
    "decision_changed": 10,
    "replied": 5,
    "opened": 2,
    "delivered": 0,
    "ignored": -2,
}

# Decay: each cycle after the feedback, boost halves
DECAY_PER_CYCLE = 0.5


# ── State I/O ──────────────────────────────────────────────

def load_feedback_state() -> dict[str, Any]:
    """Load feedback state from disk."""
    if STATE_FILE.exists():
        try:
            state = json.loads(STATE_FILE.read_text(encoding="utf-8"))
            if isinstance(state, dict):
                return state
        except (json.JSONDecodeError, OSError):
            LOGGER.warning("feedback state read error, starting fresh")
            pass
    return {"cycle": "", "history": [], "boosts": {}, "feedback_provenance": "simulated"}


def save_feedback_state(state: dict[str, Any]) -> None:
    """Persist feedback state to disk atomically (write-then-rename)."""
    STATE_FILE.parent.mkdir(parents=True, exist_ok=True)
    fd, tmp = tempfile.mkstemp(dir=STATE_FILE.parent, suffix=".tmp")
    try:
        with os.fdopen(fd, "w", encoding="utf-8") as f:
            f.write(json.dumps(state, indent=2) + "\n")
        os.replace(tmp, STATE_FILE)
    except Exception:
        try:
            os.unlink(tmp)
        except OSError:
            LOGGER.warning("temp file cleanup error")
        raise


def load_available_feedback() -> list[dict[str, Any]]:
    """Load manually-inserted feedback events (e.g. from Telegram reactions)."""
    if AVAILABLE_FILE.exists():
        try:
            data = json.loads(AVAILABLE_FILE.read_text(encoding="utf-8"))
            if isinstance(data, list):
                return data
        except (json.JSONDecodeError, OSError):
            LOGGER.warning("available feedback read error")
            pass
    return []


# ── Boost computation ──────────────────────────────────────

def compute_boosts(state: dict[str, Any]) -> dict[str, dict[str, int]]:
    """Compute net boost per signal kind + country from accumulated history.

    Returns: {signal_kind: {country: net_boost_int}}
    """
    boosts: dict[str, dict[str, int]] = {}

    for entry in state.get("history", []):
        kind = entry.get("signal_kind", "")
        country = entry.get("country", "")
        status = entry.get("feedback_status", "ignored")
        cycles_ago = entry.get("cycles_ago", 1)

        if not kind or not country:
            continue

        base = FEEDBACK_BOOST.get(status, 0)
        # Apply decay: each cycle halves the effect
        effective = int(base * (DECAY_PER_CYCLE ** cycles_ago))
        if effective == 0 and base > 0:
            effective = 1  # floor at 1 for positive boosts

        per_country = boosts.setdefault(kind, {})
        per_country[country] = per_country.get(country, 0) + effective

    return boosts


def write_boosts(boosts: dict[str, dict[str, int]]) -> None:
    """Write current cycle's boosts for editorial_enrichment to read."""
    BOOSTS_FILE.parent.mkdir(parents=True, exist_ok=True)
    payload = {
        "generated_at": datetime.now(timezone.utc).isoformat(),
        "boosts": boosts,
    }
    BOOSTS_FILE.write_text(json.dumps(payload, indent=2) + "\n", encoding="utf-8")


# ── History update ─────────────────────────────────────────

def add_cycle_history(
    state: dict[str, Any],
    dispatches: list[dict[str, Any]],
    cycle_id: str,
) -> dict[str, Any]:
    """Add current cycle's dispatches to history and age existing entries.

    Recording is idempotent for a cycle_id. During demos and cron retries the
    same daily cycle can be regenerated multiple times; replacing that cycle's
    entries prevents duplicate feedback from compounding boosts/penalties.
    """
    history: list[dict[str, Any]] = []
    for entry in state.get("history", []):
        if entry.get("cycle") == cycle_id:
            continue
        entry = dict(entry)
        entry["cycles_ago"] = entry.get("cycles_ago", 0) + 1
        history.append(entry)

    seen_dispatch_ids: set[str] = set()
    for d in dispatches:
        # Track meaningful signals (the per-country dispatches worth boosting)
        country = d.get("country_cluster", "")
        kind = d.get("signal_kind", "")
        status = d.get("feedback_status", "ignored")
        dispatch_id = d.get("dispatch_id", "")

        # Skip regional dispatches (they aggregate too many countries)
        if country == "Caribwide":
            continue
        if dispatch_id and dispatch_id in seen_dispatch_ids:
            continue
        if dispatch_id:
            seen_dispatch_ids.add(dispatch_id)

        history.append({
            "dispatch_id": dispatch_id,
            "signal_kind": kind,
            "country": country,
            "feedback_status": status,
            "cycle": cycle_id,
            "cycles_ago": 0,
        })

    # Cap history to last 50 entries so it doesn't grow unbounded
    history.sort(key=lambda e: e.get("cycles_ago", 99))
    state["history"] = history[:50]
    state["cycle"] = cycle_id

    return state


# ── Seed bootstrap ─────────────────────────────────────────

def seed_initial_feedback() -> dict[str, Any]:
    """Create seeded feedback for demo purposes (first run only).

    Simulates 5 feedback events from a 'last cycle' so the next run
    demonstrates real adaptation.
    """
    seed_history = [
        {"dispatch_id": "demo-fwd-guyana", "signal_kind": "enhanced_investment",
         "country": "Guyana", "feedback_status": "forwarded", "cycle": "20260525", "cycles_ago": 1},
        {"dispatch_id": "demo-reply-pipeline", "signal_kind": "development_pipeline",
         "country": "CARICOM", "feedback_status": "replied", "cycle": "20260525", "cycles_ago": 1},
        {"dispatch_id": "demo-open-belize", "signal_kind": "enhanced_investment",
         "country": "Belize", "feedback_status": "opened", "cycle": "20260525", "cycles_ago": 1},
        {"dispatch_id": "demo-decision-svg", "signal_kind": "economic_vulnerability",
         "country": "St. Vincent and the Grenadines", "feedback_status": "decision_changed",
         "cycle": "20260525", "cycles_ago": 1},
        {"dispatch_id": "demo-ignore-trinidad", "signal_kind": "enhanced_investment",
         "country": "Trinidad and Tobago", "feedback_status": "ignored",
         "cycle": "20260525", "cycles_ago": 1},
    ]
    return {
        "cycle": "20260525",
        "history": seed_history,
        "boosts": compute_boosts({"history": seed_history}),
        "feedback_provenance": "simulated",
    }


# ── Available feedback collector ───────────────────────────

def _load_dispatch_index() -> dict[str, dict]:
    """Build a dispatch_id → {signal_kind, country_cluster} lookup from the dispatches file."""
    dispatches_path = ROOT / "outbox" / "opportunity_dispatches.json"
    if not dispatches_path.exists():
        return {}
    try:
        data = json.loads(dispatches_path.read_text(encoding="utf-8"))
        return {
            d["dispatch_id"]: {
                "signal_kind": d.get("signal_kind", ""),
                "country": d.get("country_cluster", ""),
            }
            for d in data.get("dispatches", [])
            if d.get("dispatch_id")
        }
    except (json.JSONDecodeError, OSError, KeyError):
        return {}


def collect_available_feedback() -> None:
    """Read available.json (manual feedback insertions) and merge into state.

    Available.json format:
    [
        {"dispatch_id": "...", "feedback_status": "forwarded",
         "feedback_detail": "..."},
        ...
    ]
    This file is written by Telegram listeners or manual intake.
    """
    items = load_available_feedback()
    if not items:
        return

    state = load_feedback_state()
    state.setdefault("history", [])

    # Build dispatch lookup once so we can resolve kind + country from real dispatch IDs
    dispatch_index = _load_dispatch_index()

    for item in items:
        did = item.get("dispatch_id", "")
        status = item.get("feedback_status", "ignored")

        # Don't re-add if already in history
        if any(e.get("dispatch_id") == did for e in state["history"]):
            continue

        # Look up kind + country from the dispatches file first
        dispatch_meta = dispatch_index.get(did, {})
        kind = dispatch_meta.get("signal_kind", item.get("signal_kind", ""))
        country = dispatch_meta.get("country", item.get("country", ""))

        state["history"].append({
            "dispatch_id": did,
            "signal_kind": kind,
            "country": country,
            "feedback_status": status,
            "cycle": state.get("cycle", "live"),
            "cycles_ago": 0,
        })

    save_feedback_state(state)


# ── Main modes ─────────────────────────────────────────────

def apply_phase() -> None:
    """Run at pipeline start: read feedback, compute boosts, write current_boosts.json."""
    collect_available_feedback()
    state = load_feedback_state()

    # Bootstrap: if no state exists, seed it
    if not state.get("history"):
        state = seed_initial_feedback()
        save_feedback_state(state)

    boosts = compute_boosts(state)
    write_boosts(boosts)
    print(f"Feedback boosts applied: {len(boosts)} kinds with boosts")


def record_phase(dispatches: list[dict[str, Any]], cycle_id: str) -> None:
    """Run after dispatch generation: save dispatch history for next cycle."""
    state = load_feedback_state()
    state = add_cycle_history(state, dispatches, cycle_id)
    # Recompute and persist the boosts for reference
    state["boosts"] = compute_boosts(state)
    save_feedback_state(state)
    print(f"Feedback recorded: {len(dispatches)} dispatches → {len(state['history'])} history entries")


def record_from_dispatch_file(dispatches_path: Path) -> None:
    """Load dispatch output and record history."""
    if not dispatches_path.exists():
        print("No dispatches file found, skipping record phase")
        return
    try:
        data = json.loads(dispatches_path.read_text(encoding="utf-8"))
        dp = data.get("dispatches", [])
        cycle_id = "auto"
        # Extract cycle_id from dispatch IDs if available
        for d in dp:
            cid = d.get("cycle_id", "")
            if cid:
                cycle_id = cid
                break
        record_phase(dp, cycle_id)
    except (json.JSONDecodeError, OSError) as e:
        print(f"Could not read dispatches: {e}")


def main() -> None:
    """CLI dispatch: feedback_loop.py [apply|record] [--file path]."""
    action = sys.argv[1] if len(sys.argv) > 1 else "apply"

    if action == "apply":
        apply_phase()
    elif action == "record":
        # Check for --file argument
        file_arg = None
        if "--file" in sys.argv:
            idx = sys.argv.index("--file")
            if idx + 1 < len(sys.argv):
                file_arg = Path(sys.argv[idx + 1])
        if file_arg:
            record_from_dispatch_file(file_arg)
        else:
            print("Usage: feedback_loop.py record --file outbox/opportunity_dispatches.json")
    elif action == "seed":
        state = seed_initial_feedback()
        save_feedback_state(state)
        print(f"Seeded feedback: {len(state['history'])} history entries")
    else:
        print(f"Unknown action: {action}")
        print("Usage: feedback_loop.py [apply|record|seed]")


if __name__ == "__main__":
    main()
