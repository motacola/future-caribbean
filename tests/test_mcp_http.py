"""The hosted MCP endpoint.

The stdio adapter only ever helped someone who had already cloned the repo,
so "add Abeng to my agent" meant "first, clone this". mcp_adapter/http.py is
the Streamable HTTP transport that removes that step; it is mounted at /mcp
locally and deployed as api/mcp.py.

Verified end to end against the official MCP SDK client separately; these
cover the protocol contract and the guarantees that matter — read-only, and
one shared set of tool bodies rather than a copy per transport.
"""
from __future__ import annotations

import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from mcp_adapter.http import (  # noqa: E402
    PROTOCOL_VERSION,
    SUPPORTED_PROTOCOL_VERSIONS,
    handle_payload,
)


def _rpc(method: str, params: dict | None = None, req_id: int | None = 1):
    msg = {"jsonrpc": "2.0", "method": method}
    if req_id is not None:
        msg["id"] = req_id
    if params is not None:
        msg["params"] = params
    return handle_payload(json.dumps(msg))


def test_initialize_declares_the_server_and_its_tools():
    status, res = _rpc("initialize", {"protocolVersion": PROTOCOL_VERSION})
    assert status == 200
    result = res["result"]
    assert result["serverInfo"]["name"] == "abeng"
    assert result["capabilities"]["tools"] is not None
    assert result["instructions"], "a client shows these to its model"


def test_initialize_negotiates_the_client_version():
    """Echo a version we speak; fall back to ours when we do not."""
    for asked in SUPPORTED_PROTOCOL_VERSIONS:
        _, res = _rpc("initialize", {"protocolVersion": asked})
        assert res["result"]["protocolVersion"] == asked

    _, res = _rpc("initialize", {"protocolVersion": "1999-01-01"})
    assert res["result"]["protocolVersion"] == PROTOCOL_VERSION


def test_notifications_get_no_response():
    """A notification carries no id, so answering one breaks the client."""
    status, res = handle_payload(
        json.dumps({"jsonrpc": "2.0", "method": "notifications/initialized"})
    )
    assert status == 202
    assert res is None


def test_tools_list_is_a_usable_schema():
    _, res = _rpc("tools/list")
    tools = res["result"]["tools"]
    assert {t["name"] for t in tools} == {
        "desk_status", "list_signals", "get_dispatch",
        "get_validation_pack", "ask_desk",
    }
    for tool in tools:
        assert tool["description"].strip()
        schema = tool["inputSchema"]
        assert schema["type"] == "object"
        for name in schema.get("required", []):
            assert name in schema["properties"], f"{tool['name']} requires an undeclared arg"


def test_tool_call_returns_content_and_structured_payload():
    _, res = _rpc("tools/call", {"name": "ask_desk", "arguments": {"question": "explain lead"}})
    result = res["result"]
    assert result["isError"] is False
    assert result["content"][0]["type"] == "text"
    # Handed over structured too, so a client need not re-parse the text.
    assert result["structuredContent"]["engine"] == "deterministic"


def test_a_tool_that_finds_nothing_is_an_error_result_not_a_transport_error():
    """The request was valid; the answer is "no such thing"."""
    _, res = _rpc("tools/call", {"name": "get_dispatch", "arguments": {"dispatch_id": "nope"}})
    assert "error" not in res, "a missing record is not a JSON-RPC failure"
    assert res["result"]["isError"] is True
    assert "not found" in res["result"]["content"][0]["text"].lower()


def test_unknown_tool_and_unknown_method_are_reported_differently():
    _, res = _rpc("tools/call", {"name": "drop_tables", "arguments": {}})
    assert res["result"]["isError"] is True

    _, res = _rpc("resources/read", {})
    assert res["error"]["code"] == -32601


def test_malformed_json_does_not_crash_the_endpoint():
    status, res = handle_payload("{not json")
    assert status == 400
    assert res["error"]["code"] == -32700


def test_the_hosted_surface_exposes_no_write_tool():
    """The deployment serves published artefacts; nothing here can change them."""
    from mcp_adapter.tools import READ_TOOLS

    assert "record_feedback" not in {t["name"] for t in READ_TOOLS}


def test_both_transports_share_one_set_of_tool_bodies():
    """Four copies of the freshness check once disagreed. Not again."""
    source = (ROOT / "mcp_adapter" / "desk_server.py").read_text(encoding="utf-8")
    assert "from mcp_adapter import tools as desk_tools" in source
    for name in ("desk_status", "list_signals", "ask_desk"):
        assert f"desk_tools.{name}(" in source, f"{name} is not delegating"


def test_mcp_post_is_public_because_it_only_reads():
    """Without this the admin gate answers 503 and no client can connect."""
    import server

    assert "/mcp" in server.PUBLIC_POST_PATHS
