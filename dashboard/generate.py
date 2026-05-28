#!/usr/bin/env python3
"""Generate the Caribbean Opportunity Dispatch public dashboard.

Two views:
  1. User View (default) — product-first, narrative-led, judge-friendly
  2. Judge Audit (tabbed) — technical proof, pipeline health, data sources

Reads watcher data, outbox artifacts, and feedback state to render
a dense, utilitarian single-page console.
"""

from __future__ import annotations

import argparse
import html as html_lib
import json
import re
import subprocess
import sys
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parents[1]
OUTPUT = ROOT / "dashboard.html"

# ── Source watchers ────────────────────────────────────────

SOURCES = {
    "world_bank": {"label": "World Bank", "icon": "🏦", "path": "data/world_bank/latest.json"},
    "idb":        {"label": "IDB Open Data", "icon": "📊", "path": "data/idb/latest.json"},
    "noaa":       {"label": "NOAA Weather", "icon": "🌤", "path": "data/noaa/latest.json"},
    "ndbc":       {"label": "NDBC Buoys", "icon": "🌊", "path": "data/ndbc/latest.json"},
    "tier2":      {"label": "CARICOM + CDB", "icon": "🗃", "path": "data/tier2/latest.json"},
    "composite":  {"label": "Cross-Source Merger", "icon": "🧠", "path": "data/composite/latest.json"},
}


# ── Helpers ────────────────────────────────────────────────

def read_json(path: Path) -> dict | None:
    if not path.exists():
        return None
    try:
        return json.loads(path.read_text(encoding="utf-8"))
    except Exception:
        return None

def read_textfile(path: Path, max_lines: int = 40) -> str:
    if not path.exists():
        return ""
    try:
        lines = path.read_text(encoding="utf-8").splitlines()
        return "\n".join(lines[:max_lines])
    except Exception:
        return ""

def esc(value: Any) -> str:
    return html_lib.escape(str(value), quote=True)

def json_for_script(data: Any) -> str:
    text = json.dumps(data, ensure_ascii=False)
    return text.replace("</", "<\\/")

def clip(text: Any, limit: int = 180) -> str:
    value = " ".join(str(text or "").split())
    if len(value) <= limit:
        return value
    return value[: limit - 1].rsplit(" ", 1)[0].rstrip(".,;:") + "…"

def age_minutes(ts: str | None) -> str:
    if not ts:
        return "never"
    try:
        dt = datetime.fromisoformat(ts.replace("Z", "+00:00"))
        delta = datetime.now(timezone.utc) - dt
        mins = int(delta.total_seconds() / 60)
        if mins < 1: return "just now"
        if mins < 60: return f"{mins}m ago"
        hours = mins // 60
        if hours < 24: return f"{hours}h ago"
        return f"{hours // 24}d ago"
    except Exception:
        return "?"

def extract_watcher_stats(source_key: str, data: dict | None) -> dict:
    stats: dict[str, Any] = {"status": "offline" if data is None else "ok", "fetched_at": None, "summary": [], "count": 0}
    if data is None:
        stats["summary"].append("No data")
        return stats
    stats["fetched_at"] = data.get("fetched_at")
    if source_key == "world_bank":
        obs = data.get("observations", [])
        sigs = data.get("signals", [])
        countries = list(data.get("countries", {}).keys())
        stats["summary"] = [f"{len(obs)} observations", f"{len(countries)} countries", f"{len(sigs)} signals"]
        stats["count"] = len(obs)
    elif source_key == "idb":
        ds = data.get("datasets", [])
        stats["summary"] = [f"{len(ds)} datasets"]
        stats["count"] = len(ds)
    elif source_key == "noaa":
        alerts = data.get("alerts", [])
        total = data.get("total_active_alerts", len(alerts))
        stats["summary"] = [f"{total} active alerts"]
        stats["count"] = total
    elif source_key == "ndbc":
        readings = data.get("readings", [])
        sigs = data.get("signals_list", [])
        stats["summary"] = [f"{len(readings)} buoys", f"{len(sigs)} signals"]
        stats["count"] = len(readings)
    elif source_key == "tier2":
        items = data.get("items", [])
        stats["summary"] = [f"{len(items)} items"]
        stats["count"] = len(items)
    elif source_key == "composite":
        sigs = data.get("signals", [])
        stats["summary"] = [f"{len(sigs)} composite signals"]
        stats["count"] = len(sigs)
    return stats


# ── Confidence band mapper (Fix 10) ─────────────────────────

def confidence_band(score: int) -> tuple[str, str]:
    """Return (label, css_class) based on score."""
    if score >= 90: return ("High", "high")
    if score >= 70: return ("Moderate", "mod")
    if score >= 50: return ("Needs validation", "low")
    return ("Exploratory", "vlow")


# ── Main HTML generator ─────────────────────────────────────

