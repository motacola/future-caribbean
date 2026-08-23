#!/usr/bin/env python3
"""Build a cited regional capability graph and match signals to missing links."""
from __future__ import annotations

import json
import sys
import re
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
from pipeline_util import output_path  # noqa: E402

REGISTRY = ROOT / "config" / "regional_capabilities.json"
DISPATCHES = ROOT / "outbox" / "opportunity_dispatches.json"
TENDERS = ROOT / "data" / "tenders" / "latest.json"
GRAPH_OUT = ROOT / "data" / "coordination" / "graph.json"
OPPORTUNITIES_OUT = ROOT / "outbox" / "coordination_opportunities.json"

REQUIRED_CAPABILITIES: dict[str, list[str]] = {
    "development_pipeline": ["construction_delivery", "engineering_services", "project_finance", "professional_services"],
    "supply_chain_signal": ["shipping_logistics", "warehousing_distribution", "industrial_fabrication"],
    "food_security": ["food_processing", "shipping_logistics", "warehousing_distribution"],
    "enhanced_investment": ["project_finance", "professional_services", "digital_services"],
    "investment_signal": ["project_finance", "professional_services"],
    "economic_vulnerability": ["project_finance", "climate_resilience", "professional_services"],
    "ccrif_payout": ["climate_resilience", "construction_delivery", "project_finance"],
    "port_activity_surge": ["shipping_logistics", "warehousing_distribution"],
    "port_congestion": ["shipping_logistics", "warehousing_distribution"],
}

COUNTRY_ALIASES = {
    "caricom": "Caribbean regional demand",
    "trinidad and tobago": "Trinidad & Tobago",
    "st. vincent and the grenadines": "St Vincent & the Grenadines",
}

TENDER_CLASSIFIERS: list[tuple[str, tuple[str, ...], list[str]]] = [
    ("aviation_infrastructure", ("runway", "taxiway", "airstrip", "airport", "aviation"), ["aviation_infrastructure", "civil_engineering", "construction_delivery"]),
    ("water_and_irrigation", ("irrigation", "canal", "drainage", "flood", "water treatment", "intake structure"), ["water_infrastructure", "civil_engineering", "climate_resilience"]),
    ("medical_supplies", ("hospital", "medical", "diathermy", "cartridge", "suction", "pharmaceutical"), ["medical_supply", "shipping_logistics"]),
    ("digital_and_ict", ("ict", "software", "server", "network", "fortigate", "phone", "digital"), ["digital_services", "ict_integration"]),
    ("education_infrastructure", ("school", "laborator", "education", "university", "training"), ["construction_delivery", "education_services"]),
    ("transport_and_logistics", ("port", "bridge", "road", "transport", "warehouse", "freight"), ["civil_engineering", "shipping_logistics", "warehousing_distribution"]),
    ("climate_resilience", ("resilience", "coastal", "sea defence", "early warning", "disaster"), ["climate_resilience", "civil_engineering"]),
    ("construction_and_works", ("construction", "rehabilitation", "reconstruction", "works"), ["construction_delivery", "civil_engineering"]),
]

CAPABILITY_INTERVENTIONS: dict[str, dict[str, str]] = {
    "water_infrastructure": {"owner": "procurement_watcher", "evidence": "Two eligible regional operators with comparable water or irrigation project references"},
    "medical_supply": {"owner": "regional_operator", "evidence": "Two authorised suppliers with product registration and regional delivery evidence"},
    "ict_integration": {"owner": "founder_operator", "evidence": "Two regional integrators with reference deployments and support coverage"},
    "education_services": {"owner": "ecosystem_builder", "evidence": "Two education-sector delivery partners with institutional references"},
    "aviation_infrastructure": {"owner": "procurement_watcher", "evidence": "Two contractors with airside works references and required certifications"},
    "civil_engineering": {"owner": "regional_operator", "evidence": "Two engineering firms with comparable public-works references"},
}

