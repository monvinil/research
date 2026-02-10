# Design Review — Automation, Analytical Model, Research Edge

**Date:** 2026-02-10
**Reviewer context:** Full codebase review, all agent prompts, all data files, run_cycle.py, run_parallel.sh, connectors, state, cycle summaries.

---

## Overall Assessment

The Principles Engine (P1-P6 + emerging P7) is the strongest part of this project. It asks a different question than standard AI research: not "what can AI improve?" but "where are businesses dying from structural shifts, and can we enter as they exit?" This produces different results than the 500 generic AI pitches VCs see monthly.

The agent architecture is well-separated, the verification framework (Agent B's V1-V8) is unusually rigorous, and the kill index concept is sound.

Three structural problems need addressing: automation is not using available compute, the analytical model has confirmation bias, and the engine is approaching its own self-imposed deadline without forcing decisions.

---

## A) Automation Optimization

### Current Problems

1. **`run_parallel.sh` isn't parallel.** Runs Agent A → C → B → Master sequentially. Each `claude -p` call is blocking. With Claude Max 20x = 20 concurrent sessions, you're using 1 at a time.

2. **No scheduling or daemon.** No cron, no loop, no continuous execution. Requires manual invocation.

3. **No checkpoint/resume.** If Agent B crashes at phase 4/5, entire cycle is lost. Re-runs from scratch including data pull.

4. **No error handling for LLM output.** `parse_json_response` in `run_cycle.py` does best-effort JSON extraction. No retry, no fallback, no "fix your output" loop.

5. **Data connectors don't match data freshness.** FRED updates monthly, BLS quarterly, EDGAR continuously, web search real-time. All pulled at same frequency every cycle.

6. **No monitoring.** Logs go to `/tmp`. No alerts, no health checks, no cost tracking per cycle.

### Recommended Architecture for Claude Max 20x on Dedicated Machine

```
┌─────────────────────────────────────────────────────────┐
│                    CYCLE DAEMON                          │
│  Python process running continuously on dedicated box    │
│  Schedules cycles, manages session pool, handles errors  │
└────────────┬────────────────────────────────────────────┘
             │
    ┌────────▼────────┐
    │  SESSION POOL   │  20 sessions (Max 20x)
    │  manager        │  Tracks: busy/idle, phase, runtime
    └────────┬────────┘
             │
  ┌──────────┼──────────────────────────┐
  │          │                          │
  ▼          ▼                          ▼
SCAN PHASE  ANALYSIS PHASE         VERIFY PHASE
(2 sessions) (2 sessions)          (up to 5 sessions)
             │                          │
  Connector  Agent A ──► Agent C   Agent B × N opportunities
  refresh    (1 session)  (1 session)  (1 session each)
  (1 session)                           │
             │                          │
             └──────────┬───────────────┘
                        ▼
                   MASTER (1 session)
                        │
                        ▼
                   COMPILE + PUSH
```

**Session allocation (20 total):**
| Purpose | Sessions | Notes |
|---------|----------|-------|
| Data connectors (parallel) | 2 | EDGAR + web concurrent |
| Agent A signal extraction | 1 | Full context window per scan |
| Agent C grading | 1 | |
| Agent B verification | 5 | 1 per opportunity, parallel |
| Master synthesis | 1 | |
| Reserve (retry, ad-hoc, overlap) | 10 | Deep dives, investigation |

### Specific Implementation Changes

**1. Replace `run_parallel.sh` with Python daemon:**
- Runs cycles on configurable schedule (default: every 6 hours)
- Uses `subprocess` to spawn concurrent `claude -p` calls
- Checkpoint files per phase (`data/checkpoints/cycle-N-phase-3.json`)
- On failure, resumes from last completed checkpoint
- Tracks session usage across 20 available slots

**2. Parallelize Agent B verification:**
- Current: 1 call with all 5 opportunities sharing 16K output tokens
- Proposed: 5 concurrent calls, each with 1 opportunity + full context
- Each opportunity gets full context window for deeper verification

**3. Stagger data connector refresh:**

| Source | Refresh Frequency | Reason |
|--------|-------------------|--------|
| FRED | Weekly | Data updates monthly |
| BLS | Weekly | Data updates quarterly |
| EDGAR | Every cycle | Continuous filing flow |
| Web search | Every cycle | Real-time, rotate query sets |

**4. LLM output retry loop:**
```python
def llm_call_with_retry(system, user, model, max_retries=2):
    for attempt in range(max_retries + 1):
        response = llm_call(system, user, model)
        try:
            return parse_json_response(response)
        except ValueError:
            if attempt < max_retries:
                user += "\n\nPrevious response was not valid JSON. Return ONLY valid JSON."
            else:
                raise
```

**5. Monitoring layer:**
- Write cycle status to `data/context/monitor.json` (phase, start_time, errors, tokens)
- Webhook/email on completion or failure
- Track cost per cycle (tokens × price)
- Alert when kill index empty for 3+ cycles (filter miscalibration)

**6. Pipeline overlap:**
- While Agent B verifies cycle N, Agent A starts scanning for cycle N+1
- Doubles throughput at cost of 2 additional sessions

### Cycle frequency sweet spot

With 20x Max and a dedicated machine: ~$200/day of Opus compute available. Each full cycle uses ~100K tokens across agents. Theoretical max: 15-20 cycles/day. Practical sweet spot: **4 cycles/day** (every 6 hours). Data sources don't update fast enough to justify more.

---

## B) Analytical Model & Research Edge

### Current Problems

**1. Kill index is empty after 5 cycles.** Biggest red flag. 5 opportunities verified, 0 killed. Every recommendation is INVESTIGATE_FURTHER. The engine isn't making decisions. A functional immune system should have killed something by now.

**2. No signal lifecycle tracking.** Signals are per-cycle snapshots. No mechanism to track whether `prof_services_neg_97k` got stronger or weaker between cycles 3 and 5. Cross-cycle patterns in `running_patterns` are manually noted, not algorithmically detected.

**3. No counter-signal search.** Agent A scans for evidence supporting the Principles Engine. Nobody systematically searches for evidence *against* top opportunities. Confirmation bias is baked into the architecture.

**4. Connector stack produces macro data, not actionable intelligence.** FRED/BLS/EDGAR tell you about trends. They can't answer:
- Are distressed CPA firms actually for sale? At what price?
- Who else is doing "acquire + AI rebuild"?
- What do actual practitioners say about their industry?
- What's real client retention post-acquisition?

These are Agent B's "key unknowns" that the connector stack can't resolve.

**5. No inference cost time series.** P1 and P3 depend on cost trajectories but the engine has no structured tracking of actual API pricing over time.

**6. No calibration.** After 5 cycles, no way to measure whether the engine is improving.

### Recommended Analytical Model

**1. Signal Lifecycle System**

Replace snapshot signals with persistent signal store:
```json
{
  "signal_id": "SIG-001",
  "first_observed": "cycle 3",
  "observations": [
    {"cycle": 3, "value": "-97K", "source": "BLS", "confidence": "high"},
    {"cycle": 5, "value": "-102K", "source": "BLS", "confidence": "high"}
  ],
  "trend": "strengthening",
  "last_observed": "cycle 5",
  "decay_cycles_without_observation": 0,
  "linked_opportunities": ["OPP-001"]
}
```
Signals not reinforced for 3+ cycles get automatic confidence decay.

**2. Counter-Signal Mandate (add to Agent A)**

For each top-3 opportunity from previous cycle, Agent A must produce at least 2 counter-signals:
- Companies that tried this thesis and failed recently
- Industries where predicted cascades reversed
- Regulatory changes blocking the thesis
- Evidence that incumbents ARE successfully restructuring

Add `counter_signals` field. If counter count > supporting count → auto-flag.

**3. Deal Flow Connector (highest priority new data source)**

Biggest data gap is real transaction data:
- BizBuySell listings for distressed professional services
- DealStream for business-for-sale data
- State SOS filings for business dissolutions
- PACER for actual bankruptcy filing counts

Transforms engine from theoretical to actionable.

**4. Practitioner Sentiment Pipeline**

Structured Reddit/HN/forum scraping:
- r/accounting: "leaving the profession" posts
- r/nursing: staffing ratio discussions, burnout
- r/smallbusiness: closures, cost pressure
- HN: "I replaced X with AI", failed startup postmortems

Score sentiment by industry, track over time. Leading indicator: practitioner complaints precede BLS data by 6-12 months.

**5. Inference Cost Tracker**

Weekly tracking of:
- Anthropic, OpenAI, Google API pricing (input/output per model)
- Open-source equivalent costs (vLLM on spot instances)

Plot against opportunity viability thresholds: "At $X/1M tokens, opportunity Y becomes viable."

**6. Decision Forcing Function**

Hard rules that prevent perpetual investigation:
- After 3 verification cycles on same opportunity → must be PURSUE or KILL
- Opportunity in "scanning" for 3+ cycles without verification → auto-deprioritize
- Kill index empty for 3 consecutive cycles → flag Agent B miscalibration, inject calibration prompt

**7. Calibration Metrics**

Track per-cycle:
- Signal count, avg relevance score, score distribution
- Agent B pursue/kill/investigate ratio
- Top opportunity score trajectory
- Data freshness per source
- Token usage per agent

---

## C) Other Comments

### 1. Self-imposed deadline

EVALUATION.md says "4-6 cycles max before active pursuit." Engine is at cycle 5. Next cycle should be the last pure-research cycle. Cycle 6 output should be concrete action items, not more investigation.

### 2. Top opportunity is strong but unverified where it matters

"Distressed Professional Services Acquisition" (score 87) has strong macro data. Key unknowns are all micro-level:
- Real acquisition prices (not estimated ranges)
- Real client retention rates post-acquisition
- Regulatory transfer rules (does CPA license transfer with business acquisition in California?)

These require a call to a business broker and CPA licensing board, not more API data. The engine should output these as specific action items with contact information.

### 3. Missing: the "so what" layer

Engine produces: `Distressed Professional Services Acquisition (score 87, INVESTIGATE_FURTHER)`

Should produce:
```
ACTION ITEMS — Distressed Professional Services Acquisition
1. Search BizBuySell for CPA/bookkeeping firms for sale in CA, TX, FL
   → Filter: asking price <$300K, established client book
2. Call CA Board of Accountancy: does CPA firm license transfer
   with business acquisition?
3. Contact 2-3 business brokers in professional services: actual
   market price for distressed 1-5 person CPA firms?
4. Pull EDGAR: mid-size firms (BDO, Marcum, CBIZ) 10-K for
   cost structure baseline
```

Add action item generation to Master agent output format.

### 4. Connector priority for dedicated machine

**Immediate adds (highest edge per dollar):**

| Connector | Cost | Why |
|-----------|------|-----|
| Reddit API | Free | Practitioner sentiment, leading indicator |
| Hacker News API | Free | Failed startup postmortems, P4 data |
| BizBuySell/DealStream scraper | Free (scrape) | Real deal flow, answers top unknowns |
| Crunchbase | ~$99/mo | Dead business revival database, P4 primary source |

**Skip for now:**
- Twitter/X ($100/mo) — noisy, redundant with Reddit
- Trading Economics ($40/mo) — not useful until resource-dependent hypotheses emerge

### 5. Agent prompt refinements

- **Agent A**: Add counter-signal mandate for top-3 opportunities
- **Agent B**: Add decision forcing after 3 verification cycles (PURSUE or KILL only)
- **Agent C**: Implement signal lifecycle tracking across cycles (not just per-cycle grading)
- **Master**: Add action item generation — every verified opportunity produces 3-5 concrete next steps

### 6. Context window saturation risk

Each `claude -p` call starts fresh. Agent prompts = ~2-4K tokens. Raw data + context can hit 30-50K. As cycles accumulate, context summaries grow and useful data gets truncated.

`save_context_summary` in `run_cycle.py:93-100` does basic truncation but not semantic compression. After 10 cycles, compressed summaries will be gibberish.

Fix: implement proper context compression — summarize old cycles into structured data points rather than truncating narrative text.

### 7. Operational rhythm for dedicated machine

| Activity | Frequency | Sessions used |
|----------|-----------|---------------|
| Full automated cycle | Every 6 hours | 10 |
| Human review + direction adjustment | 1-2x daily | 0 |
| Ad-hoc deep dives | As needed | 1-5 from reserve |
| Connector data refresh (FRED/BLS) | Weekly | 1 |
| Connector data refresh (EDGAR/Web) | Every cycle | 2 |

---

## Summary of Priorities

**Immediate (before next cycle):**
1. Force Agent B to PURSUE or KILL the top 2 opportunities — no more INVESTIGATE_FURTHER
2. Add counter-signal search to Agent A
3. Add action item generation to Master output

**This week (dedicated machine setup):**
4. Build Python daemon replacing `run_parallel.sh` with parallel sessions + checkpointing
5. Add Reddit + HN connectors (free, high signal)
6. Add BizBuySell scraper (answers the #1 unknown)
7. Implement signal lifecycle tracking

**Ongoing:**
8. Calibration dashboard
9. Inference cost tracker
10. Context compression improvement