def generate_html(
    watcher_stats: dict,
    thesis_text: str,
    whynow_text: str,
    telegram_brief_text: str,
    investor_brief_text: str,
    dispatch_summary: dict[str, Any],
    feedback: dict,
    persona_counts: dict[str, int],
    product_desk: dict | None = None,
    product_json: str = "",
) -> str:
    now = datetime.now(timezone.utc).strftime("%b %d, %Y at %H:%M UTC")
    product = product_desk or {}
    clusters = product.get("clusters", []) or []
    lead_cluster = clusters[0] if clusters else None

    # ── Summary counts ──────────────────────────────────────
    total_ok = sum(1 for s in watcher_stats.values() if s["status"] == "ok")
    total_sources = len(watcher_stats)
    composite_count = watcher_stats.get("composite", {}).get("count", 0)
    feedback_events = feedback.get("total_events", 0)
    feedback_actions = feedback.get("actions", {})
    action_icons = {"forwarded": "📤", "replied": "💬", "opened": "👁", "decision_changed": "🔀", "ignored": "—"}
    cycle_id = esc(product.get("cycle_id", "unknown"))

    # ── Lead signal hero (Fix 4) ────────────────────────────
    hero_html = ""
    if lead_cluster:
        title = esc(lead_cluster.get("title", "Untitled signal"))
        decision = esc(clip(lead_cluster.get("decision", "No decision recorded."), 160))
        evidence = esc(clip(lead_cluster.get("evidence", "No evidence recorded."), 140))
        score = lead_cluster.get("confidence_score", 0)
        band_label, band_class = confidence_band(score)
        grade = esc(lead_cluster.get("evidence_grade", ""))
        freshness = esc(lead_cluster.get("freshness", "unknown"))
        risks = lead_cluster.get("risk_flags", []) or []
        risk_html = ""
        if risks:
            risk_html = '<div class="risk-pill">⚠️ Risk: ' + esc(risks[0]) + '</div>'
        personas = lead_cluster.get("personas", [])[:3]
        persona_chips = ""
        for p in personas:
            persona_chips += '<span class="persona-chip">' + esc(p.get("persona", "")) + '</span> '
        country = esc(lead_cluster.get("country_cluster", "the region"))

        # Source context (Fix 7) — extract from evidence or signals
        source_hint = ""
        if "WB" in evidence or "World Bank" in evidence:
            source_hint = "Source: World Bank indicators"
        elif "CDB" in evidence or "CARICOM" in evidence:
            source_hint = "Source: CDB / CARICOM Statistics"

        hero_html = f'''
        <div class="hero-signal">
          <div class="hero-meta">LEAD SIGNAL · {cycle_id}</div>
          <h2>{title}</h2>
          <div class="hero-band {band_class}">{band_label} confidence · {grade} · {freshness}</div>
          <p class="hero-evidence"><strong>Evidence:</strong> {evidence}</p>
          <p class="hero-decision"><strong>Decision:</strong> {decision}</p>
          <p class="hero-source">{source_hint}</p>
          {risk_html}
          <div class="hero-personas">{persona_chips}</div>
        </div>'''
    else:
        hero_html = '<div class="hero-signal"><p>No signals yet — run the pipeline first.</p></div>'

    # ── Why it matters (Fix 7) ──────────────────────────────
    thesis_plain = ""
    for line in thesis_text.split("\n"):
        line = line.strip()
        if line and not line.startswith("#") and not line.startswith("**") and not line.startswith("-") and not line.startswith("Generated"):
            thesis_plain = esc(line[:300])
            break

    whynow_html = ""
    for line in whynow_text.split("\n"):
        line = line.strip()
        if line.startswith("🟢") or line.startswith("🔴") or line.startswith("🟡"):
            whynow_html += '<li>' + esc(line[:120]) + '</li>'

    # ── Who should act (Fix 5) ──────────────────────────────
    persona_action_html = ""
    seen_personas = set()
    for cluster in clusters[:6]:
        for route in (cluster.get("personas", []) or [])[:2]:
            pname = route.get("persona", "")
            if pname in seen_personas:
                continue
            seen_personas.add(pname)
            action = esc(clip(route.get("action", ""), 100))
            channel = esc(route.get("channel", ""))
            feedback_status = esc(str(route.get("feedback_status", "")).replace("_", " ").title())
            persona_action_html += f'''
            <div class="persona-card">
              <div class="pc-name">{esc(pname)}</div>
              <div class="pc-channel">{channel}</div>
              <p class="pc-action">{action}</p>
              <div class="pc-feedback">Feedback: {feedback_status}</div>
            </div>'''

    # ── Distribution proof (Fix 5) — show finished outputs ─
    telegram_preview = esc((telegram_brief_text or "").strip()[:1500] or "No Telegram output generated yet.")
    
    # Extract a short investor brief snippet
    investor_snippet = ""
    for line in (investor_brief_text or "").split("\n"):
        line = line.strip()
        if line and not line.startswith("#") and not line.startswith("Generated") and not line.startswith("Audience"):
            investor_snippet = esc(clip(line, 200))
            break

    # ── Data sources with timestamps (Fix 8) ────────────────
    source_rows = ""
    for key, stats in watcher_stats.items():
        info = SOURCES[key]
        age = age_minutes(stats["fetched_at"])
        status_cls = "ok" if stats["status"] == "ok" else "off"
        ts = stats["fetched_at"][:19] if stats["fetched_at"] else "never"
        summaries = ", ".join(esc(s) for s in stats["summary"])
        source_rows += f'''
        <tr class="src-{status_cls}">
          <td>{info['icon']} {esc(info['label'])}</td>
          <td>{summaries}</td>
          <td>{age}</td>
          <td><code>{ts}</code></td>
        </tr>'''

    # ── Feedback actions ────────────────────────────────────
    feedback_rows = ""
    for action, count in sorted(feedback_actions.items(), key=lambda x: -x[1]):
        icon = action_icons.get(action, "•")
        label = action.replace("_", " ").title()
        feedback_rows += f'<div class="fb-row">{icon} {label}: <strong>{count}</strong></div>\n'
    if not feedback_rows:
        feedback_rows = '<p class="muted">No feedback recorded yet.</p>'

    boost_lines = ""
    for b in (product.get("boost_lines", []) or [])[:6]:
        boost_lines += f'<div class="boost-row">{esc(b)}</div>\n'

    # ── Technical clusters for Judge Audit view (Fix 9) ─────
    tech_clusters_html = ""
    for idx, cluster in enumerate(clusters[:10], 1):
        c_title = esc(cluster.get("title", "Untitled"))
        c_decision = esc(clip(str(cluster.get("decision", "")), 120))
        c_evidence = esc(clip(str(cluster.get("evidence", "")), 120))
        c_score = cluster.get("confidence_score", 0)
        c_band, c_band_cls = confidence_band(c_score)
        c_grade = esc(cluster.get("evidence_grade", ""))
        c_fresh = esc(cluster.get("freshness", "unknown"))
        c_country = esc(cluster.get("country_cluster", ""))
        c_routes = ""
        for route in (cluster.get("personas", []) or [])[:4]:
            c_routes += f'<div class="route-line"><span>{esc(route.get("persona", ""))}</span> <span>{esc(route.get("channel", ""))}</span> <span>{esc(str(route.get("feedback_status", "")).replace("_"," ").title())}</span></div>'
        c_risks = cluster.get("risk_flags", []) or []
        c_risk_html = ""
        if c_risks:
            c_risk_html = '<div class="risk-inline">⚠️ ' + esc("; ".join(str(r) for r in c_risks[:2])) + '</div>'
        tech_clusters_html += f'''
        <div class="cluster-card">
          <div class="cluster-num">{idx:02d}</div>
          <div class="cluster-body">
            <h4>{c_title}{" · " + c_country if c_country else ""}</h4>
            <div class="cluster-band {c_band_cls}">{c_band} confidence · {c_grade} · {c_fresh}</div>
            <p><strong>Decision:</strong> {c_decision}</p>
            <p><strong>Evidence:</strong> {c_evidence}</p>
            {c_risk_html}
            <div class="cluster-routes">{c_routes}</div>
          </div>
        </div>'''

    # ── Watcher health cards ────────────────────────────────
    health_cards = ""
    for key, stats in watcher_stats.items():
        info = SOURCES[key]
        status_dot = "●" if stats["status"] == "ok" else "○"
        age = age_minutes(stats["fetched_at"])
        summaries = " · ".join(esc(s) for s in stats["summary"])
        ts = stats["fetched_at"][:19] if stats["fetched_at"] else "never"
        health_cards += f'''
        <div class="hcard">
          <div class="hcard-top"><span class="hcard-ico">{info['icon']}</span><span class="hcard-lbl">{esc(info['label'])}</span><span class="hcard-dot {'dot-ok' if stats['status'] == 'ok' else 'dot-off'}">{status_dot}</span><span class="hcard-age">{esc(age)}</span></div>
          <div class="hcard-sum">{summaries}</div>
          <div class="hcard-ts">Updated: {esc(ts)}</div>
        </div>'''

    # ── Ask the Dispatch Desk data ──────────────────────────
    analyst_js = r"""
(function () {
  const desk = window.DISPATCH_DESK || {};
  const answerBox = document.getElementById('desk-answer');
  const input = document.getElementById('desk-question');
  const askButton = document.getElementById('desk-ask');
  const copyButton = document.getElementById('copy-answer');

  function clean(v) { return String(v || '').replace(/\s+/g, ' ').trim(); }
  function clip(v, n) { const t = clean(v); return t.length <= n ? t : t.slice(0, n - 1).replace(/\s+\S*$/, '') + '…'; }
  function clusters() { return Array.isArray(desk.clusters) ? desk.clusters : []; }
  function cite() { return '\n\nSources: `outbox/dispatch_desk.json`, `outbox/opportunity_dispatches.json`'; }

  function explainLead() {
    const c = clusters()[0];
    if (!c) return 'No decision clusters are available. Run the pipeline first.' + cite();
    const routes = (c.personas || []).slice(0, 4).map(r =>
      `- ${r.persona} via ${r.channel}: ${clip(r.action, 120)} [${r.dispatch_id}, feedback=${r.feedback_status}]`
    ).join('\n');
    return [`Lead signal: ${c.title}`, `Decision: ${c.decision}`,
      `Evidence: ${c.evidence} (${c.evidence_grade})`,
      `Confidence: ${c.confidence_score}/100; freshness=${c.freshness}`,
      `Feedback: ${c.feedback_summary}`, '', 'Persona routes:', routes, cite()
    ].join('\n');
  }
  function personaRoutes(q) {
    const rows = [];
    clusters().forEach(c => (c.personas || []).forEach(r => {
      const p = clean(r.persona).toLowerCase();
      if (p.includes(q) || (q.includes('investor') && p.includes('investor')) || (q.includes('operator') && p.includes('operator')))
        rows.push(`- ${c.title}: ${clip(r.action, 135)} [${r.dispatch_id}, ${r.feedback_status}]`);
    }));
    return rows.length ? `Routes matching ${q}:\n\n${rows.slice(0, 10).join('\n')}${cite()}` : `No routes matched ${q}.${cite()}`;
  }
  function whatChanged() {
    const f = {}; clusters().forEach(c => { f[c.freshness || 'unknown'] = (f[c.freshness || 'unknown'] || 0) + 1; });
    const fl = Object.entries(f).map(([k, v]) => `${k}: ${v}`).join(', ') || 'no freshness data';
    const b = (desk.boost_lines || []).slice(0, 6).map(x => `- ${x}`).join('\n') || '- No active feedback boosts.';
    return `Cycle ${desk.cycle_id || 'unknown'} changed:\n- ${desk.cluster_count || clusters().length} clusters from ${desk.dispatch_count || 0} routes\n- Freshness: ${fl}\n- Boosts:\n${b}\n\nSources: \`outbox/dispatch_desk.json\`, \`data/feedback/current_boosts.json\``;
  }
  function countryDrill(q) {
    const rows = clusters().filter(c => clean(c.title).toLowerCase().includes(q) || clean(c.country_cluster).toLowerCase().includes(q))
      .map(c => `- ${c.title}: ${c.decision} (${c.confidence_score}/100, ${c.evidence_grade})`);
    return rows.length ? `Drill: ${q}\n\n${rows.join('\n')}${cite()}` : `No match for ${q}.${cite()}`;
  }
  function draftNote(q) {
    let c = clusters().find(c => clean(c.title).toLowerCase().includes(q) || clean(c.country_cluster).toLowerCase().includes(q)) || clusters()[0];
    if (!c) return 'No dispatch available.' + cite();
    let r = (c.personas || []).find(r => clean(r.persona).toLowerCase().includes('investor')) || (c.personas || [])[0];
    if (!r) return 'No route available.' + cite();
    const country = c.country_cluster || 'the region';
    return `Draft for ${country}:\n\nSubject: ${country} signal worth reviewing\n\nSignal: ${c.title}\nEvidence: ${c.evidence} (${c.evidence_grade})\nNext step: ${r.action}\n\nThis is a diligence trigger, not investment advice.\n\nSources: \`outbox/dispatch_desk.json\``;
  }
  function answer(q) {
    const l = clean(q).toLowerCase();
    if (!l) return 'Ask about a lead signal, investor actions, what changed, or a country.';
    if (l.includes('lead') || l.includes('first') || l.includes('why is') || l.includes('top signal')) return explainLead();
    if (l.includes('what changed') || l.includes('feedback') || l.includes('boost') || l.includes('downrank') || l.includes('uprank')) return whatChanged();
    if (l.includes('investor')) return (l.includes('draft') || l.includes('note') || l.includes('message')) ? draftNote(l) : personaRoutes('investor');
    if (l.includes('procurement')) return personaRoutes('procurement');
    if (l.includes('founder') || l.includes('operator')) return personaRoutes('operator');
    for (const c of ['guyana', 'belize', 'suriname', 'barbados', 'vincent', 'antigua', 'kitts'])
      if (l.includes(c)) return (l.includes('draft') || l.includes('note') || l.includes('message')) ? draftNote(c) : countryDrill(c);
    return 'Try: explain lead, investor actions, what changed, Belize drilldown, or draft Guyana note.' + cite();
  }
  function run(q) { answerBox.textContent = answer(q); }
  document.querySelectorAll('[data-question]').forEach(btn => { btn.addEventListener('click', () => { input.value = btn.dataset.question; run(btn.dataset.question); }); });
  askButton.addEventListener('click', () => run(input.value));
  input.addEventListener('keydown', (e) => { if (e.key === 'Enter') run(input.value); });
  copyButton.addEventListener('click', async () => {
    try { await navigator.clipboard.writeText(answerBox.textContent); copyButton.textContent = 'Copied'; }
    catch (_) { copyButton.textContent = 'Select + copy manually'; }
    setTimeout(() => { copyButton.textContent = 'Copy answer'; }, 1500);
  });
})();
"""

    html = f"""<!DOCTYPE html>
<html lang="en">
<head>
<meta charset="UTF-8">
<meta name="viewport" content="width=device-width, initial-scale=1.0">
<title>Caribbean Opportunity Dispatch</title>
<style>
*, *::before, *::after {{ box-sizing: border-box; margin: 0; padding: 0; }}

:root {{
  --bg: #0a0e1a; --surface: #111827; --surface2: #1a2240;
  --text: #e8edf5; --muted: #7888a8; --accent: #3b82f6;
  --green: #10b981; --amber: #f59e0b; --red: #ef4444;
  --border: #1e293b; --radius: 8px;
}}

body {{ font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, sans-serif; background: var(--bg); color: var(--text); line-height: 1.5; }}

/* ── Navigation ── */
.nav {{ display: flex; justify-content: space-between; align-items: center; padding: 16px 24px; border-bottom: 1px solid var(--border); background: var(--surface); }}
.nav h1 {{ font-size: 18px; font-weight: 700; }}
.nav .tagline {{ font-size: 12px; color: var(--muted); }}
.nav-right {{ display: flex; gap: 12px; align-items: center; }}
.nav-pill {{ font-size: 11px; color: var(--muted); background: var(--surface2); padding: 4px 8px; border-radius: 4px; }}
.tab-btn {{ background: transparent; border: 1px solid var(--border); color: var(--muted); padding: 6px 14px; border-radius: 4px; font-size: 12px; cursor: pointer; }}
.tab-btn.active {{ background: var(--accent); color: white; border-color: var(--accent); }}

/* ── Container ── */
.container {{ max-width: 1200px; margin: 0 auto; padding: 24px; }}

/* ── Hero Signal ── */
.hero-signal {{ background: linear-gradient(135deg, var(--surface) 0%, var(--surface2) 100%); border: 1px solid var(--border); border-radius: 12px; padding: 28px; margin-bottom: 24px; }}
.hero-meta {{ font-size: 11px; text-transform: uppercase; letter-spacing: 1px; color: var(--muted); margin-bottom: 8px; }}
.hero-signal h2 {{ font-size: 24px; font-weight: 800; margin: 8px 0; }}
.hero-band {{ display: inline-block; padding: 4px 10px; border-radius: 4px; font-size: 12px; font-weight: 600; margin: 8px 0; }}
.hero-band.high {{ background: rgba(16,185,129,.15); color: var(--green); }}
.hero-band.mod {{ background: rgba(245,158,11,.15); color: var(--amber); }}
.hero-band.low, .hero-band.vlow {{ background: rgba(239,68,68,.15); color: var(--red); }}
.hero-evidence, .hero-decision {{ font-size: 14px; color: var(--muted); margin: 6px 0; }}
.hero-source {{ font-size: 12px; color: var(--accent); }}
.risk-pill {{ display: inline-block; background: rgba(239,68,68,.1); border: 1px solid rgba(239,68,68,.3); color: var(--red); padding: 4px 10px; border-radius: 4px; font-size: 12px; margin: 8px 0; }}
.hero-personas {{ display: flex; gap: 8px; margin-top: 12px; flex-wrap: wrap; }}
.persona-chip {{ background: var(--surface2); border: 1px solid var(--border); padding: 4px 10px; border-radius: 99px; font-size: 12px; }}

/* ── Grid ── */
.grid-2 {{ display: grid; grid-template-columns: 1fr 1fr; gap: 16px; margin-bottom: 24px; }}
.grid-3 {{ display: grid; grid-template-columns: 1fr 1fr 1fr; gap: 16px; margin-bottom: 24px; }}
.grid-2-1 {{ display: grid; grid-template-columns: 2fr 1fr; gap: 16px; margin-bottom: 24px; }}

/* ── Cards ── */
.card {{ background: var(--surface); border: 1px solid var(--border); border-radius: var(--radius); padding: 16px; }}
.card-title {{ font-size: 12px; font-weight: 600; text-transform: uppercase; letter-spacing: .8px; color: var(--muted); margin-bottom: 10px; }}
.card-stat {{ font-size: 28px; font-weight: 800; color: var(--text); }}
.card-sub {{ font-size: 12px; color: var(--muted); margin-top: 2px; }}

/* ── Persona cards ── */
.persona-card {{ background: var(--surface2); border: 1px solid var(--border); border-radius: 6px; padding: 12px; margin-bottom: 10px; }}
.pc-name {{ font-weight: 700; font-size: 14px; color: var(--text); }}
.pc-channel {{ font-size: 11px; color: var(--accent); margin-bottom: 6px; }}
.pc-action {{ font-size: 13px; color: var(--muted); margin-bottom: 6px; }}
.pc-feedback {{ font-size: 11px; color: var(--amber); }}

/* ── Output cards ── */
.output-card {{ background: var(--surface2); border: 1px solid var(--border); border-radius: 6px; padding: 14px; margin-bottom: 10px; }}
.output-card h4 {{ font-size: 13px; font-weight: 600; margin-bottom: 8px; }}
.output-body {{ font-size: 12px; color: var(--muted); white-space: pre-wrap; font-family: monospace; max-height: 200px; overflow: auto; }}
.output-label {{ font-size: 10px; text-transform: uppercase; letter-spacing: 1px; color: var(--muted); margin-bottom: 6px; }}

/* ── Source table ── */
.src-table {{ width: 100%; border-collapse: collapse; font-size: 13px; }}
.src-table td {{ padding: 8px; border-bottom: 1px solid var(--border); }}
.src-table tr.src-ok td:first-child {{ color: var(--green); }}
.src-table tr.src-off td:first-child {{ color: var(--muted); }}
.src-table code {{ font-size: 11px; color: var(--muted); background: var(--surface2); padding: 2px 4px; border-radius: 3px; }}

/* ── Feedback ── */
.fb-row, .boost-row {{ font-size: 13px; padding: 3px 0; color: var(--muted); }}
.fb-row strong {{ color: var(--text); }}

/* ── Why Now ── */
.whynow-list {{ list-style: none; }}
.whynow-list li {{ font-size: 13px; padding: 4px 0; color: var(--muted); }}

/* ── Track chain ── */
.chain {{ display: flex; flex-wrap: wrap; gap: 6px; margin: 12px 0 20px; }}
.chain span {{ background: var(--surface2); border: 1px solid var(--border); padding: 4px 8px; border-radius: 4px; font-size: 11px; font-weight: 600; text-transform: uppercase; letter-spacing: .5px; }}

/* ── Judge Audit ── */
.audit-section {{ display: none; }}
.audit-section.active {{ display: block; }}
.user-section {{ display: block; }}
.user-section.hidden {{ display: none; }}

.cluster-card {{ display: grid; grid-template-columns: 40px 1fr; gap: 12px; border: 1px solid var(--border); border-radius: 6px; padding: 14px; margin-bottom: 12px; }}
.cluster-num {{ font-size: 20px; font-weight: 800; color: var(--accent); }}
.cluster-body h4 {{ font-size: 14px; margin-bottom: 4px; }}
.cluster-band {{ display: inline-block; font-size: 11px; padding: 2px 8px; border-radius: 3px; margin-bottom: 8px; }}
.cluster-band.high {{ background: rgba(16,185,129,.15); color: var(--green); }}
.cluster-band.mod {{ background: rgba(245,158,11,.15); color: var(--amber); }}
.cluster-band.low, .cluster-band.vlow {{ background: rgba(239,68,68,.15); color: var(--red); }}
.cluster-body p {{ font-size: 13px; color: var(--muted); margin: 4px 0; }}
.risk-inline {{ color: var(--red); font-size: 12px; margin: 4px 0; }}
.cluster-routes {{ margin-top: 6px; }}
.route-line {{ display: flex; gap: 8px; font-size: 11px; color: var(--muted); padding: 2px 0; }}
.route-line span:first-child {{ color: var(--text); font-weight: 600; }}

/* ── Health cards ── */
.hcard {{ background: var(--surface2); border: 1px solid var(--border); border-radius: 6px; padding: 10px; }}
.hcard-top {{ display: flex; align-items: center; gap: 6px; margin-bottom: 4px; }}
.hcard-ico {{ font-size: 14px; }}
.hcard-lbl {{ font-size: 12px; font-weight: 600; flex: 1; }}
.hcard-dot {{ font-size: 10px; }}
.dot-ok {{ color: var(--green); }}
.dot-off {{ color: var(--muted); }}
.hcard-age {{ font-size: 11px; color: var(--muted); }}
.hcard-sum {{ font-size: 11px; color: var(--muted); }}
.hcard-ts {{ font-size: 10px; color: var(--muted); opacity: .7; margin-top: 4px; }}

/* ── Analyst rail ── */
.analyst-rail {{ background: var(--surface2); border: 1px solid var(--border); border-radius: 8px; padding: 14px; margin-top: 12px; }}
.analyst-rail h3 {{ font-size: 14px; margin-bottom: 6px; }}
.analyst-rail p {{ font-size: 12px; color: var(--muted); margin-bottom: 8px; }}
.aprompts {{ display: flex; flex-wrap: wrap; gap: 6px; margin: 8px 0; }}
.aprompts button {{ background: var(--surface); border: 1px solid var(--border); color: var(--text); padding: 5px 8px; border-radius: 4px; font-size: 11px; cursor: pointer; }}
.aprompts button:hover {{ border-color: var(--accent); }}
.ask-row {{ display: grid; grid-template-columns: 1fr auto; gap: 6px; margin-top: 8px; }}
.ask-row input {{ background: var(--bg); border: 1px solid var(--border); color: var(--text); padding: 6px 10px; border-radius: 4px; font-size: 12px; }}
.ask-row button {{ background: var(--accent); border: none; color: white; padding: 6px 12px; border-radius: 4px; font-size: 12px; cursor: pointer; }}
.answer-box {{ margin-top: 8px; padding: 10px; background: var(--bg); border-left: 3px solid var(--accent); font-size: 12px; white-space: pre-wrap; color: var(--muted); max-height: 250px; overflow: auto; }}

.muted {{ color: var(--muted); font-size: 13px; }}

/* Responsive */
@media(max-width:768px) {{ .grid-2,.grid-3,.grid-2-1 {{ grid-template-columns: 1fr; }} }}
</style>
</head>
<body>

<div class="nav">
  <div>
    <h1>🌴 Caribbean Opportunity Dispatch</h1>
    <div class="tagline">Live intelligence system — fragmented public data → actionable signals</div>
  </div>
  <div class="nav-right">
    <span class="nav-pill">{total_ok}/{total_sources} sources live</span>
    <button class="tab-btn active" onclick="showView('user',this)">Product View</button>
    <button class="tab-btn" onclick="showView('audit',this)">Judge Audit</button>
  </div>
</div>

<div class="container">

  <!-- ═══ USER VIEW (default) ═══ -->
  <div id="user-view" class="user-section">

    <!-- Hero signal -->
    {hero_html}

    <!-- Track chain -->
    <div class="chain"><span>Data</span><span>Signal</span><span>Packaging</span><span>Distribution</span><span>Action</span><span>Capital</span></div>

    <!-- Why it matters + Who receives -->
    <div class="grid-2">
      <div class="card">
        <div class="card-title">Why this matters</div>
        <p style="font-size:14px;color:var(--muted)">{thesis_plain}</p>
        <div style="margin-top:12px">
          <div class="card-title">Why now</div>
          <ul class="whynow-list">{whynow_html if whynow_html else '<li>No active seasonal triggers</li>'}</ul>
        </div>
      </div>
      <div>
        <div class="card" style="margin-bottom:12px">
          <div class="card-title">What the diaspora investor receives</div>
          <div class="output-body" style="font-size:12px;font-family:monospace">{telegram_preview}</div>
        </div>
        <div class="analyst-rail">
          <h3>🔍 Ask the Dispatch Desk</h3>
          <p>Interrogate this cycle. Answers are deterministic and cite sources.</p>
          <div class="aprompts">
            <button data-question="explain lead">Explain lead</button>
            <button data-question="show investor actions">Investor actions</button>
            <button data-question="what changed this cycle">What changed?</button>
            <button data-question="draft Guyana investor note">Draft Guyana note</button>
          </div>
          <div class="ask-row">
            <input id="desk-question" placeholder="Ask about a country, evidence, feedback…">
            <button id="desk-ask">Ask</button>
          </div>
          <div id="desk-answer" class="answer-box">Click a prompt or ask a question.</div>
          <button id="copy-answer" class="tab-btn" style="margin-top:6px;font-size:11px">Copy answer</button>
        </div>
      </div>
    </div>

    <!-- Who should act -->
    <h3 style="margin-bottom:12px;font-size:16px;">Who should act this cycle</h3>
    <div class="grid-3" style="margin-bottom:24px">
      {persona_action_html if persona_action_html else '<p class="muted">No persona routes yet.</p>'}
    </div>

  </div>

  <!-- ═══ JUDGE AUDIT VIEW ═══ -->
  <div id="audit-view" class="audit-section">

    <div style="display:flex;justify-content:space-between;align-items:center;margin-bottom:16px">
      <h2>Judge Audit — Technical Proof</h2>
      <span class="nav-pill">Cycle {cycle_id} · {now}</span>
    </div>

    <!-- Summary stats -->
    <div class="grid-3" style="margin-bottom:20px">
      <div class="card"><div class="card-title">Composite Signals</div><div class="card-stat">{composite_count}</div><div class="card-sub">Cross-source merged</div></div>
      <div class="card"><div class="card-title">Decision Clusters</div><div class="card-stat">{len(clusters)}</div><div class="card-sub">From {dispatch_summary.get('total_dispatches',0)} persona routes</div></div>
      <div class="card"><div class="card-title">Feedback Events</div><div class="card-stat">{feedback_events}</div><div class="card-sub">{len(persona_counts)} personas reached</div></div>
    </div>

    <!-- How it runs -->
    <div class="card" style="margin-bottom:20px">
      <div class="card-title">How this runs continuously</div>
      <p style="font-size:13px;color:var(--muted);margin-bottom:12px">Six watchers poll public APIs on schedule. A cross-source merger detects changes. Editorial enrichment scores and narrates signals. Opportunity dispatches route to personas. Feedback adapts future ranking.</p>
      <div style="overflow-x:auto">
        <table class="src-table">
          <tr><th>Source</th><th>Data</th><th>Last updated</th><th>Timestamp</th></tr>
          {source_rows}
        </table>
      </div>
    </div>

    <!-- Feedback loop -->
    <div class="grid-2" style="margin-bottom:20px">
      <div class="card">
        <div class="card-title">Feedback this cycle</div>
        {feedback_rows}
      </div>
      <div class="card">
        <div class="card-title">Feedback-adjusted priority</div>
        {boost_lines if boost_lines else '<p class="muted">No active boosts.</p>'}
      </div>
    </div>

    <!-- Decision clusters -->
    <h3 style="margin-bottom:12px">All Decision Clusters ({len(clusters)})</h3>
    {tech_clusters_html}

    <!-- Full source outputs -->
    <h3 style="margin:24px 0 12px">Generated Outputs</h3>
    <div class="grid-2">
      <div class="output-card">
        <div class="output-label">Telegram Brief</div>
        <div class="output-body">{esc(telegram_brief_text or "Not generated")[:800]}</div>
      </div>
      <div class="output-card">
        <div class="output-label">Investor Brief</div>
        <div class="output-body">{esc(investor_brief_text or "Not generated")[:800]}</div>
      </div>
    </div>

  </div>

</div>

<script>
window.DISPATCH_DESK = {product_json};

function showView(view, btn) {{
  document.querySelectorAll('.tab-btn').forEach(b => b.classList.remove('active'));
  btn.classList.add('active');
  if (view === 'user') {{
    document.getElementById('user-view').classList.remove('hidden');
    document.getElementById('audit-view').classList.remove('active');
  }} else {{
    document.getElementById('user-view').classList.add('hidden');
    document.getElementById('audit-view').classList.add('active');
  }}
}}
</script>
<script>
{analyst_js}
</script>
</body>
</html>"""

    return html


