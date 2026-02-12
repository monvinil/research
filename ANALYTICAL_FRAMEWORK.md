# Analytical Framework — Macro-to-Micro Transmission & Research Edge

**Core thesis:** The edge isn't just where you look for data. It's what data you look at, what theoretical lens you apply, and how you model the causal chain from geopolitical shift → policy response → industry structure change → firm behavior → labor market effect → specific business opportunity. Most AI research skips from "macro observation" to "business idea" without modeling the transmission steps. This misses second-order effects, timing signals, and counter-forces.

---

## Part 1: Applied Economic Theories (15 Scoring Theories + 4 Scanning Lenses)

### How Theories Connect to Scoring

Each theory maps to one or more of the 5 scoring axes:
- **SN** (Structural Necessity): T1, T3, T6, T8, T10
- **FA** (Force Alignment): T4, T5, T15, T24, T25
- **EC** (External Context): T8 (cross-geography), T5 (Perez regional variation)
- **TG** (Timing Grade): T1, T5, T18
- **CE** (Capital Efficiency): T10, T20, T24

---

### Tier 1: Core Theories (Drive Multiple Axes)

#### T1: Schumpeterian Creative Destruction + Christensen Disruption

**What it does:** Identifies sectors where incumbents are dead but don't know it yet — the "gap period" between cost structure collapse and actual exits.

**Scores it feeds:** SN (structural necessity of replacement), TG (gap period = entry window)

**Data signature:**
```
INCUMBENT DEATH SIGNAL (SN + TG):
  BLS wage growth for sector > CPI                      → costs rising
  FRED industry revenue flat or declining                → revenue not keeping up
  EDGAR 10-K: no "artificial intelligence" in strategy   → not adapting
  → DIAGNOSIS: Schumpeterian gap period. 12-24mo window.

CHRISTENSEN TEST (SN modifier):
  Can incumbent adopt AI without cannibalizing revenue?
    YES → Sustaining. Incumbent wins. SN penalty (-2).
    NO  → Disruptive. SN bonus (+1).
```

#### T3: Baumol's Cost Disease (Cure + Premium)

**What it does:** Identifies two opportunity types: (A) AI cures decades of cost inflation in cognitive services, (B) human-touch services become more valuable as digital collapses.

**Scores it feeds:** SN (stored disruption energy = structural necessity)

**Data signature:**
```
BAUMOL CURE (SN boost):
  Sector CPI growing > headline CPI for 10+ years
  + >60% of sector employment is cognitive/analytical
  → Stored energy = (years × premium × sector size)

BAUMOL PREMIUM (SN boost for human-premium models):
  Sector work is fundamentally tacit (physical, empathy, craft)
  + Adjacent digital costs collapsing
  → Premium = relative value increase
```

**Connector:** FRED (sector CPI series), BLS (occupation mix), O*NET (Polanyi classification)

#### T5: Perez Technological Revolutions (Installation → Deployment)

**What it does:** Positions the current AI revolution within the 5-surge historical pattern. We're in late Installation / early Turning Point — crash-resilient businesses are highest conviction.

**Scores it feeds:** TG (crash resilience), EC (different regions at different Perez positions)

**Data signature:**
```
CRASH RESILIENCE CHECK (TG):
  Revenue-generating within 6-12 months?        → TG +1
  Survives 18-month funding freeze?              → TG +1
  Physical economy (not just digital)?           → TG +0.5
  Needs follow-on funding before cash-flow?      → TG -2

REGIONAL PEREZ POSITION (EC):
  US: Late Installation (GPU bubble, app layer emerging)
  China: Parallel Installation (state-directed, different crash dynamics)
  EU: Early Installation (regulatory-first, slower deployment)
  Japan: Early Deployment (aging-forced adoption, pragmatic)
```

#### T6: Jevons Paradox (Demand Expansion)

**What it does:** When AI makes services 10x cheaper, demand doesn't stay constant — it expands 3-5x. TAM calculations based on current market size are wrong.

**Scores it feeds:** SN (latent demand = structural necessity)

**Data signature:**
```
JEVONS EXPANSION (SN modifier):
  Current penetration < 30% of potential customers
  + Primary barrier = PRICE (not awareness, not regulation)
  + 10x cost reduction would unlock new segments
  → TAM multiplier: 3-5x current served market
```

#### T8: Demographic Transition (Labor Supply Curves)

**What it does:** Models specific labor supply curves by occupation and geography. Japan leads US by 5-10 years; India has opposite dynamics.

**Scores it feeds:** SN (supply collapse = structural necessity), EC (cross-geography leading indicators)

