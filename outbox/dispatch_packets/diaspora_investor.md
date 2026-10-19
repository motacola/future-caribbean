# Dispatch Packet — Diaspora Investor

**Decision job:** Capital deployment screening and market entry assessment
**Delivery channel:** Email brief + Telegram
**Generated:** Oct 19, 2026 at 12:03 UTC
**Dispatches in this packet:** 6

---

## Dispatches (6)

### 1. Bahamas: +538.6% capital surge on a single official source — market entry window open

**ID:** `DSP-20261019-012` | **Country:** Bahamas | **Confidence:** 🔴 Immediate | 100/100 | C - single-source
**Channel:** Email brief + Telegram | **Window:** 14 days | **Freshness:** sustained
**Feedback status:** ignored

**Evidence:** WB FDI surge detected: Bahamas; CARICOM trade/FDI data available (regional context, not country confirmation); CDB procurement/evaluation activity (regional context, not country confirmation); Confidence: 1 country-specific source confirmed · 2 regional dataset(s) available as context
**Detail:** 538.6% change
**Grade:** C - single-source

**Recommended action:** Investigate Bahamas as a capital deployment target this cycle. Multi-source validation (538.6% change) confirms directional signal — next step is operator discovery and market entry assessment.
**Decision to influence:** Which verified opportunity to investigate for capital deployment or partnership entry
**Routing rationale:** Multi-source validation reduces screening risk — capital follows verified signals

### 2. Suriname: +206.2% investment movement, one source — needs corroboration

**ID:** `DSP-20261019-015` | **Country:** Suriname | **Confidence:** 🔴 Immediate | 98/100 | C - single-source
**Channel:** Email brief + Telegram | **Window:** 14 days | **Freshness:** sustained
**Feedback status:** ignored

**Evidence:** WB FDI surge detected: Suriname; CARICOM trade/FDI data available (regional context, not country confirmation); CDB procurement/evaluation activity (regional context, not country confirmation); Confidence: 1 country-specific source confirmed · 2 regional dataset(s) available as context
**Detail:** 206.2% change
**Grade:** C - single-source

**Recommended action:** Investigate Suriname as a capital deployment target this cycle. Multi-source validation (206.2% change) confirms directional signal — next step is operator discovery and market entry assessment.
**Decision to influence:** Which verified opportunity to investigate for capital deployment or partnership entry
**Routing rationale:** Multi-source validation reduces screening risk — capital follows verified signals

### 3. Bahamas: FDI trending at +538.6% — screening trigger active

**ID:** `DSP-20261019-001` | **Country:** Bahamas | **Confidence:** 🔴 Immediate | 94/100 | B - cross-source
**Channel:** Email brief + Telegram | **Window:** 14 days | **Freshness:** sustained
**Feedback status:** ignored

**Evidence:** Bahamas: Foreign direct investment net inflows current USD moved up 538.6% from 2024 to 2025.
**Detail:** 538.6% change
**Grade:** B - cross-source

**Recommended action:** Screen Bahamas for investment readiness. FDI movement (538.6% change) is a screening trigger — cross-reference with sector conditions before deploying capital.
**Decision to influence:** Which country-sector pair to validate for investment readiness
**Routing rationale:** Single-source FDI movement is a screening trigger, not a deployment signal — start diligence

### 4. Suriname: FDI trending at +206.2% — screening trigger active

**ID:** `DSP-20261019-003` | **Country:** Suriname | **Confidence:** 🟡 Validation | 84/100 | B - cross-source
**Channel:** Email brief + Telegram | **Window:** 14 days | **Freshness:** sustained
**Feedback status:** ignored

**Evidence:** Suriname: Foreign direct investment net inflows current USD moved up 206.2% from 2024 to 2025.
**Detail:** 206.2% change
**Grade:** B - cross-source

**Recommended action:** Screen Suriname for investment readiness. FDI movement (206.2% change) is a screening trigger — cross-reference with sector conditions before deploying capital.
**Decision to influence:** Which country-sector pair to validate for investment readiness
**Routing rationale:** Single-source FDI movement is a screening trigger, not a deployment signal — start diligence

### 5. Eastern Caribbean Currency Union: 4.6%

**ID:** `DSP-20261019-021` | **Country:** Eastern Caribbean Currency Union | **Confidence:** 🟡 Validation | 72/100 | C - single-source
**Channel:** Email brief + Telegram | **Window:** 30 days | **Freshness:** sustained
**Feedback status:** ignored

**Evidence:** Total deposits growth: +4.6% YoY (threshold 3%); Private sector credit growth: +5.8% YoY (threshold 5%); Total deposits: EC$22,353.3M; Period: 2025 (YoY: +4.6%)
**Detail:** 4.6%
**Grade:** C - single-source

**Recommended action:** Review Eastern Caribbean Currency Union: 4.6%. Validate locally before action.
**Decision to influence:** Deposit base expansion = currency union stability = confidence signal
**Routing rationale:** Deposit growth = institutional confidence = favorable capital environment

### 6. St. Vincent and the Grenadines: economic stress indicators rising — portfolio review recommended

**ID:** `DSP-20261019-005` | **Country:** St. Vincent and the Grenadines | **Confidence:** 🟢 Monitor | 60/100 | C - single-source
**Channel:** Email brief + Telegram | **Window:** 30 days | **Freshness:** sustained
**Feedback status:** decision_changed

**Evidence:** St. Vincent and the Grenadines: Unemployment % is 18.00% (2025).
**Detail:** 18.00%
**Grade:** C - single-source

**Recommended action:** Assess portfolio exposure in St. Vincent and the Grenadines. Economic stress indicators (18.00%) may affect existing positions or timing.
**Decision to influence:** Risk assessment for capital exposure or policy attention
**Routing rationale:** Vulnerability signals change risk profiles — reassess exposure and timing
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
