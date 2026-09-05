"""Shared tender watcher framework — fetch, normalize, dedupe, snapshot."""
from __future__ import annotations

import json
import re
import urllib.request
from abc import ABC, abstractmethod
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parents[2]
OUT = ROOT / "data" / "tenders" / "latest.json"
RAW = ROOT / "data" / "tenders" / "raw"

UA = {
    "User-Agent": "Mozilla/5.0 (compatible; Abeng/1.0)",
    "Accept": "application/json, text/html, */*",
}
TIMEOUT = 20

REQUIRED_KEYS = (
    "id", "title", "country", "source", "url",
    "published", "closing_date", "category", "fetched_at",
)


class TenderAdapter(ABC):
    slug: str = "base"
    label: str = "Tender source"

    @abstractmethod
    def fetch(self) -> list[dict[str, Any]]:
        """Return normalized tender records from the live source."""

    def snapshot_json(self, payload: Any, suffix: str = "json") -> None:
        RAW.mkdir(parents=True, exist_ok=True)
        stamp = datetime.now(timezone.utc).strftime("%Y%m%d")
        path = RAW / f"{self.slug}-{stamp}.{suffix}"
        if suffix == "json":
            path.write_text(json.dumps(payload, indent=1, ensure_ascii=False), encoding="utf-8")
        else:
            path.write_text(str(payload), encoding="utf-8")


def http_get(url: str, headers: dict[str, str] | None = None) -> bytes:
    req = urllib.request.Request(url, headers={**UA, **(headers or {})})
    with urllib.request.urlopen(req, timeout=TIMEOUT) as resp:
        return resp.read()


def http_json(url: str, headers: dict[str, str] | None = None) -> Any:
    return json.loads(http_get(url, headers).decode("utf-8"))


def normalize_record(
    *,
    id: str,
    title: str,
    country: str,
    source: str,
    url: str,
    published: str | None = None,
    closing_date: str | None = None,
    category: str = "",
    agency: str = "",
    method: str = "",
    status: str = "",
) -> dict[str, Any]:
    now = datetime.now(timezone.utc).isoformat()
    return {
        "id": (id or "").strip(),
        "title": (title or "").strip(),
        "country": country,
        "source": source,
        "url": url,
        "published": published or None,
        "closing_date": closing_date or None,
        "category": category or "",
        "agency": agency or "",
        "method": method or "",
        "status": status or "",
        "fetched_at": now,
    }


def validate_record(rec: dict[str, Any]) -> bool:
    return bool(rec.get("id") and rec.get("title") and rec.get("country"))


def merge_records(adapters: list[TenderAdapter]) -> list[dict[str, Any]]:
    items: list[dict[str, Any]] = []
    seen: set[tuple[str, str]] = set()
    for adapter in adapters:
        try:
            batch = adapter.fetch()
        except Exception as exc:
            print(f"tenders: {adapter.slug} failed ({exc}) — skipping")
            continue
        for rec in batch:
            if not validate_record(rec):
                continue
            key = (rec.get("source", ""), rec.get("id") or rec.get("url", ""))
            if key in seen:
                continue
            seen.add(key)
            items.append(rec)
    items.sort(key=lambda r: (r.get("closing_date") or "9999"))
    return items


def write_latest(items: list[dict[str, Any]], dest: Path = OUT) -> Path:
    dest.parent.mkdir(parents=True, exist_ok=True)
    payload = {
        "fetched_at": datetime.now(timezone.utc).isoformat(),
        "source": "tenders",
        "total": len(items),
        "items": items,
    }
    dest.write_text(json.dumps(payload, indent=1, ensure_ascii=False) + "\n", encoding="utf-8")
    return dest


def parse_iso_date(value: str | None) -> str | None:
    if not value:
        return None
    value = value.strip()
    if re.fullmatch(r"\d{4}-\d{2}-\d{2}", value):
        return value
    return None
