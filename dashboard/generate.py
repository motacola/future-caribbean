#!/usr/bin/env python3
"""Generate the operator console for Caribbean Opportunity Dispatch.

Reads watcher data, outbox artifacts, and feedback state to render
a dense, utilitarian single-page console. Not the product — the
internal health view that proves the pipeline is alive.

Usage:
  python3 dashboard/generate.py
  # Opens dashboard.html in browser

Cron: scheduled alongside the pipeline to auto-refresh.
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
import logging

LOGGER = logging.getLogger(__name__)

ROOT = Path(__file__).resolve().parents[1]
OUTPUT = ROOT / "dashboard.html"

# ── Source watchers ────────────────────────────────────────

SOURCES = {
    "world_bank": {
        "label": "World Bank",
        "icon": "🏦",
        "path": "data/world_bank/latest.json",
        "color": "#3b82f6",
    },
    "idb": {
        "label": "IDB Open Data",
        "icon": "📊",
        "path": "data/idb/latest.json",
        "color": "#8b5cf6",
    },
    "noaa": {
        "label": "NOAA Weather",
        "icon": "🌤",
        "path": "data/noaa/latest.json",
        "color": "#f59e0b",
    },
    "ndbc": {
        "label": "NDBC Buoys",
        "icon": "🌊",
        "path": "data/ndbc/latest.json",
        "color": "#06b6d4",
    },
    "tier2": {
        "label": "Tier 2 (CARICOM+CDB)",
        "icon": "🗃",
        "path": "data/tier2/latest.json",
        "color": "#10b981",
    },
    "composite": {
        "label": "Composite Intelligence",
        "icon": "🧠",
        "path": "data/composite/latest.json",
        "color": "#ef4444",
    },
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
    """Read first N lines of a text file."""
    if not path.exists():
        return ""
    try:
        lines = path.read_text(encoding="utf-8").splitlines()
        return "\n".join(lines[:max_lines])
    except Exception:
        return ""


def esc(value: Any) -> str:
    """Escape values before inserting them into generated HTML."""
    return html_lib.escape(str(value), quote=True)


def clip_sentence(value: str, max_chars: int) -> str:
    """Clip text at a sentence boundary where possible."""
    value = " ".join(value.split())
    if len(value) <= max_chars:
        return value
    clipped = value[:max_chars].rsplit(" ", 1)[0].rstrip(" ,;:-")
    last_stop = max(clipped.rfind("."), clipped.rfind("!"), clipped.rfind("?"))
    if last_stop > max_chars * 0.55:
        return clipped[: last_stop + 1]
    return clipped + "..."


def age_minutes(ts: str | None) -> str:
    if not ts:
        return "never"
    try:
        dt = datetime.fromisoformat(ts.replace("Z", "+00:00"))
        delta = datetime.now(timezone.utc) - dt
        mins = int(delta.total_seconds() / 60)
        if mins < 1:
            return "just now"
        if mins < 60:
            return f"{mins}m ago"
        hours = mins // 60
        if hours < 24:
            return f"{hours}h ago"
        days = hours // 24
        return f"{days}d ago"
    except Exception:
        return "?"


def extract_watcher_stats(source_key: str, data: dict | None) -> dict:
    stats: dict[str, Any] = {
        "status": "offline" if data is None else "ok",
        "fetched_at": None,
        "summary": [],
        "count": 0,
    }
    if data is None:
        stats["summary"].append("No data")
        return stats
    stats["fetched_at"] = data.get("fetched_at")

    if source_key == "world_bank":
        obs = data.get("observations", [])
        sigs = data.get("signals", [])
        countries = list(data.get("countries", {}).keys())
        stats["summary"] = [f"{len(obs)} obs", f"{len(countries)} countries", f"{len(sigs)} sigs"]
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
        stats["summary"] = [f"{len(readings)} buoys", f"{len(sigs)} sigs"]
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


def extract_persona_counts(dispatch_md: str) -> dict[str, int]:
    """Count dispatches by persona from opportunity_dispatches.md."""
    counts: dict[str, int] = {}
    for line in dispatch_md.split("\n"):
        m = re.search(r"To: ([A-Za-z /]+)", line)
        if m:
            persona = m.group(1).strip()
            counts[persona] = counts.get(persona, 0) + 1
    return counts


def extract_dispatch_summary(dispatch_path: Path) -> dict[str, Any]:
    """Read canonical dispatch JSON for dashboard counts and rows."""
    data = read_json(dispatch_path) or {}
    dispatches = data.get("dispatches", [])
    if not isinstance(dispatches, list):
        dispatches = []

    persona_counts: dict[str, int] = {}
    rows: list[dict[str, Any]] = []
    for dispatch in dispatches:
        if not isinstance(dispatch, dict):
            continue
        persona = str(
            dispatch.get("persona_label")
            or dispatch.get("recipient_persona")
            or "Unknown"
        )
        persona_counts[persona] = persona_counts.get(persona, 0) + 1
        rows.append(dispatch)

    rows.sort(key=lambda d: d.get("confidence_score", 0), reverse=True)
    return {
        "dispatches": rows,
        "total_dispatches": len(rows),
        "persona_counts": persona_counts,
    }


def extract_feedback_state(state_path: Path) -> dict[str, Any]:
    """Return a compact summary of the feedback loop state."""
    state = read_json(state_path)
    if not state:
        return {"total_events": 0, "actions": {}}

    history = state.get("history", [])
    boosts = state.get("boosts", {})

    # Count by feedback status
    action_counts: dict[str, int] = {}
    for entry in history:
        status = entry.get("feedback_status", "unknown")
        action_counts[status] = action_counts.get(status, 0) + 1

    # Summarise boosts
    boost_summary: list[str] = []
    for kind, countries in boosts.items():
        for country, boost in countries.items():
            if boost > 0:
                boost_summary.append(f"{country} {kind} +{boost}")
            elif boost < 0:
                boost_summary.append(f"{country} {kind} {boost}")

    return {
        "total_events": len(history),
        "actions": action_counts,
        "boost_summary": boost_summary[:6],
    }


# ── Dispatch Desk helpers ───────────────────────────────────

def extract_dispatch_desk() -> dict[str, Any]:
    """Read delivery manifest and packet directory for Dispatch Desk panel."""
    manifest_path = ROOT / "outbox" / "delivery_manifest.json"
    packets_dir = ROOT / "outbox" / "dispatch_packets"

    result: dict[str, Any] = {
        "manifest_present": False,
        "packet_count": 0,
        "delivery_count": 0,
        "personas": {},
        "channels": {},
        "status_breakdown": {},
        "packets": [],
    }

    if manifest_path.exists():
        try:
            manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
            result["manifest_present"] = True
            result["delivery_count"] = manifest.get("total_deliveries", 0)
            result["personas"] = manifest.get("summary", {}).get("by_persona", {})
            result["channels"] = manifest.get("summary", {}).get("by_channel", {})
            result["status_breakdown"] = manifest.get("summary", {}).get("by_status", {})
        except Exception:
            LOGGER.warning("manifest parse error in dashboard")

    if packets_dir.exists():
        try:
            packets = sorted(p for p in packets_dir.iterdir() if p.suffix == ".md" and p.name != "README.md")
            result["packet_count"] = len(packets)
            result["packets"] = [p.name for p in packets]
        except Exception:
            LOGGER.warning("packet directory read error in dashboard")

    return result


# ── Routing rules helpers ────────────────────────────────────

def load_routing_rules() -> tuple[list[dict[str, Any]], dict[str, str]]:
    """Load routing rules from config/recipients.json for the routing map.

    Returns (rules_list, persona_labels) for dashboard display.
    """
    path = ROOT / "config" / "recipients.json"
    rules_list: list[dict[str, Any]] = []
    persona_labels: dict[str, str] = {}
    if not path.exists():
        return rules_list, persona_labels

    try:
        config = json.loads(path.read_text(encoding="utf-8"))
        personas = config.get("personas", {})
        for pk, pv in personas.items():
            persona_labels[pk] = pv.get("label", pk)

        rules = config.get("routing_rules", {})
        for kind, rule in sorted(rules.items()):
            personas_for_kind = rule.get("personas", [])
            labels = [persona_labels.get(p, p.replace("_", " ").title()) for p in personas_for_kind]
            rationale = rule.get("routing_rationale", {})
            # Use first rationale as the summary
            first_rationale = ""
            for pk in personas_for_kind:
                r = rationale.get(pk, "")
                if r:
                    first_rationale = r
                    break
            rules_list.append({
                "kind": kind.replace("_", " ").title(),
                "personas": labels,
                "rationale": first_rationale[:120],
            })
    except (json.JSONDecodeError, OSError):
        LOGGER.warning("data file parse error")

    return rules_list, persona_labels


# ── Boost formatter ──────────────────────────────────────────

def format_boosts(boosts: dict[str, dict[str, int]]) -> str:
    """Format boost data as readable HTML lines."""
    lines = ""
    for kind, countries in boosts.items():
        for country, boost in countries.items():
            if boost > 0:
                icon = "🚀"
                cls = "boost-pos"
            elif boost < 0:
                icon = "⬇️"
                cls = "boost-neg"
            else:
                continue  # skip zero boosts
            lines += f"<frow class='{cls}'>{icon} <b>{country}</b> {kind.replace('_', ' ').title()}: {boost:+d}</frow>\\n"
    return lines if lines else '<p class="tp">No active boosts.</p>'


# ── HTML generator ─────────────────────────────────────────

def generate_html(
    watcher_stats: dict,
    thesis_text: str,
    whynow_text: str,
    dispatch_summary: dict[str, Any],
    feedback: dict,
    persona_counts: dict[str, int],
    dispatch_desk: dict | None = None,
    routing_rules: list[dict[str, Any]] | None = None,
    boost_html: str = "",
) -> str:
    now = datetime.now(timezone.utc).strftime("%b %d, %Y at %H:%M UTC")

    # Summary counts
    total_ok = sum(1 for s in watcher_stats.values() if s["status"] == "ok")
    total_sources = len(watcher_stats)

    # Composite signals
    composite = watcher_stats.get("composite", {})
    total_signals = composite.get("count", 0)

    # Persona bar chart data
    persona_groups = sorted(persona_counts.items(), key=lambda x: -x[1])
    max_pc = max((c for _, c in persona_groups), default=1)

    # Feedback stats
    feedback_events = feedback.get("total_events", 0)
    feedback_actions = feedback.get("actions", {})
    action_icons = {"forwarded": "📤", "replied": "💬", "opened": "👁", "decision_changed": "🔀", "ignored": "—"}

    # ── Dispatch Desk data ────────────────────────────────
    desk = dispatch_desk or {}
    desk_delivery_count = desk.get("delivery_count", 0)
    desk_packet_count = desk.get("packet_count", 0)
    desk_personas = desk.get("personas", {})
    desk_channels = desk.get("channels", {})
    desk_packets = desk.get("packets", [])
    desk_manifest_present = desk.get("manifest_present", False)

    desk_persona_lines = ""
    for persona, count in sorted(desk_personas.items(), key=lambda x: -x[1]):
        label = persona.replace("_", " ").title()
        desk_persona_lines += f"<frow>{esc(label)}: <b>{count}</b></frow>\n"

    desk_channel_lines = ""
    for ch, count in sorted(desk_channels.items(), key=lambda x: -x[1]):
        desk_channel_lines += f"<frow>{esc(ch)}: <b>{count}</b></frow>\n"

    desk_packet_lines = ""
    for pname in desk_packets[:8]:
        desk_packet_lines += f"<frow>📄 {esc(pname)}</frow>\n"

    # ── Watcher cards ────────────────────────────────────
    cards_html = ""
    for key, stats in watcher_stats.items():
        info = SOURCES[key]
        status_icon = "●" if stats["status"] == "ok" else "○"
        age = age_minutes(stats["fetched_at"])
        summary_html = "".join(f'<s>{esc(s)}</s>' for s in stats["summary"])
        cards_html += f"""
        <c>
            <ch><ci>{info['icon']}</ci><ct>{esc(info['label'])}</ct><cs>{status_icon}</cs><ca>{esc(age)}</ca></ch>
            <cs2>{summary_html}</cs2>
            <cf>Updated: {esc(stats['fetched_at'][:19] if stats['fetched_at'] else 'never')}</cf>
        </c>"""

    # ── Dispatches table ─────────────────────────────────
    dispatch_rows = ""
    for dispatch in dispatch_summary.get("dispatches", [])[:10]:
        title = esc(dispatch.get("title", "Untitled dispatch"))
        persona = esc(
            dispatch.get("persona_label")
            or dispatch.get("recipient_persona")
            or "Unknown persona"
        )
        channel = esc(dispatch.get("channel", "Unknown channel"))
        action = esc(
            dispatch.get("recommended_action")
            or dispatch.get("action")
            or "No action recorded"
        )[:240]
        feedback_status = esc(dispatch.get("feedback_status", "awaiting").replace("_", " ").title())
        score = esc(dispatch.get("confidence_score", "-"))
        row_class = "im" if dispatch.get("confidence_score", 0) >= 90 else ""
        dispatch_rows += (
            f"<tr class='{row_class}'><td><strong>{title}</strong><br>"
            f"<span>{persona} via {channel} · {score}/100 · Feedback: {feedback_status}</span><br>"
            f"<em>{action}</em></td></tr>\n"
        )

    # ── Persona routing bar chart ────────────────────────
    persona_html = ""
    for persona, count in persona_groups:
        pct = (count / max_pc) * 100 if max_pc else 0
        persona_html += f"""
        <pb><pl>{esc(persona)}</pl><pv>{count}</pv><pbar style='width:{pct}%'></pbar></pb>"""

    # ── Feedback loop state ──────────────────────────────
    feedback_rows = ""
    for action, count in sorted(feedback_actions.items(), key=lambda x: -x[1]):
        icon = action_icons.get(action, "•")
        label = action.replace("_", " ").title()
        feedback_rows += f"<frow>{icon} {esc(label)}: <b>{count}</b></frow>\n"

    boost_lines = boost_html if boost_html else ""
    if not boost_lines:
        for b in feedback.get("boost_summary", []):
            boost_lines += f"<frow>{esc(b)}</frow>\n"

    # ── Routing map HTML ──────────────────────────────────
    routing_map_html = ""
    if routing_rules:
        for rule in routing_rules:
            kl = esc(rule.get("kind", ""))
            personas = " → ".join(esc(p) for p in rule.get("personas", []))
            rationale = esc(rule.get("rationale", ""))
            routing_map_html += (
                f"<div style='margin-bottom:6px; padding:6px 8px; "
                f"background:#141c30; border-radius:4px;'>"
                f"<strong style='color:#e8edf5;'>{kl}</strong> → "
                f"<span style='color:#60a5fa;'>{personas}</span><br>"
                f"<span style='font-size:11px; color:#7888a8;'>{rationale}</span>"
                f"</div>\\n"
            )

    # ── Extract thesis first paragraph ───────────────────
    thesis_para = ""
    for line in thesis_text.split("\n"):
        line = line.strip()
        if (
            line
            and not line.startswith("#")
            and not line.startswith("**")
            and not line.startswith("-")
            and not line.startswith("Generated:")
        ):
            thesis_para = esc(line)
            break

    # ── Why Now bullet lines ─────────────────────────────
    whynow_bullets = ""
    for line in whynow_text.split("\n"):
        line = line.strip()
        if line.startswith("🟢") or line.startswith("🔴") or line.startswith("🟡"):
            whynow_bullets += f"<wrow>{esc(line[:220])}</wrow>\n"

    html = f"""<!DOCTYPE html>
