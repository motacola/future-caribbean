"""Generate dashboard.html from template + live data."""
from __future__ import annotations
import argparse, json, re, subprocess, sys
from datetime import datetime, timezone
from pathlib import Path

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
    except: return "──"

# ── Label rewriter: pipeline internals → user-facing ────────

def clean_title(raw: str) -> str:
    """Turn 'Guyana: +860.3% multi-source capital surge — market entry window open' → 'Guyana leads today's Caribbean capital momentum signal'"""
    # Extract country
    country = raw.split(":")[0].strip() if ":" in raw else "Caribbean"
    # Check for risk flags to adjust wording
    return f"{country} leads today's Caribbean capital momentum signal"

def clean_grade(raw: str) -> str:
    """Turn 'A - multi-source' → 'High confidence, supported by multiple sources'"""
    if "multi-source" in raw.lower() or raw.startswith("A"):
        return "High confidence · Supported by multiple sources"
    if "cross-source" in raw.lower() or raw.startswith("B"):
        return "Moderate confidence · Supported by multiple sources"
    if raw.startswith("C"):
        return "Early signal · Single source"
    return "Exploratory"

def clean_evidence(raw: str) -> str:
    """Turn 'WB FDI surge detected: Guyana' → cleaner version"""
    raw = re.sub(r"WB\s+", "World Bank ", raw)
    raw = re.sub(r"detected:\s*", "data shows: ", raw)
    raw = re.sub(r"FDI surge", "FDI movement", raw)
    return raw

def clean_signal_title(raw: str) -> str:
    """Turn internal signal titles into user-facing country summaries"""
    country = raw.split(":")[0].strip() if ":" in raw else "Caribbean"
    if "%" in raw:
        # Extract the percentage
        pct = re.search(r"([+\-]?\d+\.?\d*)%", raw)
        pct_str = pct.group(1) + "%" if pct else ""
        return f"{country}: capital momentum signal ({pct_str})"
    return f"{country} opportunity signal"

# ── Load data ──────────────────────────────────────────────

desk = read_json(ROOT / "outbox" / "dispatch_desk.json") or {}
clusters = desk.get("clusters", []) or []
lead = clusters[0] if clusters else {}

# ── Lead signal: rewrite all labels for user-facing view ───

l_country = lead.get("country_cluster", "Guyana")
l_title = clean_title(lead.get("title", ""))                    # "Guyana leads today's Caribbean capital momentum signal"
l_evidence = clean_evidence(lead.get("evidence", ""))            # "World Bank FDI movement: Guyana"
l_decision = lead.get("decision", "Where to investigate capital deployment or partnership entry")
l_score = lead.get("confidence_score", 0)
l_grade = clean_grade(lead.get("evidence_grade", ""))          # "High confidence, supported by multiple sources"
l_fresh = lead.get("freshness", "")
l_risks = lead.get("risk_flags", []) or []
# Extract percentage for context display
lead_pct = re.search(r"([+\-]?\d+\.?\d*)%", lead.get("title",""))
lead_pct_str = lead_pct.group(1) + "%" if lead_pct else ""

# ── Persona cards ──────────────────────────────────────────
pcards = []
seen = set()
for c in clusters:
    for p in c.get("personas", []) or []:
        name = p.get("persona", "")
        if name in seen: continue
        seen.add(name)
        ch = p.get("channel", "")
        act = (p.get("action", "") or "")[:100]
        pcards.append((name, ch, act))
    if len(pcards) >= 5: break

pcard_html = ""
for idx, (name, ch, act) in enumerate(pcards, 1):
    pcard_html += f'''
    <div class="aud">
      <div class="aud-num">{idx:02d}</div>
      <div class="aud-name">{j(name)}</div>
      <div class="aud-ch">{j(ch)}</div>
      <p class="aud-act">{j(act)}</p>
    </div>'''

# ── Sources ────────────────────────────────────────────────
SRC = [
    ("World Bank Indicators","world_bank","REST API · 5 indicators × 13 countries"),
    ("IDB Open Data","idb","CKAN API · Regional project datasets"),
    ("NOAA Weather Alerts","noaa","NWS API · Active hazard alerts"),
    ("NDBC Marine Buoys","ndbc","Marine conditions · 6 buoys"),
    ("CARICOM Statistics","tier2","WordPress REST · 126 datasets"),
    ("CDB Procurement Feed","tier2","RSS · Project & procurement notices"),
]
src_rows = ""
n_sources = 0
for label, key, desc in SRC:
    d = read_json(ROOT / "data" / key / "latest.json")
    ok = d is not None
    if ok: n_sources += 1
    a = age(d.get("fetched_at") if d else None)
    dot = "●" if ok else "○"
    cls = "src-ok" if ok else "src-off"
    src_rows += f'<tr class="{cls}"><td><span class="dot">{dot}</span> {j(label)}</td><td>{j(desc)}</td><td>{"Live" if ok else "Offline"}</td></tr>'

