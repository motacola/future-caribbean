"""Cross-machine palette parity check.

The Astro site and the React+Vite designer must use the same caribbeanTheme
palette. The Astro version reads CSS variables; the designer version
hardcodes hex. If the hex values diverge, charts on the live site and in
the designer will look different.

Run this from the Astro repo root. It reads the designer's source file
(if reachable on this Mac) and asserts the two palettes are equivalent
modulo the CSS-variable wrapper.
"""
from __future__ import annotations

import json
import re
import shutil
import subprocess
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[1]
ASTRO_THEME = ROOT / "src" / "lib" / "caribbean-theme.ts"
DESIGNER_THEME = Path(
    "/Users/christopherbelgrave/Documents/signal-fabric-designer/src/charts/caribbean-theme.ts"
)
NODE = shutil.which("node") or ""


def _extract_palette_from_astro() -> dict[str, str]:
    """Pull the hex fallback values out of the Astro theme source.

    Each line is e.g. `sea: 'var(--caribbean-sea, #1dbdd3)',`.
    """
    src = ASTRO_THEME.read_text()
    palette: dict[str, str] = {}
    key_to_var = {
        "sea": "sea",
        "reef": "reef",
        "sand": "sand",
        "sun": "sun",
        "storm": "storm",
        "background": "bg",
        "foreground": "fg",
    }
    for key, var in key_to_var.items():
        m = re.search(rf"var\(--caribbean-{var},\s*(\#[0-9a-fA-F]+)\)", src)
        if m:
            palette[key] = m.group(1).lower()
    return palette


def _extract_palette_from_designer() -> dict[str, str]:
    src = DESIGNER_THEME.read_text()
    palette: dict[str, str] = {}
    for key in ("sea", "reef", "sand", "sun", "storm", "background", "foreground"):
        m = re.search(rf"{key}:\s*['\"]#([0-9a-fA-F]+)['\"]", src)
        if m:
            palette[key] = "#" + m.group(1).lower()
    return palette


def test_palettes_match_when_designer_is_reachable():
    """If the designer's caribbean-theme.ts exists on this Mac (the same
    machine, in a different tree), the palette values must agree. The
    Astro version uses CSS-variable wrappers with hex fallbacks; the
    designer version is raw hex. After stripping the wrappers, the
    hexes must match.
    """
    if not DESIGNER_THEME.exists():
        import pytest
        pytest.skip(f"Designer theme not on this Mac at {DESIGNER_THEME}")
    astro = _extract_palette_from_astro()
    designer = _extract_palette_from_designer()
    # Compare every key the designer defines.
    for key, designer_hex in designer.items():
        astro_hex = astro.get(key)
        assert astro_hex is not None, (
            f"Astro theme is missing {key} but designer has it"
        )
        assert astro_hex == designer_hex, (
            f"caribbeanTheme.{key}: Astro={astro_hex} designer={designer_hex}. "
            f"Update one of them so the live site and the design tool match."
        )
