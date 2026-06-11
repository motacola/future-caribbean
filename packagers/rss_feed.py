"""RSS feed — the desk as a wire service.

Writes outbox/feed.xml from the current cycle's dispatches. Titles and
descriptions use the shared natural-language layer; machine identifiers
travel in <guid> and <category> so agents lose nothing.
"""
from __future__ import annotations

import json
import sys
from datetime import datetime, timezone
from email.utils import format_datetime
from pathlib import Path
from xml.sax.saxutils import escape

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from humanizer import humanize  # noqa: E402

SITE = "https://signal-fabric.vercel.app"
MAX_ITEMS = 20


def main() -> None:
    src = ROOT / "outbox" / "opportunity_dispatches.json"
    if not src.exists():
        print("rss: no dispatches file, skipping")
        return
    data = json.loads(src.read_text())
    dispatches = data.get("dispatches", []) or []

    # One item per signal, highest confidence first
    seen: dict[str, dict] = {}
    for d in dispatches:
        sid = d.get("signal_id") or d.get("dispatch_id", "")
        cur = seen.get(sid)
        if cur is None or (d.get("confidence_score", 0) or 0) > (cur.get("confidence_score", 0) or 0):
            seen[sid] = d
    items = sorted(seen.values(), key=lambda d: -(d.get("confidence_score", 0) or 0))[:MAX_ITEMS]

    now = datetime.now(timezone.utc)
    out = ['<?xml version="1.0" encoding="UTF-8"?>']
    out.append('<rss version="2.0" xmlns:atom="http://www.w3.org/2005/Atom">')
    out.append("<channel>")
    out.append("<title>Caribbean Opportunity Dispatch — Live Wire</title>")
    out.append(f"<link>{SITE}/dashboard.html</link>")
    out.append("<description>Signals from the Caribbean's public data, in plain language. "
               "Machine-readable companion: /api/tools.json</description>")
    out.append("<language>en</language>")
    out.append(f"<lastBuildDate>{format_datetime(now)}</lastBuildDate>")
    out.append(f'<atom:link href="{SITE}/feed.xml" rel="self" type="application/rss+xml"/>')

    for d in items:
        title = humanize(d.get("title", "")) or "Caribbean signal"
        action = humanize(d.get("recommended_action", ""))
        why = humanize(d.get("routing_rationale", ""))
        desc_parts = [p for p in (action, why) if p]
        desc = " — ".join(desc_parts) if desc_parts else title
        country = d.get("country_cluster", "")
        kind = d.get("signal_kind", "")
        pub = d.get("generated_at", "")
        try:
            pub_dt = datetime.fromisoformat(pub.replace("Z", "+00:00"))
        except Exception:
            pub_dt = now
        out.append("<item>")
        out.append(f"<title>{escape(title)}</title>")
        out.append(f"<link>{SITE}/dashboard.html#decision-workspace</link>")
        out.append(f'<guid isPermaLink="false">{escape(d.get("dispatch_id", ""))}</guid>')
        out.append(f"<pubDate>{format_datetime(pub_dt)}</pubDate>")
        if country:
            out.append(f"<category>{escape(country)}</category>")
        if kind:
            out.append(f"<category>{escape(kind)}</category>")
        out.append(f"<description>{escape(desc[:500])}</description>")
        out.append("</item>")

    out.append("</channel>")
    out.append("</rss>")
    dest = ROOT / "outbox" / "feed.xml"
    dest.write_text("\n".join(out) + "\n", encoding="utf-8")
    print(f"rss: {len(items)} items -> {dest}")


if __name__ == "__main__":
    main()
