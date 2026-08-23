"""Opportunity vs Dislocation/Risk track mapping (handover §7 item 2).

The track is a pure function of a signal's ``kind``; these tests pin the
mapping, the unclassified fallback for unknown kinds, and that the dispatch
desk now carries a ``track`` field derived from each cluster's ``signal_kind``
without disturbing the existing fields.
"""
from __future__ import annotations

from pathlib import Path

import ast
import json

from mergers.signal_track import (
    track_for_kind,
    track_label,
    annotated_kinds,
    counts_by_track,
    TRACK_OPPORTUNITY,
    TRACK_RISK,
)

ROOT = Path(__file__).resolve().parents[1]


def test_opportunity_kinds_map_to_opportunity():
    for k in ("investment_signal", "enhanced_investment", "development_pipeline",
              "tourism_impact", "supply_chain_signal", "port_activity_surge",
              "shipping_corridor", "ccrif_payout", "eccb_credit_surge",
              "eccb_deposit_growth"):
        assert track_for_kind(k) == TRACK_OPPORTUNITY, k


def test_risk_kinds_map_to_risk():
    for k in ("cyclone_risk", "maritime_hazard", "economic_vulnerability",
              "food_security", "tropical_development", "active_storm",
              "port_congestion"):
        assert track_for_kind(k) == TRACK_RISK, k


def test_unknown_kind_is_unclassified_not_guessed():
    assert track_for_kind("some_future_kind") is None
    assert track_for_kind("") is None
    assert track_for_kind(None) is None
    assert track_label(None) == "Unclassified"


def test_every_known_kind_is_mapped_exactly_once():
    mapping = annotated_kinds()
    # No kind appears in both tracks.
    opp = {k for k, v in mapping.items() if v == TRACK_OPPORTUNITY}
    risk = {k for k, v in mapping.items() if v == TRACK_RISK}
    assert opp.isdisjoint(risk)
    assert len(opp) == 10
    assert len(risk) == 7


def test_every_kind_emitted_by_merger_has_a_track():
    tree = ast.parse((ROOT / "mergers" / "cross_source_merger.py").read_text())
    emitted = {
        keyword.value.value
        for node in ast.walk(tree)
        if isinstance(node, ast.Call)
        for keyword in node.keywords
        if keyword.arg == "kind" and isinstance(keyword.value, ast.Constant) and isinstance(keyword.value.value, str)
    }
    assert emitted
    assert emitted <= set(annotated_kinds()), sorted(emitted - set(annotated_kinds()))


def test_counts_by_track_totals_correctly():
    counts = counts_by_track(["investment_signal", "cyclone_risk", "food_security", "mystery"])
    assert counts[TRACK_OPPORTUNITY] == 1
    assert counts[TRACK_RISK] == 2
    assert counts["unclassified"] == 1


def test_dispatch_desk_clusters_carry_track_field():
    """The desk must now expose the track without dropping existing fields."""
    desk_path = ROOT / "outbox" / "dispatch_desk.json"
    assert desk_path.exists(), "dispatch desk artifact must ship"
    desk = json.loads(desk_path.read_text())
    clusters = desk.get("clusters") or []
    assert clusters, "dispatch desk must contain clusters"
    for c in clusters:
        assert "track" in c, "cluster missing track field"
        assert "track_label" in c, "cluster missing track_label field"
        # track must be consistent with the cluster's signal_kind
        assert c["track"] == track_for_kind(c.get("signal_kind"))
        # existing fields are untouched
        assert "signal_kind" in c
        assert "cluster_id" in c


def test_persona_dispatches_carry_track_field():
    path = ROOT / "outbox" / "opportunity_dispatches.json"
    assert path.exists(), "opportunity dispatch artifact must ship"
    dispatches = json.loads(path.read_text()).get("dispatches") or []
    assert dispatches
    for dispatch in dispatches:
        assert dispatch["track"] == track_for_kind(dispatch.get("signal_kind"))
        assert dispatch["track_label"] == track_label(dispatch["track"])