FRICTION_INTERVENTIONS: list[tuple[tuple[str, ...], str, str, str]] = [
    (("eligibility", "qualification"), "eligibility_verification", "procurement_watcher", "Bid eligibility, registrations, and qualification requirements confirmed in writing"),
    (("shipping", "route", "logistics"), "logistics_validation", "regional_operator", "Route, lead time, landed cost, and contingency option validated"),
    (("finance", "ticket-size", "capital"), "finance_fit", "diaspora_investor", "Financing mandate, ticket size, security, and disbursement timing confirmed"),
    (("local delivery", "partner"), "partner_introduction", "ecosystem_builder", "One qualified local delivery partner accepts an introduction"),
    (("small transaction", "pooled"), "demand_aggregation", "ecosystem_builder", "Demand is pooled into a commercially viable package"),
]


def _load(path: Path) -> dict[str, Any]:
    try:
        data = json.loads(path.read_text(encoding="utf-8"))
        return data if isinstance(data, dict) else {}
    except (FileNotFoundError, json.JSONDecodeError, OSError):
        return {}


def _slug(value: str) -> str:
    return re.sub(r"[^a-z0-9]+", "-", value.lower()).strip("-")


def _canonical_country(value: str) -> str:
    value = (value or "").strip()
    return COUNTRY_ALIASES.get(value.lower(), value)


def classify_tender(item: dict[str, Any]) -> dict[str, Any]:
    """Classify procurement demand with ordered, inspectable keyword rules."""
    text = " ".join(str(item.get(key) or "") for key in ("title", "category", "agency")).lower()
    for sector, keywords, capabilities in TENDER_CLASSIFIERS:
        matched = sorted({keyword for keyword in keywords if keyword in text})
        if matched:
            return {"sector": sector, "required_capabilities": capabilities, "matched_keywords": matched, "classification": "deterministic_keyword"}
    fallback = ["construction_delivery", "civil_engineering"] if (item.get("category") or "").lower() == "works" else ["professional_services"]
    return {"sector": "general_procurement", "required_capabilities": fallback, "matched_keywords": [], "classification": "category_fallback"}


def build_unlock_path(project_match: dict[str, Any], frictions: list[str]) -> list[dict[str, Any]]:
    """Translate missing edges and known friction into owned, verifiable interventions."""
    interventions = []
    required_count = max(1, len(project_match.get("required_capabilities", [])))
    for capability in project_match.get("missing_capabilities", []):
        config = CAPABILITY_INTERVENTIONS.get(capability, {
            "owner": "ecosystem_builder",
            "evidence": f"Two verified regional providers demonstrating {capability.replace('_', ' ')} capability",
        })
        interventions.append({
            "id": f"unlock:{_slug(project_match.get('project_id', 'project'))}:capability:{capability}",
            "type": "capability_verification", "blocker": capability, "owner_persona": config["owner"],
            "minimum_evidence_request": config["evidence"],
            "success_condition": f"A cited HAS_CAPABILITY edge for {capability} can be added to an eligible regional node",
            "estimated_score_uplift": round(20 / required_count), "uplift_basis": "complementarity weight divided across required capabilities",
        })
    seen_types = set()
    for friction in frictions:
        lower = friction.lower()
        match = next((row for row in FRICTION_INTERVENTIONS if any(term in lower for term in row[0])), None)
        if not match or match[1] in seen_types:
            continue
        _, intervention_type, owner, success = match
        seen_types.add(intervention_type)
        interventions.append({
            "id": f"unlock:{_slug(project_match.get('project_id', 'project'))}:friction:{intervention_type}",
            "type": intervention_type, "blocker": friction, "owner_persona": owner,
            "minimum_evidence_request": success, "success_condition": success,
            "estimated_score_uplift": 3, "uplift_basis": "one friction-penalty unit removed",
        })
    return interventions


