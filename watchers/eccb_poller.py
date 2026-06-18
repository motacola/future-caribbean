#!/usr/bin/env python3
"""Poll Eastern Caribbean Central Bank (ECCB) for monetary and financial statistics.

ECCB publishes key monetary indicators for the Eastern Caribbean Currency Union (ECCU):
- Private sector credit growth
- Total deposits
- Net foreign assets
- Total assets
- Net claims on government

These are capital flow and banking health signals for 8 ECCU members.

Source: ECCB website statistics pages (HTML tables with download options)
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
DEFAULT_CONFIG = ROOT / "config" / "eccb_sources.json"
DEFAULT_DATA_DIR = ROOT / "data" / "eccb"
DEFAULT_SIGNAL_DIR = ROOT / "signals" / "eccb"
USER_AGENT = "future-caribbean-signal-os/0.1"


@dataclass(frozen=True)
class ECCBObservation:
    country: str
    country_code: str
    indicator: str
    indicator_label: str
    value: float
    unit: str
    period: str
    source_url: str

    def fingerprint(self) -> str:
        return f"eccb:{self.country_code}:{self.indicator}:{self.period}:{self.value:.0f}"


class ECCBTableParser(HTMLParser):
    """Parse ECCB statistics tables from HTML."""

    def __init__(self, target_indicators: list[str]):
        super().__init__()
        self.in_table = False
        self.in_row = False
        self.in_cell = False
        self.current_row = []
        self.current_cell = ""
        self.tables = []
        self.headers = []
        self.target_indicators = [t.lower() for t in target_indicators]

    def handle_starttag(self, tag, attrs):
        attrs_dict = dict(attrs)
        if tag == "table":
            self.in_table = True
            self.current_row = []
        elif tag == "tr" and self.in_table:
            self.in_row = True
            self.current_row = []
        elif tag == "td" and self.in_row:
            self.in_cell = True
            self.current_cell = ""
        elif tag == "th" and self.in_table and not self.headers:
            self.in_cell = True
            self.current_cell = ""

    def handle_endtag(self, tag):
        if tag == "td" and self.in_cell:
            self.in_cell = False
            self.current_row.append(self.current_cell.strip())
        elif tag == "th" and self.in_cell:
            self.in_cell = False
            self.headers.append(self.current_cell.strip())
        elif tag == "tr" and self.in_row:
            self.in_row = False
            if self.current_row:
                self.tables.append(self.current_row)
        elif tag == "table":
            self.in_table = False

    def handle_data(self, data):
        if self.in_cell:
            self.current_cell += data

    def get_observations(self, country_codes: list[str]) -> list[ECCBObservation]:
        """Extract target indicators from parsed tables."""
        observations = []
        if not self.headers or not self.tables:
            return observations

        # Find indicator columns
        indicator_cols = {}
        for idx, header in enumerate(self.headers):
            header_lower = header.lower()
            for target in self.target_indicators:
                if target.lower() in header_lower:
                    indicator_cols[target] = idx

        if not indicator_cols:
            return observations

        for row in self.tables:
            if len(row) <= max(indicator_cols.values()):
                continue

            # First column is usually country/period
            country = row[0] if row else ""
            country_code = None
            for cc in country_codes:
                if cc.lower() in country.lower() or country.lower() in cc.lower():
                    country_code = cc
                    break

            if not country_code:
                continue

            period = ""
            if len(row) > 1:
                period = row[1]

            for indicator, col_idx in indicator_cols.items():
                if col_idx < len(row):
                    value_str = row[col_idx].replace(",", "").replace("EC$", "").replace("$", "").strip()
                    try:
                        value = float(value_str)
                    except ValueError:
                        continue

                    observations.append(ECCBObservation(
                        country=country,
                        country_code=country_code,
                        indicator=indicator,
                        indicator_label=indicator.replace("_", " ").title(),
                        value=value,
                        unit="EC$M",
                        period=period,
                        source_url="https://www.eccb-centralbank.org/statistics",
                    ))

        return observations


def fetch_html(url: str, timeout: int) -> str:
    req = urllib.request.Request(url, headers={"User-Agent": "future-caribbean-signal-os/0.1"})
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
    observations: list[ECCBObservation],
    data_dir: Path,
    signal_dir: Path,
) -> tuple[Path, Path]:
    data_dir.mkdir(parents=True, exist_ok=True)
    signal_dir.mkdir(parents=True, exist_ok=True)
    fetched_at = datetime.now(timezone.utc).isoformat()

    payload = {
        "source": "Eastern Caribbean Central Bank",
        "fetched_at": fetched_at,
        "observations": [asdict(o) for o in observations],
    }

    json_path = data_dir / "latest.json"
    json_path.write_text(json.dumps(payload, indent=2, sort_keys=True) + "\n", encoding="utf-8")

    md_lines = [
        "# ECCB Monetary & Financial Statistics",
        "",
        "- Source: Eastern Caribbean Central Bank",
        f"- Fetched: {fetched_at}",
        f"- Observations: {len(observations)}",
        "",
        "## Key Indicators",
        "",
    ]

    by_indicator: dict[str, list[ECCBObservation]] = {}
    for obs in observations:
        by_indicator.setdefault(obs.indicator, []).append(obs)

    for indicator, items in sorted(by_indicator.items()):
        md_lines.append(f"### {indicator.replace('_', ' ').title()}")
        md_lines.append("")
        for obs in sorted(items, key=lambda x: x.value, reverse=True):
            md_lines.append(f"- **{obs.country}** ({obs.country_code}): {obs.value:,.1f} {obs.unit} ({obs.period})")
        md_lines.append("")

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
    state_file = data_dir / ".sent_eccb.json"
    state = load_state(state_file)

    member_countries = config.get("member_countries", [])
    target_indicators = list(config.get("indicators", {}).keys())

    all_observations: list[ECCBObservation] = []

    # Try monetary survey page
    for page_name, page_url in config.get("statistics_pages", {}).items():
        try:
            html = fetch_html(page_url, timeout)
            parser = ECCBTableParser(target_indicators)
            parser.feed(html)
            obs = parser.get_observations(member_countries)
            all_observations.extend(obs)
            print(f"Parsed {len(obs)} observations from {page_name}", flush=True)
        except Exception as exc:
            print(f"Failed to parse {page_name}: {exc}", file=sys.stderr)

    # Deduplicate
    seen = set()
    unique_obs = []
    for o in all_observations:
        fp = o.fingerprint()
        if fp not in seen and fp not in state:
            seen.add(fp)
            unique_obs.append(o)

    if not unique_obs:
        print("No new ECCB observations found.", flush=True)

    json_path, md_path = write_outputs(unique_obs, data_dir, signal_dir)
    print(f"Wrote {json_path}", flush=True)
    print(f"Wrote {md_path}", flush=True)
    print(f"New observations: {len(unique_obs)}", flush=True)

    # Update state
    all_fingerprints = state | {o.fingerprint() for o in all_observations}
    save_state(state_file, all_fingerprints)

    return 0


def main() -> int:
    parser = argparse.ArgumentParser(description="Poll ECCB for monetary statistics.")
    parser.add_argument("--config", type=Path, default=DEFAULT_CONFIG)
    parser.add_argument("--data-dir", type=Path, default=DEFAULT_DATA_DIR)
    parser.add_argument("--signal-dir", type=Path, default=DEFAULT_SIGNAL_DIR)
    parser.add_argument("--timeout", type=int, default=30)
    args = parser.parse_args()
    return run(args.config, args.data_dir, args.signal_dir, args.timeout)


if __name__ == "__main__":
    raise SystemExit(main())