"""Smoke test for the local operator console (import + handler wiring)."""
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from coordination import console


def test_console_imports_and_exposes_handler():
    assert hasattr(console, "Handler")
    assert hasattr(console, "main")
    # _commit_hint returns a git command string
    hint = console._commit_hint()
    assert "git add data/intervention_state.json" in hint
    assert "gh pr create" in hint


def test_console_regen_runs():
    # _regenerate should not raise against the repo modules
    interventions, engine = console._load_mods()
    console._regenerate(interventions, engine)
    assert True
