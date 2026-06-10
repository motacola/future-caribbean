#!/usr/bin/env python3
"""Poll Tier 2 Caribbean data sources — CARICOM WordPress API and CDB RSS feed.

These sources don't have clean REST APIs like Tier 1, but they publish
machine-readable data through alternative channels (WordPress REST API,
RSS feeds, downloadable XLSX files) that can be polled and normalized.

Sources:
  • CARICOM Statistics — WordPress REST API with country_data + publications
    custom post types. Contains inflation, trade, FDI, debt, GDP data.
  • CDB (Caribbean Development Bank) — RSS feed with procurement notices,
    evaluation reports, and news/events.

Outputs:
  data/tier2/latest.json  — structured snapshot
  signals/tier2/latest.md — human-readable brief

Scrapling is used for adaptive HTML parsing of WordPress content — when
CARICOM's theme or plugin changes the HTML structure, Scrapling's selector
auto-heals instead of breaking like regex-based extraction would.
"""

from __future__ import annotations

import argparse
import json
import re
import ssl
import sys
import urllib.error
import urllib.parse
import urllib.request
import xml.etree.ElementTree as ET
from dataclasses import dataclass, asdict
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

# ── Scrapling import (optional — falls back to regex if not installed) ──
SCRAPLING_AVAILABLE = False
try:
    from scrapling import Selector
    SCRAPLING_AVAILABLE = True
except ImportError:
    pass

ROOT = Path(__file__).resolve().parents[1]
DEFAULT_CONFIG = ROOT / "config" / "tier2_sources.json"
DEFAULT_DATA_DIR = ROOT / "data" / "tier2"
DEFAULT_SIGNAL_DIR = ROOT / "signals" / "tier2"
STATE_FILE = ROOT / "data" / "tier2" / ".sent_items.json"

USER_AGENT = "future-caribbean-signal-os/0.1"


@dataclass(frozen=True)
class DataItem:
    id: str
    source: str
    source_slug: str
    title: str
    item_type: str  # "country_data", "publication", "procurement", "evaluation", "news"
    url: str
    published: str
    modified: str
    data_files: list[str]  # URLs to downloadable XLSX/CSV files
    description: str

    def fingerprint(self) -> str:
        return f"{self.source_slug}:{self.id}@{self.modified}"


def load_config(path: Path) -> dict[str, Any]:
    return json.loads(path.read_text(encoding="utf-8"))


def fetch_json(url: str, timeout: int) -> Any:
    req = urllib.request.Request(url, headers={"User-Agent": USER_AGENT})
    try:
        with urllib.request.urlopen(req, timeout=timeout) as resp:
            return json.loads(resp.read().decode("utf-8"))
    except urllib.error.URLError as exc:
        if isinstance(exc.reason, ssl.SSLCertVerificationError):
            context = ssl._create_unverified_context()
            with urllib.request.urlopen(req, timeout=timeout, context=context) as resp:
                return json.loads(resp.read().decode("utf-8"))
        raise


def fetch_text(url: str, timeout: int) -> str:
    req = urllib.request.Request(url, headers={"User-Agent": USER_AGENT})
    try:
        with urllib.request.urlopen(req, timeout=timeout) as resp:
            return resp.read().decode("utf-8")
    except urllib.error.URLError as exc:
        if isinstance(exc.reason, ssl.SSLCertVerificationError):
            context = ssl._create_unverified_context()
            with urllib.request.urlopen(req, timeout=timeout, context=context) as resp:
                return resp.read().decode("utf-8")
        raise


# ── CARICOM WordPress API ────────────────────────────────

# File extensions we care about when extracting data file links
DATA_EXTENSIONS = ("xlsx", "xls", "csv", "pdf")


def extract_data_files_scrapling(html: str) -> list[str]:
    """Extract downloadable data file URLs from WordPress content HTML.

    Uses Scrapling's CSS selector engine for robust link extraction.
    Falls back to regex if Scrapling is not available.
    """
    urls: list[str] = []
    page = Selector(html)

    # Find all <a> tags whose href ends with a data file extension
    for ext in DATA_EXTENSIONS:
        links = page.css(f'a[href$=".{ext}"], a[href$=".{ext.upper()}"]')
        for link in links:
            href = link.attrib.get("href", "")
            if href:
                urls.append(href)

    # Deduplicate preserving order
    seen = set()
    unique = []
    for u in urls:
        if u not in seen:
            seen.add(u)
            unique.append(u)
    return unique


