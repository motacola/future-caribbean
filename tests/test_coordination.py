"""Tests for deterministic regional coordination matching."""
import json
from pathlib import Path

from coordination.engine import build_graph, build_opportunities, build_unlock_path, classify_tender, extract_demand_projects, run

ROOT = Path(__file__).resolve().parents[1]


def _registry():
    return json.loads((ROOT / "config" / "regional_capabilities.json").read_text())


def test_graph_has_stable_typed_nodes_and_cited_edges():
    graph = build_graph(_registry())
    assert graph["schema_version"] == 1
    assert {node["type"] for node in graph["nodes"]} == {"country", "capability"}
    countries = [node for node in graph["nodes"] if node["type"] == "country"]
    assert len([node for node in countries if node.get("kind") != "bloc_member"]) == 5
    assert {edge["type"] for edge in graph["edges"]} == {"HAS_CAPABILITY", "MEMBER_OF"}
    assert all(0 <= edge["weight"] <= 1 for edge in graph["edges"])
    assert all(edge["evidence"] for edge in graph["edges"])


def test_bloc_members_are_geographic_nodes_without_capability_claims():
    graph = build_graph(_registry())
    members = [node for node in graph["nodes"] if node.get("kind") == "bloc_member"]
    assert len(members) == 8
    assert all(node["member_of"] == "country:eastern-caribbean-oecs" for node in members)
    member_ids = {node["id"] for node in members}
    # membership edges are cited; no capability edge is claimed at island level
    for member_id in member_ids:
        assert any(e["from"] == member_id and e["type"] == "MEMBER_OF" and e["evidence"] for e in graph["edges"])
        assert not any(e["from"] == member_id and e["type"] == "HAS_CAPABILITY" for e in graph["edges"])
    bloc = next(node for node in graph["nodes"] if node["id"] == "country:eastern-caribbean-oecs")
    assert bloc.get("kind") == "bloc"


def test_development_signal_produces_cross_island_candidate():
    dispatches = {"dispatches": [{
        "signal_id": "pilot-guyana-build",
        "signal_kind": "development_pipeline",
        "country_cluster": "Guyana",
        "title": "Guyana infrastructure demand",
        "detail": "Verified procurement demand",
        "confidence_score": 90,
        "persona_key": "regional_operator",
        "persona_label": "Regional Operator",
        "channel": "Telegram",
        "action_window": "30 days",
        "dispatch_id": "DSP-PILOT-1",
    }]}
    result = build_opportunities(_registry(), dispatches)
    assert result["count"] == 1
    opportunity = result["opportunities"][0]
    assert opportunity["demand_node"]["country"] == "Guyana"
    assert len(opportunity["contributing_nodes"]) >= 2
    assert "project_finance" in opportunity["available_capabilities"]
    assert opportunity["coordination_score"] > 0
    assert opportunity["evidence"]


def test_advertised_tenders_become_cited_project_demand_nodes():
    projects = extract_demand_projects({"items": [{
        "id": "T-1", "title": "Rehabilitate regional runway", "country": "Guyana",
        "status": "Bid Advertised", "category": "Works", "agency": "Aviation Ministry",
        "closing_date": "2026-08-01", "url": "https://example.test/t-1", "source": "Official procurement portal",
    }]})
    assert len(projects) == 1
    assert projects[0]["country"] == "Guyana"
    assert projects[0]["sector"] == "aviation_infrastructure"
    assert projects[0]["required_capabilities"] == ["aviation_infrastructure", "civil_engineering", "construction_delivery"]
    graph = build_graph(_registry(), projects)
    project_id = projects[0]["id"]
    assert any(edge["from"] == project_id and edge["type"] == "LOCATED_IN" for edge in graph["edges"])
    assert any(edge["from"] == project_id and edge["type"] == "REQUIRES_CAPABILITY" for edge in graph["edges"])


def test_tender_classifier_covers_priority_procurement_sectors():
    cases = [
        ({"title": "Supply medical suction equipment", "category": "Goods"}, "medical_supplies", "medical_supply"),
        ({"title": "Install ICT network and servers", "category": "Goods"}, "digital_and_ict", "ict_integration"),
        ({"title": "Construct irrigation canal", "category": "Works"}, "water_and_irrigation", "water_infrastructure"),
        ({"title": "Build school laboratory", "category": "Works"}, "education_infrastructure", "education_services"),
    ]
    for tender, sector, capability in cases:
        result = classify_tender(tender)
        assert result["sector"] == sector
        assert capability in result["required_capabilities"]
        assert result["classification"] == "deterministic_keyword"


