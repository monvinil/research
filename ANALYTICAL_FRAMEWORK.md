# Analytical Framework — Macro-to-Micro Transmission & Research Edge

**Core thesis:** The edge isn't just where you look for data. It's what data you look at, what theoretical lens you apply, and how you model the causal chain from geopolitical shift → policy response → industry structure change → firm behavior → labor market effect → specific micro-level business opportunity. Most AI research skips from "macro observation" to "business idea" without modeling the transmission steps. This misses second-order effects (the most profitable opportunities), timing signals (which step in the chain are we at?), and counter-forces (what interrupts the chain?).

---

## Part 1: Classical Economic Theories as Analytical Weapons

Each theory below maps to specific data patterns the engine should detect. These aren't academic references — they're operational lenses that change what signals mean.

### T1: Schumpeterian Creative Destruction (Accelerated) + Christensen's Disruption Taxonomy

**Classic theory:** Innovation creates temporary monopoly → monopoly attracts imitators → prices fall → next innovation cycle. Destruction is how capitalism clears dead wood and reallocates resources to more productive uses.

**AI-era mutation:** The destruction cycle is compressing from decades to years. Intelligence costs dropped 1000x in ~2 years. Industries that normally had 20 years to adapt now have 2-5. This means:
- The "creative" part (new entrants with AI cost structures) is moving faster than the "destruction" part (incumbents exiting)
- There's a **gap period** where incumbents are dead but don't know it yet — still operating, still holding customers, but their cost structure is terminal
- This gap period IS the entry window for P2 (Liquidation Cascade)

**Christensen distinction (CRITICAL):** Not all AI adoption is disruptive. For each sector, classify:
- **Sustaining AI:** Makes incumbents better/faster (AI-enhanced Google, AI-assisted lawyers at BigLaw). Incumbents adopt and STRENGTHEN their position. Entry is hard.
- **Disruptive AI:** Makes incumbents obsolete — new entrants serve overshot or unserved markets at radically lower cost. Incumbents CAN'T adopt because it cannibalizes their business model.

**The test:** If AI makes the incumbent's core revenue model MORE profitable → sustaining (avoid). If AI destroys the incumbent's pricing power or serves customers they can't reach → disruptive (opportunity).

**What to scan for:** Industries where the Schumpeterian clock has accelerated but incumbents haven't acknowledged it. Measured by: rising labor costs + flat/falling revenue + no AI capex on 10-K → the gap period. When you see this combination, the cascade is 12-24 months away.

**Data signature:**
```
INCUMBENT DEATH SIGNAL:
  BLS wage growth for sector > CPI                      ✓ (costs rising)
  FRED industry revenue index flat or declining          ✓ (revenue not keeping up)
  EDGAR 10-K: no "artificial intelligence" in strategy   ✓ (not adapting)
  EDGAR 10-K: "restructuring charges" appearing          ✓ (trying to cut, not transform)
  → DIAGNOSIS: Schumpeterian gap period. 12-24mo window.

CHRISTENSEN CLASSIFICATION:
  Can incumbent adopt AI without cannibalizing revenue?
    YES → Sustaining innovation. Incumbent wins. AVOID entry.
    NO  → Disruptive innovation. Entry window exists.
  Does AI serve customers incumbents CAN'T serve profitably?
    YES → New-market disruption (Jevons expansion). LARGEST opportunity.
    NO  → Low-end disruption (cost competition only). Smaller window.
```

### T2: Ricardian Comparative Advantage (Applied to Firms, Not Nations)

**Classic theory:** Nations should specialize in what they produce at lowest opportunity cost, even if they're worse at everything in absolute terms.

**AI-era application:** Where does a 2-person agentic-first team have comparative advantage vs. a 500-person incumbent? Not in everything — in tasks where:
1. The marginal cost of intelligence is the dominant cost (not physical throughput, not regulatory compliance, not brand trust)
2. The incumbent's organizational overhead creates diseconomies of scale (coordination costs, management layers, office leases)
3. The output is standardizable enough that AI can produce it at near-zero marginal cost

**The inversion:** Large firms have absolute advantage in brand, relationships, regulatory capture. Small agentic teams have comparative advantage in cost structure. The Ricardian insight: it's not about being better at everything — it's about the *ratio* of cost differences. If a 500-person firm produces an audit for $50K (of which $45K is labor) and an agentic team produces the same audit for $5K (of which $500 is inference), the cost ratio is 10:1 for intelligence-heavy work but 1:1 for relationship/trust work. Enter the market at the intelligence-heavy end.

**What to scan for:** Industries where the dominant cost is human judgment/analysis (not physical labor, not brand, not regulation). These are where comparative advantage is most extreme.

**Data signature:**
```
COMPARATIVE ADVANTAGE MAP:
  BLS occupation data: % of role that is "analyze/evaluate/draft/review"
  vs. % that is "physical presence/relationship/regulatory compliance"

  HIGH comparative advantage: >70% analyze/evaluate → agentic cost kill
  MEDIUM: 40-70% → partial advantage, need human hybrid
  LOW: <40% → advantage exists but physical/regulatory floor dominates
```

### T3: Baumol's Cost Disease (The Cure AND The Premium)

**Classic theory:** In sectors where productivity doesn't easily increase (healthcare, education, legal, performing arts), costs rise over time because wages must keep up with productive sectors. A string quartet can't get more "productive" — it always needs 4 people and 40 minutes. But musicians' wages rise because they could work in manufacturing instead.

**AI-era application — TWO effects, not one:**

**Effect A — The Cure:** AI cures Baumol's disease for cognitive/routine services. Cost of legal research, medical coding, tax preparation collapses. These sectors have decades of stored potential energy for disruption. This is the REPLACEMENT opportunity.

**Effect B — The Premium:** As digital goods get cheaper (software, media, analysis), human-touch services become RELATIVELY more expensive and more valued. Nursing, therapy, artisanal crafts, live performance, personal coaching — these can't be automated (Polanyi's Paradox / T21) and their relative premium INCREASES. This is the PREMIUM opportunity.

