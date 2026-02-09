# AI Economic Research Engine — Architecture

## Purpose

Identify businesses to build in the AI-driven economy across three horizons:
- **H1 (1-3 years):** Immediate arbitrage — cost-structure kills against incumbents with low mobility
- **H2 (3-5 years):** Re-ignited businesses — previously dead economics revived by agentic cost structures
- **H3 (5-10 years):** Structural shifts — new economic categories created by infrastructure overhang

## Founding Constraints

These are starting conditions, not walls. They define *cost gradients* — not what's impossible, but what's cheap vs. expensive to execute.

```
CAPITAL:        $500K-$1M (VC angel check). No multi-year cash burn models.
                Must reach revenue or clear metrics within runway.
LOCATION:       Davis, CA — 1hr from SF. Access to Bay Area networks + large
                rural/agricultural hinterland.
TEAM:           2 founders.
                Founder 1: Argentina citizen, US resident. Native English+Spanish.
                  Can operate in US + LATAM markets natively.
                Founder 2: US citizen, Georgia Tech ML/AI Masters. Technical
                  execution on model fine-tuning, inference optimization,
                  agentic system architecture.
LANGUAGES:      English, Spanish natively. Other languages = higher ops cost,
                not a blocker. Factor into unit economics.
LEGAL:          Both legal to work in US. Founder 1 is resident (visa constraints
                may limit certain government/defense contracts — verify per opp).
LICENSES:       Neither founder holds CPA, JD, MD, etc. BUT: willing to acquire
                existing businesses that carry needed licenses. License = acquirable
                asset, not a wall. Factor acquisition cost into unit economics.
OPERATING GEO:  US + LATAM = lowest friction. Other geographies viable if the
                economics arbitrage justifies the higher ops cost. No geography
                is off-limits — evaluate on cost/benefit, not binary yes/no.
```

### What These Constraints Mean for the Engine

- **Capital-constrained = agentic-first is not optional.** At $500K-$1M, you cannot hire a team of 15. The business MUST run on AI labor from day 1. This is a feature, not a bug — it forces the cost structure the engine is looking for.
- **Two technical founders = execution speed advantage.** ML/AI Masters + operator = can build and deploy without hiring for 6-12 months.
- **Licenses are acquirable, not blockers.** If an opportunity requires a CPA, JD, MD, or any professional license, the move is to acquire a small existing licensed business. This is a cost item in the unit economics model, not a kill condition. Agent B should price the acquisition instead of killing the opportunity.
- **US + LATAM = lowest friction, not only option.** US for primary TAM, LATAM as POC/secondary. But if there's a 10x arbitrage in Germany, Japan, or UAE — the higher ops cost is worth modeling, not dismissing. Evaluate geography on economics, not convenience.
- **Language is a cost gradient.** English+Spanish markets are cheapest to operate. Non-English/Spanish markets require local hires or partners — price it, don't exclude it.

## Core Thesis (Principles Engine)

We reject the default playbook: "build another SaaS/agent tool in a crowded space."
We reject industry-picking. We look for **systemic shifts** — structural patterns that create opportunity categories.

The mental model is not "which industry should we enter?" but rather:
- Where are liquidation cascades hitting as infrastructure debt meets cheap AI competition?
- Where are low-margin businesses that survived on inertia now facing cost-structure extinction?
- Where did businesses previously die that would now work at agentic cost curves?
- Where are demographic gaps creating demand that no one can fill with human labor?

### P1: Infrastructure Overhang Exploitation
When infra is overbuilt (compute, models, tooling), the returns shift to applications that consume it cheaply. We look for businesses where the _cost of intelligence_ has dropped below the threshold that killed previous attempts.

### P2: Liquidation Cascade Detection
**NEW — replaces simple "incumbent targeting."** Track the chain reaction: AI infrastructure buildout → cheap inference → new entrants with 5-20x cost advantage → low-margin incumbents can't compete → forced consolidation/exit → asset liquidation → even cheaper entry for the next wave. We want to enter at the point where incumbents are exiting and assets (customers, contracts, physical infra) are available cheaply.

