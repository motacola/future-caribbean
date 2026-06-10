# Hermes Build Brief — 5B: Free Public Deploy (Vercel + GitHub Actions)

Strategy pass: `PLAN_ENGINE_2026-06-10.md` (open question 2, decided).
Implementation only. Goal: Chris's friends open a Vercel URL and use the
live product; agents hit the same URL's API. Total hosting cost: $0.

Architecture (decided, do not redesign):
- **GitHub Actions cron** runs the pipeline every 4h and commits artifacts.
- **Vercel** serves `dashboard.html` + static artifacts, plus Python
  serverless functions for the read-only APIs.
- **No write endpoints are deployed.** Public instance is read-only by
  construction. `server.py` local behaviour stays untouched.

## Read First

- `PLAN_ENGINE_2026-06-10.md` — Decisions + open question 2 resolution
- `server.py` — the handlers you are porting (ask, tools.json,
  validation-packs, map-data, status); port logic, do not import server.py
  from functions (it starts nothing at import, but keep functions thin)
- `agent/query.py`, `map_data.py` — reused directly by functions
- `dashboard/template.html` JS — every `fetch('/api/...')` call site and the
  existing graceful-degradation paths
- `.gitignore` — note `data/*/latest.json` is ignored; the workflow
  regenerates them at run time, they are NOT committed
- Vercel Python runtime docs (functions in `api/*.py`,
  `BaseHTTPRequestHandler` style or WSGI/ASGI app)

## Build

### 1. `.github/workflows/pipeline.yml`
- Triggers: `schedule: cron "7 */4 * * *"` + `workflow_dispatch`.
- Steps: checkout → setup-python 3.12 → `bash run_pipeline.sh` (Telegram
  step already self-skips without credentials — verify it exits 0 without
  them; if the script's failure summary would exit 1 for telegram-only
  failures, guard that) → commit & push artifact paths only:
  `outbox/ dashboard.html data/history/ data/.cycle_count.json
  data/editorial/ data/feedback/ data/ndbc/history.json`.
- Commit as `github-actions[bot]`, message `cycle: <UTC timestamp>`.
  Use `[skip ci]`-free messages (Vercel must redeploy on these pushes).
- Guard: `git diff --quiet && exit 0` — no empty commits.
- Concurrency group so overlapping runs never double-commit.

### 2. Vercel serverless functions in `api/`
Python, stdlib + repo modules only. Each reads committed JSON relative to
repo root (resolve via `Path(__file__).resolve().parents[1]`; configure
`includeFiles` in `vercel.json` if the runtime prunes non-`api/` files —
verify this works, it is the main platform risk):
- `api/ask.py` — POST `{question}` → `agent.query.ask()` → JSON with
  citations. Reject >500 char questions (413). GET returns usage hint.
- `api/status.py` — port of `_api_status` read-only parts + `public_mode:
  true`, `host: "vercel"`.
- `api/validation-packs.py` + `api/validation-packs/[id].py` (or one
  function with path param) — same sanitisation as server.py.
- `api/map-data.py` — wraps `map_data.build_map_data`.
- `/api/tools.json` — serve the manifest as a static file or rewrite to a
  function; manifest entries must mark the missing write tools as
  `"available": false, "note": "local instance only"` on this deployment
  (generate a public variant rather than lying).

### 3. `vercel.json`
- Rewrites: `/` → `/dashboard.html`; `/api/tools.json` → manifest;
  validation-pack pretty paths.
- Exclude from deployment via `.vercelignore`: `planning/`, `tests/`,
  `data/` EXCEPT `data/history/` (theater replay needs it), `cli/`,
  `mergers/`, `watchers/`, `packagers/`, `distributors/`, `.flue/`,
  `mcp_adapter/`, `*.md` working docs (KEEP `llms.txt`, `agents.md`,
  `dashboard.html`, `outbox/validation_packs/`).
  Resolve the tension carefully: functions need `agent/` and `map_data.py`
  and `outbox/*.json` — those must deploy.
- Set `regions` to the default; no env vars required.

### 4. Dashboard public-host compatibility
In `dashboard/template.html` JS:
- All fetches use relative paths (audit: they already should).
- Theater: when `/api/pipeline/stream` is unavailable (404/network error on
  Vercel), automatically fall back to client-side replay — fetch the latest
  committed `data/history/<date>.jsonl` (deploy history dir statically) and
  play events with the same 10x compression locally in JS. Label the mode
  "Replay (recorded cycle)". No SSE function on Vercel — do not attempt
  streaming functions.
- Ask-the-desk: works against `api/ask.py` unchanged; keep the offline
  message for the pure-static case.
- Regenerate `dashboard.html` via `python3 dashboard/generate.py --no-open`.

### 5. Docs
- `README.md`: replace the "Deployment" section with the Vercel + Actions
  split (3 steps: import repo in Vercel, enable the workflow, done) and the
  live-URL placeholder. Note write APIs are local-only.
- `agents.md` + `llms.txt`: add the public base URL placeholder
  `https://<project>.vercel.app` with the same examples.

### 6. Tests — `tests/test_vercel_surface.py`
- Each `api/*.py` function handler imports cleanly and returns valid JSON
  for a synthetic request (invoke handler class/function directly — no
  Vercel emulator).
- Workflow YAML parses (`python -c "import yaml"` is NOT available —
  stdlib only; do a minimal structural check or skip YAML parsing and
  assert the file exists + contains `schedule:` and `workflow_dispatch:`).
- `.vercelignore` does not exclude `agent/`, `map_data.py`, `outbox/`, or
  `data/history/`.
- Existing suite stays green.

## Constraints

- stdlib only (functions and tests). No new deps, no `requirements.txt` at
  root (Vercel must not try to install anything).
- No `git commit`. No `run_pipeline.sh`. No `server.py` `__main__`.
- Do NOT modify `server.py` write endpoints or local behaviour; this brief
  adds files and dashboard JS fallbacks only (plus README/agents.md edits).
- Do NOT add any write-capable function under `api/`.
- Do NOT touch `configurator.html`.
- You cannot run a real Vercel deploy — flag anything you could not verify
  (especially `includeFiles`/file-pruning behaviour) prominently in the
  result file.

## Validation

```bash
python3 -m py_compile api/*.py
python3 -m pytest -q                      # full suite green
python3 dashboard/generate.py --no-open   # regenerates with fallbacks
grep -n "workflow_dispatch" .github/workflows/pipeline.yml
```

Final summary to `planning/hermes-engine-5b-result.md`: changed/created
files, validation output, UNVERIFIED list (platform behaviours needing the
first real deploy), and the exact human steps Chris must do in the Vercel
dashboard (import repo → framework preset "Other" → deploy).