**Data signature:**
```
SUPPLY COLLAPSE (SN boost):
  BLS: Average practitioner age > 55
  + New entrants < retirements per year
  + No viable immigration pipeline
  → Labor supply approaches zero in 5-10 years
  → AI doesn't need to be BETTER than humans — just AVAILABLE

CROSS-GEOGRAPHY (EC modifier):
  Japan solutions preview US needs by 5-10 years    → EC +1
  India demographic dividend = different opportunity → EC +0.5
```

**Connector:** BLS (occupation demographics), O*NET (occupation profiles), Census (business owner age)

#### T10: Coase/Williamson Transaction Cost Economics

**What it does:** AI collapses transaction costs for cognitive work → optimal firm size shrinks → 532K new business applications/month.

**Scores it feeds:** SN (micro-firm infrastructure = structural necessity), CE (smaller firms = capital efficient)

**Data signature:**
```
COASEAN SHRINKAGE (SN + CE):
  Rising share of firms with <10 employees
  + Sole proprietorship growth rate by industry
  + Business applications at 532K/mo despite rising delinquency
  → Firm size shrinking = Coase in action
  → Serve the new small firms, or BE the new small firm
```

**Connector:** Census CBP (firm size distribution), FRED (business applications)

---

### Tier 2: Force-Specific Theories

#### T4: Minsky's Financial Instability Hypothesis

**What it does:** PE roll-ups borrowed at stable-era multiples to consolidate fragmented industries. AI cost compression + refinancing wall creates double squeeze.

**Scores it feeds:** FA (F4 capital force alignment), TG (distress timing)

**Data signature:**
```
MINSKY MOMENT (FA + TG):
  EDGAR: Companies with debt/EBITDA > 4x AND declining revenue
  + PE-backed companies reporting "margin pressure"
  + $936B-$1.8T PE debt maturing 2026-2028
  → Double squeeze = forced asset sales = acquisition window
```

#### T15: Minsky Extended — The Refinancing Wall

**What it does:** Specific mechanism of the PE debt maturity schedule colliding with AI margin compression.

**Scores it feeds:** FA (F4 capital force), TG (timing of distress wave)

**Data signature:**
```
REFINANCING WALL (TG):
  FRED: Corporate debt maturity schedule
  + EDGAR: >40% of debt maturing in 12-24mo
  + Combined with AI cost compression in same sector
  → Accelerated liquidation = P2 asset opportunity
```

#### T21: Polanyi's Paradox — The Automation Boundary (Autor)

**What it does:** Classifies work into routine-cognitive (automatable), tacit-manual (human premium rises), tacit-cognitive (judgment premium). Defines the Barbell Economy.

**Scores it feeds:** SN (which work category this model addresses)

**Connector: O*NET** — This theory has a DIRECT data connector. The O*NET Polanyi classifier maps work activities to automation categories:

```
POLANYI CLASSIFICATION (via O*NET connector):
  classify_polanyi(soc_code) returns:
    automation_exposure: 0-1 (routine-cognitive %)
    judgment_premium: 0-1 (tacit-cognitive %)
    human_premium: 0-1 (tacit-manual %)

  → High automation_exposure (>0.5) = Baumol Cure target → SN boost
  → High judgment_premium (>0.3) = AI+human hybrid → different model type
  → High human_premium (>0.3) = Baumol Premium → human-service model
```

**CRITICAL:** O*NET connector is BUILT but NOT routed to scoring. Route classify_polanyi() output into SN calculation.

#### T22: Prediction Machines — Complement Principle (AGG)

**What it does:** AI lowers cost of PREDICTION (pattern matching, classification). The complement — JUDGMENT — rises in value. Unbundling prediction from judgment = the opportunity.

**Scores it feeds:** SN (prediction/judgment split), CE (hybrid model margins)

**Connector: O*NET** — Use alongside T21. Work activities classified as "Making Decisions and Solving Problems" or "Developing Objectives and Strategies" = judgment. "Processing Information" or "Analyzing Data" = prediction.

```
PREDICTION-JUDGMENT SPLIT (SN + CE):
  Legal: 80% research (prediction) + 20% strategy (judgment)
  Medical: 60% diagnosis (prediction) + 40% treatment (judgment)
  → AI handles 60-80% prediction at near-zero cost
  → Human handles 20-40% judgment at premium
  → Margin: AI cost + expert cost ≪ incumbent's full expert cost
```

#### T24: Robotics × AI Compound Effect

**What it does:** AI + robotics individually limited, but compound enables flexible physical production at dramatically lower cost — compressing COGS, not just SGA.

**Scores it feeds:** SN (physical production necessity), CE (COGS compression), EC (Japan leads in robotics adoption)

**Data signature:**
```
PRODUCTION FIT SPECTRUM:
  STRONG: Custom manufacturing, specialty food, precision agriculture,
          construction prefab (labor shortage + precision)
  MODERATE: Standard discrete manufacturing, warehousing
  POOR: Commodity chemicals, raw materials, bulk agriculture

ACQUISITION ECONOMICS (CE):
  Aging owner sale: 2-4x EBITDA
  PE-distressed sale: 1-3x EBITDA
  SBA 504: up to $5.5M below-market (equipment IS collateral)
```