def extract_demand_projects(tender_data: dict[str, Any], limit: int = 8) -> list[dict[str, Any]]:
    """Normalize advertised tenders into cited project-level demand nodes."""
    projects = []
    for item in tender_data.get("items", []):
        country = _canonical_country(item.get("country", ""))
        title = (item.get("title") or "").strip()
        if not country or not title or item.get("status") != "Bid Advertised":
            continue
        classification = classify_tender(item)
        projects.append({
            "id": f"project:{_slug(country)}:{_slug(str(item.get('id') or title))}",
            "source_id": str(item.get("id") or ""),
            "type": "project", "country": country, "title": title,
            "agency": item.get("agency") or "", "category": item.get("category") or "",
            "status": item.get("status") or "", "closing_date": item.get("closing_date"),
            "url": item.get("url") or "", "sector": classification["sector"],
            "required_capabilities": classification["required_capabilities"],
            "classification": classification["classification"], "matched_keywords": classification["matched_keywords"],
            "evidence": [{"source": item.get("source") or "Tenders", "url": item.get("url") or "", "grade": "primary"}],
        })
    projects.sort(key=lambda item: (item.get("closing_date") or "9999-99-99", item["country"], item["id"]))
    return projects[:limit]


def build_graph(registry: dict[str, Any], projects: list[dict[str, Any]] | None = None) -> dict[str, Any]:
    nodes: list[dict[str, Any]] = []
    edges: list[dict[str, Any]] = []
    seen_capabilities: set[str] = set()
    for profile in registry.get("countries", []):
        country = profile["country"]
        country_id = f"country:{_slug(country)}"
        node = {"id": country_id, "type": "country", "label": country, "status": registry.get("status", "pilot")}
        if profile.get("members"):
            node["kind"] = "bloc"
        nodes.append(node)
        # Bloc members become their own geographic nodes; capability edges stay on
        # the bloc, where the cited evidence sits, until island-level evidence is verified.
        for member in profile.get("members", []):
            member_id = f"country:{_slug(member)}"
            nodes.append({"id": member_id, "type": "country", "label": member, "status": registry.get("status", "pilot"), "kind": "bloc_member", "member_of": country_id})
            edges.append({"from": member_id, "to": country_id, "type": "MEMBER_OF", "weight": 1.0, "status": "curated_pilot", "evidence": profile.get("evidence", [])})
        for capability in profile.get("capabilities", []):
            capability_id = capability["id"]
            node_id = f"capability:{capability_id}"
            if capability_id not in seen_capabilities:
                nodes.append({"id": node_id, "type": "capability", "label": capability_id.replace("_", " ").title()})
                seen_capabilities.add(capability_id)
            evidence = [item for item in profile.get("evidence", []) if capability_id in item.get("supports", [])]
            strength = capability.get("strength", 0)
            base_status = capability.get("origin", "curated_pilot")
            # Bloc keeps the cited (bloc-level) capability edge as the evidence-aggregate.
            edges.append({
                "from": country_id,
                "to": node_id,
                "type": "HAS_CAPABILITY",
                "weight": round(max(0, min(5, strength)) / 5, 2),
                "strength": strength,
                "status": base_status,
                "evidence": evidence,
            })
            # Island-as-node principle: each member island is individually scorable.
            # Replicate the bloc capability to members, tagged bloc_replicated so the
            # provenance stays honest (evidence is bloc-level, not island-verified).
            if profile.get("members"):
                for member in profile["members"]:
                    member_id = f"country:{_slug(member)}"
                    edges.append({
                        "from": member_id,
                        "to": node_id,
                        "type": "HAS_CAPABILITY",
                        "weight": round(max(0, min(5, strength)) / 5, 2),
                        "strength": strength,
                        "status": "bloc_replicated",
                        "evidence": evidence,
                    })
    for project in projects or []:
        nodes.append({key: project.get(key) for key in ("id", "type", "title", "country", "agency", "category", "sector", "classification", "status", "closing_date", "url")})
        country_id = f"country:{_slug(project['country'])}"
        if not any(node.get("id") == country_id for node in nodes):
            nodes.append({"id": country_id, "type": "country", "label": project["country"], "status": "observed_demand"})
        edges.append({"from": project["id"], "to": country_id, "type": "LOCATED_IN", "weight": 1.0, "status": "observed", "evidence": project["evidence"]})
        for capability_id in project["required_capabilities"]:
            node_id = f"capability:{capability_id}"
            if capability_id not in seen_capabilities:
                nodes.append({"id": node_id, "type": "capability", "label": capability_id.replace("_", " ").title()})
                seen_capabilities.add(capability_id)
            edges.append({"from": project["id"], "to": node_id, "type": "REQUIRES_CAPABILITY", "weight": 1.0, "status": "inferred_from_category", "evidence": project["evidence"]})
    return {
        "schema_version": 1,
        "generated_at": datetime.now(timezone.utc).isoformat(),
        "registry_status": registry.get("status", "pilot"),
        "nodes": nodes,
        "edges": edges,
        "counts": {"nodes": len(nodes), "edges": len(edges)},
    }


