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
USER_AGENT = "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 Chrome/124.0 Safari/537.36"


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


# Maps the ECCB HTML table's row labels (lowercased substrings) to our indicator keys.
ECCB_INDICATOR_MAP: dict[str, str] = {
    "claims on private sector": "private_sector_credit",
    "broad money liabilities": "total_deposits",
    "net foreign assets": "net_foreign_assets",
    "domestic claims": "total_assets",
}


class ECCBTableParser(HTMLParser):
    """Parse the ECCB monetary survey aggregate table.

    Table format (one row per indicator, columns are years):
        | Unit | 2021 | 2022 | 2023 | 2024 | 2025
        Net Foreign Assets | EC$M | 11,347 | ... | 14,080
    """

    def __init__(self):
        super().__init__()
        self.in_table = False
        self.in_row = False
        self.in_cell = False
        self.current_row: list[str] = []
        self.current_cell = ""
        self.header_row: list[str] = []
        self.data_rows: list[list[str]] = []
        self._header_captured = False

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
                if not self._header_captured and any(re.match(r"20\d\d", c) for c in self.current_row):
                    self.header_row = self.current_row
                    self._header_captured = True
                else:
                    self.data_rows.append(self.current_row)
        elif tag == "table":
            self.in_table = False

    def handle_data(self, data):
        if self.in_cell:
            self.current_cell += data

    def get_observations(self) -> list[ECCBObservation]:
        """Return one observation per target indicator using the most recent year."""
        observations: list[ECCBObservation] = []

        # Identify year columns from the header row
        year_cols: list[tuple[int, str]] = []
        for idx, cell in enumerate(self.header_row):
            if re.match(r"20\d\d", cell.strip()):
                year_cols.append((idx, cell.strip()))

        if not year_cols:
            return observations

        # Latest and previous year for YoY comparison
        latest_idx, latest_year = year_cols[-1]
        prev_idx, prev_year = year_cols[-2] if len(year_cols) >= 2 else (None, None)

        for row in self.data_rows:
            if not row:
                continue
            label = row[0].strip()
            label_lower = label.lower()

            indicator_key = None
            for fragment, key in ECCB_INDICATOR_MAP.items():
                if fragment in label_lower:
                    indicator_key = key
                    break
            if not indicator_key:
                continue

            if latest_idx >= len(row):
                continue

            def parse_val(s: str) -> float | None:
                try:
                    return float(s.replace(",", "").strip())
                except (ValueError, AttributeError):
                    return None

            current_val = parse_val(row[latest_idx])
            if current_val is None:
                continue

            prev_val = parse_val(row[prev_idx]) if prev_idx is not None and prev_idx < len(row) else None
            yoy_pct = round((current_val - prev_val) / prev_val * 100, 1) if prev_val else None

            period_label = latest_year
            if yoy_pct is not None:
                period_label = f"{latest_year} (YoY: {yoy_pct:+.1f}%)"

            observations.append(ECCBObservation(
                country="Eastern Caribbean Currency Union",
                country_code="ECCU",
                indicator=indicator_key,
                indicator_label=label,
                value=current_val,
                unit="EC$M",
                period=period_label,
                source_url="https://www.eccb-centralbank.org/statistics-category/monetary-and-financial-statistics/summarized-monetary-survey",
            ))

        return observations


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

    all_observations: list[ECCBObservation] = []

    # Monetary survey page has the aggregate ECCU table
    primary_url = config.get("statistics_pages", {}).get(
        "monetary_survey",
        "https://www.eccb-centralbank.org/statistics-category/monetary-and-financial-statistics/summarized-monetary-survey",
    )
    try:
        html = fetch_html(primary_url, timeout)
        parser = ECCBTableParser()
        parser.feed(html)
        obs = parser.get_observations()
        all_observations.extend(obs)
        print(f"Parsed {len(obs)} observations from monetary_survey", flush=True)
    except Exception as exc:
        print(f"Failed to parse monetary_survey: {exc}", file=sys.stderr)

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