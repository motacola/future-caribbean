# Future Caribbean Buildathon — Submission Answer Bank

Copy-paste source for https://os.futurecaribbean.com/builder/submission.
Every claim below is backed by a file or a live endpoint in this repo. Nothing here
describes simulated evidence as customer traction.

Numbers marked **(cycle)** come from the pipeline run of **2026-09-06 18:15 UTC, cycle `20260906`**
(`outbox/dispatch_desk.json`) and rotate every 4 hours. Re-check `https://abeng.vercel.app/api/status`
before pasting if the form is submitted on a later date.

---

## Core identifiers

| Field | Value |
|---|---|
| Project name | Abeng |
| Public name of the product surface | Abeng — the Caribbean Opportunity Desk |
| Track | Track 10 — Open Track |
| Category | Agentic market coordination infrastructure for fragmented economies |
| Live demo URL | https://abeng.vercel.app |
| Code repository | https://github.com/motacola/future-caribbean |
| Agent/API entry point | https://abeng.vercel.app/api/tools.json |
| MCP endpoint (no install) | https://abeng.vercel.app/mcp |
| Machine-readable feed | https://abeng.vercel.app/feed.xml |
| Agent discovery files | https://abeng.vercel.app/llms.txt · https://abeng.vercel.app/agents.md |
| Countries / territories watched | 23 markets on the live map; 15 carried signals this cycle **(cycle)** |
| Contact | chrisbelgrave@gmail.com |

---

## One-line pitch (≈140 chars)

> Abeng turns fragmented Caribbean public data into routed opportunity dispatches that humans read and any AI agent can query.

Alternate, if the field is longer:

> Abeng watches public Caribbean data every four hours, grades the signals, pre-assembles the diligence, and routes a clear next move to a named decision-maker — over web, HTTP, CLI and MCP.

---

## Short description (≈50 words)

> Abeng is agentic coordination infrastructure for fragmented economies. Every four hours it watches eight free public data sources, merges weak signals across them, and routes graded opportunity and risk dispatches to specific personas with an auto-assembled diligence pack. Humans read the desk; any agent queries the same deterministic, cited engine.

---

## The problem

> Caribbean opportunity data is scattered across institutions, countries and formats — a World Bank indicator here, a CDB procurement notice there, an ECCB bulletin, a CCRIF payout, a NOAA alert. That fragmentation delays investment decisions, procurement responses, resilience planning and founder matching. Deals and bidding windows are frequently missed before anyone notices they opened.
>
> Existing tools stop one step short. Data portals expose datasets but do not route decisions. Newsletters explain context but do not run a repeatable pipeline. Dashboards show status but do not package channel-ready action. Investor catalogues list opportunities but are not continuous watchers. And none of it is queryable by an AI agent.
>
> Abeng fills the last mile between public regional data and acted-on opportunity: it compresses the time between a public signal and an economic decision.

## The solution

> Abeng is a continuous multi-agent pipeline. Watchers pull public records, a reasoning merger fuses weak signals into composite signals across sources, packagers turn the strongest ones into routed dispatches, and a feedback loop re-weights the next cycle.
>
> Each cycle produces five things per signal:
> - **Priority** — what matters this cycle, evidence-graded (A cross-source → C single-source)
> - **Routing** — who should receive it: persona plus channel (7 personas, 5 channels this cycle)
> - **Action** — the decision it should trigger, with an action window and a named owner
> - **Validation** — an auto-assembled diligence pack: sector hypotheses with stated bases, matched IDB/CDB projects, live procurement with closing dates, real public intro targets (GO-Invest, JAMPRO, InvesTT), an explicit advance/hold/reject with reasons, and the unresolved questions a human still has to check
> - **Distribution** — channel-ready packets behind an approval-gated delivery manifest
>
> The useful artifact is the dispatch, not the chart.

## How it works (architecture)

> ```
> public data -> watchers -> normalized records -> reasoning merger -> composite signals
>                                                                   -> opportunity dispatches (the product)
>                                                                   -> validation packs (auto-diligence)
>                                                                   -> regional thesis + why-now context
>                                                                   -> feedback loop (re-weights next cycle)
>                                                                   -> agent interface (HTTP / MCP / CLI)
>                                                                   -> decision workspace (Astro site)
> ```
>
> Eight public, key-free sources: World Bank (REST), IDB Open Data (CKAN, 99 Caribbean datasets), CARICOM Statistics (126 datasets), CDB procurement (RSS), ECCB monetary stats, CCRIF SPC parametric payouts, NOAA NWS alerts, NDBC buoys. Fourteen composite signal rules fuse them — e.g. buoy pressure drop + marine advisory = cyclone risk; FDI surge + IDB project match + CARICOM data = enhanced investment signal; CDB procurement + stable maritime + logistics data = supply-chain opportunity.
>
> The pipeline runs on a 4-hour GitHub Actions cron, commits fresh artifacts, and redeploys. `server.py` is pure standard library; `deploy/` ships systemd units so any institution can self-host the whole thing.

## Agentic AI excellence — what to say

