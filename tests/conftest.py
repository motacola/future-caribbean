"""Test harness guards.

A test run must never change what the live site publishes. Several packagers
write artefacts the site serves — and one of them runs in a subprocess, so
monkeypatching cannot reach it. Instead every writer resolves its destination
through `pipeline_util.output_path()`, and this fixture points that at a temp
directory for the whole session.

The guard is autouse and session-scoped so it cannot be forgotten by a test
added later, which is what happened the first time round.
"""
from __future__ import annotations

import os
import subprocess
import sys
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from pipeline_util import OUTPUT_ROOT_ENV  # noqa: E402

# Artefacts the site serves, tracked in git. Listed explicitly so the guard
# reports precisely what leaked rather than flagging unrelated churn.
PUBLISHED_ARTEFACTS = (
    "outbox/track_record.json",
    "outbox/coordination_opportunities.json",
    "data/coordination/graph.json",
    "api/feedback-data.json",
    "api/source-health-data.json",
    "outbox/dispatch_desk.json",
    "outbox/calibration.json",
    "data/calibration/ledger.json",
)


@pytest.fixture(scope="session", autouse=True)
def redirect_published_output(tmp_path_factory):
    """Send every artefact write to a temp tree for the duration of the run."""
    sandbox = tmp_path_factory.mktemp("published")
    previous = os.environ.get(OUTPUT_ROOT_ENV)
    os.environ[OUTPUT_ROOT_ENV] = str(sandbox)
    try:
        yield sandbox
    finally:
        if previous is None:
            os.environ.pop(OUTPUT_ROOT_ENV, None)
        else:
            os.environ[OUTPUT_ROOT_ENV] = previous


def _dirty_artefacts() -> list[str]:
    """Published files with uncommitted changes, per git."""
    result = subprocess.run(
        ["git", "status", "--porcelain", "--", *PUBLISHED_ARTEFACTS],
        cwd=ROOT, capture_output=True, text=True,
    )
    if result.returncode != 0:
        return []  # not a git checkout — nothing to guard
    return [line[3:] for line in result.stdout.splitlines() if line.strip()]


@pytest.fixture(scope="session", autouse=True)
def fail_if_tests_publish(redirect_published_output):
    """Fail loudly if the suite still modified a published artefact.

    The redirect above should make this impossible. It stays as a tripwire:
    a new writer that bypasses `output_path()` gets caught here rather than in
    a deploy.
    """
    before = set(_dirty_artefacts())
    yield
    leaked = set(_dirty_artefacts()) - before
    if leaked:
        pytest.fail(
            "Tests modified published artefacts:\n  "
            + "\n  ".join(sorted(leaked))
            + "\n\nRoute the write through pipeline_util.output_path() so the "
              "harness can redirect it. A test run must not change what the "
              "site publishes."
        )
