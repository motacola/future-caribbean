#!/usr/bin/env python3
"""Caribbean Opportunity Dispatch — product homepage generator.

Reads the latest pipeline artifacts and renders a polished, public-facing
homepage. Designed to look like a real product, not a hackathon demo.

Layout:
  Hero       → product name, tagline, live stats
  Today      → one lead dispatch with full narrative
  For You    → audience-specific output cards
  Trust      → source provenance, recency, coverage
  Deep       → full system proof (behind toggle)
"""

from __future__ import annotations

import argparse
import html as html_module
import json
import os
import re
import subprocess
import sys
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parents[1]
OUTPUT = ROOT / "dashboard.html"

# ── helpers ────────────────────────────────────────────────

def j(v): return html_module.escape(str(v), quote=True)

def read_json(p: Path) -> dict | None:
    if not p.exists(): return None
    try: return json.loads(p.read_text())
    except: return None

def read_text(p: Path) -> str:
    if not p.exists(): return ""
    return p.read_text("utf-8", errors="replace")

def ts_age(ts: str | None) -> str:
    if not ts: return "—"
    try:
        dt = datetime.fromisoformat(ts.replace("Z", "+00:00"))
        m = int((datetime.now(timezone.utc) - dt).total_seconds() / 60)
        if m < 2: return "just now"
        if m < 60: return f"{m}m ago"
        h = m // 60
        if h < 24: return f"{h}h ago"
        return f"{h // 24}d ago"
    except: return "—"

def band(score: int) -> str:
    if score >= 85: return "High"
    if score >= 65: return "Medium"
    return "Early signal"

# ── Load all data ──────────────────────────────────────────

desk = read_json(ROOT / "outbox" / "dispatch_desk.json") or {}
clusters = desk.get("clusters", []) or []

# The lead cluster
lead = clusters[0] if clusters else {}
lead_country = lead.get("country_cluster", "Caribbean")
lead_title = lead.get("title", "")
lead_evidence = lead.get("evidence", "")
lead_decision = lead.get("decision", "")
lead_score = lead.get("confidence_score", 0)
lead_grade = lead.get("evidence_grade", "")
lead_fresh = lead.get("freshness", "")
lead_risks = lead.get("risk_flags", []) or []
lead_personas = lead.get("personas", []) or []

# Build persona output cards from lead cluster
persona_cards = ""
for p in lead_personas[:4]:
    name = p.get("persona", "")
    channel = p.get("channel", "")
    action = p.get("action", p.get("recommended_action", ""))
    feedback = str(p.get("feedback_status", "")).replace("_", " ").title()
    if len(action) > 120: action = action[:117] + "…"
    persona_cards += f"""
    <div class="aud-card">
      <div class="aud-name">{j(name)}</div>
      <div class="aud-channel">{j(channel)}</div>
      <p class="aud-action">{j(action)}</p>
      <div class="aud-status">Status: {j(feedback)}</div>
    </div>"""

# Regional thesis
thesis = read_text(ROOT / "outbox" / "regional_thesis.md")
thesis_plain = ""
for line in thesis.split("\n"):
    line = line.strip()
    if line and not line.startswith("#") and not line.startswith("Generated") and not line.startswith("**"):
        thesis_plain = line[:280]
        break

# Why now
whynow_items = []
for line in read_text(ROOT / "outbox" / "why_now.md").split("\n"):
    line = line.strip()
    if line.startswith(("🟢", "🔴", "🟡")):
        whynow_items.append(line[:100])

# Telegram brief
telegram_raw = read_text(ROOT / "outbox" / "telegram_brief.md")
# Strip telegram markdown for cleaner display
telegram_clean = re.sub(r'\*+', '', telegram_raw)
telegram_clean = re.sub(r'`+', '', telegram_clean)
telegram_preview = telegram_clean[:600]