def extract_data_files_regex(html: str) -> list[str]:
    """Fallback: extract data file URLs using regex (original method)."""
    urls: list[str] = []
    for ext in DATA_EXTENSIONS:
        found = re.findall(
            rf'href=[\"\']([^\"\']*\.{ext})[\"\']', html, re.IGNORECASE
        )
        urls.extend(found)
    seen = set()
    unique = []
    for u in urls:
        if u not in seen:
            seen.add(u)
            unique.append(u)
    return unique


def extract_data_files(html: str) -> list[str]:
    """Extract data file URLs — uses Scrapling if available, else regex."""
    if SCRAPLING_AVAILABLE:
        try:
            return extract_data_files_scrapling(html)
        except Exception:
            pass
    return extract_data_files_regex(html)


def strip_html_to_text(html: str, max_len: int = 200) -> str:
    """Strip HTML tags and truncate to max_len characters."""
    text = re.sub(r"<[^>]+>", "", html)
    text = re.sub(r"\s+", " ", text).strip()
    return text[:max_len]


def poll_caricom(
    config: dict[str, Any], timeout: int
) -> tuple[list[DataItem], list[str]]:
    items: list[DataItem] = []
    errors: list[str] = []
    base = config["base_url"]

    for post_type, pt_config in config.get("post_types", {}).items():
        params = pt_config.get("query_params", "per_page=100")
        url = f"{base}/{post_type}?{params}"
        try:
            payload = fetch_json(url, timeout)
            for entry in payload if isinstance(payload, list) else [payload]:
                item_id = str(entry.get("id", ""))
                title = entry.get("title", {}).get("rendered", "?")
                link = entry.get("link", "")
                date = entry.get("date", "")
                modified = entry.get("modified", "")

                # Extract data files from content HTML
                content = entry.get("content", {}).get("rendered", "")
                data_files = extract_data_files(content)

                # Extract description from content (strip HTML)
                desc = strip_html_to_text(content)

                item = DataItem(
                    id=item_id,
                    source="CARICOM Statistics",
                    source_slug="caricom",
                    title=title,
                    item_type=post_type,
                    url=link,
                    published=date,
                    modified=modified,
                    data_files=data_files,
                    description=desc,
                )
                items.append(item)
        except Exception as exc:
            errors.append(f"caricom/{post_type}: {exc}")

    return items, errors


# ── CDB RSS Feed ─────────────────────────────────────────

def poll_cdb_rss(
    config: dict[str, Any], timeout: int
) -> tuple[list[DataItem], list[str]]:
    items: list[DataItem] = []
    errors: list[str] = []
    feed_url = config.get("feed_url", "")
    signal_types = config.get("signal_types", {})

    if not feed_url:
        return items, errors

    try:
        xml_text = fetch_text(feed_url, timeout)
        root = ET.fromstring(xml_text)

        for entry in root.findall(".//item"):
            title = entry.findtext("title", "?")
            link = entry.findtext("link", "") or ""
            pubdate = entry.findtext("pubDate", "")
            desc = entry.findtext("description", "")[:200]

            # Classify by URL pattern
            item_type = "news"
            for signal_key, signal_cfg in signal_types.items():
                if signal_cfg.get("keyword", "") in link.lower():
                    item_type = signal_key
                    break

            # Build stable ID from link
            item_id = link.split("/")[-1] if link else "unknown"
            if not item_id:
                item_id = f"cdb-{hash(title) % 100000}"

            item = DataItem(
                id=item_id,
                source="Caribbean Development Bank",
                source_slug="cdb",
                title=title.strip(),
                item_type=item_type,
                url=link,
                published=pubdate,
                modified=pubdate,
                data_files=[],
                description=desc.strip(),
            )
            items.append(item)
    except Exception as exc:
        errors.append(f"cdb_rss: {exc}")

    return items, errors


# ── Output ────────────────────────────────────────────────

