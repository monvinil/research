#!/bin/bash
# ============================================================
# Automated Research Cycle Orchestrator
# ============================================================
#
# Fully automated — no manual intervention required.
# Runs data connectors, then pipes each agent phase through
# claude -p (non-interactive print mode) sequentially.
#
# USAGE:
#   ./scripts/run_parallel.sh              # run next cycle
#   ./scripts/run_parallel.sh --cycle 5    # specify cycle number
#   ./scripts/run_parallel.sh --skip-scan  # reuse existing raw data
#
# Each phase writes to disk. Next phase reads from disk.
# Agent B can be parallelized by splitting opportunities.
# ============================================================

set -euo pipefail

PROJECT_DIR="/home/user/research"
DATE=$(date +%Y-%m-%d)
CYCLE=""
SKIP_SCAN=false
BRANCH="claude/ai-economic-research-agents-F3iq8"

# Parse args
while [[ $# -gt 0 ]]; do
  case $1 in
    --cycle) CYCLE="$2"; shift 2 ;;
    --skip-scan) SKIP_SCAN=true; shift ;;
    *) echo "Unknown arg: $1"; exit 1 ;;
  esac
done

# Auto-detect cycle number from state.json
if [ -z "$CYCLE" ]; then
  CYCLE=$(python3 -c "import json; print(json.load(open('$PROJECT_DIR/data/context/state.json'))['current_cycle'] + 1)" 2>/dev/null || echo "4")
fi

cd "$PROJECT_DIR"

log() { echo "[$(date +%H:%M:%S)] $1"; }

log "=========================================="
log "  RESEARCH CYCLE $CYCLE — $DATE"
log "=========================================="

# ---- Phase 1: SCAN ----
if [ "$SKIP_SCAN" = false ]; then
  log ""
  log "[Phase 1/5] Pulling raw data from connectors..."
  python3 scripts/run_cycle.py --scan-only 2>&1 | grep -E '^\[|OK|WARN|ERROR' || true
  log "[Phase 1/5] Data scan complete."
else
  log "[Phase 1/5] Skipped (--skip-scan). Using existing data/raw/$DATE.json"
fi

# ---- Phase 2: AGENT A ----
log ""
log "[Phase 2/5] Agent A — Signal extraction + competitor scans..."

claude -p --dangerously-skip-permissions --max-turns 30 "$(cat <<AGENT_A_PROMPT
You are Agent A — the Trends Scanner. Your ONLY job is to read data and write output files. No conversation.

STEP 1: Read these files:
- agents/agent_a_trends_scanner.md (your role)
- data/raw/$DATE.json (raw data from connectors)
- data/context/kill_index.json (kill patterns to avoid)
- data/context/state.json (current research state — read next_cycle_suggestions)
- data/context/cycle_summaries.json (previous cycle context)

STEP 2: Extract 25-40 signals from the raw data following your signal extraction JSON format.
Focus this cycle on:
- Competitor scan: who is doing "acquire distressed professional services + AI rebuild"?
- Competitor scan: who is doing "AI-augmented healthcare staffing"?
- P4 Dead Business Revival: failed startups 2015-2023 that died from labor/coordination costs
- LATAM: professional services distress in Argentina/Brazil
- Fresh P2: new bankruptcy, distressed M&A, PE roll-up announcements

STEP 3: Write output:
- Write signals to data/signals/${DATE}-c${CYCLE}.json
- Write competitor scans to data/competitors/${DATE}-c${CYCLE}.json

Do NOT explain. Do NOT ask questions. Just read, process, write.
AGENT_A_PROMPT
)" > /tmp/agent_a_cycle${CYCLE}.log 2>&1

log "[Phase 2/5] Agent A complete. Output: data/signals/${DATE}-c${CYCLE}.json"

# ---- Phase 3: AGENT C ----
log ""
log "[Phase 3/5] Agent C — Grading & clustering..."

claude -p --dangerously-skip-permissions --max-turns 20 "$(cat <<AGENT_C_PROMPT
You are Agent C — the Sync/Orchestrator. Your ONLY job is to read, grade, and write. No conversation.

STEP 1: Read these files:
- agents/agent_c_sync.md (your role)
- data/signals/${DATE}-c${CYCLE}.json (Agent A output from this cycle)
- data/ui/signals_feed.json (previous signals for deduplication)
- data/context/state.json (grading weights and running patterns)
- data/context/kill_index.json

STEP 2: Grade each signal using these weights:
- principles_alignment: 1.0, data_specificity: 1.3, source_quality: 1.0
- timeliness: 1.0, novelty: 0.7, cross_signal_reinforcement: 1.2

STEP 3: Cluster signals into systemic patterns. Deduplicate against previous cycle.

STEP 4: Write output:
- Write graded signals to data/graded/${DATE}-c${CYCLE}.json
- Update data/ui/signals_feed.json with combined feed
- Update data/context/state.json with grading stats

Do NOT explain. Do NOT ask questions. Just read, grade, write.
AGENT_C_PROMPT
)" > /tmp/agent_c_cycle${CYCLE}.log 2>&1

