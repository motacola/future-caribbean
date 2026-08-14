"""Tests for the TanStack Charts lollipop data adapter and the Astro/React
island contract on /build.

These tests verify two contracts that other agents / future-CI will
rely on:

  1. The /build page MUST import and instantiate the LollipopIsland
     React island with the right props (this is the public integration
     surface — if anyone removes the section, this test fails).

  2. The opportunitiesFromDesk adapter has stable, documented behaviour:
     it dedupes by country, sorts desc, caps at 12, returns empty input,
     and preserves the desk's source timestamp. Node 22 executes the
     actual TypeScript module with built-in type stripping.

The chart-shape data is otherwise tested by the Astro build itself
(`pnpm run build` will fail if the React island contract breaks).
"""
from __future__ import annotations

import json
import re
import subprocess
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[1]
LOLLIPOP_TS = ROOT / "src" / "lib" / "charts" / "lollipop.ts"
THEME_TS = ROOT / "src" / "lib" / "caribbean-theme.ts"
ISLAND_TSX = ROOT / "src" / "lib" / "charts" / "LollipopIsland.tsx"
BUILD_ASTRO = ROOT / "src" / "pages" / "build.astro"
DATA_TS = ROOT / "src" / "lib" / "data.ts"
INDEX_ASTRO = ROOT / "src" / "pages" / "index.astro"



# ─────────────────────────────────────────────────────────────────
# 1. Build-page contract — string-level checks other agents can rely on
# ─────────────────────────────────────────────────────────────────

def test_build_page_includes_lollipop_island():
    """End-to-end: the /build page MUST include the LollipopIsland
    React island with the right props (this is the public integration
    surface — if anyone removes the section, this test fails).

    The test guards both the island presence and the supporting
    contracts the island depends on (the chart definition shape and
    the dataAsOf / opportunities props).
    """
    page = BUILD_ASTRO.read_text()
    assert "LollipopIsland" in page, "build.astro must import LollipopIsland"
    assert "client:load" in page, "LollipopIsland must use client:load (interactive chart)"
    # The island must receive opportunities and dataAsOf as serializable
    # props (Astro passes them through; React island reads them at runtime).
    assert "opportunities={lollipopData.opportunities}" in page, (
        "LollipopIsland must receive opportunities as a prop"
    )
    assert "dataAsOf={lollipopData.dataAsOf}" in page, (
        "LollipopIsland must receive dataAsOf as a prop (freshness label)"
    )
    # The fixture must exist and be imported — without it the frontmatter
    # PIPELINE const is empty.
    assert "build-pipeline-fixture.json" in page, (
        "build.astro must import build-pipeline-fixture.json for the offline demo data"
    )
    # The inlined <script is:inline> block reads PIPELINE — the only way
    # for the script to see it is via define:vars={{ PIPELINE }}. A future
    # agent who reverts to <script is:inline> without define:vars breaks
    # the page (the script crashes with 'PIPELINE is not defined').
    assert "is:inline define:vars={{ PIPELINE }}" in page, (
        "the in-script block on /build must use define:vars to share PIPELINE with the frontmatter"
    )


def test_build_page_computes_lollipop_data_in_frontmatter():
    page = BUILD_ASTRO.read_text()
    # The chart must use the current dispatch artifact, not the offline
    # build-walkthrough fixture.
    assert "outbox/dispatch_desk.json" in page
    assert "opportunitiesFromDesk(dispatchDesk)" in page, (
        "build.astro must derive lollipop data from the current dispatch desk"
    )
    assert "opportunitiesFromDesk(PIPELINE)" not in page
    # PIPELINE must be defined in the frontmatter (not the in-script
    # inline block, which we removed in this branch).
    assert re.search(r"^---\n.*const PIPELINE = ", page, re.DOTALL), (
        "PIPELINE must be declared in the frontmatter (between --- markers)"
    )


def test_build_page_uses_caribbean_theme_tokens():
    page = BUILD_ASTRO.read_text()
    # The build page must set the caribbeanTheme CSS variables so the
    # chart reads from the live site's design tokens. If a future agent
    # removes the --caribbean-* tokens, the chart will fall back to its
    # designer hardcoded palette — that is a regression.
    for token in ("--caribbean-bg", "--caribbean-fg", "--caribbean-sea",
                  "--caribbean-reef", "--caribbean-sun", "--caribbean-storm"):
        assert token in page, f"build.astro must define CSS variable {token}"


