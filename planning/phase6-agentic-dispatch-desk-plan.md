# Phase 6 Agentic Dispatch Desk Implementation Plan

> **For Hermes:** Use subagent-driven-development skill to implement this plan task-by-task.

**Goal:** Add an “Ask the Dispatch Desk” analyst rail and headless-ready query layer so Caribbean Opportunity Dispatch feels like an interrogable intelligence operator, not only a dashboard/report.

**Architecture:** Keep the current Dispatch Desk as the evidence/report layer. Add a deterministic query engine over `outbox/dispatch_desk.json` and related artifacts, then expose it in the static dashboard as an analyst rail with suggested questions, drilldowns, and copyable answers. Do not wire a generic LLM chatbox yet; design the query engine so a future local LLM/API can sit behind the same interface.

**Tech Stack:** Python stdlib for the headless query engine and tests; generated static HTML/CSS/JS in `dashboard/generate.py`; local JSON artifacts (`dispatch_desk.json`, `opportunity_dispatches.json`, `feedback_review.md`, `regional_thesis.md`, `why_now.md`).

---

## Conversation Snapshot / Rationale

Current state after Phase 5/Dispatch Desk work:

- `outbox/dispatch_desk.md` / `.json` is now the primary Track 08 product surface.
- `dashboard.html` starts with a Dispatch Desk product view and lower operator/audit sections.
- `telegram_brief.md` is a delivery notification, not the product.
- This is a better direction, but the UX still feels too much like a dashboard/report.

Desired shift:

- From “read this dashboard/report”
- To “interrogate an intelligence operator”

Core UX idea:

- Add an embedded “Ask the Dispatch Desk” analyst rail to the page.
- User can ask or click suggested prompts:
  - “Explain the lead signal”
  - “Show investor actions”
  - “What changed this cycle?”
  - “Where is opportunity conflicting with risk?”
  - “Why was SVG downranked?”
  - “Draft a Belize investor note”
  - “Show procurement routes”
- Answers should cite local artifacts and route IDs.
- Initial implementation should be deterministic and local, not a generic LLM chatbot.
- Long-term architecture should be headless: CLI/API/Telegram/web all call the same query engine.

Product language:

- Prefer: “analyst rail”, “Ask the Dispatch Desk”, “drill down”, “explain”, “draft”, “record feedback”
- Avoid: “chatbot”, “daily pulse”, “dashboard-first”, “generic AI assistant”

---

## Non-Goals for This Phase

- Do not add external LLM/API dependency.
- Do not add authentication.
- Do not build a persistent web server yet.
- Do not allow the browser UI to mutate files directly.
- Do not replace the Dispatch Desk; augment it.
- Do not remove generated artifacts — they are the audit/evidence layer.

---

## Acceptance Criteria

By the end of this phase:

1. `python3 agent/query.py explain-lead` returns a deterministic answer from `outbox/dispatch_desk.json`.
2. `python3 agent/query.py ask "why is Guyana first"` maps to the lead explanation.
3. `python3 agent/query.py ask "show investor actions"` returns routes for diaspora investor / investor-facing actions.
4. `python3 agent/query.py ask "what changed this cycle"` returns freshness + feedback-adjusted priority summary.
5. `python3 agent/query.py ask "draft Belize investor note"` returns a copyable short note based only on local dispatch data.
6. `dashboard.html` contains an “Ask the Dispatch Desk” analyst rail with suggested prompts.
7. The analyst rail works offline/static using embedded JSON and deterministic JavaScript.
8. Answers cite artifact names and dispatch IDs where possible.
9. Existing pipeline still passes:
   - `python3 -m py_compile $(git ls-files '*.py') agent/query.py`
   - `bash run_pipeline.sh`
   - `python3 dashboard/generate.py --no-open`
10. Telegram brief remains under 4096 chars.

---

## Task 1: Create the Headless Query Engine Package

**Objective:** Add a small stdlib-only package for deterministic query/drilldown logic.

**Files:**
- Create: `agent/__init__.py`
- Create: `agent/query.py`

**Step 1: Create package directory**

```bash
mkdir -p agent
printf '"""Headless query helpers for Caribbean Opportunity Dispatch."""\n' > agent/__init__.py
```

**Step 2: Implement initial query engine**

Create `agent/query.py` with these functions:

