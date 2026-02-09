# AI Economic Research Engine — Architecture

## Purpose

Identify businesses to build in the AI-driven economy across three horizons:
- **H1 (1-3 years):** Immediate arbitrage — cost-structure kills against incumbents with low mobility
- **H2 (3-5 years):** Re-ignited businesses — previously dead economics revived by agentic cost structures
- **H3 (5-10 years):** Structural shifts — new economic categories created by infrastructure overhang

## Founding Constraints

These are starting conditions. They define *cost gradients* and *friction levels*, not limits.

**Capital is a variable, not a constraint.** The founding team has access to angel/VC networks and can raise beyond $500K-$1M if the opportunity justifies it. The hard problem this engine solves is NOT "what can we afford" — it's "what's worth building in an economy where every pitch deck says AI." Finding capital is easy. Finding something worth funding is hard.

```
STARTING CAPITAL: $500K-$1M initial check. Can raise more if opportunity
                  merits it. Capital scales to the quality of the thesis.
LOCATION:         Davis, CA — 1hr from SF. Bay Area networks + rural hinterland.
TEAM:             2 founders.
                  Founder 1: Argentina citizen, US resident. Native English+Spanish.
                    Operator. Can work US + LATAM natively.
                  Founder 2: US citizen, Georgia Tech ML/AI Masters. Technical
                    execution — fine-tuning, inference optimization, agentic systems.
LANGUAGES:        English, Spanish natively. Others = ops cost adder, not blocker.
LEGAL:            Both legal to work in US. Founder 1 is resident (flag on
                  govt/defense contracts — verify per opportunity).
LICENSES:         Neither founder holds CPA, JD, MD, etc. Willing to acquire
                  existing businesses carrying needed licenses.
OPERATING GEO:    US + LATAM = lowest friction. Any geography viable if
                  economics justify the overhead.
VC NETWORK:       Active angel/VC relationships. Can raise follow-on capital.
                  Do not optimize for "what's fundable at $500K" — optimize for
                  "what makes VCs excited vs. the 500 generic AI pitches they
                  see this month."
```

### What These Conditions Mean for the Engine

- **The engine optimizes for opportunity quality, not capital fit.** If the best opportunity requires $3M, we raise $3M. The engine's job is to find something so structurally differentiated that capital follows.
- **Agentic-first is a thesis, not a budget constraint.** We don't use AI labor because we can't afford humans. We use it because it creates cost structures incumbents literally cannot match. This is a strategic choice, not a financial one.
- **Two technical founders = execution speed advantage.** ML/AI Masters + operator = build and deploy without hiring for 6-12 months.
- **Licenses are acquirable.** Professional licenses = acquirable via small business acquisition. Price it, don't kill it.
- **Geography is a cost gradient.** US + LATAM = lowest friction. Other markets = model the overhead.
- **VC excitement is a signal.** If Agent B can articulate why this opportunity makes a VC excited *relative to the generic AI deal flow they're drowning in*, the opportunity is stronger. If the pitch sounds like everything else, it's weak regardless of unit economics.

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
