# Dispatch Packet — Procurement Watcher

**Decision job:** Project pipeline tracking and expression of interest preparation
**Delivery channel:** Email brief
**Generated:** Jun 18, 2026 at 00:38 UTC
**Dispatches in this packet:** 2

---

## Dispatches (2)

### 1. CARICOM: 3 active procurements — bidding window open

**ID:** `DSP-20260618-016` | **Country:** CARICOM | **Confidence:** 🔴 Immediate | 95/100 | B - cross-source
**Channel:** Email brief | **Window:** 30 days | **Freshness:** sustained
**Feedback status:** ignored

**Evidence:** CDB active procurement notices: 3
**Detail:** CDB active procurement notices: 3
**Grade:** B - cross-source

**Recommended action:** Track CDB/IDB project pipeline: CDB active procurement notices: 3. Review opportunity fit and prepare expression of interest.
**Decision to influence:** Which procurement or project opportunity to pursue
**Routing rationale:** CDB/IDB project pipeline is the primary lead source for project-based business development

### 2. Belize: signal detected

**ID:** `DSP-20260618-031` | **Country:** Belize | **Confidence:** 🔴 Immediate | 91/100 | A - multi-source
**Channel:** Email brief | **Window:** 21 days | **Freshness:** sustained
**Feedback status:** ignored

**Evidence:** CDB active procurement notices: 3
**Detail:** signal detected
**Grade:** A - multi-source

**Recommended action:** CDB procurement (signal detected) aligned with stable shipping lanes. Viable corridor for logistics providers — prepare EOI.
**Decision to influence:** Which logistics/procurement corridor to bid or partner on
**Routing rationale:** CDB procurement aligned with maritime stability = viable logistics corridors for project-based entry

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
