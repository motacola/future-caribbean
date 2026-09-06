#!/usr/bin/env python3
"""Streamable HTTP transport for the Abeng MCP server.

The stdio adapter only helps someone who has already cloned the repo. This
is the transport that makes "add Abeng to my agent" true for anyone with the
URL: a single endpoint speaking JSON-RPC 2.0, mounted at /mcp locally and on
the deployed instance.

Deliberately stateless. Every tool here is a read against artefacts the
pipeline already published, so there is no session to keep, no cursor to
track, and nothing a client can lose by reconnecting. That also means the
whole thing is a pure function of the request body, which is what lets the
same code run under a long-lived server and a serverless invocation.

Protocol version is negotiated: whatever the client asks for is echoed back
when we can speak it, otherwise our own. Written against the 2025-06-18
schema, verified against the mcp SDK's own client.
"""
from __future__ import annotations

import json
import sys
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from mcp_adapter.tools import READ_TOOLS, TOOLS_BY_NAME  # noqa: E402

SERVER_NAME = "abeng"
SERVER_VERSION = "1.0.0"
PROTOCOL_VERSION = "2025-06-18"
SUPPORTED_PROTOCOL_VERSIONS = ("2025-06-18", "2025-03-26", "2024-11-05")

INSTRUCTIONS = (
    "Abeng watches public Caribbean data and routes opportunity and risk "
    "dispatches to named decision-makers. Answers are deterministic and cited: "
    "they are read from the artefacts each pipeline cycle publishes, never "
    "generated, so they do not hallucinate. Start with desk_status for the "
    "current cycle, list_signals to see what is moving, then "
    "get_validation_pack for the evidence behind a signal."
)

# JSON-RPC 2.0
PARSE_ERROR = -32700
INVALID_REQUEST = -32600
METHOD_NOT_FOUND = -32601
INVALID_PARAMS = -32602
INTERNAL_ERROR = -32603


def _error(req_id: Any, code: int, message: str) -> dict:
    return {"jsonrpc": "2.0", "id": req_id, "error": {"code": code, "message": message}}


def _result(req_id: Any, result: dict) -> dict:
    return {"jsonrpc": "2.0", "id": req_id, "result": result}


def _tool_list() -> list[dict]:
    return [
        {"name": t["name"], "description": t["description"], "inputSchema": t["inputSchema"]}
        for t in READ_TOOLS
    ]


def _call_tool(name: str, arguments: dict) -> dict:
    """Run a tool and shape it as a CallToolResult.

    A tool that reports its own failure (unknown dispatch id, missing pack)
    comes back as isError with the text, not as a transport error: the
    request was fine, the answer is "no such thing".
    """
    tool = TOOLS_BY_NAME.get(name)
    if tool is None:
        return {
            "content": [{"type": "text", "text": f"Unknown tool: {name}"}],
            "isError": True,
        }

    try:
        payload = tool["handler"](**(arguments or {}))
    except TypeError as exc:
        return {"content": [{"type": "text", "text": f"Bad arguments: {exc}"}], "isError": True}
    except Exception as exc:
        return {"content": [{"type": "text", "text": f"{type(exc).__name__}: {exc}"}], "isError": True}

    text = json.dumps(payload, ensure_ascii=False, indent=2, default=str)
    return {
        "content": [{"type": "text", "text": text}],
        # Handed over structured as well, so a client that understands it does
        # not have to parse the text back out.
        "structuredContent": payload,
        "isError": payload.get("ok") is False,
    }


def handle_message(message: dict) -> dict | None:
    """One JSON-RPC message in, one response out — or None for a notification."""
    if not isinstance(message, dict) or message.get("jsonrpc") != "2.0":
        return _error(None, INVALID_REQUEST, "Not a JSON-RPC 2.0 message")

    method = message.get("method")
    req_id = message.get("id")
    params = message.get("params") or {}

    # Notifications carry no id and get no response, per the spec.
    is_notification = "id" not in message

    if method == "initialize":
        asked = str(params.get("protocolVersion") or "")
        version = asked if asked in SUPPORTED_PROTOCOL_VERSIONS else PROTOCOL_VERSION
        return _result(req_id, {
            "protocolVersion": version,
            "capabilities": {"tools": {"listChanged": False}},
            "serverInfo": {"name": SERVER_NAME, "version": SERVER_VERSION},
            "instructions": INSTRUCTIONS,
        })

    if method in ("notifications/initialized", "notifications/cancelled"):
        return None

    if method == "ping":
        return _result(req_id, {})

    if method == "tools/list":
        return _result(req_id, {"tools": _tool_list()})

    if method == "tools/call":
        name = params.get("name")
        if not name:
            return _error(req_id, INVALID_PARAMS, "tools/call needs a name")
        return _result(req_id, _call_tool(name, params.get("arguments") or {}))

    if is_notification:
        return None
    return _error(req_id, METHOD_NOT_FOUND, f"Method not found: {method}")


def handle_payload(raw: bytes | str) -> tuple[int, dict | list | None]:
    """Whole request body in, (status, response) out.

    Batches are handled because the 2025-03-26 clients still send them; a
    batch of notifications produces nothing to send back, which is a 202.
    """
    try:
        message = json.loads(raw or b"{}")
    except (json.JSONDecodeError, UnicodeDecodeError):
        return 400, _error(None, PARSE_ERROR, "Invalid JSON")

    if isinstance(message, list):
        if not message:
            return 400, _error(None, INVALID_REQUEST, "Empty batch")
        responses = [r for r in (handle_message(m) for m in message) if r is not None]
        return (200, responses) if responses else (202, None)

    response = handle_message(message)
    return (200, response) if response is not None else (202, None)
