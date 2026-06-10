#!/usr/bin/env python3
"""MCP Adapter — Caribbean Opportunity Desk for Claude (and MCP-compatible agents).

Tools:
- desk_status: Source health, cycle info, dispatch counts, feedback outcomes
- list_signals(country?): Current signals, optionally filtered by country
- get_dispatch(dispatch_id): Full dispatch by ID
- get_validation_pack(signal_id): Full validation pack
- ask_desk(question): Deterministic Q&A against the dispatch desk
- record_feedback(dispatch_id, status, note?): Apply recipient feedback (write)

All tools wrap the SAME internals the HTTP API uses (agent.query, outbox JSON).
No duplicated logic beyond thin glue.

Transport: stdio (FastMCP style). Run with: `python3 mcp_adapter/desk_server.py`

Pipeline MUST NEVER import anything from mcp_adapter/.
"""

from __future__ import annotations

import json
import sys
from pathlib import Path

# Ensure we can import from the main project
ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

try:
    from mcp.server.fastmcp import FastMCP
except ImportError:
    print("ERROR: 'mcp' package not installed. Run: pip install -r mcp_adapter/requirements.txt", file=sys.stderr)
    sys.exit(1)

from agent.query import load_desk, ask, explain_lead, what_changed, drill_country, routes_for_persona, draft_note

mcp = FastMCP("caribbean-opportunity-desk")


def _read_desk() -> dict:
    """Load the dispatch desk, raising a clear error if missing."""
    try:
        return load_desk()
    except FileNotFoundError as exc:
        raise RuntimeError(str(exc))


@mcp.tool()
def desk_status() -> dict:
    """Get the current engine status: source health, cycle, dispatches, feedback outcomes."""
    desk = _read_desk()

    # Source health
    source_keys = {
        "World Bank": "world_bank",
        "IDB": "idb",
        "NOAA": "noaa",
        "NDBC": "ndbc",
        "CARICOM / CDB": "tier2",
    }
    sources: dict = {}
    for name, key in source_keys.items():
        p = ROOT / "data" / key / "latest.json"
        ok = p.exists()
        fetched_at = ""
        if ok:
            try:
                d = json.loads(p.read_text())
                fetched_at = d.get("fetched_at", "")
            except Exception:
                pass
        sources[key] = {"name": name, "ok": ok, "fetched_at": fetched_at}

    # Feedback outcomes
    feedback: dict = {}
    fb_p = ROOT / "data" / "feedback" / "state.json"
    if fb_p.exists():
        try:
            hist = json.loads(fb_p.read_text()).get("history", [])
            for e in hist:
                s = e.get("feedback_status", "unknown")
                feedback[s] = feedback.get(s, 0) + 1
        except Exception:
            pass

    # Cycle count
    cycle_count = 0
    cc_p = ROOT / "data" / ".cycle_count.json"
    if cc_p.exists():
        try:
            cycle_count = int(json.loads(cc_p.read_text()).get("count", 0))
        except Exception:
            pass

    return {
        "ok": True,
        "sources": sources,
        "n_sources_ok": sum(1 for s in sources.values() if s["ok"]),
        "n_dispatches": desk.get("dispatch_count", 0),
        "n_clusters": len(desk.get("clusters", [])),
        "cycle_id": desk.get("cycle_id", "—"),
        "generated_at": desk.get("generated_at", ""),
        "cadence_hours": 4,
        "cycle_count": cycle_count,
        "feedback": feedback,
    }


@mcp.tool()
def list_signals(country: str | None = None) -> dict:
    """List current signals, optionally filtered by country (case-insensitive substring)."""
    desk = _read_desk()
    clusters = desk.get("clusters", []) or []

    if country:
        q = country.lower()
        clusters = [
            c for c in clusters
            if q in str(c.get("title", "")).lower() or q in str(c.get("country_cluster", "")).lower()
        ]

    return {
        "ok": True,
        "signals": [
            {
                "cluster_id": c.get("cluster_id"),
                "title": c.get("title"),
                "country": c.get("country_cluster"),
                "decision": c.get("decision"),
                "confidence_score": c.get("confidence_score"),
                "evidence_grade": c.get("evidence_grade"),
                "freshness": c.get("freshness"),
                "risk_flags": c.get("risk_flags", []),
            }
            for c in clusters
        ],
    }


@mcp.tool()
def get_dispatch(dispatch_id: str) -> dict:
    """Get a full dispatch by dispatch_id."""
    dispatches_data = ROOT / "outbox" / "opportunity_dispatches.json"
    if not dispatches_data.exists():
        return {"ok": False, "error": "No dispatches file found"}

    try:
        data = json.loads(dispatches_data.read_text(encoding="utf-8"))
        for d in data.get("dispatches", []):
            if d.get("dispatch_id") == dispatch_id:
                return {"ok": True, "dispatch": d}
        return {"ok": False, "error": f"Dispatch '{dispatch_id}' not found"}
    except Exception as exc:
        return {"ok": False, "error": str(exc)}


@mcp.tool()
def get_validation_pack(signal_id: str) -> dict:
    """Get a full validation pack by signal_id."""
    # Sanitize
    if "/" in signal_id or ".." in signal_id:
        return {"ok": False, "error": "Invalid signal_id"}

    pack_path = ROOT / "outbox" / "validation_packs" / f"{signal_id}.json"
    if not pack_path.exists():
        return {"ok": False, "error": f"Validation pack '{signal_id}' not found"}

    try:
        return {"ok": True, "pack": json.loads(pack_path.read_text(encoding="utf-8"))}
    except Exception as exc:
        return {"ok": False, "error": str(exc)}


@mcp.tool()
def ask_desk(question: str) -> dict:
    """Ask a deterministic question against the current Dispatch Desk. Returns a cited answer."""
    desk = _read_desk()
    answer = ask(question, desk)
    return {
        "question": question,
        "answer": answer,
        "engine": "deterministic",
    }


@mcp.tool()
def record_feedback(dispatch_id: str, status: str, note: str = "") -> dict:
    """Record recipient feedback for a dispatch. Status: forwarded|replied|opened|decision_changed|ignored.
    
    This writes to available.json; the next pipeline cycle's apply phase will incorporate it
    into the persistent state and recompute boosts."""
    from packagers.feedback_intake import add_feedback

    try:
        entry = add_feedback(dispatch_id, status, note, source="mcp")
        return {"ok": True, "result": entry}
    except Exception as exc:
        return {"ok": False, "error": str(exc)}


if __name__ == "__main__":
    mcp.run()