```python
#!/usr/bin/env python3
"""Headless deterministic query layer for Dispatch Desk artifacts.

This is intentionally stdlib-only and non-LLM. It gives the web analyst rail,
CLI, and future API one shared source of truth for explanations and drilldowns.
"""

from __future__ import annotations

import argparse
import json
import re
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parents[1]
DESK_JSON = ROOT / "outbox" / "dispatch_desk.json"


def load_desk(path: Path = DESK_JSON) -> dict[str, Any]:
    if not path.exists():
        raise FileNotFoundError(f"Missing {path}. Run bash run_pipeline.sh first.")
    return json.loads(path.read_text(encoding="utf-8"))


def clean(text: Any) -> str:
    return " ".join(str(text or "").split())


def clip(text: Any, limit: int = 180) -> str:
    value = clean(text)
    if len(value) <= limit:
        return value
    return value[: limit - 1].rsplit(" ", 1)[0].rstrip(".,;:") + "…"


def artifact_citation(*names: str) -> str:
    return "Sources: " + ", ".join(f"`{name}`" for name in names)


def lead_cluster(desk: dict[str, Any]) -> dict[str, Any] | None:
    clusters = desk.get("clusters", []) or []
    return clusters[0] if clusters else None


def explain_lead(desk: dict[str, Any]) -> str:
    cluster = lead_cluster(desk)
    if not cluster:
        return "No decision clusters are available. Run the pipeline first.\n\n" + artifact_citation("outbox/dispatch_desk.json")

    routes = cluster.get("personas", []) or []
    route_lines = []
    for route in routes[:4]:
        route_lines.append(
            f"- {route.get('persona', 'Persona')} via {route.get('channel', 'channel')}: "
            f"{clip(route.get('action', 'Review dispatch.'), 130)} "
            f"[{route.get('dispatch_id', 'no-id')}, feedback={route.get('feedback_status', 'awaiting')}]"
        )

    risks = cluster.get("risk_flags", []) or []
    risk_line = ""
    if risks:
        risk_line = "\nRisk flags: " + "; ".join(str(r) for r in risks[:3])

    return "\n".join([
        f"Lead signal: {cluster.get('title', 'Untitled cluster')}",
        f"Decision: {cluster.get('decision', 'No decision recorded.')}",
        f"Evidence: {cluster.get('evidence', 'No evidence recorded.')} ({cluster.get('evidence_grade', 'grade n/a')})",
        f"Confidence: {cluster.get('confidence_score', 0)}/100; freshness={cluster.get('freshness', 'unknown')}",
        f"Feedback: {cluster.get('feedback_summary', 'No feedback summary.')}",
        risk_line.strip(),
        "",
        "Persona routes:",
        *route_lines,
        "",
        artifact_citation("outbox/dispatch_desk.json", "outbox/opportunity_dispatches.json"),
    ]).replace("\n\n\n", "\n\n")


def routes_for_persona(desk: dict[str, Any], persona_query: str) -> str:
    q = persona_query.lower()
    rows: list[str] = []
    for cluster in desk.get("clusters", []) or []:
        for route in cluster.get("personas", []) or []:
            persona = str(route.get("persona", ""))
            if q in persona.lower() or ("investor" in q and "investor" in persona.lower()):
                rows.append(
                    f"- {cluster.get('title', 'Untitled')}: {clip(route.get('action'), 145)} "
                    f"[{route.get('dispatch_id', 'no-id')}, {route.get('feedback_status', 'awaiting')}]"
                )
    if not rows:
        return f"No routes matched persona query `{persona_query}`.\n\n" + artifact_citation("outbox/dispatch_desk.json")
    return "\n".join([f"Routes matching `{persona_query}`:", "", *rows[:10], "", artifact_citation("outbox/dispatch_desk.json")])


def drill_country(desk: dict[str, Any], country: str) -> str:
    q = country.lower()
    rows: list[str] = []
    for cluster in desk.get("clusters", []) or []:
        title = str(cluster.get("title", ""))
        cluster_country = str(cluster.get("country_cluster", ""))
        if q in title.lower() or q in cluster_country.lower():
            rows.append(
                f"- {title}: {cluster.get('decision', 'No decision recorded.')} "
                f"({cluster.get('confidence_score', 0)}/100, {cluster.get('evidence_grade', 'grade n/a')})"
            )
    if not rows:
        return f"No country drilldown matched `{country}`.\n\n" + artifact_citation("outbox/dispatch_desk.json")
    return "\n".join([f"Country drilldown: {country}", "", *rows[:10], "", artifact_citation("outbox/dispatch_desk.json")])


def what_changed(desk: dict[str, Any]) -> str:
    clusters = desk.get("clusters", []) or []
    freshness = {}
    for cluster in clusters:
        key = cluster.get("freshness", "unknown")
        freshness[key] = freshness.get(key, 0) + 1
    freshness_line = ", ".join(f"{k}: {v}" for k, v in sorted(freshness.items())) or "no freshness data"
    boosts = desk.get("boost_lines", []) or []
    boost_lines = [f"- {line}" for line in boosts[:6]] or ["- No active feedback boosts this cycle."]
    return "\n".join([
        f"Cycle {desk.get('cycle_id', 'unknown')} changed summary:",
        f"- {desk.get('cluster_count', len(clusters))} decision clusters from {desk.get('dispatch_count', 0)} persona routes",
        f"- Freshness mix: {freshness_line}",
        "- Feedback-adjusted priority:",
        *boost_lines,
        "",
        artifact_citation("outbox/dispatch_desk.json", "data/feedback/current_boosts.json"),
    ])


def draft_note(desk: dict[str, Any], country_or_persona: str) -> str:
    q = country_or_persona.lower()
    chosen = None
    chosen_route = None
    for cluster in desk.get("clusters", []) or []:
        if q in str(cluster.get("title", "")).lower() or q in str(cluster.get("country_cluster", "")).lower():
            chosen = cluster
            for route in cluster.get("personas", []) or []:
                if "investor" in str(route.get("persona", "")).lower():
                    chosen_route = route
                    break
            chosen_route = chosen_route or (cluster.get("personas", []) or [None])[0]
            break
    if not chosen:
        chosen = lead_cluster(desk)
        chosen_route = (chosen.get("personas", []) or [None])[0] if chosen else None
    if not chosen or not chosen_route:
        return "No dispatch available to draft from.\n\n" + artifact_citation("outbox/dispatch_desk.json")

    country = chosen.get("country_cluster", "the region")
    title = chosen.get("title", "current signal")
    action = chosen_route.get("action", "review the signal and validate locally")
    return "\n".join([
        f"Draft note for {country}:",
        "",
        f"Subject: {country} signal worth reviewing this cycle",
        "",
        f"A current Caribbean Opportunity Dispatch signal flagged {title}.",
        f"Evidence: {chosen.get('evidence', 'Evidence recorded in Dispatch Desk')} ({chosen.get('evidence_grade', 'grade n/a')}).",
        f"Suggested next step: {action}",
        "",
        "I would treat this as a diligence trigger, not an investment recommendation: validate sector fit, local operator quality, and timing before acting.",
        "",
        artifact_citation("outbox/dispatch_desk.json"),
    ])


def ask(question: str, desk: dict[str, Any]) -> str:
    q = question.lower().strip()
    if not q:
        return "Ask about a country, persona, lead signal, feedback changes, or draft note."
    if any(term in q for term in ["lead", "first", "why is", "ranked first", "top signal"]):
        return explain_lead(desk)
    if any(term in q for term in ["what changed", "changed this cycle", "feedback", "boost", "downrank", "uprank"]):
        return what_changed(desk)
    if "investor" in q:
        if "draft" in q or "note" in q or "message" in q:
            country_match = re.search(r"(?:draft|note|message).*?([A-Z][a-zA-Z .-]+)", question)
            target = country_match.group(1) if country_match else "investor"
            return draft_note(desk, target)
        return routes_for_persona(desk, "investor")
    if "procurement" in q:
        return routes_for_persona(desk, "procurement")
    if "founder" in q or "operator" in q:
        return routes_for_persona(desk, "operator")
    country_terms = ["guyana", "belize", "suriname", "barbados", "caricom", "vincent", "antigua", "kitts"]
    for country in country_terms:
        if country in q:
            if "draft" in q or "note" in q or "message" in q:
                return draft_note(desk, country)
            return drill_country(desk, country)
    return "I can answer deterministic Dispatch Desk questions right now. Try: `explain lead`, `show investor actions`, `what changed this cycle`, `Belize drilldown`, or `draft Guyana investor note`.\n\n" + artifact_citation("outbox/dispatch_desk.json")


def main() -> int:
    parser = argparse.ArgumentParser(description="Query Dispatch Desk artifacts deterministically.")
    sub = parser.add_subparsers(dest="cmd")
    sub.add_parser("explain-lead")
    ask_parser = sub.add_parser("ask")
    ask_parser.add_argument("question", nargs="+")
    persona_parser = sub.add_parser("persona")
    persona_parser.add_argument("persona")
    country_parser = sub.add_parser("country")
    country_parser.add_argument("country")
    sub.add_parser("what-changed")
    draft_parser = sub.add_parser("draft")
    draft_parser.add_argument("target")

    args = parser.parse_args()
    desk = load_desk()
    if args.cmd == "explain-lead":
        print(explain_lead(desk))
    elif args.cmd == "ask":
        print(ask(" ".join(args.question), desk))
    elif args.cmd == "persona":
        print(routes_for_persona(desk, args.persona))
    elif args.cmd == "country":
        print(drill_country(desk, args.country))
    elif args.cmd == "what-changed":
        print(what_changed(desk))
    elif args.cmd == "draft":
        print(draft_note(desk, args.target))
    else:
        parser.print_help()
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
```

