#!/usr/bin/env python3
"""Check every configured news feed: reachable, parseable, and does it carry imagery?

Five publisher feeds were added from the publisher domains this desk already
surfaces, but their exact feed paths could not be confirmed from the sandbox
they were written in — outbound access to those hosts is blocked there. Run
this from anywhere with network to confirm them, or to find the ones that have
since moved:

    python3 scripts/check_news_feeds.py

Nothing is written. A feed that fails here also fails safely in the pipeline:
poll_feed logs it unreachable and returns no articles, so the cycle continues
on the feeds that do answer.
"""
from __future__ import annotations

import argparse
import sys
from concurrent.futures import ThreadPoolExecutor
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from watchers.regional_news_poller import fetch_feed, load_config, parse_rss  # noqa: E402


def check(feed: dict) -> dict:
    result = {"slug": feed.get("slug", "?"), "url": feed.get("url", ""),
              "unverified": bool(feed.get("unverified")), "kind": feed.get("kind", "")}
    try:
        items = parse_rss(fetch_feed(feed["url"]))
    except Exception as exc:
        result["error"] = f"{type(exc).__name__}: {exc}"
        return result
    result["items"] = len(items)
    result["with_image"] = sum(1 for i in items if i.get("image_url"))
    result["sample"] = next((i["image_url"] for i in items if i.get("image_url")), "")
    return result


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--workers", type=int, default=5)
    args = parser.parse_args()

    feeds = load_config().get("feeds", [])
    with ThreadPoolExecutor(max_workers=max(1, args.workers)) as pool:
        results = list(pool.map(check, feeds))

    dead, imageless = [], []
    print(f"{'feed':22} {'kind':11} {'items':>6} {'images':>7}  note")
    print("-" * 78)
    for r in results:
        if "error" in r:
            dead.append(r)
            note = r["error"][:34]
            print(f"{r['slug']:22} {r['kind']:11} {'—':>6} {'—':>7}  UNREACHABLE {note}")
            continue
        if r["items"] and not r["with_image"]:
            imageless.append(r)
        flag = "  <- was unverified" if r["unverified"] else ""
        print(f"{r['slug']:22} {r['kind']:11} {r['items']:>6} {r['with_image']:>7}{flag}")

    live = [r for r in results if "error" not in r]
    items = sum(r["items"] for r in live)
    images = sum(r["with_image"] for r in live)
    print("-" * 78)
    pct = f"{images / items * 100:.0f}%" if items else "n/a"
    print(f"{len(live)}/{len(results)} feeds answered · {items} items · {images} carry an image in the feed ({pct})")

    if dead:
        print("\nUnreachable — fix the URL in config/regional_news_sources.json or drop the entry:")
        for r in dead:
            print(f"  {r['slug']}: {r['url']}")
    if imageless:
        print("\nAnswered but carries no imagery (fine, just means the article page must be fetched):")
        for r in imageless:
            print(f"  {r['slug']}")
    print("\nRemove \"unverified\": true from any feed that answered above.")
    return 1 if dead else 0


if __name__ == "__main__":
    raise SystemExit(main())
