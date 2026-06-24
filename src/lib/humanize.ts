// Port of humanizer.py — natural-language rewrite rules for pipeline artifacts.
// JS regex syntax: $1 backreferences (Python uses \1; the JSON export already
// converts them so the client-side twin receives the same array).

const HUMANIZE_RULES: [string, string][] = [
  ["^([^:]+): \\+?([\\d.]+)% multi-source capital surge — market entry window open$",
   "Money is moving into $1 — up $2%, and more than one source says so"],
  ["^([^:]+): \\+?([\\d.]+)% multi-source investment validated — opportunity active$",
   "Money is moving into $1 — up $2%, validated by several sources"],
  ["^([^:]+): FDI trending at \\+?([\\d.]+)% — screening trigger active$",
   "Foreign investment into $1 is up $2% — worth a first look"],
  ["^([^:]+): (\\d+) active procurements? — bidding window open$",
   "$2 live tenders in $1 — bids are open now"],
  ["^([^:]+): food supply indicators shifting — supply chain implications$",
   "Food supply numbers are shifting in $1 — keep an eye on the supply chain"],
  ["^Capital convergence: (\\d+) Caribbean economies showing multi-source investment momentum$",
   "$1 Caribbean economies are pulling in money at the same time"],
  ["^([^:]+): GDP growth signals expanding tourist economy$",
   "$1's economy is growing — good news for tourism demand"],
  ["^([^:]+): economic stress indicators rising.*$",
   "Stress numbers are rising in $1 — worth watching"],
  ["Investigate (.+?) as a capital deployment target this cycle\\. Multi-source validation \\((.+?)\\) confirms directional signal — next step is operator discovery and market entry assessment\\.",
   "Take a serious look at $1 this cycle. Several sources point the same way ($2) — the next step is finding local partners and checking for a real way in."],
  ["Assess competitive positioning in (.+?)\\. FDI movement \\((.+?)\\) signals growing market or incoming competition — evaluate (.+?)\\.",
   "If you operate in $1, take stock: new money ($2) means a growing market — or new competition arriving."],
  ["Assess portfolio exposure in (.+?)\\. Economic stress indicators \\((.+?)\\) may affect existing positions or timing\\.",
   "Holding positions in $1? Stress numbers are at $2 — check your exposure and your timing."],
  ["Assess (.+?) demand trajectory\\. (.+?) change — adjust capacity plans\\.",
   "Demand in $1 looks to be shifting ($2) — worth revisiting capacity plans."],
  ["Screen (.+?) for investment readiness\\. FDI movement \\((.+?)\\) is a screening trigger — cross-reference with sector conditions before deploying capital\\.",
   "$1 is worth a first screen: money is moving ($2). Check the sector picture before committing anything."],
  ["Multi-source validation reduces screening risk — capital follows verified signals",
   "When several sources agree, half the homework is already done"],
  ["FDI movement in your operating country signals competition or demand growth — assess positioning",
   "Money moving into your market means demand — or competition. Either way, better to know early"],
  ["Active procurement directly maps to operational capacity needs — first to respond wins",
   "Live tenders reward whoever responds first"],
  ["Cross-country investment velocity signals where to focus ecosystem support and founder matching",
   "Where the money lands is where founders will need support next"],
  ["Economic stress indicators drive policy response and media narratives",
   "Stress numbers move policy — and headlines"],
  ["Food trade data reveals supply chain gaps that local founders and agri-tech can fill",
   "Gaps in the food trade are openings for local founders"],
  ["GDP growth in tourism-relevant economies signals demand trajectory — plan capacity accordingly",
   "A growing economy means more visitors — plan capacity for it"],
  ["CDB/IDB project pipeline is the primary lead source for project-based business development",
   "The CDB and IDB project pipeline is where project work starts"],
  ["Food security is a regional stability indicator — tracks pressure points before they become crises",
   "Food security numbers flag pressure early — before it becomes a crisis"],
  ["Which verified opportunity to investigate for capital deployment or partnership entry",
   "Which opportunity deserves your attention first"],
  ["Analyst prior from widely reported sector drivers — requires local confirmation",
   "Widely reported driver — still needs confirming on the ground"],
  ["(\\d+) independent evidence categories already attached",
   "evidence already attached from $1 directions"],
  ["High-confidence signal", "Strong signal"],
  ["Worth one validation conversation this cycle\\.", "Worth one real conversation this cycle."],
  ["Umbrella private-sector body — operator discovery",
   "Knows the private sector — ask who's really operating"],
  ["National chamber — operator discovery",
   "The national chamber — a shortcut to who's doing business"],
  ["World Bank FDI movement data shows:\\s*(.+)", "World Bank sees foreign investment moving into $1"],
  ["WB FDI surge detected:\\s*", "World Bank sees money moving into "],
  ["\\bWB\\b", "World Bank"],
  ["\\bFDI\\b", "foreign investment"],
];

const _compiled: [RegExp, string][] = HUMANIZE_RULES.map(([p, r]) => {
  try { return [new RegExp(p), r]; } catch { return null; }
}).filter(Boolean) as [RegExp, string][];

export function humanize(text: string | null | undefined): string {
  if (!text) return text ?? '';
  let out = String(text);
  for (const [rx, r] of _compiled) {
    out = out.replace(rx, r);
  }
  return out;
}

// JSON for the client-side JS twin embedded in the page script.
export const humanizeRulesJson = JSON.stringify(HUMANIZE_RULES).replace(/<\//g, '<\\/');
