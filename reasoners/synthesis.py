#!/usr/bin/env python3
"""Reasoning agent — cross-signal synthesis for Signal Fabric.

The watchers gather and the packagers route, but raw signals are still a
list. This agent is the "reason" stage: it reads the live dispatches from
every instance and produces a connected narrative — what converges, what
conflicts, and what the timing implies.

Pluggable inference:
  - If an OpenAI-compatible endpoint is configured (LLM_BASE_URL +
    LLM_API_KEY, or OPENAI_API_KEY), the synthesis is model-generated.
    This is exactly how an H200-hosted open model is consumed — point
    LLM_BASE_URL at the inference server and set LLM_MODEL.
  - Otherwise it falls back to a deterministic synthesizer. The output is
    labelled with which engine produced it, so the claim is always honest.

Input:
  outbox/dispatch_desk.json   — economic instance
  outbox/climate_desk.json    — climate instance (optional)

Output:
  outbox/reasoning.json       — { engine, model, thesis, connections[] }
"""

from __future__ import annotations

import json
import os
import re
import urllib.error
import urllib.request
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parents[1]
ECON = ROOT / "outbox" / "dispatch_desk.json"
CLIM = ROOT / "outbox" / "climate_desk.json"
OUT = ROOT / "outbox" / "reasoning.json"


# ── Load + structure the live signals ───────────────────────────

def _read(p: Path) -> dict[str, Any]:
    if not p.exists():
        return {}
    try:
        return json.loads(p.read_text(encoding="utf-8"))
    except (json.JSONDecodeError, OSError):
        return {}


def _pct(title: str) -> float:
    m = re.search(r"([\d.]+)%", title or "")
    return float(m.group(1)) if m else 0.0


def gather_signals() -> dict[str, Any]:
    econ = _read(ECON).get("clusters", [])
    clim = _read(CLIM).get("clusters", [])

    by_country: dict[str, set[str]] = {}
    for c in econ:
        country = c.get("country_cluster", "")
        kind = c.get("signal_kind", "")
        if country and kind:
            by_country.setdefault(country, set()).add(kind)

    # Convergence: a country carrying more than one distinct signal kind
    convergence = {k: sorted(v) for k, v in by_country.items() if len(v) > 1}

    # Conflict: investment signal AND vulnerability in the same country
    conflict = []
    for country, kinds in by_country.items():
        has_invest = any("invest" in k for k in kinds)
        has_vuln = any("vulnerab" in k for k in kinds)
        if has_invest and has_vuln:
            conflict.append(country)

    # Top economic momentum
    momentum = sorted(
        ({"country": c.get("country_cluster", ""), "pct": _pct(c.get("title", "")),
          "kind": c.get("signal_kind", "")} for c in econ if _pct(c.get("title", "")) > 0),
        key=lambda x: x["pct"], reverse=True,
    )

    # Active hazards from the climate instance (an all-clear is not a hazard)
    hazards = [
        {"area": c.get("country_cluster", ""), "title": c.get("title", ""),
         "risk": (c.get("risk_flags") or [None])[0]}
        for c in clim if c.get("signal_kind") != "all_clear"
    ]

    return {
        "n_econ": len(econ),
        "n_climate": len(clim),
        "convergence": convergence,
        "conflict": conflict,
        "momentum": momentum[:5],
        "hazards": hazards[:5],
    }


# ── Deterministic synthesis (fallback) ──────────────────────────

