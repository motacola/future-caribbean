# Hermes Portal Probe — Reconnaissance Findings

**Date:** 2026-06-11  
**Method:** Plain HTTP GETs (stdlib `urllib`) with browser User-Agent  
**Total targets probed:** 25 portals across 69 endpoints

---

## Summary Table

| Portal | URL Probed | Reachable | Tech | Best Data Endpoint | stdlib-parseable? | Recommendation |
|--------|------------|-----------|------|-------------------|-------------------|----------------|
| **Procurement / Tenders** |
| Guyana eProcure (reference) | `https://eprocure.gov.gy/api/method/doctracker.api.powerbi.get_public_bid_opportunities` | ✅ 200 | nginx / Frappe | **`/api/method/doctracker.api.powerbi.get_public_bid_opportunities`** | ✅ JSON | **ADAPT NOW** |
| Barbados — GIS Barbados | `https://gisbarbados.gov.bb/wp-json/wp/v2/posts?per_page=5` | ✅ 200 | WordPress + Cloudflare | **`/wp-json/wp/v2/posts`** (WP REST API) | ✅ JSON | **ADAPT NOW** |
| Trinidad & Tobago — OPRTT | `https://oprtt.org/wp-json/wp/v2/posts?per_page=5` | ✅ 200 | WordPress + nginx | WP REST API exists but returns `[]` (empty) | ✅ JSON (empty) | **POSSIBLE** |
| Trinidad & Tobago — Finance | `https://finance.gov.tt/tenders` | ✅ 200 | WordPress + nginx | `/category/tender/` (HTML listing) + paginated WP JSON via `?rest_route=/wp/v2/posts&categories=<cat_id>` | ❌ HTML | **POSSIBLE** |
| Trinidad & Tobago — Health | `https://health.gov.tt/tenders` | ✅ 200 | WordPress (LiteSpeed) | `/tenders` (HTML listing) | ❌ HTML | **POSSIBLE** |
| St Lucia — Finance | `https://www.finance.gov.lc/tenders/index/1` (paginated) | ✅ 200 | Apache | **`/tenders/index/{page}`** (HTML, paginated tender index) | ❌ HTML | **POSSIBLE** |
| OECS — Pooled Procurement | `https://procurement.oecs.org` | ✅ 200 | European Dynamics (ePPS) | `/epps/common/viewOpenedTenders.do` (HTML) — no JSON API; Frappe endpoints return HTML | ❌ HTML | **POSSIBLE** |
| Suriname — Gov.sr | `https://gov.sr/aanbestedingen/` | ✅ 200 | WordPress + Cloudflare | `/aanbestedingen/` (HTML) + PDF notices | ❌ HTML/PDF | **POSSIBLE** |
| Bahamas — Bonfire | `https://bahamas.bonfirehub.com` | ✅ 200 | Bonfire + Cloudflare | `/api` returns 401; no public JSON | ❌ Auth-gated | **POSSIBLE** |
| Jamaica — GOJEP (ePPS) | `https://www.gojep.gov.jm` | ✅ 200 | European Dynamics (ePPS) | All `/api*`, `/rest*`, `*.json` endpoints return same HTML shell — no public JSON | ❌ JS-walled | **DEAD END** |
| Barbados — Bids&Tenders | `https://bidsandtenders.gov.bb`, `https://barbados.bidsandtenders.com` | ❌ DNS / SSL fail | — | — | — | **DEAD END** |
| Bahamas — eProcurement | `https://eprocurement.gov.bs` | ❌ DNS fail | — | — | — | **DEAD END** |
| Belize — NPTAB | `https://nptab.gov.bz`, `https://www.gov.bz/nptab` | ❌ DNS / 503 | — | — | — | **DEAD END** |
| Grenada | `https://www.gov.gd/tenders` | ❌ 404 | Cloudflare | — | — | **DEAD END** |
| St Vincent & Grenadines | `https://www.gov.vc/tenders` | ❌ 404 | Apache | — | — | **DEAD END** |
| Dominica | `https://www.dominica.gov.dm/tenders` | ❌ 404 | Apache | — | — | **DEAD END** |
| Antigua & Barbuda | `https://www.ab.gov.ag/tenders` | ❌ 404 | IIS | — | — | **DEAD END** |
| St Kitts & Nevis | `https://www.gov.kn/tenders` | ❌ 404 | Sucuri/Cloudproxy | — | — | **DEAD END** |
| **Central Banks / Macro** |
| Bank of Jamaica | `https://www.boj.org.jm/feed` | ✅ 200 | WordPress | **`/feed`** (RSS 2.0, 10 items) | ✅ XML (stdlib parseable) | **ADAPT NOW** |
| Central Bank of T&T | `https://www.central-bank.org.tt/rss` | ✅ 200 | WordPress (LiteSpeed) | **`/rss`** (RSS 2.0, 10 items) | ✅ XML (stdlib parseable) | **ADAPT NOW** |
| ECCB | `https://www.eccb-centralbank.org/sitemap.xml` | ✅ 200 | nginx | `/sitemap.xml` (72KB, XML) + `/statistics` (HTML) | ⚠️ XML (no `<url>` entries found) | **POSSIBLE** |
| Central Bank of Barbados | `https://www.centralbank.org.bb` | ✅ 200 (home only) | nginx | Homepage only; `/rss`, `/statistics`, `/data` all 404 | ❌ | **POSSIBLE** |
| Bank of Guyana | `https://www.bankofguyana.org.gy` | ✅ 200 (home only) | Apache | Homepage only; `/rss`, `/statistics` 404 | ❌ | **POSSIBLE** |

