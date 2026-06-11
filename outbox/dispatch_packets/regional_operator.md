# Dispatch Packet — Regional Operator

**Decision job:** Operational readiness and bid pipeline assessment
**Delivery channel:** Telegram
**Generated:** Jun 11, 2026 at 10:00 UTC
**Dispatches in this packet:** 1

---

## Dispatches (1)

### 1. CARICOM: 2 active procurements — bidding window open

**ID:** `DSP-20260611-017` | **Country:** CARICOM | **Confidence:** 🔴 Immediate | 96/100 | B - cross-source
**Channel:** Telegram | **Window:** 30 days | **Freshness:** sustained
**Feedback status:** replied

**Evidence:** CDB active procurement notices: 2
**Detail:** CDB active procurement notices: 2
**Grade:** B - cross-source

**Recommended action:** Review operational readiness for CARICOM opportunities. CDB active procurement notices: 2 — assess capacity and bid pipeline.
**Decision to influence:** Which procurement or project opportunity to pursue
**Routing rationale:** Active procurement directly maps to operational capacity needs — first to respond wins

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