def _candidate_profiles(registry: dict[str, Any], demand_country: str, required: list[str]) -> list[dict[str, Any]]:
    candidates = []
    for profile in registry.get("countries", []):
        if profile.get("country") == demand_country:
            continue
        matches = [c for c in profile.get("capabilities", []) if c.get("id") in required]
        if not matches:
            continue
        evidence = [item for item in profile.get("evidence", []) if set(item.get("supports", [])) & {m["id"] for m in matches}]
        candidates.append({
            "country": profile["country"],
            "matched_capabilities": sorted(matches, key=lambda item: (-item.get("strength", 0), item["id"])),
            "constraints": profile.get("constraints", []),
            "evidence": evidence,
        })
    candidates.sort(key=lambda item: (-sum(c.get("strength", 0) for c in item["matched_capabilities"]), item["country"]))
    return candidates


_OWNER_LABELS = {
    "ecosystem_builder": "the ecosystem builder",
    "procurement_watcher": "the procurement watcher",
    "regional_operator": "the regional operator",
    "founder_operator": "the founder/operator",
    "diaspora_investor": "the diaspora investor",
    "policy_media": "policy/media",
}


def _human_unlock_line(item: dict[str, Any]) -> str:
    """Plain-language rendering of one unlock intervention (no jargon)."""
    owner = _OWNER_LABELS.get(item.get("owner_persona", ""), item.get("owner_persona", "someone"))
    what = item.get("minimum_evidence_request") or item.get("blocker", "this blocker")
    return f"{what} — {owner} owns this, worth about +{item.get('estimated_score_uplift', 0)} to the score."


def _humanized_unlock_path(unlock_items: list[dict[str, Any]]) -> list[str]:
    """Dedup by (type, blocker, owner) and return one plain line per campaign."""
    seen: dict[tuple[str, str, str], dict[str, Any]] = {}
    order: list[tuple[str, str, str]] = []
    for item in unlock_items:
        key = (item["type"], item["blocker"], item["owner_persona"])
        if key not in seen:
            seen[key] = item
            order.append(key)
        else:
            # keep the higher uplift of the duplicates
            if item.get("estimated_score_uplift", 0) > seen[key].get("estimated_score_uplift", 0):
                seen[key] = item
    return [_human_unlock_line(seen[k]) for k in order]


def _human_next_action(dispatch: dict[str, Any], candidates: list[dict[str, Any]], n: int) -> str:
    """Plain-language next step (no procurement-memo jargon)."""
    top = candidates[:n]
    names = ", ".join(c.get("country", "a regional partner") for c in top) or "the top regional partners"
    return (
        f"Before this moves off hold, check with {names}: are they eligible to bid, "
        f"and can they actually deliver? A short call this week answers both. "
        f"If yes, the path opens; if not, we know what's missing."
    )


