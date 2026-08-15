"""Opportunity Validation Pack generator.

Turns each lead signal from "worth investigating" into a pre-assembled
diligence pack: sector hypotheses, supporting projects, procurement
matches, relevant institutions, intro targets, and an explicit
advance/hold/reject recommendation with reasons.

Outputs:
    outbox/validation_packs/<signal_id>.json
    outbox/validation_packs/<signal_id>.md
    outbox/validation_packs/index.json
"""
from __future__ import annotations

import hashlib
import json
import re
from datetime import datetime, timezone
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
OUT_DIR = ROOT / "outbox" / "validation_packs"
STATE_FILE = ROOT / "data" / "validation_packs" / "state.json"
REGISTRY_DIR = ROOT / "data" / "registries"

MAX_PACKS = 5
MAX_MATCHES = 6
FRESHNESS_STALE_CYCLES = 2
STOPWORDS = frozenset({"from", "with", "and", "the", "that", "serving", "local", "sector"})
SHORT_SECTOR_TOKENS = frozenset({"oil", "gas", "bpo", "fdi", "gdp"})

REGISTRY_SLUGS = {
    "Guyana": "guyana",
    "Belize": "belize",
    "Jamaica": "jamaica",
    "Barbados": "barbados",
    "Trinidad and Tobago": "trinidad-and-tobago",
    "St. Vincent and the Grenadines": "st-vincent-and-the-grenadines",
}

# ── Curated reference registry ──────────────────────────────
# Stable, well-known public institutions only. Entries are surfaced as
# intro targets, never presented as validated deal partners.
INSTITUTIONS = {
    "Guyana": [
        {"name": "Guyana Office for Investment (GO-Invest)", "role": "National investment promotion agency"},
        {"name": "Private Sector Commission of Guyana", "role": "Knows the private sector — ask who's really operating"},
    ],
    "Jamaica": [
        {"name": "JAMPRO (Jamaica Promotions Corporation)", "role": "National investment and export promotion agency"},
    ],
    "Trinidad and Tobago": [
        {"name": "InvesTT", "role": "National investment promotion agency"},
    ],
    "Barbados": [
        {"name": "Invest Barbados", "role": "National investment promotion agency"},
    ],
    "Belize": [
        {"name": "BELTRAIDE (Belize Trade and Investment Development Service)", "role": "National trade and investment promotion agency"},
    ],
    "Bahamas": [
        {"name": "Bahamas Investment Authority", "role": "National investment facilitation agency"},
    ],
    "Dominica": [
        {"name": "Invest Dominica Authority", "role": "National investment promotion agency"},
    ],
    "Grenada": [
        {"name": "Grenada Investment Development Corporation", "role": "National investment promotion agency"},
    ],
    "Saint Lucia": [
        {"name": "Invest Saint Lucia", "role": "National investment promotion agency"},
    ],
    "St. Vincent and the Grenadines": [
        {"name": "Invest SVG", "role": "National investment promotion agency"},
    ],
    "St. Kitts and Nevis": [
        {"name": "St. Kitts Investment Promotion Agency", "role": "National investment promotion agency"},
    ],
    "Antigua and Barbuda": [
        {"name": "Antigua and Barbuda Investment Authority", "role": "National investment promotion agency"},
    ],
    "Haiti": [
        {"name": "Centre de Facilitation des Investissements (CFI)", "role": "National investment facilitation centre"},
    ],
    "Suriname": [
        {"name": "Chamber of Commerce and Industry Suriname (KKF)", "role": "The national chamber — a shortcut to who's doing business"},
    ],
}

REGIONAL_INSTITUTIONS = [
    {"name": "Caribbean Export Development Agency", "role": "Regional trade and investment promotion"},
    {"name": "Caribbean Development Bank (CDB)", "role": "Regional development finance and procurement"},
]