def deterministic_synthesis(s: dict[str, Any]) -> dict[str, Any]:
    parts: list[str] = []
    connections: list[str] = []

    mom = s["momentum"]
    if mom:
        lead = mom[0]
        seen = {lead["country"]}
        others_list = []
        for m in mom[1:]:
            if m["country"] and m["country"] not in seen:
                seen.add(m["country"])
                others_list.append(m["country"])
            if len(others_list) >= 2:
                break
        others = ", ".join(others_list)
        parts.append(
            f"Capital momentum is led by {lead['country']} (+{lead['pct']:.0f}%)"
            + (f", with {others} also moving" if others else "") + "."
        )

    if s["conflict"]:
        names = " and ".join(s["conflict"])
        parts.append(
            f"{names} show investment interest AND elevated vulnerability in the "
            f"same cycle — diligence before capital, not after."
        )
        for c in s["conflict"]:
            connections.append(f"{c}: investment signal × vulnerability flag — validate before deploying")

    for country, kinds in list(s["convergence"].items())[:3]:
        connections.append(f"{country}: {len(kinds)} converging signal types ({', '.join(kinds)})")

    if s["hazards"]:
        h = s["hazards"][0]
        parts.append(
            f"Meanwhile the climate instance shows an active hazard ({h['title']}). "
            f"Where hazard exposure overlaps capital momentum, recovery-capital timing "
            f"and entry timing intersect."
        )
        connections.append(f"Cross-instance: hazard ({h['area']}) overlaps economic momentum window")

    if not parts:
        parts.append("No connected pattern this cycle — signals are independent.")

    return {"thesis": " ".join(parts), "connections": connections}


# ── LLM synthesis (when an endpoint is configured) ──────────────

def _llm_config() -> dict[str, str] | None:
    base = os.environ.get("LLM_BASE_URL") or os.environ.get("OPENAI_BASE_URL")
    key = os.environ.get("LLM_API_KEY") or os.environ.get("OPENAI_API_KEY")
    if not key:
        return None
    return {
        "base": (base or "https://api.openai.com/v1").rstrip("/"),
        "key": key,
        "model": os.environ.get("LLM_MODEL", "gpt-4o-mini"),
    }


def llm_synthesis(s: dict[str, Any], cfg: dict[str, str]) -> dict[str, Any] | None:
    """Call an OpenAI-compatible chat endpoint. Returns None on any failure."""
    prompt = (
        "You are the reasoning agent for a Caribbean regional-intelligence engine. "
        "Below are structured live signals from two instances (economic + climate). "
        "Write a 2-3 sentence connected thesis: what converges, what conflicts, what the "
        "timing implies. Be specific and sober — these are screening signals, not advice. "
        "Then list up to 4 concrete cross-signal connections.\n\n"
        f"SIGNALS:\n{json.dumps(s, indent=2)}\n\n"
        'Respond as JSON: {"thesis": "...", "connections": ["...", "..."]}'
    )
    body = json.dumps({
        "model": cfg["model"],
        "messages": [{"role": "user", "content": prompt}],
        "temperature": 0.4,
        "max_tokens": 500,
    }).encode()
    req = urllib.request.Request(
        f"{cfg['base']}/chat/completions",
        data=body,
        headers={"Authorization": f"Bearer {cfg['key']}", "Content-Type": "application/json"},
    )
    try:
        with urllib.request.urlopen(req, timeout=30) as resp:
            data = json.loads(resp.read().decode("utf-8"))
        content = data["choices"][0]["message"]["content"].strip()
        content = re.sub(r"^```(?:json)?|```$", "", content, flags=re.M).strip()
        parsed = json.loads(content)
        if "thesis" in parsed:
            return {"thesis": parsed["thesis"], "connections": parsed.get("connections", [])}
    except (urllib.error.URLError, json.JSONDecodeError, KeyError, TimeoutError, OSError):
        return None
    return None


# ── Orchestration ───────────────────────────────────────────────

def main() -> int:
    signals = gather_signals()
    cfg = _llm_config()
    engine = "deterministic"
    model = None
    result = None

    if cfg:
        result = llm_synthesis(signals, cfg)
        if result:
            engine = "llm"
            model = cfg["model"]

    if result is None:
        result = deterministic_synthesis(signals)

    payload = {
        "engine": engine,
        "model": model,
        "generated_at": datetime.now(timezone.utc).isoformat(),
        "thesis": result["thesis"],
        "connections": result["connections"],
        "stats": {
            "economic_signals": signals["n_econ"],
            "climate_signals": signals["n_climate"],
            "conflicts": len(signals["conflict"]),
            "convergences": len(signals["convergence"]),
        },
    }
    OUT.parent.mkdir(parents=True, exist_ok=True)
    OUT.write_text(json.dumps(payload, indent=2) + "\n", encoding="utf-8")
    print(f"Wrote {OUT} — engine={engine}"
          + (f" model={model}" if model else "")
          + f", {len(result['connections'])} connections", flush=True)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
