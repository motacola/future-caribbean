#!/usr/bin/env python3
"""Poll the IDB Open Data CKAN portal for new/updated Caribbean datasets.

No API key required. Tracks dataset IDs and metadata_modified timestamps
for delta detection, then emits signal briefs for new and updated datasets
relevant to Abeng topics.

Outputs:
  data/idb/latest.json  — full structured snapshot
  signals/idb/latest.md — human-readable signal brief
"""

from __future__ import annotations

import argparse
import json
import ssl
import sys
import urllib.error
import urllib.parse
import urllib.request
from dataclasses import dataclass, asdict
from datetime import datetime, timezone
from pathlib import Path
from typing import Any


ROOT = Path(__file__).resolve().parents[1]
DEFAULT_CONFIG = ROOT / "config" / "idb_sources.json"
DEFAULT_DATA_DIR = ROOT / "data" / "idb"
DEFAULT_SIGNAL_DIR = ROOT / "signals" / "idb"
STATE_FILE = ROOT / "data" / "idb" / ".sent_datasets.json"

CKAN_BASE = "https://data.iadb.org/api/3"
USER_AGENT = "future-caribbean-signal-os/0.1"


@dataclass(frozen=True)
class Dataset:
    id: str
    title: str
    description: str
    created: str
    modified: str
    resources: list[dict[str, Any]]
    topics: list[str]
    url: str

    def fingerprint(self) -> str:
        """Stable ID for dedup: dataset id + modification timestamp."""
        return f"{self.id}@{self.modified}"


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


def extract_title(raw: dict[str, str] | str | None) -> str:
    """Get English title, fall back to any available language.

    The IDB CKAN API returns titles as either a language-keyed dict
    ({"en": "...", "es": "..."}) or a plain string. Handle both shapes
    and never raise on a malformed record — return "" so the dataset is
    still emitted with a fingerprint for dedup.
    """
    if not raw:
        return ""
    if isinstance(raw, str):
        return raw
    if not isinstance(raw, dict):
        return ""
    for lang in ("en", "es", "fr", "pt_BR"):
        value = raw.get(lang)
        if value:
            return value
    return ""


def extract_description(raw: dict[str, str] | str | None) -> str:
    """Get English description, or any language, or empty."""
    if not raw:
        return ""
    if isinstance(raw, str):
        return raw
    for lang in ("en", "es", "fr", "pt_BR"):
        if raw.get(lang):
            return raw[lang]
    return ""


def classify_topics(
    title: str, description: str, topic_keywords: dict[str, list[str]]
) -> list[str]:
    """Match dataset text to known topic keywords."""
    text = f"{title} {description}".lower()
    matched = []
    for topic, keywords in topic_keywords.items():
        if any(kw in text for kw in keywords):
            matched.append(topic)
    return matched


def should_exclude(title: str, description: str, exclude_keywords: list[str]) -> bool:
    text = f"{title} {description}".lower()
    return any(kw in text for kw in exclude_keywords)


def parse_datasets(
    payload: Any,
    topic_keywords: dict[str, list[str]],
    exclude_keywords: list[str],
) -> list[Dataset]:
    results = payload.get("result", {}).get("results", [])
    datasets: list[Dataset] = []
    for r in results:
        title = extract_title(r.get("title", {}))
        desc = extract_description(r.get("notes", ""))
        if exclude_keywords and should_exclude(title, desc, exclude_keywords):
            continue
        topics = classify_topics(title, desc, topic_keywords)
        dataset = Dataset(
            id=r.get("id", ""),
            title=title,
            description=desc[:200],
            created=r.get("metadata_created", ""),
            modified=r.get("metadata_modified", ""),
            resources=[
                {
                    "format": res.get("format", ""),
                    "url": res.get("url", ""),
                    "created": res.get("created", ""),
                }
                for res in r.get("resources", [])
                if res.get("format") and res.get("url")
            ],
            topics=topics,
            url=f"https://data.iadb.org/en/search?q={urllib.parse.quote(title[:40])}",
        )
        datasets.append(dataset)
    return datasets


def detect_new_and_updated(
    current: list[Dataset], state: set[str]
) -> tuple[list[Dataset], list[Dataset]]:
    """Returns (new_datasets, updated_datasets) based on fingerprint state."""
    new: list[Dataset] = []
    updated: list[Dataset] = []
    seen_ids: dict[str, str] = {}  # id -> current fingerprint

    for ds in current:
        fp = ds.fingerprint()
        seen_ids[ds.id] = fp
        if fp not in state:
            # Check if we've seen this ID before (different timestamp = update)
            id_only_fingerprints = {f for f in state if f.startswith(ds.id + "@")}
            if id_only_fingerprints:
                updated.append(ds)
            else:
                new.append(ds)

    return new, updated


def format_topic_badges(topics: list[str]) -> str:
    if not topics:
        return ""
    badges = " ".join(f"#{t}" for t in topics)
    return badges


