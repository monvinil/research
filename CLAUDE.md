# Research Engine — Claude Code Project Context

## What This Is

A multi-agent economic research engine that maps the landscape of businesses worth building in the AI-driven economy. It detects **structural economic forces** (cost-structure collapses, Baumol cures, demographic gaps, dead business revivals, Jevons expansions, Coasean shrinkage) and constructs specific business models that exploit them.

**The engine produces a LANDSCAPE MAP, not a filtered shortlist.** It shows all viable businesses created by structural shifts, organized by economic force and structural advantage. The human operator decides what to build.

## Architecture: Parallel Claude Code Sessions

This engine runs as **parallel Claude Code sessions**, each acting as a specialized agent. Sessions communicate through shared JSON files on disk.

### Agent Sessions

| Session | Agent Prompt | Role | Reads From | Writes To |
|---------|-------------|------|------------|-----------|
| **Agent A** (Scanner) | `agents/agent_a_trends_scanner.md` | Detect structural forces, generate signals + opportunity hypotheses | `data/raw/`, `data/context/barrier_index.json` | `data/signals/` |
| **Agent C** (Sync) | `agents/agent_c_sync.md` | Grade signals, manage state, score landscape, track barriers | `data/signals/`, `data/context/state.json` | `data/graded/`, `data/context/` |
| **Agent B** (Constructor) | `agents/agent_b_practitioner.md` | Construct business models, quantify economic force, assess barriers as moats | `data/graded/`, `data/context/state.json` | `data/verified/` |
| **Master** | `agents/master.md` | Set direction, synthesize landscape map, present to operator | `data/verified/`, `data/context/` | `data/ui/dashboard.json`, `data/context/state.json` |

### How to Run a Cycle

**Option 1: Single session (current)**
One Claude Code session acts as all 4 agents sequentially. Run: `Run research cycle 1` and the session will read raw data, process as each agent, and write results.

**Option 2: Parallel sessions (target architecture)**
Launch 4 terminal tabs, each running Claude Code with a specific agent role. See `scripts/run_parallel.sh`.

### Data Directory Structure

```
data/
├── raw/          # Raw API data from connectors (FRED, BLS, EDGAR, web)
├── signals/      # Agent A output — extracted signals with opportunity hypotheses
├── graded/       # Agent C output — graded and clustered signals
├── verified/     # Agent B output — constructed business models with economic force
├── context/      # Persistent state across cycles
│   ├── state.json           # Running engine state
│   ├── cycle_summaries.json # Master synthesis per cycle
│   └── barrier_index.json   # Barrier tracking (NOT permanent kills — reviewed and expired)
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

### Running Connectors

```bash
cd /Users/mv/Documents/research
python3 connectors/fred.py    # Pulls FRED data
python3 connectors/bls.py     # Pulls BLS data
python3 connectors/edgar.py   # Pulls EDGAR filings
python3 connectors/websearch.py  # Pulls web search results
```

## Engine Philosophy (v2)

### Construct First, Critique Second
Agent B constructs 2-3 business models for every structural shift BEFORE evaluating barriers. The engine asks "what business SHOULD exist?" before asking "what could go wrong?"

### Economic Force Over Novelty
Scoring prioritizes TAM × cost advantage × Jevons expansion (economic force = 35% of score). VC differentiation / pitch novelty is NOT scored. A $200B market with 15x cost advantage is valuable even if the pitch sounds "generic."

### Barriers Are Moats
Regulatory requirements, licensing, compliance complexity — these create moats for first movers. The barrier index tracks them with resolution paths and moat potential, not as permanent kills.

### Landscape Map, Not Filtered List
The engine maps ALL viable businesses, organized by tier (economic force). Founder fit is scored separately as an overlay. A great opportunity for the wrong team is still on the map.

### No Permanent Kills
Barriers have review dates and expiration. Markets change, regulations evolve, technology improves. Nothing is permanently off the table.

### Pre-Cascade Is the Entry Window
The Schumpeterian gap period (before incumbents exit) is the optimal entry window. Leading indicators (wage growth > CPI, flat revenue, no AI capex) are sufficient — don't require confirmed bankruptcies.

## Research Verification Standards

Every research output must be verifiable:

1. **Source attribution**: Every signal must cite a specific data source (URL, API endpoint, filing number)
2. **No template generation**: Outputs must show reasoning, not fill templates
3. **Confidence markers**: Every claim gets Low/Medium/High confidence
4. **What Must Be True**: Every business model lists assumptions as Confirmed/Likely/Uncertain/Unlikely
5. **Cross-cycle context**: Each cycle reads previous summaries. Patterns strengthen or weaken based on new evidence

## Current State (v2, Cycle 0)

- **Engine**: v2.0 — construct-first, landscape mapping
- **Mode**: Clean slate after v1 reset (v1 ran 11 cycles, drifted to risk-minimization)
- **Next**: First landscape mapping cycle with rewritten agents

## Analytical Framework

The engine applies classical economic theories as operational lenses. See `ANALYTICAL_FRAMEWORK.md` for the full framework, including:

- **20 theoretical lenses** (Schumpeter, Ricardo, Baumol, Minsky, Kondratieff, Jevons, Gresham, Demographic Transition, Dutch Disease, Coase/Williamson, + 10 extended)
- **Macro-to-micro transmission chain model** — 6-node causal chains
- **3-layer data analysis** — Layer 1 (what data says), Layer 2 (what it means), Layer 3 (timing/positioning)
- **Divergence detection** — indicators that should move together but aren't = market mispricing
- **Counter-signal discipline** — context for better construction, not vetoes

## Important Notes

- `.env` contains API keys — never commit
- `data/context/barrier_index.json` tracks barriers with moat potential — review and expire, never treat as permanent
- `ANALYTICAL_FRAMEWORK.md` is the theoretical foundation — update theories as evidence accumulates
- Dashboard deploys to GitHub Pages via auto-merge of claude/* branches to main
- The engine optimizes for LANDSCAPE COMPLETENESS, not risk minimization
- Founder fit is scored separately — the map shows ALL viable businesses
