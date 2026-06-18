# Handover — Signal Fabric (Future Caribbean Buildathon, Open Track)

Signal Fabric is an agentic coordination infrastructure for fragmented economies: it watches public regional data, merges weak signals, routes opportunity dispatches to the right personas with auto-assembled diligence packs, and learns from recipient feedback. The Caribbean is the live proof; the engine is domain-agnostic (economic + climate instances today). Any agent can query it via HTTP, MCP, or CLI — it's deterministic, cited, and deployable now.

> For Hermes. Read this first to get full context before touching anything.
> Last updated: cycle 20260601. Repo: `motacola/future-caribbean` (private).
> Deployed: https://future-caribbean.fly.dev · Latest commit: `dea0d8a`.

---

## 1. What this project is

**Signal Fabric** — a domain-agnostic *agentic intelligence engine*. It watches
public data, reasons over it, and distributes routed intelligence to the people
who act on it. The Caribbean is the live proof; the engine deploys to any
fragmented public-data market.

Pipeline shape, repeated for every instance: **watch → reason → distribute**
(watcher agents → reasoning agents → distribution agents), running continuously.

**Competition target: Open Track** (`futurecaribbean.com/open-track`). Judged on
originality, technical ambition, real-world usefulness, scalability, product
thinking, long-term impact, execution, and ability to evolve. NOTE: the site
restructured to **10 tracks**; the old "Intelligence/Media/Distribution" track
is gone. We deliberately chose **Open Track** because every vertical track has a
"changes outcomes, not just intelligence / weak teams build apps" bar that a
signals product struggles against — Open Track rewards the *engine* instead.

---

## 2. Current state — what's live and working

### Two live instances (the core proof the engine is domain-agnostic)
- **Caribbean Economic Signals** (`domains/caribbean.json`) — 6 sources:
  World Bank, IDB, NOAA, NDBC, NHC, CARICOM/CDB. Routes to 8 personas.
- **Climate & Catastrophe Risk** (`domains/climate-catastrophe.json`) — reuses
  the NOAA/NDBC/NHC watchers, routes to insurer / reinsurer / resilience-planner.
  Emits an honest **all-clear** dispatch when the Caribbean is quiet.
- Three **blueprints** (compliance, trade, capital) — same schema, `status:
  blueprint`, honest `null` watchers where not wired.

