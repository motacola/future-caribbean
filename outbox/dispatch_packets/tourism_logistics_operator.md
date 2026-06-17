# Dispatch Packet — Tourism/Logistics Operator

**Decision job:** Capacity planning and demand trajectory assessment
**Delivery channel:** Telegram
**Generated:** Jun 17, 2026 at 22:29 UTC
**Dispatches in this packet:** 1

---

## Dispatches (1)

### 1. Guyana: GDP growth signals expanding tourist economy

**ID:** `DSP-20260617-013` | **Country:** Guyana | **Confidence:** 🟢 Monitor | 51/100 | C - single-source
**Channel:** Telegram | **Window:** 30 days | **Freshness:** sustained
**Feedback status:** ignored

**Evidence:** Guyana: GDP current USD moved up 45.8% from 2023 to 2024.
**Detail:** 45.8% change
**Grade:** C - single-source

**Recommended action:** Assess Guyana demand trajectory. 45.8% change — adjust capacity plans.
**Decision to influence:** Tourism capacity planning and timing of marketing or expansion
**Routing rationale:** GDP growth in tourism-relevant economies signals demand trajectory — plan capacity accordingly

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
