# Handover — Signal Fabric ranking algorithm, calibration, and competitive position

**Date:** 2026-08-15 · **Cycle at handover:** `20260815` · **For:** Hermes (implementation), Chris (review)

This is a brief, not a changelog. It documents *why* the ranking works the way it now does,
what is under test, and where the genuinely unsolved problems are. Read §2 and §6 first if
you are looking for an angle.

Everything below is agent-agnostic: no Claude-specific tooling is assumed.

---

## 1. State at handover

| | |
|---|---|
| Python tests | 173 passing |
| Playwright e2e | 48 passing, 4 skipped |
| Build | clean (`node ./node_modules/astro/bin/astro.mjs build`) |
| New modules | `packagers/calibration.py` |
| New tests | `tests/test_signal_scoring.py`, `tests/test_calibration.py` |

**Note on `pnpm build`:** it triggers `pnpm install`, which aborts without a TTY and wants to
purge `node_modules`. Use `node ./node_modules/astro/bin/astro.mjs build` directly.

**Note on tests mutating tracked data:** the existing suite rewrites `outbox/track_record.json`,
`api/feedback-data.json`, `data/coordination/graph.json` and
`outbox/coordination_opportunities.json` on every run. I isolated the tests I wrote
(`tmp_path` fixtures) but did not fix the pre-existing ones. **A test run should not be able to
change what the site publishes.** Worth fixing early — it will bite during CI.

---

## 2. The ranking algorithm as it now stands

### 2.1 Signal score

`packagers/editorial_enrichment.compute_signal_score()` returns a **raw, unclamped** score:

```
  KIND_SCORE_WEIGHT[kind]                        30–54
+ priority bonus                                 high 18 / medium 10 / low 3
+ min(len(evidence) * 4, 12)
+ Σ SOURCE_SCORE_WEIGHT[s] for s in corroborating_sources
+ min(len(context_sources) * 2, 4)               capped — context is not corroboration
+ 8   if len(corroborating_sources) >= 3
+ magnitude_boost(pct)                           20 / 14 / 8 / 4  at ≥500 / 200 / 75 / 30 %
- staleness_penalty(age ÷ cadence)               18 / 12 / 7 / 3  at ≥4× / 3× / 2× / 1.5×
+ feedback_boost                                 applied to the RAW score, both directions
```

- `_score_raw` — ranking. May exceed 100. **Never clamp before ranking.**
- `_score` — display only, `display_score()` clamps to 0–100.

### 2.2 Two ideas the model now depends on

**Corroborating vs context sources.** A source that says something about *this country's claim*
is corroboration. A regional dataset that merely exists this cycle is context. Only the former
earns source weight, the three-source bonus, the evidence grade, or the words "multi-source"
in the headline. `corroborating_sources()` falls back to `sources` when a detector never split
them, so older detectors keep their previous weighting.

**Fact identity.** `fact_key = country|indicator|period`, e.g.
`Guyana|BX.KLT.DINV.CD.WD|2024`. Two signals sharing a `fact_key` describe **the same
observation** and must not be counted as two pieces of evidence.

### 2.3 Staleness is measured in refresh intervals, not days

`REFRESH_CADENCE_DAYS` per source (World Bank 365, CDB 90, NOAA 1…). Staleness is
`age ÷ cadence`. A World Bank annual series 18 months old is ~1.6 intervals — mildly overdue.
A tender 18 months old is ~20 intervals — dead. Absolute age would punish the first and excuse
the second.

`observed_period` is the period the evidence *describes*, not when we fetched it. These differ
by up to two years for World Bank series, which matters on a page whose masthead says "now".

### 2.4 Lead selection

`select_lead()` scores each country by:

```
max(weighted signal scores)                      NOT the mean — see §3.4
+ min(distinct_facts * 5, 20)                    distinct fact_keys, not records
+ min(corroborating_sources * 10, 30)
```

The lead is then the highest-scoring signal in the winning country.

