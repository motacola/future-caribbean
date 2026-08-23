"""Capability-match resolver contracts (handover §7 item 3).

The claim: a detected tender's required capability is matched to a country
the capability registry already asserts, with the registry's own evidence
grade. The tests pin the honesty rules:

- a tender only matches a country already in the registry;
- an unmatched capability is reported, never guessed;
- the count of classified/matched tenders equals the deterministic result;
- the endpoint filters by country and capability and serves the same
  artefact the page reads.
"""
from __future__ import annotations

import json
from pathlib import Path

from resolvers import capability_match as cm

ROOT = Path(__file__).resolve().parents[1]


def _tender(tender_id, title, sector="", buyer="", state="unresolved"):
    return {
        "tender_id": tender_id,
        "country": "Guyana",
        "title": title,
        "buyer": buyer,
        "sector": sector,
        "lifecycle_state": state,
    }


def _registry_with(capabilities_per_country):
    """Build a minimal registry: {country: [(cap_id, strength, grade)]}."""
    countries = []
    for country, caps in capabilities_per_country.items():
        countries.append({
            "country": country,
            "capabilities": [{"id": c, "strength": s} for c, s, _ in caps],
            "evidence": [
                {"source": "test", "url": "https://t", "grade": g, "supports": [c]}
                for c, s, g in caps
            ],
        })
    return {"status": "pilot", "capability_taxonomy": [], "countries": countries}


# ── registry index ──────────────────────────────────────────────────────

def test_registry_index_maps_capability_to_holders_with_grade():
    reg = _registry_with({"Guyana": [("construction_delivery", 3, "primary")]})
    idx = cm._registry_index(reg)
    holders = idx["construction_delivery"]
    assert len(holders) == 1
    assert holders[0]["country"] == "Guyana"
    assert holders[0]["strength"] == 3
    assert holders[0]["evidence_grades"] == ["primary"]
    assert holders[0]["evidence"] == [{"source": "test", "url": "https://t", "grade": "primary"}]


def test_registry_index_groups_multiple_holders():
    reg = _registry_with({
        "Guyana": [("water_infrastructure", 2, "primary")],
        "Barbados": [("water_infrastructure", 4, "corroborated")],
    })
    idx = cm._registry_index(reg)
    assert len(idx["water_infrastructure"]) == 2


# ── matching ────────────────────────────────────────────────────────────

def test_match_requires_a_classified_sector():
    reg = _registry_with({"Guyana": [("construction_delivery", 3, "primary")]})
    idx = cm._registry_index(reg)
    # "Miscellaneous services" has no keyword → category_fallback, not a match.
    m = cm.match_tender(_tender("x1", "Provision of consultancy services"), idx)
    assert m["classification"] != "deterministic_keyword"
    assert m["has_capability_match"] is False


def test_match_links_required_capability_to_registry_country():
    reg = _registry_with({"Guyana": [("construction_delivery", 3, "primary")]})
    idx = cm._registry_index(reg)
    m = cm.match_tender(_tender("x2", "Construction of a clinic"), idx)
    assert m["has_capability_match"] is True
    cap = next(c for c in m["capability_matches"] if c["capability"] == "construction_delivery")
    assert cap["matched"] is True
    assert cap["holders"][0]["country"] == "Guyana"
    assert cap["holders"][0]["evidence"][0]["url"] == "https://t"


def test_unmatched_capability_is_reported_not_guessed():
    # A required capability with no registry entry must not invent a holder.
    reg = _registry_with({"Guyana": [("construction_delivery", 3, "primary")]})
    idx = cm._registry_index(reg)
    m = cm.match_tender(_tender("x3", "Supply of medical supplies"), idx)
    med = next(c for c in m["capability_matches"] if c["capability"] == "medical_supply")
    assert med["matched"] is False
    assert med["holders"] == []