**The split creates two business categories:**
- **Category A (Baumol Cure):** AI replaces expensive cognitive services at 10x lower cost. Target: routine-cognitive work. Build AI-first service businesses.
- **Category B (Baumol Premium):** Human-touch services become more valuable as digital collapses. Target: tacit-knowledge work. Build businesses that CERTIFY, CONNECT, or ENABLE premium human services.

**What to scan for:**
```
BAUMOL CURE CANDIDATES (Category A):
  FRED: sector-specific CPI component growing > headline CPI for 10+ years
    → Healthcare CPI: +4.5%/yr vs headline +2.5%/yr = 2% Baumol premium
    → Legal services CPI: +3.8%/yr vs headline +2.5%/yr = 1.3% Baumol premium
    → Education CPI: +4.2%/yr vs headline +2.5%/yr = 1.7% Baumol premium

  COMBINED WITH:
  BLS: >60% of sector employment is cognitive/analytical work

  → DIAGNOSIS: Baumol cure candidate. Stored potential energy =
    (years of above-inflation growth) × (Baumol premium) × (sector size).
    The longer the disease, the bigger the cure opportunity.

BAUMOL PREMIUM CANDIDATES (Category B):
  Sectors where the work is fundamentally HUMAN (tacit knowledge, physical presence,
  empathy, trust, craft):
    → Therapy/counseling, skilled trades, artisanal food, personal training,
      elder care, live entertainment, luxury personal services

  AS DIGITAL COSTS COLLAPSE:
    → Relative value of human-touch services INCREASES
    → Willingness-to-pay for "verified human" premium rises
    → Business models: certification, marketplace, enablement platform
    → NOT AI-replacement — AI-AUGMENTED human premium

  → DIAGNOSIS: Baumol premium candidate. Opportunity =
    (digital cost collapse in adjacent sectors) × (human premium elasticity) × (market size)
```

### T4: Minsky's Financial Instability Hypothesis

**Classic theory:** Stability breeds instability. In stable periods, agents take on more risk (hedge → speculative → Ponzi financing). The system appears robust until a small shock triggers cascading failures.

**AI-era application:** PE roll-ups in professional services were the "stability" phase. Roll-up operators borrowed to consolidate fragmented industries, expecting predictable cash flows from recurring revenue. This was stable until AI created a cost-structure shock. Now:
- The roll-up's debt load (acquired at stable-era multiples) meets AI-era margin compression
- The roll-up can't restructure because the debt service requires the revenue that AI entrants are taking
- The Minsky moment: the roll-up thesis itself becomes the vulnerability

**This extends beyond PE.** Any industry where financial engineering (leverage, roll-ups, sale-leaseback) assumed stable cost structures is now a Minsky candidate.

**What to scan for:**
```
MINSKY MOMENT CANDIDATES:
  EDGAR: Companies with debt/EBITDA > 4x AND declining revenue
  EDGAR: PE-backed companies reporting "margin pressure" or "competitive dynamics"
  Web: PE roll-up announcements in industries facing AI disruption
    → Roll-up is Minsky's "speculative financing" phase
    → AI cost disruption is the trigger event
    → Cascade = forced asset sales at distressed prices = P2 entry window
```

### T5: Carlota Perez — Technological Revolutions & Financial Capital (replaces Kondratieff)

**Classic theory (Perez, 2002):** Technological revolutions follow a predictable two-phase pattern:

**Installation Phase** (we are HERE):
- Wild speculation, massive infrastructure buildout, financial bubbles
- Capital floods into the new technology's infrastructure layer
- Real economy transformation is minimal — mostly hype and financial engineering
- Ends with a CRASH (the "Turning Point") — dot-com bust, railway mania bust, etc.

**Deployment Phase** (NEXT):
- Post-crash: regulation increases, capital becomes more patient
- Real productivity transformation begins — the technology actually changes industries
- "Golden age" of broad economic growth based on the new technology
- Lasts 20-30 years

**The five surges:** Canal mania → Railway mania → Steel/electricity → Oil/auto/mass production → ICT/Internet → **AI (current)**

**AI-era application — where we are:**
- Massive GPU/datacenter capex = classic Installation overinvestment
- AI valuations detached from revenue = Installation-phase financial speculation
- Real-economy AI adoption is shallow (chatbots, copilots) = Installation, not Deployment
- **PREDICTION: A "Turning Point" crash is likely before AI transforms the physical economy**

**What this means for business model construction:**
- Infrastructure plays (more GPUs, more training, more cloud) are LATE in the Installation Phase — risky
- Application-layer plays that transform physical operations are EARLY in the Deployment Phase — high potential but may need to survive the crash
- **Crash-resilient businesses** (low burn, revenue-generating, physical-economy impact) are the best positioned
- Businesses that CONSUME overbuilt infrastructure at post-crash prices capture disproportionate value

**What to scan for:**
```
PEREZ INSTALLATION → DEPLOYMENT TRANSITION:
  Industry capex in AI infra: still rising but decelerating
  Inference cost curves: dropping faster than demand grows
  AI startup failures: increasing (shakeout beginning)
  Startup funding: shifting from "AI infrastructure" to "AI applications"
  Regulation increasing: AI safety, EU AI Act, sector-specific rules
  → Signs of approaching Turning Point

CRASH RESILIENCE CHECK (for every opportunity):
  Can this business survive a 12-18 month funding freeze?
  Does it generate revenue within 6-12 months?
  Is burn rate sustainable without follow-on funding?
  Does it serve the physical economy (not just digital)?
  → Crash-resilient businesses = highest conviction in Installation → Deployment transition

POST-CRASH DEPLOYMENT OPPORTUNITIES:
  Sectors where AI adoption is shallow (chatbots only, no operational change)
  Industries where physical operations haven't been touched by AI yet
  → These are Deployment Phase businesses — the real transformation
```

### T6: Jevons Paradox (Demand Expansion)

**Classic theory:** When a technological improvement increases the efficiency of resource use, the demand for that resource can increase rather than decrease. Jevons observed this with coal — more efficient steam engines led to MORE coal consumption, not less.

