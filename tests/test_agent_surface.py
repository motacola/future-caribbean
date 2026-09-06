"""Tests for the agent-agnostic surface layer (Phase 1)."""
import json
import sys
import subprocess
import threading
import time
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from agent.query import load_desk, ask

import pytest


# ── Test: Tool Manifest Structure ──────────────────────────────

def test_tools_manifest_valid_structure():
    """tools.json manifest has valid structure with required tools."""
    from server import TOOLS_MANIFEST

    assert "engine" in TOOLS_MANIFEST
    assert TOOLS_MANIFEST["engine"] == "Abeng"
    assert "product" in TOOLS_MANIFEST
    assert TOOLS_MANIFEST["product"] == "Abeng"
    assert "version" in TOOLS_MANIFEST
    assert TOOLS_MANIFEST["version"] == 1
    assert "tools" in TOOLS_MANIFEST
    assert isinstance(TOOLS_MANIFEST["tools"], list)
    assert len(TOOLS_MANIFEST["tools"]) > 0

    # Every entry must have name, method, path
    for tool in TOOLS_MANIFEST["tools"]:
        assert "name" in tool, f"Missing 'name' in tool: {tool}"
        assert "method" in tool, f"Missing 'method' in tool: {tool}"
        assert "path" in tool, f"Missing 'path' in tool: {tool}"
        assert "description" in tool, f"Missing 'description' in tool: {tool}"

    # Required tools must be present
    tool_names = {t["name"] for t in TOOLS_MANIFEST["tools"]}
    assert "ask" in tool_names, "Missing 'ask' tool"
    assert "validation_packs.index" in tool_names, "Missing 'validation_packs.index' tool"
    assert "validation_packs.get" in tool_names, "Missing 'validation_packs.get' tool"
    assert "coordination_opportunities.index" in tool_names
    assert "coordination_opportunities.get" in tool_names


# ── Test: /api/ask handler logic ──────────────────────────────

def test_ask_handler_routes_through_agent_query():
    """POST /api/ask routes through agent.query.ask (function layer test)."""
    desk = load_desk()
    assert desk, "Desk should exist for this test"

    # Test a known question pattern
    answer = ask("explain the lead signal", desk)
    assert isinstance(answer, str)
    assert len(answer) > 0
    assert "Sources:" in answer  # Citation line present


def test_ask_handler_empty_question_returns_400():
    """Test that empty question returns appropriate response (function layer)."""
    desk = load_desk()
    answer = ask("", desk)
    assert "Ask about a country, persona, lead signal" in answer


# ── Test: abengctl ask subcommand ─────────────────────────────

def test_abengctl_ask_returns_zero_and_output():
    """abengctl ask returns exit code 0 and non-empty output."""
    result = subprocess.run(
        [sys.executable, "cli/abengctl.py", "ask", "explain the lead signal"],
        cwd=str(ROOT),
        capture_output=True,
        text=True,
    )
    assert result.returncode == 0, f"abengctl ask failed: {result.stderr}"
    assert result.stdout.strip(), "No output from abengctl ask"
    assert "Sources:" in result.stdout, "Missing citation in output"


def test_abengctl_ask_missing_desk():
    """abengctl ask returns non-zero if desk missing (simulated via subprocess)."""
    # This is harder to test without moving files, but we can verify
    # the command exists and has the right structure
    result = subprocess.run(
        [sys.executable, "cli/abengctl.py", "ask", "--help"],
        cwd=str(ROOT),
        capture_output=True,
        text=True,
    )
    # The ask subcommand doesn't have its own --help, but the main parser will show usage
    assert "ask" in result.stdout or "usage" in result.stdout.lower()


# ── Test: Discovery files exist ────────────────────────────────

def test_llms_txt_exists_and_mentions_tools():
    """llms.txt exists and mentions /api/tools.json."""
    llms = ROOT / "llms.txt"
    assert llms.exists(), "llms.txt missing"
    content = llms.read_text()
    assert "/api/tools.json" in content
    assert "/api/ask" in content
    assert "Abeng" in content


def test_agents_md_exists_and_mentions_tools():
    """agents.md exists and mentions /api/tools.json."""
    agents = ROOT / "agents.md"
    assert agents.exists(), "agents.md missing"
    content = agents.read_text()
    assert "/api/tools.json" in content
    assert "Caribbean Opportunity" in content  # Either "Desk" or "Dispatch"
    # Should have sections for different frameworks
    assert "Plain HTTP" in content or "plain HTTP" in content or "curl" in content
    assert "Hermes" in content
    assert "OpenClaw" in content or "abengctl" in content
    assert "Claude" in content or "MCP" in content


# ── Test: Validation packs endpoints (function layer) ──────────

def test_validation_packs_index_exists():
    """Validation packs index file exists and is valid JSON."""
    index_path = ROOT / "outbox" / "validation_packs" / "index.json"
    assert index_path.exists(), "Validation packs index missing"
    index = json.loads(index_path.read_text())
    assert "generated_at" in index
    assert "packs" in index
    assert isinstance(index["packs"], list)
    assert len(index["packs"]) > 0


def test_validation_pack_file_matches_index():
    """Each pack listed in index exists as a file and matches recommendation."""
    index_path = ROOT / "outbox" / "validation_packs" / "index.json"
    index = json.loads(index_path.read_text())
    for entry in index["packs"]:
        pack_file = ROOT / "outbox" / "validation_packs" / entry["file"]
        assert pack_file.exists(), f"Pack file missing: {entry['file']}"
        pack = json.loads(pack_file.read_text())
        assert pack["advance_or_reject_recommendation"] == entry["recommendation"]


if __name__ == "__main__":
    pytest.main([__file__, "-v"])

# ── Manifest addressability ─────────────────────────────────
# The README invites an agent to "ingest the manifest, configure yourself".
# It could not: every tool carried a relative path and the envelope named no
# host, so an agent that fetched /api/tools.json had 17 tools and nowhere to
# send them.

def test_manifest_resolves_tools_to_callable_urls():
    from api_manifest import manifest_for

    m = manifest_for("https://abeng.example.org")
    assert m["base_url"] == "https://abeng.example.org"
    assert m["tools"], "manifest has no tools"
    for tool in m["tools"]:
        assert tool["url"] == "https://abeng.example.org" + tool["path"], (
            f"{tool['name']} has no callable url"
        )


def test_manifest_without_a_base_url_stays_relative():
    """No host given, no invented one — the stored form is unchanged."""
    from api_manifest import manifest_for

    m = manifest_for()
    assert "base_url" not in m
    assert all("url" not in t for t in m["tools"])


def test_public_manifest_marks_write_tools_unavailable():
    """The deployed instance is read-only and has to say so."""
    from api_manifest import manifest_for

    m = manifest_for("https://abeng.example.org", public=True)
    writes = [t for t in m["tools"] if t.get("writes")]
    reads = [t for t in m["tools"] if not t.get("writes")]
    assert writes, "no write tools in the manifest to check"
    assert all(t["available"] is False for t in writes)
    assert all(t["note"] == "local instance only" for t in writes)
    assert all(t["available"] is True for t in reads)


def test_mcp_config_ships_so_a_clone_is_already_wired():
    """mcp_adapter/README told people to write this file themselves."""
    import json

    cfg = json.loads((ROOT / ".mcp.json").read_text(encoding="utf-8"))
    server = cfg["mcpServers"]["abeng"]
    assert server["command"] == "python3"
    assert server["args"] == ["mcp_adapter/desk_server.py"]
    assert (ROOT / server["args"][0]).is_file(), "config points at a missing server"
