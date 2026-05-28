# Dispatch Packet — Policy/Media

**Decision job:** Briefing input and narrative lead sourcing
**Delivery channel:** Telegram digest
**Generated:** May 28, 2026 at 20:34 UTC
**Dispatches in this packet:** 3

---

## Dispatches (3)

### 1. CARICOM: food supply indicators shifting — supply chain implications

**ID:** `DSP-20260528-016` | **Country:** CARICOM | **Confidence:** 🟡 Validation | 78/100 | B - cross-source
**Channel:** Telegram digest | **Window:** 30 days | **Freshness:** sustained
**Feedback status:** ignored

**Evidence:** CARICOM food trade data: 18 datasets available
**Detail:** 5%
**Grade:** B - cross-source

**Recommended action:** Signal context for CARICOM: 5%. Use this dispatch as a briefing input or narrative lead.
**Decision to influence:** Agricultural/logistics investment case or policy response planning
**Routing rationale:** Food security is a regional stability indicator — tracks pressure points before they become crises

### 2. St. Vincent and the Grenadines: economic stress indicators rising — portfolio review recommended

**ID:** `DSP-20260528-012` | **Country:** St. Vincent and the Grenadines | **Confidence:** 🟡 Validation | 72/100 | C - single-source
**Channel:** Telegram digest | **Window:** 30 days | **Freshness:** sustained
**Feedback status:** ignored

**Evidence:** St. Vincent and the Grenadines: Unemployment % is 18.00% (2025).
**Detail:** 18.00%
**Grade:** C - single-source

**Recommended action:** Signal context for St. Vincent and the Grenadines: 18.00%. Use this dispatch as a briefing input or narrative lead.
**Decision to influence:** Risk assessment for capital exposure or policy attention
**Routing rationale:** Economic stress indicators drive policy response and media narratives
**Risk flags:** Elevated economic stress in St. Vincent and the Grenadines

### 3. Suriname: economic stress indicators rising — portfolio review recommended

**ID:** `DSP-20260528-010` | **Country:** Suriname | **Confidence:** 🟢 Monitor | 54/100 | C - single-source
**Channel:** Telegram digest | **Window:** 30 days | **Freshness:** sustained
**Feedback status:** ignored

**Evidence:** Suriname: Inflation annual % is 16.23% (2024).
**Detail:** 16.23%
**Grade:** C - single-source

**Recommended action:** Signal context for Suriname: 16.23%. Use this dispatch as a briefing input or narrative lead.
**Decision to influence:** Risk assessment for capital exposure or policy attention
**Routing rationale:** Economic stress indicators drive policy response and media narratives
**Risk flags:** Elevated economic stress in Suriname

---

## Action Checklist

- [ ] Review each dispatch and validate evidence
- [ ] Prioritise by confidence score (higher = more actionable)
- [ ] Take recommended action or route to relevant contact
- [ ] Provide feedback: forwarded, replied, opened, or ignored

## Feedback Options

Each dispatch accepts feedback via the intake system:

```bash
python3 packagers/feedback_intake.py --dispatch-id <ID> --status forwarded|replied|opened|ignored --note "..."
```

Feedback affects next-cycle ranking: forwarded (+8), replied (+5),
opened (+2), ignored (-2).

## Sources

Dispatches in this packet are sourced from:

- World Bank FDI indicators (net inflows)
- IDB Open Data (Caribbean datasets)
- NOAA NWS (weather alerts)
- NDBC Buoys (marine conditions)
- CARICOM Statistics (WordPress REST API)
- CDB (procurement notices via RSS)
- NHC (storm tracking)

Cross-source merger validates signals across multiple sources
before dispatch generation.
