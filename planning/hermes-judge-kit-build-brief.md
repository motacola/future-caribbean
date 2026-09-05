# Hermes Build Brief — 4C: Judge Demo Kit

Implementation only. Goal: anyone (Chris, a teammate, a judge alone) can run
a flawless 3-minute demo from one document, with a rehearsed fallback for
every failure mode.

## Read First

- `README.md` — product claims and architecture
- `PLAN_ENGINE_2026-06-10.md` — Decisions section (what was promised)
- `outbox/judge_brief.md` — existing generated judge artifact
- `agents.md`, `llms.txt` — the agent surface
- Live site: https://abeng.vercel.app (fetch the dashboard and
  /api/status to confirm what is actually live before you write about it)

## Build — one file: `JUDGE_DEMO.md`

Structure (use these exact section headings):

### 1. The pitch in three sentences
Plain language. The fragmentation problem, the desk that solves it, and the
"humans read it, agents query it" differentiator. No hype words
(revolutionary, game-changing, etc.).

### 2. Three-minute walkthrough (live site)
Numbered, timed steps using https://abeng.vercel.app:
0:00 Live Wire + front page; 0:30 click Guyana on the map (drill cards);
1:00 the lead story — decision, checklist, validation pack with the LIVE
tender closing 2026-06-16; 1:45 Ask the desk — click "Draft a note for
Guyana"; 2:15 the For Agents block — run the curl command live in a
terminal; 2:45 close on /feed.xml in a browser tab.
Each step: what to do, what to say (one sentence), what the judge should
notice.

### 3. The agent demo (terminal, 30 seconds)
The exact three commands from README's "same engine, three ways" plus the
MCP connect line for Claude, each with its expected output shape.

### 4. Proof commands per claim
A table: claim → command/URL → what proves it. Cover: 6 public sources,
4-hour cycles (GitHub Actions), deterministic cited answers, live Guyana
tenders with closing dates, agent-agnostic surface (tools.json + feed.xml +
MCP), feedback loop re-weighting.

### 5. Failure drill
- Wi-Fi dies → local: `python3 -m http.server 8090` + dashboard.html
  (theater auto-falls back to replay; ask-desk shows offline state — say
  "the artifacts ARE the product, the site is just a window").
- Vercel down → same local fallback.
- A judge asks "is this AI-generated content?" → the honest answer
  (deterministic pipeline, cited artifacts, humanizer is a translation
  layer, the only LLM in the system is the agents that USE it).
- A judge asks about Jamaica tenders → the honest answer (GOJEP is
  session-gated; documented finding; Guyana eProcure is live).

### 6. Pre-demo checklist
5 items max: live site loads, /api/ask answers, feed.xml fresh (check
lastBuildDate), local fallback tested, terminal ready with commands pasted.

## Constraints

- Facts must match the live system — verify each claim against the live
  site or the repo before writing it. No invented numbers.
- House voice: plain, confident, no hype (match README tone).
- Do NOT git commit. Do NOT run run_pipeline.sh or server.py __main__.
- Only create `JUDGE_DEMO.md` and your result file; touch nothing else.

## Validation

```bash
python3 -m pytest -q          # untouched, stays 42 passed
ls JUDGE_DEMO.md
```

Final summary to `planning/hermes-judge-kit-result.md`: what you verified
live vs from the repo, plus anything you could not verify.