# ── Secondary signals (clean titles) ───────────────────────
sec_signals = ""
for c in clusters[1:5]:
    ct = clean_signal_title(c.get("title", ""))
    cc = c.get("country_cluster", "")
    risk_html = ""
    if c.get("risk_flags"):
        risk_html = f'<span class="risk-tag">⚠️ {j(c["risk_flags"][0][:50])}</span>'
    sec_signals += f'''
    <div class="sig-row">
      <div class="sig-main"><strong>{j(ct)}</strong><div class="sig-loc">{j(cc)}</div></div>
      {risk_html}
    </div>'''

# ── Feedback: product view hides "ignored" ─────────────────
fb = read_json(ROOT / "data" / "feedback" / "state.json") or {}
fb_hist = fb.get("history", []) or []
fb_boosts = fb.get("boosts", {})
fb_actions: dict[str, int] = {}
for e in fb_hist:
    s = e.get("feedback_status", "unknown")
    fb_actions[s] = fb_actions.get(s, 0) + 1

# Product view: only actionable responses (no "ignored")
fb_action_pills = ""
for act, cnt in sorted([(a, c) for a, c in fb_actions.items() if a != "ignored"], key=lambda x: -x[1]):
    icons = {"forwarded": "📤", "replied": "💬", "opened": "👁", "decision_changed": "🔀"}
    fb_action_pills += f'<span class="fb-pill">{icons.get(act,"•")} {act.replace("_"," ").title()}: {cnt}</span>'

# Audit view: all responses including ignored
fb_all_pills = ""
for act, cnt in sorted(fb_actions.items(), key=lambda x: -x[1]):
    icons = {"forwarded": "📤", "replied": "💬", "opened": "👁", "decision_changed": "🔀", "ignored": "—"}
    fb_all_pills += f'<span class="fb-pill">{icons.get(act,"•")} {act.replace("_"," ").title()}: {cnt}</span>'

# Boost lines (cleaned)
boost_lines = ""
for kind, countries in fb_boosts.items():
    for country, val in countries.items():
        if val != 0:
            sign = "+" if val > 0 else ""
            boost_lines += f'<div class="boost-line">{j(country)} {j(kind.replace("_"," "))}: {sign}{val}</div>'

# ── Thesis ─────────────────────────────────────────────────
thesis = read_text(ROOT / "outbox" / "regional_thesis.md")
thesis_line = next((l.strip() for l in thesis.split("\n")
                    if l.strip() and not l.startswith("#") and not l.startswith("**")
                    and not l.startswith("Generated") and len(l.strip()) > 20), "")

# ── Why now ────────────────────────────────────────────────
whynow_items = []
for line in read_text(ROOT / "outbox" / "why_now.md").split("\n"):
    line = line.strip()
    if line.startswith(("🟢", "🔴", "🟡")):
        whynow_items.append(line[:100])

# ── Counts ─────────────────────────────────────────────────
n_clusters = len(clusters)
n_composite = len((read_json(ROOT / "data" / "composite" / "latest.json") or {}).get("signals", []) or [])
n_personas = desk.get("dispatch_count", 0)
n_fb = len(fb_hist)
cycle_id = desk.get("cycle_id", "—")
now_str = datetime.now(timezone.utc).strftime("%B %d, %Y at %H:%M UTC")

# ── Analyst JS data ────────────────────────────────────────
analyst_data = {
    "cycle": cycle_id,
    "lead": {
        "title": l_title, "country": l_country,
        "evidence": l_evidence, "decision": l_decision,
        "pct": lead_pct_str, "risks": l_risks,
        "personas": [{"persona": p[0], "channel": p[1], "action": p[2]} for p in pcards[:4]],
    },
    "thesis": thesis_line[:300],
    "sources": n_sources, "signals": n_composite, "dispatches": n_personas,
}
aj = json.dumps(analyst_data, ensure_ascii=False).replace("</", "<\\/")

