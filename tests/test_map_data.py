"""Tests for the Caribbean map data feed."""
import json
import threading
import urllib.request
from pathlib import Path

import server
from map_data import WATCHED_COUNTRIES, build_map_data

ROOT = Path(__file__).resolve().parents[1]
REQUIRED_FIELDS = {"country", "confidence", "kind", "signal_count", "lead_dispatch_id"}


def _get_map_data_endpoint():
    httpd = server.http.server.ThreadingHTTPServer(("127.0.0.1", 0), server.AppHandler)
    thread = threading.Thread(target=httpd.serve_forever, daemon=True)
    thread.start()
    try:
        with urllib.request.urlopen(
            f"http://127.0.0.1:{httpd.server_port}/api/map-data",
            timeout=5,
        ) as response:
            return response.status, response.headers, json.load(response)
    finally:
        httpd.shutdown()
        httpd.server_close()


def test_map_data_endpoint_structure():
    status, headers, data = _get_map_data_endpoint()
    assert status == 200
    assert headers.get_content_type() == "application/json"
    assert isinstance(data, list)
    assert data
    assert all(REQUIRED_FIELDS <= set(entry) for entry in data)


def test_map_data_country_coverage():
    data = build_map_data(ROOT)
    assert {entry["country"] for entry in data} == set(WATCHED_COUNTRIES)
    assert len(data) == len(WATCHED_COUNTRIES)


def test_map_data_confidence_range():
    assert all(0 <= entry["confidence"] <= 100 for entry in build_map_data(ROOT))
