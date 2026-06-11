"""Tests for the newspaper front-page layer (desk nav, dateline, agents block)."""
import re
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
DASH = (ROOT / "dashboard.html").read_text()


def test_desk_navigation_present():
    assert 'class="desknav"' in DASH
    for label in ("Front Page", "Investment Desk", "Ask the Desk", "For Agents"):
        assert label in DASH, f"desk nav missing {label}"


def test_lead_story_dateline():
    assert 'class="dateline"' in DASH
    assert "By the Desk" in DASH


def test_wire_article_cards():
    assert 'id="more-wire"' in DASH and "More from the wire" in DASH
    assert DASH.count("art-kicker") >= 2
    assert "art-dek" in DASH and "art-by" in DASH


def test_for_agents_block():
    assert 'id="for-agents"' in DASH
    assert "Reading this as an AI agent? This page is yours too." in DASH
    for surface in ("/api/ask", "/api/tools.json", "/feed.xml", "/agents.md"):
        assert surface in DASH, f"agents block missing {surface}"


def test_no_unresolved_template_placeholders():
    # {{snake_case}} placeholders must all be substituted; htm object literals
    # like ${{ width: ... }} are JS, not placeholders.
    leftovers = re.findall(r"(?<!\$){{[a-z_]+}}", DASH)
    assert not leftovers, f"unresolved placeholders: {leftovers}"
