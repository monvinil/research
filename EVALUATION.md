# Engine Evaluation & API Edge Analysis

## Principles Engine Self-Test: Which APIs Produce Edge?

We applied our own framework to the question "which data sources should we connect?"
The filter: an API is worth connecting if it produces signals that pass our Principles Engine
AND cannot be replicated by general web search.

### Evaluation Criteria

For each API, we ask:
1. **Does it detect systemic patterns?** (Not just industry news)
2. **Does it produce quantified signals?** (Numbers Agent B can use for unit economics)
3. **Is it non-obvious?** (Would a competitor doing naive research miss this?)
4. **Signal-to-noise ratio:** How much filtering needed to extract useful signals?
5. **Founding constraint fit:** Usable by 2 people without a data team?

---

### TIER 1: CONNECT IMMEDIATELY — These produce signals no other source can

| API | Edge Thesis | Principle Served | Monthly Cost |
|-----|-------------|-----------------|-------------|
| **BLS API** | Occupation-level wage data + vacancy rates. THE dataset for P5 (demographic gaps). Identify exact occupations where: wages rising > CPI AND vacancy rates > 5%. These are the roles AI can fill with least resistance. No other public source gives this granularity. | P5, P3 | Free |
| **FRED API** | Industry-level financial health indicators. Combine with BLS to identify sectors in the squeeze (rising labor costs + falling margins = P2 liquidation cascade). Also: interest rate data for runway modeling (high rates = advantage for low-burn thesis). | P1, P2, P3 | Free |
| **SEC EDGAR** | 10-K filings contain cost structure breakdowns by segment. How Agent B names specific incumbents and calculates actual cost structures. No earnings summary site gives the raw cost data needed for P3 unit economics comparison. | P2, P3 | Free |
| **Web Search API (Serper)** | Agent A's general scanning backbone. Without this, Agent A is blind. Every source category except structured financial data flows through web search. ~$50/mo buys systematic querying vs. manual browsing. | All | ~$50/mo |

**Total Tier 1: ~$50/mo.** Three free APIs produce the quantified foundation, plus one paid API makes Agent A functional.

---

### TIER 2: CONNECT WITHIN FIRST WEEK — High edge, not blocking

| API | Edge Thesis | Principle Served | Monthly Cost |
|-----|-------------|-----------------|-------------|
| **Crunchbase** | Failed startup database. Primary input for P4 (dead business revival). Search startups in non-software verticals that failed 2015-2023, filter by failure reasons. Also: competitor landscape data for Agent A's competitor scan mode. No substitute at this scale. | P4, Competitor | ~$99/mo |
| **X/Twitter API** | Real-time practitioner complaints and industry sentiment. Individual practitioners saying "this industry is broken because X" = leading indicators before BLS/FRED data shows up. Also: early adopter reports ("I replaced X with AI and...") = direct P3 evidence. | P2, P3, P5 | ~$100/mo |
| **Reddit API** | Industry-specific subreddits = unfiltered practitioner pain. r/accounting, r/nursing, r/logistics, r/insurance, r/smallbusiness have daily posts about operational pain mapping directly to agentic substitution opportunities. | P2, P3, P5 | Free |
| **Hacker News API** | "What's becoming trivially easy to build" (P1). Track threads about agentic tools, cost reductions, capability unlocks. HN crowd reliably identifies failed business patterns worth revisiting (P4). | P1, P4 | Free |

**Total Tier 2: ~$199/mo.** Crunchbase is the biggest unlock — the dead business revival database.

---

### TIER 3: CONNECT AFTER FIRST 2-3 CYCLES — Useful when we have hypotheses to test

| API | Edge Thesis | Why Wait | Monthly Cost |
|-----|-------------|----------|-------------|
| **Trading Economics** | Commodities, metals, energy — P6 geopolitical inputs. | Until specific resource-dependent hypotheses emerge from scanning, this is background noise. | ~$40/mo |
| **Alpha Vantage / Polygon** | Earnings transcripts, financial data. | SEC EDGAR gives 10-K/10-Q free. Transcripts only useful once Agent B needs to verify specific recent-quarter incumbent claims. | Free-$30/mo |
| **Google Trends (pytrends)** | Search trend signals for timing validation. | Only after we have specific opportunities to test demand trajectory. Blind trend scans = noise. | Free |
| **LinkedIn Job Data** | Company-level job posting trends. | BLS covers occupation-level. LinkedIn adds company granularity — worth it after identifying specific incumbent sectors to monitor. | Varies |
| **INDEC (Argentina) / BCRA** | LATAM-specific economic data. | Not needed until LATAM POC opportunities are identified. Connect when we have a specific LATAM thesis to verify. | Free |

**Total Tier 3: ~$70/mo, mostly optional.**

---

### KILLED: APIs That Don't Pass Our Filter

