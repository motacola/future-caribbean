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

import json
import re
from datetime import datetime, timezone
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
OUT_DIR = ROOT / "outbox" / "validation_packs"

MAX_PACKS = 5
MAX_MATCHES = 6

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
        bool([h for h in hyps if h.get("status") == "data_available"]),
        bool(projects),
        bool([p for p in procurement if p.get("match") == "country"]),
        bool(operators),
    ])
    if confidence >= 80 and evidence_categories >= 2:
        return ("advance", (
            f"High-confidence signal ({confidence}/100) with {evidence_categories} independent "
            "evidence categories already attached. Worth one validation conversation this cycle."
        ))
    if confidence >= 60 or evidence_categories >= 1:
        return ("hold", (
            f"Signal confidence {confidence}/100 with {evidence_categories} evidence categories. "
            "Keep on the desk; advance only after the unresolved questions below are answered."
        ))
    return ("reject", (
        f"Signal confidence {confidence}/100 with no corroborating evidence categories. "
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
        qs.append("Operator discovery is not yet automated — source two credible local operators via the listed institutions.")
    qs.append("Validate that the underlying FDI movement is sustained, not a one-off transaction or statistical revision.")
    return qs


# ── Pack assembly ───────────────────────────────────────────

def build_pack(dispatch: dict, wb: dict, idb: dict, tier2: dict, now_iso: str,
               tenders: list[dict] | None = None) -> dict:
    country = dispatch.get("country_cluster", "Caribbean")
    tier2_items = (tier2 or {}).get("items", []) or []
    wb_obs = wb_observations_for(country, wb)

    hyps = sector_hypotheses_for(country, tier2_items, wb_obs)
    projects = supporting_projects_for(country, idb, tier2_items)
    procurement = procurement_matches_for(country, tier2_items, tenders)
    cdata = country_data_for(country, tier2_items)
    institutions = INSTITUTIONS.get(country, []) + REGIONAL_INSTITUTIONS
    # No automated operator source exists yet; never fabricate one.
    operators: list[dict] = []

    confidence = int(dispatch.get("confidence_score", 0) or 0)
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

    return {
        "signal_id": dispatch.get("signal_id", ""),
        "dispatch_id": dispatch.get("dispatch_id", ""),
        "country": country,
        "signal_title": dispatch.get("title", ""),
        "confidence_score": confidence,
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


def render_md(pack: dict) -> str:
    lines = [
        f"# Opportunity Validation Pack — {pack['country']}",
        "",
        f"- Signal: `{pack['signal_id']}` · Dispatch: `{pack['dispatch_id']}`",
        f"- Confidence: {pack['confidence_score']}/100 · {pack['evidence_grade']}",
        f"- Recommendation: **{pack['advance_or_reject_recommendation'].upper()}** — {pack['recommendation_reason']}",
        f"- Last validated: {pack['last_validated_at']}",
        "",
        "## Sector hypotheses",
    ]
    for h in pack["sector_hypotheses"] or [{"sector": "None identified this cycle", "basis": ""}]:
        basis = f" — _{h['basis']}_" if h.get("basis") else ""
        lines.append(f"- {h['sector']}{basis}")
    lines += ["", "## Supporting projects & publications"]
    for p in pack["supporting_projects"] or []:
        lines.append(f"- [{p['title']}]({p['url']}) — {p['source']}")
    if not pack["supporting_projects"]:
        lines.append("- No matched projects this cycle.")
    lines += ["", "## Procurement matches"]
    for p in pack["procurement_matches"] or []:
        lines.append(f"- [{p['title']}]({p['url']}) — {p['source']} ({p['match']})")
    if not pack["procurement_matches"]:
        lines.append("- No live procurement notices matched.")
    lines += ["", "## Official country data"]
    for d in pack["official_country_data"] or []:
        lines.append(f"- [{d['title']}]({d['url']}) — {d['source']}")
    if not pack["official_country_data"]:
        lines.append("- No official country datasets matched.")
    lines += ["", "## Relevant institutions & intro targets"]
    for i in pack["relevant_institutions"]:
        lines.append(f"- {i['name']} — {i['role']}")
    lines += ["", "## Unresolved questions"]
    for q in pack["unresolved_questions"]:
        lines.append(f"- {q}")
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

    OUT_DIR.mkdir(parents=True, exist_ok=True)
    now_iso = datetime.now(timezone.utc).isoformat()

    index = []
    for dispatch in select_lead_dispatches(dispatches):
        pack = build_pack(dispatch, wb, idb, tier2, now_iso, tenders)
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
    print(f"Validation packs written: {len(index)} -> {OUT_DIR}")


if __name__ == "__main__":
    main()
