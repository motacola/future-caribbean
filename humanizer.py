"""Natural-language layer — shared by the dashboard, RSS feed, and ticker.

Pipeline artifacts stay machine-shaped (agents consume them verbatim);
human-facing surfaces translate them with these rules at render time.
"""
from __future__ import annotations
import json
import re

# Each rule: (regex, replacement). Specific templates first, generic last.
HUMANIZE_RULES = [
    (r"^([^:]+): \+?([\d.]+)% multi-source capital surge — market entry window open$",
     r"Money is moving into \1: up \2%, and more than one source says so"),
    (r"^([^:]+): \+?([\d.]+)% multi-source investment validated — opportunity active$",
     r"Money is moving into \1: up \2%, validated by several sources"),
    (r"^([^:]+): \+?([\d.]+)% capital surge on a single official source — market entry window open$",
     r"Money is moving into \1: up \2%, on one official source so far"),
    (r"^([^:]+): \+?([\d.]+)% investment movement, one source — needs corroboration$",
     r"Money is moving into \1: up \2%, but only one source says so yet"),
    (r"^([^:]+): FDI trending at \+?([\d.]+)% — screening trigger active$",
     r"Foreign investment into \1 is up \2%. Worth a first look"),
    (r"^([^:]+): (\d+) active procurements? — bidding window open$",
     r"\2 live tenders in \1. Bids are open now"),
    (r"^([^:]+): food supply indicators shifting — supply chain implications$",
     r"Food supply numbers are shifting in \1. Keep an eye on the supply chain"),
    (r"^Capital convergence: (\d+) Caribbean economies showing multi-source investment momentum$",
     r"\1 Caribbean economies are pulling in money at the same time"),
    (r"^([^:]+): GDP growth signals expanding tourist economy$",
     r"\1's economy is growing, which is good news for tourism demand"),
    (r"^([^:]+): economic stress indicators rising.*$",
     r"Stress numbers are rising in \1. Worth watching"),
    (r"Investigate (.+?) as a capital deployment target this cycle\. Multi-source validation \((.+?)\) confirms directional signal — next step is operator discovery and market entry assessment\.",
     r"Take a serious look at \1 this cycle. Several sources point the same way (\2), so the next step is finding local partners and checking for a real way in."),
    (r"Assess competitive positioning in (.+?)\. FDI movement \((.+?)\) signals growing market or incoming competition — evaluate (.+?)\.",
     r"If you operate in \1, take stock. New money (\2) means a growing market, or new competition arriving."),
    (r"Assess portfolio exposure in (.+?)\. Economic stress indicators \((.+?)\) may affect existing positions or timing\.",
     r"Holding positions in \1? Stress numbers are at \2. Check your exposure and your timing."),
    (r"Assess (.+?) demand trajectory\. (.+?) change — adjust capacity plans\.",
     r"Demand in \1 looks to be shifting (\2), so it is worth revisiting capacity plans."),
    (r"Screen (.+?) for investment readiness\. FDI movement \((.+?)\) is a screening trigger — cross-reference with sector conditions before deploying capital\.",
     r"\1 is worth a first screen: money is moving (\2). Check the sector picture before committing anything."),
    (r"Multi-source validation reduces screening risk — capital follows verified signals",
     r"When several sources agree, half the homework is already done"),
    (r"FDI movement in your operating country signals competition or demand growth — assess positioning",
     r"Money moving into your market means demand, or competition. Either way, better to know early"),
    (r"Active procurement directly maps to operational capacity needs — first to respond wins",
     r"Live tenders reward whoever responds first"),
    (r"Cross-country investment velocity signals where to focus ecosystem support and founder matching",
     r"Where the money lands is where founders will need support next"),
    (r"Economic stress indicators drive policy response and media narratives",
     r"Stress numbers move policy, and headlines"),
    (r"Food trade data reveals supply chain gaps that local founders and agri-tech can fill",
     r"Gaps in the food trade are openings for local founders"),
    (r"GDP growth in tourism-relevant economies signals demand trajectory — plan capacity accordingly",
     r"A growing economy means more visitors. Plan capacity for it"),
    (r"CDB/IDB project pipeline is the primary lead source for project-based business development",
     r"The CDB and IDB project pipeline is where project work starts"),
    (r"Food security is a regional stability indicator — tracks pressure points before they become crises",
     r"Food security numbers flag pressure early, before it becomes a crisis"),
    (r"Which verified opportunity to investigate for capital deployment or partnership entry",
     r"Which opportunity deserves your attention first"),
    (r"Analyst prior from widely reported sector drivers — requires local confirmation",
     r"Widely reported driver, still needs confirming on the ground"),
    (r"(\d+) independent evidence categories already attached",
     r"evidence already attached from \1 directions"),
    (r"High-confidence signal", r"Strong signal"),
    (r"Worth one validation conversation this cycle\.", r"Worth one real conversation this cycle."),
    (r"Umbrella private-sector body — operator discovery",
     r"Knows the private sector. Ask who's really operating"),
    (r"National chamber — operator discovery",
     r"The national chamber, a shortcut to who's doing business"),
    (r"World Bank FDI movement data shows:\s*(.+)", r"World Bank sees foreign investment moving into \1"),
    (r"WB FDI surge detected:\s*", r"World Bank sees money moving into "),
    (r"\bWB\b", "World Bank"),
    (r"\bFDI\b", "foreign investment"),
    # ── 2026-08-22 voice pass: strings found live on the homepage ──
    # CCRIF payout routing decision (was rendering 39× on the front page)
    (r"^Insurance capital deployment for reconstruction / parametric trigger validation$",
     r"Insurance money is moving for rebuilding. Check what the payout trigger covers"),
    (r"^Private sector credit expansion = banking confidence = investment timing signal$",
     r"Banks are lending more, usually a good moment to time an investment"),
    (r"^Deposit base expansion = currency union stability = confidence signal$",
     r"Deposits are growing across the currency union, a quiet sign of confidence"),
    (r"^Which country-sector pair to validate for investment readiness$",
     r"Pick the country and sector most ready for investment, and check it holds up"),
    # Validation-pack verdict lines
    (r"Calibrated confidence (\d+)/100 with (\d+) evidence categories including dated procurement or corroborated sector news\. Worth one validation conversation\.",
     r"Confidence sits at \1 out of 100, backed by \2 kinds of evidence including a dated tender or corroborated news. Worth one real conversation."),
    (r"Calibrated confidence (\d+)/100 with (\d+) evidence categories, but no dated country tender or corroborated sector article yet — advance after confirmation\.",
     r"Confidence sits at \1 out of 100 with \2 kinds of evidence, but nothing dated or independently corroborated yet. Hold until that lands."),
    (r"Calibrated confidence (\d+)/100 with (\d+) evidence categories\. Keep on the desk; advance only after the unresolved questions below are answered\.",
     r"Confidence sits at \1 out of 100 with \2 kinds of evidence. Keep it on the desk until the open questions below get answers."),
    (r"Calibrated confidence (\d+)/100 with no corroborating evidence categories\. Park unless new corroborating data arrives next cycle\.",
     r"Confidence sits at just \1 out of 100 with nothing to back it yet. Park it unless fresh evidence arrives next cycle."),
    # ── 2026-08-25 voice pass: machine phrasing still reaching the front page ──
    # Single-source variant of the capital-deployment action (multi-source variant above).
    (r"Investigate (.+?) as a capital deployment target this cycle\. One official source shows the movement \((.+?)\) — corroborate it before acting, then move to operator discovery\.",
     r"Take a serious look at \1 this cycle. One official source shows the move (\2). Get a second one before you act, then start finding local partners."),
    (r"Which specific sectors are driving the movement in (.+?)\? No official sector-breakdown dataset matched this cycle\.",
     r"Which industries are actually driving this in \1? Nobody has published a breakdown yet."),
    (r"Validate fit with registry-listed operators \((.+?)\) before outreach\.",
     r"Check these companies are the right fit before you reach out: \1."),
    (r"^Analyst prior — sector likely but unconfirmed$", r"Likely, but nobody has confirmed it yet"),
    (r"\bcorroborated\b", "confirmed"),
    (r"\bCorroborated\b", "Confirmed"),
    (r"\bunconfirmed\b", "not yet confirmed"),
    (r"\bUnconfirmed\b", "Not yet confirmed"),
    (r"\bcorroboration\b", "a second source"),
    (r"\boperator discovery\b", "finding local partners"),
    (r"^Source registry now tracked by the desk$", r"Where the desk gets this"),
    # Generic dispatch fallbacks. The pipeline has no specifics for these, so
    # say that plainly rather than dressing an empty card as an insight.
    (r"Review (.+?): signal detected\. Validate locally before action\.",
     r"The desk logged movement in \1 but nothing specific yet. Worth a local check before it firms up."),
    (r"Signal context for (.+?): signal detected\. Use this dispatch as a briefing input or narrative lead\.",
     r"Movement logged in \1, with no detail attached yet: background for a briefing rather than a story on its own."),
    (r"^(.+?): signal detected$", r"Early signal in \1, no detail yet"),
    # The generic placeholder also gets interpolated into templates that expect a
    # figure, producing "Signal strength (signal detected)".
    (r"\(signal detected\)", r"(no figure attached yet)"),
    # ── Internal vocabulary ─────────────────────────────────
    # Signal kinds, CCRIF perils and persona ids travel through generated
    # prose as the slugs the pipeline stores them as, and reached readers
    # intact: "Peril: tropical_cyclone" on the front page, "2 converging
    # signal types (enhanced_investment, investment_signal)" on /build.
    # Rewrite the vocabulary wherever it lands in a sentence.
    (r"\benhanced_investment\b", r"validated investment"),
    (r"\binvestment_signal\b", r"investment signal"),
    (r"\beconomic_vulnerability\b", r"economic stress"),
    (r"\bdevelopment_pipeline\b", r"development pipeline"),
    (r"\bccrif_payout\b", r"catastrophe insurance payout"),
    (r"\bfinance_signal\b", r"finance signal"),
    (r"\bnews_coverage\b", r"news coverage"),
    (r"\bfood_security\b", r"food security"),
    (r"\btourism_impact\b", r"tourism impact"),
    (r"\btropical_cyclone\b", r"tropical cyclone"),
    (r"\bexcess_rainfall\b", r"excess rainfall"),
    (r"\bprocurement_watcher\b", r"procurement watcher"),
    (r"\bregional_operator\b", r"regional operator"),
]
_HUMANIZE_COMPILED = [(re.compile(p), r) for p, r in HUMANIZE_RULES]

def humanize(text: str) -> str:
    if not text:
        return text
    for rx, repl in _HUMANIZE_COMPILED:
        text = rx.sub(repl, text)
    return text

# JS twin for live content (theater stream, ask-desk answers):
# same patterns, replacement backrefs converted \1 -> \1
humanize_rules_json = json.dumps(
    [[p, re.sub(r"\\(\d)", r"$\1", r)] for p, r in HUMANIZE_RULES],
    ensure_ascii=False).replace("</", "<\\/")