| API | Kill Reason |
|-----|-------------|
| **ArXiv API** | Tracks AI research, not business signals. We need inference cost curves and capability thresholds, not model architectures. Cloud pricing pages + announcements cover this. |
| **Hugging Face API** | Same. Open model landscape doesn't produce signals mapping to business opportunities at our founding constraints. |
| **GitHub API** | Dev tooling popularity ≠ business signals. Trending repos don't tell us about liquidation cascades in service businesses. |
| **World Bank / IMF / OECD** | Too aggregated for systemic pattern detection. FRED + BLS cover US. For LATAM we need country-specific sources (INDEC, IBGE), not global aggregates. |
| **EIA Energy API** | Energy matters as a compute cost constraint, but cloud provider pricing pages give us the direct signal (inference cost at point of consumption). We don't need to model energy markets upstream. |
| **UN Population Division** | Demographic projections = H3 (5-10yr). BLS + Census cover US for H1/H2. Defer. |

---

### API Budget Summary

| Phase | APIs | Monthly Cost |
|-------|------|-------------|
| **Day 1** | BLS, FRED, SEC EDGAR, Serper | ~$50/mo |
| **Week 1** | + Crunchbase, X/Twitter, Reddit, HN | ~$249/mo |
| **After cycle 3** | + Trading Economics, Alpha Vantage, Google Trends, LATAM sources as needed | ~$320/mo max |

**Total at full speed: ~$320/mo.** At $500K-$1M capital, negligible. Each API connects when we have hypotheses to feed it.

---

## Social Accounts & Feeds to Monitor

**X/Twitter lists to build:**
- AI economics: @benedictevans, @levelsio, @paulg, @elaboratist
- Macro/geopolitics: @JavierBlas, @RobinBrooksIIF, @jessefelder
- LATAM angle: Argentina/LATAM tech and economics accounts
- Industry practitioners: Follow as sectors emerge from scanning

**Reddit:**
- Practitioner pain: r/smallbusiness, r/accounting, r/nursing, r/logistics, r/insurance
- AI capability: r/LocalLLaMA, r/MachineLearning, r/artificial
- Macro: r/economics, r/geopolitics

**Newsletters (curated signal, less noise):**
- Matt Levine (Bloomberg Money Stuff) — financial industry structure
- Doomberg — energy/commodities/physical economy
- Construction Physics — physical infrastructure/industry
- Apricitas Economics — macro data with analysis
- Ben Thompson (Stratechery) — tech strategy

---

## Self-Critique: Updated Design Assessment

### Strengths

1. **Systemic shift focus over industry-picking.** The engine looks for structural patterns. Industries emerge from data, not from guessing.

2. **Founding constraint gate runs first.** Agent B kills on constraints before wasting cycles on unit economics. This alone prevents the most common research-engine failure: producing ideas no one can execute.

3. **Kill index as institutional memory.** Dead-end patterns accumulate. The engine's immune system.

4. **P2 (Liquidation Cascade) is the sharpest principle.** Most AI analysis asks "what can AI improve?" We ask "where are businesses dying because of AI, and can we enter as they exit?" Different search = different results.

5. **LATAM as a POC accelerator.** Argentina access = test hypotheses against weaker incumbents before US attack.

### Watch Items

1. **Hard deadline: 4-6 cycles max before active pursuit.** Don't let the engine become the product. Within 6 cycles we need 2-3 opportunities in active development, or the engine is self-serving.

2. **Crunchbase early for P4.** Dead business revival is the most differentiated principle but needs specific failed-startup data. Prioritize.

3. **LATAM data gap.** If LATAM is a secondary operating geography, we need Argentina-specific sources (INDEC, BCRA, local startup databases) in Tier 3.

4. **Competitor scan: consider making proactive.** Currently reactive (after verification). Maybe lightweight competitive sweep on signals above threshold, not just verified ones.

---

## Running the Engine

### Quick Start

```bash
# 1. Start the UI
python scripts/serve_ui.py --port 8080
# Open http://localhost:8080/ui/

# 2. Initialize first cycle
python scripts/run_cycle.py --phase init \
  --directive "Systemic patterns: liquidation cascades + demographic gaps in US labor-intensive services"

# 3. Run Agent A — feed agent_a_trends_scanner.md as system prompt, scan directive as user message
#    Output → data/signals/2026-02-09.json

# 4. Run Agent C grading — feed agent_c_sync.md, signals as input
#    Output → data/grades/2026-02-09.json

# 5. Run Agent B verification — feed agent_b_practitioner.md, top signals as input
#    Output → data/verified/2026-02-09.json

# 6. Compile and update UI
python scripts/run_cycle.py --phase compile
```

### Automation Path

For automated cycles:
1. Claude API or OpenAI API with agent prompts as system messages
2. Runner script chaining agent calls with JSON data passing
3. Each full cycle: ~$2-10 in LLM API costs depending on model and volume
4. `scripts/run_cycle.py` handles data plumbing; agent execution via API calls

### Resolved Corrections

| Issue | Status | How |
|-------|--------|-----|
| Agent A scope too broad | **Fixed** | Systemic pattern focus, not industry lists |
| No competitor tracking | **Fixed** | Competitor scan mode added to Agent A |
| Static grading weights | **Fixed** | Dynamic weights per-cycle in Agent C |
| No kill-reason feedback | **Fixed** | Kill index in Agent C, referenced by Agent A |
| Founding constraints not enforced | **Fixed** | Constraint gate mandatory first step in Agent B |
| UI is read-only | **Deferred** | Phase 2 — not needed for initial cycles |
