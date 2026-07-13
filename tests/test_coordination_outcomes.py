"""Tests for the coordination outcome model and its feedback into scoring."""
import json
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from coordination import interventions as iv, engine


def _scratch_state(tmp_path: Path) -> Path:
    root = tmp_path / "proj"
    data = root / "data"
    data.mkdir(parents=True, exist_ok=True)
    state = {
        "interventions": {
            "unlock:project-x:friction:logistics_validation": {
                "id": "unlock:project-x:friction:logistics_validation",
                "status": "proposed",
                "owner_persona": "regional_operator",
                "blocker": "route economics",
                "evidence": [],
                "related_signals": ["coord-demo"],
                "created_at": "2026-01-01T00:00:00+00:00",
                "updated_at": "2026-01-01T00:00:00+00:00",
            }
        },
        "campaigns": {},
    }
    (data / "intervention_state.json").write_text(json.dumps(state))
    return root


def test_submit_outcome_unknown_type_rejected(tmp_path):
    root = _scratch_state(tmp_path)
    try:
        iv.submit_outcome("unlock:project-x:friction:logistics_validation",
                          "not_a_real_outcome", root=root)
        assert False, "should have raised"
    except ValueError as e:
        assert "unknown outcome" in str(e)


def test_supplier_validated_lifts_score(tmp_path):
    root = _scratch_state(tmp_path)
    iv.submit_outcome("unlock:project-x:friction:logistics_validation",
                      "supplier_validated",
                      note="Two authorised regional suppliers confirmed", root=root)
    opp = {
        "id": "coord-demo",
        "trigger_signal_id": "coord-demo",
        "coordination_score": 50,
        "score_components": {},
        "ranking_rationale": [],
        "frictions": [],
        "unknowns": [],
        "intervention_state": [
            iv._load(root)["interventions"]["unlock:project-x:friction:logistics_validation"]
        ],
    }
    engine._apply_outcomes([opp], root=root)
    assert opp["coordination_score"] == 54, opp["coordination_score"]
    assert opp["score_components"]["outcome_adjustment"] == 4
    assert any("supplier_validated" in r for r in opp["ranking_rationale"])


def test_blocked_logistics_stays_open_but_flagged(tmp_path):
    root = _scratch_state(tmp_path)
    iv.submit_outcome("unlock:project-x:friction:logistics_validation",
                      "blocked_logistics",
                      note="No viable inter-island freight until Q3", root=root)
    opp = {
        "id": "coord-demo",
        "trigger_signal_id": "coord-demo",
        "coordination_score": 50,
        "score_components": {},
        "ranking_rationale": [],
        "frictions": [],
        "unknowns": [],
        "intervention_state": [
            iv._load(root)["interventions"]["unlock:project-x:friction:logistics_validation"]
        ],
    }
    engine._apply_outcomes([opp], root=root)
    # logistics block gives no score gain
    assert opp["coordination_score"] == 50
    assert "blocked_by_logistics" in opp["frictions"]
    assert any("logistics" in str(u).lower() for u in opp.get("unknowns", []))


def test_intro_accepted_adds_three(tmp_path):
    root = _scratch_state(tmp_path)
    iv.submit_outcome("unlock:project-x:friction:logistics_validation",
                      "intro_accepted", root=root)
    opp = {
        "id": "coord-demo",
        "trigger_signal_id": "coord-demo",
        "coordination_score": 50,
        "score_components": {},
        "ranking_rationale": [],
        "frictions": [],
        "unknowns": [],
        "intervention_state": [
            iv._load(root)["interventions"]["unlock:project-x:friction:logistics_validation"]
        ],
    }
    engine._apply_outcomes([opp], root=root)
    assert opp["coordination_score"] == 53
    assert opp["score_components"]["outcome_adjustment"] == 3


def test_cli_submit_outcome_end_to_end(tmp_path):
    import subprocess
    root = _scratch_state(tmp_path)
    # point the CLI at our scratch root by monkeypatching via env is overkill;
    # instead call the module path through python on the real repo but a scratch copy.
    from coordination import cli
    cli.ROOT = root
    rc = cli.cmd_submit_outcome(_ns(cli.build_parser().parse_args(
        ["submit-outcome", "--id", "unlock:project-x:friction:logistics_validation",
         "--type", "supplier_validated", "--note", "confirmed"])))
    assert rc == 0
    state = iv._load(root)
    assert state["interventions"]["unlock:project-x:friction:logistics_validation"]["outcomes"][0]["type"] == "supplier_validated"


def _ns(parsed):
    return parsed
