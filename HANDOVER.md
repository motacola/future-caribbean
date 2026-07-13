# Signal Fabric — Coordination Graph Handover (for Claude)

**Date:** 2026-07-12
**Repo:** `/Users/christopherbelgrave/clawd/projects/future-caribbean`
**Goal:** Build a deterministic Caribbean coordination graph that detects missing cross-market connections, prescribes the smallest verifiable action to reduce fragmentation, and closes the loop (intervention → evidence → graph update → score recompute → outcome recorded).

---

## 1. What is built and verified

- **Originating concept (Chris's "Caribbean algorithm"):** This whole Coordination Graph is the implementation of Chris's idea — a deterministic algorithm for reducing Caribbean economic fragmentation by modeling the region as a network where **each island/market is a node**, capabilities and demand are edges, and the engine computes *which connection is missing* and the smallest verifiable action to close it. Signal Fabric's coordination layer is the product embodiment of that algorithm. When extending this, preserve the "island-as-node + missing-edge detection + prescribed smallest intervention" shape — that is the core design intent, not just an implementation detail.
- **Island-as-node reality check (verified 2026-07-12):** The graph currently has **5 `country`/territory nodes**: `country:guyana`, `country:trinidad-tobago`, `country:barbados`, `country:jamaica`, and `country:eastern-caribbean-oecs`. So the "each island = a node" principle holds at the **market/territory level** for the major independent markets, but **OECS (Eastern Caribbean) is currently one grouped cluster node**, not one node per island (Antigua, Barbuda, St Lucia, Grenada, etc.). If Chris wants strict per-island granularity, the registry + graph builder need an OECS-expansion step. Flag this as a known divergence from the literal "each island = a node" phrasing.
- **Coordination graph engine** (`coordination/engine.py`): deterministic, no ML/LLM.
  - Builds a multi-layer graph (Geographic / Economic / Actor / Constraint nodes).
  - **Geographic layer = the island/market nodes** (the "Caribbean algorithm" backbone): currently Guyana, Trinidad & Tobago, Barbados, Jamaica, and Eastern Caribbean/OECS as country-type nodes; projects attach via `LOCATED_IN`; capabilities attach via `REQUIRES_CAPABILITY` / `HAS_CAPABILITY`.
  - Extracts real advertised tenders from `data/tenders/latest.json` into Project nodes with `LOCATED_IN` (Project→Country) and `REQUIRES_CAPABILITY` (Project→Capability) edges.
  - Classifies tenders with a deterministic ordered-keyword classifier (`TENDER_CLASSIFIERS`): aviation_infrastructure, water_and_irrigation, medical_supplies, digital_and_ict, education_infrastructure, transport_and_logistics, climate_resilience, construction_and_works, general_procurement (fallback). Classification recorded as `deterministic_keyword` or `category_fallback`.
  - Matches demand (Guyana projects) → regional supply (Trinidad/Barbados/Jamaica) → finance → logistics → friction.
  - Gap score: `G = O * C * R * A * T - F` (O=opportunity magnitude, C=complementarity, R=regional relevance, A=actionability, T=trust, F=friction).
  - Produces Coordination Opportunities with `unlock_path` (blocker→intervention→owner→evidence request→success condition→estimated score uplift).
- **Intervention persistence + campaigns** (`coordination/interventions.py`): `apply_interventions(opportunity)` reads `data/intervention_state.json`, seeds `proposed` state for each unlock-path entry, groups by `(type, blocker, owner)` into `operator_campaigns`, and writes the state file.
- **Operator outcome feedback** (`coordination/interventions.py` + `coordination/engine.py`): `submit_outcome(state_id, type, note)` records one of `intro_accepted` | `supplier_validated` | `blocked_logistics` on an intervention. `engine._apply_outcomes()` (wired into `run()`) feeds these back into scoring — `supplier_validated` +4, `intro_accepted` +3 (de-risk nudge), `blocked_logistics` leaves the gap open but records the reason in `frictions` + `unknowns` (honest, not hidden). Verified: a `supplier_validated` outcome moved a candidate 50 → 54 with `outcome_adjustment: +4`.
- **Operator CLI** (`cli/signalctl.py` is the primary CLI; `coordination/cli.py` supplements it): `cli/signalctl.py coordinator status|submit-evidence|verify` covers the evidence lifecycle. `coordination/cli.py` adds `run`, `state [--id]`, `submit-outcome --id --type ... [--note]` (the outcome feedback command — not in `cli/signalctl.py`), plus `submit-evidence`/`verify` mirrors. `coordination/console.py` is the local web UI.
- **Local operator console** (`coordination/console.py`, stdlib-only): `python3 coordination/console.py [--port 8765]` → http://localhost:8765. Lists interventions with one-click outcome/evidence/verify buttons; persists to `data/intervention_state.json`, reruns the engine, and prints the commit command to ship. Local-first by design — Vercel's runtime FS is read-only, so outcomes are recorded locally then committed + deployed (same artifact-commit convention as the rest of the pipeline).
- **Regional Connections product surface** (`src/pages/regional-connections.astro`): server-rendered page reading `outbox/coordination_opportunities.json` + `data/coordination/graph.json` + `data/intervention_state.json` at build time. Shows the island-as-node network, all coordination candidates, and a live "Closed loop — interventions" section with status pills + outcome badges. Reachable from the index masthead.
- **Validation pack enrichment** (`packagers/validation_pack_generator.py`): injects `coordination_path` (score, demand countries, minimum next action, contributing countries, matched capabilities) into the dev-pipeline validation pack.
- **API contract** (`api/coordination-opportunities.py`, `api_manifest.py`, `server.py`): `/api/coordination-opportunities` index + get; contract now advertises project demand, missing capabilities, frictions, owned unlock interventions, score-uplift estimates, cited evidence.
- **Pipeline integration** (`run_pipeline.sh`): "Coordination Graph" step added after Opportunity Dispatch.
- **Capability registry** (`config/regional_capabilities.json`): pilot, screening-level, cited-evidence only, NOT audited supplier capacity. Expanded taxonomy: civil_engineering, aviation_infrastructure, water_infrastructure, medical_supply, ict_integration, education_services.

**Verified state before lifecycle work:**
- Full suite: 69 passed, build passed, `git diff --check` passed.
- Graph: 28 nodes / 51 edges; 2 coordination candidates (food-security path, development-pipeline path).

---

## 2. Lifecycle stage — CURRENT STATUS: **CLOSED** (completed 2026-07-12, see §7)

> The loop described elsewhere as "partially built but blocked" is **fully closed**. All items below are DONE; recorded here as historical context only. Do NOT re-implement.

### Files touched in this stage (historical)
- Created `coordination/interventions.py` (persistence + campaigns + full lifecycle).
- Patched `coordination/engine.py` `run()` to call `apply_interventions(opportunity, root=...)` and set `opportunities["interventions_persisted"]`.
- Added `tests/test_coordination.py::test_run_persists_intervention_state_and_campaigns`.
- Added `coordinator status | submit-evidence | verify` subcommands to the **real** `cli/signalctl.py` (proper subparsers; the earlier overwrite-with-stub incident was reverted via `git checkout HEAD -- cli/signalctl.py` before re-adding correctly).

### Historical bug (now fixed)
The persistence layer hardcoded `_STATE` to repo ROOT, ignoring the `root` passed to `engine.run(tmp_path)`, which broke the isolation test. **Fixed** by making `apply_interventions(opportunity, root=ROOT)` accept a root param and threading it through `run()` → `build_opportunities()` → `apply_interventions()`. Test now passes (part of the 74 green).

### Known caveat carried forward (NOT a bug)
The 4 per-project `education_services` unlock items (projects 00369–00372) each emit `+10` uplift but collapse into ONE operator campaign keyed on `(capability_verification, education_services, ecosystem_builder)`. Verifying the capability once adds the edge serving all four — so naive summing of `estimated_total_uplift` across the flat `unlock_path` overstates gain. `opportunity.estimated_total_uplift` is currently `None`; resolution is a Claude next-step (see §3 #2).

---

## 3. What Claude should do next (ordered)

> **STATUS NOTE:** The lifecycle/loop stage is **ALREADY CLOSED** (see §7), and the operator tooling (CLI + console + outcome feedback + Regional Connections page) is **BUILT and merged** (2026-07-13). Do NOT re-implement. The remaining work is product decisions, not missing plumbing.

1. **Run a first live `verify()` end-to-end** to exercise the closed loop on real data. `data/coordination/track_record.json` still does **not** exist because no intervention has been verified — all 24 are `proposed`. The unit tests cover `verify()` (it requeues the engine and writes before/after scores), but no live verification has fired. Operator path: `python3 coordination/console.py` → click an intervention → submit-evidence → verify, then commit + deploy.
2. **Fix the `estimated_total_uplift` over-summing caveat:** the 4 per-project `education_services` unlock items each claim `+10` uplift, but they collapse into ONE operator campaign (`campaign-capability_verification-ecosystem_builder-education_services`) — verifying the capability once adds the edge that serves all four. Anything summing `estimated_total_uplift` across the flat `unlock_path` overstates gain. `opportunity.estimated_total_uplift` is currently `None`; decide whether to (a) null it / compute it from campaigns instead of flat items, or (b) cap per-campaign uplift. Make the choice deterministic and document it.
3. **Decide on OECS granularity:** currently `country:eastern-caribbean-oecs` is ONE clustered node. Scoring counts "complementary regional nodes," so a cluster undercounts them. Splitting OECS into per-island nodes (Antigua, St Lucia, Grenada, etc.) is the bigger structural change and the most natural next piece of work. Requires registry + graph-builder expansion.
4. Run `PYTEST_DISABLE_PLUGIN_AUTOLOAD=1 python3 -m pytest tests -q` → expect **81** passing. `pnpm run build` + `git diff --check` clean.

---

## 4. Critical rules / pitfalls (from this thread)

- **Pytest isolation:** run with `PYTEST_DISABLE_PLUGIN_AUTOLOAD=1` — LangSmith/pydantic_core plugins contaminate the suite on this machine and cause spurious failures.
- **Never run full `run_pipeline.sh`** — its final stages send Telegram/webhook alerts. Verify the coordination stage by direct `python3 coordination/engine.py` execution.
- **Deterministic only:** no LLM inference in matching/classification. Ordered keyword rules, cited evidence.
- **`cli/signalctl.py` is the primary CLI** and DOES exist (status/domains/signals/preview/reason/run/send + `coordinator status|submit-evidence|verify`). It does **not** have a `submit-outcome` command — that's why `coordination/cli.py` (adds `submit-outcome` + `run`/`state`) and `coordination/console.py` (web UI) were added this session. Use `cli/signalctl.py` for the evidence lifecycle; use `coordination/cli.py`/`console.py` for operator outcomes.
- **Don't fabricate data:** capability registry is screening-level pilot data, explicitly marked as NOT audited supplier capacity.

---

## 5. Key commands

```bash
cd /Users/christopherbelgrave/clawd/projects/future-caribbean
python3 coordination/engine.py                              # rebuild graph + opportunities
python3 packagers/validation_pack_generator.py              # (if used directly)
PYTEST_DISABLE_PLUGIN_AUTOLOAD=1 python3 -m pytest tests -q
pnpm run build
git diff --check

# Primary CLI (cli/signalctl.py):
python3 cli/signalctl.py coordinator status
python3 cli/signalctl.py coordinator submit-evidence --id <id> --summary "..." --source "..." [--country BB]
python3 cli/signalctl.py coordinator verify --id <id>

# Supplement CLI (coordination/cli.py) — adds submit-outcome + run/state:
python3 coordination/cli.py run
python3 coordination/cli.py state
python3 coordination/cli.py submit-outcome --id <id> --type supplier_validated [--note "..."]

# Local operator console (coordination/console.py):
python3 coordination/console.py --port 8765   # → http://localhost:8765
```

## 6. Current artifacts

- `outbox/coordination_opportunities.json` — 13 candidates (as of 2026-07-13), `interventions_persisted: true`.
- `data/coordination/graph.json` — 36 nodes, 59 edges (13 country, 15 capability, 8 project + edges).
- `data/intervention_state.json` — 24 interventions (all `proposed`), 9 campaigns (verified 2026-07-12; unchanged since).
- `data/coordination/track_record.json` — **does NOT exist yet**; created on first `verify()`. No intervention verified so far.
- `outbox/validation_packs/dev-pipeline-regional.{md,json}` — includes `coordination_path` (score, demand countries, minimum next action, contributing countries, matched capabilities) + the `humanized_unlock_path`.
- `src/pages/regional-connections.astro` — live product surface; reads the three artifacts above at build time.

---

## 7. COMPLETED 2026-07-12 (this session)
All items in §3 are done: root-isolation bug fixed (`apply_interventions(opportunity, root=ROOT)`, threaded through `engine.run`), coordinator CLI subcommands added to the real `cli/signalctl.py` (`coordinator status`, `coordinator submit-evidence --id --summary --source [--country]`, `coordinator verify --id`), and the lifecycle/evidence workflow implemented in `coordination/interventions.py`:
- Transitions: proposed → evidence_requested → evidence_received → verified/rejected/expired (invalid transitions raise).
- `add_evidence`, `request_evidence`, `reject`, `expire`, `verify`.
- `verify()` requires evidence naming a country for capability interventions, records a `verified_edge`, reruns the engine, and appends before/after scores to `data/coordination/track_record.json`.
- `apply_verified_capabilities()` merges verified edges into the in-memory registry at `engine.run()` time, so the graph gains a cited `HAS_CAPABILITY` edge (status `verified_intervention`) and scores recompute deterministically.
Verified: 74 tests pass (`PYTEST_DISABLE_PLUGIN_AUTOLOAD=1`), `pnpm run build` passes, `git diff --check` clean, engine run 28 nodes/51 edges/2 candidates. Stale `test` entry removed from `data/intervention_state.json`.

> 📌 Note: §7 references `cli/signalctl.py coordinator …` subcommands — that file **does exist** on `main` and has `status` / `submit-evidence` / `verify`. It does **not** have `submit-outcome`; that command was added in `coordination/cli.py` + `coordination/console.py` (2026-07-13). Both CLIs are valid; use `cli/signalctl.py` for the evidence lifecycle.

---

## 8. COMPLETED 2026-07-13 (coordination MVP finish)

Built and merged on top of the closed lifecycle (PRs #5–#10):

- **Copy humanize** (#6): `minimum_next_action` rewritten to plain voice; `humanized_unlock_path` (deduped, plain-language) added to each opportunity; titles kept as technical labels.
- **Regional Connections surface** (#7): `src/pages/regional-connections.astro` — server-rendered page showing the island-as-node network + all 13 candidates + a live "Closed loop — interventions" section (status pills + outcome badges). Linked from index masthead. Live at `/regional-connections`.
- **Operator outcome feedback** (#8): `interventions.submit_outcome()` + `engine._apply_outcomes()` feed outcomes into scoring (`supplier_validated` +4, `intro_accepted` +3, `blocked_logistics` honest flag). `coordination/cli.py` exposes `run`/`state`/`submit-evidence`/`verify`/`submit-outcome`.
- **Live state on page** (#9): page reads `data/intervention_state.json` and renders per-campaign status + outcome badges.
- **Operator console** (#10): `coordination/console.py` — local stdlib HTTP console at `http://localhost:8765` with one-click outcome/evidence/verify; persists + regenerates + prints commit command. Local-first because Vercel runtime FS is read-only.

Verified: **81 tests pass** (`PYTEST_DISABLE_PLUGIN_AUTOLOAD=1`), `pnpm run build` clean, all 6 Vercel checks green, live page confirmed serving with interventions section. Each PR merged via squash after CI; no force-push.

**Remaining (product decisions, not plumbing):** first live `verify()` (track_record.json still absent), `estimated_total_uplift` over-sum caveat (§3 #2), OECS per-island granularity (§3 #3).