### P3: Output Cost Kill
The winning move is not "better product" but "same output at 5-20x lower cost." We model unit economics of existing businesses and find where agentic labor collapses the cost stack. At $500K-$1M capital, we need businesses where our cost structure IS the moat.

### P4: Dead Business Revival
Businesses that died (or never started) because labor/coordination costs exceeded revenue potential. With agentic operations, the break-even shifts. Scan for these systematically — failed startups 2010-2023, abandoned business categories, "everyone knows this doesn't work" conventional wisdom that was actually just a cost problem.

### P5: Demographic Alignment
Aging populations, skill shortages, migration patterns create structural gaps. Agentic businesses that fill demographic gaps have regulatory tailwinds instead of headwinds. Filling gaps = governments want solutions. Competing for existing jobs = governments resist.

### P6: Geopolitical Resilience
Can this business operate within the US bloc? Does it benefit from US-China decoupling (reshoring demand, localization requirements)? Does it exploit LATAM's position as a neutral/US-aligned manufacturing/services alternative?

## Agent Topology

```
┌─────────────────────────────────────────────────┐
│                 MASTER AGENT                     │
│         (Communication / Direction)              │
│                                                  │
│  - Maintains research thesis & priorities        │
│  - Reviews outputs from all agents               │
│  - Adjusts scanning parameters                   │
│  - Interfaces with human operator                │
│  - Applies Principles Engine as filter           │
│  - Sets dynamic grading weights per cycle        │
└──────────┬──────────┬──────────┬────────────────┘
           │          │          │
     ┌─────▼──┐  ┌────▼───┐  ┌──▼──────────┐
     │ AGENT A│  │AGENT B │  │  AGENT C     │
     │ Trends │  │Practi- │  │  Sync /      │
     │Scanner │  │tioner  │  │  Orchestrator│
     │        │  │        │  │              │
     │+Comp.  │  │        │  │+Kill Index   │
     │ Scan   │  │        │  │+Dyn. Weights │
     └────────┘  └────────┘  └─────────────┘

  A: Scans signals + competitor   B: Verifies      C: Manages cycles,
     landscape for verified        assumptions,      kill-reason feedback,
     opportunities                 models unit       dynamic grading,
                                   economics,        context bridging,
                                   stress-tests      UI updates
```

## Data Flow

1. **Master** sets research direction + constraints + grading weight overrides
2. **Agent A** (Trends) scans sources, produces raw signal list
3. **Agent C** (Sync) ingests signals, deduplicates, grades with dynamic weights
4. **Agent B** (Practitioner) takes top-graded signals, runs viability checks against founding constraints
5. **Agent C** (Sync) compiles verified results, updates kill index, pushes to UI
6. **Agent A** (Trends) runs competitor scan on verified opportunities
7. **Master** reviews compiled output, adjusts direction, triggers next cycle

## Output Structure

Each research cycle produces:
- `data/signals/YYYY-MM-DD.json` — raw signals from Agent A
- `data/verified/YYYY-MM-DD.json` — verified opportunities from Agent B
- `data/grades/YYYY-MM-DD.json` — graded and ranked output from Agent C
- `data/competitors/YYYY-MM-DD.json` — competitor landscape for verified opps
- `data/context/state.json` — running state for cross-cycle context
- `data/context/kill_index.json` — accumulated kill reasons for feedback

## Time Horizons Mapping

| Horizon | Signal Type | Verification Focus | Example Pattern |
|---------|-------------|-------------------|-----------------|
| H1 (1-3y) | Liquidation cascades, current cost structures, available AI tooling | Unit economics vs. incumbent COGS at $500K-$1M start | Agentic service firm entering market where incumbents are consolidating/exiting |
| H2 (3-5y) | Emerging model capabilities, regulatory shifts, demographic curves | TAM viability, can 2 founders + AI scale to this? | AI-native operations in category where human labor pipeline is collapsing |
| H3 (5-10y) | Infrastructure buildout, geopolitical realignment, energy transitions | Strategic positioning, moat durability, LATAM angle | Vertical AI business positioned for US-LATAM corridor advantages |