def test_lollipop_island_applies_caribbean_theme():
    island = ISLAND_TSX.read_text()
    chart = LOLLIPOP_TS.read_text()
    assert "buildOpportunityLollipop" in island
    assert "theme: caribbeanTheme" in chart
    assert "function clientLollipop" not in island, (
        "the React island must use the shared builder rather than a second chart definition"
    )


def test_index_astro_has_drill_lifecycle_css():
    """The map-drill panel renders a lifecycle + evidence-mix strip on
    click. The CSS that styles it must live in index.astro (it's part
    of the homepage, not the build page)."""
    page = (ROOT / "src" / "pages" / "index.astro").read_text()
    # CSS for the head, state, and the bar.
    for sel in (
        ".drill-lifecycle {",
        ".drill-lifecycle-head {",
        ".drill-lifecycle-state {",
        ".drill-lifecycle-state--fresh",
        ".drill-lifecycle-state--aging",
        ".drill-lifecycle-state--stale",
        ".drill-evidence {",
        ".drill-evidence-bar {",
        ".drill-evidence-seg {",

    ):
        assert sel in page, f"index.astro must define {sel} CSS"


def test_data_ts_reads_market_record_freshness_not_just_snapshot():
    """Regression: the freshness_state derivation must read from the
    market record's top-level freshness_state, not from the embedded
    market_snapshot (which the loader calls market_snapshot) that
    doesn't carry freshness_state.

    Before this fix, every chip was marked 'stale' even when the
    market had freshness_state='current' (Trinidad & Tobago,
    Barbados, Bahamas, etc.). This test asserts the source code
    reads the top-level field and uses the correct embedded field
    name (market_snapshot, not market.snapshot).

    Per Codex review 0492814: market.snapshot does not exist on the
    market record — snapshotFor() and the loader call it
    market_snapshot. Asserting market.market_snapshot is the correct
    fallback path.
    """
    src = DATA_TS.read_text()
    # The freshness derivation must reach market.freshness_state
    assert "market.freshness_state" in src, \
        "data.ts must read market.freshness_state (top-level)"
    # The fallback must use market_snapshot (not market.snapshot
    # which doesn't exist on the market record).
    assert "market.market_snapshot" in src, \
        "data.ts must read market.market_snapshot (the actual loader field name) for the embedded fallback"
    # market.snapshot (no underscore) must NOT appear as a JS expression.
    # Strip line comments first so the bug-recap prose doesn't trigger
    # the assertion. The bug-recap comment DOES say `market.snapshot`
    # which is correct as historical context but wrong as a JS reference.
    import re
    code_only = re.sub(r"//.*", "", src)
    code_refs = re.findall(r"market\.snapshot(?![_a-zA-Z])", code_only)
    assert len(code_refs) == 0, \
        f"data.ts must not reference market.snapshot as a JS property ({len(code_refs)} references found); the loader field is market_snapshot"
    # The buggy pattern (only checking snapshot) must NOT be present
    assert "(market.snapshot || {}).freshness_state" not in src, \
        "data.ts must not rely on (market.snapshot || {}).freshness_state"
    # The observation_at read must also try the top-level first
    assert "market.observation_at" in src, \
        "data.ts must read market.observation_at (top-level)"
    assert "(market.snapshot || {}).observation_at" not in src, \
        "data.ts must not rely on (market.snapshot || {}).observation_at"


def test_data_ts_emits_map_drill_lifecycle_fields():
    """Roadmap-2: the map-drill panel on the homepage has a lifecycle
    strip (last seen, next refresh, freshness state) and an evidence-mix
    bar. data.ts must populate these on every map marker.
    """
    data_ts = (ROOT / "src" / "lib" / "data.ts").read_text()
    # The marker builder must include these three fields. The actual
    # syntax is `lifecycle,` (no colon, because it's inside an object
    # literal) — accept both forms.
    for needle in ("evidence_mix:", "lifecycle", "freshness_state:"):
        assert needle in data_ts, f"data.ts must emit {needle.strip(':')} on every map marker"
    # The evidence_mix object must reference the same 6 source buckets
    # the lollipop uses (so users learn one taxonomy, not two).
    for bucket in ("wb", "idb", "noaa", "ndbc", "caricom", "cdb"):
        assert f"{bucket}:" in data_ts, f"evidence_mix must include bucket {bucket}"