**AI-era application:** As AI makes professional services cheaper, demand won't stay constant — it expands. Markets that couldn't afford $500/hr legal advice WILL buy $50/hr AI legal advice. Small businesses that couldn't afford a CFO WILL buy $200/mo agentic finance.

**The insight:** TAM calculations based on current market size are wrong. The real TAM includes latent demand that was priced out at incumbent cost structures. P3 (Output Cost Kill) isn't just about stealing incumbent revenue at lower cost — it's about expanding the addressable market by 5-10x.

**What to scan for:**
```
JEVONS EXPANSION CANDIDATES:
  Industries where:
    Current penetration < 30% of potential customers
    Primary barrier to adoption = PRICE (not awareness, not regulation)
    10x cost reduction would unlock new customer segments

  Example: Only ~30% of US small businesses use a CPA.
  70% do their own taxes/books because CPA costs $200-500/hr.
  At $20-50/hr equivalent (agentic), penetration could reach 70-80%.
  → TAM is not "steal CPAs' clients." TAM is "serve the 70% who
     couldn't afford a CPA."
```

### T7: Gresham's Law (Adapted — Labor Version)

**Classic theory:** "Bad money drives out good" — when two currencies circulate, the overvalued one is spent while the undervalued one is hoarded.

**AI-era adaptation:** Cheap AI labor drives out expensive human labor in commodity tasks. But this CONCENTRATES human labor in judgment-intensive, relationship-heavy, high-trust roles where it's more valuable. Gresham's in reverse: "good labor" (human judgment) becomes MORE valuable as "bad labor" (routine cognitive work) is replaced by AI.

**The insight:** The opportunity isn't only replacing humans with AI. It's ALSO building businesses around the newly concentrated, higher-value human work. When AI handles 80% of a CPA's tasks, the remaining 20% (complex judgment, client trust, regulatory navigation) becomes more scarce and valuable.

**What to scan for:**
```
GRESHAM LABOR CONCENTRATION:
  Roles where routine cognitive tasks are >60% of time
  → AI replaces the routine, concentrates humans in judgment
  → Business model: AI does the 80%, human does the 20% at premium
  → Cost: 80% × inference cost + 20% × (higher) human rate
  → This beats the incumbent's 100% × human rate when routine tasks
     are the majority of the cost
```

### T8: Demographic Transition Theory (Labor Supply Curves)

**Classic theory:** Populations move through stages: high birth/death → low death/high birth → low birth/death → aging. Each stage has different labor dynamics.

**Application:** Japan (stage 5 — declining population) is the leading indicator. What Japan adopts for its aging workforce, the US needs in 5-10 years, and Europe in 3-7. LATAM is at stage 3-4 (younger, growing workforce) — different opportunities.

**The insight:** This isn't just "aging population = opportunity." It's about modeling specific labor supply curves for specific occupations in specific geographies, and finding where the supply curve goes to zero.

**What to scan for:**
```
DEMOGRAPHIC SUPPLY COLLAPSE:
  BLS: Average age of practitioners in occupation > 55
  BLS: New entrants per year < retirements per year
  COMBINED WITH: No viable immigration pipeline for this role

  → Labor supply curve approaches zero in 5-10 years
  → AI doesn't need to be BETTER than humans — just AVAILABLE
  → Regulatory posture: filling gaps = tailwind, replacing workers = headwind

  Track Japan's solutions — they preview US/EU needs by 5-10 years.
```

### T9: Resource Curse / Dutch Disease (Applied to AI Talent)

**Classic theory:** Countries that discover a windfall resource often see other sectors atrophy because capital and talent flow to the resource sector, making other sectors less competitive.

**AI-era application:** The AI infrastructure "gold rush" (GPU companies, model training, cloud infra) is absorbing engineering talent and venture capital that would otherwise go to application-layer businesses. This creates a talent/capital vacuum in the application layer.

**The insight:** The application layer is LESS competitive than it should be because the best talent is building infrastructure. This won't last — infrastructure matures, talent migrates to applications. But RIGHT NOW, the resource curse means application-layer businesses face less competition from talent than expected.

**What to scan for:**
```
AI TALENT DUTCH DISEASE:
  LinkedIn/job boards: ratio of "AI infrastructure" roles to
    "AI application" roles in same industry
  If infrastructure roles > 3x application roles → talent vacuum

  Startup funding: ratio of infra-layer to app-layer investment
  If infra > 5x app → capital vacuum at app layer

  → Application-layer businesses built now face less talent competition
  → This advantage is temporary (2-4 years) — move during the window
```

### T10: Transaction Cost Economics (Coase/Williamson)

**Classic theory:** Firms exist because market transactions have costs (finding suppliers, negotiating contracts, enforcing agreements). When transaction costs are high, it's cheaper to do things in-house. When transaction costs drop, firms shrink and markets expand.

**AI-era application:** AI collapses transaction costs for cognitive work. When it cost $200/hr to hire a specialist for an hour, you'd hire a full-time employee instead (firm boundary expands). When it costs $2/hr equivalent in AI, the firm boundary contracts. This means:
- Large firms lose their organizational advantage (they existed to internalize high-cost transactions)
- Small firms/solo operators can access specialist capabilities via AI at near-zero transaction cost
- The optimal firm size SHRINKS in cognitive-intensive industries

**The insight:** The Coasean prediction for AI: **average firm size in cognitive industries will decrease.** The businesses worth building are the ones that serve the new, smaller firms — or that ARE the new, smaller firms with AI replacing what used to require 50 employees.

**What to scan for:**
```
COASEAN FIRM SHRINKAGE:
  BLS: Rising share of firms with <10 employees in a sector
  Census: Sole proprietorship growth rate by industry
  EDGAR: Large firms reporting "outsourcing" or "contractor" increases

  → Industries where firm size is shrinking = Coase in action
  → Opportunity: serve the new small firms, or BE the new small firm
```

---

## Part 2: The Macro-to-Micro Transmission Chain

The engine currently skips from "geopolitical observation" to "opportunity." The missing piece is a formal transmission model.

