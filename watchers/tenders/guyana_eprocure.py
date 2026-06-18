"""Guyana eProcure (NPTA) — public bid opportunities JSON API."""
from __future__ import annotations

from typing import Any

from .base import TenderAdapter, http_json, normalize_record, parse_iso_date

GY_API = "https://eprocure.gov.gy/api/method/doctracker.api.powerbi.get_public_bid_opportunities"


def parse_guyana_records(payload: Any) -> list[dict[str, Any]]:
    msg = payload.get("message", payload) if isinstance(payload, dict) else payload
    records = msg if isinstance(msg, list) else []
    out: list[dict[str, Any]] = []
    for rec in records:
        if not isinstance(rec, dict):
            continue
        n = normalize_guyana_record(rec)
        if n["id"] and n["title"]:
            out.append(n)
    return out


def normalize_guyana_record(rec: dict[str, Any]) -> dict[str, Any]:
    closing = (
        parse_iso_date(rec.get("projected_bid_opening_date"))
        or parse_iso_date(rec.get("actual_bid_opening_date"))
    )
    return normalize_record(
        id=str(rec.get("project_id", "")),
        title=str(rec.get("project_name", "")).strip(),
        country="Guyana",
        source="Guyana eProcure (NPTA)",
        url="https://eprocure.gov.gy/",
        published=parse_iso_date(rec.get("advertisement_date")),
        closing_date=closing,
        category=str(rec.get("procurement_nature", "") or ""),
        agency=str(rec.get("agency", "") or ""),
        method=str(rec.get("procurement_method", "") or ""),
        status=str(rec.get("current_state", "") or ""),
    )


class GuyanaEprocureAdapter(TenderAdapter):
    slug = "guyana-eprocure"
    label = "Guyana eProcure (NPTA)"

    def fetch(self) -> list[dict[str, Any]]:
        try:
            payload = http_json(GY_API)
        except Exception as exc:
            print(f"tenders: guyana eprocure unreachable ({exc}) — returning empty")
            return []
        self.snapshot_json(payload)
        items = parse_guyana_records(payload)
        print(f"tenders: guyana eprocure -> {len(items)} records")
        return items
