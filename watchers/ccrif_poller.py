#!/usr/bin/env python3
"""Poll CCRIF SPC (Caribbean Catastrophe Risk Insurance Facility) for parametric insurance payouts.

CCRIF parametric insurance payouts are immediate capital flow signals:
- Payout = parametric trigger hit = verified hazard event = capital inflow
- Countries: 16 Caribbean members + Central America
- Perils: Tropical cyclone, earthquake, excess rainfall
- Payouts are public and announced on their website

Source: CCRIF SPC website (https://www.ccrif.org)
"""

from __future__ import annotations

import argparse
import json
import re
import ssl
import sys
import urllib.error
import urllib.request
from dataclasses import dataclass, asdict
from datetime import datetime, timezone
from pathlib import Path
from typing import Any
from html.parser import HTMLParser

ROOT = Path(__file__).resolve().parents[1]
DEFAULT_CONFIG = ROOT / "config" / "ccrif_sources.json"
DEFAULT_DATA_DIR = ROOT / "data" / "ccrif"
DEFAULT_SIGNAL_DIR = ROOT / "signals" / "ccrif"
USER_AGENT = "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 Chrome/124.0 Safari/537.36"


@dataclass(frozen=True)
class PayoutEvent:
    id: str
    country: str
    country_code: str
    peril: str
    payout_usd: float
    event_date: str
    announced_date: str
    policy_type: str
    source_url: str

    def fingerprint(self) -> str:
        return f"ccrif:{self.country_code}:{self.peril}:{self.event_date}:{self.payout_usd:.0f}"


COUNTRY_NAME_TO_CODE: dict[str, str] = {
    "antigua": "AG", "barbuda": "AG",
    "barbados": "BB",
    "belize": "BZ",
    "dominica": "DM",
    "grenada": "GD",
    "guyana": "GY",
    "haiti": "HT",
    "jamaica": "JM",
    "st. kitts": "KN", "saint kitts": "KN", "st kitts": "KN",
    "st. lucia": "LC", "saint lucia": "LC",
    "montserrat": "MS",
    "suriname": "SR",
    "turks": "TC",
    "trinidad": "TT",
    "st. vincent": "VC", "saint vincent": "VC",
    "british virgin": "VG",
    "anguilla": "AI",
    "bahamas": "BS",
    "cayman": "KY",
    "nicaragua": "NI",
    "guatemala": "GT",
    "honduras": "HN",
    "costa rica": "CR",
    "panama": "PA",
    "el salvador": "SV",
}


def _country_code(name: str) -> str | None:
    low = name.lower()
    for fragment, code in COUNTRY_NAME_TO_CODE.items():
        if fragment in low:
            return code
    return None


def _peril_from_event(event: str) -> str:
    low = event.lower()
    if any(w in low for w in ["tropical cyclone", "hurricane", "tropical storm"]):
        return "tropical_cyclone"
    if "earthquake" in low:
        return "earthquake"
    if any(w in low for w in ["rainfall", "trough", "flood"]):
        return "excess_rainfall"
    return "unknown"


def _date_from_event(event: str) -> str:
    """Best-effort: extract year from event text, fall back to today."""
    m = re.search(r"\b(20\d{2})\b", event)
    return f"{m.group(1)}-01-01" if m else datetime.now(timezone.utc).date().isoformat()


class CCRIFParser(HTMLParser):
    """Parse the CCRIF payouts table at /aboutus/ccrif-spc-payouts.

    Table format: Event | Country Affected | Payouts (USD)
    Multi-country events have blank event cell in subsequent rows.
    """

    def __init__(self):
        super().__init__()
        self.in_table = False
        self.in_row = False
        self.in_cell = False
        self.current_row: list[str] = []
        self.current_cell = ""
        self.all_rows: list[list[str]] = []

    def handle_starttag(self, tag, attrs):
        if tag == "table":
            self.in_table = True
        elif tag == "tr" and self.in_table:
            self.in_row = True
            self.current_row = []
        elif tag in ("td", "th") and self.in_row:
            self.in_cell = True
            self.current_cell = ""

    def handle_endtag(self, tag):
        if tag in ("td", "th") and self.in_cell:
            self.in_cell = False
            self.current_row.append(self.current_cell.strip())
        elif tag == "tr" and self.in_row:
            self.in_row = False
            if self.current_row:
                self.all_rows.append(self.current_row)
        elif tag == "table":
            self.in_table = False

    def handle_data(self, data):
        if self.in_cell:
            self.current_cell += data

    def handle_entityref(self, name):
        if self.in_cell and name == "amp":
            self.current_cell += "&"

    def get_payouts(self) -> list[PayoutEvent]:
        payouts: list[PayoutEvent] = []
        last_event = ""
        for row in self.all_rows:
            if len(row) < 2:
                continue
            # Skip header rows
            if row[0].lower() in ("event", "") and row[1].lower() in ("country affected", "member", ""):
                continue
            # Skip totals rows
            if re.match(r"total", row[0], re.I):
                continue

            event_cell = row[0].strip()
            if event_cell:
                last_event = event_cell

            if len(row) < 3:
                continue

            country_cell = row[1].strip()
            amount_cell = row[2].strip() if len(row) > 2 else ""
            if not country_cell or not amount_cell:
                continue

            country_code = _country_code(country_cell)
            if not country_code:
                continue

            try:
                amount = float(amount_cell.replace(",", "").replace("$", "").strip())
            except ValueError:
                continue
            if amount <= 0:
                continue

            # Rows like "Excess Rainfall - Jamaica" encode the peril in the country cell
            peril = _peril_from_event(country_cell) if _peril_from_event(country_cell) != "unknown" else _peril_from_event(last_event)
            event_date = _date_from_event(last_event)
            payouts.append(PayoutEvent(
                id=f"ccrif-{country_code.lower()}-{peril}-{event_date}",
                country=country_cell,
                country_code=country_code,
                peril=peril,
                payout_usd=amount,
                event_date=event_date,
                announced_date=event_date,
                policy_type="parametric",
                source_url="https://www.ccrif.org/aboutus/ccrif-spc-payouts",
            ))
        return payouts


