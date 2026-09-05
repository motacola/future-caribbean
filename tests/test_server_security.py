"""Regression coverage for the local operator server trust boundary."""

from __future__ import annotations

import json
import threading
import urllib.error
import urllib.request
from contextlib import contextmanager

import pytest

import server


@contextmanager
def running_server(handler=server.AppHandler):
    httpd = server.http.server.ThreadingHTTPServer(("127.0.0.1", 0), handler)
    thread = threading.Thread(target=httpd.serve_forever, daemon=True)
    thread.start()
    try:
        yield f"http://127.0.0.1:{httpd.server_port}"
    finally:
        httpd.shutdown()
        httpd.server_close()
        thread.join(timeout=5)


def request(base_url: str, path: str, *, method: str, token: str | None = None,
            origin: str | None = None, body: bytes = b"{}") -> tuple[int, dict, dict]:
    headers = {"Content-Type": "application/json"}
    if token is not None:
        headers["Authorization"] = f"Bearer {token}"
    if origin is not None:
        headers["Origin"] = origin
    req = urllib.request.Request(base_url + path, data=body if method != "DELETE" else None,
                                 headers=headers, method=method)
    try:
        response = urllib.request.urlopen(req, timeout=5)
    except urllib.error.HTTPError as exc:
        response = exc
    payload = response.read()
    parsed = json.loads(payload.decode("utf-8")) if payload else {}
    return response.status, dict(response.headers.items()), parsed


def test_bind_host_defaults_to_loopback_and_allows_explicit_override(monkeypatch):
    monkeypatch.delenv("HOST", raising=False)
    assert server.get_bind_host() == "127.0.0.1"
    monkeypatch.setenv("HOST", "0.0.0.0")
    assert server.get_bind_host() == "0.0.0.0"


def test_mutation_fails_closed_before_handler_when_token_unconfigured(monkeypatch):
    called = False

    def forbidden_handler(self):
        nonlocal called
        called = True
        self._json({"ok": True})

    monkeypatch.delenv("DESK_ADMIN_TOKEN", raising=False)
    monkeypatch.setattr(server.AppHandler, "_api_create_domain", forbidden_handler)
    with running_server() as base_url:
        status, _, payload = request(
            base_url,
            "/api/domains/create",
            method="POST",
            body=b'{"name":"must-not-be-read"}',
        )

    assert status == 503
    assert payload == {"ok": False, "error": "Admin write API is disabled"}
    assert called is False


def test_missing_and_invalid_tokens_are_rejected_before_handler(monkeypatch):
    called = False

    def forbidden_handler(self):
        nonlocal called
        called = True
        self._json({"ok": True})

    monkeypatch.setenv("DESK_ADMIN_TOKEN", "correct-test-token")
    monkeypatch.setattr(server.AppHandler, "_api_create_domain", forbidden_handler)
    with running_server() as base_url:
        missing, _, _ = request(base_url, "/api/domains/create", method="POST")
        invalid, _, _ = request(
            base_url, "/api/domains/create", method="POST", token="incorrect-test-token"
        )

    assert missing == 401
    assert invalid == 401
    assert called is False


@pytest.mark.parametrize("header_name", ["Authorization", "X-Desk-Admin-Token"])
def test_valid_token_reaches_mutation_handler(monkeypatch, header_name):
    monkeypatch.setenv("DESK_ADMIN_TOKEN", "correct-test-token")

    def harmless_handler(self):
        self._json({"ok": True, "handler": "reached"})

    monkeypatch.setattr(server.AppHandler, "_api_create_domain", harmless_handler)
    headers = {"Content-Type": "application/json"}
    headers[header_name] = (
        "Bearer correct-test-token" if header_name == "Authorization" else "correct-test-token"
    )
    with running_server() as base_url:
        req = urllib.request.Request(
            base_url + "/api/domains/create", data=b"{}", headers=headers, method="POST"
        )
        with urllib.request.urlopen(req, timeout=5) as response:
            payload = json.loads(response.read())
            status = response.status

    assert status == 200
    assert payload == {"ok": True, "handler": "reached"}


def test_token_validation_uses_constant_time_comparison(monkeypatch):
    compared = []
    monkeypatch.setenv("DESK_ADMIN_TOKEN", "correct-test-token")

    def compare(left, right):
        compared.append((left, right))
        return True

    monkeypatch.setattr(server.hmac, "compare_digest", compare)
    monkeypatch.setattr(server.AppHandler, "_api_create_domain", lambda self: self._json({"ok": True}))
    with running_server() as base_url:
        status, _, _ = request(
            base_url, "/api/domains/create", method="POST", token="presented-token"
        )

    assert status == 200
    assert compared == [("presented-token", "correct-test-token")]


def test_public_ask_remains_unauthenticated_and_cross_origin(monkeypatch):
    monkeypatch.setenv("DESK_ADMIN_TOKEN", "correct-test-token")
    monkeypatch.setattr(server.AppHandler, "_api_ask", lambda self: self._json({"ok": True}))
    with running_server() as base_url:
        status, headers, payload = request(
            base_url,
            "/api/ask",
            method="POST",
            origin="https://public-agent.example",
        )

    assert status == 200
    assert payload == {"ok": True}
    assert headers["Access-Control-Allow-Origin"] == "*"


