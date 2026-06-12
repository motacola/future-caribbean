# Hermes Build Brief — 6A: Track Record ("The desk's receipts")

Claude designed this; implement faithfully — markup, CSS, and copy below
are verbatim. Goal: a public, honest record of what the desk said each
cycle, what responses came back, and how priorities shifted — the trust
surface no comparable product has.

## Read First

- `data/feedback/state.json` — `history[]` entries: dispatch_id,
  signal_kind, country, feedback_status, cycle, cycles_ago; plus
  `boosts{kind:{country:delta}}` (CURRENT cumulative adjustments)
- `outbox/opportunity_dispatches.json` — for lead signal per current cycle
- `packagers/rss_feed.py` — house packager style (humanizer import pattern)
- `dashboard/generate.py` — template-var pattern; `humanize` import
- `api/reasoning.py` — house Vercel function pattern
- `tests/test_tenders.py` — test conventions

## Build

### 1. Packager: `packagers/track_record.py`
Writes `outbox/track_record.json`. Contract (exact keys):

```json
{
  "generated_at": "<iso>",
  "current_boosts": {"<signal_kind>": {"<country>": <int>}},
  "cycles": [
    {
      "cycle_id": "20260611",
      "responses": {"forwarded": 3, "replied": 1, "opened": 2, "ignored": 4, "decision_changed": 0},
      "dispatch_count": 12,
      "countries": ["Guyana", "Belize"],
      "lead": {"country": "Guyana", "title": "<humanized lead title or empty>"}
    }
  ]
}
```

- `cycles`: group `history[]` by `cycle`, newest first, max 8. Counts per
  feedback_status; dispatch_count = entries in that cycle; countries =
  unique, by response volume desc.
- `lead`: only fill for cycles found in `outbox/opportunity_dispatches.json`
  (match `cycle_id`); use the highest-confidence dispatch, title through
  `humanize()`. For older cycles leave `{"country": "", "title": ""}` —
  do NOT invent leads for cycles we no longer have artifacts for.
- `current_boosts`: copy from state verbatim. They are cumulative — the
  page labels them honestly as "current priorities", not per-cycle deltas.
- stdlib + `from humanizer import humanize` only.
- Wire into `run_pipeline.sh` directly after the RSS Feed step:
  `run_step "Track Record" "python3 \"$ROOT/packagers/track_record.py\"" "track_record"`

### 2. API
- `api/track-record.py` — Vercel function serving `outbox/track_record.json`
  (copy the `api/reasoning.py` pattern; read-only).
- `server.py`: route `GET /api/track-record` serving the same file (copy
  the `/feed.xml` route pattern, JSON content type).
- `api_manifest.py`: add tool `track_record` — description "Public record
  of what the desk said each cycle, responses received, and current
  priority adjustments", method GET, path `/api/track-record`,
  `"writes": False`.

### 3. Dashboard section — verbatim
In `dashboard/generate.py`, read `outbox/track_record.json` and build
`receipts_html`: one row per cycle (max 6). Row template (f-string,
escape with `j()` everywhere):

```html
<div class="receipt-row">
  <div class="receipt-when"><strong>{cycle date as e.g. "11 Jun 2026"}</strong><span>Cycle {cycle_id}</span></div>
  <div class="receipt-said">
    <span class="fp-kicker">{lead country or "Region"}</span>
    <strong>{lead title or f"{dispatch_count} briefings routed"}</strong>
    <p>{dispatch_count} briefings · {len(countries)} markets: {", ".join(countries[:4])}</p>
  </div>
  <div class="receipt-resp">{pills}</div>
</div>
```

`pills`: for each non-zero status except `ignored`, in order
forwarded/replied/decision_changed/opened:
`<span class="r-pill">{label} {n}</span>` with labels Forwarded/Replied/
Changed a decision/Opened. If all zero: `<span class="r-pill r-quiet">No responses yet</span>`.

