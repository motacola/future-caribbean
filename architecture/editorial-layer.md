# Editorial Layer — Abeng

## Architecture

The editorial layer lives in `packagers/editorial_enrichment.py` and is called by
`packagers/build_channel_outputs.py`. It transforms raw composite signals (25+
structured data points from 6 watchers) into channel-ready intelligence with
editorial judgment.

The pipeline order is:

```
watchers/ → mergers/cross_source_merger.py → packagers/editorial_enrichment.py → packagers/build_channel_outputs.py
```

The merger generates structured signals. The editorial enrichment adds the
judgment. The packager formats for each audience.

## Components

### 1. Lead Story Selection (`select_lead`)

Groups all signals by country, scores each cluster by:
- Weighted signal score (enhanced investment weighted 1.5×, tourism 0.6×)
- Cross-signal bonus (+5 per additional signal, max +20)
- Cross-source bonus (+10 per unique source, max +30)

The country with the highest cluster score becomes the editorial lead.
Regional clusters (CARICOM, Atlantic) cannot lead unless no country-specific
signals exist.

### 2. Score Bands (`compute_signal_score` → `resolve_band`)

Each signal gets a 0–100 score with a structural base (kind, sources, evidence
count, priority) plus a **magnitude boost** for FDI/inflation/unemployment
signals that carry a percentage in their evidence text:

| Change | Boost |
|--------|-------|
| ≥500%  | +20   |
| ≥200%  | +14   |
| ≥75%   | +8    |
| ≥30%   | +4    |

The score maps to a decision band:

| Band        | Range | Telegram label     |
|-------------|-------|--------------------|
| immediate   | 90+   | 🔴 Immediate       |
| validation  | 70–89 | 🟡 Validation       |
| monitor     | 50–69 | 🟢 Monitor          |
| context     | <50   | ⚪ Context           |

### 3. Differentiated Decision Language (`get_decision`)

Templates are keyed by signal kind *and* score band, not just kind alone.
Guyana at 860% with 3 sources scores in "immediate" band and gets:

> "Immediate investigation. Guyana has multi-source investment validation
> (3 signals converging). Priority: assess market entry options, identify
> existing operators."

St Vincent at 88% with 2 sources scores in "validation" band and gets:

> "Validation priority. St Vincent and the Grenadines FDI movement
> (88.2% change) signals opportunity. Cross-reference with sector data."

### 4. FDI Magnitude Transfer (`_transfer_fdi_magnitudes`)

Enhanced investment signals (3+ sources) don't carry the raw FDI percentage
in their evidence — the merger only says "WB FDI surge detected: Belize."
This function cross-references matching regular investment signals, extracts
the percentage, and re-scores the enhanced signal so the magnitude boost
applies. Ensures the Regional Investment Overview table can sort by magnitude.

### 5. Temporal Freshness Tracking

`data/editorial/state.json` persists signal IDs, scores, and summaries
between pipeline runs. Each cycle each signal is classified as:

| Status      | Meaning |
|-------------|---------|
| 🆕 new     | Signal ID not seen in previous cycle |
| — sustained | Same ID, same score (±5 pts) |
| ⬆️ intensified | Same ID, score increased ≥5 pts |
| ⬇️ weakened | Same ID, score decreased ≥5 pts |
| 🔄 updated  | Same ID, summary text changed |

### 6. Cross-Signal Context

The Regional Investment Overview table cross-references enhanced investment
signals with vulnerability signals for the same country. SVG shows both
"FDI +88%" and "⚠️ also has vulnerability: 18% unemployment." This is the
first cross-signal synthesis — more should be added.

## Channel Outputs

| Channel | Function | What Changed |
|---------|----------|--------------|
| Telegram | `write_telegram_digest` | Lead story → 5 diverse kinds; freshness badges; score-band labels |
| Investor | `write_investor_brief` | Regional Investment Overview table (magnitude-sorted); cross-conflict flags; pipeline titles |
| Judge | `write_judge_brief` | Lead story section → Supporting Decision Signals with full metadata |
| Diaspora | `write_diaspora_post` | Magnitude-sorted entries with `+860%` format; pipeline summary |

## Scoring Details

The `compute_signal_score` function weights:

- **Kind base**: 54 (enhanced investment) down to 30 (tourism)
- **Priority**: +18 (high), +10 (medium), +3 (low)
- **Evidence count**: up to +12 (capped at 3+ items)
- **Sources**: +10 per major source (WB, IDB, CDB, CARICOM), +8 per NOAA/NDBC
- **3+ source bonus**: +8
- **Magnitude boost**: +4 to +20 based on FDI/inflation/unemployment %

Capped at 100. Enhanced signals with 3 major sources typically hit cap before
magnitude boost is applied — this is by design (multi-source validation
guarantees top tier).

## Next Improvements (in priority order)

### 1. Signal Velocity Column

The investor brief table shows "100/100" for both Guyana (860% FDI) and
Suriname (29% FDI). The score is semantically correct (both have multi-source
validation) but doesn't communicate *impact*. Add a Signal Velocity column
derived from the magnitude boost that shows "🟢 exceptional" / "🟡 major" /
"🔵 notable" / "⚪ steady" independent of structural score.

### 2. Calendar/Context Layer

A rules file (`config/editorial_calendar.yaml`) that injects seasonal and
event context into the narrative intro:

- Hurricane season (Jun–Nov): amplify storm-related signals, note preparedness
- Tourism high season (Dec–Apr, Jul–Aug): add "tourism impact" context
- IMF/EU/World Bank cycle: note when new disbursements or reviews are due
- Election calendar: flag political risk in countries with upcoming elections

This is the "why this matters *this week*" gap — the narrative intro currently
describes *what happened* but not *why it matters right now*.

### 3. Cross-Cluster Synthesis

Currently the lead story is always a single country. The next level is
identifying *regional patterns* that span multiple countries:

- "Regional FDI momentum: 8 of 10 tracked countries show positive FDI
  signals this cycle — the broadest wave since tracking began."
- "Trade corridor heating: Belize procurement + Barbados FDI + SVG
  investment = Eastern Caribbean supply chain zone showing activity."

This would require a second pass over the enriched signals to detect
emergent regional patterns, then compose narrative language for the most
prominent ones.

### 4. Signal History

The editorial state only tracks previous cycle. Adding a lightweight rolling
window (last 5 cycles) would enable:
- Trend labels: "↑ 3rd consecutive cycle" / "↘ first decline in 4 cycles"
- Baseline comparisons: "Guyana 860% is the highest single-cycle FDI print
  in 6 months"
- Volatility detection: rapid changes in vulnerability indicators

## Files

| File | Role |
|------|------|
| `packagers/editorial_enrichment.py` | Core editorial engine (~650 lines) |
| `packagers/build_channel_outputs.py` | Channel output generators (~500 lines) |
| `data/editorial/state.json` | Temporal state (auto-created) |
| `architecture/editorial-layer.md` | This document |