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
USER_AGENT = "future-caribbean-signal-os/0.1"


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


class CCRIFParser(HTMLParser):
    """Parse CCRIF payout announcements from HTML."""

    def __init__(self):
        super().__init__()
        self.in_payout_section = False
        self.current_data = []
        self.payouts = []
        self.current_tag = ""
        self.current_attrs = {}

    def handle_starttag(self, tag, attrs):
        self.current_tag = tag
        self.current_attrs = dict(attrs)
        if tag == "article" or (tag == "div" and "payout" in str(attrs).lower()):
            self.in_payout_section = True
            self.current_data = []

    def handle_endtag(self, tag):
        if self.in_payout_section and (tag == "article" or tag == "div"):
            self.in_payout_section = False
            # Process collected data
            self._process_payout()

    def handle_data(self, data):
        if self.in_payout_section:
            self.current_data.append(data.strip())

    def _process_payout(self):
        """Extract payout info from collected text."""
        text = " ".join(self.current_data)
        # Look for patterns like "US$X million to Country" or "payout of $X"
        payout_match = re.search(r"(?:US\$|\$)\s*([\d,.]+)\s*(?:million|M|billion|B)?", text, re.IGNORECASE)
        country_codes = ["AG", "BB", "BZ", "DM", "GD", "GY", "HT", "JM", "KN", "LC", "MS", "SR", "TC", "TT", "VC", "VG", "HN", "GT", "PA", "NI", "CR", "SV", "BQ", "CW", "SX"]
        country_names = {
            "Antigua": "AG", "Barbados": "BB", "Belize": "BZ", "Dominica": "DM",
            "Grenada": "GD", "Guyana": "GY", "Haiti": "HT", "Jamaica": "JM",
            "St. Kitts": "KN", "St. Lucia": "LC", "Montserrat": "MS", "Suriname": "SR",
            "Turks": "TC", "Trinidad": "TT", "St. Vincent": "VC", "British Virgin": "VG",
            "Anguilla": "AI"
        }
        country = None
        for name, code in country_names.items():
            if name.lower() in text.lower():
                country = code
                break

        peril = None
        for p in ["tropical cyclone", "hurricane", "earthquake", "excess rainfall", "rainfall"]:
            if p in text.lower():
                peril = p.replace(" ", "_")
                break

        if payout_match and country:
            amount_str = payout_match.group(1).replace(",", "")
            try:
                amount = float(amount_str)
                if "million" in text.lower() or "M" in text.lower():
                    amount *= 1_000_000
                elif "billion" in text.lower() or "B" in text.lower():
                    amount *= 1_000_000_000
            except ValueError:
                amount = 0.0

            payout = PayoutEvent(
                id=f"ccrif-{country.lower()}-{peril or 'unknown'}-{datetime.now(timezone.utc).strftime('%Y%m%d')}",
                country=country,
                country_code=country,
                peril=peril or "unknown",
                payout_usd=amount,
                event_date=datetime.now(timezone.utc).date().isoformat(),
                announced_date=datetime.now(timezone.utc).date().isoformat(),
                policy_type="parametric",
                source_url="https://www.ccrif.org",
            )
            self.payouts.append(payout)

    def get_payouts(self):
        return self.payouts


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

    # Fetch and parse
    html = ""
    try:
        html = fetch_html(config["payouts_page"], timeout)
    except Exception as exc:
        print(f"Failed to fetch CCRIF page: {exc}", file=sys.stderr)

    parser = CCRIFParser()
    parser.feed(html)
    payouts = parser.get_payouts()

    # Also try news page
    for peril in config.get("perils", []):
        try:
            news_url = f"https://www.ccrif.org/news?peril={peril}"
            news_html = fetch_html(news_url, timeout)
            parser2 = CCRIFParser()
            parser2.feed(news_html)
            payouts.extend(parser2.get_payouts())
        except Exception:
            pass

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