# Analyst priors: widely reported sector drivers per country. Always
# flagged as hypotheses requiring local confirmation, never as findings.
SECTOR_PRIORS = {
    "Guyana": ["Oil & gas and offshore support services", "Construction and infrastructure", "Logistics serving the energy supply chain", "Agriculture and agro-processing"],
    "Suriname": ["Offshore oil & gas exploration", "Gold mining and extractives services"],
    "Belize": ["Tourism and hospitality", "Agribusiness and agro-exports", "Business process outsourcing"],
    "Jamaica": ["Tourism and hospitality", "Logistics and BPO", "Mining (bauxite/alumina)"],
    "Barbados": ["Tourism and hospitality", "International business and financial services"],
    "Trinidad and Tobago": ["Energy and petrochemicals", "Manufacturing and regional exports"],
    "Bahamas": ["Tourism and hospitality", "Financial services"],
}

# ── Helpers ─────────────────────────────────────────────────

def read_json(path: Path) -> dict | None:
    if not path.exists():
        return None
    try:
        return json.loads(path.read_text())
    except Exception:
        return None


def _norm(text: str) -> str:
    return re.sub(r"[^a-z0-9 ]", " ", (text or "").lower())


COUNTRY_ALIASES = {
    "St. Vincent and the Grenadines": ["st vincent", "saint vincent"],
    "St. Kitts and Nevis": ["st kitts", "saint kitts"],
    "Saint Lucia": ["st lucia", "saint lucia"],
    "Trinidad and Tobago": ["trinidad"],
    "Antigua and Barbuda": ["antigua"],
}


def mentions_country(text: str, country: str) -> bool:
    blob = _norm(text)
    needles = [_norm(country)] + [_norm(a) for a in COUNTRY_ALIASES.get(country, [])]
    return any(n and n in blob for n in needles)


# ── Evidence extraction per country ─────────────────────────

def wb_observations_for(country: str, wb: dict) -> list[dict]:
    out = []
    for o in (wb or {}).get("observations", []) or []:
        if _norm(o.get("country_name", "")) == _norm(country) or mentions_country(o.get("country_name", ""), country):
            out.append(o)
    return out


def registry_slug(country: str) -> str:
    if country in REGISTRY_SLUGS:
        return REGISTRY_SLUGS[country]
    return re.sub(r"[^a-z0-9]+", "-", country.lower()).strip("-")


def load_operators_from_registry(country: str) -> list[dict]:
    path = REGISTRY_DIR / f"{registry_slug(country)}.json"
    if not path.exists():
        return []
    try:
        payload = json.loads(path.read_text(encoding="utf-8"))
    except Exception:
        return []
    out = []
    for op in payload.get("operators", []) or []:
        if not op.get("name"):
            continue
        out.append({
            "name": op["name"],
            "sector": op.get("sector", ""),
            "role": op.get("role", ""),
            "source_url": op.get("source_url", ""),
            "verified_by": op.get("verified_by", "registry"),
        })
    return out[:MAX_MATCHES]


def _sector_tokens(sector: str) -> list[str]:
    words = re.findall(r"[a-z]{3,}", _norm(sector))
    return [
        w for w in words
        if w not in STOPWORDS and (len(w) >= 4 or w in SHORT_SECTOR_TOKENS)
    ]


def corroborate_sector_hypotheses(
    hyps: list[dict], articles: list[dict], country: str,
) -> list[dict]:
    """Upgrade unconfirmed hypotheses when regional news cites the sector."""
    country_articles = [
        a for a in articles
        if country in (a.get("countries") or [])
        or mentions_country(f"{a.get('title', '')} {a.get('summary', '')}", country)
    ]
    out: list[dict] = []
    for hyp in hyps:
        if hyp.get("status") != "unconfirmed" or not country_articles:
            out.append(hyp)
            continue
        tokens = _sector_tokens(hyp.get("sector", ""))
        matched = None
        for art in country_articles:
            blob = _norm(f"{art.get('title', '')} {art.get('summary', '')}")
            hits = sum(1 for t in tokens if t in blob)
            if hits >= 2 or (hits >= 1 and len(tokens) <= 2):
                matched = art
                break
        if matched:
            out.append({
                **hyp,
                "status": "corroborated",
                "basis": f"{matched.get('source', 'Regional news')}: {matched.get('title', '')}",
                "url": matched.get("url", ""),
            })
        else:
            out.append(hyp)
    return out