<html lang="en">
<head>
<meta charset="UTF-8">
<meta name="viewport" content="width=device-width, initial-scale=1.0">
<title>Caribbean Opportunity Dispatch — Operator Console</title>
<style>
* {{ margin:0; padding:0; box-sizing:border-box; }}
body {{ font-family:-apple-system,BlinkMacSystemFont,'Segoe UI',Roboto,sans-serif; background:#0a0e1a; color:#c8d0e0; padding:20px; }}
h1,h2,h3,h4 {{ font-weight:600; }}
a {{ color:#60a5fa; text-decoration:none; }}

/* ── Header ──────────────────────────────────────────── */
.hdr {{ display:flex; justify-content:space-between; align-items:flex-start; margin-bottom:20px; padding-bottom:14px; border-bottom:1px solid #1a2240; }}
.hdr-l {{ display:flex; flex-direction:column; gap:2px; }}
.hdr-l h1 {{ font-size:22px; font-weight:700; color:#e8edf5; letter-spacing:-0.3px; }}
.hdr-l .tagline {{ color:#7888a8; font-size:13px; }}
.hdr-r {{ text-align:right; }}
.hdr-r .badge {{ display:inline-block; background:#1a2240; color:#60a5fa; padding:4px 12px; border-radius:4px; font-size:11px; font-weight:600; letter-spacing:0.5px; border:1px solid #2a3a60; }}
.badges {{ display:flex; gap:8px; margin-top:6px; flex-wrap:wrap; justify-content:flex-end; }}
.badges .badge {{ background:#141c30; color:#8898b8; font-size:11px; }}

/* ── Layout ──────────────────────────────────────────── */
.grid2 {{ display:grid; grid-template-columns:1fr 1fr; gap:14px; margin-bottom:16px; }}
.grid3 {{ display:grid; grid-template-columns:1fr 1fr 1fr; gap:14px; margin-bottom:16px; }}
.panel {{ background:#111827; border-radius:8px; padding:14px; border:1px solid #1e293b; }}
.panel-full {{ grid-column:1/-1; }}
.ph {{ display:flex; justify-content:space-between; align-items:center; margin-bottom:10px; }}
.ph h2 {{ font-size:13px; font-weight:600; color:#7888a8; text-transform:uppercase; letter-spacing:0.8px; }}
.ph .val {{ font-size:18px; font-weight:700; color:#e8edf5; }}

/* ── Watcher cards ───────────────────────────────────── */
.wg {{ display:grid; grid-template-columns:repeat(auto-fill,minmax(200px,1fr)); gap:10px; margin-bottom:16px; }}
c {{ background:#111827; border-radius:6px; padding:10px; border:1px solid #1e293b; border-left:3px solid #3b82f6; }}
ch {{ display:flex; align-items:center; gap:6px; margin-bottom:6px; }}
ci {{ font-size:16px; }}
ct {{ font-weight:600; font-size:12px; flex:1; }}
cs {{ font-size:12px; }}
ca {{ font-size:11px; color:#7888a8; }}
cs2 {{ display:flex; flex-wrap:wrap; gap:4px; }}
s {{ background:#1a2240; padding:2px 8px; border-radius:10px; font-size:11px; font-weight:500; }}
cf {{ font-size:10px; color:#566886; margin-top:6px; padding-top:6px; border-top:1px solid #1a2240; }}

/* ── Dispatches table ────────────────────────────────── */
dt {{ width:100%; border-collapse:collapse; font-size:12px; }}
dt td {{ padding:4px 8px; border-bottom:1px solid #1a2240; color:#b0b8c8; }}
dt tr.im td {{ color:#f87171; font-weight:600; }}

/* ── Persona bars ────────────────────────────────────── */
pb {{ display:flex; align-items:center; gap:8px; margin:4px 0; }}
pl {{ width:160px; font-size:11px; color:#8898b8; text-align:right; }}
pv {{ width:28px; font-size:11px; font-weight:600; color:#e8edf5; text-align:right; }}
pbar {{ height:14px; background:#3b82f6; border-radius:3px; min-width:6px; }}

/* ── Feedback ────────────────────────────────────────── */
frow {{ font-size:12px; padding:2px 0; color:#b0b8c8; }}

/* ── Thesis / Why Now ────────────────────────────────── */
tp {{ font-size:13px; line-height:1.5; color:#b0b8c8; }}
wrow {{ font-size:12px; padding:2px 0; color:#b0b8c8; }}

/* ── Footer ──────────────────────────────────────────── */
.ft {{ text-align:center; color:#566886; font-size:11px; padding:16px 0; border-top:1px solid #1a2240; margin-top:16px; }}

@media(max-width:800px){{ .grid2,.grid3 {{ grid-template-columns:1fr; }} }}
</style>
</head>
<body>

<div class="hdr">
<div class="hdr-l">
<h1>Caribbean Opportunity Dispatch</h1>
<div class="tagline">Routed opportunity and risk dispatches from fragmented Caribbean public data. ← Operator console — not the product.</div>
</div>
<div class="hdr-r">
<div class="badge">OPERATOR CONSOLE</div>
<div class="badges">
<span class="badge">{total_signals} composite signals</span>
<span class="badge">{total_ok}/{total_sources} sources online</span>
<span class="badge">{now[:16]}</span>
</div>
</div>
</div>

<div class="grid3">
<div class="panel">
<div class="ph"><h2>Composite Signals</h2><span class="val">{total_signals}</span></div>
<div class="ph" style="margin-top:8px"><h2>Dispatches</h2><span class="val">{dispatch_summary.get('total_dispatches', 0)}</span></div>
</div>
<div class="panel">
<div class="ph"><h2>Feedback Events</h2><span class="val">{feedback_events}</span></div>
<div class="ph" style="margin-top:8px"><h2>Personas Reached</h2><span class="val">{len(persona_counts)}</span></div>
</div>
<div class="panel">
<div class="ph"><h2>Pipeline Status</h2><span class="val">{"LIVE" if total_ok > 2 else "DEGRADED"}</span></div>
<div class="ph" style="margin-top:8px"><h2>Cycle</h2><span class="val">{now.split()[0]}</span></div>
</div>
</div>

<div class="grid2">
<div class="panel panel-full">
<div class="ph"><h2>Regional Thesis</h2></div>
<p class="tp">{thesis_para if thesis_para else 'No regional thesis generated yet — run pipeline first.'}</p>
</div>
</div>

<div class="grid2">
<div class="panel panel-full">
<div class="ph"><h2>Why Now — Editorial Calendar</h2></div>
{whynow_bullets if whynow_bullets else '<p class="tp">No calendar context for this cycle.</p>'}
</div>
</div>

<div class="grid2">
<div class="panel panel-full">
<div class="ph"><h2>Top Opportunity Dispatches</h2><span class="val">{dispatch_summary.get('total_dispatches', 0)} total</span></div>
<table class="dt">
{dispatch_rows if dispatch_rows else '<tr><td>No dispatches generated yet — run pipeline first.</td></tr>'}
</table>
</div>
</div>

<div class="grid2">
<div class="panel">
<div class="ph"><h2>Persona Routing</h2></div>
{persona_html if persona_html else '<p class="tp">No persona data yet.</p>'}</div>

<div class="panel">
<div class="ph"><h2>Feedback Loop</h2></div>
<div style="margin-bottom:8px">
<div class="ph" style="margin-bottom:4px"><h3>Actions This Cycle</h3></div>
{feedback_rows if feedback_rows else '<p class="tp">No feedback recorded yet.</p>'}
</div>
<div>
<div class="ph" style="margin-bottom:4px"><h3>Active Boosts</h3></div>
{boost_lines if boost_lines else '<p class="tp">No active boosts.</p>'}
</div>
</div>
</div>

<!-- ── Dispatch Desk ────────────────────────────────────── -->
<div class="grid2">
<div class="panel">
<div class="ph"><h2>Dispatch Desk — Delivery Manifest</h2><span class="val">{desk_delivery_count}</span></div>
<div style="margin-bottom:8px">
<div class="ph" style="margin-bottom:4px"><h3>By Persona</h3></div>
{desk_persona_lines if desk_persona_lines else '<p class="tp">No manifest data.</p>'}
</div>
<div>
<div class="ph" style="margin-bottom:4px"><h3>By Channel</h3></div>
{desk_channel_lines if desk_channel_lines else '<p class="tp">No channel data.</p>'}
</div>
{'' if desk_manifest_present else '<p class="tp">Run pipeline to generate delivery manifest.</p>'}
</div>

<div class="panel">
<div class="ph"><h2>Dispatch Desk — Packets</h2><span class="val">{desk_packet_count}</span></div>
<div style="margin-bottom:8px">
<div class="ph" style="margin-bottom:4px"><h3>Available Packets</h3></div>
{desk_packet_lines if desk_packet_lines else '<p class="tp">No packets generated yet.</p>'}
</div>
<div style="margin-top:8px; padding-top:8px; border-top:1px solid #1a2240;">
<div class="ph" style="margin-bottom:4px"><h3>Feedback Intake</h3></div>
<frow style="font-size:11px; color:#7888a8;">Use <code>feedback_intake.py</code> to record outcomes:</frow>
<frow style="font-size:11px; font-family:monospace; color:#566886;">
python3 packagers/feedback_intake.py --dispatch-id &lt;ID&gt; --status forwarded --note "..."
</frow>
</div>
</div>
</div>
</div>

<div class="panel panel-full">
<div class="ph"><h2>Watcher Health</h2></div>
<div class="wg">{cards_html}</div>
</div>

<div class="ft">
Caribbean Opportunity Dispatch — Operator Console<br>
Generated {now}<br>
Sources: World Bank, IDB, NOAA NWS, NDBC Buoys, CARICOM Statistics, CDB
</div>

</body>
</html>"""

    return html


# ── Main ───────────────────────────────────────────────────

def main() -> int:
    parser = argparse.ArgumentParser(description="Generate the operator console.")
    parser.add_argument("--no-open", action="store_true", help="Do not open in browser.")
    args = parser.parse_args()

    # ── Read watcher data ─────────────────────────────────
    watcher_stats: dict[str, dict] = {}
    for key, info in SOURCES.items():
        data_path = ROOT / info["path"]
        data = read_json(data_path)
        stats = extract_watcher_stats(key, data)
        watcher_stats[key] = stats

    # ── Read outbox artifacts ──────────────────────────────
    thesis_text = read_textfile(ROOT / "outbox" / "regional_thesis.md", max_lines=30)
    whynow_text = read_textfile(ROOT / "outbox" / "why_now.md", max_lines=20)
    dispatch_summary = extract_dispatch_summary(ROOT / "outbox" / "opportunity_dispatches.json")

    # ── Read feedback state ────────────────────────────────
    feedback = extract_feedback_state(ROOT / "data" / "feedback" / "state.json")

    # ── Extract persona counts ─────────────────────────────
    persona_counts = dispatch_summary["persona_counts"]

    # ── Read dispatch desk data ──────────────────────────
    dispatch_desk = extract_dispatch_desk()

    # ── Load routing rules and format boosts ─────────────
    routing_rules, _persona_labels = load_routing_rules()
    boost_state = feedback.get("boosts", {})
    boost_html = format_boosts(boost_state)

    # ── Generate ───────────────────────────────────────────
    html = generate_html(
        watcher_stats,
        thesis_text,
        whynow_text,
        dispatch_summary,
        feedback,
        persona_counts,
        dispatch_desk=dispatch_desk,
        routing_rules=routing_rules,
        boost_html=boost_html,
    )
    OUTPUT.write_text(html, encoding="utf-8")
    print(f"Operator console written to {OUTPUT}", flush=True)

    if args.no_open:
        return 0

    try:
        if sys.platform == "darwin":
            subprocess.Popen(["open", str(OUTPUT)])
        elif sys.platform == "linux":
            subprocess.Popen(["xdg-open", str(OUTPUT)])
        print("Opened in browser.", flush=True)
    except Exception:
        print(f"Open {OUTPUT} in your browser.", flush=True)

    return 0


if __name__ == "__main__":
    raise SystemExit(main())
