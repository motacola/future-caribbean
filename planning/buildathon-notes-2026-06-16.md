# Future Caribbean Buildathon Notes — June 16, 2026

**Source:** Granola transcript of "The Next Wave: Future Caribbean Community Gathering #2"

---

## Initiative Overview

- **Future Caribbean**: Global agentic AI buildathon, open to teams at any stage
- **Core thesis**: Solutions built for complex, fragmented Caribbean markets can work anywhere
  - ~100M Caribbean people (50M diaspora, 50M in-region) as addressable base
  - Agentic AI as coordination layer across currencies, legal systems, languages, jurisdictions
- "Get Involved" page live and generating strong inbound from around the world
- Applications close **July 3**; final event: all-expenses trip to present at the **New York Stock Exchange**

---

## Partners and Advisors Joining

| Partner/Advisor | Role | Key Contribution |
|----------------|------|------------------|
| **High-Rise AI (Vince)** | Neo-cloud compute partner | H200 (Hopper-class Nvidia) GPUs via API; open-source coding model on High-Rise infra; 1B+ tokens/day total, tens of millions per team; acquired Impala AI for accelerated inference |
| **Bill** | Strategic advisor (40+ yrs tech, VC since 1991) | Brokered NYSE and High-Rise partnerships; referenced Canva origin story |
| **Cayman Enterprise City** | Financial sponsor | Incorporation support + 3-month incubator in Cayman |
| **Head of Venture at Citibank** | Advisor (signed yesterday) | Major financial institution validation |
| **$6B Singapore fund** | Advisor (joined yesterday) | Significant capital network |
| **Multiple VCs** | Advisors | $25M-$100M check sizes |
| **McGill University professor** | Advisor | Cancer technology research |
| **Barbadian aerospace engineer** | Advisor | Oxford/MIT PhD, Head of Science at major drone company; "I want to shape a region that shaped me" |
| **E (Lagos-based)** | Advisor & champion | Co-founded 2 African unicorns, Barbados part-time; "Today the Caribbean hosts global capital. There's no reason why it can't host global talent"; floated idea of registering AI agents as legal entities in the Caribbean |
| **Larry (Trinidad & Tobago)** | OG Caribbean AI builder | Building AI-native supply chain product with global inbound (African, Canadian, USD-denominated clients) |
| **Steve (Claw Camp)** | Global onboarding | clawcamp.global; SF event June 24 (veterans-to-entrepreneurs, 3M follower influencer) |
| **Mika (Grenada/Calgary)** | Advisor to teams | Drone and disaster-coordination expert |
| **Anya (Barbados)** | Community advisor | Flagged need to simplify language for broader local reach |

---

## Application Process

- Apply at any stage: pre-idea, MVP, or revenue-generating company
- **Requirement**: At least one verifiable prior build artifact (GitHub, demo, deployed URL, diagram, or flowchart)
- Teams can opt in to be matched with other teams (cross-region pairings already forming: China + Caribbean, India + Barbados)
- Applications in from 10+ countries including France; teams from China already submitted (frontier agentic finance architecture)
- Lily manually matching teams with advisors and on-the-ground banks (Jamaica, Caribbean) for early synergy calls
- **Encouraged frameworks**: OpenCall (agent coordination layer) and High-Rise GPU API

---

## Distribution Push Before July 3

- Press coverage live: Barbados Today, Dominica; interviews pending with Antigua, Trinidad
- WhatsApp channel: ~200 members; also active on Discord, Instagram, X
- Jamaica call: ~50 developers from local AI community (organized by Matthew Stone)
- Media kit built by community member: AI-generated social blurbs for X, Instagram, etc., one-click
- Productivity approach: Every call recorded, AI generates article, published to website and LinkedIn for transparency and SEO
- **Gaps flagged**: University pipelines, developer WhatsApp groups across islands, plain-language framing for non-technical Caribbean builders
- **In-person builder event**: July 10-12 in Barbados (travel sponsor covering accommodation)

---

## Next Steps (for Signal Fabric positioning)

1. **Submit application before July 3** — Signal Fabric qualifies (Signal Fabric is a deployed, verifiable artifact)
2. **Leverage High-Rise H200 compute** — The reasoning agent (`reasoners/synthesis.py`) already supports `LLM_BASE_URL` — point it at High-Rise inference for LLM synthesis instead of deterministic fallback
3. **Agent coordination layer** — OpenCall is explicitly encouraged; Signal Fabric's MCP adapter + HTTP toolset + `signalctl` CLI already form a multi-agent interface layer
4. **Validation packs as moat** — The `validation_pack_generator.py` produces pre-assembled diligence packs (sector hypotheses, procurement matches, intro targets, unresolved questions) — this is a differentiation vs. raw signal feeds
5. **Track record transparency** — The `track_record.py` packager publishes the desk's public track record (feedback provenance, priority adjustments) — aligns with buildathon's "AI generates article, publishes for transparency"
6. **Cross-region team matching** — Signal Fabric's domain registry (`domains/registry.py`) is a config-driven multi-instance engine — can spin up "buildathon team" instances as blueprint domains

---

## Strategic Implications for Signal Fabric

### Immediate (pre-July 3)
- [ ] Apply with Signal Fabric as the submission artifact (deployed API at `signal-fabric.vercel.app`, MCP adapter, CLI, deterministic query layer)
- [ ] Configure High-Rise H200 endpoint for reasoning agent LLM synthesis
- [ ] Document the "agent coordination layer" narrative — Signal Fabric IS an agent coordination layer (MCP + HTTP tools + OpenCall compatible)

### Moat Deepening (post-acceptance)
- [ ] **Agent-as-legal-entity** concept from advisor E → validation packs could include "agent registration readiness" scoring per Caribbean jurisdiction
- [ ] **Supply chain signals** from Larry's product → merge with `tenders_poller.py` and `tier2_scraper.py` (CDB procurement) for a dedicated supply chain signal kind
- [ ] **Disaster coordination** from Mika → integrate with NHC storm intelligence + NDBC buoy data for resilience routing
- [ ] **Plain-language layer** from Anya → add a "community brief" renderer alongside `telegram_brief.py` for non-technical audiences
- [ ] **University pipeline** gap → expose `signalctl` + MCP adapter as teaching tools; the deterministic query layer is auditable for coursework

### Compute & Infrastructure
- High-Rise provides: H200 GPUs via API, open-source coding model, 1B+ tokens/day
- Signal Fabric's reasoning agent (`reasoners/synthesis.py`) already has pluggable LLM config (`LLM_BASE_URL`, `LLM_API_KEY`, `LLM_MODEL`)
- Can run local Gemma 4 12B QAT on 8081 for deterministic fallback; High-Rise H200 for LLM synthesis cycles
- Pipeline runs on 4-hour cadence — fits within "tens of millions of tokens per team" budget easily

---

## Link to Transcript

https://notes.granola.ai/t/d7fe428f-f198-4d1a-84c0-169895b2f7c0-00demib2