def test_caribbean_theme_uses_css_variables_with_fallbacks():
    theme_src = THEME_TS.read_text()
    # Each token that controls the chart's color must be a CSS variable
    # so the live site can override it; the hard-coded fallback in the
    # var() is the designer default. If anyone removes the var() wrapper
    # this test catches it before merge.
    # Map theme-key -> expected --caribbean-* variable suffix
    token_to_var = {
        "sea": "--caribbean-sea",
        "reef": "--caribbean-reef",
        "sand": "--caribbean-sand",
        "sun": "--caribbean-sun",
        "storm": "--caribbean-storm",
        "background": "--caribbean-bg",
        "foreground": "--caribbean-fg",
    }
    for token, var_name in token_to_var.items():
        pattern = rf"{token}:\s*['\"]var\(\s*{re.escape(var_name)}\b"
        assert re.search(pattern, theme_src), (
            f"caribbeanTheme.{token} must be a CSS variable, e.g. "
            f"'var({var_name}, #fallback)'"
        )


# ─────────────────────────────────────────────────────────────────
# 2. opportunitiesFromDesk — execute the actual TypeScript module
# ─────────────────────────────────────────────────────────────────

NODE = subprocess.run(
    ["/usr/bin/env", "sh", "-c", "command -v node || true"],
    capture_output=True,
    text=True,
).stdout.strip()


def _run_adapter(desk: dict) -> dict:
    script = (
        "import { opportunitiesFromDesk } from "
        "'./src/lib/charts/lollipop.ts';"
        f"process.stdout.write(JSON.stringify(opportunitiesFromDesk({json.dumps(desk)})));"
    )
    result = subprocess.run(
        [NODE, "--input-type=module", "-e", script],
        cwd=ROOT,
        capture_output=True,
        text=True,
        timeout=20,
    )
    assert result.returncode == 0, f"node failed: {result.stderr}"
    return json.loads(result.stdout)


@pytest.mark.skipif(not NODE, reason="node not on PATH")
def test_opportunities_from_desk_dedupes_sorts_caps_and_preserves_source_time():
    desk = {
        "cycle_id": "20260813",
        "generated_at": "2026-08-13 16:44 UTC",
        "clusters": [
            {"country_cluster": "Guyana", "confidence_score": 140},
            {"country_cluster": "Guyana", "confidence_score": 80},
            {"country_cluster": "Belize", "confidence_score": 95},
            {"country_cluster": "Caribwide", "confidence_score": 50},
        ]
        + [
            {"country_cluster": f"Island-{i:02d}", "confidence_score": 49 - i}
            for i in range(11)
        ],
    }
    out = _run_adapter(desk)
    assert out["cycle"] == "20260813"
    assert out["dataAsOf"] == "2026-08-13T16:44:00.000Z"
    scores = [item["score"] for item in out["opportunities"]]
    assert scores == sorted(scores, reverse=True)
    assert len(out["opportunities"]) == 12
    by_name = {item["name"]: item["score"] for item in out["opportunities"]}
    assert by_name["Guyana"] == 100  # dedupe max wins, then clamps to domain
    assert by_name["Belize"] > by_name["Caribwide"]
    ids = {item["id"] for item in out["opportunities"]}
    assert {"guyana", "belize", "caribwide", "island-08"} <= ids
    assert "island-09" not in ids
    assert "island-10" not in ids


@pytest.mark.skipif(not NODE, reason="node not on PATH")
def test_opportunities_from_desk_handles_empty_and_uses_cycle_fallback_time():
    for desk in [{}, {"cycle_id": "x"}, {"clusters": "not-an-array"}]:
        out = _run_adapter(desk)
        assert out["opportunities"] == [], f"empty input must yield []; got {out}"
    dated = _run_adapter({"cycle_id": "20260813", "clusters": []})
    assert dated["dataAsOf"] == "2026-08-13T00:00:00.000Z"
