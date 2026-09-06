#!/usr/bin/env python3
"""The Abeng desk as plain functions, with no MCP SDK in sight.

Two transports serve these: the stdio adapter in desk_server.py, which a
local client like Claude Code launches, and the Streamable HTTP endpoint in
mcp_adapter/http.py, which is what a hosted instance exposes so an agent can
add Abeng without cloning anything.

Keeping the bodies here means the two transports cannot drift — the same
mistake that left four copies of the source-freshness check disagreeing with
each other.

Read-only by design. record_feedback writes, so it lives with the stdio
adapter and is absent from the public HTTP surface.
"""
from __future__ import annotations

import json
import sys
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from agent.query import ask, load_desk  # noqa: E402

SOURCE_KEYS = {
    "World Bank": "world_bank",
    "IDB": "idb",
    "NOAA": "noaa",
    "NDBC": "ndbc",
    "CARICOM / CDB": "tier2",
}


def _read_desk() -> dict:
    try:
        return load_desk()
    except FileNotFoundError as exc:
        raise RuntimeError(str(exc))


def desk_status() -> dict:
    """Source health, cycle info, dispatch counts and feedback outcomes."""
    desk = _read_desk()

    # One freshness rule for every surface (see packagers/source_health):
    # a snapshot file existing is not proof a source is alive.
    from packagers.source_health import source_freshness

    sources = source_freshness(ROOT, SOURCE_KEYS)

    feedback: dict = {}
    fb_p = ROOT / "data" / "feedback" / "state.json"
    if fb_p.exists():
        try:
            for e in json.loads(fb_p.read_text()).get("history", []):
                s = e.get("feedback_status", "unknown")
                feedback[s] = feedback.get(s, 0) + 1
        except Exception:
            pass

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


def list_signals(country: str | None = None) -> dict:
    """Current signals, optionally filtered by country (case-insensitive substring)."""
    desk = _read_desk()
    clusters = desk.get("clusters", []) or []

    if country:
        q = country.lower()
        clusters = [
            c for c in clusters
            if q in str(c.get("title", "")).lower()
            or q in str(c.get("country_cluster", "")).lower()
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


def get_dispatch(dispatch_id: str) -> dict:
    """One full dispatch by id."""
    path = ROOT / "outbox" / "opportunity_dispatches.json"
    if not path.exists():
        return {"ok": False, "error": "No dispatches file found"}
    try:
        data = json.loads(path.read_text(encoding="utf-8"))
        for d in data.get("dispatches", []):
            if d.get("dispatch_id") == dispatch_id:
                return {"ok": True, "dispatch": d}
        return {"ok": False, "error": f"Dispatch '{dispatch_id}' not found"}
    except Exception as exc:
        return {"ok": False, "error": str(exc)}


def get_validation_pack(signal_id: str) -> dict:
    """One full validation pack by signal id."""
    # The id becomes a filename, so it never gets to leave the directory.
    if "/" in signal_id or "\\" in signal_id or ".." in signal_id:
        return {"ok": False, "error": "Invalid signal_id"}

    path = ROOT / "outbox" / "validation_packs" / f"{signal_id}.json"
    if not path.exists():
        return {"ok": False, "error": f"Validation pack '{signal_id}' not found"}
    try:
        return {"ok": True, "pack": json.loads(path.read_text(encoding="utf-8"))}
    except Exception as exc:
        return {"ok": False, "error": str(exc)}


def ask_desk(question: str) -> dict:
    """A deterministic, cited answer from the current desk. No LLM involved."""
    desk = _read_desk()
    return {"question": question, "answer": ask(question, desk), "engine": "deterministic"}


# ── MCP tool declarations ────────────────────────────────────
# The schemas a client sees from tools/list. The stdio adapter derives its
# own from the function signatures; this is the HTTP transport's copy of the
# same contract.

READ_TOOLS: list[dict[str, Any]] = [
    {
        "name": "desk_status",
        "description": "Current engine status: source health with freshness, cycle info, "
                       "dispatch counts and feedback outcomes.",
        "inputSchema": {"type": "object", "properties": {}, "additionalProperties": False},
        "handler": desk_status,
    },
    {
        "name": "list_signals",
        "description": "List the current decision clusters, optionally filtered by country.",
        "inputSchema": {
            "type": "object",
            "properties": {
                "country": {
                    "type": "string",
                    "description": "Case-insensitive substring, e.g. 'Guyana'. Omit for all.",
                },
            },
            "additionalProperties": False,
        },
        "handler": list_signals,
    },
    {
        "name": "get_dispatch",
        "description": "Fetch one routed dispatch by its id, e.g. DSP-20260905-017.",
        "inputSchema": {
            "type": "object",
            "properties": {"dispatch_id": {"type": "string"}},
            "required": ["dispatch_id"],
            "additionalProperties": False,
        },
        "handler": get_dispatch,
    },
    {
        "name": "get_validation_pack",
        "description": "Fetch the auto-assembled diligence pack for a signal: sector "
                       "hypotheses, projects, procurement matches, and an advance/hold/"
                       "reject recommendation with reasons.",
        "inputSchema": {
            "type": "object",
            "properties": {"signal_id": {"type": "string"}},
            "required": ["signal_id"],
            "additionalProperties": False,
        },
        "handler": get_validation_pack,
    },
    {
        "name": "ask_desk",
        "description": "Ask a question against the current desk. Answers are deterministic "
                       "and cited — read from the generated artefacts, not an LLM.",
        "inputSchema": {
            "type": "object",
            "properties": {"question": {"type": "string"}},
            "required": ["question"],
            "additionalProperties": False,
        },
        "handler": ask_desk,
    },
]

TOOLS_BY_NAME = {t["name"]: t for t in READ_TOOLS}
