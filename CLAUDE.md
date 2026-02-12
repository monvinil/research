# Research Engine — Claude Code Project Context

## What This Is

A multi-agent economic research engine that projects **what the economy becomes** over the next 5 years. It tracks 6 macro forces (technology, demographics, geopolitics, capital, psychology, energy), projects sector transformations year by year (2026→2031), maps geographic variation, and identifies emergent economic categories.

**v1-v2 (cycles 1-9)**: Built a landscape map of 522 business models across 293 NAICS sectors, confirmed 28 structural patterns, cross-validated against 7 live data sources. This provides the **evidence base** for economy mapping.

**v3 (current)**: Pivoted from "what businesses are safe to build" to "what does the economy look like in 5 years." Business models from v2 are evidence for sector transformations, not the end product.

## Architecture: Parallel Claude Code Sessions

This engine runs as **parallel Claude Code sessions**, each acting as a specialized agent. Sessions communicate through shared JSON files on disk.

### Agent Sessions

| Session | Agent Prompt | Role | Key Output |
|---------|-------------|------|------------|
| **Agent A** (Scanner) | `agents/agent_a_trends_scanner.md` | Scan for transformation signals across 6 force dimensions, 10 source categories | Signals tagged by force, geography, time horizon, fear friction |
| **Agent C** (Sync) | `agents/agent_c_sync.md` | Grade signals, track force velocities, maintain sector transformation state | Force velocity tracking, geographic profiles, fear friction index |
| **Agent B** (Analyst) | `agents/agent_b_practitioner.md` | Project sector transformation paths (2026→2031), model second-order effects | Sector transformation projections with Barbell Economy analysis |
| **Master** | `agents/master.md` | Synthesize 4-layer economy map, present to operator | Economy Map Update (forces, sectors, geographies, emergent economy) |

### Key Framework Documents

- `ECONOMY_MAP_FRAMEWORK.md` — The 4-layer economy map architecture (forces, sectors, geographies, emergent economy)
- `ANALYTICAL_FRAMEWORK.md` — 25 theoretical lenses (T1-T25), transmission chain model, data analysis methodology

### Data Directory Structure

```
data/
├── raw/          # Raw API data from connectors (FRED, BLS, EDGAR, web)
├── signals/      # Agent A output — transformation signals
├── graded/       # Agent C output — graded and classified signals
├── verified/     # Agent B output — sector transformation projections
├── context/      # Persistent state across cycles
│   ├── state.json           # Running engine state (force velocities, sector states)
│   ├── cycle_summaries.json # Master synthesis per cycle
│   └── barrier_index.json   # Barrier/fear friction tracking
└── ui/           # Dashboard data (read by index.html)
    ├── dashboard.json
    └── signals_feed.json
```

### Connectors

Python scripts in `connectors/` pull live data:
- `fred.py` — Federal Reserve economic data (API key in .env)
- `bls.py` — Bureau of Labor Statistics
- `edgar.py` — SEC filings search
- `websearch.py` — DuckDuckGo web search
- `onet.py` — O*NET occupation data

### Running Connectors

```bash
cd /Users/mv/Documents/research
python3 connectors/fred.py    # Pulls FRED data
python3 connectors/bls.py     # Pulls BLS data
python3 connectors/edgar.py   # Pulls EDGAR filings
python3 connectors/websearch.py  # Pulls web search results
```

## Engine Philosophy (v3 — Economy Map)

### Project Transformations, Don't Rank Opportunities
The map shows what the economy BECOMES — not what to build. Sector transformation paths with year-by-year projections, not ranked business model lists.

### 4-Layer Architecture
1. **Macro Forces** (F1-F6): Technology, Demographics, Geopolitics, Capital, Psychology, Energy
2. **Sector Transformations**: NAICS-level, year-by-year 2026→2031, with second-order effects
3. **Geographic Variation**: US, China, EU, Japan, India, LATAM, SEA, MENA
4. **Emergent Economy**: New categories, firm structures, labor roles, capital structures

### Psychology Is Structural
Fear, trust, and institutional resistance are not noise — they shape transformation timing and path. The fear friction gap (economic readiness minus psychological readiness) modifies every sector projection.

### Second-Order Effects Matter More
When accounting transforms, commercial real estate reprices, business software disrupts, professional education restructures. The cascade matters more than the initial disruption.

### Geography Is a First-Class Dimension
The same force transforms sectors differently in Japan (aging-driven) vs India (leapfrog) vs EU (regulation-first). Geographic variation is data, not a footnote.

### Business Models Are Evidence
The 522 models from v2 tell us HOW sectors transform. They're evidence for projections, not recommendations.

### Honest Uncertainty
Every projection gets confidence levels and falsification criteria. The map acknowledges what we don't know.

## Research Verification Standards

1. **Source attribution**: Every signal must cite a specific data source
2. **No template generation**: Outputs must show reasoning, not fill templates
3. **Confidence markers**: Every claim gets Low/Medium/High confidence
4. **Falsification criteria**: Every projection lists what evidence would invalidate it
5. **Cross-cycle context**: Each cycle reads previous summaries. Projections strengthen or weaken based on new evidence

## Current State (v3, Economy Map Cycle 0)

- **Engine**: v3.0 — economy map, 5-year transformation projections
- **Evidence base**: 522 business models, 28 confirmed patterns, 7 data sources validated (from v2 cycles 1-9)
- **New dimensions**: Psychology/fear (T25), geographic variation, second-order cascades, emergent economy categories
- **Next**: First economy mapping cycle — project sector transformations using 9 cycles of evidence as foundation

## Analytical Framework

See `ANALYTICAL_FRAMEWORK.md` for the full framework:

- **25 theoretical lenses** (T1-T25): Schumpeter, Baumol, Minsky, Perez, Jevons, Coase, Polanyi, AGG Prediction Machines, Robotics×AI, Fear Economics (new), + 15 more
- **6-node transmission chain model**: Shift → Policy → Structure → Firm Behavior → Labor → Transformation
- **3-layer data analysis**: What data says → what it means → timing/positioning
- **Divergence detection**: Indicators that should move together but aren't
- **Fear friction model**: Economic readiness vs psychological readiness gap

## Important Notes

- `.env` contains API keys — never commit
- `ECONOMY_MAP_FRAMEWORK.md` is the economy map architecture — the primary output structure
- `ANALYTICAL_FRAMEWORK.md` is the theoretical foundation — 25 lenses including Fear Economics (T25)
- Dashboard deploys to GitHub Pages via auto-merge of claude/* branches to main
- The engine optimizes for PROJECTION ACCURACY and HONEST UNCERTAINTY, not opportunity ranking
- v2 business model data (522 models, 28 patterns) is preserved as evidence base