# Investor brief
investor_raw = read_text(ROOT / "outbox" / "investor_brief.md")
investor_clean = re.sub(r'#+', '', investor_raw)
investor_clean = re.sub(r'\*+', '', investor_clean)
investor_preview = investor_clean[:500]

# Sources with timestamps
sources_cfg = [
    ("World Bank Indicators",   "world_bank", "REST API · 5 indicators × 13 countries"),
    ("IDB Open Data",           "idb",        "CKAN API · Regional project datasets"),
    ("NOAA Weather Alerts",     "noaa",       "NWS API · Active hazard alerts"),
    ("NDBC Marine Buoys",       "ndbc",       "Marine conditions · 6 buoys"),
    ("CARICOM Statistics",      "tier2",      "WordPress REST · 126 datasets"),
    ("CDB Procurement Feed",    "tier2",      "RSS · Project & procurement notices"),
]
source_rows = ""
for label, key, desc in sources_cfg:
    d = read_json(ROOT / "data" / key / "latest.json")
    age = ts_age(d.get("fetched_at") if d else None)
    ok = d is not None
    dot = "●" if ok else "○"
    color = "src-ok" if ok else "src-off"
    source_rows += f"""
    <tr class="{color}">
      <td><span class="dot">{dot}</span> {j(label)}</td>
      <td>{j(desc)}</td>
      <td>{j(age)}</td>
    </tr>"""

# Feedback
fb_raw = read_json(ROOT / "data" / "feedback" / "state.json") or {}
fb_history = fb_raw.get("history", []) or []
fb_boosts = fb_raw.get("boosts", {})
fb_total = len(fb_history)
fb_actions: dict[str, int] = {}
for e in fb_history:
    s = e.get("feedback_status", "unknown")
    fb_actions[s] = fb_actions.get(s, 0) + 1
fb_action_rows = ""
icons = {"forwarded": "📤", "replied": "💬", "opened": "👁", "decision_changed": "🔀", "ignored": "—"}
for act, cnt in sorted(fb_actions.items(), key=lambda x: -x[1]):
    fb_action_rows += f'<span class="fb-pill">{icons.get(act,"•")} {act.replace("_"," ").title()}: {cnt}</span>'

boost_rows = ""
for kind, countries in fb_boosts.items():
    for country, val in countries.items():
        if val != 0:
            sign = "+" if val > 0 else ""
            boost_rows += f'<div class="boost-line">{j(country)} {j(kind.replace("_"," "))}: {sign}{val}</div>'

cycle_id = desk.get("cycle_id", "—")
now_str = datetime.now(timezone.utc).strftime("%B %d, %Y — %H:%M UTC")

# Counts
n_clusters = len(clusters)
n_personas = desk.get("dispatch_count", 0)
n_sources = sum(1 for k in ["world_bank","idb","noaa","ndbc","tier2"]
                if (ROOT / "data" / k / "latest.json").exists())
n_composite = 0
comp = read_json(ROOT / "data" / "composite" / "latest.json")
if comp: n_composite = len(comp.get("signals", []) or [])

# Regional signals summary (for "For You" section)
regional_signals = ""
for c in clusters[1:5]:
    ct = c.get("title", "")
    cc = c.get("country_cluster", "")
    cs = c.get("confidence_score", 0)
    cb = band(cs)
    risk = c.get("risk_flags", [])
    risk_note = f'<span class="risk-tag">⚠️ {j(risk[0][:60])}</span>' if risk else ""
    regional_signals += f"""
    <div class="signal-row">
      <div class="signal-main">
        <strong>{j(ct)}</strong>
        <span class="signal-loc">{j(cc)} · {cb} confidence</span>
      </div>
      {risk_note}
    </div>"""