**Step 3: Verify compile**

Run:

```bash
python3 -m py_compile agent/query.py
```

Expected: no output, exit 0.

**Step 4: Verify against current artifacts**

Run:

```bash
python3 agent/query.py explain-lead
python3 agent/query.py ask "show investor actions"
python3 agent/query.py ask "what changed this cycle"
python3 agent/query.py ask "draft Belize investor note"
```

Expected:

- Each command prints a useful deterministic answer.
- Each answer includes `Sources:` citations.
- No command calls external APIs.

---

## Task 2: Add Minimal Tests for Query Engine

**Objective:** Lock the deterministic query behavior before wiring UI.

**Files:**
- Create: `tests/test_agent_query.py`

**Step 1: Create tests directory**

```bash
mkdir -p tests
```

**Step 2: Add fixture-based tests**

Create `tests/test_agent_query.py`:

```python
from agent.query import ask, explain_lead, routes_for_persona, what_changed


def sample_desk():
    return {
        "cycle_id": "20260527",
        "cluster_count": 1,
        "dispatch_count": 2,
        "boost_lines": ["Guyana enhanced investment upranked +5"],
        "clusters": [
            {
                "title": "Guyana: capital surge",
                "country_cluster": "Guyana",
                "decision": "Which market to investigate",
                "evidence": "WB FDI surge detected: Guyana",
                "evidence_grade": "A - multi-source",
                "confidence_score": 100,
                "freshness": "sustained",
                "feedback_summary": "Feedback this cycle: 1 forwarded.",
                "personas": [
                    {
                        "persona": "Diaspora Investor",
                        "channel": "Email brief + Telegram",
                        "action": "Investigate Guyana as a capital deployment target.",
                        "dispatch_id": "DSP-1",
                        "feedback_status": "forwarded",
                    },
                    {
                        "persona": "Regional Founder/Operator",
                        "channel": "Telegram",
                        "action": "Assess competitive positioning in Guyana.",
                        "dispatch_id": "DSP-2",
                        "feedback_status": "ignored",
                    },
                ],
            }
        ],
    }


def test_explain_lead_includes_decision_and_citation():
    answer = explain_lead(sample_desk())
    assert "Guyana: capital surge" in answer
    assert "Which market to investigate" in answer
    assert "Sources:" in answer


def test_investor_query_returns_investor_route():
    answer = routes_for_persona(sample_desk(), "investor")
    assert "Diaspora Investor" not in answer  # summary is action-focused
    assert "Investigate Guyana" in answer
    assert "DSP-1" in answer


def test_what_changed_includes_boosts():
    answer = what_changed(sample_desk())
    assert "Guyana enhanced investment upranked +5" in answer


def test_ask_routes_lead_question():
    answer = ask("why is Guyana first", sample_desk())
    assert "Lead signal" in answer
```

