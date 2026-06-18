"""Jamaica GOJEP (ePPS) — public opened-bid and contract-award listings.

Current competitions require a captcha session, but these pages are reachable
via plain HTTP (no browser required):
  - Opened bid details (submission deadlines): viewOpenedTenders.do
  - Contract award notices (recent awards): quickSearchAction searchSelect=5

Snapshots are cached under data/tenders/raw/ for offline resilience.
"""
from __future__ import annotations

import re
from datetime import datetime, timezone
from html import unescape
from pathlib import Path
from typing import Any

from .base import RAW, TenderAdapter, http_get, normalize_record, parse_iso_date

BASE = "https://www.gojep.gov.jm"
OPENED_URL = f"{BASE}/epps/common/viewOpenedTenders.do"
AWARDS_URL = (
    f"{BASE}/epps/quickSearchAction.do"
    "?searchSelect=5&selectedItem=quickSearchAction.do%3FsearchSelect%3D5"
)

MONTHS = {
    "jan": "01", "feb": "02", "mar": "03", "apr": "04", "may": "05", "jun": "06",
    "jul": "07", "aug": "08", "sep": "09", "oct": "10", "nov": "11", "dec": "12",
}


def _clean(text: str) -> str:
    return re.sub(r"\s+", " ", unescape(re.sub(r"<[^>]+>", " ", text or ""))).strip()


def parse_gojep_date(text: str) -> str | None:
    """Parse 'Wed Jun 17 11:00:00 COT 2026' → '2026-06-17'."""
    text = _clean(text)
    m = re.search(
        r"\b(?:Mon|Tue|Wed|Thu|Fri|Sat|Sun)\s+"
        r"(Jan|Feb|Mar|Apr|May|Jun|Jul|Aug|Sep|Oct|Nov|Dec)\s+"
        r"(\d{1,2})\b.*?\b(20\d{2})\b",
        text,
        re.I,
    )
    if not m:
        return parse_iso_date(text[:10]) if len(text) >= 10 else None
    month = MONTHS[m.group(1).lower()[:3]]
    day = f"{int(m.group(2)):02d}"
    return f"{m.group(3)}-{month}-{day}"


def _cell_values(row_html: str) -> list[str]:
    return [_clean(td) for td in re.findall(r"<td[^>]*>(.*?)</td>", row_html, re.S | re.I)]


def _title_and_url(cell_html: str) -> tuple[str, str]:
    m = re.search(
        r'href="(/epps/cft/prepareViewCfTWS\.do\?resourceId=\d+)"[^>]*>(.*?)</a>',
        cell_html,
        re.S | re.I,
    )
    if m:
        return _clean(m.group(2)), f"{BASE}{m.group(1)}"
    return _clean(cell_html), f"{OPENED_URL}"


def parse_opened_tenders_html(html: str) -> list[dict[str, Any]]:
    """Opened bids table: title, ref, agency, deadline, method, status."""
    block = re.search(r'<table id="T01">(.*?)</table>', html, re.S | re.I)
    if not block:
        return []
    rows = re.findall(r"<tr>\s*<td>(\d+)</td>(.*?)</tr>", block.group(1), re.S | re.I)
    out: list[dict[str, Any]] = []
    for _num, body in rows:
        cells = _cell_values(f"<td>{_num}</td>{body}")
        if len(cells) < 6:
            continue
        title, url = _title_and_url(body)
        if not title:
            continue
        ref = cells[2] if len(cells) > 2 else ""
        agency = cells[3] if len(cells) > 3 else ""
        closing = parse_gojep_date(cells[4]) if len(cells) > 4 else None
        method = cells[5] if len(cells) > 5 else ""
        status = cells[-1] if cells else ""
        out.append(normalize_record(
            id=ref or title[:80],
            title=title,
            country="Jamaica",
            source="Jamaica GOJEP (opened bids)",
            url=url,
            published=None,
            closing_date=closing,
            category=method,
            agency=agency,
            method=method,
            status=status,
        ))
    return out


def parse_award_notices_html(html: str) -> list[dict[str, Any]]:
    """Contract award notices — recent awards (no future closing date)."""
    block = re.search(r'<table id="T01">(.*?)</table>', html, re.S | re.I)
    if not block:
        return []
    rows = re.findall(r"<tr>\s*<td>(\d+)</td>(.*?)</tr>", block.group(1), re.S | re.I)
    out: list[dict[str, Any]] = []
    for _num, body in rows:
        cells = _cell_values(f"<td>{_num}</td>{body}")
        if len(cells) < 5:
            continue
        title, url = _title_and_url(body)
        if not title:
            continue
        method = cells[1] if len(cells) > 1 else ""
        agency = cells[2] if len(cells) > 2 else ""
        published = parse_gojep_date(cells[5]) if len(cells) > 5 else None
        out.append(normalize_record(
            id=f"award-{title[:60]}",
            title=title,
            country="Jamaica",
            source="Jamaica GOJEP (contract award)",
            url=url,
            published=published,
            closing_date=None,
            category=method,
            agency=agency,
            method=method,
            status="awarded",
        ))
    return out


def latest_snapshot(slug: str) -> str | None:
    if not RAW.exists():
        return None
    files = sorted(RAW.glob(f"{slug}-*.html"), reverse=True)
    if not files:
        return None
    return files[0].read_text(encoding="utf-8", errors="replace")


class JamaicaGojepAdapter(TenderAdapter):
    slug = "jamaica-gojep"
    label = "Jamaica GOJEP"

    def fetch(self) -> list[dict[str, Any]]:
        items: list[dict[str, Any]] = []
        opened_html = self._load(OPENED_URL, "jamaica-gojep-opened", "opened bids")
        if opened_html:
            parsed = parse_opened_tenders_html(opened_html)
            items.extend(parsed)
            print(f"tenders: jamaica gojep opened bids -> {len(parsed)} records")
        awards_html = self._load(AWARDS_URL, "jamaica-gojep-awards", "contract awards")
        if awards_html:
            parsed = parse_award_notices_html(awards_html)
            items.extend(parsed)
            print(f"tenders: jamaica gojep contract awards -> {len(parsed)} records")
        if not items:
            print("tenders: jamaica GOJEP returned no records (live fetch and cache both empty)")
        return items

    def _load(self, url: str, snap_slug: str, label: str) -> str | None:
        try:
            html = http_get(url).decode("utf-8", errors="replace")
            if "An error has occurred" in html and '<table id="T01">' not in html:
                raise RuntimeError(f"GOJEP error page for {label}")
            RAW.mkdir(parents=True, exist_ok=True)
            stamp = datetime.now(timezone.utc).strftime("%Y%m%d")
            (RAW / f"{snap_slug}-{stamp}.html").write_text(html[:2_000_000], encoding="utf-8")
            return html
        except Exception as exc:
            print(f"tenders: jamaica gojep {label} unreachable ({exc}) — trying cache")
            cached = latest_snapshot(snap_slug)
            if cached:
                print(f"tenders: jamaica gojep using cached {label} snapshot")
                return cached
            return None
