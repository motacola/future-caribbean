#!/usr/bin/env python3
"""Climate & Catastrophe Risk — second live Abeng instance.

Reads the already-running hazard watchers (NOAA NWS alerts, NDBC marine
buoys, NHC tropical outlook) and routes them into climate dispatches for
insurers, reinsurers, and resilience planners.

This is the proof that the engine is domain-agnostic: the SAME
watch -> reason -> distribute pipeline, pointed at hazard data instead of
economic data, with no change to the watchers themselves.

Input  (already produced each cycle):
  data/noaa/latest.json   — active weather alerts
  data/ndbc/latest.json   — marine buoy readings + signals
  data/nhc/latest.json    — tropical weather outlook

Output:
  outbox/climate_desk.json — dispatch desk for the climate instance
"""

from __future__ import annotations

import json
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parents[1]

NOAA = ROOT / "data" / "noaa" / "latest.json"
NDBC = ROOT / "data" / "ndbc" / "latest.json"
NHC = ROOT / "data" / "nhc" / "latest.json"
OUT = ROOT / "outbox" / "climate_desk.json"

# Severity → confidence grade (mirrors the economic instance's A/B/C bands)
SEV_GRADE = {
    "Extreme": ("A - official alert", 100),
    "Severe": ("A - official alert", 95),
    "Moderate": ("B - official alert", 80),
    "Minor": ("C - advisory", 60),
    "Unknown": ("C - advisory", 50),
}

# Climate-instance recipient roles (defined in domains/climate-catastrophe.json)
PERSONAS = {
    "insurer": {"label": "Insurer / Reinsurer", "channel": "Email + alert"},
    "resilience_planner": {"label": "Resilience Planner", "channel": "Telegram/SMS alert"},
    "operator_resilience": {"label": "Operations/Resilience", "channel": "Telegram/SMS alert"},
}


def _read(p: Path) -> Any:
    if not p.exists():
        return None
    try:
        return json.loads(p.read_text(encoding="utf-8"))
    except (json.JSONDecodeError, OSError):
        return None


def _first_area(area_desc: str) -> str:
    """Shorten a NWS area string to its first named area."""
    if not area_desc:
        return "Caribbean basin"
    return area_desc.split(";")[0].strip() or "Caribbean basin"


def _personas_for(event_kind: str, detail: str) -> list[dict[str, Any]]:
    """Route a climate signal to its recipient roles with concrete actions."""
    out = []
    if event_kind == "alert":
        out.append({
            "persona": PERSONAS["resilience_planner"]["label"],
            "channel": PERSONAS["resilience_planner"]["channel"],
            "action": f"Active hazard alert — {detail}. Pre-position resources and "
                      f"confirm evacuation/shelter readiness in the affected area now.",
        })
        out.append({
            "persona": PERSONAS["insurer"]["label"],
            "channel": PERSONAS["insurer"]["channel"],
            "action": f"Exposure check — {detail}. Flag policies in the affected zone "
                      f"and prepare parametric-trigger assessment.",
        })
    elif event_kind == "marine":
        out.append({
            "persona": PERSONAS["operator_resilience"]["label"],
            "channel": PERSONAS["operator_resilience"]["channel"],
            "action": f"Marine hazard — {detail}. Advise vessels and coastal operations; "
                      f"delay exposed activity until conditions ease.",
        })
        out.append({
            "persona": PERSONAS["resilience_planner"]["label"],
            "channel": PERSONAS["resilience_planner"]["channel"],
            "action": f"Marine conditions deteriorating — {detail}. Monitor for escalation "
                      f"toward small-craft / coastal-flood thresholds.",
        })
    else:  # tropical
        out.append({
            "persona": PERSONAS["insurer"]["label"],
            "channel": PERSONAS["insurer"]["channel"],
            "action": f"Tropical development watch — {detail}. Begin exposure modelling "
                      f"for the basin; recovery-capital may be needed within days.",
        })
        out.append({
            "persona": PERSONAS["resilience_planner"]["label"],
            "channel": PERSONAS["resilience_planner"]["channel"],
            "action": f"Tropical outlook active — {detail}. Move readiness posture up; "
                      f"verify supply and communication chains across exposed islands.",
        })
    return out


