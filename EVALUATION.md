# Engine Evaluation & Setup Requirements

## Self-Critique of the Design

### What's strong

1. **The Principles Engine is the differentiator.** Most AI research tools scan and summarize. This one filters through an economic thesis. P3 (Output Cost Kill) and P4 (Dead Business Revival) are the most novel lenses — they force non-obvious opportunity identification.

2. **Agent B (Practitioner) as mandatory skeptic.** Without this, the engine just produces idea lists. The forensic verification step with named incumbents and calculated unit economics separates this from brainstorming.

3. **Time horizon separation.** Forcing every signal into H1/H2/H3 prevents conflating "could build today" with "interesting in theory." Keeps H1 outputs actionable.

4. **Agent C as memory.** Cross-cycle context is what makes this a research *engine* rather than repeated one-shots. Pattern detection across cycles compounds value.

### What needs correction

1. **Agent A scope is too broad for cycle 1.** Scanning all 6 categories across 5 geographies will produce noise.
   - **Fix:** First 2-3 cycles should be narrowly focused. Suggest starting with H1 + US + healthcare/professional-services/logistics. Expand after initial patterns emerge.

2. **Missing: competitive landscape agent.** The current design doesn't systematically track who else is building agentic businesses in identified spaces.
   - **Fix (deferred):** Add this as Agent D in a later phase, or give Agent A a specific "competitor scan" mode to run after Agent B identifies viable opportunities.

3. **Grading weights in Agent C are static.** The scoring should adapt based on what Master learns across cycles.
   - **Fix:** Agent C's grading weights should be settable per-cycle via Master directives, not hardcoded.

4. **No feedback loop from kills.** When Agent B kills an opportunity, the reason should feed back to Agent A to improve scanning precision.
   - **Fix:** Agent C should maintain a "kill reason index" that Agent A references to avoid producing similar low-viability signals.

5. **UI is read-only.** For real operation, you'd want to flag/bookmark opportunities, add notes, and trigger re-verification from the UI.
   - **Fix (deferred):** Phase 2 — add simple POST endpoints for annotations. Not needed for initial cycles.

## Recommended Cycle 1 Focus

```
INITIAL SCAN DIRECTIVE
Focus: H1 opportunities — businesses buildable in the next 12-18 months
Sectors: Healthcare admin, accounting/bookkeeping, legal services,
         insurance operations, logistics/freight, property management
Geographies: US primary, Japan secondary
Thesis: Find incumbents with >40% labor cost ratios in roles that
        current AI models can perform at >80% accuracy
Exclusions: Pure tech, consumer apps, social media, crypto
```

## Required APIs & Data Sources

### Tier 1 — Essential (connect before first cycle)

| Source | Access Method | Purpose | Cost |
|--------|-------------|---------|------|
| **FRED API** | Free API key (api.stlouisfed.org) | Labor costs, CPI, industry production indices | Free |
| **BLS Public Data API** | Free (api.bls.gov) | Occupation employment stats, wage data by industry | Free |
| **SEC EDGAR** | Free (efts.sec.gov) | 10-K filings for incumbent cost structure analysis | Free |
| **Web search API** | Serper.dev or SerpAPI | General web scanning for Agent A | ~$50/mo |
| **X/Twitter API** | Basic tier (developer.x.com) | Sentiment scanning, practitioner pain points | $100/mo |
| **Reddit API** | Free (oauth.reddit.com) | Industry subreddit scanning | Free |
| **Hacker News API** | Free (hn.algolia.com) | Tech community signals | Free |

### Tier 2 — High Value (connect within first week)

| Source | Access Method | Purpose | Cost |
|--------|-------------|---------|------|
| **Crunchbase API** | Basic plan | Startup activity, funding patterns, failures | ~$99/mo |
| **Indeed/LinkedIn job data** | Scraping or data providers | Job posting trends, salary data by role | Varies |
| **Trading Economics API** | Basic plan | Commodities, metals, macro indicators | ~$40/mo |
| **Alpha Vantage or Polygon.io** | Free/basic tier | Financial data, earnings transcripts | Free-$30/mo |
| **Google Trends API** | pytrends (unofficial) | Search trend signals | Free |