def evidence_fingerprint(pack: dict) -> str:
    parts: list[str] = []
    for h in pack.get("sector_hypotheses", []):
        if h.get("status") == "corroborated":
            parts.append(f"h:{h.get('url') or h.get('sector')}")
    for p in pack.get("procurement_matches", []):
        if p.get("match") == "country":
            parts.append(f"p:{p.get('title')}:{p.get('closing_date')}")
    for o in pack.get("credible_local_operators", []):
        parts.append(f"o:{o.get('name')}")
    digest = hashlib.sha256("|".join(sorted(parts)).encode()).hexdigest()[:16]
    return digest or "empty"


def load_pack_state() -> dict:
    if not STATE_FILE.exists():
        return {"signals": {}}
    try:
        return json.loads(STATE_FILE.read_text(encoding="utf-8"))
    except Exception:
        return {"signals": {}}


def save_pack_state(state: dict) -> None:
    STATE_FILE.parent.mkdir(parents=True, exist_ok=True)
    STATE_FILE.write_text(json.dumps(state, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")


def apply_freshness_decay(
    pack: dict, previous: dict | None, now_iso: str,
) -> dict:
    """Downgrade advance → hold when evidence has not refreshed for N cycles."""
    fp = evidence_fingerprint(pack)
    prev_fp = (previous or {}).get("evidence_fingerprint", "")
    stale_cycles = int((previous or {}).get("stale_cycles", 0))
    if prev_fp and fp == prev_fp:
        stale_cycles += 1
    else:
        stale_cycles = 0

    decision = pack["advance_or_reject_recommendation"]
    reason = pack["recommendation_reason"]
    if decision == "advance" and stale_cycles >= FRESHNESS_STALE_CYCLES:
        decision = "hold"
        reason = (
            f"Evidence fingerprint unchanged for {stale_cycles} cycles — "
            "downgraded from advance to hold until new corroboration arrives."
        )

    pack = {
        **pack,
        "advance_or_reject_recommendation": decision,
        "recommendation_reason": reason,
        "evidence_fingerprint": fp,
        "cycles_since_refresh": stale_cycles,
        "evidence_freshness": "stale" if stale_cycles >= FRESHNESS_STALE_CYCLES else (
            "refreshing" if stale_cycles == 0 else "aging"
        ),
        "last_validated_at": now_iso,
    }
    return pack


def calibrate_confidence(
    confidence: int,
    hyps: list[dict],
    procurement: list[dict],
    wb_obs: list[dict],
) -> tuple[int, str]:
    """Separate raw signal strength from action readiness."""
    effective = confidence
    notes: list[str] = []
    has_corroborated = any(h.get("status") == "corroborated" for h in hyps)
    has_data = any(h.get("status") == "data_available" for h in hyps)
    dated_country_tender = any(
        p.get("match") == "country" and p.get("closing_date") for p in procurement
    )
    macro_only = bool(wb_obs) and not has_corroborated and not dated_country_tender

    if macro_only and not has_data:
        effective = min(effective, 68)
        notes.append("annual macro signal only")
    elif not has_corroborated and not dated_country_tender:
        effective = min(effective, 78)
        notes.append("no dated country procurement or news corroboration")

    readiness = "high" if effective >= 80 and (has_corroborated or dated_country_tender) else (
        "medium" if effective >= 60 else "low"
    )
    return effective, readiness + (f" ({'; '.join(notes)})" if notes else "")


def sector_hypotheses_for(country: str, tier2_items: list[dict], wb_obs: list[dict]) -> list[dict]:
    """Each hypothesis carries an explicit basis so nothing reads as a finding."""
    hyps: list[dict] = []
    for sector in SECTOR_PRIORS.get(country, []):
        hyps.append({
            "sector": sector,
            "basis": "Analyst prior from widely reported sector drivers — requires local confirmation",
            "status": "unconfirmed",
        })
    # Point at the country's own industry-breakdown data when it exists.
    for item in tier2_items:
        title = item.get("title", "")
        if mentions_country(title, country) and re.search(r"gdp by industr|value added", title, re.I):
            hyps.append({
                "sector": "Sector mix verifiable from official GDP-by-industry data",
                "basis": f"{item.get('source', 'CARICOM Statistics')}: {title}",
                "status": "data_available",
                "url": item.get("url", ""),
            })
    fdi = [o for o in wb_obs if o.get("indicator_code") == "BX.KLT.DINV.CD.WD"]
    for o in fdi:
        hyps.append({
            "sector": "FDI-receiving sectors (composition not yet broken down)",
            "basis": f"World Bank: FDI net inflows moved {o.get('delta_pct', 0):+.1f}% from {o.get('previous_year')} to {o.get('year')}",
            "status": "macro_signal",
        })
    return hyps


def supporting_projects_for(country: str, idb: dict, tier2_items: list[dict]) -> list[dict]:
    out = []
    for ds in (idb or {}).get("datasets", []) or []:
        text = f"{ds.get('title', '')} {ds.get('description', '')}"
        if mentions_country(text, country):
            out.append({
                "title": ds.get("title", ""),
                "source": "IDB Open Data",
                "url": ds.get("url", ""),
                "topics": ds.get("topics", []),
            })
    for item in tier2_items:
        if item.get("item_type") not in ("news", "publications"):
            continue
        text = f"{item.get('title', '')} {item.get('description', '')}"
        if mentions_country(text, country):
            out.append({
                "title": item.get("title", ""),
                "source": item.get("source", ""),
                "url": item.get("url", ""),
                "topics": [],
            })
    return out[:MAX_MATCHES]


def procurement_matches_for(country: str, tier2_items: list[dict],
                            tenders: list[dict] | None = None) -> list[dict]:
    direct, regional = [], []
    # Live national-portal tenders rank first — dated, country-specific.
    for t in tenders or []:
        if _norm(t.get("country", "")) == _norm(country) or mentions_country(t.get("country", ""), country):
            direct.append({
                "title": t.get("title", ""),
                "source": t.get("source", ""),
                "url": t.get("url", ""),
                "match": "country",
                "closing_date": t.get("closing_date"),
            })
    for item in tier2_items:
        if item.get("item_type") != "procurement":
            continue
        row = {
            "title": item.get("title", ""),
            "source": item.get("source", ""),
            "url": item.get("url", ""),
        }
        text = f"{item.get('title', '')} {item.get('description', '')}"
        if mentions_country(text, country):
            row["match"] = "country"
            direct.append(row)
        else:
            row["match"] = "regional"
            regional.append(row)
    return (direct + regional)[:MAX_MATCHES]


def country_data_for(country: str, tier2_items: list[dict]) -> list[dict]:
    out = []
    for item in tier2_items:
        if item.get("item_type") != "country_data":
            continue
        if mentions_country(item.get("title", ""), country):
            out.append({
                "title": item.get("title", ""),
                "source": item.get("source", ""),
                "url": item.get("url", ""),
            })
    return out[:MAX_MATCHES]


# ── Recommendation logic ────────────────────────────────────

def recommend(confidence: int, hyps: list[dict], projects: list[dict],
              procurement: list[dict], operators: list[dict]) -> tuple[str, str]:
    evidence_categories = sum([
        bool([h for h in hyps if h.get("status") in ("data_available", "corroborated")]),
        bool(projects),
        bool([p for p in procurement if p.get("match") == "country"]),
        bool(operators),
    ])
    dated_tender = any(p.get("match") == "country" and p.get("closing_date") for p in procurement)
    if confidence >= 80 and evidence_categories >= 2 and (dated_tender or any(
        h.get("status") == "corroborated" for h in hyps
    )):
        return ("advance", (
            f"Calibrated confidence {confidence}/100 with {evidence_categories} evidence categories "
            "including dated procurement or corroborated sector news. Worth one validation conversation."
        ))
    if confidence >= 80 and evidence_categories >= 2:
        return ("hold", (
            f"Calibrated confidence {confidence}/100 with {evidence_categories} evidence categories, "
            "but no dated country tender or corroborated sector article yet — advance after confirmation."
        ))
    if confidence >= 60 or evidence_categories >= 1:
        return ("hold", (
            f"Calibrated confidence {confidence}/100 with {evidence_categories} evidence categories. "
            "Keep on the desk; advance only after the unresolved questions below are answered."
        ))
    return ("reject", (
        f"Calibrated confidence {confidence}/100 with no corroborating evidence categories. "
        "Park unless new corroborating data arrives next cycle."
    ))


def unresolved_questions_for(country: str, hyps: list[dict], procurement: list[dict],
                             operators: list[dict]) -> list[str]:
    qs = []
    if not [h for h in hyps if h.get("status") == "data_available"]:
        qs.append(f"Which specific sectors are driving the movement in {country}? No official sector-breakdown dataset matched this cycle.")
    else:
        qs.append(f"Confirm which sectors in the official {country} GDP-by-industry data actually align with the FDI movement.")
    dated = [p for p in procurement if p.get("match") == "country" and p.get("closing_date")]
    if dated:
        qs.append(f"Tender closes {dated[0]['closing_date']} — confirm eligibility and bid requirements early.")
    elif not [p for p in procurement if p.get("match") == "country"]:
        qs.append(f"No live {country}-specific procurement notice matched this cycle — check CDB and national tender portals directly.")
    if not operators:
        qs.append(
            "No registry-backed local operators matched — source two credible operators "
            "via the listed institutions."
        )
    else:
        qs.append(
            f"Validate fit with registry-listed operators ({operators[0]['name']}"
            f"{', ' + operators[1]['name'] if len(operators) > 1 else ''}) before outreach."
        )
    qs.append("Validate that the underlying FDI movement is sustained, not a one-off transaction or statistical revision.")
    return qs


# ── Pack assembly ───────────────────────────────────────────

def build_pack(
    dispatch: dict,
    wb: dict,
    idb: dict,
    tier2: dict,
    now_iso: str,
    tenders: list[dict] | None = None,
    news_articles: list[dict] | None = None,
    previous_state: dict | None = None,
    coordination_opportunities: list[dict] | None = None,
) -> dict:
    country = dispatch.get("country_cluster", "Caribbean")
    tier2_items = (tier2 or {}).get("items", []) or []
    wb_obs = wb_observations_for(country, wb)

    hyps = sector_hypotheses_for(country, tier2_items, wb_obs)
    hyps = corroborate_sector_hypotheses(hyps, news_articles or [], country)
    projects = supporting_projects_for(country, idb, tier2_items)
    procurement = procurement_matches_for(country, tier2_items, tenders)
    cdata = country_data_for(country, tier2_items)
    institutions = INSTITUTIONS.get(country, []) + REGIONAL_INSTITUTIONS
    operators = load_operators_from_registry(country)

    # Action-readiness calibration starts from the bounded score published to
    # readers. Preserve the ranking score separately: after raw-score ranking
    # was introduced it can exceed 100, and calling the already-clamped display
    # score "raw" made the validation pack misstate what the algorithm used.
    published_confidence = int(dispatch.get("confidence_score", 0) or 0)
    ranking_confidence = int(dispatch.get("confidence_raw", published_confidence) or 0)
    confidence, action_readiness = calibrate_confidence(
        published_confidence, hyps, procurement, wb_obs
    )
    decision, reason = recommend(confidence, hyps, projects, procurement, operators)
    questions = unresolved_questions_for(country, hyps, procurement, operators)

    source_links = sorted({
        row.get("url", "")
        for row in projects + procurement + cdata + [h for h in hyps if h.get("url")]
        if row.get("url")
    })

    intro_targets = [
        {"name": i["name"], "why": i["role"]}
        for i in INSTITUTIONS.get(country, [])
    ] or [{"name": REGIONAL_INSTITUTIONS[0]["name"], "why": REGIONAL_INSTITUTIONS[0]["role"]}]

    pack = {
        "signal_id": dispatch.get("signal_id", ""),
        "dispatch_id": dispatch.get("dispatch_id", ""),
        "country": country,
        "signal_title": dispatch.get("title", ""),
        "confidence_score": confidence,
        "raw_confidence_score": ranking_confidence,
        "action_readiness": action_readiness,
        "evidence_grade": dispatch.get("evidence_grade", ""),
        "sector_hypotheses": hyps,
        "supporting_projects": projects,
        "procurement_matches": procurement,
        "official_country_data": cdata,
        "credible_local_operators": operators,
        "relevant_institutions": institutions,
        "source_links": source_links,
        "unresolved_questions": questions,
        "recommended_intro_targets": intro_targets,
        "advance_or_reject_recommendation": decision,
        "recommendation_reason": reason,
        "last_validated_at": now_iso,
    }
    # Deterministic coordination-path enrichment: attach the best-matching
    # coordination opportunity for this dispatch (by trigger_signal_id, then
    # by demand country, then the single highest-scoring candidate).
    pack["coordination_path"] = _match_coordination_path(
        dispatch, coordination_opportunities or []
    )
    return apply_freshness_decay(pack, previous_state, now_iso)


def _match_coordination_path(
    dispatch: dict, opportunities: list[dict]
) -> dict | None:
    """Return the coordination_path block for the best-matching opportunity, or None."""
    if not opportunities:
        return None
    sid = dispatch.get("signal_id") or dispatch.get("dispatch_id", "")
    country = dispatch.get("country_cluster", "")
    by_signal = next(
        (o for o in opportunities if o.get("trigger_signal_id") == sid), None
    )
    by_country = next(
        (o for o in opportunities if country and country in (o.get("demand_countries") or [])),
        None,
    )
    best = by_signal or by_country or max(
        opportunities, key=lambda o: (o.get("coordination_score", 0) or 0)
    )
    return {
        "coordination_score": best.get("coordination_score"),
        "demand_countries": best.get("demand_countries", []),
        "minimum_next_action": best.get("minimum_next_action", ""),
        "contributing_nodes": best.get("contributing_nodes", []),
        "matched_capabilities": best.get("matched_capabilities", []),
    }


def render_md(pack: dict) -> str:
    lines = [
        f"# Opportunity Validation Pack \u2014 {pack['country']}",
        "",
        f"- Signal: `{pack['signal_id']}` \u00b7 Dispatch: `{pack['dispatch_id']}`",
        f"- Confidence: {pack['confidence_score']}/100 (raw {pack.get('raw_confidence_score', pack['confidence_score'])}) \u00b7 {pack['evidence_grade']}",
        f"- Action readiness: {pack.get('action_readiness', 'n/a')}",
        f"- Evidence freshness: {pack.get('evidence_freshness', 'n/a')} \u00b7 cycles since refresh: {pack.get('cycles_since_refresh', 0)}",
        f"- Recommendation: **{pack['advance_or_reject_recommendation'].upper()}** \u2014 {pack['recommendation_reason']}",
        f"- Last validated: {pack['last_validated_at']}",
        "",
        "## Sector hypotheses",
    ]
    for h in pack["sector_hypotheses"] or [{"sector": "None identified this cycle", "basis": ""}]:
        basis = f" \u2014 _{h['basis']}_" if h.get("basis") else ""
        status = f" [{h['status']}]" if h.get("status") else ""
        lines.append(f"- {h['sector']}{status}{basis}")
    lines += ["", "## Credible local operators (registry-backed)"]
    for o in pack.get("credible_local_operators") or []:
        url = o.get("source_url", "")
        link = f" ([profile]({url}))" if url else ""
        lines.append(f"- {o['name']} \u2014 {o.get('role', '')}{link}")
    if not pack.get("credible_local_operators"):
        lines.append("- No registry-backed operators for this country yet.")
    lines += ["", "## Supporting projects & publications"]
    for pr in pack["supporting_projects"] or []:
        lines.append(f"- [{pr['title']}]({pr['url']}) \u2014 {pr['source']}")
    if not pack["supporting_projects"]:
        lines.append("- No matched projects this cycle.")
    lines += ["", "## Procurement matches"]
    for pr in pack["procurement_matches"] or []:
        lines.append(f"- [{pr['title']}]({pr['url']}) \u2014 {pr['source']} ({pr['match']})")
    if not pack["procurement_matches"]:
        lines.append("- No live procurement notices matched.")
    lines += ["", "## Official country data"]
    for d in pack["official_country_data"] or []:
        lines.append(f"- [{d['title']}]({d['url']}) \u2014 {d['source']}")
    if not pack["official_country_data"]:
        lines.append("- No official country datasets matched.")
    lines += ["", "## Relevant institutions & intro targets"]
    for i in pack["relevant_institutions"]:
        lines.append(f"- {i['name']} \u2014 {i['role']}")
    lines += ["", "## Unresolved questions"]
    for q in pack["unresolved_questions"]:
        lines.append(f"- {q}")
    cp = pack.get("coordination_path")
    if cp:
        lines += ["", "## Regional coordination path"]
        score = cp.get("coordination_score")
        if score is not None:
            lines.append(f"- Coordination score: {score}/100")
        demand = cp.get("demand_countries") or []
        if demand:
            lines.append("- Demand countries: " + ", ".join(demand))
        nodes = cp.get("contributing_nodes") or []
        if nodes:
            lines.append("- Contributing nodes:")
            for n in nodes:
                caps = ", ".join(c.get("id", "") for c in (n.get("matched_capabilities") or []))
                line = "  - " + str(n.get("country", n.get("node", "")))
                if caps:
                    line += f" ({caps})"
                lines.append(line)
        action = cp.get("minimum_next_action")
        if action:
            lines.append(f"- Minimum next action: {action}")
    lines += [
        "",
        "> Screening support, not investment advice. Institutions listed are public bodies",
        "> suggested as first conversations; no operator or partner has been validated.",
        "",
    ]
    return "\n".join(lines)
def select_lead_dispatches(dispatches: list[dict]) -> list[dict]:
    """One dispatch per signal_id, highest confidence first."""
    by_signal: dict[str, dict] = {}
    for d in dispatches:
        sid = d.get("signal_id") or d.get("dispatch_id", "")
        if not sid:
            continue
        cur = by_signal.get(sid)
        if cur is None or (d.get("confidence_score", 0) or 0) > (cur.get("confidence_score", 0) or 0):
            by_signal[sid] = d
    ranked = sorted(by_signal.values(), key=lambda d: -(d.get("confidence_score", 0) or 0))
    return ranked[:MAX_PACKS]


def main() -> None:
    dispatch_data = read_json(ROOT / "outbox" / "opportunity_dispatches.json") or {}
    dispatches = dispatch_data.get("dispatches", []) or []
    wb = read_json(ROOT / "data" / "world_bank" / "latest.json") or {}
    idb = read_json(ROOT / "data" / "idb" / "latest.json") or {}
    tier2 = read_json(ROOT / "data" / "tier2" / "latest.json") or {}
    tenders = (read_json(ROOT / "data" / "tenders" / "latest.json") or {}).get("items", [])
    news = (read_json(ROOT / "data" / "regional_news" / "latest.json") or {}).get("items", [])
    pack_state = load_pack_state()
    signals_state = pack_state.setdefault("signals", {})

    OUT_DIR.mkdir(parents=True, exist_ok=True)
    now_iso = datetime.now(timezone.utc).isoformat()

    index = []
    for dispatch in select_lead_dispatches(dispatches):
        sid = dispatch.get("signal_id") or dispatch.get("dispatch_id", "")
        previous = signals_state.get(sid)
        pack = build_pack(
            dispatch, wb, idb, tier2, now_iso, tenders, news, previous,
        )
        signals_state[sid] = {
            "evidence_fingerprint": pack.get("evidence_fingerprint"),
            "stale_cycles": pack.get("cycles_since_refresh", 0),
            "last_validated_at": now_iso,
            "recommendation": pack["advance_or_reject_recommendation"],
        }
        sid = pack["signal_id"] or pack["dispatch_id"]
        safe = re.sub(r"[^A-Za-z0-9._-]", "-", sid)
        (OUT_DIR / f"{safe}.json").write_text(
            json.dumps(pack, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")
        (OUT_DIR / f"{safe}.md").write_text(render_md(pack), encoding="utf-8")
        index.append({
            "signal_id": sid,
            "file": f"{safe}.json",
            "country": pack["country"],
            "recommendation": pack["advance_or_reject_recommendation"],
            "confidence_score": pack["confidence_score"],
        })
        print(f"  pack: {pack['country']} [{pack['advance_or_reject_recommendation']}] -> {safe}.json")

    (OUT_DIR / "index.json").write_text(
        json.dumps({"generated_at": now_iso, "packs": index}, indent=2, ensure_ascii=False) + "\n",
        encoding="utf-8")
    pack_state["updated_at"] = now_iso
    save_pack_state(pack_state)
    print(f"Validation packs written: {len(index)} -> {OUT_DIR}")


if __name__ == "__main__":
    main()