**Step 3: Run tests**

Run:

```bash
python3 -m pytest tests/test_agent_query.py -q
```

Expected: `4 passed`.

If pytest is unavailable, use:

```bash
python3 -m unittest discover -s tests
```

But prefer pytest if already installed.

---

## Task 3: Embed Dispatch Desk JSON for Static Analyst Rail

**Objective:** Make generated `dashboard.html` carry enough local JSON for offline query/drilldown.

**Files:**
- Modify: `dashboard/generate.py`

**Step 1: Add safe JSON embedding helper**

Near helper functions in `dashboard/generate.py`, add:

```python
def json_for_script(data: Any) -> str:
    """Serialize JSON safely inside a script tag."""
    text = json.dumps(data, ensure_ascii=False)
    return text.replace("</", "<\\/")
```

**Step 2: Pass serialized product desk into template**

Inside `generate_html`, after `product = product_desk or {}` add:

```python
product_json = json_for_script(product)
```

**Step 3: Add script seed near bottom of HTML**

Before `</body>` add:

```html
<script>
window.DISPATCH_DESK = {product_json};
</script>
```

**Step 4: Verify dashboard generation**

Run:

```bash
python3 dashboard/generate.py --no-open
```

Expected:

- `dashboard.html` generated.
- It contains `window.DISPATCH_DESK =`.
- It does not contain raw `</script>` inside JSON.

Verification command:

```bash
python3 - <<'PY'
from pathlib import Path
html = Path('dashboard.html').read_text()
assert 'window.DISPATCH_DESK =' in html
print('ok')
PY
```

---

## Task 4: Add Analyst Rail UI Shell

**Objective:** Add a visible “Ask the Dispatch Desk” rail beside the product view.

**Files:**
- Modify: `dashboard/generate.py`

**Step 1: Add CSS**

Inside the existing CSS block, add:

```css
.analyst-rail {
  border: 2px solid #21180f;
  background: #fffaf0;
  padding: 14px;
  position: sticky;
  top: 14px;
}
.analyst-rail h2 {
  font-size: 18px;
  color: #21180f;
  margin-bottom: 8px;
}
.analyst-prompts {
  display: flex;
  flex-wrap: wrap;
  gap: 6px;
  margin: 10px 0;
}
.analyst-prompts button,
.ask-row button {
  border: 1px solid #21180f;
  background: #21180f;
  color: #f8ead0;
  padding: 7px 9px;
  font: inherit;
  font-size: 12px;
  cursor: pointer;
}
.ask-row {
  display: grid;
  grid-template-columns: 1fr auto;
  gap: 6px;
}
.ask-row input {
  border: 1px solid #b4874c;
  background: #fdf1d7;
  padding: 8px;
  color: #21180f;
  font: inherit;
  font-size: 13px;
}
.answer-box {
  margin-top: 10px;
  padding: 12px;
  background: #f3ead8;
  border-left: 4px solid #8a3b12;
  white-space: pre-wrap;
  font-size: 13px;
  line-height: 1.45;
  max-height: 420px;
  overflow: auto;
}
.copy-answer {
  margin-top: 8px;
  background: transparent !important;
  color: #8a3b12 !important;
}
```

**Step 2: Add HTML rail**

In the product section where `product-columns` currently has left clusters and right context, add an analyst rail in the right column above or below the notification preview:

```html
<div class="analyst-rail">
  <h2>Ask the Dispatch Desk</h2>
  <p class="tp">Interrogate the cycle without reading every artifact. Answers are deterministic and cite local files.</p>
  <div class="analyst-prompts">
    <button data-question="explain lead">Explain lead signal</button>
    <button data-question="show investor actions">Investor actions</button>
    <button data-question="what changed this cycle">What changed?</button>
    <button data-question="show procurement routes">Procurement routes</button>
    <button data-question="draft Guyana investor note">Draft Guyana note</button>
  </div>
  <div class="ask-row">
    <input id="desk-question" placeholder="Ask about a country, persona, evidence, or feedback…">
    <button id="desk-ask">Ask</button>
  </div>
  <div id="desk-answer" class="answer-box">Try “Explain lead signal” or ask about Guyana, Belize, investors, procurement, or feedback.</div>
  <button id="copy-answer" class="copy-answer">Copy answer</button>
</div>
```

**Step 3: Verify visual placement**

Run:

```bash
python3 dashboard/generate.py --no-open
```

Expected:

- `dashboard.html` contains `Ask the Dispatch Desk`.
- Product clusters still render.
- Existing sections remain below.

---

## Task 5: Add Deterministic Browser-Side Query Logic

**Objective:** Make analyst rail work offline over embedded `window.DISPATCH_DESK`.

**Files:**
- Modify: `dashboard/generate.py`

**Step 1: Add JS query functions**

Before `</body>` after `window.DISPATCH_DESK = ...`, add:

