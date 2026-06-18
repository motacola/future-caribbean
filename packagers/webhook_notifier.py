"""Webhook notifier — fires HTTP POSTs when a signal crosses a subscriber's threshold.

Subscriptions live in data/webhooks/subscriptions.json.
Called at the end of each pipeline cycle.
"""
from __future__ import annotations

import json
import secrets
import urllib.request
import urllib.error
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

ROOT = Path(__file__).parent.parent
SUBS_PATH = ROOT / "data" / "webhooks" / "subscriptions.json"
DISPATCHES_PATH = ROOT / "outbox" / "opportunity_dispatches.json"


# ── Subscription store ──────────────────────────────────────────

def _load() -> list[dict]:
    if not SUBS_PATH.exists():
        return []
    return json.loads(SUBS_PATH.read_text(encoding="utf-8"))


def _save(subs: list[dict]) -> None:
    SUBS_PATH.parent.mkdir(parents=True, exist_ok=True)
    SUBS_PATH.write_text(json.dumps(subs, indent=2, ensure_ascii=False), encoding="utf-8")


def list_subscriptions() -> list[dict]:
    return _load()


def create_subscription(url: str, threshold: int = 80,
                        country: str | None = None,
                        signal_kind: str | None = None) -> dict:
    subs = _load()
    sub = {
        "id": f"wh-{secrets.token_hex(5)}",
        "url": url,
        "country": country,
        "signal_kind": signal_kind,
        "threshold": int(threshold),
        "created_at": datetime.now(timezone.utc).isoformat(),
        "last_fired_at": None,
        "last_signal_id": None,
    }
    subs.append(sub)
    _save(subs)
    return sub


def delete_subscription(sub_id: str) -> bool:
    subs = _load()
    before = len(subs)
    subs = [s for s in subs if s["id"] != sub_id]
    if len(subs) == before:
        return False
    _save(subs)
    return True


# ── Evaluation ──────────────────────────────────────────────────

def _best_dispatch_per_signal(dispatches: list[dict]) -> dict[str, dict]:
    """Return highest-confidence dispatch per (country, signal_kind) pair."""
    best: dict[str, dict] = {}
    for d in dispatches:
        key = f"{d.get('country_cluster','')}|{d.get('signal_kind','')}"
        if key not in best or (d.get("confidence_score") or 0) > (best[key].get("confidence_score") or 0):
            best[key] = d
    return best


def _matches(sub: dict, dispatch: dict) -> bool:
    if sub.get("country") and sub["country"].lower() != (dispatch.get("country_cluster") or "").lower():
        return False
    if sub.get("signal_kind") and sub["signal_kind"] != dispatch.get("signal_kind"):
        return False
    return (dispatch.get("confidence_score") or 0) >= sub["threshold"]


def _fire(sub: dict, dispatch: dict) -> bool:
    payload = json.dumps({
        "event": "threshold_crossed",
        "subscription_id": sub["id"],
        "country": dispatch.get("country_cluster"),
        "signal_kind": dispatch.get("signal_kind"),
        "confidence_score": dispatch.get("confidence_score"),
        "dispatch_id": dispatch.get("dispatch_id"),
        "signal_id": dispatch.get("signal_id"),
        "title": dispatch.get("title", ""),
        "action_window": dispatch.get("action_window", ""),
        "evidence_summary": dispatch.get("evidence_summary", ""),
        "fired_at": datetime.now(timezone.utc).isoformat(),
    }, ensure_ascii=False).encode()

    req = urllib.request.Request(
        sub["url"],
        data=payload,
        headers={"Content-Type": "application/json", "User-Agent": "SignalFabric-Webhook/1"},
        method="POST",
    )
    try:
        with urllib.request.urlopen(req, timeout=8) as resp:
            return resp.status < 300
    except urllib.error.URLError:
        return False


def run_notifications() -> list[dict]:
    """Evaluate all subscriptions against current dispatches. Returns a log of fires."""
    subs = _load()
    if not subs:
        return []

    if not DISPATCHES_PATH.exists():
        return []

    dispatches = json.loads(DISPATCHES_PATH.read_text(encoding="utf-8")).get("dispatches", [])
    best = _best_dispatch_per_signal(dispatches)
    log: list[dict] = []
    updated = False

    for sub in subs:
        for dispatch in best.values():
            if not _matches(sub, dispatch):
                continue
            # Don't re-fire for the same signal_id
            if sub.get("last_signal_id") == dispatch.get("signal_id"):
                continue
            fired = _fire(sub, dispatch)
            now = datetime.now(timezone.utc).isoformat()
            entry: dict[str, Any] = {
                "subscription_id": sub["id"],
                "url": sub["url"],
                "country": dispatch.get("country_cluster"),
                "signal_kind": dispatch.get("signal_kind"),
                "confidence_score": dispatch.get("confidence_score"),
                "fired": fired,
                "fired_at": now,
            }
            log.append(entry)
            if fired:
                sub["last_fired_at"] = now
                sub["last_signal_id"] = dispatch.get("signal_id")
                updated = True

    if updated:
        _save(subs)
    return log


def main() -> None:
    log = run_notifications()
    if not log:
        print("  webhook_notifier: no subscriptions or no threshold crossings")
        return
    for entry in log:
        status = "fired" if entry["fired"] else "failed"
        print(f"  webhook [{status}] → {entry['url']} | "
              f"{entry['country']} {entry['signal_kind']} @ {entry['confidence_score']}")


if __name__ == "__main__":
    main()