log "[Phase 3/5] Agent C complete. Output: data/graded/${DATE}-c${CYCLE}.json"

# ---- Phase 4: AGENT B ----
log ""
log "[Phase 4/5] Agent B — Deep verification (skeptic mode)..."

claude -p --dangerously-skip-permissions --max-turns 40 "$(cat <<AGENT_B_PROMPT
You are Agent B — the Practitioner/Accountant. You are a SKEPTIC. Your ONLY job is to stress-test opportunities and write verdicts. No conversation.

STEP 1: Read these files:
- agents/agent_b_practitioner.md (your role — read the FULL verification framework V1-V8)
- data/graded/${DATE}-c${CYCLE}.json (graded opportunities from Agent C)
- data/competitors/${DATE}-c${CYCLE}.json (competitor scans from Agent A)
- data/context/state.json (founding constraints)

STEP 2: For EACH opportunity scoring 5+, run the FULL verification framework (V1-V7).

CRITICAL REALITY CHECKS (apply to every opportunity):
- V1 unit economics: use ACTUAL current pricing. If claiming AI replaces a \$37/hr worker, calculate the REAL inference cost per task (tokens * price per token * error retry rate).
- Physical constraints: if the opportunity involves physical work (trucking, construction, healthcare), verify that proposed throughput is physically possible. A truck can only drive X miles/day. A nurse can only work Y hours. Account for sleep, regulation, turnover.
- Regulatory floor: name the SPECIFIC regulation. "HIPAA" is not enough — which section? What's the penalty? What's the compliance cost?
- Human limits: if proposing to "multiply" human capacity by 3x, show exactly which tasks are offloaded and verify the human can actually handle the remaining workload.
- Acquisition reality: if the thesis requires acquiring a business, check: are businesses of that type actually for sale? At what multiple? Use BizBuySell/DealStream norms.
- Customer switching: why would a customer leave their current provider? What's the ACTUAL switching cost (not just price, but risk, relationship, habit)?

STEP 3: Kill opportunities that deserve to die. The kill reason is an asset.

STEP 4: Write output:
- Write verification results to data/verified/${DATE}-c${CYCLE}.json
- Include: unit economics model, kill reasons, VC differentiation score (1-10), fatal flaws, and manageable risks for each opportunity.

Be BRUTAL. If everything passes verification, your filter is broken.
Do NOT explain. Do NOT ask questions. Just read, verify, write.
AGENT_B_PROMPT
)" > /tmp/agent_b_cycle${CYCLE}.log 2>&1

log "[Phase 4/5] Agent B complete. Output: data/verified/${DATE}-c${CYCLE}.json"

# ---- Phase 5: MASTER ----
log ""
log "[Phase 5/5] Master — Synthesis & direction setting..."

claude -p --dangerously-skip-permissions --max-turns 25 "$(cat <<MASTER_PROMPT
You are the Master Agent. Your ONLY job is to synthesize results and set direction. No conversation.

STEP 1: Read these files:
- agents/master.md (your role)
- data/verified/${DATE}-c${CYCLE}.json (Agent B verification results)
- data/competitors/${DATE}-c${CYCLE}.json (competitor scans)
- data/graded/${DATE}-c${CYCLE}.json (graded signals)
- data/context/cycle_summaries.json (previous cycle syntheses)
- data/context/state.json (current engine state)

STEP 2: Apply Principles Engine filter (P1-P6) to all verified opportunities.
STEP 3: Compare to previous cycles — what strengthened? Weakened? New?
STEP 4: Identify cross-cycle patterns.
STEP 5: Set direction for Cycle $((CYCLE + 1)).

STEP 6: Write output:
- Write data/ui/dashboard.json (full dashboard with top_opportunities, master_synthesis, cross_principle_patterns, cycle_history)
- Update data/ui/signals_feed.json
- Update data/context/cycle_summaries.json (add Cycle $CYCLE synthesis)
- Update data/context/state.json (set next cycle direction, update weights if needed)
- Update data/context/kill_index.json (add any KILL verdicts from Agent B)

Do NOT explain. Do NOT ask questions. Just read, synthesize, write.
MASTER_PROMPT
)" > /tmp/master_cycle${CYCLE}.log 2>&1

log "[Phase 5/5] Master synthesis complete."

# ---- Phase 6: COMMIT & PUSH ----
log ""
log "Committing and pushing Cycle $CYCLE results..."

cd "$PROJECT_DIR"
git add data/ -A
git commit -m "Research Cycle $CYCLE — $DATE (automated orchestrator)" 2>/dev/null || log "Nothing new to commit"

# Push with retry
for attempt in 1 2 3 4; do
  if git push -u origin "$BRANCH" 2>/dev/null; then
    log "Pushed to $BRANCH"
    break
  else
    delay=$((2 ** attempt))
    log "Push failed, retrying in ${delay}s (attempt $attempt/4)..."
    sleep $delay
  fi
done

log ""
log "=========================================="
log "  CYCLE $CYCLE COMPLETE"
log "  Dashboard: https://monvinil.github.io/research/"
log "  Logs: /tmp/agent_*_cycle${CYCLE}.log"
log "=========================================="
