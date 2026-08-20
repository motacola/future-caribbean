"""IDB procurement notices and contract award notifications.

Why a second publisher matters
------------------------------
Until now every procurement record came from a national portal, and each
portal both announced its tenders and announced their outcomes. A source
cannot corroborate itself, so no outcome in the corpus could ever be
independently resolved — the ceiling was structural, not a matching bug.

The IDB publishes bidding notices and award notifications for the
projects it finances across the region. Where a tender appears both here
and on a national portal, one publisher's award notice resolves the
other's opportunity, which is the only way an outcome earns the word
`independent`.

The dataset also widens coverage well past the two countries the
national adapters reach: roughly 2,700 Caribbean bidding notices with
real deadlines and 400 award notifications across seven jurisdictions.

Source: data.iadb.org CKAN, "IDB Project procurement bidding notices and
notification of contract awards dataset" (CSV).
"""
from __future__ import annotations

import csv
import io
from datetime import datetime, timezone
from html import unescape
from typing import Any

from .base import RAW, TenderAdapter, http_get, normalize_record, parse_iso_date

CSV_URL = "https://data.iadb.org/file/download/9cc29cd0-c487-42e9-ad49-9971b4125066"

NOTICE_SOURCE = "IDB Procurement Notices"
AWARD_SOURCE = "IDB Contract Award Notifications"

# Caribbean scope (AGENTS.md: Caribbean-only unless reopened explicitly).
COUNTRIES = {
    "GUYANA": "Guyana",
    "JAMAICA": "Jamaica",
    "BARBADOS": "Barbados",
    "TRINIDAD AND TOBAGO": "Trinidad and Tobago",
    "SURINAME": "Suriname",
    "BELIZE": "Belize",
    "BAHAMAS": "Bahamas",
    "HAITI": "Haiti",
    "DOMINICAN REPUBLIC": "Dominican Republic",
}

# Notice types that announce an opportunity vs an outcome. GENERAL notices
# are programme-level ("General Procurement Notice") with no tender of their
# own, so they are not opportunities and are skipped.
OPPORTUNITY_TYPES = {"SPECIFIC", "EOI"}
AWARD_TYPES = {"AWARD"}

# Programme-level notices announce a whole loan operation, not a tender, and
# carry the operation's horizon as a "deadline" — one such row typed itself
# SPECIFIC and produced a 1,032-day detection lead time. They are excluded on
# their title as well as their type.
PROGRAMME_TITLE_PREFIX = "general procurement notice"

# The CSV carries every notice back to 2001. Procurement horizons are weeks
# to months, so a notice from a decade ago can never be resolved by this
# desk — it would only inflate the corpus with permanently `unresolved`
# records. The window is measured against the newest publication date in
# the file rather than the wall clock, so replaying a given snapshot always
# produces the same corpus.
RECENT_YEARS = 2


def _parse_us_date(text: str | None) -> str | None:
    """IDB deadlines are M/D/YYYY; publication dates are ISO."""
    text = (text or "").strip()
    if not text or text.upper() == "NULL":
        return None
    for fmt in ("%m/%d/%Y", "%Y-%m-%d"):
        try:
            return datetime.strptime(text[:10], fmt).date().isoformat()
        except ValueError:
            continue
    return parse_iso_date(text)


def parse_idb_notices(csv_text: str) -> list[dict[str, Any]]:
    """Normalize the IDB notice CSV into tender records.

    Award notifications are emitted with `status="awarded"` so the resolver
    treats them as outcomes; bidding notices carry their deadline as the
    closing date. Rows outside the Caribbean, and programme-level GENERAL
    notices, are dropped.
    """
    rows = list(csv.DictReader(io.StringIO(csv_text)))
    published = [d for d in (_parse_us_date(r.get("publicationdate")) for r in rows) if d]
    cutoff = f"{int(max(published)[:4]) - RECENT_YEARS:04d}-01-01" if published else ""

    out: list[dict[str, Any]] = []
    for row in rows:
        country = COUNTRIES.get((row.get("countryname") or "").strip().upper())
        if not country:
            continue
        published_at = _parse_us_date(row.get("publicationdate"))
        if cutoff and (published_at or "") < cutoff:
            continue
        kind = (row.get("type") or "").strip().upper()
        title = unescape((row.get("noticetitle") or "").strip())
        if not title or title.lower().startswith(PROGRAMME_TITLE_PREFIX):
            continue

        if kind in AWARD_TYPES:
            source, status, closing = AWARD_SOURCE, "awarded", None
        elif kind in OPPORTUNITY_TYPES:
            source, status = NOTICE_SOURCE, "Bid submission"
            closing = _parse_us_date(row.get("deadline"))
        else:
            continue

        out.append(normalize_record(
            id=(row.get("noticeid") or "").strip(),
            title=title,
            country=country,
            source=source,
            url=(row.get("documenturl") or row.get("proyecturl") or "").strip(),
            published=published_at,
            closing_date=closing,
            # The notice CSV carries no executing agency; the resolver
            # matches these on country + title alone (see resolvers/
            # procurement.py, alias matching) rather than inventing a buyer.
            agency="",
            category=(row.get("sectorenglnm") or row.get("sector") or "").strip(),
            method=(row.get("prcrmnt_mthd_engl_nm") or "").strip(),
            status=status,
        ))
    return out


class IdbProcurementAdapter(TenderAdapter):
    slug = "idb-procurement"
    label = "IDB procurement notices"

    def fetch(self) -> list[dict[str, Any]]:
        try:
            csv_text = http_get(CSV_URL).decode("utf-8", errors="replace")
        except Exception as exc:
            print(f"tenders: idb procurement unreachable ({exc}) — trying cache")
            csv_text = self._cached()
            if not csv_text:
                return []
        if not csv_text.strip():
            print("tenders: idb procurement returned an empty body")
            return []
        self._snapshot(csv_text)
        items = parse_idb_notices(csv_text)
        awards = sum(1 for i in items if i["source"] == AWARD_SOURCE)
        print(f"tenders: idb procurement -> {len(items)} Caribbean records ({awards} award notifications)")
        return items

    def _snapshot(self, csv_text: str) -> None:
        RAW.mkdir(parents=True, exist_ok=True)
        stamp = datetime.now(timezone.utc).strftime("%Y%m%d")
        (RAW / f"{self.slug}-{stamp}.csv").write_text(csv_text, encoding="utf-8")

    def _cached(self) -> str | None:
        if not RAW.exists():
            return None
        for path in sorted(RAW.glob(f"{self.slug}-*.csv"), reverse=True):
            try:
                if path.stat().st_size == 0:
                    continue
                return path.read_text(encoding="utf-8", errors="replace")
            except OSError:
                continue
        return None
