"""The Vercel function budget, and the promise /api/tools.json makes about it.

Vercel's Hobby plan deploys at most 12 Serverless Functions. Going over does not
fail the build — the extra functions are simply absent in production, returning
404 while working locally. That failure mode is invisible until someone calls the
endpoint, and it already bit this project: regional-news and market-watch were
excluded from deploys to stay legal while the public tool manifest kept
advertising /api/regional-news.
"""

from __future__ import annotations

import fnmatch
import json
import sys
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[1]
BUDGET = 12

sys.path.insert(0, str(ROOT))


def _ignored_api_patterns() -> list[str]:
    ignore = ROOT / ".vercelignore"
    if not ignore.exists():
        return []
    return [
        line.strip()
        for line in ignore.read_text(encoding="utf-8").splitlines()
        if line.strip().startswith("api/") and not line.strip().startswith("#")
    ]


def deployed_functions() -> list[str]:
    patterns = _ignored_api_patterns()
    return sorted(
        path.name
        for path in (ROOT / "api").glob("*.py")
        if not any(fnmatch.fnmatch(f"api/{path.name}", pattern) for pattern in patterns)
    )


def test_function_count_is_within_the_hobby_budget():
    deployed = deployed_functions()
    assert len(deployed) <= BUDGET, (
        f"{len(deployed)} functions would deploy, over the {BUDGET} limit. "
        f"Vercel drops the excess silently and they 404 in production. "
        f"Fold read-only endpoints into api/artifact.py instead. Current: {deployed}"
    )


def test_every_publicly_available_tool_has_a_deployable_function():
    """An agent following the public manifest must not hit a 404.

    api/tools.py marks write tools `available: false` with "local instance only",
    which is honest — Vercel's filesystem is ephemeral, so a write endpoint could
    not persist anyway. Those are exempt. Anything still advertised as available
    has to resolve to a function that actually deploys, which is precisely what
    regional_news.list did not do.
    """
    import re

    from api_manifest import TOOLS_MANIFEST

    deployed = set(deployed_functions())
    routes = json.loads((ROOT / "vercel.json").read_text(encoding="utf-8"))["routes"]

    def module_for(path: str) -> str | None:
        # Resolve the way Vercel does: first matching route wins.
        for route in routes:
            src, dest = route.get("src"), route.get("dest", "")
            if not src or not dest.startswith("/api/"):
                continue
            match = re.fullmatch(src, path)
            if match:
                resolved = dest
                for group, value in enumerate(match.groups(), start=1):
                    resolved = resolved.replace(f"${group}", value or "")
                return Path(resolved.split("?")[0]).name
        return None

    missing = []
    for tool in TOOLS_MANIFEST.get("tools", []):
        path = tool.get("path", "")
        if not path.startswith("/api/") or tool.get("writes"):
            continue
        # Templated paths are exercised through a concrete sample.
        concrete = re.sub(r"\{[^}]+\}", "sample-id", path)
        module = module_for(concrete)
        if module is None or module not in deployed:
            missing.append((tool.get("name"), path, module or "no matching route"))

    assert not missing, (
        "The public tool manifest advertises paths with no deployable function: "
        + ", ".join(f"{name} {path} -> {module}" for name, path, module in missing)
    )


@pytest.mark.parametrize("doc", ["reasoning", "track-record", "calibration"])
def test_artifact_dispatcher_preserves_the_passthrough_contract(doc, tmp_path):
    """Shape is load-bearing: the site, CLI, MCP adapter and agents all read it."""
    import importlib.util

    spec = importlib.util.spec_from_file_location("artifact", ROOT / "api" / "artifact.py")
    artifact = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(artifact)

    status, payload = artifact.resolve(doc)
    assert status in (200, 503)
    assert payload["ok"] is (status == 200)

    # Absent artifact must say so rather than inventing an empty success.
    missing_status, missing_payload = artifact.resolve(doc, tmp_path)
    assert missing_status == 503
    assert missing_payload["ok"] is False
    assert "run the pipeline" in missing_payload["error"].lower()


def test_artifact_dispatcher_rejects_unknown_docs():
    import importlib.util

    spec = importlib.util.spec_from_file_location("artifact", ROOT / "api" / "artifact.py")
    artifact = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(artifact)

    status, payload = artifact.resolve("../../etc/passwd")
    assert status == 404
    assert payload["ok"] is False


def test_every_artifact_route_points_at_a_known_doc():
    import importlib.util

    spec = importlib.util.spec_from_file_location("artifact", ROOT / "api" / "artifact.py")
    artifact = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(artifact)

    known = set(artifact.PASSTHROUGH) | {"map-data"}
    routes = json.loads((ROOT / "vercel.json").read_text(encoding="utf-8"))["routes"]
    for route in routes:
        dest = route.get("dest", "")
        if "artifact.py?doc=" in dest:
            assert dest.split("doc=")[1] in known, f"{route['src']} routes to an unknown doc"
