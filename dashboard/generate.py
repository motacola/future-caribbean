"""Generate dashboard.html from template + live data."""
from __future__ import annotations
import argparse, json, re, subprocess, sys
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parents[1]

def j(v): return json.dumps(str(v), ensure_ascii=False)[1:-1]

def read_json(p: Path) -> dict | None:
    if not p.exists(): return None
    try: return json.loads(p.read_text())
    except: return None

def read_text(p: Path) -> str:
    if not p.exists(): return ""
    return p.read_text("utf-8", errors="replace")

def age(ts):
    if not ts: return "—"
    try:
        m = int((datetime.now(timezone.utc) - datetime.fromisoformat(ts.replace("Z","+00:00"))).total_seconds()/60)
        if m < 2: return "just now"
        if m < 60: return f"{m}m ago"
        h = m // 60
        if h < 24: return f"{h}h ago"
        return f"{h//24}d ago"
    except: return "—"

# ── Load data ──────────────────────────────────────────────

desk = read_json(ROOT / "outbox" / "dispatch_desk.json") or {}
clusters = desk.get("clusters", []) or []
lead = clusters[0] if clusters else {}

# Persona cards — use lead cluster personas, fill from others if needed
pcards = []
seen = set()
for c in clusters:
    for p in c.get("personas", []) or []:
        name = p.get("persona","")
        if name in seen: continue
        seen.add(name)
        ch = p.get("channel","")
        act = (p.get("action","") or "")[:110]
        fb = str(p.get("feedback_status","")).replace("_"," ").title()
        pcards.append((name, ch, act, fb))
    if len(pcards) >= 5: break

# Sources
SRC = [
    ("World Bank Indicators","world_bank","REST API · 5 indicators × 13 countries"),
    ("IDB Open Data","idb","CKAN API · Regional project datasets"),
    ("NOAA Weather Alerts","noaa","NWS API · Active hazard alerts"),
    ("NDBC Marine Buoys","ndbc","Marine conditions · 6 buoys"),
    ("CARICOM Statistics","tier2","WordPress REST · 126 datasets"),
    ("CDB Procurement Feed","tier2","RSS · Project & procurement notices"),
]

# Thesis
thesis = read_text(ROOT / "outbox" / "regional_thesis.md")
thesis_line = next((l.strip() for l in thesis.split("\n") if l.strip() and not l.startswith("#") and not l.startswith("**") and not l.startswith("Generated")), "")

# Feedback
fb = read_json(ROOT / "data" / "feedback" / "state.json") or {}
fb_hist = fb.get("history",[]) or []
fb_boosts = fb.get("boosts",{})
fb_actions: dict[str,int] = {}
for e in fb_hist:
    s = e.get("feedback_status","unknown"); fb_actions[s] = fb_actions.get(s,0) + 1
# Only show actionable feedback (no "ignored" in product view)
fb_action_pills = ""
for act,cnt in sorted([(a,c) for a,c in fb_actions.items() if a != "ignored"], key=lambda x: -x[1]):
    icons = {"forwarded":"📤","replied":"💬","opened":"👁","decision_changed":"🔀"}
    fb_action_pills += f'<span class="fb-pill">{icons.get(act,"•")} {act.replace("_"," ").title()}: {cnt}</span>'

boost_lines = ""
for kind,countries in fb_boosts.items():
    for country,val in countries.items():
        if val != 0:
            sign = "+" if val > 0 else ""
            boost_lines += f'<div class="boost-line">{j(country)} {j(kind.replace("_"," "))}: {sign}{val}</div>'

# Secondary signals
sec_signals = ""
for c in clusters[1:5]:
    ct = c.get("title",""); cc = c.get("country_cluster","")
    risk_tag = ""
    if c.get("risk_flags"):
        risk_tag = f'<span class="risk-tag">⚠️ {j(c["risk_flags"][0][:50])}</span>'
    sec_signals += f'''
    <div class="signal-row">
      <div><strong>{j(ct)}</strong><div class="signal-loc">{j(cc)}</div></div>
      {risk_tag}
    </div>'''