# ── Main ───────────────────────────────────────────────────

def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--no-open", action="store_true")
    args = parser.parse_args()

    watcher_stats: dict[str, dict] = {}
    for key, info in SOURCES.items():
        data = read_json(ROOT / info["path"])
        watcher_stats[key] = extract_watcher_stats(key, data)

    thesis_text = read_textfile(ROOT / "outbox" / "regional_thesis.md")
    whynow_text = read_textfile(ROOT / "outbox" / "why_now.md")
    telegram_brief_text = read_textfile(ROOT / "outbox" / "telegram_brief.md")
    investor_brief_text = read_textfile(ROOT / "outbox" / "investor_brief.md")

    # Dispatch summary
    dp_data = read_json(ROOT / "outbox" / "opportunity_dispatches.json") or {}
    dispatches = dp_data.get("dispatches", []) if isinstance(dp_data.get("dispatches"), list) else []
    persona_counts: dict[str, int] = {}
    for d in dispatches:
        p = str(d.get("persona_label") or d.get("recipient_persona") or "Unknown")
        persona_counts[p] = persona_counts.get(p, 0) + 1

    product_desk: dict[str, Any] = {}
    desk_data = read_json(ROOT / "outbox" / "dispatch_desk.json")
    if desk_data:
        clusters = desk_data.get("clusters", []) or []
        product_desk = {
            "cycle_id": desk_data.get("cycle_id", "unknown"),
            "cluster_count": desk_data.get("cluster_count", len(clusters)),
            "dispatch_count": desk_data.get("dispatch_count", 0),
            "persona_count": desk_data.get("persona_count", len(persona_counts)),
            "channel_count": desk_data.get("channel_count", 0),
            "regional_thesis": desk_data.get("regional_thesis", ""),
            "why_now": desk_data.get("why_now", []),
            "boost_lines": desk_data.get("boost_lines", []),
            "clusters": clusters,
        }

    product_json = json_for_script(product_desk)

    feedback_state = read_json(ROOT / "data" / "feedback" / "state.json")
    if feedback_state is None:
        feedback_state = {}
    feedback = {
        "total_events": len(feedback_state.get("history", []) or []),
        "actions": {},
        "boosts": feedback_state.get("boosts", {}),
        "boost_summary": [],
    }
    for entry in feedback_state.get("history", []) or []:
        s = entry.get("feedback_status", "unknown")
        feedback["actions"][s] = feedback["actions"].get(s, 0) + 1
    for kind, countries in feedback["boosts"].items():
        for country, boost in countries.items():
            if boost != 0:
                feedback["boost_summary"].append(f"{country} {kind} {boost:+d}")
    feedback["boost_summary"] = feedback["boost_summary"][:6]

    html = generate_html(
        watcher_stats, thesis_text, whynow_text,
        telegram_brief_text, investor_brief_text,
        {"dispatches": dispatches, "total_dispatches": len(dispatches), "persona_counts": persona_counts},
        feedback, persona_counts,
        product_desk=product_desk, product_json=product_json,
    )

    OUTPUT.write_text(html, encoding="utf-8")
    print(f"Dashboard written to {OUTPUT}", flush=True)

    if args.no_open:
        return 0
    try:
        if sys.platform == "darwin":
            subprocess.Popen(["open", str(OUTPUT)])
        print("Opened in browser.", flush=True)
    except Exception:
        pass
    return 0

if __name__ == "__main__":
    raise SystemExit(main())
