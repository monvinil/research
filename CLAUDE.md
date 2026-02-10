# Research Engine — Claude Code Project Context

## What This Is

A multi-agent economic research engine that identifies businesses worth building in the AI-driven economy. It detects **systemic shifts** (liquidation cascades, cost-structure collapses, demographic gaps, dead business revivals) and lets specific industries emerge from the data.

## Architecture: Parallel Claude Code Sessions

This engine runs as **parallel Claude Code sessions**, each acting as a specialized agent. Sessions communicate through shared JSON files on disk.

### Agent Sessions

| Session | Agent Prompt | Reads From | Writes To |
|---------|-------------|------------|-----------|
| **Agent A** (Scanner) | `agents/agent_a_trends_scanner.md` | `data/raw/`, `data/context/kill_index.json` | `data/signals/` |
| **Agent C** (Sync) | `agents/agent_c_sync.md` | `data/signals/`, `data/context/state.json` | `data/graded/`, `data/context/` |
| **Agent B** (Practitioner) | `agents/agent_b_practitioner.md` | `data/graded/`, `data/context/state.json` | `data/verified/` |
| **Master** | `agents/master.md` | `data/verified/`, `data/context/` | `data/ui/dashboard.json`, `data/context/state.json` |

### How to Run a Cycle

**Option 1: Single session (current)**
One Claude Code session acts as all 4 agents sequentially. Run: `Run research cycle 4` and the session will read raw data, process as each agent, and write results.

**Option 2: Parallel sessions (target architecture)**
Launch 4 terminal tabs, each running Claude Code with a specific agent role. See `scripts/run_parallel.sh`.

### Data Directory Structure

```
data/
├── raw/          # Raw API data from connectors (FRED, BLS, EDGAR, web)
├── signals/      # Agent A output — extracted signals
├── graded/       # Agent C output — graded and clustered signals
├── verified/     # Agent B output — verified opportunities
├── context/      # Persistent state across cycles
│   ├── state.json           # Running engine state
│   ├── cycle_summaries.json # Master synthesis per cycle
│   └── kill_index.json      # Kill patterns (never delete)
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
cd /home/user/research
python3 connectors/fred.py    # Pulls FRED data
python3 connectors/bls.py     # Pulls BLS data
python3 connectors/edgar.py   # Pulls EDGAR filings
python3 connectors/websearch.py  # Pulls web search results
```

## Research Verification Standards

Every research output must be verifiable:

1. **Source attribution**: Every signal must cite a specific data source (URL, API endpoint, filing number)
2. **No template generation**: Outputs must show reasoning, not fill templates. If a signal says "Chapter 11 filings +76% YoY" it must link to the actual PACER/ABI data
3. **Confidence markers**: Every claim gets Low/Medium/High confidence. Low = inference from partial data. High = direct primary source
4. **Kill index integrity**: Kill reasons are permanent assets. Never delete without explicit new data contradicting them
5. **Cross-cycle context**: Each cycle reads previous cycle summaries. Patterns must strengthen or weaken based on new evidence, not reset

## Current State (Cycle 3)

- **Engine**: Opus 4.6 in-session (first LLM-reasoned cycle)
- **Top opportunity**: Distressed Professional Services Acquisition (score 87)
- **4 confirmed patterns**: P2+P5 Divergence Corridor, P2+P3 Credit-Squeeze, P1+P3 Cost Floor Unlock, P7 Timing Arbitrage (emerging)
- **Next**: Deep verification on top 2 opportunities, competitor scans, LATAM expansion

## Important Notes

- `.env` contains API keys — never commit
- `data/context/kill_index.json` is the most valuable persistent asset — never truncate
- Dashboard deploys to GitHub Pages via auto-merge of claude/* branches to main
- The engine optimizes for OPPORTUNITY QUALITY, not capital fit
