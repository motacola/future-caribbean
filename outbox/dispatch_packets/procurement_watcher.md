# Dispatch Packet — Procurement Watcher

**Decision job:** Project pipeline tracking and expression of interest preparation
**Delivery channel:** Email brief
**Generated:** Aug 30, 2026 at 19:17 UTC
**Dispatches in this packet:** 1

---

## Dispatches (1)

### 1. CARICOM: 9 active procurements — bidding window open

**ID:** `DSP-20260830-014` | **Country:** CARICOM | **Confidence:** 🔴 Immediate | 95/100 | B - cross-source
**Channel:** Email brief | **Window:** 30 days | **Freshness:** sustained
**Feedback status:** ignored

**Evidence:** CDB active procurement notices: 9; • Enhancing the Quality of the Belize National Quality Infrastructure; • Grenada Education Enhancement Project - Phase II; • The Bahamas Water Supply Improvement Project Phase 2
**Detail:** CDB active procurement notices: 9
**Grade:** B - cross-source

**Recommended action:** Track CDB/IDB project pipeline: CDB active procurement notices: 9. Review opportunity fit and prepare expression of interest.
**Decision to influence:** Which procurement or project opportunity to pursue
**Routing rationale:** CDB/IDB project pipeline is the primary lead source for project-based business development

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
