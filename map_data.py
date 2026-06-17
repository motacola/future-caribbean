"""Build the watched-country data used by the API and dashboard map."""
from __future__ import annotations

import json
from pathlib import Path

WATCHED_COUNTRIES = (
    "Jamaica", "Trinidad & Tobago", "Barbados", "Guyana", "Belize", "Haiti",
    "Dominican Republic", "Puerto Rico", "Bahamas", "Antigua & Barbuda",
    "St Lucia", "Grenada", "Suriname",
    "St Kitts & Nevis", "St Vincent & the Grenadines", "Dominica",
    "Cayman Islands", "Turks & Caicos", "Montserrat",
    "Anguilla", "British Virgin Islands", "US Virgin Islands",
    "Cuba",
)

_ALIASES = {
    "trinidad and tobago": "Trinidad & Tobago",
    "antigua and barbuda": "Antigua & Barbuda",
    "saint lucia": "St Lucia",
    "st. lucia": "St Lucia",
    "st kitts and nevis": "St Kitts & Nevis",
    "saint kitts and nevis": "St Kitts & Nevis",
    "st vincent and the grenadines": "St Vincent & the Grenadines",
    "saint vincent and the grenadines": "St Vincent & the Grenadines",
    "cayman islands": "Cayman Islands",
    "turks and caicos": "Turks & Caicos",
    "turks & caicos": "Turks & Caicos",
    "british virgin islands": "British Virgin Islands",
    "us virgin islands": "US Virgin Islands",
    "u.s. virgin islands": "US Virgin Islands",
}


def canonical_country(value: str) -> str:
    value = (value or "").strip()
    return _ALIASES.get(value.lower(), value)


def _kind(value: str) -> str:
    value = (value or "").lower()
    if "procurement" in value or "development_pipeline" in value:
        return "procurement"
    if "climate" in value or "vulnerability" in value or "food_security" in value:
        return "climate"
    return "investment"


def _load(path: Path) -> dict:
    try:
        return json.loads(path.read_text())
    except (FileNotFoundError, json.JSONDecodeError, OSError):
        return {}


def build_map_data(root: Path) -> list[dict]:
    """Return one stable map entry for every watched country."""
    desk = _load(root / "outbox" / "dispatch_desk.json")
    dispatch_data = _load(root / "outbox" / "opportunity_dispatches.json")
    dispatches = dispatch_data.get("dispatches", []) or []

    dispatches_by_country: dict[str, list[dict]] = {}
    for dispatch in dispatches:
        country = canonical_country(dispatch.get("country_cluster", ""))
        if country in WATCHED_COUNTRIES:
            dispatches_by_country.setdefault(country, []).append(dispatch)

    best_cluster: dict[str, dict] = {}
    signal_counts: dict[str, int] = {}
    for cluster in desk.get("clusters", []) or []:
        country = canonical_country(cluster.get("country_cluster", ""))
        if country not in WATCHED_COUNTRIES:
            continue
        signal_counts[country] = signal_counts.get(country, 0) + 1
        confidence = max(0, min(100, int(cluster.get("confidence_score", 0) or 0)))
        if confidence > int(best_cluster.get(country, {}).get("confidence_score", -1)):
            best_cluster[country] = {**cluster, "confidence_score": confidence}

    result = []
    for country in WATCHED_COUNTRIES:
        cluster = best_cluster.get(country, {})
        country_dispatches = dispatches_by_country.get(country, [])
        lead_dispatch = next(
            (d for d in country_dispatches if d.get("persona_key") == "diaspora_investor"),
            country_dispatches[0] if country_dispatches else {},
        )
        result.append({
            "country": country,
            "confidence": int(cluster.get("confidence_score", 0)),
            "kind": _kind(cluster.get("signal_kind", "")) if cluster else "none",
            "signal_count": signal_counts.get(country, 0),
            "lead_dispatch_id": lead_dispatch.get("dispatch_id"),
            "top_signal_summary": cluster.get("title") or cluster.get("evidence") or "No current signal",
        })
    return result