### Transmission Chain Model

Every macro shift propagates through 6 nodes before creating a micro-level business opportunity:

```
NODE 1: GEOPOLITICAL/MACRO SHIFT
  │  (observable: policy announcements, trade data, conflict events)
  ▼
NODE 2: POLICY RESPONSE
  │  (observable: tariffs, regulations, subsidies, sanctions)
  ▼
NODE 3: INDUSTRY STRUCTURE CHANGE
  │  (observable: supply chain shifts, cost curve changes, new competition)
  ▼
NODE 4: FIRM BEHAVIOR
  │  (observable: entry/exit, restructuring, M&A, hiring/firing)
  ▼
NODE 5: LABOR MARKET EFFECT
  │  (observable: wage changes, vacancy rates, skill shortages)
  ▼
NODE 6: MICRO OPPORTUNITY
  │  (derived: specific business, geography, timing, entry strategy)
  ▼
VALIDATION: Does this pass P1-P6? Unit economics? Founding constraints?
```

### How to Use the Chain

**For each active geopolitical/macro force, model the full chain:**

Example — US-China Chip Export Controls:
```
N1: SHIFT — US restricts advanced chip exports to China (Oct 2022, expanded 2024-2025)
N2: POLICY — CHIPS Act subsidies ($52B domestic fabs), entity list expansions
N3: STRUCTURE — Bifurcated compute supply. US-bloc inference costs dropping (competition).
    China-bloc inference costs rising (restricted hardware). Reshoring demand spike.
N4: FIRMS — US cloud providers expanding capacity (infra overhang). Chinese firms
    building parallel ecosystem (less efficient). US manufacturers reshoring =
    new compliance/coordination burden.
N5: LABOR — Engineering talent concentrated in fabs (Dutch Disease/T9). Reshored
    manufacturing needs local compliance staff that doesn't exist yet.
N6: OPPORTUNITY — Agentic compliance/coordination for reshored manufacturers.
    They need it, can't hire for it, will pay for AI that handles it.
    → Passes: P1 (infra overhang), P3 (cost kill vs. hiring), P5 (demographic gap),
      P6 (geopolitical tailwind)
```

