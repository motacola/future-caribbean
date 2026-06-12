# Hermes Brief — 6C Portal Probe Sweep (research only, NO code changes)

Goal: find the next live data sources. Guyana's eProcure ran a standard
platform (Frappe/doctracker) exposing a public JSON API at
`/api/method/doctracker.api.powerbi.get_public_bid_opportunities` — other
territories may run the same or similar stacks. Your job is reconnaissance
and a findings report. You change NO project files.

## Probe list

Procurement / tenders:
- Trinidad & Tobago: health.gov.tt tenders? finance.gov.tt? Look for the
  Office of Procurement Regulation (oprtt.org) and any e-tender portal.
- Barbados: gisbarbados / procurement portal (bidsandtenders? eProcure?)
- Bahamas: bonfirehub? eprocurement.gov.bs?
- Belize: any NPTAB-equivalent public notices page.
- OECS members (St Lucia, Grenada, SVG, Dominica, Antigua, St Kitts):
  national tender boards; also oecs.org pooled procurement.
- Suriname: nationale aanbestedingen / gov.sr notices.
- Jamaica re-check: GOJEP (www.gojep.gov.jm) — try RSS, print views,
  sitemap.xml, /epps JSON endpoints; it is ePPS (European Dynamics).

Macro / monetary (higher-frequency than World Bank annuals):
- Central banks: Bank of Jamaica (boj.org.jm), Central Bank of T&T,
  Central Bank of Barbados, ECCB (eccb-centralbank.org), Bank of Guyana —
  look for RSS feeds, statistics JSON/CSV endpoints, press-release feeds.

## Method per target

1. Plain HTTP GET with a browser User-Agent (stdlib urllib via python3 -
   you may write throwaway scripts under /tmp, never in the repo).
2. Note: status, server tech if visible, whether a public listing exists,
   whether it is static HTML / JSON API / JS-walled / session-gated.
3. For anything Frappe-like, try `/api/method/` endpoints analogous to
   Guyana's. For WordPress, try `/wp-json/wp/v2/posts?per_page=5`.
   For anything, try `/feed`, `/rss`, `/sitemap.xml`.
4. NEVER attempt auth bypass, form abuse, or anything beyond plain GETs
   of public pages.

## Deliverable — `planning/hermes-portal-probe-result.md` ONLY

A table: portal | URL probed | reachable | tech | best data endpoint |
stdlib-parseable? | recommendation (ADAPT NOW / POSSIBLE / DEAD END) —
followed by, for each ADAPT NOW: the exact endpoint, one sample record's
field names, and update frequency if visible. Honesty rule: report what
you actually observed; unreachable/blocked is a finding, not a failure.

Constraints: no git commit, no edits to any repo file except the result
file, no run_pipeline.sh, no server.py.
