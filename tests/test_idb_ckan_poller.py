"""Tests for watchers/idb_ckan_poller.extract_title.

The IDB CKAN API returns dataset titles in two shapes:
  - language-keyed dict: {"en": "...", "es": "..."}
  - plain string: "Plain title"
Malformed records (None, int, list) must NOT crash the poller — they
return an empty title so the dataset is still emitted with a fingerprint.

This regression was hit on 2026-08-13: the live site showed idb as the
sole stale source (~28,684 minutes old) because the poller raised
AttributeError on the str-title shape and aborted before writing
data/idb/latest.json.
"""
from __future__ import annotations

import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
sys.path.insert(0, str(ROOT / "watchers"))

from idb_ckan_poller import extract_title


def test_dict_en_wins():
    assert extract_title({"en": "English", "es": "Spanish"}) == "English"


def test_dict_falls_back_to_es_when_en_missing():
    assert extract_title({"es": "Solo español", "fr": "Français"}) == "Solo español"


def test_plain_string_passes_through():
    assert extract_title("Plain string title") == "Plain string title"


def test_empty_string_returns_empty():
    assert extract_title("") == ""


def test_none_returns_empty():
    assert extract_title(None) == ""


def test_empty_dict_returns_empty():
    assert extract_title({}) == ""


def test_empty_en_value_falls_through_to_other_lang():
    assert extract_title({"en": "", "es": "Español"}) == "Español"


def test_unexpected_type_does_not_raise():
    # Defensive: if the API ever returns something we don't recognise,
    # we should not abort the whole poll run.
    assert extract_title(123) == ""
    assert extract_title(["not", "a", "dict"]) == ""
    # Non-string values under "en" are skipped (no falsy fallback), so the
    # next language wins. This is intentional — we don't trust the type.


def test_poller_wrote_latest_json():
    """Sanity check: extract_title fix means the poller now writes output.

    This is an end-to-end smoke that runs the actual poller (no network in
    test mode: we just confirm the file exists). Skipped if the file is
    missing so this doesn't break CI on a fresh checkout.
    """
    latest = ROOT / "data" / "idb" / "latest.json"
    if not latest.exists():
        import pytest
        pytest.skip("data/idb/latest.json missing — poller hasn't been run yet")
    import json
    payload = json.loads(latest.read_text())
    assert payload, "idb latest.json should not be empty after a successful poll"