def _score(dispatch: dict[str, Any], candidates: list[dict[str, Any]], required: list[str]) -> tuple[int, dict[str, int], list[str]]:
    evidence_quality = min(100, 45 + 12 * len({e.get("source") for c in candidates for e in c.get("evidence", [])}))
    matched = {cap["id"] for c in candidates for cap in c["matched_capabilities"]}
    complementarity = round(100 * len(matched) / max(1, len(required)))
    unlockability = max(20, 80 - 8 * len({constraint for c in candidates for constraint in c.get("constraints", [])}))
    recipient_readiness = 75 if dispatch.get("persona_key") in {"regional_operator", "procurement_watcher", "ecosystem_builder"} else 60
    logistics = 75 if "shipping_logistics" in matched else 55
    regional_impact = min(100, 55 + 10 * min(4, len(candidates)))
    friction_penalty = min(25, 3 * len({constraint for c in candidates for constraint in c.get("constraints", [])}))
    components = {
        "evidence_quality": evidence_quality,
        "complementarity": complementarity,
        "unlockability": unlockability,
        "recipient_readiness": recipient_readiness,
        "logistics_feasibility": logistics,
        "regional_impact": regional_impact,
        "friction_penalty": friction_penalty,
    }
    score = round(
        0.25 * evidence_quality + 0.20 * complementarity + 0.20 * unlockability
        + 0.15 * recipient_readiness + 0.10 * logistics + 0.10 * regional_impact
        - friction_penalty
    )
    gates = []
    if len(candidates) < 2:
        gates.append("fewer than two complementary regional nodes")
    if evidence_quality < 55:
        gates.append("insufficient registry evidence")
    if complementarity < 50:
        gates.append("less than half of required capabilities matched")
    return max(0, min(100, score)), components, gates