def test_match_corpus_counts_agree_with_deterministic_classifier():
    reg = _registry_with({
        "Guyana": [("construction_delivery", 3, "primary"), ("water_infrastructure", 2, "primary")],
        "Barbados": [("water_infrastructure", 4, "corroborated")],
    })
    idx = cm._registry_index(reg)
    corpus = {
        "tenders": {
            "a": _tender("a", "Construction of a school"),
            "b": _tender("b", "Water treatment plant intake"),
            "c": _tender("c", "Miscellaneous consultancy"),
        }
    }
    res = cm.match_corpus(corpus, registry=reg)
    assert res["total_tenders"] == 3
    assert res["classified_tenders"] == 2
    assert res["tenders_with_capability_match"] == 2
    assert res["by_capability"]["water_infrastructure"] == 1
    assert res["by_country"]["Guyana"] == 2
    assert res["by_country"]["Barbados"] == 1


def test_best_grade_ranks_primary_over_claimed():
    assert cm.best_grade(["claimed", "primary"]) == "primary"
    assert cm.best_grade(["corroborated", "claimed"]) == "corroborated"
    assert cm.best_grade([None, "claimed"]) == "claimed"


# ── endpoint ────────────────────────────────────────────────────────────

def _load_api():
    import importlib.util
    spec = importlib.util.spec_from_file_location("procurement_outcomes_api", ROOT / "api" / "procurement-outcomes.py")
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    return mod


def test_endpoint_filters_by_capability_and_country():
    api = _load_api()
    matches = [
        {"country": "Guyana", "capability_matches": [{"capability": "water_infrastructure", "matched": True, "holders": []}]},
        {"country": "Jamaica", "capability_matches": [{"capability": "medical_supply", "matched": True, "holders": []}]},
    ]
    assert len(api.filter_capability_matches(matches, {"capability": ["water_infrastructure"]})) == 1
    assert len(api.filter_capability_matches(matches, {"country": ["Guyana"]})) == 1
    assert len(api.filter_capability_matches(matches, {"country": ["Guyana"], "capability": ["medical_supply"]})) == 0


def test_consolidated_vercel_handler_serves_capability_view():
    from io import BytesIO

    api = _load_api()
    out = BytesIO()

    class _Req(api.handler):
        def __init__(self):
            self.path = "/api/procurement-outcomes?view=capability_matches&capability=water_infrastructure&limit=2"
            self._out = out

        def send_response(self, code):
            self._code = code

        def send_header(self, *args):
            pass

        def end_headers(self):
            pass

        wfile = property(lambda self: self)  # type: ignore

        def write(self, body):
            self._out.write(body)

    request = _Req()
    request.do_GET()
    payload = json.loads(out.getvalue())
    assert request._code == 200
    assert payload["registry_status"] == "pilot"
    assert payload["returned"] <= 2
    assert all(
        any(c["capability"] == "water_infrastructure" for c in m["capability_matches"])
        for m in payload["matches"]
    )


def test_endpoint_is_registered_in_the_tool_manifest():
    from api_manifest import TOOLS_MANIFEST
    paths = {t["path"] for t in TOOLS_MANIFEST["tools"]}
    assert "/api/capability-matches" in paths


def test_published_artefact_matches_the_corpus_when_built():
    published = ROOT / "outbox" / "capability_matches.json"
    assert published.exists(), "pipeline artifact must ship for the page and Vercel function"
    payload = json.loads(published.read_text())
    assert payload["schema_version"] == 1
    assert "matches" in payload
    assert "by_capability" in payload
    assert "count_semantics" in payload


def test_pipeline_regenerates_capability_matches():
    pipeline = (ROOT / "run_pipeline.sh").read_text()
    assert 'resolvers/capability_match.py' in pipeline


def test_local_server_routes_both_procurement_surfaces():
    server = (ROOT / "server.py").read_text()
    assert 'path == "/api/procurement-outcomes"' in server
    assert 'path == "/api/capability-matches"' in server