**The engine should maintain a chain for each major macro force**, tracking which node each chain has reached. The opportunity materializes when the chain reaches nodes 4-5. If the chain stalls at node 2 (policy announced but not implemented) or node 3 (structure didn't change as expected), the opportunity should be PARKED or KILLED.

### Chain Tracking Format

```json
{
  "chain_id": "TC-001",
  "macro_force": "US-China chip export controls",
  "theoretical_lenses": ["T5-Kondratieff", "T9-Dutch-Disease"],
  "nodes": [
    {
      "node": 1,
      "status": "confirmed",
      "evidence": "Export controls expanded 3x since 2022",
      "data_source": "Commerce BIS entity list"
    },
    {
      "node": 2,
      "status": "confirmed",
      "evidence": "CHIPS Act funded, $52B allocated",
      "data_source": "Federal budget data"
    },
    {
      "node": 3,
      "status": "confirmed",
      "evidence": "Inference costs diverging between blocs. US down 1000x, China estimated 3-5x less reduction.",
      "data_source": "Cloud pricing data + industry estimates"
    },
    {
      "node": 4,
      "status": "emerging",
      "evidence": "TSMC Arizona fab under construction. Intel foundry expanding. But reshoring actual production is 2-3 years out.",
      "data_source": "EDGAR 10-K, news"
    },
    {
      "node": 5,
      "status": "not_yet",
      "evidence": "Reshoring labor demand hasn't materialized at scale yet.",
      "data_source": "BLS"
    },
    {
      "node": 6,
      "status": "not_yet",
      "derived_opportunity": "Agentic compliance for reshored manufacturers",
      "timing": "H2 (3-5 years) — chain hasn't reached node 5 yet"
    }
  ],
  "chain_velocity": "moderate — moving through nodes but node 4→5 is slow",
  "counter_forces": [
    "China developing domestic alternatives faster than expected",
    "Reshoring may concentrate in chips only, not broader manufacturing"
  ],
  "last_updated": "cycle 6"
}
```

### Chains to Model Immediately

| Macro Force | Expected Chain | Current Node | Theoretical Lens |
|-------------|---------------|--------------|-----------------|
| US-China chip controls | Controls → reshoring → labor gap → agentic compliance | Node 3-4 | T5, T9 |
| AI inference cost collapse | Overinvestment → overhang → app layer viability → firm size shrinkage | Node 3-4 | T5, T6, T10 |
| Professional services cascade | Credit squeeze → margin compression → exits → asset availability | Node 4-5 | T1, T4, T7 |
| Healthcare demographic gap | Aging population → nursing shortage → ratio pressure → AI augmentation | Node 4-5 | T3, T8 |
| LATAM nearshoring | China decoupling → supply chain diversification → LATAM manufacturing growth → services demand | Node 2-3 | T2, T6 |
| Interest rate environment | High rates → low-burn advantage → incumbents leveraged → agentic-first capital efficiency | Node 4 | T4 |
| PE roll-up disruption | AI cost compression → roll-up margin decline → debt stress → forced exits | Node 3-4 | T4, T1 |
| Japan aging (leading indicator) | Population decline → service automation adoption → pattern preview for US/EU | Node 4-5 | T3, T8 |

---

## Part 3: The Analytical Edge — What Data and How to Look

### Principle: Data Has Three Layers

Most research reads data at face value (Layer 1). The edge comes from Layers 2 and 3.

**Layer 1: What the data says (everyone sees this)**
- "Professional services employment fell 97K YoY"
- "Chapter 11 filings up 76%"
- "Inference costs dropped 1000x"

**Layer 2: What the data means in context of transmission chains (few see this)**
- "Professional services employment fell 97K YoY" + "Credit availability fell $55B" + "No AI capex on 10-Ks" = Schumpeterian gap period at node 4, cascade is 12-24mo from peak distress. The credit squeeze prevents restructuring (Minsky), so the exit rate will accelerate not stabilize.

**Layer 3: What the data implies about timing and positioning (almost no one sees this)**
- The bond market (HY spread 2.87%) hasn't priced the cascade. This is the "Minsky moment hasn't been recognized" signal. When HY spreads widen for professional services specifically, the window is closing because distressed assets get bid up. Entry timing: NOW, while bond markets still think this sector is stable.
- Jevons Paradox: the 70% of small businesses that don't use CPAs become the real TAM at 10x lower cost. The opportunity isn't competing for existing CPA clients — it's serving the unsserved.

### How to Look: Analytical Methods

**1. Divergence Analysis**
Don't look at single indicators. Look for DIVERGENCES between indicators that should move together:
- Employment falling + wages rising = structural shortage (P5), not recession
- Bankruptcies rising + HY spreads tight = market hasn't priced the cascade (timing window)
- AI capex rising + application revenue flat = Kondratieff transition (P1 overhang forming)

**2. Velocity Tracking**
Track rate of change, not just levels. A signal at level 7 that was at 5 last cycle is more important than a signal that's been at 8 for 3 cycles. The engine should track first derivatives of key metrics.

**3. Cross-Geography Leading Indicators**
Japan's demographic solutions preview US needs by 5-10 years. Argentina's professional services market (weaker incumbents) previews what happens when cost compression hits harder. Use cross-geography comparison as a time machine.

**4. Contra-Indicator Discipline**
For every supporting signal, actively search for the most compelling counter-argument. The engine should maintain a "bull case" and "bear case" for every opportunity, with the bear case given equal analytical rigor. If you can't articulate a strong bear case, you don't understand the opportunity well enough.

**5. Threshold Analysis**
Every opportunity has specific quantitative thresholds where it flips from non-viable to viable:
- "At inference cost < $X per 1M tokens, this opportunity's unit economics work"
- "When this industry's bankruptcy rate exceeds Y%, acquisition prices drop to Z"
- "When nursing vacancy rate hits W% in state S, regulatory pressure forces AI acceptance"

Track proximity to these thresholds. When a threshold is approached, the signal urgency increases.

### Data Source Upgrade Priority (What to Add)

**Highest edge (addresses Layer 2-3 analysis):**

| Source | What It Measures | Transmission Node | Theory |
|--------|-----------------|-------------------|--------|
| PACER/bankruptcy data | Actual firm exits by industry | Node 4 (firm behavior) | T1, T4 |
| BizBuySell/DealStream | Real acquisition prices | Node 4 (firm behavior) | T2 |
| Reddit/HN practitioner sentiment | Pre-BLS labor signals | Node 5 (labor market) | Leading indicator |
| State licensing board data | License supply/demand | Node 5 (labor market) | T3, T8 |
| Japan METI reports | Leading indicator for US/EU | Cross-geography | T8 |
| Cloud provider pricing (tracked weekly) | Inference cost trajectory | Node 3 (structure) | T5, T6 |

**Medium edge:**

| Source | Why |
|--------|-----|
| Crunchbase failure database | P4 dead business revival — what failed at old cost curves |
| PE deal announcements (PitchBook) | Minsky phase detection — which sectors are in speculative financing |
| Census business dynamics | Coasean firm shrinkage — are firm sizes changing? |

---

## Part 4: Integration Into Agent Architecture

### Agent A: Add Transmission Chain Scanning

Agent A currently scans for signals matching P1-P6. Add:
- For each active transmission chain, scan for evidence at the NEXT expected node
- Flag when a chain advances or stalls
- Produce counter-signals for chains that might be interrupted

### Agent C: Add Chain Tracking

Agent C currently grades individual signals. Add:
- Map signals to transmission chains
- Track chain velocity (how fast are nodes progressing?)
- Flag chains approaching node 4-5 (opportunity materializing)
- Flag chains that stalled (opportunity not materializing — park or kill)

### Agent B: Add Theoretical Stress Tests

Agent B currently does V1-V8 verification. Add:
- **V9: Theoretical Consistency** — which economic theories support this opportunity? Which contradict it?
- **Jevons check:** Is TAM calculated at current market size, or does it account for demand expansion at lower cost?
- **Coase check:** Does this opportunity align with or fight the direction of optimal firm size change?
- **Minsky check:** Is the incumbent's vulnerability structural (their entire financing model is wrong) or cyclical (they'll recover)?

### Master: Add Chain Synthesis

Master currently synthesizes signals. Add:
- Maintain the full set of transmission chains
- Compare chain velocities — which macro forces are translating fastest?
- Identify chain intersections (when two chains converge on the same micro opportunity, priority increases)
- Derive timing from chain position: node 2-3 = H3 opportunity, node 4 = H2, node 5 = H1

---

## Part 5: Summary — Where the Hidden Edge Lives

The hidden edge is not in having better data sources. Everyone has access to FRED, BLS, EDGAR.

The edge is in:

1. **Theoretical lens.** Applying Schumpeter, Minsky, Baumol, Jevons, Coase, and Kondratieff to interpret the same data everyone else sees, but drawing different conclusions. When others see "professional services decline," the engine sees "Schumpeterian gap period at node 4, Minsky moment approaching, Baumol cure creating 5x TAM expansion via Jevons."

2. **Transmission chain modeling.** Knowing that a geopolitical shift takes 6 steps to become a micro opportunity, and tracking exactly which step each shift has reached. This gives timing precision that "scan and grade" approaches lack.

3. **Divergence detection.** Looking for indicators that SHOULD move together but aren't — these divergences are where the market is mispricing, and where entry windows exist.

4. **Layer 2-3 analysis.** Reading data not for what it says (everyone does this) but for what it means in the context of chains and theories, and what it implies about timing and positioning.

5. **Counter-force discipline.** Maintaining bear cases with equal rigor to bull cases. The kill index isn't just for filtering — it's for building institutional knowledge about what interrupts transmission chains.

---

## Part 6: Extended Economic Theories (T11–T20)

These ten additional frameworks expand the engine's analytical repertoire beyond the founding ten theories. Each adds a distinct lens that catches opportunities and risks the original ten miss.