def build_opportunities(
    registry: dict[str, Any],
    dispatch_data: dict[str, Any],
    projects: list[dict[str, Any]] | None = None,
) -> dict[str, Any]:
    unique: dict[str, dict[str, Any]] = {}
    for dispatch in dispatch_data.get("dispatches", []):
        kind = dispatch.get("signal_kind", "")
        required = REQUIRED_CAPABILITIES.get(kind)
        signal_id = dispatch.get("signal_id", "")
        if not required or not signal_id:
            continue
        existing = unique.get(signal_id)
        if existing is None or dispatch.get("confidence_score", 0) > existing.get("confidence_score", 0):
            unique[signal_id] = dispatch

    opportunities = []
    rejected = []
    for signal_id, dispatch in sorted(unique.items()):
        demand_country = _canonical_country(dispatch.get("country_cluster", ""))
        required = REQUIRED_CAPABILITIES[dispatch["signal_kind"]]
        linked_projects = (projects or []) if dispatch["signal_kind"] == "development_pipeline" else []
        project_matches = []
        for project in linked_projects:
            project_candidates = _candidate_profiles(registry, project["country"], project["required_capabilities"])
            supplied = {cap["id"] for candidate in project_candidates for cap in candidate["matched_capabilities"]}
            project_frictions = sorted({constraint for candidate in project_candidates[:3] for constraint in candidate.get("constraints", [])})
            project_match = {
                "project_id": project["id"], "title": project["title"], "country": project["country"],
                "sector": project["sector"], "required_capabilities": project["required_capabilities"],
                "matched_capabilities": sorted(supplied),
                "missing_capabilities": sorted(set(project["required_capabilities"]) - supplied),
                "candidate_nodes": project_candidates[:3], "frictions": project_frictions,
            }
            project_match["unlock_path"] = build_unlock_path(project_match, project_frictions)
            # Deduped per (type, blocker, owner) — same key as operator campaigns.
            # Each verification serves every project sharing the blocker, so a flat
            # sum over unlock_path over-counts collapsed items (e.g. 4x education_services).
            _pu: dict[tuple[str, str, str], int] = {}
            for _it in project_match["unlock_path"]:
                _k = (_it["type"], _it["blocker"], _it["owner_persona"])
                _pu[_k] = max(_pu.get(_k, 0), _it["estimated_score_uplift"])
            project_match["estimated_total_uplift"] = sum(_pu.values())
            project_matches.append(project_match)
        unlock_items = [item for match in project_matches for item in match["unlock_path"]]
        unlock_items.sort(key=lambda item: (item["type"] != "capability_verification", -item["estimated_score_uplift"], item["id"]))
        # One verification serves every project sharing the blocker, so total uplift
        # counts each (type, blocker, owner) once — same key as operator campaigns.
        deduped_uplift: dict[tuple[str, str, str], int] = {}
        for item in unlock_items:
            key = (item["type"], item["blocker"], item["owner_persona"])
            deduped_uplift[key] = max(deduped_uplift.get(key, 0), item["estimated_score_uplift"])
        candidates = _candidate_profiles(registry, demand_country, required)
        score, components, gates = _score(dispatch, candidates, required)
        matched = {cap["id"] for candidate in candidates for cap in candidate["matched_capabilities"]}
        opportunity = {
            "id": f"coord-{_slug(signal_id)}",
            "title": f"Regional coordination path for {dispatch.get('title', signal_id)}",
            "status": "candidate" if not gates else "screened_out",
            "trigger_signal_id": signal_id,
            "trigger_dispatch_id": dispatch.get("dispatch_id"),
            "signal_kind": dispatch["signal_kind"],
            "demand_node": {"country": demand_country, "summary": dispatch.get("detail") or dispatch.get("title")},
            "demand_projects": linked_projects,
            "demand_countries": sorted({project["country"] for project in linked_projects}) or [demand_country],
            "project_coordination_matches": project_matches,
            "unlock_path": unlock_items,
            "humanized_unlock_path": _humanized_unlock_path(unlock_items),
            "estimated_total_uplift": sum(deduped_uplift.values()),
            "unique_intervention_count": len(deduped_uplift),
            "required_capabilities": required,
            "available_capabilities": sorted(matched),
            "missing_capabilities": sorted(set(required) - matched),
            "contributing_nodes": candidates[:4],
            "frictions": sorted({constraint for candidate in candidates[:4] for constraint in candidate.get("constraints", [])}),
            "minimum_next_action": _human_next_action(dispatch, candidates, min(3, len(candidates))),
            "accountable_recipient": {"persona_key": dispatch.get("persona_key"), "persona_label": dispatch.get("persona_label"), "channel": dispatch.get("channel")},
            "coordination_score": score,
            "score_components": components,
            "ranking_rationale": [
                f"Trigger signal confidence: {dispatch.get('confidence_score', 0)}/100",
                f"Matched {len(matched)} of {len(required)} required capabilities across {len(candidates)} regional nodes",
                f"Registry evidence from {len({e.get('source') for c in candidates for e in c.get('evidence', [])})} primary-source organisations",
            ],
            "evidence": ([e for project in linked_projects for e in project.get("evidence", [])]
                         + [{"source": e.get("source"), "url": e.get("url"), "grade": e.get("grade")} for c in candidates[:4] for e in c.get("evidence", [])]),
            "unknowns": gates,
        }
        (opportunities if not gates else rejected).append(opportunity)

    opportunities.sort(key=lambda item: (-item["coordination_score"], item["id"]))
    summary = {
        "schema_version": 1,
        "generated_at": datetime.now(timezone.utc).isoformat(),
        "engine": "deterministic",
        "registry_status": registry.get("status", "pilot"),
        "count": len(opportunities),
        "screened_out_count": len(rejected),
        "interventions_persisted": False,
        "screened_out": rejected,
    }
    summary["opportunities"] = opportunities
    return summary


