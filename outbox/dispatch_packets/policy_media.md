# Dispatch Packet — Policy/Media

**Decision job:** Briefing input and narrative lead sourcing
**Delivery channel:** Telegram digest
**Generated:** Jul 24, 2026 at 18:31 UTC
**Dispatches in this packet:** 1

---

## Dispatches (1)

### 1. St. Vincent and the Grenadines: economic stress indicators rising — portfolio review recommended

**ID:** `DSP-20260724-010` | **Country:** St. Vincent and the Grenadines | **Confidence:** 🟢 Monitor | 69/100 | C - single-source
**Channel:** Telegram digest | **Window:** 30 days | **Freshness:** sustained
**Feedback status:** ignored

**Evidence:** St. Vincent and the Grenadines: Unemployment % is 18.00% (2025).
**Detail:** 18.00%
**Grade:** C - single-source

**Recommended action:** Signal context for St. Vincent and the Grenadines: 18.00%. Use this dispatch as a briefing input or narrative lead.
**Decision to influence:** Risk assessment for capital exposure or policy attention
**Routing rationale:** Economic stress indicators drive policy response and media narratives
**Risk flags:** Elevated economic stress in St. Vincent and the Grenadines

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
