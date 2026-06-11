# Hermes Build Brief — The Wire Service Front Page

Claude designed this; your job is faithful implementation. Where this brief
gives exact markup, classes, copy, or CSS values, use them verbatim — do not
improvise design, wording, or structure. Direction: the dashboard becomes a
newspaper front page for the Caribbean (pattern reference: theagenttimes.com,
but in our existing brand voice and palette).

## Read First

- `dashboard/template.html` — current structure: masthead → livewire →
  map-hero → theater → ask-desk → proof-band → decision-workspace →
  coordination-strip → briefing → radar (sig-list) → audiences → outputs → footer
- `dashboard/generate.py` — `sec_signals` loop (radar rows), `clean_signal_title`,
  `humanize`, the `V` dict
- `humanizer.py` — use `humanize()` for any artifact text you surface
- `tests/test_week2d.py` — test conventions

## Build

### 1. Desk navigation strip (new, directly under the Live Wire)

Markup, verbatim:

```html
<nav class="desknav" aria-label="Desks">
  <div class="desknav-inner">
    <a href="#leaflet-map" class="dn-item">Front Page</a>
    <a href="#decision-workspace" class="dn-item dn-invest">Investment Desk</a>
    <a href="#theater" class="dn-item">The Engine</a>
    <a href="#ask-desk" class="dn-item">Ask the Desk</a>
    <a href="#more-wire" class="dn-item">More from the Wire</a>
    <a href="#for-agents" class="dn-item dn-agents">For Agents</a>
  </div>
</nav>
```

CSS (place after the livewire rules):

```css
.desknav { background: var(--bg); border-bottom: 3px double var(--border-dark); position: relative; z-index: 5; }
.desknav-inner { max-width: 1160px; margin: 0 auto; padding: 0 24px; display: flex; gap: 4px; overflow-x: auto; scrollbar-width: none; }
.desknav-inner::-webkit-scrollbar { display: none; }
.dn-item { padding: 11px 14px; font: 600 11px var(--sans); letter-spacing: 1.1px; text-transform: uppercase; color: var(--sub); white-space: nowrap; text-decoration: none; border-bottom: 2px solid transparent; margin-bottom: -1px; }
.dn-item:hover { color: var(--ink); text-decoration: none; border-bottom-color: var(--gold); }
.dn-agents { color: var(--teal); }
```

### 2. Lead-story dateline on the decision workspace

Inside `#decision-workspace`, immediately BEFORE the existing
`<div class="decision-kicker">`, insert:

```html
<div class="dateline"><span class="dl-desk">Investment Desk</span><span class="dl-by">By the Desk</span><span class="dl-when">Cycle {{cycle_id}} · {{now_str}}</span></div>
```

CSS:

```css
.dateline { display: flex; gap: 14px; align-items: baseline; flex-wrap: wrap; padding-bottom: 10px; margin-bottom: 14px; border-bottom: 3px double var(--border-dark); }
.dl-desk { font: 700 10px var(--mono); letter-spacing: 1.4px; text-transform: uppercase; color: var(--sky); }
.dl-by { font: italic 600 13px var(--serif); color: var(--ink); }
.dl-when { font: 400 10px var(--mono); color: var(--muted); margin-left: auto; }
```

### 3. "More from the wire" — radar rows become article cards

In `dashboard/generate.py`, replace the `sec_signals` loop body so each entry
renders as an article card instead of a bare row. Keep the SAME outer ids and
the expandable validation-pack behaviour (`sig-row`, `data-verdict`,
`sig-expand`, `sig-validation` machinery must keep working — wrap, don't
remove). Add to each `sig-main` block, above the existing `<strong>`:

```python
kind = c.get("signal_kind", "") or ""
desk = "Investment Desk" if "invest" in kind else "Climate Desk" if ("climate" in kind or "weather" in kind) else "Procurement Desk" if ("procure" in kind or "pipeline" in kind) else "Regional Desk"
desk_color = {"Investment Desk": "#2676A8", "Climate Desk": "#0D766E", "Procurement Desk": "#B57A22"}.get(desk, "#7F8C83")
dek = humanize((c.get("decision", "") or ""))[:110]
```

and render: a kicker line `<span class="art-kicker" style="color:{desk_color}">{desk}</span>`,
the existing title as serif headline (add class `art-head` to the `<strong>`),
then `<p class="art-dek">{dek}</p>`, then a byline `<span class="art-by">By the Desk · Cycle {{cycle_id}}</span>`
(use the cycle variable available in generate.py, not the literal template token).

Also change the section label in `template.html` from
`<div class="sec-label">Also on our radar</div>` to
`<div class="sec-label" id="more-wire">More from the wire</div>`.

CSS:

```css
.art-kicker { display: block; font: 700 9px var(--mono); letter-spacing: 1.3px; text-transform: uppercase; margin-bottom: 3px; }
.art-head { font-family: var(--serif); font-size: 17px; font-weight: 700; line-height: 1.2; }
.art-dek { font-size: 12.5px; color: var(--sub); margin-top: 3px; line-height: 1.5; }
.art-by { display: block; font: italic 500 11px var(--serif); color: var(--muted); margin-top: 5px; }
```

### 4. "For the agents reading this" block (new section, before the footer)

Markup, verbatim (placeholders `{{...}}` only where shown):

```html
<div class="sec" id="for-agents">
  <div class="agents-block">
    <div class="agents-head">
      <span class="agents-eyebrow">// machine-readable edition</span>
      <h2>Reading this as an AI agent? This page is yours too.</h2>
      <p>Everything the desk publishes is available as structured data — same facts, no scraping required.</p>
    </div>
    <div class="agents-grid">
      <div class="agents-card"><h4>One question, one answer</h4><pre>curl -X POST https://signal-fabric.vercel.app/api/ask \
  -d '{"question":"explain lead"}'</pre><span>Deterministic, cited — no hallucinations</span></div>
      <div class="agents-card"><h4>Every tool, self-described</h4><pre>GET /api/tools.json</pre><span>Ingest the manifest, configure yourself</span></div>
      <div class="agents-card"><h4>Follow the wire</h4><pre>GET /feed.xml</pre><span>RSS of every signal, every cycle</span></div>
    </div>
    <div class="agents-foot">Full connection guide for Claude (MCP), Hermes, OpenClaw, and anything HTTP-capable: <a href="/agents.md">agents.md</a> · <a href="/llms.txt">llms.txt</a></div>
  </div>
</div>
```

CSS:

```css
.agents-block { background: var(--ink); color: var(--bg); border-radius: 10px; padding: 34px 30px 24px; box-shadow: 0 18px 60px rgba(24,37,31,.16); }
.agents-eyebrow { font: 700 10px var(--mono); letter-spacing: 1.6px; text-transform: uppercase; color: var(--lime); }
.agents-head h2 { font-family: var(--serif); font-size: clamp(24px,3.4vw,36px); line-height: 1.1; margin: 10px 0 8px; }
.agents-head p { color: rgba(244,235,221,.66); font-size: 14px; max-width: 560px; margin-bottom: 22px; }
.agents-grid { display: grid; grid-template-columns: repeat(auto-fit, minmax(230px, 1fr)); gap: 12px; }
.agents-card { border: 1px solid rgba(244,235,221,.16); border-radius: 8px; padding: 16px; }
.agents-card h4 { font-family: var(--serif); font-size: 16px; margin-bottom: 10px; }
.agents-card pre { font: 11px var(--mono); color: var(--lime); white-space: pre-wrap; overflow-wrap: anywhere; background: rgba(244,235,221,.06); border-radius: 5px; padding: 10px 12px; margin-bottom: 8px; }
.agents-card span { font-size: 11px; color: rgba(244,235,221,.5); }
.agents-foot { margin-top: 18px; padding-top: 14px; border-top: 1px solid rgba(244,235,221,.12); font-size: 12px; color: rgba(244,235,221,.6); }
.agents-foot a { color: var(--lime); }
```

### 5. Mobile rules

Add inside the existing `@media(max-width:768px)` block:

```css
.desknav-inner { padding: 0 12px; }
.dateline .dl-when { margin-left: 0; width: 100%; }
.agents-block { border-radius: 0; }
```

### 6. Tests — `tests/test_frontpage.py`

- Generated `dashboard.html` contains: `desknav`, `dateline`, `For the agents
  reading this` block id `for-agents`, `art-kicker`, `More from the wire`.
- No unresolved `{{` template placeholders outside the two known htm-object
  lines (match against `{{[a-z_]+}}` pattern specifically).
- Existing 33 tests stay green.

## Constraints

- Do NOT run `git commit`, `run_pipeline.sh`, or `server.py` `__main__`.
- Do NOT modify: the Live Wire, the map, the theater, the ask-desk React
  island, the validation pack internals, `configurator.html`.
- Do NOT change any copy beyond what this brief specifies.
- Regenerate via `python3 dashboard/generate.py --no-open`.
- All existing tests must pass: `python3 -m pytest -q`.

## Validation

```bash
python3 dashboard/generate.py --no-open
python3 -m pytest -q
grep -c "desknav\|for-agents\|art-kicker" dashboard.html   # all > 0
```

Final summary to `planning/hermes-newspaper-front-result.md`: changed files,
validation output, anything skipped and why. Claude will do the visual
review, error harness, mobile check, commit, and deploy.