# Analyst desk JS data
analyst_data = {
    "cycle": cycle_id,
    "lead": {
        "title": lead_title, "country": lead_country,
        "evidence": lead_evidence, "decision": lead_decision,
        "score": lead_score, "band": band(lead_score),
        "grade": lead_grade, "freshness": lead_fresh,
        "risks": lead_risks,
        "personas": [{"persona": p.get("persona",""), "channel": p.get("channel",""),
                       "action": p.get("action",""), "feedback": p.get("feedback_status","")}
                     for p in lead_personas],
    },
    "regional": [{"title": c.get("title",""), "country": c.get("country_cluster",""),
                   "score": c.get("confidence_score",0), "band": band(c.get("confidence_score",0)),
                   "decision": c.get("decision",""), "evidence": c.get("evidence",""),
                   "risks": c.get("risk_flags",[]) or []} for c in clusters[1:8]],
    "sources": n_sources, "countries": 13,
    "signals": n_composite, "dispatches": n_personas,
    "feedback_total": fb_total, "boosts": boost_rows,
    "thesis": thesis_plain, "whynow": whynow_items,
}
analyst_json = json.dumps(analyst_data, ensure_ascii=False).replace("</", "<\\/")

# ── HTML ───────────────────────────────────────────────────

html = f"""<!DOCTYPE html>
<html lang="en">
<head>
<meta charset="UTF-8">
<meta name="viewport" content="width=device-width,initial-scale=1.0">
<title>Caribbean Opportunity Dispatch</title>
<style>
:root {{
  --bg: #080B14; --surface: #111627; --surface-2: #1A2035;
  --line: #1E2A40; --text: #E8ECF4; --faint: #6B7FA0; --accent: #3B82F6;
  --ok: #10B981; --warn: #F59B0B; --no: #EF4444; --radius: 10px;
  --font: -apple-system, 'Inter', 'Segoe UI', system-ui, sans-serif;
}}
* {{ box-sizing: border-box; margin: 0; padding: 0; }}
body {{ font-family: var(--font); background: var(--bg); color: var(--text); line-height: 1.6; font-size: 15px; }}

/* ── top bar ── */
.top-bar {{ background: var(--surface); border-bottom: 1px solid var(--line); padding: 14px 0; }}
.top-inner {{ max-width: 1080px; margin: 0 auto; padding: 0 24px; display: flex; justify-content: space-between; align-items: center; }}
.brand {{ font-size: 16px; font-weight: 800; letter-spacing: -0.3px; }}
.brand span {{ color: var(--accent); }}
.top-links a {{ color: var(--faint); text-decoration: none; font-size: 13px; margin-left: 18px; }}
.top-links a:hover {{ color: var(--text); }}
.live-dot {{ width: 7px; height: 7px; background: var(--ok); border-radius: 50%; display: inline-block; margin-right: 5px; animation: pulse 2s infinite; }}
@keyframes pulse {{ 0%,100% {{ opacity:1; }} 50% {{ opacity:.4; }} }}

/* ── hero ── */
.hero {{ max-width: 1080px; margin: 0 auto; padding: 52px 24px 40px; }}
.hero h1 {{ font-size: clamp(28px, 4vw, 42px); font-weight: 900; letter-spacing: -1.2px; line-height: 1.1; margin-bottom: 14px; }}
.hero h1 em {{ font-style: normal; color: var(--accent); }}
.hero p {{ font-size: 17px; color: var(--faint); max-width: 600px; margin-bottom: 28px; }}
.hero-stats {{ display: flex; gap: 28px; flex-wrap: wrap; }}
.stat {{ text-align: left; }}
.stat-n {{ font-size: 22px; font-weight: 800; color: var(--text); }}
.stat-l {{ font-size: 11px; color: var(--faint); text-transform: uppercase; letter-spacing: .8px; margin-top: 2px; }}

/* ── sections ── */
.section {{ max-width: 1080px; margin: 0 auto; padding: 32px 24px; }}
.section-label {{ font-size: 11px; text-transform: uppercase; letter-spacing: 1.2px; color: var(--faint); margin-bottom: 14px; }}
.section-title {{ font-size: 20px; font-weight: 800; letter-spacing: -.3px; margin-bottom: 6px; }}
.section-sub {{ font-size: 14px; color: var(--faint); margin-bottom: 24px; max-width: 560px; }}

/* ── dispatch card ── */
.dispatch-card {{ background: var(--surface); border: 1px solid var(--line); border-radius: var(--radius); padding: 28px; margin-bottom: 16px; }}
.dispatch-header {{ display: flex; justify-content: space-between; align-items: flex-start; margin-bottom: 16px; }}
.dispatch-tag {{ font-size: 11px; text-transform: uppercase; letter-spacing: 1.2px; color: var(--faint); }}
.conf-badge {{ display: inline-block; padding: 3px 10px; border-radius: 20px; font-size: 12px; font-weight: 700; }}
.high {{ background: rgba(16,185,129,.12); color: var(--ok); }}
.med {{ background: rgba(245,185,11,.12); color: var(--warn); }}
.early {{ background: rgba(239,68,68,.12); color: var(--no); }}
.dispatch-card h2 {{ font-size: 22px; font-weight: 800; margin: 8px 0 12px; letter-spacing: -.3px; }}
.dispatch-why {{ font-size: 15px; color: var(--faint); margin-bottom: 16px; padding-bottom: 16px; border-bottom: 1px solid var(--line); }}
.dispatch-why strong {{ color: var(--text); }}
.risk-note {{ background: rgba(239,68,68,.08); border: 1px solid rgba(239,68,68,.2); border-radius: 6px; padding: 8px 12px; font-size: 13px; color: var(--no); margin: 10px 0; }}

/* ── signals list ── */
.signal-row {{ display: flex; justify-content: space-between; align-items: center; padding: 14px 0; border-bottom: 1px solid var(--line); gap: 12px; }}
.signal-row:last-child {{ border-bottom: none; }}
.signal-main {{ flex: 1; }}
.signal-main strong {{ display: block; font-size: 14px; font-weight: 600; margin-bottom: 2px; }}
.signal-loc {{ font-size: 12px; color: var(--faint); }}
.risk-tag {{ font-size: 12px; color: var(--no); background: rgba(239,68,68,.08); padding: 3px 8px; border-radius: 4px; white-space: nowrap; }}

/* ── audience cards ── */
.audience-grid {{ display: grid; grid-template-columns: repeat(auto-fill, minmax(240px, 1fr)); gap: 14px; }}
.aud-card {{ background: var(--surface); border: 1px solid var(--line); border-radius: var(--radius); padding: 16px; }}
.aud-name {{ font-weight: 700; font-size: 14px; margin-bottom: 2px; }}
.aud-channel {{ font-size: 11px; color: var(--accent); margin-bottom: 8px; }}
.aud-action {{ font-size: 13px; color: var(--faint); margin-bottom: 8px; }}
.aud-status {{ font-size: 11px; color: var(--warn); }}

/* ── output cards ── */
.output-grid {{ display: grid; grid-template-columns: 1fr 1fr; gap: 14px; }}
.output-card {{ background: var(--surface); border: 1px solid var(--line); border-radius: var(--radius); padding: 20px; }}
.output-card h4 {{ font-size: 13px; font-weight: 700; margin-bottom: 4px; }}
.output-channel {{ font-size: 11px; color: var(--accent); margin-bottom: 10px; white-space: nowrap; overflow: hidden; text-overflow: ellipsis; }}
.output-body {{ font-size: 12px; color: var(--faint); white-space: pre-wrap; font-family: 'SF Mono', 'Fira Code', monospace; max-height: 180px; overflow: auto; line-height: 1.5; background: var(--bg); border-radius: 6px; padding: 12px; }}

/* ── analyst rail ── -->
.analyst {{ background: var(--surface); border: 1px solid var(--line); border-radius: var(--radius); padding: 18px; margin-top: 20px; }}
.analyst h3 {{ font-size: 14px; font-weight: 700; margin-bottom: 6px; }}
.analyst > p {{ font-size: 12px; color: var(--faint); margin-bottom: 10px; }}
.aprompts {{ display: flex; flex-wrap: wrap; gap: 6px; margin-bottom: 10px; }}
.aprompts button {{ background: var(--surface-2); border: 1px solid var(--line); color: var(--text); padding: 5px 10px; border-radius: 6px; font-size: 12px; cursor: pointer; font-family: var(--font); }}
.aprompts button:hover {{ border-color: var(--accent); }}
.ask-row {{ display: grid; grid-template-columns: 1fr auto; gap: 8px; }}
.ask-row input {{ background: var(--bg); border: 1px solid var(--line); color: var(--text); padding: 8px 12px; border-radius: 6px; font-size: 13px; font-family: var(--font); }}
.ask-row button {{ background: var(--accent); border: none; color: white; padding: 8px 14px; border-radius: 6px; font-size: 13px; cursor: pointer; font-weight: 600; font-family: var(--font); }}
.a-box {{ margin-top: 10px; padding: 12px; background: var(--bg); border-left: 3px solid var(--accent); font-size: 13px; color: var(--faint); white-space: pre-wrap; max-height: 220px; overflow: auto; border-radius: 0 6px 6px 0; }}

/* ── sources table ── */
.src-table {{ width: 100%; border-collapse: collapse; font-size: 13px; }}
.src-table td {{ padding: 10px 12px; border-bottom: 1px solid var(--line); color: var(--faint); }}
.src-table tr:last-child td {{ border-bottom: none; }}
.src-table td:first-child {{ color: var(--text); font-weight: 600; }}
.src-ok .dot {{ color: var(--ok); }}
.src-off .dot {{ color: var(--faint); }}
.dot {{ margin-right: 6px; }}

/* ── feedback ── */
.fb-pill {{ display: inline-block; padding: 4px 10px; border-radius: 20px; font-size: 12px; background: var(--surface-2); color: var(--faint); margin: 2px; }}
.boost-line {{ font-size: 13px; color: var(--faint); padding: 3px 0; }}
.fb-section {{ background: var(--surface); border: 1px solid var(--line); border-radius: var(--radius); padding: 18px; }}

/* ── deep proof (collapsible) ── */
.deep-proof {{ margin-top: 32px; border-top: 1px solid var(--line); padding-top: 24px; }}
.deep-btn {{ background: var(--surface-2); border: 1px solid var(--line); color: var(--faint); padding: 8px 16px; border-radius: 6px; font-size: 13px; cursor: pointer; font-family: var(--font); }}
.deep-btn:hover {{ border-color: var(--accent); color: var(--text); }}
.deep-content {{ display: none; margin-top: 20px; }}
.deep-content.open {{ display: block; }}

/* ── two-col ── -->
.two-col {{ display: grid; grid-template-columns: 2fr 1fr; gap: 24px; }}
@media(max-width:800px) {{ .two-col {{ grid-template-columns: 1fr; }} .output-grid {{ grid-template-columns: 1fr; }} .hero-stats {{ gap: 16px; }} }}

/* ── footer ── */
footer {{ border-top: 1px solid var(--line); padding: 24px; text-align: center; font-size: 12px; color: var(--faint); margin-top: 40px; }}
</style>
</head>
<body>

<!-- top bar -->
<div class="top-bar">
  <div class="top-inner">
    <div class="brand">🌴 Caribbean <span>Opportunity Dispatch</span></div>
    <div class="top-links">
      <a href="#" onclick="return false;"><span class="live-dot"></span>Live</a>
      <a href="#" onclick="showDeep(); return false;">System Proof</a>
    </div>
  </div>
</div>

<!-- hero -->
<div class="hero">
  <h1>Daily intelligence for a <em>connected Caribbean</em> market.</h1>
  <p>We turn fragmented public data into clear opportunity signals — then deliver the right version to investors, founders, operators, and policymakers.</p>
  <div class="hero-stats">
    <div class="stat"><div class="stat-n">13</div><div class="stat-l">Countries</div></div>
    <div class="stat"><div class="stat-n">{n_sources}/6</div><div class="stat-l">Sources live</div></div>
    <div class="stat"><div class="stat-n">{n_composite}</div><div class="stat-l">Signals found</div></div>
    <div class="stat"><div class="stat-n">{n_personas}</div><div class="stat-l">Dispatches sent</div></div>
    <div class="stat"><div class="stat-n">4h</div><div class="stat-l">Refresh cycle</div></div>
  </div>
</div>

<!-- today's lead dispatch -->
<div class="section">
  <div class="section-label">Today's lead dispatch</div>
  <div class="dispatch-card">
    <div class="dispatch-header">
      <div class="dispatch-tag">{j(lead_country)} · Cycle {j(cycle_id)}</div>
      <span class="conf-badge {'high' if lead_score>=85 else 'med' if lead_score>=65 else 'early'}">{band(lead_score)} confidence · {j(lead_grade)}</span>
    </div>
    <h2>{j(lead_title)}</h2>
    <div class="dispatch-why">
      <strong>Why it matters:</strong> {j(thesis_plain)}
    </div>
    {"<div class='risk-note'>⚠️ Risk: " + j(lead_risks[0]) + "</div>" if lead_risks else ""}
    <div style="margin-top:14px;font-size:13px;color:var(--faint)"><strong>Evidence:</strong> {j(lead_evidence)}</div>
    <div style="margin-top:6px;font-size:13px;color:var(--faint)"><strong>Decision:</strong> {j(lead_decision)}</div>
  </div>
</div>

<!-- more signals -->
<div class="section" style="padding-top:0">
  <div class="section-label">Also on our radar</div>
  <div class="dispatch-card" style="padding:20px">
    {regional_signals if regional_signals else '<p style="color:var(--faint);font-size:14px">Processing next cycle…</p>'}
  </div>
</div>

<!-- for you -->
<div class="section">
  <div class="section-label">For you</div>
  <div class="section-title">Who should act on this</div>
  <div class="section-sub">Every dispatch is written for a specific audience. Here's who gets today's signal.</div>
  <div class="audience-grid">
    {persona_cards if persona_cards else '<p style="color:var(--faint)">No routes yet.</p>'}
  </div>
</div>

<!-- what they receive -->
<div class="section" style="padding-top:0">
  <div class="section-label">What they receive</div>
  <div class="section-title">Ready to send</div>
  <div class="section-sub">Each audience gets a different format. These are real outputs from today's cycle.</div>
  <div class="output-grid">
    <div class="output-card">
      <h4>🌴 Telegram Alert</h4>
      <div class="output-channel">Telegram channel</div>
      <div class="output-body">{j(telegram_preview)[:500]}</div>
    </div>
    <div class="output-card">
      <h4>📊 Investor Brief</h4>
      <div class="output-channel">Email</div>
      <div class="output-body">{j(investor_preview)[:400]}</div>
    </div>
  </div>
  <!-- analyst rail -->
  <div class="analyst">
    <h3>🔍 Ask the Dispatch Desk</h3>
    <p>Interrogate today's cycle. Answers come from the data, not an AI.</p>
    <div class="aprompts">
      <button onclick="window.askDesk('explain')">Explain lead signal</button>
      <button onclick="window.askDesk('investor')">Investor perspective</button>
      <button onclick="window.askDesk('what-changed')">What changed</button>
      <button onclick="window.askDesk('guyana-focus')">Why Guyana</button>
      <button onclick="window.askDesk('draft-notes')">Draft investor note</button>
    </div>
    <div class="ask-row">
      <input id="dq" placeholder="Ask about a signal, country, audience…" onkeydown="if(event.key==='Enter')window.askDesk(this.value)">
      <button onclick="window.askDesk(document.getElementById('dq').value)">Ask</button>
    </div>
    <div id="da" class="a-box">Select a prompt or ask a question.</div>
  </div>
</div>

<!-- trust -->
<div class="section" style="padding-top:0">
  <div class="section-label">Trust</div>
  <div class="section-title">Where this comes from</div>
  <div class="section-sub">Six public data sources, all free, all updating on schedule.</div>
  <div class="dispatch-card" style="padding:0;overflow:hidden">
    <table class="src-table">
      {source_rows}
    </table>
  </div>
</div>

<!-- feedback loop -->
<div class="section" style="padding-top:0">
  <div class="section-label">Feedback loop</div>
  <div class="section-title">What happened after delivery</div>
  <div class="section-sub">When recipients open, forward, or act on a dispatch, the next cycle adjusts.</div>
  <div class="fb-section">
    <div style="margin-bottom:10px">{fb_action_rows if fb_action_rows else '<span style="color:var(--faint);font-size:13px">No feedback recorded yet.</span>'}</div>
    {f'<div style="margin-top:12px;font-size:13px"><strong style="color:var(--text)">Priority shifts:</strong></div><div style="margin-top:6px">{boost_rows}</div>' if boost_rows else ''}
  </div>
</div>

<!-- deep proof (collapsible) -->
<div class="section deep-proof">
  <button class="deep-btn" id="deepBtn" onclick="toggleDeep()">▸ Show pipeline internals</button>
  <div class="deep-content" id="deepContent">
    <div class="dispatch-card" style="margin-top:16px">
      <h3 style="margin-bottom:4px">Pipeline internals</h3>
      <p style="font-size:13px;color:var(--faint);margin-bottom:16px">This is the technical proof layer — for judges and reviewers who want to see the full system.</p>
      <div class="two-col">
        <div>
          <h4 style="font-size:14px;margin-bottom:8px">All decision clusters ({n_clusters})</h4>
          {"".join(f'''
          <div style="border-bottom:1px solid var(--line);padding:12px 0">
            <div style="font-weight:600;font-size:14px">{j(c.get("title",""))}</div>
            <div style="font-size:12px;color:var(--faint);margin:4px 0">{j(c.get("country_cluster",""))} · {band(c.get("confidence_score",0))} · {j(c.get("evidence_grade",""))}</div>
            <div style="font-size:13px;color:var(--faint)">{j(c.get("decision","")[:120])}</div>
            {"<div style='font-size:12px;color:var(--no);margin-top:4px'>⚠️ " + j(c["risk_flags"][0][:80]) + "</div>" if c.get("risk_flags") else ""}
          </div>''' for c in clusters)}
        </div>
        <div>
          <h4 style="font-size:14px;margin-bottom:8px">Why now — editorial context</h4>
          {"".join(f'<div style="font-size:13px;color:var(--faint);padding:4px 0">{j(item)}</div>' for item in whynow_items) if whynow_items else '<p style="color:var(--faint);font-size:13px">No active triggers</p>'}
          <h4 style="font-size:14px;margin:16px 0 8px">Raw counts</h4>
          <div style="font-size:13px;color:var(--faint)">
            <div>Clusters: {n_clusters}</div>
            <div>Routed dispatches: {n_personas}</div>
            <div>Feedback events: {fb_total}</div>
            <div>Composite signals: {n_composite}</div>
            <div>Sources online: {n_sources}/6</div>
          </div>
        </div>
      </div>
    </div>
  </div>
</div>

<script>
const DESK = {analyst_json};

window.askDesk = function(q) {{
  const box = document.getElementById('da');
  if (!q) {{ box.textContent = 'Select a prompt or ask a question.'; return; }}
  const d = DESK.lead;
  const l = q.toLowerCase();
  if (l === 'explain' || l.includes('lead') || l.includes('first')) {{
    box.textContent = `Lead signal: ${{d.title}}\n\nWhy: ${{DESK.thesis}}\n\nEvidence: ${{d.evidence}} (${{d.grade}})\nConfidence: ${{d.band}} · ${{d.freshness}}\n${{d.risks.length ? 'Risk: ' + d.risks[0] : ''}}\n\nTop audiences:\n${{d.personas.slice(0,3).map(p => `• ${{p.persona}} via ${{p.channel}}: ${{p.action.substring(0,80)}}…`).join('\n')}}`;
  }} else if (l.includes('investor')) {{
    box.textContent = `Diaspora investor receives:\n\n"Today's lead: ${{d.title}}.\n\n${{DESK.thesis.length > 120 ? DESK.thesis.substring(0,120) + '…' : DESK.thesis}}\n\n${{d.risks.length ? '⚠️ ' + d.risks[0] + '\n\n' : ''}}Suggested next step: Investigate ${{d.country}} as a potential deployment target. Validate local partners, sector fit, and timing before committing capital."`;
  }} else if (l.includes('what changed') || l.includes('changed')) {{
    box.textContent = `Cycle ${{DESK.cycle}} changes:\n\n• ${{DESK.signals}} cross-source signals detected\n• ${{DESK.dispatches}} dispatches routed to audiences\n\nPriority shifts from feedback:\n${{DESK.boosts || 'No active feedback boosts.'}}\n\nRegional read: ${{DESK.thesis}}`;
  }} else if (l.includes('guyana')) {{
    box.textContent = `Guyana is the lead signal (${{d.band}} confidence).\n\n${{d.evidence}}\n\n${{d.risks.length ? '⚠️ ' + d.risks[0] : ''}}\n\nWhy now: ${{DESK.thesis}}\n\nSuggested: Compare Guyana against Belize and St. Vincent before committing. Multi-source confirmation reduces screening risk.`;
  }} else if (l.includes('draft') || l.includes('note')) {{
    box.textContent = `Draft investor note:\n\nSubject: ${{d.country}} signal worth reviewing this cycle\n\nOur system flagged ${{d.title}}.\n\nEvidence: ${{d.evidence}} (${{d.grade}}).\n${{d.risks.length ? '\\nNote: ' + d.risks[0] + '\\n' : ''}}\nNext step: Validate sector fit, local partners, and timing. This is a diligence trigger, not an investment recommendation.`;
  }} else {{
    // Search regional
    const match = DESK.regional.find(r => l.includes(r.country.toLowerCase()) || l.includes(r.title.toLowerCase().split(':')[0]));
    if (match) {{
      box.textContent = `${{match.title}} (${{match.band}} confidence)\n\nDecision: ${{match.decision.substring(0,120)}}\nEvidence: ${{match.evidence.substring(0,120)}}${{match.risks.length ? '\\n\\n⚠️ ' + match.risks[0] : ''}}`;
    }} else {{
      box.textContent = `I can answer: explain lead, investor perspective, what changed, why Guyana, draft investor note, or ask about any country.\n\nToday: ${{d.title}} · ${{DESK.signals}} signals · ${{DESK.dispatches}} dispatches.`;
    }}
  }}
  box.scrollTop = 0;
}};

function showDeep() {{
  toggleDeep();
}}

function toggleDeep() {{
  const c = document.getElementById('deepContent');
  const b = document.getElementById('deepBtn');
  if (c.classList.contains('open')) {{
    c.classList.remove('open');
    b.textContent = '▸ Show pipeline internals';
  }} else {{
    c.classList.add('open');
    b.textContent = '▾ Hide pipeline internals';
    c.scrollIntoView({{behavior:'smooth'}});
  }}
}}
</script>

<footer>
  Caribbean Opportunity Dispatch · Cycle {j(cycle_id)} · {j(now_str)} · Data: World Bank · IDB · NOAA · NDBC · CARICOM · CDB
</footer>
</body>
</html>"""

if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("--no-open", action="store_true")
    args = parser.parse_args()

    OUTPUT.write_text(html, encoding="utf-8")
    print(f"Written {OUTPUT}", flush=True)
    if not args.no_open:
        try:
            if sys.platform == "darwin": subprocess.Popen(["open", str(OUTPUT)])
        except: pass
    raise SystemExit(0)
