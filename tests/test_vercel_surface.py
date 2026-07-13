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
    for fn in API_FUNCTIONS:
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


def _drive_coordination_handler(path: str) -> tuple[int, dict]:
    """Drive the coordination-opportunities handler with a fake request and return (status, json)."""
    import json as _json
    from io import BytesIO

    mod = _load("coordination-opportunities.py")
    out = BytesIO()

    class _Req(mod.handler):
        def __init__(self, p):
            self.path = p
            self._out = out
            self.headers = {}

        def send_response(self, code):
            self._code = code

        def send_header(self, *a):
            pass

        def end_headers(self):
            pass

        def wfile_write(self, b):
            out.write(b)

        wfile = property(lambda self: self)  # type: ignore
        write = wfile_write

    req = _Req(path)
    req.do_GET()
    body = out.getvalue().decode()
    return req._code, _json.loads(body)


def test_coordination_handler_resolves_by_id_query_and_path():
    # Query-param form (what vercel.json routes forward)
    status_q, payload_q = _drive_coordination_handler(
        "/api/coordination-opportunities?id=coord-dev-pipeline-regional"
    )
    assert status_q == 200, payload_q
    assert payload_q.get("id") == "coord-dev-pipeline-regional"
    # Path form (direct)
    status_p, payload_p = _drive_coordination_handler(
        "/api/coordination-opportunities/coord-dev-pipeline-regional"
    )
    assert status_p == 200, payload_p
    assert payload_p.get("id") == "coord-dev-pipeline-regional"
    # Index returns the full list
    status_i, payload_i = _drive_coordination_handler("/api/coordination-opportunities")
    assert status_i == 200, payload_i
    assert "opportunities" in payload_i
    # Unknown id -> 404
    status_n, _ = _drive_coordination_handler(
        "/api/coordination-opportunities?id=does-not-exist"
    )
    assert status_n == 404