def test_project_demand_matches_specific_regional_capabilities():
    dispatches = {"dispatches": [{
        "signal_id": "dev-project", "signal_kind": "development_pipeline",
        "country_cluster": "CARICOM", "title": "Regional projects", "confidence_score": 90,
        "persona_key": "regional_operator", "dispatch_id": "DSP-PROJECT",
    }]}
    projects = extract_demand_projects({"items": [{
        "id": "RUNWAY-1", "title": "Rehabilitate airport runway", "country": "Guyana",
        "status": "Bid Advertised", "category": "Works", "url": "https://example.test/runway",
        "source": "Official procurement portal",
    }]})
    result = build_opportunities(_registry(), dispatches, projects)
    match = result["opportunities"][0]["project_coordination_matches"][0]
    assert match["sector"] == "aviation_infrastructure"
    assert "aviation_infrastructure" in match["matched_capabilities"]
    assert any(node["country"] == "Jamaica" for node in match["candidate_nodes"])


def test_unlock_path_assigns_owner_evidence_and_uplift():
    project_match = {
        "project_id": "project:guyana:water-1",
        "required_capabilities": ["water_infrastructure", "civil_engineering", "climate_resilience"],
        "missing_capabilities": ["water_infrastructure"],
    }
    path = build_unlock_path(project_match, ["procurement eligibility", "shipping cost validation"])
    capability = next(item for item in path if item["type"] == "capability_verification")
    assert capability["owner_persona"] == "procurement_watcher"
    assert "Two eligible regional operators" in capability["minimum_evidence_request"]
    assert capability["estimated_score_uplift"] > 0
    assert {item["type"] for item in path} >= {"eligibility_verification", "logistics_validation"}


def test_run_persists_intervention_state_and_campaigns(tmp_path):
    (tmp_path / "config").mkdir()
    (tmp_path / "outbox").mkdir()
    (tmp_path / "data" / "tenders").mkdir(parents=True)
    (tmp_path / "config" / "regional_capabilities.json").write_text(json.dumps(_registry()))
    (tmp_path / "outbox" / "opportunity_dispatches.json").write_text(json.dumps({
        "dispatches": [{
            "signal_id": "pilot-guyana-build", "signal_kind": "development_pipeline",
            "country_cluster": "Guyana", "title": "Guyana infrastructure demand", "confidence_score": 90,
            "persona_key": "regional_operator", "dispatch_id": "DSP-PILOT-1",
        }]
    }))
    (tmp_path / "data" / "tenders" / "latest.json").write_text(json.dumps({
        "items": [{
            "id": "T-1", "title": "Rehabilitate regional runway", "country": "Guyana",
            "status": "Bid Advertised", "category": "Works", "url": "https://example.test/t-1",
            "source": "Official procurement portal",
        }]
    }))
    graph, opportunities = run(tmp_path)
    assert opportunities["interventions_persisted"] is True
    dev = next((item for item in opportunities.get("opportunities", []) if item.get("signal_kind") == "development_pipeline"), {})
    assert "intervention_state" in dev
    assert "operator_campaigns" in dev
    assert (tmp_path / "data" / "intervention_state.json").exists()


def test_run_writes_real_artifacts(tmp_path):
    (tmp_path / "config").mkdir()
    (tmp_path / "outbox").mkdir()
    (tmp_path / "data" / "tenders").mkdir(parents=True)
    (tmp_path / "config" / "regional_capabilities.json").write_text(json.dumps(_registry()))
    (tmp_path / "outbox" / "opportunity_dispatches.json").write_text(json.dumps({"dispatches": []}))
    (tmp_path / "data" / "tenders" / "latest.json").write_text(json.dumps({"items": []}))
    graph, opportunities = run(tmp_path)
    assert graph["counts"]["nodes"] > 5
    assert opportunities["count"] == 0
    assert (tmp_path / "data" / "coordination" / "graph.json").exists()
    assert (tmp_path / "outbox" / "coordination_opportunities.json").exists()


def _seed_pilot(tmp_path):
    (tmp_path / "config").mkdir()
    (tmp_path / "outbox").mkdir()
    (tmp_path / "data" / "tenders").mkdir(parents=True)
    (tmp_path / "config" / "regional_capabilities.json").write_text(json.dumps(_registry()))
    (tmp_path / "outbox" / "opportunity_dispatches.json").write_text(json.dumps({
        "dispatches": [{
            "signal_id": "pilot-guyana-water", "signal_kind": "development_pipeline",
            "country_cluster": "Guyana", "title": "Guyana water demand", "confidence_score": 90,
            "persona_key": "regional_operator", "dispatch_id": "DSP-PILOT-2",
        }]
    }))
    (tmp_path / "data" / "tenders" / "latest.json").write_text(json.dumps({
        "items": [{
            "id": "W-1", "title": "Construct irrigation canal and drainage", "country": "Guyana",
            "status": "Bid Advertised", "category": "Works", "url": "https://example.test/w-1",
            "source": "Official procurement portal",
        }]
    }))
    return run(tmp_path)