### 2.5 Cluster ordering

`packagers/dispatch_desk.build_clusters()` sorts by:

```
confidence_raw → magnitude_pct → persona count → feedback flag
```

Persona count is a *routing artefact* and must never outrank evidence. It used to be the first
tiebreaker after a score that always tied.

---

## 3. The six defects, and how each was proven

Each was confirmed against live data before changing anything. Reproduce with the shipped
`data/composite/latest.json`.

### 3.1 The magnitude boost never fired on the signals that rank
`_transfer_fdi_magnitudes` wrote `"FDI change: 860.3%"`; `compute_signal_score` read
`/moved (?:up|down) ([\d.]+)%/`. **Writer/reader format mismatch** — the transfer, whose entire
purpose was to carry magnitude onto the ranking signals, was a no-op for scoring.

*Fix:* one shared `signal_magnitude_pct()` recognising every phrasing we emit, preferring a
structured `_magnitude_pct` field over prose.

### 3.2 The clamp destroyed the ranking
All three `enhanced_investment` signals scored **raw 114 → clamped 100**. Identical on every
component. They tied *before* the clamp too, so raising the cap alone would not have helped.

### 3.3 Feedback was one-directional
`min(score + boost, 100)` with `score` already 100: Guyana's `+7` vanished, Suriname's and
Barbados's `−9` applied. Guyana led because the others were *penalised*, not because
forwarding rewarded it.

### 3.4 Cluster scoring averaged, so breadth of evidence was a penalty
```
mean-based:  Suriname 170.2 > Guyana 154.2     ← Guyana loses for having a 3rd, weaker signal
max-based:   Guyana   256.5 > Suriname 218.5
```
Guyana carries three signals including a weak tourism one; Suriname carries two, both strong.
Averaging punished corroboration — backwards for a product whose thesis *is* corroboration.

### 3.5 Corroboration was two region-wide constants
In `mergers/cross_source_merger.py`, `has_caricom_trade` and `has_cdb_activity` were computed
**once, outside the per-country loop**. They mean "a CARICOM/CDB dataset exists this cycle" —
not that either says anything about Guyana. Every country inherited the same two "sources".

This was worth +30 source weight and the +8 three-source bonus — **38 of Guyana's 141 points** —
and it was what made the site say "validated by several sources".

*Fix:* `corroborating_sources` / `context_sources` split, and the claim was chased through every
surface it reached:

| Before | After |
|---|---|
| "All signals point to Guyana." | "Guyana is the one to watch." |
| "+860.3% multi-source capital surge" | "+860.3% capital surge on a single official source" |
| "A - multi-source" | "C - single-source" → "Early — one source so far" |
| "Multi-source validation confirms directional signal" | "One official source shows the movement — corroborate it before acting" |

### 3.6 One fact counted twice
`investment_signal` and `enhanced_investment` are both generated per country from the *same*
World Bank observation, so a country collected two `cross_signal_bonus` credits for one fact.

**Guyana still leads after all six fixes** — now on the 860.3% movement that actually
differentiates it, and stably under input reordering.

### 3.7 Also fixed, found while verifying
- `track_record` keyed cycles off feedback only, so a freshly published cycle vanished from the
  receipts page until someone responded.
- Freshness compared the **clamped** score against a **raw** stored one (a bug I introduced with
  the clamp change), which would have reported every capped signal as "weakened −41" next cycle.
  Freshness is now measured post-transfer on raw scores, with a `score_basis` marker so state
  written under the old scale is skipped for one cycle rather than producing phantom deltas.

---

## 4. Calibration — the part that accrues

`packagers/calibration.py`, wired into `run_pipeline.sh` after Track Record.

Every cycle: **record** each claim keyed by `fact_key` → **resolve** claims older than
`RESOLUTION_WINDOW_CYCLES` → **report** confirmation rate per score band to
`outbox/calibration.json`.