```html
<script>
(function () {
  const desk = window.DISPATCH_DESK || {};
  const answerBox = document.getElementById('desk-answer');
  const input = document.getElementById('desk-question');
  const askButton = document.getElementById('desk-ask');
  const copyButton = document.getElementById('copy-answer');

  function clean(value) { return String(value || '').replace(/\s+/g, ' ').trim(); }
  function clip(value, limit) {
    const text = clean(value);
    if (text.length <= limit) return text;
    return text.slice(0, limit - 1).replace(/\s+\S*$/, '') + '…';
  }
  function clusters() { return Array.isArray(desk.clusters) ? desk.clusters : []; }
  function cite() { return '\n\nSources: `outbox/dispatch_desk.json`, `outbox/opportunity_dispatches.json`'; }

  function explainLead() {
    const c = clusters()[0];
    if (!c) return 'No decision clusters are available. Run the pipeline first.' + cite();
    const routes = (c.personas || []).slice(0, 4).map(r =>
      `- ${r.persona} via ${r.channel}: ${clip(r.action, 120)} [${r.dispatch_id}, feedback=${r.feedback_status}]`
    ).join('\n');
    return [
      `Lead signal: ${c.title}`,
      `Decision: ${c.decision}`,
      `Evidence: ${c.evidence} (${c.evidence_grade})`,
      `Confidence: ${c.confidence_score}/100; freshness=${c.freshness}`,
      `Feedback: ${c.feedback_summary}`,
      '',
      'Persona routes:',
      routes,
      cite()
    ].join('\n');
  }

  function personaRoutes(q) {
    const rows = [];
    clusters().forEach(c => (c.personas || []).forEach(r => {
      const persona = clean(r.persona).toLowerCase();
      if (persona.includes(q) || (q.includes('investor') && persona.includes('investor')) || (q.includes('operator') && persona.includes('operator'))) {
        rows.push(`- ${c.title}: ${clip(r.action, 135)} [${r.dispatch_id}, ${r.feedback_status}]`);
      }
    }));
    return rows.length ? `Routes matching ${q}:\n\n${rows.slice(0, 10).join('\n')}${cite()}` : `No routes matched ${q}.${cite()}`;
  }

  function whatChanged() {
    const freshness = {};
    clusters().forEach(c => { freshness[c.freshness || 'unknown'] = (freshness[c.freshness || 'unknown'] || 0) + 1; });
    const freshLine = Object.entries(freshness).map(([k, v]) => `${k}: ${v}`).join(', ') || 'no freshness data';
    const boosts = (desk.boost_lines || []).slice(0, 6).map(x => `- ${x}`).join('\n') || '- No active feedback boosts this cycle.';
    return `Cycle ${desk.cycle_id || 'unknown'} changed summary:\n- ${desk.cluster_count || clusters().length} decision clusters from ${desk.dispatch_count || 0} persona routes\n- Freshness mix: ${freshLine}\n- Feedback-adjusted priority:\n${boosts}\n\nSources: \`outbox/dispatch_desk.json\`, \`data/feedback/current_boosts.json\``;
  }

  function countryDrilldown(q) {
    const rows = clusters().filter(c => clean(c.title).toLowerCase().includes(q) || clean(c.country_cluster).toLowerCase().includes(q))
      .map(c => `- ${c.title}: ${c.decision} (${c.confidence_score}/100, ${c.evidence_grade})`);
    return rows.length ? `Country drilldown: ${q}\n\n${rows.join('\n')}${cite()}` : `No country drilldown matched ${q}.${cite()}`;
  }

  function draftNote(q) {
    let c = clusters().find(c => clean(c.title).toLowerCase().includes(q) || clean(c.country_cluster).toLowerCase().includes(q)) || clusters()[0];
    if (!c) return 'No dispatch available to draft from.' + cite();
    let route = (c.personas || []).find(r => clean(r.persona).toLowerCase().includes('investor')) || (c.personas || [])[0];
    if (!route) return 'No persona route available to draft from.' + cite();
    const country = c.country_cluster || 'the region';
    return `Draft note for ${country}:\n\nSubject: ${country} signal worth reviewing this cycle\n\nA current Caribbean Opportunity Dispatch signal flagged ${c.title}.\nEvidence: ${c.evidence} (${c.evidence_grade}).\nSuggested next step: ${route.action}\n\nI would treat this as a diligence trigger, not an investment recommendation: validate sector fit, local operator quality, and timing before acting.\n\nSources: \`outbox/dispatch_desk.json\``;
  }

  function answer(question) {
    const q = clean(question).toLowerCase();
    if (!q) return 'Ask about a country, persona, lead signal, feedback changes, or draft note.';
    if (q.includes('lead') || q.includes('first') || q.includes('why is') || q.includes('top signal')) return explainLead();
    if (q.includes('what changed') || q.includes('feedback') || q.includes('boost') || q.includes('downrank') || q.includes('uprank')) return whatChanged();
    if (q.includes('investor')) return (q.includes('draft') || q.includes('note') || q.includes('message')) ? draftNote(q) : personaRoutes('investor');
    if (q.includes('procurement')) return personaRoutes('procurement');
    if (q.includes('founder') || q.includes('operator')) return personaRoutes('operator');
    for (const country of ['guyana', 'belize', 'suriname', 'barbados', 'caricom', 'vincent', 'antigua', 'kitts']) {
      if (q.includes(country)) return (q.includes('draft') || q.includes('note') || q.includes('message')) ? draftNote(country) : countryDrilldown(country);
    }
    return 'Try: explain lead, show investor actions, what changed this cycle, Belize drilldown, or draft Guyana investor note.' + cite();
  }

  function run(question) {
    const result = answer(question);
    answerBox.textContent = result;
  }

  document.querySelectorAll('[data-question]').forEach(btn => {
    btn.addEventListener('click', () => {
      input.value = btn.dataset.question;
      run(btn.dataset.question);
    });
  });
  askButton.addEventListener('click', () => run(input.value));
  input.addEventListener('keydown', (event) => {
    if (event.key === 'Enter') run(input.value);
  });
  copyButton.addEventListener('click', async () => {
    try { await navigator.clipboard.writeText(answerBox.textContent); copyButton.textContent = 'Copied'; }
    catch (_) { copyButton.textContent = 'Select + copy manually'; }
    setTimeout(() => { copyButton.textContent = 'Copy answer'; }, 1500);
  });
})();
</script>
```

**Step 2: Verify static behavior exists**

Run:

```bash
python3 dashboard/generate.py --no-open
python3 - <<'PY'
from pathlib import Path
html = Path('dashboard.html').read_text()
for needle in ['Ask the Dispatch Desk', 'function explainLead()', 'data-question="show investor actions"']:
    assert needle in html, needle
