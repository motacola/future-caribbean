"""Tender watcher — live procurement notices from national portals.

Sources:
  - Guyana: eprocure.gov.gy public bid opportunities (JSON API)
  - Jamaica: GOJEP (www.gojep.gov.jm) — the public listing sits behind a
    session/form flow (European Dynamics ePPS); no static HTML or JSON is
    reachable with stdlib HTTP, so the adapter returns [] and logs the
    finding rather than faking records.

Output: data/tenders/latest.json
Honesty rule: only records actually returned by a portal. Empty is fine.
"""
from __future__ import annotations

import json
import urllib.request
from datetime import datetime, timezone
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
OUT = ROOT / "data" / "tenders" / "latest.json"
RAW = ROOT / "data" / "tenders" / "raw"

UA = {"User-Agent": "Mozilla/5.0 (compatible; CaribbeanSignalOS/1.0)", "Accept": "application/json"}
GY_API = "https://eprocure.gov.gy/api/method/doctracker.api.powerbi.get_public_bid_opportunities"


def normalize_guyana(rec: dict) -> dict:
    return {
        "id": rec.get("project_id", ""),
        "title": rec.get("project_name", ""),
        "country": "Guyana",
        "source": "Guyana eProcure (NPTA)",
        "url": "https://eprocure.gov.gy/",
        "published": rec.get("advertisement_date") or None,
        "closing_date": rec.get("projected_bid_opening_date") or rec.get("actual_bid_opening_date") or None,
        "category": rec.get("procurement_nature", "") or "",
        "agency": rec.get("agency", "") or "",
        "method": rec.get("procurement_method", "") or "",
        "status": rec.get("current_state", "") or "",
    }


def fetch_guyana() -> list[dict]:
    try:
        req = urllib.request.Request(GY_API, headers=UA)
        with urllib.request.urlopen(req, timeout=20) as r:
            payload = json.loads(r.read())
    except Exception as e:
        print(f"tenders: guyana eprocure unreachable ({e}) — returning empty")
        return []
    msg = payload.get("message", payload)
    records = msg if isinstance(msg, list) else []
    RAW.mkdir(parents=True, exist_ok=True)
    snap = RAW / f"guyana-eprocure-{datetime.now(timezone.utc):%Y%m%d}.json"
    snap.write_text(json.dumps(payload, indent=1, ensure_ascii=False), encoding="utf-8")
    out = []
    for rec in records:
        if not isinstance(rec, dict):
            continue
        n = normalize_guyana(rec)
        if n["id"] and n["title"]:
            out.append(n)
    return out


def fetch_jamaica() -> list[dict]:
    # GOJEP's "Current competitions" page is a search form requiring an ePPS
    # session; no parseable public listing via plain HTTP as of 2026-06-11.
    print("tenders: jamaica GOJEP is session-gated — no public records reachable, returning empty")
    return []


def main() -> None:
    items: list[dict] = []
    seen: set[tuple] = set()
    for fetch in (fetch_guyana, fetch_jamaica):
        for rec in fetch():
            key = (rec["source"], rec["id"] or rec["url"])
            if key in seen:
                continue
            seen.add(key)
            items.append(rec)
    items.sort(key=lambda r: (r.get("closing_date") or "9999"), reverse=False)
    OUT.parent.mkdir(parents=True, exist_ok=True)
    OUT.write_text(json.dumps({
        "fetched_at": datetime.now(timezone.utc).isoformat(),
        "source": "tenders",
        "total": len(items),
        "items": items,
    }, indent=1, ensure_ascii=False) + "\n", encoding="utf-8")
    print(f"tenders: {len(items)} live records -> {OUT}")


if __name__ == "__main__":
    main()
