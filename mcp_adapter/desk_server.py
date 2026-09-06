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
except ImportError as exc:
    # Distinguish "no SDK" from "wrong SDK": v2 renamed FastMCP to MCPServer
    # and moved the module, so an mcp 2.x install fails here too — and
    # reporting that as "not installed" sends people to reinstall the very
    # version that broke it.
    try:
        import mcp as _mcp  # noqa: F401
    except ImportError:
        print("ERROR: 'mcp' package not installed. Run: pip install -r mcp_adapter/requirements.txt",
              file=sys.stderr)
    else:
        print("ERROR: the installed 'mcp' package does not provide "
              "mcp.server.fastmcp.FastMCP — this adapter targets the v1 SDK "
              "and v2 renamed it to MCPServer.\n"
              f"       Underlying import error: {exc}\n"
              "       Install a compatible version: pip install -r mcp_adapter/requirements.txt",
              file=sys.stderr)
    sys.exit(1)

from agent.query import load_desk, ask, explain_lead, what_changed, drill_country, routes_for_persona, draft_note

mcp = FastMCP("caribbean-opportunity-desk")


# Tool bodies live in mcp_adapter/tools.py so the stdio transport here and
# the Streamable HTTP transport in mcp_adapter/http.py cannot drift apart.
from mcp_adapter import tools as desk_tools  # noqa: E402


@mcp.tool()
def desk_status() -> dict:
    """Get the current engine status: source health, cycle, dispatches, feedback outcomes."""
    return desk_tools.desk_status()


@mcp.tool()
def list_signals(country: str | None = None) -> dict:
    """List current signals, optionally filtered by country (case-insensitive substring)."""
    return desk_tools.list_signals(country)


@mcp.tool()
def get_dispatch(dispatch_id: str) -> dict:
    """Get a full dispatch by dispatch_id."""
    return desk_tools.get_dispatch(dispatch_id)


@mcp.tool()
def get_validation_pack(signal_id: str) -> dict:
    """Get a full validation pack by signal_id."""
    return desk_tools.get_validation_pack(signal_id)


@mcp.tool()
def ask_desk(question: str) -> dict:
    """Ask a deterministic question against the current Dispatch Desk. Returns a cited answer."""
    return desk_tools.ask_desk(question)


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