print('ok')
PY
```

Expected: `ok`.

---

## Task 6: Add Headless CLI to README and Demo Docs

**Objective:** Update docs so the agent rail/headless direction is explicit.

**Files:**
- Modify: `README.md`
- Modify: `deliverables/demo-script.md`
- Modify: `deliverables/submission-positioning.md`
- Modify: `architecture/cron.md`

**Step 1: README additions**

In `README.md`, under Run / Individual steps, add:

```markdown
Headless Dispatch Desk query:

```bash
python3 agent/query.py explain-lead
python3 agent/query.py ask "show investor actions"
python3 agent/query.py ask "what changed this cycle"
python3 agent/query.py ask "draft Belize investor note"
```
```

Under Delivery/User Interaction, add:

```markdown
The dashboard includes an **Ask the Dispatch Desk** analyst rail. It is deterministic and local for now: answers come from `outbox/dispatch_desk.json` and cite local artifacts. This keeps the demo reliable while leaving a clean path to a future headless LLM/API layer.
```

**Step 2: Demo script update**

In `deliverables/demo-script.md`, add one demo step after opening dashboard:

```markdown
2. Use the “Ask the Dispatch Desk” analyst rail:
   - click “Explain lead signal”
   - click “Investor actions”
   - ask “draft Guyana investor note”
```

Renumber remaining steps.

**Step 3: Submission positioning update**

Add to Product Framing:

```markdown
- Ask the Dispatch Desk analyst rail for drilldowns, evidence explanations, persona filters, and copyable draft briefs
- Headless query CLI (`agent/query.py`) so web, CLI, Telegram, and future API clients can share the same deterministic intelligence layer
```

**Step 4: Architecture cron update**

In `architecture/cron.md`, add:

```markdown
The agent/query layer is intentionally separate from cron. Cron produces artifacts; `agent/query.py` and the dashboard analyst rail interrogate those artifacts. Future headless services should call the same query functions rather than reimplementing interpretation.
```

**Step 5: Verify docs mention new layer**

Run:

```bash
grep -R "Ask the Dispatch Desk\|agent/query.py" README.md deliverables architecture -n
```

Expected: matches in README, demo, positioning, and architecture docs.

---

## Task 7: Add Feedback Recording Placeholder, Not Browser Mutation

**Objective:** Make feedback action visible without unsafe browser-side file writes.

**Files:**
- Modify: `dashboard/generate.py`
- Modify: `agent/query.py`

**Step 1: Add CLI helper output**

In `agent/query.py`, add function:

```python
def feedback_command(dispatch_id: str, status: str, note: str = "") -> str:
    safe_note = note.replace('"', "'")
    return f'python3 packagers/feedback_intake.py --dispatch-id {dispatch_id} --status {status} --note "{safe_note}"'
```

Add CLI subcommand:

```python
feedback_parser = sub.add_parser("feedback-command")
feedback_parser.add_argument("dispatch_id")
feedback_parser.add_argument("status")
feedback_parser.add_argument("--note", default="")
```

And handler:

```python
elif args.cmd == "feedback-command":
    print(feedback_command(args.dispatch_id, args.status, args.note))
