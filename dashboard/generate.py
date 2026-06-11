"""Generate dashboard.html from template + live data."""
from __future__ import annotations
import argparse, json, re, subprocess, sys
from datetime import datetime, timezone
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from map_data import build_map_data, canonical_country

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
    return f"All signals point to {country}."

def clean_grade(raw: str) -> str:
    """Turn 'A - multi-source' → 'High confidence, supported by multiple sources'"""
    if "multi-source" in raw.lower() or raw.startswith("A"):
        return "Solid — several sources agree"
    if "cross-source" in raw.lower() or raw.startswith("B"):
        return "Promising — more than one source"
    if raw.startswith("C"):
        return "Early — one source so far"
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
        return f"{country} — money on the move ({pct_str})"
    return f"{country} — early signal"

# ── Load data ──────────────────────────────────────────────

desk = read_json(ROOT / "outbox" / "dispatch_desk.json") or {}
clusters = desk.get("clusters", []) or []
lead = clusters[0] if clusters else {}
dispatch_data = read_json(ROOT / "outbox" / "opportunity_dispatches.json") or {}
dispatches = dispatch_data.get("dispatches", []) or []
map_data = build_map_data(ROOT)

# Real coordinates (country centroid / capital region) for the Leaflet map
COUNTRY_COORDS = {
    "Bahamas": (24.70, -77.80),
    "Belize": (17.25, -88.76),
    "Jamaica": (18.11, -77.30),
    "Haiti": (18.97, -72.69),
    "Dominican Republic": (18.79, -70.16),
    "Puerto Rico": (18.22, -66.42),
    "Antigua & Barbuda": (17.08, -61.80),
    "St Lucia": (13.91, -60.98),
    "Barbados": (13.16, -59.55),
    "Grenada": (12.11, -61.68),
    "Trinidad & Tobago": (10.46, -61.25),
    "Guyana": (4.86, -58.93),
    "Suriname": (3.92, -56.03),
}

map_markers = []
for entry in map_data:
    lat, lng = COUNTRY_COORDS[entry["country"]]
    map_markers.append({
        "country": entry["country"],
        "lat": lat,
        "lng": lng,
        "confidence": entry["confidence"],
        "kind": entry["kind"],
        "summary": entry["top_signal_summary"],
    })
map_markers_json = json.dumps(map_markers, ensure_ascii=False).replace("</", "<\\/")

map_dispatches: dict[str, list[dict]] = {country: [] for country in COUNTRY_COORDS}
for dispatch in dispatches:
    country = canonical_country(dispatch.get("country_cluster", ""))
    if country in map_dispatches:
        map_dispatches[country].append({
            "dispatch_id": dispatch.get("dispatch_id"),
            "title": dispatch.get("title", ""),
            "recommended_action": dispatch.get("recommended_action", ""),
            "confidence_score": dispatch.get("confidence_score", 0),
            "signal_kind": dispatch.get("signal_kind", ""),
            "persona_label": dispatch.get("persona_label", ""),
        })
map_dispatches_json = json.dumps(map_dispatches, ensure_ascii=False).replace("</", "<\\/")

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

# ── Lead decision workspace ───────────────────────────────
lead_dispatches = [
    d for d in dispatches
    if d.get("country_cluster") == l_country and d.get("signal_kind") == lead.get("signal_kind")
]
lead_dispatch = next(
    (d for d in lead_dispatches if d.get("persona_key") == "diaspora_investor"),
    lead_dispatches[0] if lead_dispatches else {},
)
lead_action = lead_dispatch.get(
    "recommended_action",
    "Validate sector fit, local partners, and timing before advancing this opportunity.",
)
lead_window = lead_dispatch.get("action_window", "14 days")
lead_owner = lead_dispatch.get("persona_label", "Diaspora Investor")
lead_dispatch_id = lead_dispatch.get("dispatch_id", lead.get("cluster_id", "lead-dispatch"))
lead_delivery = lead_dispatch.get("delivery_status", "queued").replace("_", " ").title()
lead_feedback = lead_dispatch.get("feedback_status", "awaiting").replace("_", " ").title()
lead_rationale = lead_dispatch.get(
    "routing_rationale",
    "This route matches a high-confidence signal to the person most likely to advance it.",
)

