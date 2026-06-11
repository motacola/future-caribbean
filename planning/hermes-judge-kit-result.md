# Hermes Judge Kit — Build Result

## What got built

- `JUDGE_DEMO.md` at the repo root, with all six required sections.
- `planning/hermes-judge-kit-result.md` (this file).

## What I verified live vs from the repo

Verified live against https://signal-fabric.vercel.app:
- `/api/status` returns `cadence_hours: 4`, `cycle_id: 20260611`, `n_clusters: 13`, `n_dispatches: 31`, six sources listed (all `ok: false` in the public status payload because the hosted instance surfaces the config, not runtime health from the watchers).
- `/feed.xml` builds at `lastBuildDate: Thu, 11 Jun 2026 17:22:38 +0000`.
- `/api/ask` with question "draft a note for Guyana" returned a deterministic answer with `engine: "deterministic"` and `generated_at: 2026-06-11T19:33:37.289488+00:00`, citing `outbox/dispatch_desk.json`.
- `/api/validation-packs` returns five packs for the current cycle, including `enhanced-invest-guyana`.
- `/api/validation-packs/enhanced-invest-guyana` includes a Guyana validation pack with `confidence_score: 100`, evidence grade A, and procurement matches containing a tender closing on `2026-06-16`.

Verified from the repo:
- README tone: plain, no hype, product-first.
- `PLAN_ENGINE_2026-06-10.md` documents the Vercel read-only split, deterministic ask, and agent-agnostic API design confirmed by the live manifests.
- `agents.md`, `llms.txt`, `mcp_adapter/README.md`, and `server.py` confirm the `/api/tools.json` contract, `/feed.xml` route, MCP connect instructions, and dashboard replay fallback from `data/history/*.jsonl`.
- `dashboard/generate.py` confirms the theater replay URL is built from `data/history/<latest>.jsonl`.
- `data/history/` contains cycle snapshots for 2026-06-10 and 2026-06-11, and `dashboard.html` is present, so `python3 -m http.server 8090` plus `/dashboard.html` is a real local fallback.
- Vercel endpoint `/api/domains` returns `404`; the hosted README doesn’t expose that as a live proof route, so I avoided putting a domains claim as a primary 60-second proof.

## Residual gaps or known caveats

- Local fallback runs the validator against Python’s stdlib http.server; nothing in the repo runs `server.py --public` or a similar production-only flag — the fallback is the existing `server.py` with full local read/write, not a true “public-mode only” mirror.
- Rehearsed answers about Jamaica tenders are based on the planning docs and the brief’s “session-gated” statement; the live site does not expose a validation pack for Jamaica, so I couldn’t verify that claim interactively in this session.
- The `/api/status` public response surfaces source `ok: false` for all six sources in the current hosted payload; the brief calls for “6 public sources,” so the script can still list six source names, but runtime availability isn’t observable until a live source check succeeds.

## Validation run

- `python3 -m pytest -q` → 42 passed in 2.78s.

## Files changed

- `/Users/christopherbelgrave/clawd/projects/future-caribbean/JUDGE_DEMO.md` (created)
- `/Users/christopherbelgrave/clawd/projects/future-caribbean/planning/hermes-judge-kit-result.md` (created)

No git commits, no other files touched.