### Web app (`server.py`, pure-stdlib http.server on `:8080`)
Routes:
- `/` and `/build` → **configurator.html** — the **Signal Fabric** interactive
  builder. THIS IS THE PREFERRED FRONT PAGE (user confirmed "the SIGNAL FABRIC
  version was the best"). Has: domain switcher (2 live + 3 blueprints),
  watch→reason→distribute pipeline diagram, reasoning panel, the Signal Builder
  (persona/country/signal/channel chips → live device previews for Telegram /
  WhatsApp / email / memo), deploy-a-domain wizard, continuity heartbeat,
  freshness badges, impact strip.
- `/briefing` (alias `/desk`) → **dashboard.html** — editorial briefing desk.
- `/system` → dashboard.html (carries the audit section).

APIs (all JSON, served by `server.py`):
- `GET /api/status` — source health, cycle id, cadence, cycle_count,
  live_instances, feedback outcomes.
- `GET /api/domains` — the domain registry (from `domains/registry.py`).
- `GET /api/reasoning` — cross-signal synthesis (`outbox/reasoning.json`).
- `GET /api/preview?domain=&persona=&countries=&signals=&channel=` — renders a
  dispatch as a recipient sees it. `domain=climate` switches instance + framing.
- `POST /api/domains/create` — the wizard; writes `domains/user-<slug>.json`
  (hardened: slug-only, status forced to blueprint, caps, dup rejection).
- `POST /api/send/telegram` — dry-run unless `TELEGRAM_BOT_TOKEN` set.
- `GET /api/whatsapp/link` — pre-filled wa.me share link (no Twilio).
- `GET /api/pipeline/stream` — SSE of a live pipeline run.

### CLI (`cli/signalctl.py`) — dependency-free, drives the same engine
```
python3 cli/signalctl.py status      # sources, cycle, instances, outcomes
python3 cli/signalctl.py domains      # list instances (live + blueprints)
python3 cli/signalctl.py signals --domain climate -n 8
python3 cli/signalctl.py preview --persona investor --channel telegram
python3 cli/signalctl.py preview --domain climate --persona policy
python3 cli/signalctl.py reason       # cross-signal synthesis
python3 cli/signalctl.py run          # one full pipeline cycle
python3 cli/signalctl.py send --channel telegram   # dry-run (add --live)
```

### Reasoning agent (`reasoners/synthesis.py`)
Cross-instance synthesis: convergence (multi-kind countries), conflict
(investment × vulnerability), hazard × momentum overlap. **Pluggable to an
H200-hosted model** via `LLM_BASE_URL` + `LLM_API_KEY` (or `OPENAI_API_KEY`),
OpenAI-compatible. Honest deterministic fallback; output labelled with engine
used. Currently runs deterministic (no key set).

---

## 3. CRITICAL gotcha — read before editing the front page

`configurator.html` is a **hand-maintained static file**. It is NOT generated.
`dashboard/generate.py` USED to regenerate it from a stale
`dashboard/configurator_template.html`, which silently wiped the engine
features on every pipeline run (this caused hours of "the design keeps
reverting"). That generation block has been **removed** from `generate.py`
(commit `8f07cae`). Do NOT re-add it. `configurator.html` gets all live data
from `/api/*` at runtime — it needs no templating.

`dashboard.html` IS generated from `dashboard/template.html` by `generate.py`.
Edit the **template**, not the output.

---

## 4. Architecture / key files

```
server.py                      # web server + all /api/* endpoints + cycle counter
run_pipeline.sh                # one full cycle: watchers → mergers → packagers → reasoner → dashboard
cli/signalctl.py               # command-line control
domains/*.json                 # instance manifests (the engine's config layer)
domains/registry.py            # load/validate/list domains; CLI: --json / --validate
domains/README.md              # the domain contract (for judges)
reasoners/synthesis.py         # reasoning agent (LLM-pluggable)
watchers/                      # world_bank, idb_ckan, noaa_nws, ndbc_buoy, nhc_storm, tier2
mergers/cross_source_merger.py # builds composite signals
packagers/                     # opportunity_dispatch, dispatch_desk, climate_dispatch, telegram_brief, ...
distributors/telegram_sender.py# live/dry-run Telegram
configurator.html              # SIGNAL FABRIC front page (STATIC — see §3)
dashboard/template.html        # editorial page source → dashboard.html
config/*.json                  # per-source + routing + composite-rule config
```

Data flows into `data/<source>/latest.json` and `outbox/*.json`
(`dispatch_desk.json`, `climate_desk.json`, `reasoning.json`). `data/` and
`outbox/` are gitignored; they regenerate each cycle.

---

## 5. Conventions / guardrails

- **Honesty is the rule.** Live vs blueprint is always labelled. Fallbacks say
  so ("nearest available signal"). Disclaimers: economic = "Screening signal,
  not investment advice"; climate = "Follow official emergency directives."
  Never fabricate data for a non-live domain.
- **All Python passes `ruff check`** for files we authored (server.py, cli/,
  domains/, reasoners/, packagers/climate_dispatch.py). NOTE: `dashboard/
  generate.py` and `packagers/dispatch_desk.py` have pre-existing E701/E401/E722
  style violations (compact `def f(): return` style) — out of scope, left alone.
- **No new cron jobs** — the user explicitly asked to hold off. There is an
  existing in-process 4h loop inside `server.py` (`pipeline_loop`); don't add
  system crontab / scheduled tasks until the user says so.
- NOAA is scoped to **Caribbean-only** zones (NWS San Juan AMZ7xx + PR/USVI) —
  don't widen it back to the basin "AM" area (pulled in Florida).
- Commit style: clear subject + body; co-author trailer
  `Co-Authored-By: Claude Opus 4.8 <noreply@anthropic.com>`.

---

## 6. Open threads / where the user left off

- **Page feel:** user wants the SIGNAL FABRIC page (current `/`) but feels it
  could be "more alive and interactive, not overwhelming." A focused question
  was asked (lead-with-builder / progressive-disclosure / motion / stronger
  hero) and dismissed — so DO NOT restructure unprompted. Wait for direction.
- **Live Telegram delivery:** sender + route exist but run dry-run. Needs the
  user's `TELEGRAM_BOT_TOKEN` + `TELEGRAM_CHAT_ID` in `.env` to go live.
- **LLM reasoning:** set `LLM_BASE_URL` + `LLM_API_KEY` (H200 endpoint) to flip
  the reasoning badge from "deterministic" to "⚡ model".
- Uncommitted working changes right now: `dashboard.html`,
  `data/editorial/state.json` (regenerated artifacts — safe to ignore/discard).

---

## 7. How to run locally

```
python3 server.py            # serves on :8080, runs one pipeline on startup
# then open http://localhost:8080/   (Signal Fabric builder)
python3 run_pipeline.sh      # run a cycle manually
python3 cli/signalctl.py status
python3 domains/registry.py  # see the instance registry
```
```
