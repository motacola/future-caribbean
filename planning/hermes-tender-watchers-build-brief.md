# Hermes Build Brief — 3A: Tender Watchers (Jamaica + Guyana)

Strategy: `PLAN_ENGINE_2026-06-10.md` Phase 3A. Implementation only.
Goal: real, dated procurement notices from national portals, so the
validation packs stop saying "no live procurement notice matched."

## Read First

- `watchers/tier2_scraper.py` — the house pattern for scraping watchers
  (stdlib urllib, defensive parsing, snapshot caching, latest.json output)
- `packagers/validation_pack_generator.py` — `procurement_matches_for()`
  is the consumer you are feeding
- `run_pipeline.sh` — where watchers are wired
- `tests/test_validation_pack.py` — fixture-based test conventions

## Build

### 1. Framework: `watchers/tenders/__init__.py` + `watchers/tenders/base.py`
- `TenderAdapter` base: `fetch() -> list[dict]`, with shared helpers for
  HTTP GET (stdlib urllib, 15s timeout, browser User-Agent), HTML snapshot
  caching to `data/tenders/raw/<source>-<date>.html`, and defensive
  extraction (any parse failure → log warning, return []).
- Normalised tender record schema (exact keys):
  `{"id", "title", "country", "source", "url", "published", "closing_date",
    "category", "fetched_at"}` — dates ISO-8601 strings or null, never guess.

### 2. Adapters (inspect the live pages and adapt your parsers)
- `watchers/tenders/jamaica_gojep.py` — Jamaica's e-procurement portal
  (www.gojep.gov.jm). Find the public tender-notices listing. If the
  listing requires a session/JS and cannot be fetched with plain urllib,
  document that in the result file and fall back to any public RSS/print
  view it offers; if nothing is reachable, the adapter returns [] with a
  clear log line — do NOT fake records.
- `watchers/tenders/guyana_ppc.py` — Guyana Public Procurement Commission
  (ppc.gov.gy) and/or the National Procurement & Tender Administration
  Board public notices. Same rules.
- Honesty rule: only records actually parsed from the live page. Empty is
  an acceptable result; fabricated is not.

### 3. Runner: `watchers/tenders_poller.py`
- Runs all adapters, merges, dedupes by (source, id|url), writes
  `data/tenders/latest.json`:
  `{"fetched_at", "source": "tenders", "total": n, "items": [...]}`.
- Wire into `run_pipeline.sh` after the Tier 2 step:
  `run_step "Tenders (GOJEP + PPC)" "python3 \"$ROOT/watchers/tenders_poller.py\"" "tenders"`

### 4. Validation pack integration
In `packagers/validation_pack_generator.py`:
- Load `data/tenders/latest.json` in `main()` and pass into `build_pack`.
- In `procurement_matches_for()`: country-matched tender records rank FIRST
  (above tier2 procurement), each carrying
  `{"title", "source", "url", "match": "country", "closing_date"}`.
- In `recommend()`: a country-matched tender with a future closing_date
  counts as one evidence category (it already will via procurement — just
  ensure tenders flow through).
- `unresolved_questions_for()`: when a dated tender exists, replace the
  "No live country-specific procurement notice" question with
  "Tender closes <date> — confirm eligibility and bid requirements early."

### 5. Tests: `tests/test_tenders.py` (fixtures only, NO network)
- Save one small representative HTML fixture per adapter under
  `tests/fixtures/` (trimmed real markup from your live inspection).
- Test each adapter's parse function against its fixture → ≥1 record with
  required keys and ISO dates.
- Test the poller merge/dedupe with two overlapping adapter outputs.
- Test pack integration: a synthetic tender for Guyana appears first in
  procurement_matches and flips the unresolved question.
- All existing 38 tests stay green.

## Constraints

- stdlib only. No new dependencies.
- No `git commit`, no `run_pipeline.sh`, no `server.py __main__`.
- You MAY run `python3 watchers/tenders_poller.py` directly to test live
  fetching (it only writes under `data/tenders/`).
- Do not modify the dashboard, templates, humanizer, or server.
- Do not weaken the no-fabrication rule anywhere.

## Validation

```bash
python3 -m py_compile watchers/tenders/*.py watchers/tenders_poller.py packagers/validation_pack_generator.py
python3 -m pytest -q                       # 38 existing + new, all green
python3 watchers/tenders_poller.py         # live run; empty result acceptable
python3 packagers/validation_pack_generator.py
```

Final summary to `planning/hermes-tender-watchers-result.md`: changed files,
what each portal actually exposed (reachable? parseable? blocked?), live
record counts, validation output, and risks. If a portal was unreachable,
say so plainly — that is a finding, not a failure.