```

**Step 2: Browser UX copy**

In analyst rail, add text:

```html
<p class="tp">Feedback is copy-command only in the static page. The browser does not write files.</p>
```

Optional button later can generate command text for selected dispatch IDs; do not implement mutation in this phase.

**Step 3: Verify**

Run:

```bash
python3 agent/query.py feedback-command DSP-20260527-023 forwarded --note "shared with investor"
```

Expected:

```bash
python3 packagers/feedback_intake.py --dispatch-id DSP-20260527-023 --status forwarded --note "shared with investor"
```

---

## Task 8: Validation Sweep

**Objective:** Verify code, generated artifacts, and UI markers.

**Files:**
- No new files unless failures require fixes.

**Step 1: Compile Python**

Run:

```bash
python3 -m py_compile $(git ls-files '*.py') agent/query.py
```

Expected: no output, exit 0.

**Step 2: Run tests**

Run:

```bash
python3 -m pytest tests/test_agent_query.py -q
```

Expected: `4 passed`.

If pytest is not installed, record that and run:

```bash
python3 -m unittest discover -s tests
```

**Step 3: Regenerate pipeline**

Run:

```bash
bash run_pipeline.sh
```

Expected:

- All steps pass except Telegram send may skip if env vars missing.
- Dispatch Desk regenerates.
- Dashboard regenerates.

**Step 4: Static assertions**

Run:

```bash
python3 - <<'PY'
from pathlib import Path
html = Path('dashboard.html').read_text()
telegram = Path('outbox/telegram_brief.md').read_text()
assert 'Ask the Dispatch Desk' in html
assert 'window.DISPATCH_DESK =' in html
assert 'function explainLead()' in html
assert len(telegram) < 4096
print('ok')
PY
```

Expected: `ok`.

**Step 5: Headless query assertions**

Run:

```bash
python3 agent/query.py explain-lead | head -20
python3 agent/query.py ask "show investor actions" | head -20
python3 agent/query.py ask "what changed this cycle" | head -20
python3 agent/query.py ask "draft Guyana investor note" | head -30
```

Expected: useful deterministic answers with `Sources:` citations.

---

## Future Phase: Real Headless Agent/API

Do not implement in this phase, but keep interfaces compatible.

Future files likely:

- `agent/server.py` — tiny local HTTP API over `agent/query.py`
- `agent/llm.py` — optional local LLM summarizer constrained to retrieved artifacts
- `agent/retrieval.py` — artifact/context retrieval with citations
- `distributors/telegram_agent.py` — Telegram reply handler using same query functions

---

## Later Version / Nice to Have: Optional ML Sidecar

**Discussion capture (2026-06-17):** Whether to add PyTorch/ML to deepen the moot.

**Decision:** **No — stay deterministic in core.** The moat is *auditable coordination*: cited answers, deterministic rules, agent-agnostic protocol. PyTorch makes you "another AI tool."

**When it would make sense (separate repo: `signal-fabric-ml/`):**

| Use Case | Approach |
|----------|----------|
| Semantic deduplication across cycles | Local embeddings + FAISS sidecar |
| Anomaly detection on NDBC buoy time series | Tiny LSTM forecaster sidecar |
| Signal classification for new source types | Fine-tuned DistilBERT sidecar |
| Sector hypothesis generation from unstructured text | Local LLM (Gemma/Llama) constrained to retrieved artifacts |

**Interfaces:** Sidecar exposes gRPC/HTTP (`/ml/deduplicate`, `/ml/anomaly`, `/ml/classify`). Core stays deterministic; sidecar is optional enhancer.

**Revisit trigger:** When signal volume >500/cycle OR new unstructured sources (satellite imagery, social media, PDFs) need classification at scale.

Future endpoints:

- `GET /api/context`
- `POST /api/ask`
- `POST /api/drilldown`
- `POST /api/draft`
- `POST /api/feedback-command`

Important rule for future LLM mode:

- Retrieval first.
- Cite artifacts.
- If data is missing, say missing.
- Never infer beyond generated artifacts unless explicitly labeled as analysis.

---

## Suggested Commit Boundaries

1. `feat: add headless dispatch desk query engine`
2. `test: cover deterministic dispatch desk queries`
3. `feat: add dashboard analyst rail`
4. `docs: document agentic dispatch desk plan and demo flow`

---

## Risks and Mitigations

- **Risk:** Analyst rail becomes another generic chatbot.
  - **Mitigation:** Deterministic intent matching first; no open-ended LLM in this phase.

- **Risk:** Browser attempts file mutation for feedback.
  - **Mitigation:** Static page only emits copyable CLI commands; no writes.

- **Risk:** Dashboard gets visually crowded.
  - **Mitigation:** Keep rail compact; product clusters remain primary; operator sections stay below.

- **Risk:** Query logic duplicates Python and JS.
  - **Mitigation:** Accept small duplication for static demo now; future Phase extracts shared API from `agent/query.py`.

- **Risk:** Reports and agent answers drift.
  - **Mitigation:** Both read `dispatch_desk.json`; generated artifact is source of truth.