def _apply_outcomes(opportunites: list[dict[str, Any]], root: Path = ROOT) -> None:
    """Feed operator-reported outcomes back into each opportunity's score.

    Reads the persisted intervention_state on disk (outcomes an operator
    submitted via submit-outcome), lifts the coordination_score for
    de-risked paths (supplier validated / intro accepted), and honestly
    flags logistics blocks (gap stays open, reason recorded). Pure in-memory
    mutation of the opportunity dicts; engine.run() persists them.
    """
    try:
        from coordination.interventions import _load as _load_state, _outcome_adjustment
    except ImportError:
        from interventions import _load as _load_state, _outcome_adjustment
    state = _load_state(root)
    state_by_id = state.get("interventions", {})
    for opp in opportunites:
        interventions = opp.get("intervention_state") or opp.get("operator_campaigns")
        if not interventions and opp.get("trigger_signal_id"):
            # match persisted interventions by related signal
            interventions = [
                e for e in state_by_id.values()
                if opp["trigger_signal_id"] in (e.get("related_signals") or [])
            ]
        if not interventions:
            continue
        total_delta = 0
        flags: list[str] = []
        for entry in interventions:
            if not isinstance(entry, dict):
                continue
            adj = _outcome_adjustment(entry)
            total_delta += adj.get("delta", 0)
            flags.extend(adj.get("flags", []))
        if total_delta:
            opp["coordination_score"] = max(0, min(100, opp.get("coordination_score", 0) + total_delta))
            comp = opp.setdefault("score_components", {})
            comp["outcome_adjustment"] = total_delta
            rationale = opp.setdefault("ranking_rationale", [])
            rationale.append(
                f"Operator outcomes adjusted score by {total_delta:+d} "
                f"({', '.join(sorted(set(flags)))})"
            )
        if "blocked_logistics" in flags:
            opp.setdefault("frictions", [])
            if "blocked_by_logistics" not in opp["frictions"]:
                opp["frictions"].append("blocked_by_logistics")
            opp.setdefault("unknowns", [])
            if not any("logistics" in str(u).lower() for u in opp.get("unknowns", [])):
                opp["unknowns"].append("Path stalled by logistics — recorded by operator, not resolved.")


def run(root: Path = ROOT) -> tuple[dict[str, Any], dict[str, Any]]:
    registry = _load(root / "config" / "regional_capabilities.json")
    if not registry.get("countries"):
        raise ValueError("regional capability registry is empty")
    try:
        from coordination.interventions import apply_verified_capabilities
    except ImportError:
        from interventions import apply_verified_capabilities
    apply_verified_capabilities(registry, root)
    projects = extract_demand_projects(_load(root / "data" / "tenders" / "latest.json"))
    graph = build_graph(registry, projects)
    opportunities = build_opportunities(registry, _load(root / "outbox" / "opportunity_dispatches.json"), projects)
    # Resolved here, not at import time — the test harness sets the output
    # root after this module has already been imported during collection.
    graph_path = output_path(root / "data" / "coordination" / "graph.json")
    opportunities_path = output_path(root / "outbox" / "coordination_opportunities.json")
    graph_path.parent.mkdir(parents=True, exist_ok=True)
    opportunities_path.parent.mkdir(parents=True, exist_ok=True)
    try:
        from coordination.interventions import apply_interventions
    except ImportError:
        from interventions import apply_interventions
    try:
        for item in opportunities.get("opportunities", []):
            apply_interventions(item, root=root)
        _apply_outcomes(opportunities.get("opportunities", []), root=root)
        # Outcome deltas mutate coordination_score AFTER the list was
        # sorted at build time (Codex P2 on #9): without this re-sort a
        # boosted candidate stays rendered below lower-scored entries.
        opportunities.get("opportunities", []).sort(
            key=lambda item: (-item.get("coordination_score", 0), item.get("id", ""))
        )
        persisted = True
    except Exception:
        persisted = False
    opportunities["interventions_persisted"] = persisted
    opportunities_path.write_text(json.dumps(opportunities, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")
    graph_path.write_text(json.dumps(graph, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")
    return graph, opportunities


def main() -> int:
    graph, opportunities = run()
    print(f"Wrote {GRAPH_OUT.relative_to(ROOT)} ({graph['counts']['nodes']} nodes, {graph['counts']['edges']} edges)")
    print(f"Wrote {OPPORTUNITIES_OUT.relative_to(ROOT)} ({opportunities['count']} candidates, {opportunities['screened_out_count']} screened out)")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
