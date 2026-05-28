# Dispatch Packet — Tourism/Logistics Operator

**Decision job:** Capacity planning and demand trajectory assessment
**Delivery channel:** Telegram
**Generated:** May 28, 2026 at 03:46 UTC
**Dispatches in this packet:** 1

---

## Dispatches (1)

### 1. Caribbean: signal detected

**ID:** `DSP-20260528-002` | **Country:** Caribbean | **Confidence:** 🟡 Validation | 82/100 | B - cross-source
**Channel:** Telegram | **Window:** 48 hours | **Freshness:** sustained
**Feedback status:** ignored

**Evidence:** Buoy Eastern Caribbean (E of Barbados): 25 kts
**Detail:** signal detected
**Grade:** B - cross-source

**Recommended action:** Assess Caribbean demand trajectory. signal detected — adjust capacity plans.
**Decision to influence:** Maritime operations adjustment for safety and logistics routing
**Routing rationale:** Maritime hazards affect island supply chains and tourism transport schedules

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