### T11: Regulatory Capture Theory (Stigler)

**Classic theory:** Industries capture the regulators meant to oversee them, using regulation as a barrier to entry rather than consumer protection. Licensing requirements, compliance costs, and lobbying create moats around incumbents.

**AI-era application:** Regulatory capture is a DOUBLE-EDGED signal:
- **As barrier:** Captured industries (healthcare, legal, financial services) have regulatory moats that slow AI entrants. First-movers who navigate the regulatory maze lock out followers.
- **As opportunity:** When regulators face a crisis (labor shortage, cost explosion), capture weakens. Nursing shortages → states allow expanded scope of practice → AI augmentation gets regulatory tailwind.

**What to scan for:**
```
REGULATORY CAPTURE SIGNALS:
  Lobbying spend by industry association + position on AI regulation
  State/federal licensing rule changes (loosening = window opening)
  "Regulatory sandbox" announcements (explicit permission to innovate)
  Legal challenges to licensing requirements (Teladoc-style precedent)

  → Capture WEAKENING + labor shortage = fastest entry window
  → Capture STRENGTHENING = moat for first-movers already inside
```

### T12: Game Theory / Nash Equilibrium Dynamics

**Classic theory:** Rational actors reach equilibria where no player benefits from unilateral change. Markets can get stuck in suboptimal equilibria when switching requires coordinated action.

**AI-era application:** Many industries are stuck in a "nobody moves first" equilibrium:
- Law firms won't adopt AI because clients expect human lawyers. Clients won't demand AI because firms don't offer it. The equilibrium breaks when ONE firm defects (offers AI at 5x lower cost) and wins clients. Then ALL firms must follow.
- The defection moment is the opportunity window. Scan for the FIRST defector in each industry.

**What to scan for:**
```
NASH EQUILIBRIUM BREAK:
  First incumbent to publicly adopt AI-first model in a sector
  First client to publicly switch to AI-first provider
  Industry conference panels debating "should we use AI?"
    (debate = pre-defection, consensus = post-defection)
  → The window is between first defection and equilibrium shift
```

### T13: Principal-Agent Theory (Jensen & Meckling)

**Classic theory:** When agents (managers, employees) have different incentives than principals (owners, shareholders), costly monitoring and misalignment result. Agency costs are a significant share of organizational overhead.

**AI-era application:** AI collapses agency costs in two ways:
1. **AI as perfect agent:** AI agents have zero agency costs — they don't shirk, don't empire-build, don't need monitoring. This eliminates middle management in information-processing hierarchies.
2. **AI as monitoring tool:** AI can monitor compliance, quality, and performance at near-zero cost, reducing agency costs for remaining human workers.

**What to scan for:**
```
AGENCY COST COLLAPSE:
  Industries with deep management hierarchies (>5 layers)
  Sectors where "oversight" and "quality assurance" are major cost lines
  Companies reporting "span of control" changes (managers overseeing more)
  → High agency cost sectors = biggest margin improvement from AI
  → Middle management layers = most directly displaced
```

### T14: Prospect Theory (Kahneman & Tversky)

**Classic theory:** People overweight losses relative to gains (loss aversion), evaluate outcomes relative to reference points, and have diminishing sensitivity to larger changes.

**AI-era application for customer acquisition:** Understanding prospect theory predicts which customers switch to AI and which resist:
- **Loss aversion:** Customers won't switch if they perceive risk of LOSING current quality, even if expected value is higher. Frame as "keep everything + save 80%" not "replace your accountant."
- **Reference point:** Customers anchored to $500/hr expect premium. Customers anchored to "I can't afford this at all" have no switching friction — they're pure acquisition.
- **Status quo bias:** Existing relationships create inertia. Target the UNSERVED (no status quo to defend) before the served.

**What to scan for:**
```
BEHAVIORAL SWITCHING SIGNALS:
  Customer satisfaction + switching cost surveys by industry
  Industries where >50% of target market is currently UNSERVED
  Sectors where trust/relationship is the primary purchase driver
    (high switching friction) vs. commodity (low friction)
  → Unserved markets + commodity perception = fastest adoption
  → High-trust + served markets = slowest adoption (PARK or acquire)
```

### T15: Minsky Extended — The Refinancing Wall

**Classic theory (extended):** Beyond the instability hypothesis (T4), the specific mechanism of the refinancing wall. Companies and PE funds that took on debt at low rates face refinancing at higher rates, creating a wave of distress.

**AI-era application:** The 2020-2021 low-rate borrowing cohort faces refinancing in 2025-2027. This is SIMULTANEOUS with AI margin compression. The double squeeze:
- Revenue declining (AI competition on price)
- Debt service increasing (higher refinancing rates)
- No equity market exit (IPO window narrow for traditional businesses)

**What to scan for:**
```
REFINANCING WALL + AI SQUEEZE:
  FRED: Corporate debt maturity schedule (BOGZ1FL series)
  EDGAR: Companies with >40% of debt maturing in 12-24mo
  FRED: HY spread trajectory (widening = distress approaching)
  Combined with: AI cost compression in same sector
  → Double squeeze = accelerated liquidation = P2 asset opportunity
```

### T16: Resource-Based View (Barney)

**Classic theory:** Sustained competitive advantage comes from resources that are Valuable, Rare, Inimitable, and Non-substitutable (VRIN). Strategy should be built around defending and exploiting these resources.

**AI-era application:** AI reshuffles which resources are VRIN:
- **No longer rare:** Information processing, pattern recognition, content generation, code writing
- **Newly rare:** Proprietary training data, regulatory licenses, physical infrastructure, trust/brand in AI-skeptical markets, domain-specific fine-tuned models
- **Still rare:** Human judgment in novel situations, physical presence, relationship networks, regulatory capture

**What to scan for:**
```
VRIN RESOURCE SHIFT:
  Industries where the primary competitive resource was human expertise
    (being de-VRIN'd by AI — competitive advantage eroding)
  Industries where proprietary data is the scarce resource
    (competitive advantage INCREASING — data moat)
  Sectors where trust/brand matters more than cost
    (AI adoption slower, but first-mover with trust = durable moat)
```