def test_lifecycle_evidence_and_verify_updates_graph_and_track_record(tmp_path):
    from coordination.interventions import add_evidence, verify, get_state

    graph, opportunities = _seed_pilot(tmp_path)
    dev = next(item for item in opportunities["opportunities"] if item["signal_kind"] == "development_pipeline")
    capability_item = next(item for item in dev["unlock_path"] if item["type"] == "capability_verification")
    state_id = capability_item["id"]

    entry = add_evidence(state_id, "Two water-works operators with comparable references",
                         "https://example.test/registry", country="Jamaica", root=tmp_path)
    assert entry["status"] == "evidence_received"
    assert entry["evidence"][-1]["country"] == "Jamaica"

    record = verify(state_id, root=tmp_path)
    state = get_state(tmp_path)
    assert state["interventions"][state_id]["status"] == "verified"
    assert record["verified_edge"] == {"country": "Jamaica", "capability": capability_item["blocker"]}

    graph_after = json.loads((tmp_path / "data" / "coordination" / "graph.json").read_text())
    assert any(
        edge["type"] == "HAS_CAPABILITY" and edge["status"] == "verified_intervention"
        and edge["from"] == "country:jamaica" and edge["to"] == f"capability:{capability_item['blocker']}"
        for edge in graph_after["edges"]
    )
    track = json.loads((tmp_path / "data" / "coordination" / "track_record.json").read_text())
    assert track["outcomes"][-1]["intervention_id"] == state_id
    assert "scores_before" in track["outcomes"][-1] and "scores_after" in track["outcomes"][-1]


def test_lifecycle_rejects_invalid_transitions(tmp_path):
    import pytest
    from coordination.interventions import add_evidence, verify, reject

    graph, opportunities = _seed_pilot(tmp_path)
    dev = next(item for item in opportunities["opportunities"] if item["signal_kind"] == "development_pipeline")
    ids = [item["id"] for item in dev["unlock_path"]]
    capability_id = next(i for i in ids if ":capability:" in i)

    with pytest.raises(ValueError):
        verify(capability_id, root=tmp_path)  # no evidence yet
    with pytest.raises(KeyError):
        add_evidence("unlock:missing:capability:nothing", "s", "src", root=tmp_path)
    with pytest.raises(ValueError):
        add_evidence(capability_id, "", "src", root=tmp_path)

    reject(capability_id, reason="supplier withdrew", root=tmp_path)
    with pytest.raises(ValueError):
        add_evidence(capability_id, "late evidence", "src", root=tmp_path)  # terminal state


def test_opportunity_total_uplift_counts_shared_blockers_once(tmp_path):
    (tmp_path / "config").mkdir()
    (tmp_path / "outbox").mkdir()
    (tmp_path / "data" / "tenders").mkdir(parents=True)
    (tmp_path / "config" / "regional_capabilities.json").write_text(json.dumps(_registry()))
    (tmp_path / "outbox" / "opportunity_dispatches.json").write_text(json.dumps({
        "dispatches": [{
            "signal_id": "pilot-guyana-schools", "signal_kind": "development_pipeline",
            "country_cluster": "Guyana", "title": "Guyana school demand", "confidence_score": 90,
            "persona_key": "regional_operator", "dispatch_id": "DSP-PILOT-3",
        }]
    }))
    (tmp_path / "data" / "tenders" / "latest.json").write_text(json.dumps({
        "items": [
            {"id": f"S-{i}", "title": f"Construct school laboratory block {i}", "country": "Guyana",
             "status": "Bid Advertised", "category": "Works", "url": f"https://example.test/s-{i}",
             "source": "Official procurement portal"}
            for i in range(1, 4)
        ]
    }))
    graph, opportunities = run(tmp_path)
    dev = next(item for item in opportunities["opportunities"] if item["signal_kind"] == "development_pipeline")
    education_items = [item for item in dev["unlock_path"] if item["blocker"] == "education_services"]
    assert len(education_items) == 3  # one per project in the flat path
    keys = {(item["type"], item["blocker"], item["owner_persona"]) for item in dev["unlock_path"]}
    assert dev["unique_intervention_count"] == len(keys)
    assert dev["estimated_total_uplift"] == sum(
        max(i["estimated_score_uplift"] for i in dev["unlock_path"]
            if (i["type"], i["blocker"], i["owner_persona"]) == key)
        for key in keys
    )
    # shared blocker counted once, not three times
    assert dev["estimated_total_uplift"] < sum(i["estimated_score_uplift"] for i in dev["unlock_path"])


def test_verify_capability_requires_country_in_evidence(tmp_path):
    import pytest
    from coordination.interventions import add_evidence, verify

    graph, opportunities = _seed_pilot(tmp_path)
    dev = next(item for item in opportunities["opportunities"] if item["signal_kind"] == "development_pipeline")
    capability_id = next(item["id"] for item in dev["unlock_path"] if item["type"] == "capability_verification")
    add_evidence(capability_id, "References collected", "https://example.test/refs", root=tmp_path)
    with pytest.raises(ValueError):
        verify(capability_id, root=tmp_path)