Below the rows, a boosts line built from `current_boosts` (top 5 by
absolute value): `<span class="r-boost {up|down}">{country} {▲|▼}{+n|n}</span>`.

Template section — insert in `dashboard/template.html` AFTER the
"More from the wire" section's closing `</div>` and BEFORE the
"Who it's for" section:

```html
<div class="sec" id="receipts">
  <div class="sec-label">The desk's receipts</div>
  <div class="st">What the desk said — and what happened next</div>
  <div class="ss">Every briefing is recorded, and reader responses change what the desk prioritises. Here is that loop, in public.</div>
  <div class="receipts-table">{{receipts_html}}</div>
  <div class="receipts-boosts"><span class="fp-head">Current priorities, shaped by responses</span>{{boosts_html}}</div>
  <p class="receipts-foot">Machine-readable record: <a href="/api/track-record">/api/track-record</a></p>
</div>
```

CSS — add after the `.art-by` rules:

```css
/* the desk's receipts */
.receipts-table { border-top: 2px solid var(--ink); }
.receipt-row { display: grid; grid-template-columns: 150px minmax(0,1fr) 240px; gap: 18px; padding: 14px 0; border-bottom: 1px solid var(--border); align-items: start; }
.receipt-when strong { display: block; font-family: var(--serif); font-size: 16px; }
.receipt-when span { font: 400 9px var(--mono); color: var(--muted); text-transform: uppercase; letter-spacing: .8px; }
.receipt-said strong { display: block; font-family: var(--serif); font-size: 16px; line-height: 1.25; margin: 2px 0; }
.receipt-said p { font-size: 11.5px; color: var(--muted); }
.receipt-resp { display: flex; flex-wrap: wrap; gap: 6px; justify-content: flex-end; }
.r-pill { font: 600 10px var(--mono); color: var(--teal); background: rgba(13,118,110,.08); border-radius: 3px; padding: 4px 8px; white-space: nowrap; }
.r-pill.r-quiet { color: var(--muted); background: var(--card-alt); }
.receipts-boosts { padding: 12px 0; border-bottom: 1px solid var(--border); display: flex; gap: 10px; align-items: center; flex-wrap: wrap; }
.r-boost { font: 600 11px var(--mono); padding: 3px 8px; border-radius: 3px; }
.r-boost.up { color: var(--teal); background: rgba(13,118,110,.08); }
.r-boost.down { color: var(--coral); background: rgba(201,76,76,.08); }
.receipts-foot { font-size: 11px; color: var(--muted); margin-top: 10px; }
```

Mobile (inside the existing `@media(max-width:768px)` block):

```css
.receipt-row { grid-template-columns: 1fr; gap: 6px; }
.receipt-resp { justify-content: flex-start; }
```

Also add to the desk nav, before the For Agents item:
`<a href="#receipts" class="dn-item">Receipts</a>`

### 4. Tests — `tests/test_track_record.py`
- Packager grouping: synthetic history with 2 cycles → correct counts,
  newest first, ignored counted but never rendered as a pill.
- Contract keys present; no lead invented for a cycle absent from the
  dispatches file.
- After running the real packager: `outbox/track_record.json` valid and
  generated dashboard contains `id="receipts"` and `receipt-row`.
- All existing 42 tests stay green.

## Constraints
- No git commit, no run_pipeline.sh, no `server.py __main__`.
- Run `python3 packagers/track_record.py` then
  `python3 dashboard/generate.py --no-open` to verify rendering.
- Touch only: the new packager, new api function, new test file,
  `server.py` (route), `api_manifest.py` (entry), `run_pipeline.sh`
  (step), `dashboard/generate.py` (receipts_html/boosts_html),
  `dashboard/template.html` (section + CSS + nav + mobile).

## Validation
```bash
python3 packagers/track_record.py
python3 dashboard/generate.py --no-open
python3 -m pytest -q
python3 -m py_compile api/track-record.py server.py
```
Result file: `planning/hermes-track-record-result.md` — changed files,
validation output, anything skipped.