> Abeng is agent infrastructure, not an app with a chatbot bolted on.
>
> **Multi-agent coordination.** Independent watcher agents per source, a reasoning merger that resolves cross-source agreement, packager agents per persona and channel, a validation agent that runs the first diligence pass, and a feedback agent that re-weights scoring for the next cycle. Execution model: strategy and review by Claude, implementation by Hermes, engine pluggable by anything.
>
> **Agent-agnostic contract.** The foundation is a plain HTTP API plus a self-describing tool manifest at `/api/tools.json`; MCP is one adapter on top, not the base. The same engine answers over: browser, `POST /api/ask`, `python3 cli/abengctl.py ask`, the hosted MCP endpoint (`desk_status`, `list_signals`, `get_dispatch`, `get_validation_pack`, `ask_desk`), the Flue workflow harness, and an RSS feed. `llms.txt` and `agents.md` document every endpoint with copy-paste examples per framework.
>
> **Deterministic and cited.** Answers are generated from the desk artifacts, not by an LLM — so they are free, work offline, are reproducible, and cannot hallucinate in front of a judge. Every response carries `engine: deterministic`, a `generated_at` timestamp, and a `Sources:` line pointing at the `outbox/` file it came from. The LLM sits on the consuming side, where it belongs.
>
> **Human approval in the loop.** Delivery is prepare → approve → send, dry-run by default. Write endpoints are disabled unless `DESK_ADMIN_TOKEN` is set and presented as a bearer token. No dispatch leaves the system without an explicit approval ID.
>
> **Efficiency and scale.** Zero API keys, zero paid inference in the pipeline, ~4-hour cadence on free CI. The engine is domain-agnostic — economic and climate instances run today; the Caribbean is the live proof, not the limit.

## Innovation, uniqueness, defensibility

> Three things compound. First, cross-market normalization: turning thirteen inconsistent public sources across many small markets into one comparable signal space is the hard, unglamorous work, and it is done. Second, machine-readability: this is the first agent-ready opportunity surface for the region — as agents become the buyers of market data, being the endpoint they already know how to call is the moat. Third, the response loop: every dispatch carries a feedback path, and observed responses re-weight the next cycle's scoring, so routing accuracy improves with use in a way a static portal cannot copy.

## Product-market fit and business model

> The buyer is anyone who must act on Caribbean market movement before it is public consensus: regional investment funds and DFI teams, IPA and trade-promotion agencies, contractors bidding CDB/IDB procurement, insurers and resilience planners, and diaspora capital networks.
>
> Model: a free public desk for reach and credibility; paid tiers for private routing (your personas, your channels, your watchlist), institutional self-hosting, and agent/API access metered per query. The self-hosting path already exists in `deploy/`.
>
> Honest position: the closed-loop mechanism works with simulated response evidence (`feedback_provenance: simulated` at `/api/track-record`). The next validation step is replacing it with observed recipient outcomes from named design partners — not more product surface.

## What is live right now **(cycle 20260906)**

> - 27 decision clusters, 92 routed dispatches, 7 personas, 5 channels, this cycle
> - Lead signal: Guyana +860.3% capital surge, evidence-graded, routed to investor/founder via email brief + Telegram, with a validation pack including live Guyana eProcure tenders and their closing dates
> - Regional thesis, why-now editorial context, feedback review, judge brief, delivery manifest — regenerated every cycle
> - 23 Caribbean markets on the live map; every beacon carries either a routed live signal or a clearly labelled watchlist signal
> - Verify any of it: `/api/status`, `/api/validation-packs`, `/api/ask`, `/api/track-record`, `/feed.xml`

## Roadmap / what's next

> 1. Replace simulated feedback with observed recipient outcomes from three named design partners
> 2. Country coverage where portals allow it — Guyana eProcure is live; Jamaica GOJEP sits behind a session-gated portal and the system says so rather than fabricating coverage
> 3. Private routing tier: bring-your-own personas, watchlists and channels
> 4. A second regional instance to prove the engine is domain- and geography-agnostic
> 5. Signal permalink persistence (IDs currently rotate each cycle by design)

## Team

> _Fill in — the form will want names, roles and short bios._ Frame per the rubric's Team Quality line: execution speed (a full watch → merge → route → validate → distribute pipeline shipped and deployed), domain understanding (why Caribbean fragmentation is legible to you specifically), and product vision (agent-first regional infrastructure, not a dashboard).

## Demo video script (3 minutes)

> Use `JUDGE_DEMO.md` verbatim: 0:00 front page and live map · 0:30 click Guyana · 1:00 the lead story as a decision, not a headline · 1:45 ask the desk, cited answer · 2:15 the same answer via one curl call · 2:45 close on `/feed.xml`. Failure drills and per-claim proof commands are in the same file.

## If the form asks "is this AI-generated content?"

> The pipeline is deterministic: it merges public records, normalizes them and applies fixed scoring rules. The only LLMs are the agents that consume the desk. The humanizer is a translation layer, not a generator. Every answer and every feed item is cited from `outbox/*.json` or `outbox/*.md`.
