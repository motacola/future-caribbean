# Connecting Agents to the Caribbean Opportunity Desk

The Signal Fabric engine exposes a **plain HTTP API** as its foundation — no SDK, no vendor lock-in. Every framework below hits the same endpoints.

**Base URL (local):** `http://localhost:8080`
**Base URL (hosted):** `https://signal-fabric.vercel.app`

**Tool manifest:** `GET /api/tools.json (see also /feed.xml — RSS of the latest signals)` — machine-readable, ingest to self-configure.

---

## (a) Plain HTTP / curl

No agent framework needed. The API is REST + JSON.

```bash
# Status check
curl https://signal-fabric.vercel.app/api/status

# Ask a question (deterministic, cited)
curl -X POST https://signal-fabric.vercel.app/api/ask \
  -H "Content-Type: application/json" \
  -d '{"question": "what changed this cycle"}'

# List validation packs
curl https://signal-fabric.vercel.app/api/validation-packs

# Get a specific pack
curl https://signal-fabric.vercel.app/api/validation-packs/enhanced-invest-guyana

# Tool manifest (for any tool-calling agent)
curl https://signal-fabric.vercel.app/api/tools.json
```

**Response shape (`/api/ask`):**
```json
{
  "question": "what changed this cycle",
  "answer": "Cycle 20260610 changed summary:\n- 3 decision clusters from 15 persona routes\n- Freshness mix: fresh: 2, stale: 1\n- Feedback-adjusted priority:\n- Guyana FDI surge: +3 (forwarded ×2, replied ×1)\n- Belize tourism: +1 (opened ×1)\n\nSources: `outbox/dispatch_desk.json`, `data/feedback/current_boosts.json`",
  "engine": "deterministic",
  "generated_at": "2026-06-10T15:30:00.000000+00:00"
}
```

---

## (b) Hermes (Nous Research)

Hermes uses **HTTP toolsets** pointed at `/api/tools.json`.

1. Create a toolset file (or use Hermes UI):

```json
{
  "name": "caribbean-desk",
  "type": "http",
  "url": "https://signal-fabric.vercel.app/api/tools.json",
  "auth": "none"
}
```

2. Or add via CLI:

```bash
hermes tools add http caribbean-desk https://signal-fabric.vercel.app/api/tools.json
```

3. Now Hermes can call `caribbean_desk.ask`, `caribbean_desk.status`, `caribbean_desk.validation_packs.get`, etc., directly.

**Example prompt:**
> "Ask the Caribbean desk what changed this cycle and show me the Guyana validation pack."

---

## (c) OpenClaw (or any HTTP-capable CLI agent)

OpenClaw can call the HTTP API directly, or use the provided **`signalctl` CLI** for shell-tool agents.

### Option 1: HTTP (same as plain curl above)

OpenClaw's HTTP tools pointed at `https://signal-fabric.vercel.app/api/tools.json`.

### Option 2: `signalctl` (no HTTP server needed — runs against local files)

```bash
# Install (already in repo)
python3 cli/signalctl.py ask "explain the lead signal"
python3 cli/signalctl.py ask "what changed this cycle"
python3 cli/signalctl.py ask "routes for diaspora investor"
python3 cli/signalctl.py ask "draft a note for Guyana"
```

**Output:** Formatted answer + citation line (bold/dim styling on TTY).

**Use from OpenClaw:** Define `signalctl` as a shell tool in your agent config.

---

## (d) Claude (via MCP)

The MCP adapter exposes the same operations as MCP tools over stdio.

### Setup (Claude Code)

Add to `claude_desktop_config.json` or `.mcp.json`:

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

### Setup (Claude Desktop)

Same config, ensure `python3` is on PATH and the `mcp` package is installed in the environment.

### Available MCP Tools

| Tool | Description |
|------|-------------|
| `desk_status` | Source health, cycle, dispatches, feedback counts |
| `list_signals(country?)` | Current signals, optionally filtered by country |
| `get_dispatch(dispatch_id)` | Full dispatch details |
| `get_validation_pack(signal_id)` | Full validation pack |
| `ask_desk(question)` | Deterministic Q&A (same as `/api/ask`) |
| `record_feedback(dispatch_id, status, note?)` | Apply feedback (write) |

**Example prompts in Claude:**
> "Use the Caribbean desk to explain the lead signal."
> "Get the Guyana validation pack and tell me the sector hypotheses."
> "What changed this cycle according to the desk?"

**Note:** The MCP adapter runs locally against your checked-out repo. For a hosted public instance, the MCP server would need to be deployed alongside the API (future work). The HTTP API at `https://signal-fabric.vercel.app` remains the universal interface.

---

## Notes for All Frameworks

- **Deterministic only:** Answers come from `agent/query.py` against `outbox/dispatch_desk.json` — no LLM generation, no hallucinations.
- **Read-first:** All endpoints are GET except `/api/ask` (POST, read-only) and `/api/feedback/apply` (POST, write).
- **No auth required locally.** Hosted instance requires `DESK_ADMIN_TOKEN` header for write endpoints.
- **Citations included:** Every answer ends with `Sources: `artifact1`, `artifact2`` pointing to verifiable files.
- **Pipeline must run first:** `bash run_pipeline.sh` generates the desk artifacts that the API queries.
