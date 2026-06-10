"""Tests for the Vercel deploy surface (5B): api/ functions, workflow, ignore rules."""
import importlib.util
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

API_FUNCTIONS = ["ask.py", "status.py", "tools.py", "map-data.py", "validation-packs.py"]


def _load(name: str):
    path = ROOT / "api" / name
    spec = importlib.util.spec_from_file_location(f"api_{name.replace('-', '_').replace('.py', '')}", path)
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    return mod


def test_api_functions_import_and_define_handler():
    for fn in API_FUNCTIONS:
        mod = _load(fn)
        assert hasattr(mod, "handler"), f"api/{fn} missing Vercel handler class"


def test_no_write_capable_functions_deployed():
    # Public instance is read-only by construction: no function may import
    # or shell out to delivery/feedback write paths.
    forbidden = ("feedback_loop", "telegram_sender", "delivery", "subprocess")
    for fn in API_FUNCTIONS + ["validation-packs/[id].py"]:
        src = (ROOT / "api" / fn).read_text()
        for word in forbidden:
            assert word not in src, f"api/{fn} references write path: {word}"


def test_workflow_has_cron_and_manual_trigger():
    wf = (ROOT / ".github" / "workflows" / "pipeline.yml").read_text()
    assert "schedule:" in wf
    assert "workflow_dispatch" in wf
    assert "run_pipeline.sh" in wf


def test_vercelignore_keeps_runtime_needs():
    rules = (ROOT / ".vercelignore").read_text().splitlines()
    excluded = {r.strip() for r in rules if r.strip() and not r.startswith(("#", "!"))}
    negated = {r.strip()[1:] for r in rules if r.strip().startswith("!")}
    # Functions need these at runtime — they must never be excluded outright.
    for needed in ("agent/", "map_data.py", "outbox/"):
        assert needed not in excluded, f".vercelignore excludes runtime dependency {needed}"
    # Theater replay needs history despite the data/* exclusion.
    assert any(n.startswith("data/history") for n in negated), "data/history not re-included"


def test_discovery_files_mention_manifest():
    for f in ("llms.txt", "agents.md"):
        assert "/api/tools.json" in (ROOT / f).read_text(), f"{f} missing tools.json pointer"