---

## ADAPT NOW — Detailed Findings

### 1. Guyana eProcure (Reference Implementation)
- **Endpoint:** `https://eprocure.gov.gy/api/method/doctracker.api.powerbi.get_public_bid_opportunities`
- **Method:** GET, no auth
- **Response:** JSON `{"message": [...]}`
- **Record count:** 22 (observed)
- **Sample record fields:**
  ```
  project_id, project_name, agency, agency_logo, procurement_method,
  procurement_nature, procurement_sub_nature, estimated_value, current_state,
  advertisement_date, actual_bid_opening_date, projected_bid_opening_date,
  regions, advertisement_documents
  ```
- **Update frequency:** Not explicitly stated; `advertisement_date` values span recent months (Feb 2026 observed) — appears updated as tenders are published.
- **Notes:** Frappe/doctracker stack. This is the exact pattern to hunt for in other territories.

---

### 2. Barbados — GIS Barbados (WordPress REST API)
- **Endpoint:** `https://gisbarbados.gov.bb/wp-json/wp/v2/posts?per_page=5&categories=<tender_cat_id>`
- **Method:** GET, no auth
- **Response:** JSON array of posts
- **Sample record fields (full WP post object):**
  ```
  id, date, date_gmt, guid, modified, modified_gmt, slug, status, type,
  link, title, content, excerpt, author, featured_media, comment_status,
  ping_status, sticky, template, format, meta, categories, tags, _links
  ```
- **Update frequency:** Posts dated daily/weekly; `modified_gmt` shows last edit.
- **Notes:** Need to discover the tender category ID (inspect `/wp-json/wp/v2/categories` or HTML). Cloudflare present but API accessible.

---

### 3. Bank of Jamaica — RSS Feed
- **Endpoint:** `https://www.boj.org.jm/feed`
- **Method:** GET
- **Response:** RSS 2.0 (XML)
- **Items:** 10 most recent
- **Item fields:** `<title>`, `<link>`, `<pubDate>`, `<category>`, `<guid>`, `<description>` (HTML), `<dc:creator>`
- **Update frequency:** New items appear daily/weekly (latest observed: 2026-06-11)
- **Notes:** Covers notices, speeches, statistics releases. Parse with `xml.etree.ElementTree` (stdlib).

---

### 4. Central Bank of Trinidad & Tobago — RSS Feed
- **Endpoint:** `https://www.central-bank.org.tt/rss`
- **Method:** GET
- **Response:** RSS 2.0 (XML)
- **Items:** 10 most recent
- **Item fields:** `<title>`, `<link>`, `<pubDate>`, `<guid>`, `<description>` (HTML), `<comments>`
- **Update frequency:** Weekly/bi-weekly (latest observed: mid-2026)
- **Notes:** Covers policy decisions, payment provider authorisations, statistical releases. Stdlib XML parseable.