def write_outputs(
    items: list[DataItem],
    new_items: list[DataItem],
    errors: list[str],
    config: dict[str, Any],
    data_dir: Path,
    signal_dir: Path,
) -> tuple[Path, Path]:
    data_dir.mkdir(parents=True, exist_ok=True)
    signal_dir.mkdir(parents=True, exist_ok=True)
    fetched_at = datetime.now(timezone.utc).isoformat()

    payload = {
        "source": "Tier 2 (CARICOM + CDB)",
        "fetched_at": fetched_at,
        "total_items": len(items),
        "new_items": len(new_items),
        "items": [asdict(i) for i in items],
    }

    json_path = data_dir / "latest.json"
    json_path.write_text(json.dumps(payload, indent=2, sort_keys=True) + "\n", encoding="utf-8")

    md_lines = [
        "# Tier 2 Caribbean Data Signals",
        "",
        "- Sources: CARICOM Statistics (WP API), CDB (RSS)",
        f"- Fetched: {fetched_at}",
        f"- Total items: {len(items)}",
        f"- New since last check: {len(new_items)}",
        "",
    ]

    if new_items:
        by_type: dict[str, list[DataItem]] = {}
        for item in new_items:
            by_type.setdefault(item.item_type, []).append(item)

        for type_key, type_items in sorted(by_type.items()):
            type_label = {"country_data": "📊 Country Data", "publications": "📄 Publications",
                         "procurement": "📋 Procurement", "evaluation": "📊 Evaluation",
                         "news": "📰 News"}.get(type_key, type_key)
            md_lines.append(f"## {type_label}")
            md_lines.append("")
            for item in sorted(type_items, key=lambda x: x.modified, reverse=True):
                md_lines.append(f"- **{item.title}**")
                md_lines.append(f"  Source: {item.source}")
                if item.data_files:
                    md_lines.append(f"  📁 Data: {', '.join(item.data_files[:2])}")
                md_lines.append(f"  🔗 {item.url[:100]}")
                md_lines.append(f"  📅 {item.modified[:10]}")
                md_lines.append("")

    if errors:
        md_lines.append("## Errors")
        md_lines.append("")
        for err in errors:
            md_lines.append(f"- {err}")
        md_lines.append("")

    md_lines.append(f"**Total items tracked:** {len(items)}")
    md_lines.append(f"**New since last check:** {len(new_items)}")

    md_path = signal_dir / "latest.md"
    md_path.write_text("\n".join(md_lines) + "\n", encoding="utf-8")
    return json_path, md_path


def load_state() -> set[str]:
    if STATE_FILE.exists():
        return set(json.loads(STATE_FILE.read_text(encoding="utf-8")))
    return set()


def save_state(items: list[DataItem]) -> None:
    STATE_FILE.parent.mkdir(parents=True, exist_ok=True)
    fingerprints = {i.fingerprint() for i in items}
    STATE_FILE.write_text(json.dumps(sorted(fingerprints), indent=2) + "\n", encoding="utf-8")


def run(
    config_path: Path,
    data_dir: Path,
    signal_dir: Path,
    timeout: int,
) -> int:
    config = load_config(config_path)
    sources = config.get("sources", {})
    all_items: list[DataItem] = []
    all_errors: list[str] = []

    # CARICOM
    caricom_cfg = sources.get("caricom_statistics", {})
    if caricom_cfg:
        items, errors = poll_caricom(caricom_cfg, timeout)
        all_items.extend(items)
        all_errors.extend(errors)

    # CDB RSS
    cdb_cfg = sources.get("cdb_rss", {})
    if cdb_cfg:
        items, errors = poll_cdb_rss(cdb_cfg, timeout)
        all_items.extend(items)
        all_errors.extend(errors)

    if not all_items:
        print("No items retrieved from any Tier 2 source.", file=sys.stderr)
        return 1

    # Delta
    state = load_state()
    new_items = [i for i in all_items if i.fingerprint() not in state]

    json_path, md_path = write_outputs(
        all_items, new_items, all_errors, config, data_dir, signal_dir
    )
    print(f"Wrote {json_path}", flush=True)
    print(f"Wrote {md_path}", flush=True)
    print(f"Total items: {len(all_items)}", flush=True)
    print(f"New items: {len(new_items)}", flush=True)

    save_state(all_items)
    return 0


def main() -> int:
    parser = argparse.ArgumentParser(description="Poll Tier 2 Caribbean data sources.")
    parser.add_argument("--config", type=Path, default=DEFAULT_CONFIG)
    parser.add_argument("--data-dir", type=Path, default=DEFAULT_DATA_DIR)
    parser.add_argument("--signal-dir", type=Path, default=DEFAULT_SIGNAL_DIR)
    parser.add_argument("--timeout", type=int, default=20)
    args = parser.parse_args()
    return run(args.config, args.data_dir, args.signal_dir, args.timeout)


if __name__ == "__main__":
    raise SystemExit(main())
