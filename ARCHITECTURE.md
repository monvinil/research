# AI Economic Research Engine — Architecture

## Purpose

Identify businesses to build in the AI-driven economy across three horizons:
- **H1 (1-3 years):** Immediate arbitrage — cost-structure kills against incumbents with low mobility
- **H2 (3-5 years):** Re-ignited businesses — previously dead economics revived by agentic cost structures
- **H3 (5-10 years):** Structural shifts — new economic categories created by infrastructure overhang

## Core Thesis (Principles Engine)

We reject the default playbook: "build another SaaS/agent tool in a crowded space."
Instead, we apply economic mechanics:

1. **Infrastructure Overhang Exploitation** — When infra is overbuilt (compute, models, tooling), the returns shift to applications that consume it cheaply. We look for businesses where the _cost of intelligence_ has dropped below the threshold that killed previous attempts.

2. **Low-Mobility Incumbent Targeting** — Large orgs with high fixed costs, union constraints, regulatory capture, or cultural inertia cannot restructure to match agentic-first cost curves. These are the targets.

3. **Output Cost Dominance** — The winning move is not "better product" but "same output at 5-20x lower cost." We model unit economics of existing businesses and find where agentic labor collapses the cost stack.

4. **Dead Business Revival** — Businesses that died (or never started) because labor/coordination costs exceeded revenue potential. With agentic operations, the break-even shifts. We scan for these systematically.

5. **Demographic Arbitrage** — Aging populations, skill shortages, migration patterns create structural gaps. Agentic businesses that fill demographic gaps have regulatory tailwinds instead of headwinds.

6. **Resource/Geopolitical Coupling** — Hardware supply chains, energy costs, and trade policy directly constrain which AI businesses are viable where. We track these as hard constraints, not background noise.

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
└──────────┬──────────┬──────────┬────────────────┘
           │          │          │
     ┌─────▼──┐  ┌────▼───┐  ┌──▼──────────┐
     │ AGENT A│  │AGENT B │  │  AGENT C     │
     │ Trends │  │Practi- │  │  Sync /      │
     │Scanner │  │tioner  │  │  Orchestrator│
     └────────┘  └────────┘  └─────────────┘

  A: Scans web, social, financial    B: Verifies     C: Manages cycles,
     data, policy, research for       assumptions,    data persistence,
     signals matching our thesis      models unit     context bridging,
                                      economics,      grading, UI updates
                                      stress-tests
                                      viability
```

## Data Flow

1. **Master** sets research direction + constraints
2. **Agent A** (Trends) scans sources, produces raw signal list
3. **Agent C** (Sync) ingests signals, deduplicates, grades preliminary relevance
4. **Agent B** (Practitioner) takes top-graded signals, runs viability checks
5. **Agent C** (Sync) compiles verified results, updates tracking, pushes to UI
6. **Master** reviews compiled output, adjusts direction, triggers next cycle

## Output Structure

Each research cycle produces:
- `data/signals/YYYY-MM-DD.json` — raw signals from Agent A
- `data/verified/YYYY-MM-DD.json` — verified opportunities from Agent B
- `data/grades/YYYY-MM-DD.json` — graded and ranked output from Agent C
- `data/context/state.json` — running state for cross-cycle context

## Time Horizons Mapping

| Horizon | Signal Type | Verification Focus | Example Pattern |
|---------|-------------|-------------------|-----------------|
| H1 (1-3y) | Current cost structures, existing incumbents, available AI tooling | Unit economics vs. incumbent COGS | Agentic bookkeeping firm @ 1/10th cost of traditional |
| H2 (3-5y) | Emerging model capabilities, regulatory shifts, demographic curves | TAM viability, regulatory trajectory | AI-native insurance underwriting in aging markets |
| H3 (5-10y) | Infrastructure buildout, geopolitical realignment, energy transitions | Strategic positioning, moat durability | Vertical AI utility co. in energy-constrained regions |