### T17: Institutional Theory (DiMaggio & Powell)

**Classic theory:** Organizations become similar (isomorphic) through coercive pressure (regulation), mimetic pressure (copying successful peers), and normative pressure (professional standards). Industries self-standardize.

**AI-era application:** Institutional isomorphism explains why incumbents move slowly AND why they'll eventually all move at once:
- **Mimetic:** No firm wants to be first to adopt AI (risk). But once a peer succeeds, ALL adopt rapidly (herd behavior).
- **Coercive:** When regulators mandate AI reporting, compliance costs, or capabilities, the entire industry must move.
- **Normative:** Professional associations setting AI competency standards create a tipping point.

**What to scan for:**
```
INSTITUTIONAL TIPPING POINT:
  Professional association AI policy statements
  First major firm in sector publicly committing to AI-first
  Regulatory mandates requiring AI capabilities
  → Pre-tipping = opportunity window for entrants
  → Post-tipping = incumbents flood in, competition intensifies
  → TIMING: Enter BEFORE the institutional tipping point
```

### T18: Real Options Theory

**Classic theory:** Business decisions under uncertainty are options, not commitments. The value of waiting can exceed the value of acting, especially when investments are irreversible and uncertainty is high.

**AI-era application:** Real options theory explains optimal entry timing:
- **High uncertainty + irreversible investment = wait.** Don't build a $10M platform when the model landscape changes quarterly.
- **Low investment + reversible = act now.** Agentic-first businesses with $500K seed and minimal infrastructure have low option value to waiting — act now, pivot cheap.
- **Declining uncertainty = window closing.** As AI capabilities stabilize, the option value of waiting drops and the cost of delay rises.

**What to scan for:**
```
REAL OPTIONS TIMING:
  Sectors where AI capability uncertainty is DECREASING (models stabilizing)
  → Option value of waiting drops → enter NOW
  Sectors where required investment is HIGH and irreversible
  → Option value of waiting still high → PARK until clearer
  Track model capability benchmarks — stabilizing scores = declining uncertainty
```

### T19: Attention Economics (Simon / Davenport)

**Classic theory:** In an information-rich world, the scarce resource is attention, not information. Wealth flows to those who can capture and direct attention effectively.

**AI-era application:** AI generates unlimited content but human attention remains fixed at ~16 waking hours/day. This creates:
- **Content flood → attention scarcity:** Every business can now produce infinite content. Differentiation shifts from content production to attention capture and trust.
- **Curation premium:** The value of filtering, summarizing, and prioritizing increases as content volume explodes.
- **Decision fatigue:** More AI-generated options = more paralysis. Businesses that REDUCE choices (opinionated, curated) win over businesses that EXPAND choices.

**What to scan for:**
```
ATTENTION SCARCITY SIGNALS:
  Declining engagement rates on AI-generated content
  Rising premium for "verified human" or "expert curated" labels
  Industries where decision complexity is paralyzing customers
  → Build AI that REDUCES cognitive load, not increases options
  → Curation/recommendation businesses have counter-cyclical advantage
```

### T20: Complexity Economics (Arthur / Santa Fe Institute)

**Classic theory:** Economies are complex adaptive systems, not equilibrium machines. Small perturbations can cascade into large effects. Positive feedback loops create winner-take-all dynamics. Path dependence locks in early outcomes.

**AI-era application:** AI creates multiple positive feedback loops simultaneously:
- **Data flywheel:** More users → more data → better model → more users
- **Cost flywheel:** More volume → lower per-unit cost → lower price → more volume
- **Talent flywheel:** Better product → attracts talent → better product
- **Ecosystem lock-in:** Early integrations → switching costs → defensibility

**What to scan for:**
```
COMPLEXITY / FEEDBACK LOOP SIGNALS:
  Sectors where data flywheel is POSSIBLE but NO ONE has started it
  Markets with strong network effects that AI could activate
  Industries where the first AI entrant creates switching costs
  → Positive feedback loops = winner-take-all = first-mover critical
  → If loops already spinning for a competitor = avoid or differentiate
```

### T21: Polanyi's Paradox — The Automation Boundary (Autor)

**Classic theory (Polanyi, 1966 / Autor, 2014):** "We know more than we can tell." Tacit knowledge — skills we have but can't articulate as explicit rules — defines the boundary of what can be automated. If you can't codify it, you can't automate it.

**Autor's extension:** This creates a "Barbell Economy":
- **Routine cognitive** tasks (data entry, bookkeeping, basic analysis, code generation, document review) → fully automatable. The MIDDLE collapses.
- **Non-routine manual** tasks (plumbing, surgery, eldercare, carpentry) → hard to automate (requires physical dexterity + tacit spatial reasoning). Value INCREASES.
- **Non-routine cognitive** tasks (strategic judgment, negotiation, empathy, creative direction, novel problem-solving) → hard to automate (requires tacit social/creative intelligence). Value INCREASES.

**AI-era application — the work classification system:**

For EVERY sector the engine analyzes, classify the work:

```
POLANYI WORK CLASSIFICATION:

ROUTINE COGNITIVE (automatable — AI cost kill):
  → Data processing, form filling, standard analysis, report generation,
    pattern matching, code generation, document review, scheduling,
    basic customer service, standard legal research, medical coding
  → BUSINESS MODEL: AI replaces this work at 10x lower cost
  → This is where Baumol Cure (T3 Category A) applies

TACIT MANUAL (NOT automatable — premium increases):
  → Plumbing, electrical, surgery, physical therapy, eldercare,
    construction, cooking, haircutting, massage, equipment repair
  → BUSINESS MODEL: Enable/certify/connect these workers (marketplace,
    training, tools). Their premium RISES as routine work collapses.
  → This is where Baumol Premium (T3 Category B) applies

TACIT COGNITIVE (NOT automatable — judgment premium):
  → Strategic consulting, complex negotiation, creative direction,
    novel R&D, empathy-driven therapy, leadership, crisis management,
    high-stakes decision-making under ambiguity
  → BUSINESS MODEL: AI provides prediction (T22), human provides judgment.
    Build AI+human hybrid services where the human judgment is the premium.
  → This is where AGG Prediction Machines (T22) applies
```