### Tier 3 — Nice to Have (connect as needed)

| Source | Access Method | Purpose | Cost |
|--------|-------------|---------|------|
| **ArXiv API** | Free (export.arxiv.org) | AI capability tracking | Free |
| **Hugging Face API** | Free (huggingface.co/api) | Open model landscape | Free |
| **World Bank Data API** | Free (api.worldbank.org) | International demographic/economic data | Free |
| **Cloud pricing APIs** | Public pages + scraping | AI inference cost tracking | Free |
| **GitHub API** | Free (api.github.com) | Open source tooling trends | Free |
| **EIA API** | Free (api.eia.gov) | Energy prices and outlook | Free |

### Social Accounts to Monitor (Agent A feed)

**X/Twitter lists to build:**
- AI economics: @benedictevans, @sama, @elaboratist, @levelsio, @paulg, @paborenstein
- Macro/geopolitics: @zabormeister, @INArteCarlworx, @RobinBrooksIIF, @jessefelder
- Industry insiders: Follow practitioners in target sectors (accounting, healthcare admin, logistics)
- Energy/commodities: @JavierBlas, @NickCunningham, @EnergyIntel

**Reddit subreddits:**
- r/smallbusiness, r/accounting, r/nursing, r/logistics, r/insurance
- r/artificial, r/MachineLearning, r/LocalLLaMA
- r/economics, r/geopolitics, r/commodities

**Newsletters/Substacks:**
- Matt Levine (Bloomberg Money Stuff) — financial industry signals
- Ben Thompson (Stratechery) — tech strategy
- Doomberg — energy/commodities
- Construction Physics — physical economy
- Apricitas Economics — macro data

## Running the Engine

### Quick Start

```bash
# 1. Start the UI
python scripts/serve_ui.py --port 8080
# Open http://localhost:8080/ui/

# 2. Initialize first cycle
python scripts/run_cycle.py --phase init --directive "H1 healthcare admin and professional services, US market"

# 3. Run Agent A scan (manually or via Claude/LLM API)
# Feed agents/agent_a_trends_scanner.md as system prompt
# Feed the scan directive as user message
# Collect output into data/signals/YYYY-MM-DD.json

# 4. Run Agent C grading
# Feed agents/agent_c_sync.md as system prompt
# Feed signals file as input
# Output to data/grades/YYYY-MM-DD.json

# 5. Run Agent B verification on top signals
# Feed agents/agent_b_practitioner.md as system prompt
# Feed top graded signals as input
# Output to data/verified/YYYY-MM-DD.json

# 6. Compile
python scripts/run_cycle.py --phase compile
```

### Automation Path

For fully automated cycles, you'll need:
1. An LLM API (Anthropic Claude API, OpenAI, or local models via Ollama)
2. A runner script that chains agent calls with data passing
3. Rate limiting and cost tracking (each full cycle ~$2-10 in API costs depending on model and volume)

The `scripts/run_cycle.py` handles the data plumbing. The actual agent execution requires either:
- **Claude Code sessions** — run each agent prompt manually
- **API automation** — Python script calling Claude/OpenAI API with agent prompts as system messages
- **Local models** — For Agent A scanning tasks, a capable open model (Llama 3, Mixtral) can handle signal extraction at lower cost

## Proposed Corrections Summary

| Issue | Severity | Fix | When |
|-------|----------|-----|------|
| Agent A scope too broad | High | Narrow first cycles to H1 + 3 sectors | Now |
| No competitor tracking | Medium | Add competitor scan mode to Agent A | Week 2 |
| Static grading weights | Medium | Make weights settable per-cycle | Week 1 |
| No kill-reason feedback loop | Medium | Add kill index to Agent C state | Week 1 |
| UI is read-only | Low | Add annotation endpoints | Phase 2 |
| No cost tracking for API usage | Low | Add simple token/cost counter | Week 1 |