lead_routes_html = ""
for route in lead_dispatches[:3]:
    lead_routes_html += f'''
    <div class="route-lane">
      <div>
        <strong>{j(route.get("persona_label", "Decision-maker"))}</strong>
        <span>{j(route.get("channel", "Brief"))} · {j(route.get("action_window", "14 days"))}</span>
      </div>
      <p>{j(route.get("recommended_action", ""))}</p>
      <span class="route-state">{j(route.get("feedback_status", "awaiting").replace("_", " ").title())}</span>
    </div>'''

# ── All validation packs (indexed by signal_id for client-side expansion) ──
validation_packs_index = read_json(ROOT / "outbox" / "validation_packs" / "index.json") or {}
all_packs = {}
for entry in validation_packs_index.get("packs", []):
    sid = entry.get("signal_id")
    if not sid:
        continue
    safe = re.sub(r"[^A-Za-z0-9._-]", "-", sid)
    pack = read_json(ROOT / "outbox" / "validation_packs" / f"{safe}.json")
    if pack:
        all_packs[sid] = pack

# ── Lead validation pack (for backward compat with existing template) ──
vp_sid = lead_dispatch.get("signal_id", "")
vp_file = re.sub(r"[^A-Za-z0-9._-]", "-", vp_sid) if vp_sid else ""
vpack = all_packs.get(vp_sid) or (read_json(ROOT / "outbox" / "validation_packs" / f"{vp_file}.json") if vp_file else None)

validation_pack_html = ""
if vpack:
    verdict = vpack.get("advance_or_reject_recommendation", "hold")
    verdict_label = {"advance": "Advance", "hold": "Hold", "reject": "Reject"}.get(verdict, "Hold")

    hyp_lis = ""
    for h in (vpack.get("sector_hypotheses") or [])[:5]:
        hyp_lis += f'<li><strong>{j(h.get("sector",""))}</strong><em>{j(h.get("basis",""))}</em></li>'
    if not hyp_lis:
        hyp_lis = '<li>No sector hypotheses generated this cycle.</li>'

    proj_lis = ""
    for p in (vpack.get("supporting_projects") or [])[:4]:
        url = p.get("url", "")
        title = j(p.get("title", "")[:90])
        proj_lis += f'<li><a href="{j(url)}" target="_blank" rel="noopener">{title}</a><em>{j(p.get("source",""))}</em></li>' if url else f'<li>{title}</li>'
    if not proj_lis:
        proj_lis = '<li>No matched projects this cycle.</li>'

    proc_lis = ""
    for p in (vpack.get("procurement_matches") or [])[:4]:
        url = p.get("url", "")
        title = j(p.get("title", "")[:90])
        tag = f'<span class="vpack-tag">{j(p.get("match",""))}</span>'
        proc_lis += f'<li><a href="{j(url)}" target="_blank" rel="noopener">{title}</a>{tag}</li>' if url else f'<li>{title}{tag}</li>'
    if not proc_lis:
        proc_lis = '<li>No live procurement notices matched.</li>'

    intro_lis = ""
    for i in (vpack.get("recommended_intro_targets") or [])[:4]:
        intro_lis += f'<li><strong>{j(i.get("name",""))}</strong><em>{j(i.get("why",""))}</em></li>'
    if not intro_lis:
        intro_lis = '<li>No intro targets identified.</li>'

    q_lis = "".join(f'<li>{j(q)}</li>' for q in (vpack.get("unresolved_questions") or [])[:4])

    validation_pack_html = f'''
      <div class="vpack">
        <div class="vpack-head">
          <div>
            <span>Validation pack · auto-assembled this cycle</span>
            <h3>What the system already checked for {j(vpack.get("country", l_country))}</h3>
          </div>
          <span class="vpack-verdict {j(verdict)}">{j(verdict_label)}</span>
        </div>
        <div class="vpack-reason">{j(vpack.get("recommendation_reason", ""))}</div>
        <div class="vpack-grid">
          <div class="vpack-col"><h4>Sector hypotheses</h4><ul>{hyp_lis}</ul></div>
          <div class="vpack-col"><h4>Suggested first conversations</h4><ul>{intro_lis}</ul></div>
          <div class="vpack-col"><h4>Supporting projects &amp; data</h4><ul>{proj_lis}</ul></div>
          <div class="vpack-col"><h4>Procurement pipeline</h4><ul>{proc_lis}</ul></div>
        </div>
        <div class="vpack-questions"><h4>Still unresolved — what to validate this week</h4><ul>{q_lis}</ul></div>
      </div>'''

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