def build_clusters() -> list[dict[str, Any]]:
    clusters: list[dict[str, Any]] = []

    # ── NOAA active alerts ──────────────────────────────────────
    noaa = _read(NOAA) or {}
    alerts = noaa.get("alerts", []) or []
    # Strongest first
    alerts = sorted(
        alerts,
        key=lambda a: SEV_GRADE.get(a.get("severity", "Unknown"), ("", 0))[1],
        reverse=True,
    )
    for a in alerts[:6]:
        sev = a.get("severity", "Unknown")
        grade, score = SEV_GRADE.get(sev, ("C - advisory", 50))
        area = _first_area(a.get("area_desc", ""))
        event = a.get("event", "Weather alert")
        detail = f"{event} — {sev} ({area})"
        clusters.append({
            "cluster_id": f"CLIM-alert-{a.get('id','')[:24]}",
            "country_cluster": area,
            "signal_kind": "hazard_alert",
            "title": f"{area}: {event} in effect ({sev})",
            "evidence": f"NOAA NWS: {a.get('headline', event)}",
            "evidence_grade": grade,
            "confidence_score": score,
            "freshness": "new",
            "decision": "Hazard response and exposure assessment",
            "risk_flags": [f"{sev} {event} active in {area}"] if sev in ("Severe", "Extreme") else [],
            "personas": _personas_for("alert", detail),
        })

    # ── NDBC marine signals ─────────────────────────────────────
    ndbc = _read(NDBC) or {}
    for sig in (ndbc.get("signals_list", []) or [])[:4]:
        # signals_list entries are pre-formatted strings from the buoy poller
        clean = sig.replace("**", "").replace("🌬️", "").replace("🌊", "").replace("📉", "").strip()
        clusters.append({
            "cluster_id": f"CLIM-marine-{abs(hash(sig)) % 100000}",
            "country_cluster": "Caribbean marine zones",
            "signal_kind": "maritime_hazard",
            "title": f"Marine hazard: {clean[:70]}",
            "evidence": f"NDBC buoy network: {clean}",
            "evidence_grade": "B - sensor",
            "confidence_score": 80,
            "freshness": "new",
            "decision": "Marine operations and coastal risk",
            "risk_flags": [],
            "personas": _personas_for("marine", clean[:80]),
        })

    # ── NHC tropical outlook ────────────────────────────────────
    nhc = _read(NHC) or {}
    snap = (nhc.get("snapshot") or {}) if isinstance(nhc, dict) else {}
    outlook = (snap.get("outlook_text") or "").strip()
    if outlook:
        # Heuristic: is anything actually developing?
        low = outlook.lower()
        developing = any(t in low for t in (
            "tropical depression", "tropical storm", "hurricane",
            "area of low pressure", "percent", "formation"
        ))
        has_active = "tropical cyclone formation is not expected" not in low
        if developing and has_active:
            clusters.append({
                "cluster_id": "CLIM-tropical-outlook",
                "country_cluster": "North Atlantic / Caribbean basin",
                "signal_kind": "tropical_development",
                "title": "Tropical development being monitored (NHC outlook)",
                "evidence": "NHC Tropical Weather Outlook indicates a system worth watching across the basin.",
                "evidence_grade": "B - official outlook",
                "confidence_score": 85,
                "freshness": "new",
                "decision": "Basin-wide exposure and readiness",
                "risk_flags": ["Active tropical outlook for the basin"],
                "personas": _personas_for("tropical", "NHC basin outlook active"),
            })

    # ── All-clear baseline ──────────────────────────────────────
    # A quiet cycle is still intelligence: resilience planners and
    # insurers value a confirmed all-clear with current conditions.
    # Built from the always-present NDBC readings + NHC status.
    if not clusters:
        readings = ndbc.get("readings", []) or []
        n_buoys = len(readings)
        waves = [r.get("wave_height_m") for r in readings if r.get("wave_height_m") is not None]
        winds = [r.get("wind_speed_ms") for r in readings if r.get("wind_speed_ms") is not None]
        max_wave = max(waves) if waves else None
        max_wind_kt = round(max(winds) * 1.94384, 0) if winds else None

        nhc2 = _read(NHC) or {}
        snap2 = (nhc2.get("snapshot") or {}) if isinstance(nhc2, dict) else {}
        tropics_quiet = "formation is not expected" in (snap2.get("outlook_text", "") or "").lower()

        cond_bits = []
        if n_buoys:
            cond_bits.append(f"{n_buoys} buoys reporting")
        if max_wave is not None:
            cond_bits.append(f"peak seas {max_wave:.1f}m")
        if max_wind_kt is not None:
            cond_bits.append(f"max wind {max_wind_kt:.0f} kt")
        if tropics_quiet:
            cond_bits.append("no tropical development expected (NHC)")
        conditions = "; ".join(cond_bits) if cond_bits else "monitoring continues"

        clusters.append({
            "cluster_id": "CLIM-allclear",
            "country_cluster": "Caribbean basin",
            "signal_kind": "all_clear",
            "title": "All clear — no active hazards this cycle",
            "evidence": f"No active NWS alerts in Caribbean zones. Current conditions: {conditions}.",
            "evidence_grade": "A - official sources",
            "confidence_score": 70,
            "freshness": "new",
            "decision": "Routine monitoring — no action required",
            "risk_flags": [],
            "personas": [
                {
                    "persona": PERSONAS["resilience_planner"]["label"],
                    "channel": PERSONAS["resilience_planner"]["channel"],
                    "action": f"All clear across Caribbean zones — {conditions}. "
                              f"No action required; the engine keeps watching and will "
                              f"escalate the moment a threshold is crossed.",
                },
                {
                    "persona": PERSONAS["insurer"]["label"],
                    "channel": PERSONAS["insurer"]["channel"],
                    "action": f"No active hazard exposure this cycle ({conditions}). "
                              f"Baseline confirmed for parametric monitoring.",
                },
            ],
        })

    # Strongest signals first
    clusters.sort(key=lambda c: c.get("confidence_score", 0), reverse=True)
    return clusters


def main() -> int:
    clusters = build_clusters()
    dispatch_count = sum(len(c.get("personas", [])) for c in clusters)
    desk = {
        "instance": "climate",
        "instance_label": "Climate & Catastrophe Risk",
        "cycle_id": datetime.now(timezone.utc).strftime("%Y%m%d"),
        "generated_at": datetime.now(timezone.utc).isoformat(),
        "clusters": clusters,
        "dispatch_count": dispatch_count,
        "sources": ["NOAA NWS", "NDBC buoys", "NHC outlook"],
    }
    OUT.parent.mkdir(parents=True, exist_ok=True)
    OUT.write_text(json.dumps(desk, indent=2) + "\n", encoding="utf-8")
    print(f"Wrote {OUT} — {len(clusters)} climate signals, {dispatch_count} dispatches", flush=True)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
