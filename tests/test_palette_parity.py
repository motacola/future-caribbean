"""Palette contract for the live site, with optional cross-repo parity."""
from __future__ import annotations

import os
import re
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
ASTRO_THEME = ROOT / "src" / "lib" / "caribbean-theme.ts"
CANONICAL = {
    "sea": "#1dbdd3",
    "reef": "#36c98a",
    "sand": "#f2d94c",
    "sun": "#ff8a3d",
    "storm": "#315cff",
    "background": "#fffcf4",
    "foreground": "#18251f",
}


def _extract_astro_palette() -> dict[str, str]:
    src = ASTRO_THEME.read_text()
    key_to_var = {
        "sea": "sea",
        "reef": "reef",
        "sand": "sand",
        "sun": "sun",
        "storm": "storm",
        "background": "bg",
        "foreground": "fg",
    }
    palette: dict[str, str] = {}
    for key, var in key_to_var.items():
        match = re.search(rf"var\(--caribbean-{var},\s*(#[0-9a-fA-F]+)\)", src)
        if match:
            palette[key] = match.group(1).lower()
    return palette


def _extract_raw_palette(path: Path) -> dict[str, str]:
    src = path.read_text()
    palette: dict[str, str] = {}
    for key in CANONICAL:
        match = re.search(rf"{key}:\s*['\"]#([0-9a-fA-F]+)['\"]", src)
        if match:
            palette[key] = f"#{match.group(1).lower()}"
    return palette


def test_live_theme_matches_canonical_caribbean_palette():
    assert _extract_astro_palette() == CANONICAL


def test_designer_palette_matches_when_explicitly_configured():
    """A configured external designer path is a strict comparison.

    CI remains meaningful without Christopher's local filesystem because the
    live canonical palette is always checked above. Set
    ABENG_DESIGNER_THEME to add cross-repository parity.
    """
    configured = os.environ.get("ABENG_DESIGNER_THEME")
    if not configured:
        return
    designer_theme = Path(configured).expanduser()
    assert designer_theme.is_file(), f"designer theme not found: {designer_theme}"
    assert _extract_raw_palette(designer_theme) == CANONICAL