def write_outputs(
    datasets: list[Dataset],
    new: list[Dataset],
    updated: list[Dataset],
    config: dict[str, Any],
    data_dir: Path,
    signal_dir: Path,
) -> tuple[Path, Path]:
    data_dir.mkdir(parents=True, exist_ok=True)
    signal_dir.mkdir(parents=True, exist_ok=True)
    fetched_at = datetime.now(timezone.utc).isoformat()

    payload = {
        "source": "IDB Open Data (CKAN)",
        "fetched_at": fetched_at,
        "total_datasets": len(datasets),
        "datasets": [asdict(ds) for ds in datasets],
        "new": [asdict(ds) for ds in new],
        "updated": [asdict(ds) for ds in updated],
    }

    json_path = data_dir / "latest.json"
    json_path.write_text(json.dumps(payload, indent=2, sort_keys=True) + "\n", encoding="utf-8")

    # Build signal brief
    md_lines = [
        "# IDB Caribbean Dataset Signals",
        "",
        f"- Source: {config['source']}",
        f"- Fetched: {fetched_at}",
        f"- Total Caribbean datasets tracked: {len(datasets)}",
        "",
    ]

    if new:
        md_lines.extend([
            "## New Datasets",
            "",
        ])
        for ds in sorted(new, key=lambda d: d.modified, reverse=True):
            badges = format_topic_badges(ds.topics)
            md_lines.append(f"- *{ds.title}* {badges}")
            if ds.description:
                desc = ds.description[:120].replace("\n", " ")
                md_lines.append(f"  {desc}")
            formats = [r["format"] for r in ds.resources[:3]]
            if formats:
                md_lines.append(f"  Formats: {', '.join(formats)}")
            md_lines.append(f"  Published: {ds.created[:10]}, Updated: {ds.modified[:10]}")
            md_lines.append("")

    if updated:
        md_lines.extend([
            "## Recently Updated Datasets",
            "",
        ])
        for ds in sorted(updated, key=lambda d: d.modified, reverse=True)[:15]:
            badges = format_topic_badges(ds.topics)
            md_lines.append(f"- *{ds.title}* {badges}")
            md_lines.append(f"  Updated: {ds.modified[:10]}")
            md_lines.append("")

    if not new and not updated:
        md_lines.append("No new or updated datasets since last check.")
        md_lines.append("")

    # Observation count
    md_lines.extend([
        f"**Total datasets tracked:** {len(datasets)}",
        f"**New since last poll:** {len(new)}",
        f"**Updated since last poll:** {len(updated)}",
    ])

    md_path = signal_dir / "latest.md"
    md_path.write_text("\n".join(md_lines) + "\n", encoding="utf-8")
    return json_path, md_path


def load_state() -> set[str]:
    if STATE_FILE.exists():
        return set(json.loads(STATE_FILE.read_text(encoding="utf-8")))
    return set()


def save_state(datasets: list[Dataset]) -> None:
    STATE_FILE.parent.mkdir(parents=True, exist_ok=True)
    fingerprints = {ds.fingerprint() for ds in datasets}
    STATE_FILE.write_text(json.dumps(sorted(fingerprints), indent=2) + "\n", encoding="utf-8")


def run(
    config_path: Path,
    data_dir: Path,
    signal_dir: Path,
    timeout: int,
) -> int:
    config = load_config(config_path)
    base = config["base_url"]
    topic_keywords = config.get("topics", {})
    exclude_keywords = config.get("exclude_keywords", [])
    signal_thresholds = config.get("signal_thresholds", {})

    all_datasets: list[Dataset] = []

    for qdef in config.get("queries", []):
        params = urllib.parse.urlencode({
            "q": qdef["query"],
            "rows": qdef.get("rows", 100),
            "sort": qdef.get("sort", "metadata_modified desc"),
        })
        url = f"{base}/action/package_search?{params}"
        try:
            payload = fetch_json(url, timeout)
        except Exception as exc:
            print(f"Failed to query {qdef['query']}: {exc}", file=sys.stderr)
            continue

        datasets = parse_datasets(payload, topic_keywords, exclude_keywords)
        all_datasets.extend(datasets)

    # Dedup by ID (keep highest modified timestamp per dataset)
    deduped: dict[str, Dataset] = {}
    for ds in all_datasets:
        if ds.id not in deduped or ds.modified > deduped[ds.id].modified:
            deduped[ds.id] = ds

    datasets = list(deduped.values())

    if not datasets:
        print("No datasets found.", file=sys.stderr)
        return 1

    state = load_state()
    new, updated = detect_new_and_updated(datasets, state)

    # Only emit signals if thresholds are met
    new_to_report = new if signal_thresholds.get("new_dataset", True) else []
    updated_to_report = updated if signal_thresholds.get("updated_dataset", True) else []

    json_path, md_path = write_outputs(
        datasets, new_to_report, updated_to_report, config, data_dir, signal_dir
    )
    print(f"Wrote {json_path}", flush=True)
    print(f"Wrote {md_path}", flush=True)
    print(f"Total datasets: {len(datasets)}", flush=True)
    print(f"New: {len(new)}, Updated: {len(updated)}", flush=True)

    # Update state with ALL current fingerprints
    save_state(datasets)
    return 0


def main() -> int:
    parser = argparse.ArgumentParser(description="Poll IDB CKAN for Caribbean dataset signals.")
    parser.add_argument("--config", type=Path, default=DEFAULT_CONFIG)
    parser.add_argument("--data-dir", type=Path, default=DEFAULT_DATA_DIR)
    parser.add_argument("--signal-dir", type=Path, default=DEFAULT_SIGNAL_DIR)
    parser.add_argument("--timeout", type=int, default=30)
    args = parser.parse_args()
    return run(args.config, args.data_dir, args.signal_dir, args.timeout)


if __name__ == "__main__":
    raise SystemExit(main())
