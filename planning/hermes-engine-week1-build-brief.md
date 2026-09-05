# Hermes Build Brief — Engine Week 1: Agent-Agnostic Interface Layer

Claude has completed the strategy pass in `PLAN_ENGINE_2026-06-10.md`
(Phase 1 + 2A). Your job is implementation only.

Goal in one line: any agent — Claude via MCP, Hermes via HTTP, OpenClaw via
HTTP/CLI, or plain curl — can query this engine and get the same
deterministic, cited answers; humans get an "Ask the desk" panel on the
dashboard.

## Read First

- `PLAN_ENGINE_2026-06-10.md` (Decisions + Phase 1 + 2A sections)
- `agent/query.py` — the deterministic query engine you are exposing
- `server.py` — request handler patterns (`_api_status`, `_json`, `_read_json_body`)
- `outbox/validation_packs/index.json` and one pack file
- `cli/abengctl.py` — CLI subcommand patterns
- `dashboard/template.html` + `dashboard/generate.py` — placeholder/render pattern
- `tests/test_validation_pack.py` — test conventions

## Build (in this order)

### 1. Core agent endpoints in `server.py`
- `POST /api/ask` — body `{"question": "..."}`. Calls
  `agent.query.ask(question, desk)` with the desk loaded via
  `agent.query.load_desk()`. Returns `{"question", "answer", "engine":
  "deterministic", "generated_at"}`. Empty/missing question → 400.
- `GET /api/validation-packs` — returns `outbox/validation_packs/index.json`
  verbatim (404 with a clear message if missing).
- `GET /api/validation-packs/<signal_id>` — returns the matching pack JSON.
  Sanitise the path segment (reject `/`, `..`); unknown id → 404.

### 2. Tool manifest `GET /api/tools.json`
Hand-written JSON (a `TOOLS_MANIFEST` dict in `server.py` or
`api_manifest.py`) describing every callable tool: `name`, `description`,
`method`, `path`, `params` (JSON-schema-ish), `example_request`,
`example_response_keys`. Cover: ask, status, validation-packs (both),
domains, reasoning, feedback-apply (mark `"writes": true`). Include top-level
`{"engine": "Abeng", "product": "Abeng",
"version": 1}`.

### 3. Discovery files, served and committed
- `llms.txt` at repo root: what the engine is, base URL pattern, endpoint
  list, one curl example, pointer to `/api/tools.json` and `agents.md`.
- `agents.md` at repo root: connect instructions per framework —
  (a) plain HTTP/curl, (b) Hermes (point its HTTP tooling at
  `/api/tools.json`), (c) OpenClaw (same HTTP contract, plus
  `python3 cli/abengctl.py` for shell-tool agents), (d) Claude via the MCP
  adapter (see item 5). Keep each section copy-paste runnable.
- Serve both at `/llms.txt` and `/agents.md` from `server.py`.

### 4. `abengctl ask` subcommand
`python3 cli/abengctl.py ask "what changed this cycle"` → prints the answer
+ citation line, matching existing abengctl output style (bold/dim helpers).
Reuses `agent.query` directly (no HTTP). Nonzero exit if desk artifacts
missing.

### 5. MCP adapter (Claude ecosystem) — `mcp_adapter/desk_server.py`
- Tools: `desk_status`, `list_signals(country?)`, `get_dispatch(dispatch_id)`,
  `get_validation_pack(signal_id)`, `ask_desk(question)`,
  `record_feedback(dispatch_id, status, note?)`.
- Each tool wraps the SAME internals the HTTP API uses (import
  `agent.query`, read outbox JSON) — no duplicated logic beyond thin glue.
- Use the official `mcp` Python package (FastMCP style), stdio transport.
- `mcp_adapter/requirements.txt` with the `mcp` pin; `mcp_adapter/README.md`
  with the Claude Code/Desktop config snippet. The pipeline must NEVER
  import anything from `mcp_adapter/`.
- If the `mcp` package cannot be installed in this environment, still write
  the adapter + README and note it untested in your summary — do not block
  the rest of the brief on it.

### 6. "Ask the desk" panel in the dashboard
- New section in `dashboard/template.html` directly below the hero (before
  the proof strip): input box + submit, 4 suggestion chips ("Explain the
  lead signal", "What changed this cycle?", "Routes for diaspora investor",
  "Draft a note for Guyana"). POSTs to `/api/ask`, renders answer with the
  citation line styled distinctly (mono, muted).
- Must degrade gracefully: when `fetch` fails (dashboard.html opened
  statically), show the chips but replace the answer area with "Live desk
  offline — run `python3 server.py` to ask questions." Never a JS error.
- Match existing CSS variables/typography. Mobile: full-width, no overflow
  at 390px.
- Regenerate `dashboard.html` via `python3 dashboard/generate.py --no-open`.

### 7. Tests — `tests/test_agent_surface.py`
Stdlib/pytest only, no live server needed where avoidable:
- tools.json manifest: valid structure, every entry has name/method/path,
  ask + validation-packs present.
- `/api/ask` handler logic: question routes through `agent.query.ask` (test
  the function layer or use `http.client` against a server started on an
  ephemeral port in a thread WITHOUT the pipeline loop — import the handler
  class, not `__main__`).
- `abengctl ask` returns 0 and non-empty output via `subprocess`.
- llms.txt and agents.md exist and mention `/api/tools.json`.

## Constraints

- stdlib-only everywhere EXCEPT inside `mcp_adapter/` (isolated requirements).
- Do NOT run `git commit` — leave all changes in the working tree.
- Do NOT run `bash run_pipeline.sh` or start `server.py` via `__main__`
  (it auto-runs the pipeline and mutates outbox/ + data/). For HTTP tests,
  instantiate the handler on an ephemeral port without the pipeline thread.
- Do NOT touch `configurator.html` (hand-maintained, see note in
  `dashboard/generate.py`).
- Do NOT modify generated artifacts by hand (`dashboard.html` only via
  `generate.py`; nothing in `outbox/` or `data/` except files your code
  legitimately writes).
- All new endpoints are read-only except nothing — feedback stays on the
  existing `/api/feedback/apply`; reference it in the manifest, don't add a
  new write path.
- Keep the existing 9 tests passing.

## Validation

```bash
python3 -m py_compile server.py cli/abengctl.py dashboard/generate.py
python3 -m pytest -q                          # all pass, including new file
python3 cli/abengctl.py ask "explain lead"   # prints cited answer, exit 0
python3 dashboard/generate.py --no-open
grep -c "ask-desk\|askdesk" dashboard.html    # panel rendered, >0
python3 - <<'PY'
import json, urllib.request, threading, http.server, importlib
# minimal smoke: manifest is valid JSON with required tools
import sys; sys.path.insert(0, '.')
# adjust import to wherever TOOLS_MANIFEST lives:
from server import TOOLS_MANIFEST
names = {t["name"] for t in TOOLS_MANIFEST["tools"]}
assert {"ask", "status"} <= {n.split(".")[-1] for n in names} or "ask" in str(names)
print("manifest ok:", sorted(names))
PY
```

Final summary must list: changed/created files, validation command output,
anything untested (e.g. MCP adapter if package unavailable), and any risks.
Write the summary to `planning/hermes-engine-week1-result.md`.