### What counts as confirmation, in strength order

1. `external_publisher` — an **independent** publisher covered the same country and topic after
   we published. Independence is by domain, excluding every source already cited on the signal
   (corroborating *and* context — a source we showed the reader cannot later confirm us).
   Requires `SOURCE_DOMAIN_ALIASES` because `"World Bank"` does not substring-match
   `worldbank.org`.
2. `indicator_revision` — a newer release of the same indicator held the move up (or gave it back).
3. `internal_persistence` — our own pipeline kept reporting it. **Weakest**, recorded as such.

The report exposes `resolved_by`, `externally_resolved` and `external_share` so a rate built on
outside agreement is never silently mixed with one built on self-repetition.

### It refuses to print what it has not earned

Below `MIN_SAMPLE` resolved claims, `confirmation_rate` is `None` and the page says:

> Ranking position, not a probability — 16 claims still open, 5 needed per band before a rate is published.

Once earned it becomes *"signals scored 85-100 have held up 61% of the time (23 resolved)"*.

### Dry run against the real 107-article corpus

```
Barbados  investment_signal  →  barbadostoday.bb, caribank.org
Guyana    investment_signal  →  caribank.org, guyanachronicle.com
Suriname  investment_signal  →  caribank.org
Guyana    tourism_impact     →  no independent coverage
```

3 of 10 resolve on outside evidence. **That ratio is itself a finding:** investment signals get
picked up by regional press; tourism signals do not. That says something real about which
outputs the region actually confirms — worth mining.

### Probabilistic scoring, pre-commitment, tamper-evidence — added after §5.4

Three upgrades prompted directly by the Vorenth finding:

**Brier score against a stated baseline.** Each claim now records a `forecast_probability` at
claim time plus the `prior_basis` used:
- `naive` — `score/100`. **This is the null model, and it is the claim the product makes
  implicitly every time it prints "84/100".** Measuring Brier against it shows exactly how wrong
  that implication is.
- `calibrated` — the band's own historical confirmation rate, computed from claims already
  resolved when this one was made, so it is genuinely out-of-sample.

The report publishes `brier`, `brier_naive_baseline`, `brier_improvement_over_naive`, `log_loss`
and `calibration_error`. **Beating the naive baseline is the value the ledger adds, and it is now
measured rather than asserted.** Probabilities are clamped to [0.05, 0.95] — log-loss is undefined
at the extremes, and certainty is never honest.

**Public pre-commitment.** `COMMITMENTS` in `calibration.py`, committed `2026-08-15`, rendered in
the receipts section of the homepage:

| Milestone | Gate |
|---|---|
| Day 30 | 20 resolved |
| Day 60 | 80 resolved · Brier ≤ 0.22 |
| Day 90 | 150 resolved · Brier ≤ 0.20 |
| Year 1 | 200 resolved · Brier ≤ 0.18 |

Gates are judged from `COMMITMENT_MADE_AT`, **not from today** — otherwise every gate stays
trivially passable forever. A due gate that is not met renders `missed`, in red, and stays on the
page. That is the point.

**Hash-chained ledger.** Each claim carries `prev_hash` and `hash` over the fields fixed at claim
time; resolution fields are deliberately excluded so recording an outcome does not break the
chain. `verify_chain()` returns `(intact, index_of_first_break)` and the report exposes
`chain_intact`. Editing or deleting a historical claim is detectable — no chain dependency
required. Vorenth uses Solana for this; a hash chain committed in git achieves the same
auditability.

### Two weaknesses in the current design

- **One window for all three resolvers.** `RESOLUTION_WINDOW_CYCLES = 3` at a 4-hour cadence is
  12 hours — fine for news pickup, useless for `indicator_revision`, which needs a year.
  These want per-resolver windows. This is the weakest part of the design.
- **One publisher clears a claim.** Requiring two independent domains would be more honest, but
  would resolve almost nothing at current volume. Revisit once the ledger has depth.

