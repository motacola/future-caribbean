# Abeng brand and voice

Status: **draft for Chris**, 18 October 2026. Companion to `DESIGN.md` (visual tokens and layout live there; this file owns what Abeng is called, how it sounds and how it presents itself). Choices marked *Jev* were judged by the local Jev CLI — advisory evidence, not reader research.

## 1. What Abeng is

**Descriptor:** A live desk for the Caribbean.
**Tagline:** What changed. Who should act. *(Jev 0.62 over "A live desk for the Caribbean" 0.30; "Where Caribbean capital is moving" 0.01)*

**One paragraph:** Every four hours Abeng reads what Caribbean governments, development banks, central banks, tender portals, exchanges and storm services publish across 23 markets and territories. It flags where something actually changed, who is best placed to act, and how solid the evidence is — with the source attached to every claim. No reporters, no opinions, no invented figures.

**For:** fund managers and diaspora investors, operators and founders, shipping and logistics firms, procurement watchers, government and development agencies.

**The name.** An abeng is the horn the Maroons of Jamaica blew to send signals across the hills. Abeng does the same for public data. Tell this once — on the About section and in the one-pager — never as a slogan or hero line. *(Jev 0.81)*

**Portfolio line:** an application in the next8.tech portfolio (Applications · Data · Intelligence). Mention in footers and decks, not in product copy.

## 2. Personality: the harbour pilot

*(Jev 0.62 over "analyst friend" 0.34; "institution" 0.03; "newswire" 0.01)*

A pilot brings ships into Caribbean harbours. They know the channel, name the rocks, and do not dramatise. That is the voice.

| Abeng is | Abeng is not |
|---|---|
| **Calm** — states the move, then the evidence | breathless, urgent, "huge", "massive" |
| **Exact** — figures, sources, dates, one decimal | rounded hype, vague "growth", "momentum" alone |
| **Local** — names the market, the agency, the port | generic "emerging markets", "the region" when a country is meant |
| **Plain-spoken** — words a busy operator uses | system language: validated, magnitudes, layer, pipeline, seeded |
| **Candid** — says when one source is all there is | certainty it has not earned; investment advice |

Borrowed from the analyst friend: direct second person when telling the reader what to do ("Get a second source before you act").

## 3. How we write

1. **Lead with the change, then the source, then the action.** "Guyana: foreign investment up 860%, on one source so far."
2. **Every figure carries its source and its confidence.** One source → say so. Never let a headline outrun its evidence.
3. **Say who should act, in their words.** "Worth passing to founders and investors you know in Guyana."
4. **No internal machinery on the page.** Readers never see: validated, magnitude, signal strength, routing, reprioritisation, seeded, layer, cluster, track (as a noun), dispatch IDs, raw values like `none`.
5. **Not advice.** Abeng points; people on the ground confirm. Keep "A signal, not advice" where a call to act appears.
6. **Name places properly.** Full names first time (St Vincent and the Grenadines, Turks and Caicos Islands); no "Caribwide" in reader copy — say "Regional".

### Mechanics

- **Spelling:** British/Caribbean (colour, centre, organisation, programme) — the register CARICOM and regional institutions use.
- **Case:** sentence case for headings, buttons and labels. Uppercase only as a CSS treatment on short mono labels.
- **Numbers:** `+860.3%` for changes (sign always, one decimal); `US$6.6 million`; local currency with code first time (`J$1.05 billion`). Never "(860.3% change)".
- **Dates:** `6 Sept 2026`, `18 Oct`; times as `16:00 UTC`.
- **Sources:** name the publisher: "World Bank", "CDB", "Bank of Guyana" — not "an official source" when we know which.
- **Lists:** country, then status word: "Jamaica · early signal".
- **Buttons:** verb first, plain: "Read the briefing", "Ask the desk", "Open the full desk". No "Click here", no "Learn more".
- **Device-neutral:** "Select a country", not "Tap" or "Click".

### Words

| Use | Avoid |
|---|---|
| moving into, rose, fell, opened, closed | surging, skyrocketing, exploding, booming |
| early signal, one source so far, confirmed by two | validated, verified (unless a person verified it) |
| worth passing to, best placed to act | route to, high-priority introduction target |
| the desk, the wire, the briefing, a move | engine, pipeline, layer, cluster, dispatch (in reader copy) |
| research, not advice | insights, intelligence layer, AI-powered, unlock, leverage, seamless |

## 4. Tone by context

| Context | Tone | Example |
|---|---|---|
| Lead briefing | measured, specific, one clear action | "Take a serious look at Guyana this cycle. One World Bank series shows the move. Get a second source before you act." |
| Moves / wire | headline only, change + market | "Suriname: foreign investment up 206%, one source so far" |
| Country card | status, one line, link | "Investment · Money is moving into Guyana, on one official source so far" |
| Ask the desk | direct answer first, sources last | "Three markets changed this cycle… Sources: World Bank WDI, CDB." |
| Empty / error | say what happened and what still works | "The desk is not reachable from this copy of the page. The full desk has every country and source." |
| Test or seeded data | label it plainly | "These responses are test data, there to show how feedback changes priority." |
| One-pager / pitch | confident, no superlatives, no unproven traction | Never claim customers, revenue or partners we do not have. |

