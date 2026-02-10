#!/bin/bash
# ============================================================
# Parallel Claude Code Research Cycle Orchestrator
# ============================================================
#
# Launches research cycle phases using parallel Claude Code sessions.
# Each session acts as a specific agent, reading from and writing to
# shared data directories.
#
# USAGE:
#   ./scripts/run_parallel.sh [cycle_number]
#
# PREREQUISITES:
#   - Claude Code CLI installed and authenticated
#   - Data connectors configured (.env with API keys)
#   - Python3 with requirements installed
#
# The script runs in phases because agents depend on prior outputs:
#   Phase 1: SCAN  — Pull raw data (Python connectors, parallel)
#   Phase 2: AGENT A — Extract signals from raw data (Claude Code)
#   Phase 3: AGENT C — Grade and cluster signals (Claude Code)
#   Phase 4: AGENT B — Verify top opportunities (Claude Code)
#   Phase 5: MASTER — Synthesize and set direction (Claude Code)
#
# Within each phase, independent tasks run in parallel.
# Between phases, we wait for completion before proceeding.
# ============================================================

set -euo pipefail

PROJECT_DIR="/home/user/research"
CYCLE=${1:-$(date +%s)}
DATE=$(date +%Y-%m-%d)
TIMESTAMP=$(date -u +%Y-%m-%dT%H:%M:%SZ)

echo "=========================================="
echo "  Research Cycle $CYCLE — $DATE"
echo "=========================================="

# ---- Phase 1: SCAN (pull raw data) ----
echo ""
echo "[Phase 1] Pulling raw data from connectors..."

cd "$PROJECT_DIR"

# Run all connectors in parallel
python3 connectors/fred.py &
PID_FRED=$!
python3 connectors/bls.py &
PID_BLS=$!
python3 connectors/edgar.py &
PID_EDGAR=$!
python3 connectors/websearch.py &
PID_WEB=$!

# Wait for all connectors
wait $PID_FRED && echo "  [OK] FRED data pulled" || echo "  [WARN] FRED failed"
wait $PID_BLS && echo "  [OK] BLS data pulled" || echo "  [WARN] BLS failed"
wait $PID_EDGAR && echo "  [OK] EDGAR data pulled" || echo "  [WARN] EDGAR failed"
wait $PID_WEB && echo "  [OK] Web search data pulled" || echo "  [WARN] Web search failed"

echo "[Phase 1] Raw data collection complete."

# ---- Phase 2: AGENT A — Signal Extraction ----
echo ""
echo "[Phase 2] Launching Agent A (Signal Extraction)..."
echo "  Open a new terminal and run:"
echo ""
echo "  cd $PROJECT_DIR"
echo "  claude --print 'You are Agent A (Trends Scanner). Read your role from agents/agent_a_trends_scanner.md. Read raw data from data/raw/$DATE.json and the kill index from data/context/kill_index.json. Extract 20-50 signals following your signal extraction format. Write output to data/signals/$DATE.json. Include signal_id, source attribution, confidence levels, and kill_index_check for every signal.'"
echo ""
read -p "Press Enter when Agent A is complete..."

# ---- Phase 3: AGENT C — Grading & Clustering ----
echo ""
echo "[Phase 3] Launching Agent C (Grading & Clustering)..."
echo "  Open a new terminal and run:"
echo ""
echo "  cd $PROJECT_DIR"
echo "  claude --print 'You are Agent C (Sync/Orchestrator). Read your role from agents/agent_c_sync.md. Read signals from data/signals/$DATE.json, state from data/context/state.json, and kill index from data/context/kill_index.json. Grade each signal using the current grading weights. Cluster related signals. Forward signals scoring 5+ to verification. Write graded output to data/graded/$DATE.json. Update data/context/state.json with this cycle stats.'"
echo ""
read -p "Press Enter when Agent C grading is complete..."

# ---- Phase 4: AGENT B — Verification (can run multiple in parallel) ----
echo ""
echo "[Phase 4] Launching Agent B (Verification)..."
echo "  You can launch MULTIPLE Agent B sessions in parallel — one per opportunity."
echo "  Open new terminals and run:"
echo ""
echo "  cd $PROJECT_DIR"
echo "  claude --print 'You are Agent B (Practitioner/Accountant). Read your role from agents/agent_b_practitioner.md. Read graded opportunities from data/graded/$DATE.json and state from data/context/state.json. For EACH opportunity scoring 5+, run the full verification framework (V1-V7). Be skeptical — assume every opportunity is flawed until proven otherwise. Write verification results to data/verified/$DATE.json. Include unit economics, kill reasons for any KILLed opportunities, and VC differentiation scores.'"
echo ""
echo "  TIP: For faster processing, split opportunities across sessions:"
echo "  - Session 1: Verify opportunities 1-2"
echo "  - Session 2: Verify opportunities 3-5"
echo ""
read -p "Press Enter when all Agent B verifications are complete..."

# ---- Phase 5: MASTER — Synthesis ----
echo ""
echo "[Phase 5] Launching Master (Synthesis)..."
echo "  Open a new terminal and run:"
echo ""
echo "  cd $PROJECT_DIR"
echo "  claude --print 'You are the Master Agent. Read your role from agents/master.md. Read verified results from data/verified/$DATE.json, cycle summaries from data/context/cycle_summaries.json, state from data/context/state.json. Apply the Principles Engine filter. Identify cross-cycle patterns. Produce the Research Cycle output format. Write dashboard data to data/ui/dashboard.json and signals feed to data/ui/signals_feed.json. Update data/context/cycle_summaries.json with this cycle synthesis. Set direction for next cycle in data/context/state.json.'"
echo ""
read -p "Press Enter when Master synthesis is complete..."

# ---- Phase 6: COMMIT & PUSH ----
echo ""
echo "[Phase 6] Committing and pushing results..."
cd "$PROJECT_DIR"
git add data/ -A
git commit -m "Research Cycle $CYCLE — $DATE (parallel Claude Code sessions)" || echo "Nothing to commit"
git push -u origin claude/ai-economic-research-agents-F3iq8 || echo "Push failed — retry manually"

echo ""
echo "=========================================="
echo "  Cycle $CYCLE complete!"
echo "  Dashboard: https://monvinil.github.io/research/"
echo "=========================================="
