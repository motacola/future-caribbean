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


def json_for_script(data: Any) -> str:
    """Serialize JSON safely inside a script tag."""
    text = json.dumps(data, ensure_ascii=False)
    return text.replace("</", "<\\/")


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



def extract_dispatch_desk_product(path: Path) -> dict[str, Any]:
    """Read the judge/product-facing Dispatch Desk clusters."""
    data = read_json(path) or {}
    clusters = data.get("clusters", [])
    if not isinstance(clusters, list):
        clusters = []
    return {
        "cycle_id": data.get("cycle_id", "unknown"),
        "cluster_count": data.get("cluster_count", len(clusters)),
        "dispatch_count": data.get("dispatch_count", 0),
        "persona_count": data.get("persona_count", 0),
        "channel_count": data.get("channel_count", 0),
        "regional_thesis": data.get("regional_thesis", ""),
        "why_now": data.get("why_now", []),
        "boost_lines": data.get("boost_lines", []),
        "clusters": clusters,
    }


def render_product_clusters(product_desk: dict[str, Any]) -> str:
    """Render top Dispatch Desk clusters as the primary product view."""
    clusters = product_desk.get("clusters", [])[:4]
    if not clusters:
        return '<p class="tp">No Dispatch Desk clusters yet — run pipeline first.</p>'
    html = ""
    for idx, cluster in enumerate(clusters, 1):
        title = esc(cluster.get("title", "Untitled decision cluster"))
        decision = esc(clip_sentence(str(cluster.get("decision", "Decision not recorded.")), 180))
        evidence = esc(clip_sentence(str(cluster.get("evidence", "Evidence unavailable.")), 160))
        score = esc(cluster.get("confidence_score", 0))
        grade = esc(cluster.get("evidence_grade", "grade n/a"))
        feedback_summary = esc(clip_sentence(str(cluster.get("feedback_summary", "No feedback yet.")), 150))
        risk_flags = cluster.get("risk_flags", []) or []
        risks = ""
        if risk_flags:
            risks = '<div class="riskline">Risk: ' + esc("; ".join(str(r) for r in risk_flags[:2])) + '</div>'
        routes = ""
        for route in (cluster.get("personas", []) or [])[:4]:
            persona = esc(route.get("persona", "Persona"))
            channel = esc(route.get("channel", "channel"))
            action = esc(clip_sentence(str(route.get("action", "Review dispatch.")), 135))
            feedback = esc(str(route.get("feedback_status", "awaiting")).replace("_", " "))
            dispatch_id = esc(route.get("dispatch_id", ""))
            routes += f'<div class="route"><div><b>{persona}</b><span>{channel} · {dispatch_id}</span></div><p>{action}</p><em>{feedback}</em></div>'
        if len(cluster.get("personas", []) or []) > 4:
            routes += f'<div class="route more">+{len(cluster.get("personas", [])) - 4} more route(s) in dispatch_desk.md</div>'
        html += f"""
        <section class="cluster-card">
          <div class="cluster-index">{idx:02d}</div>
          <div class="cluster-main">
            <h3>{title}</h3>
            <p class="decision"><strong>Decision:</strong> {decision}</p>
            <div class="meta-line"><span>{score}/100</span><span>{grade}</span><span>{feedback_summary}</span></div>
            <p class="evidence"><strong>Evidence:</strong> {evidence}</p>
            {risks}
            <div class="routes">{routes}</div>
          </div>
        </section>
        """
    return html

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
    telegram_brief_text: str,
    dispatch_summary: dict[str, Any],
    feedback: dict,
    persona_counts: dict[str, int],
    dispatch_desk: dict | None = None,
    product_desk: dict | None = None,
    routing_rules: list[dict[str, Any]] | None = None,
    boost_html: str = "",
    product_json: str = "",
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

    # ── Product Dispatch Desk view ───────────────────────
    product = product_desk or {}
    product_clusters_html = render_product_clusters(product)
    product_cycle = esc(product.get("cycle_id", "unknown"))
    product_cluster_count = esc(product.get("cluster_count", 0))
    product_dispatch_count = esc(product.get("dispatch_count", dispatch_summary.get("total_dispatches", 0)))
    product_persona_count = esc(product.get("persona_count", len(persona_counts)))
    product_channel_count = esc(product.get("channel_count", 0))
    product_thesis = esc(product.get("regional_thesis") or thesis_para or "No regional thesis generated yet.")
    product_why_now = ""
    for item in (product.get("why_now", []) or [])[:3]:
        product_why_now += f"<li>{esc(item)}</li>"
    if not product_why_now:
        product_why_now = "<li>No seasonal trigger recorded this cycle.</li>"

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
                f"background:#f3ead8; border-radius:4px;'>"
                f"<strong style='color:#21180f;'>{kl}</strong> → "
                f"<span style='color:#8a3b12;'>{personas}</span><br>"
                f"<span style='font-size:11px; color:#6b4b2f;'>{rationale}</span>"
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

    # ── User-facing Telegram pulse preview ───────────────
    telegram_preview = esc(telegram_brief_text.strip() or "No Telegram pulse generated yet — run pipeline first.")
    telegram_chars = len(telegram_brief_text.strip())

    html = f"""<!DOCTYPE html>
<html lang="en">
<head>
<meta charset="UTF-8">
<meta name="viewport" content="width=device-width, initial-scale=1.0">
<title>Caribbean Opportunity Dispatch — Dispatch Desk</title>
<style>
* {{ margin:0; padding:0; box-sizing:border-box; }}
body {{ font-family:Georgia,'Times New Roman',serif; background:#f3ead8; color:#21180f; padding:24px; }}
h1,h2,h3,h4 {{ font-weight:700; }}
a {{ color:#8a3b12; text-decoration:none; }}
code, pre {{ font-family:'SF Mono',Menlo,Consolas,monospace; }}

/* ── Header ──────────────────────────────────────────── */
.hdr {{ display:flex; justify-content:space-between; align-items:flex-start; margin-bottom:20px; padding-bottom:14px; border-bottom:2px solid #21180f; }}
.hdr-l {{ display:flex; flex-direction:column; gap:2px; }}
.hdr-l h1 {{ font-size:clamp(28px,4vw,54px); font-weight:800; color:#21180f; letter-spacing:-1.4px; line-height:.95; max-width:780px; }}
.hdr-l .tagline {{ color:#5f4b36; font-size:15px; max-width:680px; }}
.hdr-r {{ text-align:right; }}
.hdr-r .badge {{ display:inline-block; background:#21180f; color:#f8ead0; padding:5px 10px; border-radius:999px; font-size:11px; font-weight:700; letter-spacing:0.5px; border:1px solid #21180f; }}
.badges {{ display:flex; gap:8px; margin-top:6px; flex-wrap:wrap; justify-content:flex-end; }}
.badges .badge {{ background:#ead9bd; color:#5f4b36; font-size:11px; }}
.product-note {{ margin:-4px 0 18px; padding:12px 14px; border:1px solid #b4874c; background:#fff7e8; border-radius:0; color:#3b2a1b; font-size:14px; line-height:1.45; }}
.product-note strong {{ color:#8a3b12; }}

/* ── Layout ──────────────────────────────────────────── */
.grid2 {{ display:grid; grid-template-columns:1fr 1fr; gap:14px; margin-bottom:16px; }}
.grid3 {{ display:grid; grid-template-columns:1fr 1fr 1fr; gap:14px; margin-bottom:16px; }}
.panel {{ background:#fff7e8; border-radius:0; padding:16px; border:1px solid #d7bd91; }}
.panel.product {{ border:2px solid #21180f; background:#fdf1d7; }}
.panel-full {{ grid-column:1/-1; }}
.ph {{ display:flex; justify-content:space-between; align-items:center; margin-bottom:10px; }}
.ph h2 {{ font-size:12px; font-weight:800; color:#6b4b2f; text-transform:uppercase; letter-spacing:1.2px; }}
.ph .val {{ font-size:20px; font-weight:800; color:#21180f; }}


/* ── Dispatch Desk product surface ───────────────────── */
.track-chain {{ display:flex; flex-wrap:wrap; gap:8px; margin:12px 0 16px; }}
.track-chain span {{ background:#21180f; color:#f8ead0; padding:7px 10px; border-radius:0; font-size:12px; font-weight:800; text-transform:uppercase; letter-spacing:.8px; }}
.desk-summary {{ display:grid; grid-template-columns:repeat(4,1fr); gap:10px; margin:12px 0 16px; }}
.desk-summary div {{ border-left:4px solid #8a3b12; padding:8px 10px; background:#f3ead8; }}
.desk-summary b {{ display:block; font-size:26px; color:#21180f; line-height:1; }}
.desk-summary span {{ color:#6b4b2f; font-size:11px; text-transform:uppercase; letter-spacing:.8px; }}
.cluster-card {{ display:grid; grid-template-columns:54px 1fr; gap:14px; border-top:2px solid #21180f; padding:16px 0; }}
.cluster-index {{ font-size:28px; font-weight:900; color:#8a3b12; font-family:Georgia,'Times New Roman',serif; }}
.cluster-main h3 {{ font-size:22px; line-height:1.05; color:#21180f; margin-bottom:8px; }}
.decision,.evidence {{ font-size:14px; line-height:1.45; color:#3b2a1b; margin:6px 0; }}
.meta-line {{ display:flex; flex-wrap:wrap; gap:6px; margin:8px 0; }}
.meta-line span {{ background:#ead9bd; border:1px solid #d0ad76; padding:4px 8px; font-size:11px; font-weight:800; color:#3b2a1b; }}
.riskline {{ margin:8px 0; color:#7f1d1d; font-weight:800; font-size:13px; }}
.routes {{ display:grid; grid-template-columns:repeat(auto-fit,minmax(240px,1fr)); gap:8px; margin-top:10px; }}
.route {{ background:#fffaf0; border:1px solid #d7bd91; padding:10px; min-height:92px; }}
.route div {{ display:flex; justify-content:space-between; gap:8px; align-items:flex-start; }}
.route b {{ color:#21180f; font-size:13px; }}
.route span {{ color:#7a6248; font-size:10px; text-align:right; }}
.route p {{ margin:6px 0; color:#3b2a1b; font-size:12px; line-height:1.35; }}
.route em {{ color:#8a3b12; font-style:normal; font-size:11px; font-weight:800; text-transform:uppercase; }}
.route.more {{ color:#6b4b2f; font-size:12px; min-height:0; }}
.product-columns {{ display:grid; grid-template-columns:1.2fr .8fr; gap:16px; margin-top:14px; }}
.product-columns ul {{ margin-left:18px; color:#3b2a1b; line-height:1.55; font-size:13px; }}

/* ── Watcher cards ───────────────────────────────────── */
.wg {{ display:grid; grid-template-columns:repeat(auto-fill,minmax(200px,1fr)); gap:10px; margin-bottom:16px; }}
c {{ background:#fff7e8; border-radius:6px; padding:10px; border:1px solid #d7bd91; border-left:3px solid #3b82f6; }}
ch {{ display:flex; align-items:center; gap:6px; margin-bottom:6px; }}
ci {{ font-size:16px; }}
ct {{ font-weight:600; font-size:12px; flex:1; }}
cs {{ font-size:12px; }}
ca {{ font-size:11px; color:#6b4b2f; }}
cs2 {{ display:flex; flex-wrap:wrap; gap:4px; }}
s {{ background:#ead9bd; padding:2px 8px; border-radius:10px; font-size:11px; font-weight:500; }}
cf {{ font-size:10px; color:#7a6248; margin-top:6px; padding-top:6px; border-top:1px solid #ead9bd; }}

/* ── Dispatches table ────────────────────────────────── */
dt {{ width:100%; border-collapse:collapse; font-size:12px; }}
dt td {{ padding:4px 8px; border-bottom:1px solid #ead9bd; color:#3b2a1b; }}
dt tr.im td {{ color:#f87171; font-weight:600; }}

/* ── Persona bars ────────────────────────────────────── */
pb {{ display:flex; align-items:center; gap:8px; margin:4px 0; }}
pl {{ width:160px; font-size:11px; color:#8898b8; text-align:right; }}
pv {{ width:28px; font-size:11px; font-weight:600; color:#21180f; text-align:right; }}
pbar {{ height:14px; background:#3b82f6; border-radius:3px; min-width:6px; }}

/* ── Feedback ────────────────────────────────────────── */
frow {{ font-size:12px; padding:2px 0; color:#3b2a1b; }}

/* ── Thesis / Why Now ────────────────────────────────── */
tp {{ font-size:13px; line-height:1.5; color:#3b2a1b; }}
wrow {{ font-size:12px; padding:2px 0; color:#3b2a1b; }}
.pulse-wrap {{ display:grid; grid-template-columns:minmax(0,1.25fr) minmax(240px,.75fr); gap:14px; align-items:start; }}
.pulse-preview {{ background:#f8fafc; border:1px solid #bfdbfe; border-radius:16px; padding:16px 18px; white-space:pre-wrap; color:#0f172a; font-size:13px; line-height:1.5; max-height:520px; overflow:auto; box-shadow:0 18px 45px rgba(15,23,42,.28); }}
.interaction-card {{ background:#fffaf0; border:1px solid #d7bd91; border-radius:8px; padding:12px; }}
.interaction-card h3 {{ color:#21180f; font-size:13px; margin-bottom:8px; }}
.interaction-card ul {{ margin-left:18px; color:#3b2a1b; font-size:12px; line-height:1.65; }}
.interaction-card li code {{ color:#93c5fd; }}

/* ── Analyst Rail ─────────────────────────────────────── */
.analyst-rail {{
  border: 2px solid #21180f;
  background: #fffaf0;
  padding: 14px;
  position: sticky;
  top: 14px;
}}
.analyst-rail h2 {{
  font-size: 18px;
  color: #21180f;
  margin-bottom: 8px;
}}
.analyst-prompts {{
  display: flex;
  flex-wrap: wrap;
  gap: 6px;
  margin: 10px 0;
}}
.analyst-prompts button,
.ask-row button {{
  border: 1px solid #21180f;
  background: #21180f;
  color: #f8ead0;
  padding: 7px 9px;
  font: inherit;
  font-size: 12px;
  cursor: pointer;
}}
.ask-row {{
  display: grid;
  grid-template-columns: 1fr auto;
  gap: 6px;
}}
.ask-row input {{
  border: 1px solid #b4874c;
  background: #fdf1d7;
  padding: 8px;
  color: #21180f;
  font: inherit;
  font-size: 13px;
}}
.answer-box {{
  margin-top: 10px;
  padding: 12px;
  background: #f3ead8;
  border-left: 4px solid #8a3b12;
  white-space: pre-wrap;
  font-size: 13px;
  line-height: 1.45;
  max-height: 420px;
  overflow: auto;
}}
.copy-answer {{
  margin-top: 8px;
  background: transparent !important;
  color: #8a3b12 !important;
}}

/* ── Footer ──────────────────────────────────────────── */
.ft {{ text-align:center; color:#7a6248; font-size:11px; padding:16px 0; border-top:1px solid #ead9bd; margin-top:16px; }}

@media(max-width:800px){{ .grid2,.grid3,.pulse-wrap {{ grid-template-columns:1fr; }} }}
</style>
</head>
<body>

<div class="hdr">
<div class="hdr-l">
<h1>Caribbean Opportunity Dispatch</h1>
<div class="tagline">Routed opportunity and risk dispatches from fragmented Caribbean public data.</div>
</div>
<div class="hdr-r">
<div class="badge">DISPATCH DESK</div>
<div class="badges">
<span class="badge">{total_signals} composite signals</span>
<span class="badge">{total_ok}/{total_sources} sources online</span>
<span class="badge">{now[:16]}</span>
</div>
</div>
</div>

<div class="product-note"><strong>Track 08 product surface:</strong> this is a decision desk, not a dashboard-first demo and not a Telegram digest. It shows the chain from fragmented data to routed persona action, then proves delivery and feedback adaptation below.</div>

<div class="panel panel-full product">
<div class="ph"><h2>Dispatch Desk — Cycle {product_cycle}</h2><span class="val">{product_cluster_count} clusters</span></div>
<div class="track-chain"><span>Data</span><span>Signal</span><span>Packaging</span><span>Distribution</span><span>Action</span><span>Capital</span></div>
<div class="desk-summary">
<div><b>{total_signals}</b><span>composite signals</span></div>
<div><b>{product_cluster_count}</b><span>decision clusters</span></div>
<div><b>{product_dispatch_count}</b><span>persona routes</span></div>
<div><b>{product_persona_count}</b><span>personas reached</span></div>
</div>
<p class="tp"><strong>Regional read:</strong> {product_thesis}</p>
<div class="product-columns">
<div>
<div class="ph"><h2>Priority Decision Clusters</h2></div>
{product_clusters_html}
</div>
<div>
<div class="ph"><h2>Why This Cycle Matters</h2></div>
<ul>{product_why_now}</ul>
<div class="analyst-rail">
  <h2>Ask the Dispatch Desk</h2>
  <p class="tp">Interrogate the cycle without reading every artifact. Answers are deterministic and cite local files. Feedback is copy-command only in the static page — the browser does not write files.</p>
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
  <div id="desk-answer" class="answer-box">Try "Explain lead signal" or ask about Guyana, Belize, investors, procurement, or feedback.</div>
  <button id="copy-answer" class="copy-answer">Copy answer</button>
</div>
<div class="ph" style="margin-top:18px"><h2>Delivery Channels</h2><span class="val">{product_channel_count}</span></div>
<p class="tp">Telegram and email are adapters. The product output is the routed dispatch cluster and persona packet.</p>
<div class="ph" style="margin-top:18px"><h2>Notification Preview</h2></div>
<pre class="pulse-preview">{telegram_preview}</pre>
</div>
</div>
</div>

<div class="grid3" style="margin-top:16px">
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
<div style="margin-top:8px; padding-top:8px; border-top:1px solid #ead9bd;">
<div class="ph" style="margin-bottom:4px"><h3>Feedback Intake</h3></div>
<frow style="font-size:11px; color:#6b4b2f;">Use <code>feedback_intake.py</code> to record outcomes:</frow>
<frow style="font-size:11px; font-family:monospace; color:#7a6248;">
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
Caribbean Opportunity Dispatch — Dispatch Desk + Operator Audit<br>
Generated {now}<br>
Sources: World Bank, IDB, NOAA NWS, NDBC Buoys, CARICOM Statistics, CDB
</div>

<script>
window.DISPATCH_DESK = __PRODUCT_JSON__;
__ANALYST_JS__
</script>

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
    telegram_brief_text = read_textfile(ROOT / "outbox" / "telegram_brief.md", max_lines=80)
    dispatch_summary = extract_dispatch_summary(ROOT / "outbox" / "opportunity_dispatches.json")
    product_desk = extract_dispatch_desk_product(ROOT / "outbox" / "dispatch_desk.json")
    product_json = json_for_script(product_desk)

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

    # ── Analyst JS (injected post-template to avoid f-string brace issues) ──
    analyst_js = r"""
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
      `Lead signal: ${c.title}`, `Decision: ${c.decision}`,
      `Evidence: ${c.evidence} (${c.evidence_grade})`,
      `Confidence: ${c.confidence_score}/100; freshness=${c.freshness}`,
      `Feedback: ${c.feedback_summary}`, '', 'Persona routes:', routes, cite()
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
    const boosts = (desk.boost_lines || []).slice(0, 6).map(x => `- ${x}`).join('\\n') || '- No active feedback boosts.';
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

  function run(question) { answerBox.textContent = answer(question); }

  document.querySelectorAll('[data-question]').forEach(btn => {
    btn.addEventListener('click', () => { input.value = btn.dataset.question; run(btn.dataset.question); });
  });
  askButton.addEventListener('click', () => run(input.value));
  input.addEventListener('keydown', (event) => { if (event.key === 'Enter') run(input.value); });
  copyButton.addEventListener('click', async () => {
    try { await navigator.clipboard.writeText(answerBox.textContent); copyButton.textContent = 'Copied'; }
    catch (_) { copyButton.textContent = 'Select + copy manually'; }
    setTimeout(() => { copyButton.textContent = 'Copy answer'; }, 1500);
  });
})();
"""

    # ── Generate ───────────────────────────────────────────
    html = generate_html(
        watcher_stats,
        thesis_text,
        whynow_text,
        telegram_brief_text,
        dispatch_summary,
        feedback,
        persona_counts,
        dispatch_desk=dispatch_desk,
        product_desk=product_desk,
        routing_rules=routing_rules,
        boost_html=boost_html,
        product_json=product_json,
    )
    html = html.replace("__ANALYST_JS__", analyst_js)
    OUTPUT.write_text(
        html.replace("__PRODUCT_JSON__", product_json), encoding="utf-8"
    )
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