---

## POSSIBLE — Require HTML Scraping or Discovery

| Portal | Why | Next Step |
|--------|-----|-----------|
| **Trinidad OPRTT** | WP REST API exists but empty (`[]`). Tender content may be in a custom post type or category not exposed by default. | Probe `/wp-json/wp/v2/types`, `/wp-json/wp/v2/categories`, search for `tender`/`procurement` post type. |
| **Trinidad Finance** | `/category/tender/` lists tenders (oldest 2012). WP JSON can filter by category once cat ID known. | Get category ID from `/wp-json/wp/v2/categories?search=tender`, then query posts. |
| **Trinidad Health** | `/tenders` page lists RFPs. WP JSON likely similar to Finance. | Same approach as Finance. |
| **St Lucia** | Paginated `/tenders/index/{page}` returns HTML with tender links (15–27 per page). No JSON API detected. | Scrape paginated index; each tender links to detail page. Apache server, simple HTML. |
| **OECS Pooled** | ePPS (European Dynamics) at `/epps/common/viewOpenedTenders.do`. All `/api*` endpoints return HTML shell. | Check if `epps` has JSON export (some ePPS deployments expose `/api/v1/tenders.json` with auth). |
| **Suriname** | `/aanbestedingen/` page lists notices + PDF scans. WordPress backend. | Scrape notice list; PDFs require `pdfminer`/`pymupdf` for text extraction. |
| **Bahamas Bonfire** | Bonfire platform; `/api` returns 401. Public project listings may exist at `/projects` HTML. | Explore public project listing pages; Bonfire sometimes has unauthenticated `/opportunities` view. |
| **ECCB** | `/statistics` page (HTML tables). `/sitemap.xml` exists but no `<url>` entries found (may be index). | Parse statistics HTML tables; check `/sitemap.xml` for subsitemaps. |
| **Central Bank Barbados** | Only homepage reaches; subpaths 404. May have different URL structure. | Crawl homepage for links to statistics/publications. |
| **Bank of Guyana** | Only homepage reaches. Statistics likely in PDF reports. | Crawl for "Statistics" or "Reports" links; expect PDFs. |

---

## DEAD END — Unreachable or No Public Data

| Portal | Failure Mode |
|--------|--------------|
| Barbados Bids&Tenders | Both `bidsandtenders.gov.bb` (DNS) and `barbados.bidsandtenders.com` (SSL handshake fail) unreachable |
| Bahamas eProcurement | `eprocurement.gov.bs` DNS fails — domain may not exist |
| Belize NPTAB | `nptab.gov.bz` DNS fails; `gov.bz` subpaths return 503 |
| Grenada / St Vincent / Dominica / Antigua / St Kitts | `/tenders` paths return 404 on all; no procurement subdomain detected |
| Jamaica GOJEP | All API-like endpoints (`/api/*`, `/rest/*`, `*.json`) return identical HTML shell — SPA walled garden |

---

## Recommendations for Pipeline Integration

1. **Immediate adapters (this sprint):**
   - Guyana eProcure → JSON adapter (already proven in Abeng)
   - Barbados GIS → WP REST API adapter (parameterise category ID)
   - Bank of Jamaica → RSS adapter
   - Central Bank T&T → RSS adapter

2. **Next sprint (HTML scrapers):**
   - St Lucia paginated tender index (Apache, clean HTML)
   - Trinidad Finance/Health (WP category feeds once cat IDs known)
   - Suriname aanbestedingen (WP + PDF)
   - OECS ePPS — investigate `/epps/common/viewOpenedTenders.do` for export links

3. **Park / revisit:**
   - OPRTT WP custom post type discovery
   - Bahamas Bonfire public views
   - ECCB statistics tables
   - Central Bank Barbados / Bank of Guyana — crawl for report links

4. **Write off (for now):**
   - All DEAD END entries — no public signal without auth or domain change.

---

## Raw Probe Data

Full JSON log saved to `/tmp/hermes_portal_probe_raw.json` (69 probe records with headers, status codes, content-type, body sizes).