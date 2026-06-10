# Claude Handover — Future Caribbean

Date: 2026-06-10

## Project Location

```text
/Users/christopherbelgrave/clawd/projects/future-caribbean
```

## Start Here

The product is **Caribbean Opportunity Dispatch**, powered by **Caribbean Signal OS**.

It watches fragmented Caribbean public data, detects cross-source signals, routes each signal to a relevant decision-maker, packages channel-ready dispatches, and learns from recipient feedback.

The current strategic concern is that the project still risks feeling like an intelligent newsletter. The latest pass improved the product surface by making the existing operational data visible, but the next major value jump requires automatically completing more of the diligence work.

Read these first:

1. `README.md`
2. `analysis/website-fit-audit.md`
3. `analysis/page-by-page-strategy-read.md`
4. `dashboard/template.html`
5. `dashboard/generate.py`
6. `outbox/opportunity_dispatches.json`
7. `PHASE_3A_HANDOFF.md` for backend workflow history

## Latest Product Pass

The homepage was reframed from a passive briefing into a **decision workspace**.

Changed files:

- `dashboard/template.html`
- `dashboard/generate.py`
- `dashboard.html` generated from the template

What changed:

- The hero now promises a clear user outcome: know which Caribbean opportunity to advance next.
- The first useful section is now the lead decision workspace.
- The workspace exposes existing dispatch data:
  - dispatch ID
  - recommended action
  - action window
  - named owner/persona
  - evidence grade
  - delivery state
  - feedback state
  - persona-specific routes
- Added a persistent three-step diligence checklist using `localStorage`.
- Moved the system/engine explanation below the decision experience.
- Fixed mobile horizontal overflow, including long risk tags.

## Verification Completed

Passed:

```bash
python3 dashboard/generate.py --no-open
python3 -m pytest -q
python3 -m py_compile dashboard/generate.py server.py
git diff --check -- dashboard/generate.py dashboard/template.html dashboard.html
```

Results:

- `4 passed`
- Desktop render reviewed in headless Chrome
- Mobile render reviewed at 390px
- Confirmed mobile document width equals viewport width
- Confirmed diligence checklist interaction works

## Important Runtime Note

Starting `server.py` automatically starts a pipeline cycle after three seconds:

```python
threading.Thread(target=pipeline_loop, daemon=True).start()
```

During the latest rendered review, this refreshed generated/runtime artifacts in `outbox/` and `data/`. The repository already had many modified generated files before this pass. Do not blindly revert them.

For visual-only review without running the pipeline, use:

```bash
python3 -m http.server 8090
```

Then open:

```text
http://127.0.0.1:8090/dashboard.html
```

## Product Assessment

### What now works better

- The product leads with a decision instead of architecture.
- Existing backend dispatch value is visible to users.
- A judge can see who should act, by when, and what response occurred.
- The interface feels more like an operating desk than a report.

### Biggest remaining value gap

The system still tells users what to investigate instead of doing enough of the investigation for them.

For example, the Guyana signal currently asks the user to:

1. Identify the sector behind the FDI movement.
2. Find credible local operators.
3. Cross-check procurement and project pipelines.

Those are exactly the tasks the next product layer should automate.

## Recommended Next Build

Build an automatically generated **Opportunity Validation Pack** for each lead signal.

Suggested artifact:

```text
outbox/validation_packs/<signal_id>.json
outbox/validation_packs/<signal_id>.md
```

Minimum useful fields:

- `signal_id`
- `country`
- `sector_hypotheses`
- `supporting_projects`
- `procurement_matches`
- `credible_local_operators`
- `relevant_institutions`
- `source_links`
- `unresolved_questions`
- `recommended_intro_targets`
- `advance_or_reject_recommendation`
- `recommendation_reason`
- `last_validated_at`

Then display the lead validation pack inside the dashboard decision workspace.

The desired user outcome:

> Move from “Guyana deserves investigation” to “Here are the two sectors, three local operators, and one active project worth validating this week.”

## Scope Guidance

Prioritise:

- Product usefulness over more architecture explanation
- One primary wedge: diaspora investors and regional founder/operators
- Evidence-backed actions over generic narrative
- Concrete opportunity/project/operator matching
- Clear advance, hold, or reject decisions

Avoid:

- Adding more generic data sources without connecting them to decisions
- Expanding the persona list
- More dashboard metrics
- More channel-copy examples
- Claims about moving capital without a visible capital-adjacent workflow

## Git State

The repo is dirty and contains pre-existing source, generated, and runtime changes.

Do not revert unrelated changes.

Review these source files carefully before editing:

- `dashboard/generate.py`
- `dashboard/template.html`
- `server.py`
- `watchers/tier2_scraper.py`
- `.flue/`

Generated/runtime surfaces to treat cautiously:

- `dashboard.html`
- `outbox/*`
- `data/feedback/*`
- `data/editorial/state.json`
- `data/ndbc/history.json`
- `data/.cycle_count.json`
- `data/approvals/*`
- `data/history/*`

## Suggested First Commands

```bash
cd /Users/christopherbelgrave/clawd/projects/future-caribbean
git status --short
sed -n '1,260p' CLAUDE_HANDOVER_2026-06-10.md
python3 dashboard/generate.py --no-open
python3 -m pytest -q
```