# ── Secondary signals (clean titles) with expandable validation ────
sec_signals = ""
advance_count = 0
hold_count = 0
reject_count = 0
for c in clusters[1:5]:
    ct = clean_signal_title(c.get("title", ""))
    cc = c.get("country_cluster", "")
    risk_html = ""
    if c.get("risk_flags"):
        risk_html = f'<span class="risk-tag">⚠️ {j(c["risk_flags"][0][:50])}</span>'
    
    # Get validation verdict for this signal
    sid = c.get("signal_id", "")
    verdict = "hold"  # default
    if sid and sid in all_packs:
        verdict = all_packs[sid].get("advance_or_reject_recommendation", "hold")
    
    if verdict == "advance":
        advance_count += 1
    elif verdict == "hold":
        hold_count += 1
    else:
        reject_count += 1
    
    # Build validation HTML if pack exists
    validation_html = ""
    if sid and sid in all_packs:
        pack = all_packs[sid]
        verdict_label = {"advance": "Advance", "hold": "Hold", "reject": "Reject"}.get(verdict, "Hold")
        
        # Sector hypotheses
        hyp_lis = ""
        for h in (pack.get("sector_hypotheses") or [])[:3]:
            basis = f'<em>{j(h.get("basis", ""))}</em>' if h.get("basis") else ""
            hyp_lis += f'<li><strong>{j(h.get("sector", ""))}</strong>{basis}</li>'
        if not hyp_lis:
            hyp_lis = '<li>No sector hypotheses this cycle.</li>'
        
        # Supporting projects
        proj_lis = ""
        for p in (pack.get("supporting_projects") or [])[:2]:
            url = p.get("url", "")
            title = j(p.get("title", "")[:80])
            proj_lis += f'<li><a href="{j(url)}" target="_blank" rel="noopener">{title}</a><em>{j(p.get("source", ""))}</em></li>' if url else f'<li>{title}</li>'
        if not proj_lis:
            proj_lis = '<li>No matched projects.</li>'
        
        # Procurement matches
        proc_lis = ""
        for p in (pack.get("procurement_matches") or [])[:2]:
            url = p.get("url", "")
            title = j(p.get("title", "")[:80])
            tag = f'<span class="vpack-tag">{j(p.get("match", ""))}</span>'
            proc_lis += f'<li><a href="{j(url)}" target="_blank" rel="noopener">{title}</a>{tag}</li>' if url else f'<li>{title}{tag}</li>'
        if not proc_lis:
            proc_lis = '<li>No procurement matches.</li>'
        
        validation_html = f'''
        <div class="sig-validation">
          <div class="sig-validation-inner">
            <div class="sig-validation-head">
              <span>Validation pack · auto-assembled this cycle</span>
              <h4>Evidence for {j(pack.get("country", cc))}</h4>
              <span class="sig-validation-verdict {j(verdict)}">{j(verdict_label)}</span>
            </div>
            <div class="sig-validation-grid">
              <div class="sig-validation-col"><h5>Sector hypotheses</h5><ul>{hyp_lis}</ul></div>
              <div class="sig-validation-col"><h5>Projects &amp; data</h5><ul>{proj_lis}</ul></div>
              <div class="sig-validation-col"><h5>Procurement pipeline</h5><ul>{proc_lis}</ul></div>
              <div class="sig-validation-col"><h5>Still unresolved</h5><ul>{"".join(f"<li>{j(q)}</li>" for q in (pack.get("unresolved_questions") or [])[:2]) or "<li>All questions resolved.</li>"}</ul></div>
            </div>
          </div>
        </div>'''
    
    sec_signals += f'''
    <div class="sig-row" data-verdict="{j(verdict)}" data-signal-id="{j(sid)}">
      <div class="sig-main"><strong>{j(ct)}</strong><div class="sig-loc">{j(cc)}</div></div>
      {risk_html}
      <span class="sig-expand" aria-label="Expand validation" title="View validation pack">▼</span>
      {validation_html}
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

# Verdict counts for filter bar
verdict_counts_json = json.dumps({
    "all": advance_count + hold_count + reject_count,
    "advance": advance_count,
    "hold": hold_count,
    "reject": reject_count,
}, ensure_ascii=False)

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

# ── Prepare all validation packs for client-side expansion ────
all_packs_json = json.dumps(all_packs, ensure_ascii=False).replace("</", "<\\/")

# ── Find latest replay JSONL for theater fallback ─────────────
history_dir = ROOT / "data" / "history"
replay_jsonl_url = ""
if history_dir.exists():
    jsonl_files = sorted(history_dir.glob("*.jsonl"), key=lambda p: p.stat().st_mtime, reverse=True)
    if jsonl_files:
        # Use the most recent file; Vercel serves data/history/ statically
        replay_jsonl_url = f"/data/history/{jsonl_files[0].name}"

# ── Render dashboard (system audit page) ───────────────────
template = Path(ROOT / "dashboard" / "template.html").read_text()

V = dict(
    n_sources=n_sources, n_clusters=n_clusters, n_composite=n_composite,
    n_personas=n_personas, n_fb=n_fb,
    cycle_id=j(cycle_id), now_str=j(now_str),
    l_title=j(l_title), l_country=j(l_country),
    l_evidence=j(l_evidence), l_decision=j(l_decision),
    l_grade=j(l_grade), lead_pct=j(lead_pct_str),
    lead_action=j(lead_action), lead_window=j(lead_window),
    lead_owner=j(lead_owner), lead_dispatch_id=j(lead_dispatch_id),
    lead_delivery=j(lead_delivery), lead_feedback=j(lead_feedback),
    lead_rationale=j(lead_rationale),
    lead_routes_html=lead_routes_html,
    validation_pack_html=validation_pack_html,
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
    map_markers_json=map_markers_json,
    map_dispatches_json=map_dispatches_json,
    all_packs_json=all_packs_json,
    verdict_counts_json=verdict_counts_json,
    replay_jsonl_url=j(replay_jsonl_url),
)

for k, val in V.items():
    template = template.replace("{{" + k + "}}", str(val))

OUT = ROOT / "dashboard.html"
template = "\n".join(line.rstrip() for line in template.splitlines()) + "\n"
OUT.write_text(template, encoding="utf-8")
print(f"Written {OUT}", flush=True)

# ── Signal Builder (configurator.html) ──────────────────────
# NOTE: configurator.html is a hand-maintained static page (the Signal
# Fabric engine UI: domain switcher, reasoning panel, deploy wizard,
# heartbeat). It pulls all live data from /api/* at runtime, so it is
# intentionally NOT regenerated here — doing so previously overwrote the
# engine features from a stale template. Leave it untouched.

if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("--no-open", action="store_true")
    args = parser.parse_args()
    if not args.no_open:
        try:
            if sys.platform == "darwin": subprocess.Popen(["open", str(CONF_OUT)])
        except: pass
