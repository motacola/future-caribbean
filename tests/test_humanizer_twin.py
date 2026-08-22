"""Parity guard between the two humanizer engines.

humanizer.py serves pipeline artifacts (Python re syntax, \\1 backrefs);
src/lib/humanize.ts serves client-rendered surfaces (JS RegExp, $1
backrefs). They MUST hold the same rule set — a rule added to one and
forgotten in the other means pipeline text reads naturally while the
live page still shows robotic copy (or vice versa).

This test parses the TS array and diffs it against the Python list,
applying exactly the backref conversion humanizer.py documents.
"""
import json
import re
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from humanizer import HUMANIZE_RULES  # noqa: E402

TS_FILE = ROOT / "src" / "lib" / "humanize.ts"


def _ts_rules() -> list[tuple[str, str]]:
    src = TS_FILE.read_text(encoding="utf-8")
    m = re.search(r"const HUMANIZE_RULES[^=]*= \[([\s\S]*?)\n\];", src)
    assert m, "HUMANIZE_RULES array not found in humanize.ts"
    body = m.group(1)
    pairs = re.findall(
        r'\[\s*"(?:[^"\\]|\\.)*"\s*,\s*"(?:[^"\\]|\\.)*"\s*\]', body
    )
    rules = []
    for raw in pairs:
        pat, repl = json.loads(raw)
        rules.append((pat, repl))
    return rules


def _py_rule_as_js(rule: tuple[str, str]) -> tuple[str, str]:
    pat, repl = rule
    js_repl = re.sub(r"\\(\d)", r"$\1", repl)
    return pat, js_repl


def test_twin_engines_hold_identical_rules():
    ts_rules = _ts_rules()
    py_rules = [_py_rule_as_js(r) for r in HUMANIZE_RULES]
    assert len(ts_rules) == len(py_rules), (
        f"rule count drifted: humanizer.py has {len(py_rules)}, "
        f"humanize.ts has {len(ts_rules)}. Mirror every rule into BOTH files."
    )
    for i, (py, ts) in enumerate(zip(py_rules, ts_rules)):
        assert py == ts, (
            f"rule #{i} diverged between the twins:\n"
            f"  python : {py}\n  typescript: {ts}"
        )


def test_every_python_pattern_compiles_and_backrefs_convert():
    """Catches typos at the source before they reach either engine."""
    for pat, repl in HUMANIZE_RULES:
        compiled = re.compile(pat)  # raises on bad pattern
        js_repl = re.sub(r"\\(\d)", r"$\1", repl)
        assert "\\1" not in js_repl or "$1" not in js_repl
        # groups referenced must exist
        n_groups = compiled.groups
        for ref in re.findall(r"\\\d", repl):
            assert int(ref[1:]) <= n_groups, f"{pat!r}: bad backref {ref}"


if __name__ == "__main__":
    import pytest

    pytest.main([__file__])