## 5. Before and after (live copy, Jev-judged)

| Before | After | Jev prefers after |
|---|---|---|
| Guyana is the one to watch. | Guyana: foreign investment up 860%, on one source so far | 0.67 (original 0.02) |
| Bigger pulse, stronger signal. Tap a country. | Larger pulses mark stronger signals. Select a country for what the desk found. | 0.89 |
| Route Guyana opportunity to relevant founders and investors in your network. Signal strength (860.3% change) makes this a high-priority introduction target. | Worth passing to founders and investors you know in Guyana: inflows rose 860% on one World Bank series. Confirm with a second source first. | 1.00 |
| Evidence: Multi-country enhanced investment validated across 3 countries. Top magnitudes: … | Evidence: foreign investment rose in three markets — Guyana +860.3%, Suriname +206.0%, Barbados +34.8% (World Bank). | 0.96 |
| Validation note: these seeded responses exercise the feedback and reprioritisation loop… | These responses are test data, there to show how feedback changes priority. Real reader responses will replace them. | 0.63 |
| Market momentum / research layer | Market momentum: research, not advice | 0.83 |
| Jamaica — early signal · Jamaica | *keep* (Jev 0.59 for the original) — but drop the repeated country name in code | — |

## 6. Visual identity (summary; tokens in DESIGN.md)

- **Palette: Harbour navy** (18 Oct 2026; Chris: no brown, no green; Jev 0.71 over "Sea and sun" 0.27 and "Coral and charcoal" 0.02).
- **Nameplate:** ABENG in Playfair Display 700, uppercase, 3px tracking, sun amber (`#E0A526`) on the navy masthead (`#14243B → #0A1424`), amber→blue rule beneath. 30–38px; never below 24px. Same masthead on every page.
- **Palette roles:** cool white paper `#F7F8FA`, white cards; navy ink `#0F1B2D` for text and masthead; Caribbean blue `#1D5FD0` for links, progress and accents; deep blue `#1747A6` for small labels and kickers; amber `#E0A526` for the nameplate and rules only (not small text); red `#C0392B` for risk only. Map pins: investment `#1D5FD0`, climate `#22A3D6`, procurement `#E07A2E`, market watch `#7B5CD6`, quiet `#8A94A6`.
- **Never:** brown, beige, ochre, olive, teal or any green, in UI or charts. Third-party brand colours in channel mock-ups (WhatsApp, Telegram) are the only exception.
- **Type:** Playfair for headlines; Inter for reading; IBM Plex Mono only for small labels and figures.
- **Signature:** the live map of 23 pulsing markets is the hero and the brand's most recognisable asset. Never cut or shrink it.
- **Imagery:** publisher photography that belongs to the story, or none. No stock, no illustrations standing in for news.
- **Open:** no symbol/logomark yet. A horn mark could follow, but only if it reads at 16px and does not replace the wordmark.

## 7. Copy defects from the 18 Oct audit — all fixed 18 Oct

Fixed at the display layer (`humanizer.py` + its twin `src/lib/humanize.ts`, `src/lib/data.ts`), not in the pipeline, so stored artifacts are unchanged and API/MCP/Ask answers pick up the voice through `humanizer.py`. Both TS humanizers now replace every match, as Python's `re.sub` always did. Every inner page uses `src/components/SiteMast.astro`. Jev re-audit: strings below 0.5 fell from 60/293 (20%) to 36/288 (12%); median 0.60; no banned terms reach readers. Headlines round large moves to whole numbers ("up 860%"); evidence keeps one decimal.


1. Raw `none` signal kind rendered as a visible label in the desk's "Watch the desk work" event log (e.g. "none · Grenada · 84%").
2. System language in generated copy (`src/lib/data.ts`, `humanize.ts`): validated, magnitudes, signal strength, introduction target, seeded, research layer.
3. Three formats for the same change: `+860.3%`, `(860.3% change)`, `moved up 860.3%` → standardise on `+860.3%`.
4. Watchlist labels repeat the country ("Jamaica — early signal · Jamaica").
5. "Caribwide" shown to readers → "Regional".
6. Lead headline template "X is the one to watch." → change-led headline.
7. Device verbs ("Tap") → "Select".
8. Pages off-brand: `/accuracy` has no masthead; `/market-momentum` uses a different white "Abeng" header.

Audit method: 293 authored strings from `/` and `/desk` scored by Jev against this voice (60 below 0.5, concentrated in data-generated copy); key rewrites tested head-to-head. Scores are advisory.