# Source rows
src_rows = ""
n_sources = 0
for label,key,desc in SRC:
    d = read_json(ROOT / "data" / key / "latest.json")
    ok = d is not None
    if ok: n_sources += 1
    a = age(d.get("fetched_at") if d else None)
    dot = "●" if ok else "○"
    cls = "src-ok" if ok else "src-off"
    src_rows += f'<tr class="{cls}"><td><span class="dot">{dot}</span> {j(label)}</td><td>{j(desc)}</td><td>{j(a)}</td></tr>'

# Counts
n_clusters = len(clusters)
n_composite = len((read_json(ROOT / "data" / "composite" / "latest.json") or {}).get("signals",[]) or [])
n_personas = desk.get("dispatch_count", 0)
n_fb = len(fb_hist)

# Cycle
cycle_id = desk.get("cycle_id","—")
now_str = datetime.now(timezone.utc).strftime("%B %d, %Y — %H:%M UTC")

# Lead signal fields
l_title = lead.get("title","")
l_country = lead.get("country_cluster","Caribbean")
l_evidence = lead.get("evidence","")
l_decision = lead.get("decision","")
l_score = lead.get("confidence_score",0)
l_grade = lead.get("evidence_grade","")
l_risks = lead.get("risk_flags",[]) or []

# Build analyst data for JS
analyst_data = {
    "cycle": cycle_id,
    "lead": {
        "title": l_title, "country": l_country,
        "evidence": l_evidence, "decision": l_decision,
        "risks": l_risks,
        "personas": [{"persona":p[0],"channel":p[1],"action":p[2]} for p in pcards[:4]],
    },
    "thesis": thesis_line[:300],
    "sources": n_sources, "signals": n_composite, "dispatches": n_personas,
}
aj = json.dumps(analyst_data, ensure_ascii=False).replace("</", "<\\/")

# ── Build persona card HTML ────────────────────────────────
pcard_html = ""
for name,ch,act,fb in pcards:
    pcard_html += f'''
    <div class="aud-card">
      <div class="aud-name">{j(name)}</div>
      <div class="aud-channel">{j(ch)}</div>
      <p class="aud-action">{j(act)}</p>
      <div class="aud-status">Last delivery: {j(fb)}</div>
    </div>'''

# ── Secondary signals HTML (if any) ────────────────────────
sec_html = sec_signals if sec_signals else '<p class="muted">No additional signals</p>'

# ── Feedback HTML (product view — no ignored count) ───────
fb_html = fb_action_pills if fb_action_pills else '<span class="muted">No delivery responses yet</span>'
boost_html = f'<div style="margin-top:10px">{boost_lines}</div>' if boost_lines else ''

# ── Build the page ─────────────────────────────────────────

# Prepare template vars as simple strings to avoid f-string brace issues
vars_dict = dict(
    j=j, cycle_id=j(cycle_id), now_str=j(now_str),
    n_sources=n_sources, n_clusters=n_clusters, n_composite=n_composite,
    n_personas=n_personas, n_fb=n_fb,
    l_title=j(l_title), l_country=j(l_country),
    l_evidence=j(l_evidence), l_decision=j(l_decision),
    l_grade=j(l_grade),
    thesis_line=j(thesis_line[:280]),
    l_risks_json=json.dumps(l_risks, ensure_ascii=False),
    pcard_html=pcard_html,
    sec_html=sec_html,
    src_rows=src_rows,
    fb_html=fb_html,
    boost_html=boost_html,
    aj=aj,
)

# Substitute {{var}} placeholders in template
template = Path(ROOT / "dashboard" / "template.html").read_text()
def render(t, v):
    for k, val in v.items():
        t = t.replace("{{"+k+"}}", str(val))
    return t

html = render(template, vars_dict)

OUT = ROOT / "dashboard.html"
OUT.write_text(html, encoding="utf-8")
print(f"Written {OUT}", flush=True)

if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("--no-open", action="store_true")
    args = parser.parse_args()
    if not args.no_open:
        try:
            if sys.platform == "darwin": subprocess.Popen(["open", str(OUT)])
        except: pass
