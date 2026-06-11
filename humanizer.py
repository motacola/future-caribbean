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
     r"Money is moving into \1 — up \2%, and more than one source says so"),
    (r"^([^:]+): FDI trending at \+?([\d.]+)% — screening trigger active$",
     r"Foreign investment into \1 is up \2% — worth a first look"),
    (r"^([^:]+): (\d+) active procurements? — bidding window open$",
     r"\2 live tenders in \1 — bids are open now"),
    (r"^([^:]+): food supply indicators shifting — supply chain implications$",
     r"Food supply numbers are shifting in \1 — keep an eye on the supply chain"),
    (r"^Capital convergence: (\d+) Caribbean economies showing multi-source investment momentum$",
     r"\1 Caribbean economies are pulling in money at the same time"),
    (r"^([^:]+): GDP growth signals expanding tourist economy$",
     r"\1's economy is growing — good news for tourism demand"),
    (r"^([^:]+): economic stress indicators rising.*$",
     r"Stress numbers are rising in \1 — worth watching"),
    (r"Investigate (.+?) as a capital deployment target this cycle\. Multi-source validation \((.+?)\) confirms directional signal — next step is operator discovery and market entry assessment\.",
     r"Take a serious look at \1 this cycle. Several sources point the same way (\2) — the next step is finding local partners and checking for a real way in."),
    (r"Assess competitive positioning in (.+?)\. FDI movement \((.+?)\) signals growing market or incoming competition — evaluate (.+?)\.",
     r"If you operate in \1, take stock: new money (\2) means a growing market — or new competition arriving."),
    (r"Assess portfolio exposure in (.+?)\. Economic stress indicators \((.+?)\) may affect existing positions or timing\.",
     r"Holding positions in \1? Stress numbers are at \2 — check your exposure and your timing."),
    (r"Assess (.+?) demand trajectory\. (.+?) change — adjust capacity plans\.",
     r"Demand in \1 looks to be shifting (\2) — worth revisiting capacity plans."),
    (r"Screen (.+?) for investment readiness\. FDI movement \((.+?)\) is a screening trigger — cross-reference with sector conditions before deploying capital\.",
     r"\1 is worth a first screen: money is moving (\2). Check the sector picture before committing anything."),
    (r"Multi-source validation reduces screening risk — capital follows verified signals",
     r"When several sources agree, half the homework is already done"),
    (r"FDI movement in your operating country signals competition or demand growth — assess positioning",
     r"Money moving into your market means demand — or competition. Either way, better to know early"),
    (r"Active procurement directly maps to operational capacity needs — first to respond wins",
     r"Live tenders reward whoever responds first"),
    (r"Cross-country investment velocity signals where to focus ecosystem support and founder matching",
     r"Where the money lands is where founders will need support next"),
    (r"Economic stress indicators drive policy response and media narratives",
     r"Stress numbers move policy — and headlines"),
    (r"Food trade data reveals supply chain gaps that local founders and agri-tech can fill",
     r"Gaps in the food trade are openings for local founders"),
    (r"GDP growth in tourism-relevant economies signals demand trajectory — plan capacity accordingly",
     r"A growing economy means more visitors — plan capacity for it"),
    (r"CDB/IDB project pipeline is the primary lead source for project-based business development",
     r"The CDB and IDB project pipeline is where project work starts"),
    (r"Food security is a regional stability indicator — tracks pressure points before they become crises",
     r"Food security numbers flag pressure early — before it becomes a crisis"),
    (r"Which verified opportunity to investigate for capital deployment or partnership entry",
     r"Which opportunity deserves your attention first"),
    (r"Analyst prior from widely reported sector drivers — requires local confirmation",
     r"Widely reported driver — still needs confirming on the ground"),
    (r"(\d+) independent evidence categories already attached",
     r"evidence already attached from \1 directions"),
    (r"High-confidence signal", r"Strong signal"),
    (r"Worth one validation conversation this cycle\.", r"Worth one real conversation this cycle."),
    (r"Umbrella private-sector body — operator discovery",
     r"Knows the private sector — ask who's really operating"),
    (r"National chamber — operator discovery",
     r"The national chamber — a shortcut to who's doing business"),
    (r"World Bank FDI movement data shows:\s*(.+)", r"World Bank sees foreign investment moving into \1"),
    (r"WB FDI surge detected:\s*", r"World Bank sees money moving into "),
    (r"\bWB\b", "World Bank"),
    (r"\bFDI\b", "foreign investment"),
]
_HUMANIZE_COMPILED = [(re.compile(p), r) for p, r in HUMANIZE_RULES]

def humanize(text: str) -> str:
    if not text:
        return text
    for rx, repl in _HUMANIZE_COMPILED:
        text = rx.sub(repl, text)
    return text

# JS twin for live content (theater stream, ask-desk answers):
# same patterns, replacement backrefs converted \1 -> $1
humanize_rules_json = json.dumps(
    [[p, re.sub(r"\\(\d)", r"$\1", r)] for p, r in HUMANIZE_RULES],
    ensure_ascii=False).replace("</", "<\\/")

