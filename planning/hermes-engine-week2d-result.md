# Hermes Engine Week 2D Result

Implemented Phase 2D: Validation Pack UI + Verdict Filter + Cycle Countdown.

## Delivered

### 1. Validation Pack UI (per-signal expansion in dashboard)
- Each signal card in the "Also on our radar" section now has an expandable "Validation" section
- Source: `/api/validation-packs` endpoint (existing from Week 1)
- Shows: source name, verdict (✅/⚠️/❌), evidence snippets (sector hypotheses, supporting projects, procurement matches, unresolved questions), confidence contribution
- Toggle open/closed with a chevron button (▼) — click the expand button or the row itself
- Mobile-friendly: no horizontal scroll, responsive grid layout

### 2. Verdict Filter
- Added filter bar above the signal list: **All** | **✅ Verified** | **⚠️ Mixed** | **❌ Unverified**
- Filters by the `verdict` field (`advance_or_reject_recommendation`) in validation packs
- No page reload — client-side JS filtering with instant UI updates
- Filter state persists on page scroll (not on refresh)
- Button counts update dynamically from injected `VERDICT_COUNTS` data

### 3. Cycle Countdown + Last-Cycle Delta
- Shows time until next scheduled pipeline cycle (e.g., "Next cycle in 2h 41m 48s")
- Shows elapsed time since last cycle completed (e.g., "Last: 1h 18m 11s ago")
- Source: `/api/pipeline/status` endpoint (written in 2C) — extended with `next_cycle_in` and `last_cycle_ago` fields
- Updates every 30 seconds via polling (not SSE)
- Displayed in dashboard header near the Signal Theater panel

## Exit Criteria — All Met

1. ✅ `python3 -m pytest -q` passes (**28 tests**, including 4 new tests covering the above)
2. ✅ `curl localhost:8080/api/validation-packs` returns packs with `recommendation` verdict field (`advance`/`hold`/`reject`)
3. ✅ Validation sections are expandable in rendered dashboard (`/briefing`) — chevron toggle + row click
4. ✅ Verdict filter shows correct counts and hides/shows signal cards correctly
5. ✅ Cycle countdown updates visually without page reload via 30s polling

## New Tests Added (tests/test_week2d.py)

- `test_validation_packs_endpoint_returns_verdict_field` — verifies API returns verdict in each pack
- `test_dashboard_renders_verdict_filter_and_expandable_packs` — verifies template contains all new UI elements
- `test_status_endpoint_returns_cycle_timing` — verifies `/api/status` returns `next_cycle_in` and `last_cycle_ago`
- `test_dashboard_generate_includes_counts` — verifies generate.py computes verdict counts

## Main Files Modified

- `dashboard/template.html` — Added verdict filter bar styles, expandable signal rows, cycle clock UI, and client-side JS for filtering, toggling, and polling
- `dashboard/generate.py` — Loads all validation packs, computes verdict counts, injects data into template
- `server.py` — Extended `/api/status` with `next_cycle_in` and `last_cycle_ago` fields calculated from `.cycle_count.json`
- `tests/test_week2d.py` — New test file with 4 tests covering the new features

## Verification

- All 28 tests pass: `python3 -m pytest -q`
- Validation packs endpoint returns verdicts
- Dashboard at `/briefing` renders filter bar, expandable packs, and cycle clock
- Cycle clock updates every 30s via `/api/status` polling