**The Barbell prediction for business construction:**
- **The collapsing middle** = massive AI-replacement opportunity (routine cognitive). Build here for volume.
- **The rising ends** = human premium opportunity (tacit manual + tacit cognitive). Build here for margin.
- **The trap** = building AI for tacit work that AI can't actually do. Polanyi prevents this.

**What to scan for:**
```
POLANYI BOUNDARY SIGNALS:
  O*NET: Task composition of occupations (% routine vs. non-routine)
  BLS: Wage growth by occupation type (routine declining, tacit rising)
  AI benchmark data: Error rates on tacit vs routine tasks
  Job posting trends: "Human required" language increasing in certain roles

  For each sector:
    % routine cognitive → size of AI-replacement opportunity
    % tacit manual → size of human-premium opportunity
    % tacit cognitive → size of judgment-hybrid opportunity

  → THREE different business models per sector, not one
```

### T22: Prediction Machines — The Complement Principle (Agrawal, Gans, Goldfarb)

**Classic theory (AGG, 2018):** AI does not "think." It lowers the cost of PREDICTION (pattern matching, classification, forecasting, recommendation). When the cost of prediction drops, the value of its complement rises. The complement to prediction is JUDGMENT — the human ability to decide what to do with predictions, especially under ambiguity, ethical complexity, or novel situations.

**AI-era application:**

The most valuable businesses may not be "AI replaces humans" but "AI predicts, humans judge":

```
PREDICTION vs. JUDGMENT DECOMPOSITION:

PREDICTION (AI does this — cost approaching zero):
  → "What is this medical image showing?"
  → "What's the probability this loan defaults?"
  → "Which legal precedents are most relevant?"
  → "What will demand be next quarter?"
  → "Which candidates match this job description?"

JUDGMENT (Humans do this — value RISING):
  → "Should we operate, given the patient's wishes?"
  → "Should we approve this loan, given relationship context?"
  → "Which legal strategy serves this client's actual goals?"
  → "Should we expand or consolidate given this forecast?"
  → "Which candidate will thrive in our specific culture?"
```

**Business model implications:**
- **Pure AI prediction service** = commodity (every competitor can offer the same prediction). Race to zero margins. WEAK model.
- **AI prediction + human judgment hybrid** = premium service. The judgment component is scarce, valuable, and defensible. STRONG model.
- **Judgment-as-a-service** = the highest-margin business. Use AI to handle all prediction, charge premium for the human judgment layer. Doctors who ONLY make decisions (AI does diagnosis). Lawyers who ONLY strategize (AI does research). Financial advisors who ONLY counsel (AI does analysis).

**What to scan for:**
```
PREDICTION-JUDGMENT SPLIT OPPORTUNITIES:
  Sectors where prediction is the majority of work time but judgment
    is the majority of value delivered
  → Legal: 80% research (prediction) + 20% strategy (judgment)
  → Medical: 60% diagnosis (prediction) + 40% treatment decisions (judgment)
  → Financial advisory: 70% analysis (prediction) + 30% counsel (judgment)

  The business model: AI handles the 60-80% prediction.
    Human handles the 20-40% judgment. Price at premium.
    Cost structure: 80% AI cost + 20% expert cost ≪ incumbent's 100% expert cost.
    Value captured: by the judgment, not the prediction.

  WATCH FOR: Industries where prediction and judgment are currently BUNDLED
    in the same professional role. Unbundling them = the opportunity.
```

### T23: Innovation Stack / Competitive Immunity (Jim McKelvey)

**Theory (McKelvey, 2020):** When solving a problem no one has solved before, each solution creates a new problem that requires another novel solution. The resulting "innovation stack" — a tower of interdependent innovations — creates competitive immunity not through any single moat but through the COMPLEXITY of copying the entire stack.

**AI-era application:** In AI-disrupted markets, the first entrant who solves the full problem (not just "use AI for X") builds an innovation stack that's extremely hard to copy:
- Solve the AI accuracy problem → need domain-specific training data → need customer relationships → need trust mechanism → need compliance framework → need pricing model that works at AI economics → need support model for AI errors
- Each layer is individually copyable. The STACK is not.

**What to scan for:**
```
INNOVATION STACK POTENTIAL:
  Sectors where the problem requires 5+ interdependent innovations
  Markets where "just add AI" doesn't work (need domain expertise,
    regulatory navigation, trust building, data acquisition)
  → These are HARDER to enter (barrier) but HARDER to copy (moat)
  → The barrier IS the moat
  → Build the full stack; competitors who copy one layer fail
```

---

### Integration: How T11-T23 Map to Scanning

| Theory | Primary Signal Type | Transmission Node | Complements |
|--------|-------------------|-------------------|-------------|
| T11 Regulatory Capture | regulatory_moat | N2-N3 | T3, T8 |
| T12 Nash Equilibrium | competitive_saturation | N4 | T1, T17 |
| T13 Principal-Agent | agency_cost_collapse | N4-N5 | T10, T3 |
| T14 Prospect Theory | switching_friction | N5-N6 | T6, T7 |
| T15 Minsky Extended | credit_cycle_sensitivity | N3-N4 | T4, T1 |
| T16 Resource-Based View | resource_shift | N3-N4 | T2, T10 |
| T17 Institutional Theory | institutional_tipping | N3-N4 | T1, T12 |
| T18 Real Options | timing_optimization | N4-N6 | T5, T1 |
| T19 Attention Economics | attention_scarcity | N5-N6 | T6, T7 |
| T20 Complexity Economics | feedback_loop | N4-N6 | T6, T10 |
| **T21 Polanyi's Paradox** | **work_classification** | **N5-N6** | **T3, T7, T22** |
| **T22 Prediction Machines** | **judgment_premium** | **N5-N6** | **T21, T3, T7** |
| **T23 Innovation Stack** | **competitive_immunity** | **N4-N6** | **T11, T20, T16** |