#### T25: Fear Economics — Psychology as Structural Force

**What it does:** For every sector, there are TWO timelines: economic (when AI is viable) and psychological (when stakeholders adopt). The gap is exploitable AND creates new demand categories.

**Scores it feeds:** FA (F5 psychology force), TG (fear delays adoption)

**Five friction dimensions:**
1. Worker displacement fear → slows employer adoption
2. Customer trust barrier → "verified human" premium
3. Regulatory fear response → compliance moat
4. Institutional resistance → delays until tipping point
5. Media narrative → accelerates or delays 1-2 years

**Fear-driven demand creation:** AI compliance services, AI safety/audit, human verification, job retraining, AI insurance, cybersecurity, AI ethics consulting — REAL categories from fear.

---

### Tier 3: Scoring Sub-Factors

#### T18: Real Options Theory → TG Scoring

**What it does:** Business decisions under uncertainty are options. Value of waiting vs. acting depends on investment reversibility and uncertainty level.

**Scores it feeds:** TG (directly)

```
TG MODIFIER FROM REAL OPTIONS:
  Low investment + reversible (agentic-first, $500K)
    → Option value of waiting is LOW → TG +1 (act now)
  High investment + irreversible ($10M+ platform)
    → Option value of waiting is HIGH → TG -1 (wait)
  AI capability uncertainty DECREASING (benchmarks stabilizing)
    → Option value of waiting DROPS → TG +0.5 (window closing)
```

**CONNECT TO TG:** This theory should directly modify TG scores but currently doesn't. Implementation: check if model's capital_required > $5M AND architecture is platform → TG penalty.

#### T20: Complexity Economics — Feedback Loops → CE Sub-Factor

**What it does:** Positive feedback loops (data flywheel, cost flywheel, ecosystem lock-in) create winner-take-all dynamics.

**Scores it feeds:** CE (for platform/network models only)

```
FEEDBACK LOOP ASSESSMENT (CE modifier for platforms):
  Data flywheel possible AND no one has started it → CE +1
  Network effects strong AND first-mover → CE +1
  Feedback loops already spinning for competitor → CE -2
```

#### T14: Prospect Theory (Kahneman & Tversky) → Customer Acquisition

**What it does:** Loss aversion predicts which customers switch to AI and which resist.

**Scores it feeds:** TG (adoption speed), SN (unserved vs. served market sizing)

```
BEHAVIORAL SWITCHING (TG + SN modifiers):
  >50% of target market currently UNSERVED → SN +1 (Jevons)
  High-trust + served market → TG -1 (slow adoption)
  Commodity perception → TG +0.5 (fast adoption)
```

#### T16: Resource-Based View (Barney) → Moat Assessment

**What it does:** VRIN resources (Valuable, Rare, Inimitable, Non-substitutable) have shifted. Information processing is no longer rare. Proprietary data, licenses, physical assets, trust in AI-skeptical markets = newly VRIN.

**Scores it feeds:** CE (moat durability sub-factor)

```
VRIN RESOURCE SHIFT (CE modifier):
  Primary moat is human expertise → CE -1 (eroding)
  Primary moat is proprietary data → CE +1 (strengthening)
  Primary moat is regulatory license → CE +1 (durable)
  Primary moat is physical assets → CE +0.5 (Perez-resilient)
```

---

### Scanning-Only Lenses (Agent A Use, Not Scored)

These theories guide what Agent A scans for but don't directly feed scoring axes.

#### S1 (formerly T9): Dutch Disease — AI Talent Vacuum
Scan for: ratio of AI infrastructure jobs to AI application jobs. If infra > 3x app → talent vacuum at application layer. Application-layer businesses face less competition.

#### S2 (formerly T11): Regulatory Capture (Stigler)
Scan for: Lobbying spend by industry association + position on AI regulation. Capture WEAKENING + labor shortage = fastest entry window. Capture STRENGTHENING = moat for first-movers inside.

#### S3 (formerly T12): Nash Equilibrium Dynamics
Scan for: First incumbent to publicly adopt AI-first model in a sector. First client to switch. Industry conference panels debating "should we use AI?" = pre-defection. Window is between first defection and equilibrium shift.

#### S4 (formerly T17): Institutional Theory (DiMaggio & Powell)
Scan for: Professional association AI policy statements, first major firm committing to AI-first, regulatory mandates requiring AI capabilities. Pre-tipping = opportunity window. Post-tipping = incumbents flood in.

---

## Part 2: The Macro-to-Micro Transmission Chain

Every macro shift propagates through 6 nodes:

```
N1: GEOPOLITICAL/MACRO SHIFT    (observable: policy, trade, conflict)
  ▼
N2: POLICY RESPONSE              (observable: tariffs, regulations, subsidies)
  ▼
N3: INDUSTRY STRUCTURE CHANGE    (observable: supply chain shifts, cost curves)
  ▼
N4: FIRM BEHAVIOR                (observable: entry/exit, restructuring, M&A)
  ▼
N5: LABOR MARKET EFFECT          (observable: wage changes, vacancies, shortages)
  ▼
N6: BUSINESS OPPORTUNITY         (derived: specific model, geography, timing)
```

### Active Transmission Chains

| Macro Force | Current Node | Scoring Impact |
|-------------|--------------|----------------|
| AI inference cost collapse | N3-4 | SN + CE for all AI-enabled models |
| Professional services cascade | N4-5 | SN + TG for financial/accounting models |
| Silver Tsunami | N4-5 | SN + TG for acquire-and-modernize models |
| PE refinancing wall | N3-4 | FA (F4) + TG for rollup/acquisition models |
| US-China chip controls | N3-4 | EC + FA (F3) for manufacturing/compliance |
| Robotics × AI compound | N3-4 | SN + CE for physical production models |
| Japan aging (leading indicator) | N4-5 | EC for healthcare/elder care models |
| EU AI Act implementation | N2-3 | EC + FA (F3) for compliance/regulatory models |
| LATAM nearshoring | N2-3 | EC for manufacturing/supply chain models |

The opportunity materializes at nodes 4-5. If a chain stalls at node 2-3, the business model should be PARKED.

---

## Part 3: Analytical Edge — Data Layers

### Layer 1: What the data says (everyone sees this)
"Professional services employment fell 97K YoY"

### Layer 2: What it means in transmission chain context
"Employment fell 97K + credit fell $55B + no AI capex on 10-Ks = Schumpeterian gap period at node 4. Credit squeeze prevents restructuring (Minsky), so exit rate accelerates."

### Layer 3: Timing and positioning implications
"Bond market (HY spread 2.87%) hasn't priced the cascade. Entry timing: NOW, while bond markets think this sector is stable. Jevons: the 70% of SMBs that don't use CPAs become the real TAM."

### Analytical Methods

**1. Divergence Analysis:** Indicators that SHOULD move together but aren't = market mispricing.

**2. Velocity Tracking:** Rate of change matters more than levels. Track first derivatives.

**3. Cross-Geography Leading Indicators:** Japan previews US by 5-10 years. Argentina previews cost compression effects with weaker incumbents.

**4. Counter-Force Discipline:** For every bull case, construct the strongest bear case with equal rigor.

**5. Threshold Analysis:** Every model has specific quantitative thresholds where it flips viable/non-viable. Track proximity.

---

## Part 4: Theory-to-Connector Mapping

| Theory | Primary Connector | Data It Needs |
|--------|------------------|---------------|
| T1 Schumpeter | BLS + FRED + EDGAR | Wage growth, revenue, 10-K text |
| T3 Baumol | FRED + BLS | Sector CPI, occupation employment |
| T5 Perez | FRED + Web Search | Capex trends, startup failure rates |
| T6 Jevons | Census CBP | Market penetration, establishment counts |
| T8 Demographics | BLS + Census + O*NET | Occupation age, firm owner age |
| T10 Coase | Census CBP + FRED | Firm size distribution, business apps |
| T4/T15 Minsky | EDGAR + FRED | Debt/EBITDA, HY spreads, maturity schedule |
| T21 Polanyi | **O*NET** | Work activity classification |
| T22 AGG | **O*NET** | Prediction vs. judgment decomposition |
| T24 Robotics×AI | Web Search + BLS | Robot installations, manufacturing PMI |
| T25 Fear | Google Trends + Web Search | AI fear queries, trust surveys |
| T18 Real Options | FRED + Web Search | Benchmark stability, uncertainty metrics |
| T14 Prospect Theory | Census CBP | Market penetration (served vs. unserved) |
| T16 Resource-Based | EDGAR + Web Search | Competitive moat analysis |
| T20 Complexity | Web Search | Network effect evidence |

---

## Summary: Theory Count

**15 scoring theories** (directly feed SN, FA, EC, TG, or CE):
T1, T3, T4, T5, T6, T8, T10, T14, T15, T16, T18, T20, T21, T22, T24, T25

**4 scanning lenses** (guide Agent A, don't score):
S1 (Dutch Disease), S2 (Regulatory Capture), S3 (Nash Equilibrium), S4 (Institutional Theory)

**4 cut** (redundant or unmeasurable):
~~T2 Ricardo~~ (subsumed by T21), ~~T7 Gresham~~ (duplicate of T21), ~~T13 Principal-Agent~~ (generic, absorbed into SN), ~~T23 Innovation Stack~~ (unmeasurable)
