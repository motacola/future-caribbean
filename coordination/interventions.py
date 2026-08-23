"""Persist intervention state and derive operator campaigns."""
from __future__ import annotations

import json
from datetime import datetime, timezone
from pathlib import Path
from typing import Any


ROOT = Path(__file__).resolve().parents[1]

LIFECYCLE_TRANSITIONS: dict[str, set[str]] = {
    "proposed": {"evidence_requested", "rejected", "expired"},
    "evidence_requested": {"evidence_received", "rejected", "expired"},
    "evidence_received": {"verified", "rejected", "expired"},
}
TERMINAL_STATES = {"verified", "rejected", "expired"}
ACTIVE_STATES = {"proposed", "evidence_requested", "evidence_received"}


def _state_path(root: Path) -> Path:
    return root / "data" / "intervention_state.json"


def _load(root: Path) -> dict[str, Any]:
    state_path = _state_path(root)
    if not state_path.exists():
        return {"interventions": {}, "campaigns": {}}
    try:
        payload = json.loads(state_path.read_text(encoding="utf-8"))
    except Exception:
        payload = {"interventions": {}, "campaigns": {}}
    payload.setdefault("interventions", {})
    payload.setdefault("campaigns", {})
    return payload


def _save(payload: dict[str, Any], root: Path) -> None:
    state_path = _state_path(root)
    state_path.parent.mkdir(parents=True, exist_ok=True)
    state_path.write_text(json.dumps(payload, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")


def _now() -> str:
    return datetime.now(timezone.utc).isoformat()


def campaign_slug(intervention_type: str, blocker: str, owner: str) -> str:
    slug = f"campaign-{intervention_type}-{owner}-{blocker}".lower()
    return slug.replace(" ", "-")


def apply_interventions(opportunity: dict[str, Any], root: Path = ROOT) -> dict[str, Any]:
    state = _load(root)
    now = _now()
    mapped: dict[str, dict[str, Any]] = {}
    campaign_groups: dict[str, list[str]] = {}

    for item in opportunity.get("unlock_path", []):
        key = item.get("id")
        if not key:
            continue
        mapped[key] = state["interventions"].setdefault(key, {
            "id": key,
            "status": "proposed",
            "owner_persona": item.get("owner_persona"),
            "blocker": item.get("blocker"),
            "evidence": [],
            "related_signals": [opportunity.get("trigger_signal_id")],
            "created_at": now,
            "updated_at": now,
        })
        mapped[key].setdefault("evidence", [])
        mapped[key].setdefault("related_signals", [])
        mapped[key]["updated_at"] = now
        sig = opportunity.get("trigger_signal_id")
        if sig and sig not in mapped[key].setdefault("related_signals", []):
            mapped[key]["related_signals"].append(sig)
        slug = campaign_slug(item.get("type", ""), item.get("blocker", ""), item.get("owner_persona", ""))
        campaign_groups.setdefault(slug, []).append(key)

    for slug, ids in campaign_groups.items():
        entries = [mapped[key] for key in ids if key in mapped]
        active_count = sum(1 for entry in entries if entry.get("status") in ACTIVE_STATES)
        state["campaigns"][slug] = {
            "slug": slug,
            "intervention_count": len(ids),
            "active_count": active_count,
            "owner_persona": entries[0]["owner_persona"] if entries else None,
            "blocker": entries[0]["blocker"] if entries else None,
            "intervention_type": next((item.get("type") for item in (entries or []) if item.get("type")), None),
            "interventions": ids,
            "updated_at": now,
        }

    _save(state, root)
    opportunity["intervention_state"] = [
        mapped[item["id"]]
        for item in (opportunity.get("unlock_path") or [])
        if item.get("id") in mapped
    ]
    # Scope campaigns to THIS opportunity's interventions (Codex P2 on
    # #9/#10/#11/#12): the global campaign list is shared state — attaching
    # it wholesale made every candidate display the same 9 unrelated
    # intervention rows. Only campaigns whose member interventions belong
    # to this opportunity's unlock path are rendered on its card.
    own_ids = {item.get("id") for item in opportunity.get("intervention_state", [])}
    own_campaigns = [
        c for c in state["campaigns"].values()
        if own_ids & set(c.get("interventions") or [])
    ]
    own_campaigns.sort(key=lambda item: (-item.get("active_count", 0), item.get("slug", "")))
    opportunity["operator_campaigns"] = own_campaigns
    return opportunity


# ── lifecycle: proposed → evidence_requested → evidence_received → verified/rejected/expired ──

def get_state(root: Path = ROOT) -> dict[str, Any]:
    return _load(root)


def _get_entry(state: dict[str, Any], state_id: str) -> dict[str, Any]:
    entry = state["interventions"].get(state_id)
    if entry is None:
        raise KeyError(f"unknown intervention: {state_id}")
    return entry


def _transition(entry: dict[str, Any], new_status: str) -> None:
    current = entry.get("status", "proposed")
    allowed = LIFECYCLE_TRANSITIONS.get(current, set())
    if new_status not in allowed:
        raise ValueError(f"invalid transition {current} -> {new_status} for {entry.get('id')}")
    entry["status"] = new_status
    entry["updated_at"] = _now()


def request_evidence(state_id: str, root: Path = ROOT) -> dict[str, Any]:
    state = _load(root)
    entry = _get_entry(state, state_id)
    _transition(entry, "evidence_requested")
    _save(state, root)
    return entry


def add_evidence(state_id: str, summary: str, source: str, country: str | None = None, root: Path = ROOT) -> dict[str, Any]:
    """Attach cited evidence and advance the intervention to evidence_received."""
    if not summary.strip() or not source.strip():
        raise ValueError("evidence requires a non-empty summary and source")
    state = _load(root)
    entry = _get_entry(state, state_id)
    if entry.get("status") == "proposed":
        _transition(entry, "evidence_requested")
    _transition(entry, "evidence_received")
    record = {"summary": summary.strip(), "source": source.strip(), "submitted_at": _now()}
    if country:
        record["country"] = country.strip()
    entry.setdefault("evidence", []).append(record)
    _save(state, root)
    return entry


def reject(state_id: str, reason: str = "", root: Path = ROOT) -> dict[str, Any]:
    state = _load(root)
    entry = _get_entry(state, state_id)
    _transition(entry, "rejected")
    if reason:
        entry["rejection_reason"] = reason
    _save(state, root)
    return entry


def expire(state_id: str, root: Path = ROOT) -> dict[str, Any]:
    state = _load(root)
    entry = _get_entry(state, state_id)
    _transition(entry, "expired")
    _save(state, root)
    return entry


# ── Outcomes ───────────────────────────────────────────────
# Operator-reported coordination outcomes. These are NOT the hard lifecycle
# (proposed → evidence_received → verified); they are the softer signals
# the user named: an introduction was accepted, a supplier was validated,
# or the path is blocked by logistics. They feed back into scoring
# and are surfaced honestly (a logistics block stays a gap, but we say why).

OUTCOME_TYPES = {
    "intro_accepted",
    "supplier_validated",
    "blocked_logistics",
}


def submit_outcome(state_id: str, outcome_type: str, note: str = "", root: Path = ROOT) -> dict[str, Any]:
    """Record an operator-reported coordination outcome against an intervention."""
    if outcome_type not in OUTCOME_TYPES:
        raise ValueError(f"unknown outcome: {outcome_type} (want one of {sorted(OUTCOME_TYPES)})")
    state = _load(root)
    entry = _get_entry(state, state_id)
    record = {
        "type": outcome_type,
        "note": (note or "").strip(),
        "submitted_at": _now(),
    }
    entry.setdefault("outcomes", []).append(record)
    entry["updated_at"] = _now()
    # A logistics block does not advance the lifecycle, but it is an honest,
    # persistent reason the path is stalled — surfaced (not hidden) downstream.
    if outcome_type == "blocked_logistics":
        entry["blocked_reason"] = (note or "blocked by logistics").strip()
    _save(state, root)
    return entry


def _outcome_adjustment(entry: dict[str, Any]) -> dict[str, Any]:
    """Map an intervention's reported outcomes to a score delta + honest flags.

    Returns {"delta": int, "flags": list[str]}.
    - supplier_validated / intro_accepted on a friction intervention: de-risks it,
      small positive nudge (the path is warmer, not solved).
    - blocked_logistics: no score gain; the gap stays open but we record WHY.
    """
    outcomes = entry.get("outcomes", [])
    if not outcomes:
        return {"delta": 0, "flags": []}
    types = {o.get("type") for o in outcomes}
    delta = 0
    flags: list[str] = []
    if "supplier_validated" in types:
        delta += 4
        flags.append("supplier_validated")
    if "intro_accepted" in types:
        delta += 3
        flags.append("intro_accepted")
    if "blocked_logistics" in types:
        flags.append("blocked_logistics")
    return {"delta": delta, "flags": flags}


def _capability_from_id(state_id: str) -> str | None:
    if ":capability:" in state_id:
        return state_id.rsplit(":capability:", 1)[1] or None
    return None


def _opportunity_scores(root: Path) -> dict[str, int]:
    path = root / "outbox" / "coordination_opportunities.json"
    try:
        payload = json.loads(path.read_text(encoding="utf-8"))
    except (FileNotFoundError, json.JSONDecodeError, OSError):
        return {}
    return {item["id"]: item.get("coordination_score", 0) for item in payload.get("opportunities", [])}


def verify(state_id: str, root: Path = ROOT) -> dict[str, Any]:
    """Mark an intervention verified, push its cited edge into the graph, and record before/after scores."""
    state = _load(root)
    entry = _get_entry(state, state_id)
    if entry.get("status") != "evidence_received":
        raise ValueError(f"cannot verify {state_id}: status is {entry.get('status')}, needs evidence_received")
    evidence = entry.get("evidence") or []
    if not evidence:
        raise ValueError(f"cannot verify {state_id}: no evidence on record")
    capability = _capability_from_id(state_id)
    if capability:
        country = next((item.get("country") for item in reversed(evidence) if item.get("country")), None)
        if not country:
            raise ValueError(f"cannot verify {state_id}: capability verification needs evidence naming a country")
        entry["verified_edge"] = {"country": country, "capability": capability}
    before = _opportunity_scores(root)
    _transition(entry, "verified")
    entry["verified_at"] = _now()
    _save(state, root)

    from coordination.engine import run as engine_run
    engine_run(root)
    after = _opportunity_scores(root)

    record = {
        "intervention_id": state_id,
        "verified_at": entry["verified_at"],
        "verified_edge": entry.get("verified_edge"),
        "scores_before": before,
        "scores_after": after,
        "score_changes": {
            opp_id: {"before": before.get(opp_id), "after": after.get(opp_id)}
            for opp_id in sorted(set(before) | set(after))
            if before.get(opp_id) != after.get(opp_id)
        },
    }
    track_path = root / "data" / "coordination" / "track_record.json"
    try:
        track = json.loads(track_path.read_text(encoding="utf-8"))
    except (FileNotFoundError, json.JSONDecodeError, OSError):
        track = {"schema_version": 1, "outcomes": []}
    track.setdefault("outcomes", []).append(record)
    track_path.parent.mkdir(parents=True, exist_ok=True)
    track_path.write_text(json.dumps(track, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")
    return record


def apply_verified_capabilities(registry: dict[str, Any], root: Path = ROOT) -> dict[str, Any]:
    """Merge verified capability interventions into the in-memory registry before graph build."""
    state = _load(root)
    for entry in state["interventions"].values():
        if entry.get("status") != "verified":
            continue
        edge = entry.get("verified_edge") or {}
        country, capability = edge.get("country"), edge.get("capability")
        if not country or not capability:
            continue
        profile = next((p for p in registry.setdefault("countries", []) if p.get("country") == country), None)
        if profile is None:
            profile = {"country": country, "capabilities": [], "constraints": [], "evidence": []}
            registry["countries"].append(profile)
        if not any(c.get("id") == capability for c in profile.setdefault("capabilities", [])):
            profile["capabilities"].append({"id": capability, "strength": 2, "origin": "verified_intervention"})
        for item in entry.get("evidence", []):
            profile.setdefault("evidence", []).append({
                "source": item.get("source", ""), "url": item.get("url", ""),
                "grade": "verified_intervention", "supports": [capability],
                "intervention_id": entry.get("id"),
            })
    return registry
