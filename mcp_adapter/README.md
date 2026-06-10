# Caribbean Opportunity Desk — MCP Adapter

This is a **thin wrapper** exposing the Signal Fabric engine's deterministic operations as MCP tools for the Claude ecosystem (Claude Code, Claude Desktop, or any MCP-compatible client).

**Key principle:** The pipeline (`run_pipeline.sh`, `server.py`, agents) **never imports anything from `mcp_adapter/`**. This adapter is a one-way consumer of the engine's output files.

---

## Installation

```bash
cd mcp_adapter
pip install -r requirements.txt
```

> **Note:** If the `mcp` package cannot be installed in your environment, the adapter code is still written and documented here — it is simply untested. The rest of the engine (HTTP API, CLI, dashboard) works without it.

---

## Configuration

### Claude Code (`.mcp.json` at repo root)

```json
{
  "mcpServers": {
    "caribbean-desk": {
      "command": "python3",
      "args": ["mcp_adapter/desk_server.py"],
      "cwd": "/path/to/future-caribbean"
    }
  }
}
```

### Claude Desktop (`claude_desktop_config.json`)

```json
{
  "mcpServers": {
    "caribbean-desk": {
      "command": "python3",
      "args": ["mcp_adapter/desk_server.py"],
      "cwd": "/absolute/path/to/future-caribbean"
    }
  }
}
```

> Ensure `python3` is on your PATH and the `mcp` package is available in that Python environment.

---

## Available Tools

| Tool | Parameters | Description |
|------|------------|-------------|
| `desk_status` | — | Source health, cycle info, dispatch counts, feedback outcomes |
| `list_signals` | `country?` (string) | Current signals, optionally filtered by country substring |
| `get_dispatch` | `dispatch_id` (string) | Full dispatch details by ID |
| `get_validation_pack` | `signal_id` (string) | Full validation pack (sector hypotheses, projects, procurement, etc.) |
| `ask_desk` | `question` (string) | **Deterministic Q&A** — same engine as `/api/ask` |
| `record_feedback` | `dispatch_id` (string), `status` (string), `note?` (string) | Record feedback (forwarded/replied/opened/decision_changed/ignored). Writes to `available.json`; next pipeline apply phase incorporates it. |

---

## Example Usage (in Claude)

> **You:** "Ask the Caribbean desk what changed this cycle."

> **Claude (calls `ask_desk`):** Returns a cited answer like:
>
> ```
> Cycle 20260610 changed summary:
> - 3 decision clusters from 15 persona routes
> - Freshness mix: fresh: 2, stale: 1
> - Feedback-adjusted priority:
> - Guyana FDI surge: +3 (forwarded ×2, replied ×1)
> - Belize tourism: +1 (opened ×1)
>
> Sources: `outbox/dispatch_desk.json`, `data/feedback/current_boosts.json`
> ```

> **You:** "Get the Guyana validation pack."

> **Claude (calls `get_validation_pack` with `signal_id="enhanced-invest-guyana"`):** Returns the full pack with sector hypotheses, supporting projects, procurement matches, intro targets, and unresolved questions.

> **You:** "Record that I forwarded dispatch DSP-20260610-023."

> **Claude (calls `record_feedback`):** Writes to `available.json`. Next pipeline run (`feedback_loop.py apply`) will incorporate it and adjust signal priorities.

---

## How It Works

1. **Stdio transport** — MCP client launches `python3 mcp_adapter/desk_server.py` as a subprocess.
2. **Same internals** — Every tool imports `agent.query` or reads `outbox/*.json` directly. No separate logic.
3. **Read-first** — All tools are read-only except `record_feedback`, which appends to `available.json` (the standard intake path).
4. **Pipeline independence** — The engine runs normally via `run_pipeline.sh`. The MCP adapter is a passive consumer.

---

## Prerequisites

- Run the pipeline at least once: `bash run_pipeline.sh`
- This generates `outbox/dispatch_desk.json`, `outbox/validation_packs/`, etc.

---

## Troubleshooting

| Issue | Fix |
|-------|-----|
| `No dispatch desk found` | Run `bash run_pipeline.sh` first |
| `ModuleNotFoundError: mcp` | `pip install -r mcp_adapter/requirements.txt` |
| `Validation pack not found` | Check `outbox/validation_packs/index.json` for valid signal_ids |
| Feedback not affecting next cycle | Run `python3 packagers/feedback_loop.py apply` after recording feedback |

---

## Architecture Note

This adapter is intentionally isolated:
- **Pipeline** → writes `outbox/*.json`
- **MCP Adapter** → reads `outbox/*.json`, wraps `agent.query`
- **No circular deps** — Pipeline has zero knowledge of MCP

This keeps the deterministic engine pure and the MCP layer replaceable/upgradable independently.