def fetch_html(url: str, timeout: int) -> str:
    req = urllib.request.Request(url, headers={"User-Agent": USER_AGENT})
    try:
        with urllib.request.urlopen(req, timeout=timeout) as response:
            return response.read().decode("utf-8")
    except urllib.error.URLError as exc:
        if isinstance(exc.reason, ssl.SSLCertVerificationError):
            context = ssl._create_unverified_context()
            with urllib.request.urlopen(req, timeout=timeout, context=context) as response:
                return response.read().decode("utf-8")
        raise


def load_config(path: Path) -> dict[str, Any]:
    return json.loads(path.read_text(encoding="utf-8"))


def load_state(path: Path) -> set[str]:
    if path.exists():
        try:
            return set(json.loads(path.read_text(encoding="utf-8")))
        except (json.JSONDecodeError, OSError):
            pass
    return set()


def save_state(path: Path, fingerprints: set[str]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(sorted(fingerprints), indent=2) + "\n", encoding="utf-8")


def write_outputs(
    payouts: list[PayoutEvent],
    data_dir: Path,
    signal_dir: Path,
) -> tuple[Path, Path]:
    data_dir.mkdir(parents=True, exist_ok=True)
    signal_dir.mkdir(parents=True, exist_ok=True)
    fetched_at = datetime.now(timezone.utc).isoformat()

    payload = {
        "source": "CCRIF SPC",
        "fetched_at": fetched_at,
        "payouts": [asdict(p) for p in payouts],
    }

    json_path = data_dir / "latest.json"
    json_path.write_text(json.dumps(payload, indent=2, sort_keys=True) + "\n", encoding="utf-8")

    md_lines = [
        "# CCRIF Parametric Insurance Payouts",
        "",
        "- Source: CCRIF SPC (Caribbean Catastrophe Risk Insurance Facility)",
        f"- Fetched: {fetched_at}",
        f"- Payouts found: {len(payouts)}",
        "",
    ]

    if payouts:
        by_peril: dict[str, list[PayoutEvent]] = {}
        for p in payouts:
            by_peril.setdefault(p.peril, []).append(p)

        for peril, items in sorted(by_peril.items()):
            md_lines.append(f"## {peril.replace('_', ' ').title()}")
            md_lines.append("")
            for p in sorted(items, key=lambda x: x.payout_usd, reverse=True):
                md_lines.append(f"- **{p.country}**: US$ {p.payout_usd:,.0f} ({p.peril})")
                md_lines.append(f"  Event: {p.event_date} | Announced: {p.announced_date}")
                md_lines.append(f"  Policy: {p.policy_type} | [Source]({p.source_url})")
                md_lines.append("")
    else:
        md_lines.append("- No new payouts found in this run.")

    md_path = signal_dir / "latest.md"
    md_path.write_text("\n".join(md_lines) + "\n", encoding="utf-8")
    return json_path, md_path


def run(
    config_path: Path,
    data_dir: Path,
    signal_dir: Path,
    timeout: int,
) -> int:
    config = load_config(config_path)
    state_file = data_dir / ".sent_payouts.json"
    state = load_state(state_file)

    # Fetch and parse the consolidated payouts table
    html = ""
    try:
        html = fetch_html(config["payouts_page"], timeout)
    except Exception as exc:
        print(f"Failed to fetch CCRIF page: {exc}", file=sys.stderr)

    parser = CCRIFParser()
    parser.feed(html)
    payouts = parser.get_payouts()

    # Deduplicate
    seen = set()
    unique_payouts = []
    for p in payouts:
        fp = p.fingerprint()
        if fp not in seen and fp not in state:
            seen.add(fp)
            unique_payouts.append(p)

    if not unique_payouts:
        print("No new CCRIF payouts found.", flush=True)

    json_path, md_path = write_outputs(unique_payouts, data_dir, signal_dir)
    print(f"Wrote {json_path}", flush=True)
    print(f"Wrote {md_path}", flush=True)
    print(f"New payouts: {len(unique_payouts)}", flush=True)

    # Update state
    all_fingerprints = state | {p.fingerprint() for p in payouts}
    save_state(state_file, all_fingerprints)

    return 0


def main() -> int:
    parser = argparse.ArgumentParser(description="Poll CCRIF SPC for parametric insurance payouts.")
    parser.add_argument("--config", type=Path, default=DEFAULT_CONFIG)
    parser.add_argument("--data-dir", type=Path, default=DEFAULT_DATA_DIR)
    parser.add_argument("--signal-dir", type=Path, default=DEFAULT_SIGNAL_DIR)
    parser.add_argument("--timeout", type=int, default=30)
    args = parser.parse_args()
    return run(args.config, args.data_dir, args.signal_dir, args.timeout)


if __name__ == "__main__":
    raise SystemExit(main())