---

## 5. Competitive landscape — verified 2026-08-15

Checked directly against vendor sites. Quotes are from the vendors' own copy. Sources at §5.5.

### 5.1 Dataminr — closest on mechanism

The nearest thing to Signal Fabric's *method* anywhere. Their own description of the pipeline is
almost a description of ours:

> "assembling fragmented signals, enriching data, scoring risks, and routing finished
> intelligence to the appropriate security workflows"

> "Instead of waiting for a confirmed report from a single source, Dataminr event detection looks
> for patterns across many signals, including language, location, source credibility, timing, and
> event similarity."

Scale to be realistic about: **43+ TB of public data daily**, **50+ proprietary LLMs**, **12+ years
of data**.

**Where they are not:** their domain is threat, risk and cyber defence — event detection for
security operations. Not capital flows, not FDI, not procurement, not a region. Signal Fabric is
not competing with Dataminr; it is applying a comparable method to a subject they do not cover.

### 5.2 fDi Markets (Financial Times) — closest on subject

> "the most comprehensive greenfield FDI tracking database on the market… real-time data since 2003"

**The important distinction:** fDi Markets tracks **greenfield project announcements** — a company
announcing a new facility. Signal Fabric tracks **macro flows** (World Bank FDI net inflows),
**procurement**, and **regional press**. Different data layer entirely. A greenfield database will
never tell you a CDB tender opened in Belize.

### 5.3 Regional analogues in other underserved markets — the pattern is proven

The "regional intelligence platform for a market the majors ignore" model is well populated for
Africa and emerging markets generally:

| Product | Positioning |
|---|---|
| **EMIS** | "AI-powered research and intelligence platform focused on emerging markets" — company data, industry reports, news, macro, M&A |
| **Briter** (formerly Briter Bridges) | "Intelligence for emerging markets" — business and investment data |
| **Akinia** | "Trusted Private Market Data for Africa" |
| **ORQAI** | Market-data platforms and APIs for African financial institutions |

