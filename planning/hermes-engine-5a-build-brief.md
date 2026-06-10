# Hermes Build Brief — 5A: Read-Only Public Mode + Admin Token

Strategy pass: `PLAN_ENGINE_2026-06-10.md` Phase 5A. Implementation only.
This gates 5B (public deploy) — nothing goes on the internet until this
passes review. Security details below are requirements, not suggestions.

## Read First

- `PLAN_ENGINE_2026-06-10.md` (Phase 5 + hosting risk table)
- `server.py` — full handler (`do_GET`, `do_POST`, `_cors`, static serving)
- `tests/test_agent_surface.py`, `tests/test_pipeline_stream.py` — server test patterns

## Build

### 1. Public mode switch
- Activated by `--public` CLI flag OR `DESK_PUBLIC=1` env (either suffices).
- Expose a module-level `PUBLIC_MODE` bool; default off — local behaviour
  must be byte-for-byte unchanged when off.

### 2. Write-endpoint gate (public mode only)
- Every state-changing endpoint requires header `X-Desk-Admin-Token`
  matching env `DESK_ADMIN_TOKEN`: all `/api/send/*`, `/api/feedback/apply`,
  `/api/delivery/prepare`, `/api/delivery/approve`,
  `/api/delivery/send-approved`, `/api/domains/create`,
  `/api/history/archive`, and any other POST that writes.
- Compare with `hmac.compare_digest` (constant-time). 
- If `DESK_ADMIN_TOKEN` is unset/empty in public mode: ALL writes return 403
  (fail closed, body explains "public instance is read-only").
- Never log or echo the token.

### 3. Static file allowlist (public mode only)
The handler currently serves the working directory. In public mode, GET of
file paths is restricted to an explicit allowlist:
`/`, `/dashboard.html`, `/configurator.html`, `/llms.txt`, `/agents.md`,
plus `/api/*` routes. Everything else — especially `/.git/*`, `/planning/*`,
`/data/*`, `/outbox/*` (except via the API), `/cli/*`, `*.py`, dotfiles —
returns 404 (not 403; don't confirm existence). Add the validation-pack `.md`
files via API route or explicit `/outbox/validation_packs/<safe-id>.md`
allowlist entry with the same path sanitisation used in
`/api/validation-packs/<id>`.

### 4. Light abuse guards (public mode only)
- `/api/ask`: cap question length at 500 chars (413 above).
- In-memory per-IP rate limit on all `/api/*`: 60 requests/min sliding or
  bucket, stdlib only (dict + monotonic time, prune on access). Over limit →
  429 with `Retry-After: 30`. Keep it simple; this is a demo guard, not WAF.
- SSE stream: cap concurrent public streams at 20 (503 beyond).

### 5. Ops affordances
- `GET /api/status` gains `"public_mode": true|false`.
- `README.md`: short "Public deployment" section — flag, env vars, reverse
  proxy note (TLS terminates at Caddy/nginx; app binds 127.0.0.1 when
  public), example `curl` with admin header.
- `deploy/desk.service` example systemd unit (not wired anywhere, reference
  only).

### 6. Tests — extend `tests/test_agent_surface.py` or new `tests/test_public_mode.py`
Using the existing ephemeral-port ThreadingHTTPServer pattern (never the
`__main__` pipeline loop):
- Public mode, no token: POST to a write endpoint → 403. GET /api/ask → 200.
- Public mode, correct token header → write endpoint succeeds (use the most
  side-effect-free write available, or monkeypatch the handler action).
- Public mode: GET `/planning/hermes-engine-5a-build-brief.md`, `/.git/config`,
  `/server.py`, `/data/feedback/state.json` → all 404.
- Public mode: GET `/dashboard.html`, `/llms.txt` → 200.
- Local mode (default): writes work without token; `/server.py` still
  fetchable (unchanged behaviour).
- Question >500 chars in public mode → 413.

## Constraints

- stdlib only. No new dependencies.
- No `git commit`. No `run_pipeline.sh`. No `server.py` `__main__`.
- Do not change local-mode behaviour in any observable way.
- Do not weaken or remove any existing endpoint.
- Keep all 24 existing tests passing.

## Validation

```bash
python3 -m py_compile server.py
python3 -m pytest -q        # 24 existing + new public-mode tests, all pass
```

Final summary to `planning/hermes-engine-5a-result.md`: changed files,
validation output, and an explicit security checklist (each Build item 2–4
requirement → met/not met). 5B will not be dispatched until Claude reviews
that checklist.