# ── All clusters for audit (clean titles + clean grades) ───
all_clusters_html = ""
for i, c in enumerate(clusters, 1):
    ct = clean_signal_title(c.get("title", ""))
    cc = c.get("country_cluster", "")
    cg = clean_grade(c.get("evidence_grade", ""))
    cf = c.get("freshness", "")
    cd = (c.get("decision", "") or "")[:100]
    ce = clean_evidence(c.get("evidence", ""))
    cr = c.get("risk_flags", []) or []
    cr_html = f'<div class="risk-inline">⚠️ {j(cr[0][:80])}</div>' if cr else ""
    routes_html = ""
    for r in (c.get("personas", []) or [])[:3]:
        routes_html += f'<div class="route-line"><span>{j(r.get("persona",""))}</span> <span>{j(r.get("channel",""))}</span></div>'
    all_clusters_html += f'''
    <div class="cluster-card">
      <div class="cnum">{i:02d}</div>
      <div class="cbody">
        <h4>{j(ct)}{" · " + j(cc) if cc else ""}</h4>
        <div class="conf-badge conf-high">{j(cg)} · {j(cf)}</div>
        <p><strong>Decision:</strong> {j(cd)}</p>
        <p><strong>Evidence:</strong> {j(ce)}</p>
        {cr_html}
        <div class="croutes">{routes_html}</div>
      </div>
    </div>'''

# ── Render dashboard (system audit page) ───────────────────
template = Path(ROOT / "dashboard" / "template.html").read_text()

V = dict(
    n_sources=n_sources, n_clusters=n_clusters, n_composite=n_composite,
    n_personas=n_personas, n_fb=n_fb,
    cycle_id=j(cycle_id), now_str=j(now_str),
    l_title=j(l_title), l_country=j(l_country),
    l_evidence=j(l_evidence), l_decision=j(l_decision),
    l_grade=j(l_grade), lead_pct=j(lead_pct_str),
    l_risks_json=json.dumps(l_risks, ensure_ascii=False),
    pcard_html=pcard_html,
    sec_html=sec_signals if sec_signals else '<p class="muted">No additional signals</p>',
    src_rows=src_rows,
    fb_html=fb_action_pills if fb_action_pills else '<span class="muted">No delivery responses yet</span>',
    fb_all_html=fb_all_pills if fb_all_pills else '<span class="muted">No feedback</span>',
    boost_html=f'<div style="margin-top:10px">{boost_lines}</div>' if boost_lines else "",
    all_clusters_html=all_clusters_html,
    whynow_html="".join(f"<li>{j(item)}</li>" for item in whynow_items) if whynow_items else "<li>No active seasonal triggers</li>",
    aj=aj,
)

for k, val in V.items():
    template = template.replace("{{" + k + "}}", str(val))

OUT = ROOT / "dashboard.html"
OUT.write_text(template, encoding="utf-8")
print(f"Written {OUT}", flush=True)

# ── Render configurator (Signal Builder homepage) ───────────
# Build source rows for proof panel (compact version)
proof_src_rows = ""
for label, key, desc in SRC:
    d = read_json(ROOT / "data" / key / "latest.json")
    ok = d is not None
    dot_cls = "src-ok" if ok else "src-off"
    status = "Live" if ok else "Offline"
    proof_src_rows += (
        f'<div class="src-row">'
        f'<span><span class="src-dot {dot_cls}"></span>{label}</span>'
        f'<span style="font-size:12px;color:var(--{"teal" if ok else "muted"})">{status}</span>'
        f'</div>'
    )

# Embed all cluster data as JSON for client-side filtering/fallback
conf_data = {
    "clusters": clusters,
    "n_sources": n_sources,
    "n_clusters": n_clusters,
    "n_personas": n_personas,
    "cycle_id": cycle_id,
}
conf_json_str = json.dumps(conf_data, ensure_ascii=False).replace("</", "<\\/")

conf_template = Path(ROOT / "dashboard" / "configurator_template.html").read_text()
CV = dict(
    n_sources=n_sources,
    n_clusters=n_clusters,
    n_personas=n_personas,
    cycle_id=j(cycle_id),
    now_str=j(now_str),
    proof_src_rows=proof_src_rows,
    conf_json=conf_json_str,
)
for k, val in CV.items():
    conf_template = conf_template.replace("{{" + k + "}}", str(val))

CONF_OUT = ROOT / "configurator.html"
CONF_OUT.write_text(conf_template, encoding="utf-8")
print(f"Written {CONF_OUT}", flush=True)

if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("--no-open", action="store_true")
    args = parser.parse_args()
    if not args.no_open:
        try:
            if sys.platform == "darwin": subprocess.Popen(["open", str(CONF_OUT)])
        except: pass