**No Caribbean equivalent was found.** Searching for a Caribbean investment-signal platform
returns analyst blogs (Hope Research Group's CARICOM trade analysis), industry-association
commentary, and CARICOM's own site — no scored, routed signal desk. **This remains the gap, and
it is now checked rather than assumed.**

### 5.4 ⚠️ Someone is already running the calibration play — and starts today

**This corrects advice given earlier in the session.** I said "nobody in this space publishes their
hit rate." **That is false.**

**Vorenth** (vorenth.com/track-record) leads with exactly the positioning §6.2 recommends:

> "Vorenth commits probabilities to a public ledger before outcomes are known. Each call is hashed,
> time-stamped on Solana, and scored when the world resolves."

> "Every forecasting platform claims accuracy retroactively. We're committing to specific accuracy
> numbers before the forecasts resolve, in public… Why publish targets we might miss? Because
> forecasters who won't pre-commit to numbers shouldn't be trusted with other people's decisions."

Their public commitment schedule:

| Milestone | Gate |
|---|---|
| Day 30 | N ≥ 20 |
| Day 60 | N ≥ 80 · Brier ≤ 0.22 |
| Day 90 | N ≥ 150 · Brier ≤ 0.20 |
| End 2026 | N ≥ 200 · Brier ≤ 0.18 |

**Three things follow, and they matter more than anything else in this document:**

1. **They are at day zero — cutoff `2026-08-15`, RESOLVED: 0, 65 active forecasts.**
   Signal Fabric is at 16 open claims, same day. **Nobody has a track record yet. The race is
   even, and it starts now.** Every cycle Signal Fabric runs without the ledger recording is a
   cycle of compounding forfeited.

2. **Their metric set is more rigorous than ours.** They report Brier score, log-loss, calibration
   error, sharpness, bootstrap 95% CI, and a domain × horizon cohort matrix. §4 currently reports a
   confirmation rate per score band — cruder. Brier is the correct metric for probabilistic calls
   and should be adopted; see §6.2.

3. **Pre-commitment beats post-hoc reporting.** Publishing targets you might miss, before
   resolution, is a far stronger trust signal than a rate published after the fact. It is also
   free to copy — and Signal Fabric can do it this week.

They are a general forecasting platform, not Caribbean and not FDI, so they are not a direct
competitor. But they are proof the positioning works, executed by someone who has thought about
it harder than we have.

### 5.5 Sources

- Dataminr — https://www.dataminr.com/ai-platform/ · https://www.dataminr.com/products/cyber-defense/threat-intelligence/ · https://github.com/Dataminr-API
- fDi Markets — https://www.fdimarkets.com · https://www.ftlocations.com/products-and-services/fdi-markets
- Vorenth — https://www.vorenth.com/track-record
- EMIS — https://isimarkets.com/emis/ · Briter — https://www.briter.co · Akinia — https://app-akinia.com · ORQAI — https://www.orqai.io/solutions/market-data-intelligence
- Hope Research Group, CARICOM trade analysis — https://www.hoperesearchgroup.com/blog/caricom-trade-data-analysis
- CDB funds feasibility study on CARICOM regional stock exchange, Jamaica Gleaner, 2026-08-09 — https://jamaica-gleaner.com/article/business/20260809/cdb-funds-feasibility-study-caricom-regional-stock-exchange

*Live lead spotted while researching:* the CDB has granted US$100,000 to study a **single regional
CARICOM stock exchange**. That is directly upstream of Signal Fabric's market-watch layer and worth
tracking as a product signal, not just a news item.

---

## 6. Moat assessment, and where to find another angle

**Blunt version: the algorithm is not a moat.** Post-fix it is correct, but it is ~40 lines of
weighted constants. A competent engineer reading this document reimplements it in a week.

Three things are actually defensible, in ascending order:

### 6.1 The calibration ledger — value accrues, cannot be cloned
The mechanism is copyable; the **history is not**. A competitor launching tomorrow has an empty
ledger and cannot say "we have been right 61% of the time" for eighteen months. This is the only
asset here that compounds. Protect it: never reset it, version the schema, back it up.

### 6.2 The regional source graph — field knowledge
`data/market_watch/latest.json` already encodes something valuable: **which sources actually
publish.** The JSE returns HTTP 200 and no dated close. Cayman the same. Four of six exchanges
give a dated observation.

That knowledge — which of 23 countries' registries and tender portals publish, in what format,
on what cadence, and where they silently fail — is field-earned and not in any repo. The site
now surfaces it (dashed chips = tracked but silent). **Deepen this deliberately.** It is the most
under-exploited asset in the codebase.

### 6.3 Angles I did not pursue — where Hermes might find the unique thing

1. **Outcome resolution against procurement.** Tenders have closing dates and award notices.
   "We flagged this tender, it was awarded to X" is a *far* stronger outcome claim than news
   pickup. `data/tenders/latest.json` exists. **This is the highest-value unexplored thread.**

2. **Publish the calibration record as the product — ✅ DONE, now keep the promise.** All three
   upgrades are implemented (§4): Brier against a naive baseline, public pre-commitment rendered
   on the homepage, hash-chained ledger. **The remaining work is not code — it is running the
   pipeline every cycle so claims accumulate and resolve.** A commitment page showing `0 resolved`
   in ninety days is worse than never having published one.

3. **Source-silence as a signal.** When a tender portal goes quiet for three cycles, that *is*
   information about a market. Currently modelled as absence of data. It could be an output.

4. **The negative-move gap.** `moved down 640%` currently scores identically to `moved up 640%`
   (inherited, not introduced). For an *opportunity* product, a collapse ranking as a top
   opportunity is arguably wrong — but "capital flight from X" is a genuinely valuable signal
   that nobody publishes for this region. **Decide deliberately: suppress it, or make it a
   product.** Do not leave it ambiguous.

5. **Agent-readable distribution.** `llms.txt` and `mcp_adapter/` exist. If the calibration
   figure is exposed through MCP, Signal Fabric becomes the Caribbean data source an agent can
   *reason about the reliability of* — which is a different product from a feed.

6. **Signal decay as an editorial product.** `_transfer_fdi_magnitudes` and the freshness
   machinery already track how long a fact has been unchanged. "This has been true and
   unconfirmed for 4 cycles" is a story the region's press does not tell.

---

## 7. Contracts under test — do not break these

`tests/test_signal_scoring.py` (19) and `tests/test_calibration.py` (19):

- Raw scores are **not** clamped before ranking; `display_score()` clamps for display only
- Magnitude is read from **every** phrasing the pipeline emits
- Magnitude separates otherwise-identical signals, and outranks persona count in cluster order
- Feedback boosts are **symmetric**
- Lead follows magnitude, **not input order**; an extra weak signal never costs a country the lead
- Regional context never counts as corroboration, and never triggers the three-source bonus
- Signals without the corroborating/context split keep their **previous** weighting
- A source cited on a signal cannot later corroborate it
- No confirmation rate is published below `MIN_SAMPLE`
- A faded claim counts **against** the band that made it

The scoring tests were checked to **fail against the pre-fix code** — they are regression tests,
not tautologies. One early version passed both ways; its fixture was rebuilt to mirror the real
cycle's shape. Apply the same standard to anything added.

---

## 8. Known-open, lower priority

- `snap.bars` is near-identical across all five markets — possibly placeholder data upstream in
  the poller. Only the rendering was changed, not the source.
- The suite mutates published artefacts (§1).
- `config/market_sources.json` defines only `markets`; the registry is now *derived* from live
  market records rather than a parallel hand-maintained list. If those arrays are ever populated
  they take precedence — keep the two from drifting.


---

## 9. Environment fix applied during this session

WebSearch failed with *"issue with the selected model (gemma-4-12B-it-Q4_K_M)"*.

**Root cause:** `~/.claude/settings.json` set `ANTHROPIC_MODEL` plus the Haiku/Sonnet/Opus
defaults to `gemma-4-12B-it-Q4_K_M`, with `ANTHROPIC_BASE_URL = http://127.0.0.1:1337`.
Nothing is listening on 1337. The desktop app overrides `ANTHROPIC_BASE_URL` back to
`api.anthropic.com` for an OAuth session, **but the model overrides leaked through** — so any
component resolving a model by name asked the real API for a local GGUF build. The main
conversation was unaffected because the host pins its model explicitly.

**Removed** from `~/.claude/settings.json` (backup: `~/.claude/settings.json.bak-20260815-gemma`):
`ANTHROPIC_MODEL`, `ANTHROPIC_DEFAULT_{HAIKU,SONNET,OPUS}_MODEL`, `ANTHROPIC_BASE_URL`,
`ANTHROPIC_AUTH_TOKEN`, and the top-level `model` key. Hooks, MCP servers, plugins, permissions
and statusLine untouched.

**Deliberately left alone:**
- `.zshrc:150` — `ANTHROPIC_BASE_URL=http://127.0.0.1:8787` (Headroom proxy). **Port 8787 is
  open and working.** This is a live, intentional setup.
- `.zshrc:85-95` — `clc` / `claude-local` / `*-cloud` aliases pointing at port 4001. Currently
  closed, but opt-in so they only affect sessions that invoke them.

**Config drift worth cleaning up:** three different local endpoints were configured across these
files — 1337 (settings.json, dead), 4001 (aliases, dead), 8787 (Headroom, live). Only 8787 is
real. If you want a local-model profile back, scope it to a project `.claude/settings.json` or a
shell alias rather than global settings, so it cannot leak into cloud sessions.

**Takes effect on restart** — env vars are read at process start, so the current session still
carries the old values.