def test_delete_route_requires_admin_token(monkeypatch):
    called = False

    def forbidden_delete(self, subscription_id):
        nonlocal called
        called = True
        self._json({"ok": True, "id": subscription_id})

    monkeypatch.setenv("DESK_ADMIN_TOKEN", "correct-test-token")
    monkeypatch.setattr(server.AppHandler, "_api_webhooks_delete", forbidden_delete)
    with running_server() as base_url:
        status, _, _ = request(base_url, "/api/webhooks/test-id", method="DELETE")

    assert status == 401
    assert called is False


def test_mutation_preflight_rejects_untrusted_origin(monkeypatch):
    monkeypatch.setenv("DESK_ADMIN_TOKEN", "correct-test-token")
    with running_server() as base_url:
        status, headers, _ = request(
            base_url,
            "/api/domains/create",
            method="OPTIONS",
            origin="https://evil.example",
            body=b"",
        )

    assert status == 403
    assert "Access-Control-Allow-Origin" not in headers


def test_mutation_preflight_allows_loopback_and_configured_origins(monkeypatch):
    monkeypatch.setenv("DESK_ADMIN_TOKEN", "correct-test-token")
    monkeypatch.setenv("ABENG_CORS_ORIGINS", "https://operator.example")
    with running_server() as base_url:
        loopback_status, loopback_headers, _ = request(
            base_url,
            "/api/domains/create",
            method="OPTIONS",
            origin="http://localhost:4321",
            body=b"",
        )
        configured_status, configured_headers, _ = request(
            base_url,
            "/api/domains/create",
            method="OPTIONS",
            origin="https://operator.example",
            body=b"",
        )

    assert loopback_status == 204
    assert loopback_headers["Access-Control-Allow-Origin"] == "http://localhost:4321"
    assert "Authorization" in loopback_headers["Access-Control-Allow-Headers"]
    assert configured_status == 204
    assert configured_headers["Access-Control-Allow-Origin"] == "https://operator.example"


# ── Read-path exposure ─────────────────────────────────────────
# Writes were locked first; these cover the reads. The operator endpoints leak
# state rather than product: pending sends carry unsent message bodies and the
# webhook list carries subscriber URLs.

@pytest.mark.parametrize("path", ["/api/delivery/approvals", "/api/webhooks"])
def test_operator_reads_require_admin_token(monkeypatch, path):
    called = False

    def forbidden(self, *args, **kwargs):
        nonlocal called
        called = True
        self._json({"ok": True})

    monkeypatch.setenv("DESK_ADMIN_TOKEN", "correct-test-token")
    monkeypatch.setattr(server.AppHandler, "_api_delivery_approvals", forbidden)
    monkeypatch.setattr(server.AppHandler, "_api_webhooks_list", forbidden)
    with running_server() as base_url:
        status, headers, _ = request(base_url, path, method="GET")

    assert status == 401
    assert called is False
    assert headers.get("Access-Control-Allow-Origin") != "*"


@pytest.mark.parametrize("path", ["/api/status", "/api/tools.json"])
def test_published_reads_stay_open(monkeypatch, path):
    monkeypatch.setenv("DESK_ADMIN_TOKEN", "correct-test-token")
    monkeypatch.setattr(server.AppHandler, "_api_status", lambda self: self._json({"ok": True}))
    monkeypatch.setattr(server.AppHandler, "_api_tools_manifest", lambda self: self._json({"ok": True}))
    with running_server() as base_url:
        status, headers, payload = request(base_url, path, method="GET")

    assert status == 200
    assert payload == {"ok": True}
    assert headers["Access-Control-Allow-Origin"] == "*"


def test_rebinding_host_is_rejected(monkeypatch):
    """A page resolving its own domain to 127.0.0.1 reaches the port; Host betrays it."""
    monkeypatch.delenv("HOST", raising=False)
    monkeypatch.setattr(server.AppHandler, "_api_status", lambda self: self._json({"ok": True}))
    with running_server() as base_url:
        port = base_url.rsplit(":", 1)[1]
        req = urllib.request.Request(
            base_url + "/api/status", headers={"Host": f"evil.example:{port}"}, method="GET"
        )
        try:
            response = urllib.request.urlopen(req, timeout=5)
        except urllib.error.HTTPError as exc:
            response = exc
        status = response.status
        payload = json.loads(response.read().decode("utf-8"))

    assert status == 403
    assert payload == {"ok": False, "error": "Host is not allowed"}


def test_configured_origin_host_is_accepted(monkeypatch):
    monkeypatch.delenv("HOST", raising=False)
    monkeypatch.setenv("ABENG_CORS_ORIGINS", "https://operator.example")
    monkeypatch.setattr(server.AppHandler, "_api_status", lambda self: self._json({"ok": True}))
    with running_server() as base_url:
        port = base_url.rsplit(":", 1)[1]
        req = urllib.request.Request(
            base_url + "/api/status", headers={"Host": f"operator.example:{port}"}, method="GET"
        )
        with urllib.request.urlopen(req, timeout=5) as response:
            assert response.status == 200


def test_host_check_steps_aside_when_bind_is_widened(monkeypatch):
    """HOST=0.0.0.0 is a deliberate choice; the operator owns that exposure."""
    monkeypatch.setenv("HOST", "0.0.0.0")
    monkeypatch.setattr(server.AppHandler, "_api_status", lambda self: self._json({"ok": True}))
    with running_server() as base_url:
        port = base_url.rsplit(":", 1)[1]
        req = urllib.request.Request(
            base_url + "/api/status", headers={"Host": f"box.local:{port}"}, method="GET"
        )
        with urllib.request.urlopen(req, timeout=5) as response:
            assert response.status == 200
