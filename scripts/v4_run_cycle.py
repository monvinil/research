#!/usr/bin/env python3
"""v4 Research Cycle Runner — Narrative-first economy map pipeline.

Extends run_cycle.py with v4 collision detection, narrative updates,
and cascade mapping. Uses the same connector infrastructure and LLM routing.

v4 Pipeline:
  Phase 1:   SCAN — pull live data from 12 connectors (unchanged)
  Phase 1.5: ANALYTICS — derived indicators (unchanged)
  Phase 2:   AGENT A — collision evidence scanning (v4 prompts)
  Phase 3:   AGENT C — collision clustering + signal grading (v4 prompts)
  Phase 3.5: COLLISION DETECTOR — algorithmic collision matching (NEW)
  Phase 4:   AGENT B — narrative construction/update (v4 prompts)
  Phase 5:   MASTER — economy map synthesis (v4 prompts)
  Phase 6:   COMPILE — narrative scoring + UI generation (v4 scripts)

Usage:
    python scripts/v4_run_cycle.py                   # full v4 cycle
    python scripts/v4_run_cycle.py --scan-only        # data pull only
    python scripts/v4_run_cycle.py --analytics-only   # scan + analytics
    python scripts/v4_run_cycle.py --skip-narratives   # skip Agent B narrative update
    python scripts/v4_run_cycle.py --model opus       # use opus for all agents
    python scripts/v4_run_cycle.py --verbose          # show raw LLM responses
    python scripts/v4_run_cycle.py --use-api          # use Anthropic API
"""

import argparse
import json
import os
import subprocess
import sys
import time
import traceback
from datetime import datetime, timezone
from pathlib import Path

# ---------------------------------------------------------------------------
# Setup
# ---------------------------------------------------------------------------

PROJECT_ROOT = Path(__file__).resolve().parent.parent
DATA_DIR = PROJECT_ROOT / "data"
V4_DIR = DATA_DIR / "v4"
AGENTS_DIR = PROJECT_ROOT / "agents"
SCRIPTS_DIR = PROJECT_ROOT / "scripts"

sys.path.insert(0, str(PROJECT_ROOT))

# Load .env
_env_path = PROJECT_ROOT / ".env"
if _env_path.exists():
    with open(_env_path) as f:
        for line in f:
            line = line.strip()
            if line and not line.startswith("#") and "=" in line:
                key, val = line.split("=", 1)
                os.environ.setdefault(key.strip(), val.strip())


# ---------------------------------------------------------------------------
# I/O helpers
# ---------------------------------------------------------------------------

def load_json(path):
    path = Path(path)
    if path.exists():
        with open(path) as f:
            return json.load(f)
    return None


def save_json(path, data):
    path = Path(path)
    path.parent.mkdir(parents=True, exist_ok=True)
    with open(path, "w") as f:
        json.dump(data, f, indent=2, ensure_ascii=False)


def load_v4_state():
    """Load v4 state (primary) with fallback to v3 state for cycle count."""
    v4_state = load_json(V4_DIR / "state.json") or {}
    v3_state = load_json(DATA_DIR / "context" / "state.json") or {}

    # Ensure cycle counter exists
    if "current_cycle" not in v4_state:
        v4_state["current_cycle"] = "v4-0"

    # Carry forward v3 context references
    v4_state["_v3_cycle"] = v3_state.get("current_cycle", 0)

    return v4_state


def save_v4_state(state):
    # Remove transient keys
    clean = {k: v for k, v in state.items() if not k.startswith("_")}
    save_json(V4_DIR / "state.json", clean)


def bump_cycle(state):
    """Increment the v4 cycle counter: v4-0 → v4-1 → v4-2 ..."""
    current = state.get("current_cycle", "v4-0")
    try:
        num = int(current.split("-")[-1])
    except (ValueError, IndexError):
        num = 0
    state["current_cycle"] = f"v4-{num + 1}"
    return state["current_cycle"]


def load_agent_prompt(name):
    path = AGENTS_DIR / name
    with open(path) as f:
        return f.read()


def load_context_summaries():
    path = DATA_DIR / "context" / "cycle_summaries.json"
    return load_json(path) or {"cycles": []}


def save_context_summary(cycle_id, summary):
    path = DATA_DIR / "context" / "cycle_summaries.json"
    data = load_json(path) or {"cycles": []}
    data["cycles"].append({
        "cycle": cycle_id,
        "date": datetime.now(timezone.utc).isoformat(),
        "summary": summary,
    })
    if len(data["cycles"]) > 10:
        old = data["cycles"][:-10]
        data["compressed"] = data.get("compressed", "") + "\n".join(
            f"Cycle {c['cycle']}: {(c.get('summary') or '')[:200]}" for c in old
        ) + "\n"
        data["cycles"] = data["cycles"][-10:]
    save_json(path, data)


def load_kill_index():
    path = DATA_DIR / "context" / "kill_index.json"
    return load_json(path) or {"kill_patterns": [], "stats": {}}


# ---------------------------------------------------------------------------
# LLM Engine (imported from run_cycle.py)
# ---------------------------------------------------------------------------

MODELS = {
    "sonnet": "claude-sonnet-4-5-20250929",
    "opus": "claude-opus-4-6",
    "haiku": "claude-haiku-4-5-20251001",
}

_client = None
_total_input_tokens = 0
_total_output_tokens = 0
_use_api = False


def get_client():
    global _client
    if _client is None:
        import anthropic
        api_key = os.environ.get("ANTHROPIC_API_KEY", "")
        if not api_key:
            raise RuntimeError("ANTHROPIC_API_KEY not set.")
        _client = anthropic.Anthropic(api_key=api_key)
    return _client


def llm_call_cli(system_prompt, user_message, model="sonnet", max_tokens=8192):
    import shutil
    claude_path = shutil.which("claude")
    if not claude_path:
        for path in ["/usr/local/bin/claude", os.path.expanduser("~/.local/bin/claude"),
                     os.path.expanduser("~/.npm/bin/claude")]:
            if os.path.exists(path):
                claude_path = path
                break

    if not claude_path:
        print("    [CLI] claude binary not found — falling back to API")
        if os.environ.get("ANTHROPIC_API_KEY"):
            return llm_call_api(system_prompt, user_message, model, max_tokens)
        raise RuntimeError("Neither claude CLI nor ANTHROPIC_API_KEY available.")

    model_id = MODELS.get(model, model)
    combined_prompt = f"{system_prompt}\n\n---\n\n{user_message}"

    t0 = time.time()
    result = subprocess.run(
        [claude_path, "--print", "--model", model_id, "--max-tokens", str(max_tokens)],
        input=combined_prompt,
        capture_output=True, text=True, timeout=300,
    )
    elapsed = time.time() - t0
    text = result.stdout.strip()

    if result.returncode != 0:
        err = result.stderr.strip()
        print(f"    [CLI {model}] ERROR: {err[:200]}")
        if os.environ.get("ANTHROPIC_API_KEY"):
            print("    Falling back to API...")
            return llm_call_api(system_prompt, user_message, model, max_tokens)
        raise RuntimeError(f"Claude CLI failed: {err[:500]}")

    chars = len(text)
    est_tokens = chars // 4
    print(f"    [CLI {model}] ~{est_tokens:,} tokens / {elapsed:.1f}s")
    return text


def llm_call_api(system_prompt, user_message, model="sonnet", max_tokens=8192):
    global _total_input_tokens, _total_output_tokens
    client = get_client()
    model_id = MODELS.get(model, model)

    t0 = time.time()
    response = client.messages.create(
        model=model_id,
        max_tokens=max_tokens,
        system=system_prompt,
        messages=[{"role": "user", "content": user_message}],
    )
    elapsed = time.time() - t0
    usage = response.usage
    _total_input_tokens += usage.input_tokens
    _total_output_tokens += usage.output_tokens

    text = response.content[0].text
    print(f"    [{model_id}] {usage.input_tokens} in / {usage.output_tokens} out / {elapsed:.1f}s")
    return text


def llm_call(system_prompt, user_message, model="sonnet", max_tokens=8192):
    if _use_api:
        return llm_call_api(system_prompt, user_message, model, max_tokens)
    return llm_call_cli(system_prompt, user_message, model, max_tokens)


def parse_json_response(text):
    import re
    text = text.strip()
    if text.startswith("{") or text.startswith("["):
        try:
            return json.loads(text)
        except json.JSONDecodeError:
            pass

    blocks = re.findall(r"```(?:json)?\s*\n?(.*?)\n?```", text, re.DOTALL)
    for block in blocks:
        try:
            return json.loads(block.strip())
        except json.JSONDecodeError:
            continue

    for sc, ec in [("{", "}"), ("[", "]")]:
        start = text.find(sc)
        if start == -1:
            continue
        depth = 0
        for i in range(start, len(text)):
            if text[i] == sc:
                depth += 1
            elif text[i] == ec:
                depth -= 1
            if depth == 0:
                try:
                    return json.loads(text[start:i + 1])
                except json.JSONDecodeError:
                    break

    raise ValueError(f"Could not parse JSON from LLM response:\n{text[:500]}...")


# ---------------------------------------------------------------------------
# Data formatting — import from run_cycle.py
# ---------------------------------------------------------------------------

# Import formatting functions from run_cycle.py
sys.path.insert(0, str(SCRIPTS_DIR))
try:
    from run_cycle import (
        format_fred_data, format_bls_data, format_edgar_data,
        format_web_data, format_international_data, format_market_data,
        format_analytics_for_agent, phase_scan, phase_analytics,
    )
    _HAS_V3_RUNNER = True
except ImportError:
    _HAS_V3_RUNNER = False
    print("  WARNING: Could not import from run_cycle.py — scan/analytics unavailable")


# ---------------------------------------------------------------------------
# v4 Agent Message Formatting
# ---------------------------------------------------------------------------

def format_for_agent_a_v4(raw, context_summaries, kill_index, v4_state,
                           analytics_result=None):
    """Build Agent A user message with v4 collision-awareness."""
    sections = []

    # Derived analytics
    if analytics_result and _HAS_V3_RUNNER:
        sections.append("# DERIVED ANALYTICS\n")
        sections.append(format_analytics_for_agent(analytics_result))

    # Raw data
    if _HAS_V3_RUNNER:
        sections.append("# RAW DATA FROM THIS CYCLE'S SCAN\n")
        sections.append(format_fred_data(raw))
        sections.append(format_bls_data(raw))
        sections.append(format_market_data(raw))
        sections.append(format_edgar_data(raw))
        sections.append(format_web_data(raw))
        sections.append(format_international_data(raw))

    # v4 context: force velocities
    fv = v4_state.get("force_velocities", {})
    if fv:
        sections.append("# CURRENT FORCE VELOCITIES\n")
        for fid, data in fv.items():
            vel = data.get("velocity", "steady")
            conf = data.get("confidence", "medium")
            sections.append(f"  {fid}: {vel} (confidence: {conf})")
            km = data.get("key_metrics", {})
            if isinstance(km, dict):
                for k, v in list(km.items())[:3]:
                    sections.append(f"    {k}: {v}")
        sections.append("")

    # v4 context: active collisions (top 10 by last evidence)
    collisions = load_json(V4_DIR / "collisions.json") or {}
    colls = collisions.get("collisions", [])
    if colls:
        sections.append("# ACTIVE COLLISIONS (reference when tagging signals)\n")
        for c in colls[:20]:
            forces = [f["force_id"] for f in c.get("forces", [])]
            sections.append(f"  {c['collision_id']}: {' × '.join(forces)} — "
                            f"{c.get('name', '')[:60]} [{c.get('collision_type', '')}]")
        sections.append("")

    # v4 context: top narratives
    narratives = load_json(V4_DIR / "narratives.json") or {}
    narrs = narratives.get("narratives", [])
    if narrs:
        sections.append("# TOP TRANSFORMATION NARRATIVES (reference when tagging signals)\n")
        for n in narrs[:10]:
            tns = n.get("tns", {})
            sections.append(f"  {n['narrative_id']}: {n['name'][:50]} "
                            f"[TNS {tns.get('composite', 0):.0f}, {tns.get('category', '')}]")
        sections.append("")

    # Previous cycle context
    cycles = context_summaries.get("cycles", [])
    if cycles:
        sections.append("# CONTEXT FROM PREVIOUS CYCLES\n")
        for c in cycles[-3:]:
            sections.append(f"## Cycle {c['cycle']} ({c.get('date', '?')[:10]})")
            summary = c.get("summary") or c.get("master_synthesis") or ""
            if summary:
                sections.append(summary[:2000])
            sections.append("")

    # Kill index
    patterns = kill_index.get("kill_patterns", [])
    if patterns:
        sections.append("# KILL INDEX\n")
        for p in patterns:
            if p.get("still_active", True):
                sections.append(f"- [{p.get('pattern_id', '?')}] {p.get('kill_reason', '?')}")
        sections.append("")

    # v4 scan directive
    sections.append("# v4 SCAN DIRECTIVE")
    sections.append(
        "Scan for COLLISION EVIDENCE — signals where 2+ forces interact. "
        "Tag each signal with collision_pair, collision_id_ref (if matches existing collision), "
        "and narrative_id_ref (if relevant to existing narrative)."
    )
    sections.append("")
    sections.append("Signal type distribution target:")
    sections.append("  - 60%+ collision_evidence (2+ forces interacting)")
    sections.append("  - 10%+ cascade_transmission (collision→downstream)")
    sections.append("  - 10%+ timeline_evidence (year-specific collision proof)")
    sections.append("  - Remainder: force_velocity, geographic_variation, collision_friction")
    sections.append("")
    sections.append(
        "Extract 30-60 signals. Return a JSON array of signal objects "
        "following the v4 Signal Extraction Format. Include collision_pair for "
        "every multi-force signal. Reference existing FC-NNN and TN-NNN IDs."
    )
    sections.append("")
    sections.append("Return ONLY a JSON array of signal objects. No preamble.")

    return "\n".join(sections)


def format_for_agent_c_v4(signals, v4_state, kill_index):
    """Build Agent C user message with v4 collision clustering."""
    sections = []

    sections.append("# SIGNALS FROM AGENT A\n")
    sections.append(json.dumps(signals, indent=2)[:20000])

    sections.append("\n# CURRENT v4 STATE\n")
    # Send force velocities + entity counts (not full state)
    slim_state = {
        "current_cycle": v4_state.get("current_cycle", "v4-0"),
        "force_velocities": {
            fid: {"velocity": fv.get("velocity"), "confidence": fv.get("confidence")}
            for fid, fv in v4_state.get("force_velocities", {}).items()
        },
        "entity_counts": v4_state.get("entity_counts", {}),
    }
    sections.append(json.dumps(slim_state, indent=2))

    sections.append("\n# EXISTING COLLISIONS (for matching)\n")
    collisions = load_json(V4_DIR / "collisions.json") or {}
    coll_slim = [
        {
            "collision_id": c["collision_id"],
            "name": c.get("name", ""),
            "forces": [f["force_id"] for f in c.get("forces", [])],
            "sectors": c.get("sectors_affected", []),
            "type": c.get("collision_type", ""),
        }
        for c in collisions.get("collisions", [])
    ]
    sections.append(json.dumps(coll_slim, indent=2)[:5000])

    sections.append("\n# KILL INDEX\n")
    sections.append(json.dumps(kill_index, indent=2)[:2000])

    sections.append("\n# v4 INSTRUCTIONS")
    sections.append("1. Grade each signal using the 6-dimension rubric (0-10)")
    sections.append("2. CLUSTER signals into collision groups by force pair + sector")
    sections.append("3. Match collision groups to existing FC-NNN collisions")
    sections.append("4. Identify new collision hypotheses (2+ signals, unmatched force pair)")
    sections.append("5. Update force velocity assessments based on signals")
    sections.append("6. Detect cascade transmission signals")
    sections.append("")
    sections.append("Return a JSON object:")
    sections.append("```json")
    sections.append("""{
  "graded_signals": [...signals with relevance_score, collision_pair added...],
  "collision_groups": [
    {
      "collision_id": "FC-NNN or NEW",
      "force_pair": ["F1_technology", "F2_demographics"],
      "strength": "emerging|moderate|strong",
      "signal_count": N,
      "sectors": ["NAICS"],
      "key_evidence": ["headline1", "headline2"]
    }
  ],
  "force_velocity_updates": {
    "F1_technology": {"velocity": "accelerating", "confidence": "high", "key_change": "..."}
  },
  "cascade_transmissions": [
    {"from": "FC/TN-NNN", "to": "FC/TN-NNN", "mechanism": "...", "strength": "..."}
  ],
  "new_collision_hypotheses": [
    {"force_pair": [...], "sectors": [...], "evidence": "...", "suggested_name": "..."}
  ],
  "next_cycle_suggestions": ["..."]
}""")
    sections.append("```")
    sections.append("Return ONLY the JSON object. No preamble.")

    return "\n".join(sections)


def format_for_agent_b_v4(collision_updates, graded_signals, v4_state):
    """Build Agent B user message for narrative construction/update."""
    sections = []

    # Collision updates (primary input)
    sections.append("# COLLISION UPDATES THIS CYCLE\n")
    sections.append("## Strengthened Collisions")
    for s in collision_updates.get("strengthened", [])[:10]:
        sections.append(f"  {s['collision_id']}: {s['signal_count']} signals, "
                        f"strength={s['strength']} — {s['collision_name'][:60]}")
        for h in s.get("signal_headlines", [])[:3]:
            sections.append(f"    - {h}")
    sections.append("")

    sections.append("## New Collision Hypotheses")
    for n in collision_updates.get("new_hypotheses", [])[:5]:
        sections.append(f"  {n['pair_key']}: {n['signal_count']} signals — "
                        f"{n['suggested_name'][:60]}")
    sections.append("")

    sections.append("## Cascade Transmissions")
    for c in collision_updates.get("cascade_signals", [])[:5]:
        sections.append(f"  {c.get('from_collision', '')} → {', '.join(c.get('downstream', []))}")
        sections.append(f"    {c['headline'][:80]}")
    sections.append("")

    # Narrative evidence matches
    sections.append("## Narrative Evidence Matches")
    for nm in collision_updates.get("narrative_matches", [])[:10]:
        sections.append(f"  {nm['narrative_id']}: {nm['signal_count']} new signals — "
                        f"{nm['narrative_name'][:50]}")
    sections.append("")

    # Top graded signals for context
    sections.append("# TOP GRADED SIGNALS (score >= 6)\n")
    top_signals = [s for s in graded_signals if s.get("relevance_score", 0) >= 6]
    top_signals.sort(key=lambda s: s.get("relevance_score", 0), reverse=True)
    for s in top_signals[:20]:
        sections.append(f"  [{s.get('relevance_score', 0)}] {s.get('headline', '?')[:80]}")
        detail = s.get("detail", "")
        if detail:
            sections.append(f"      {detail[:150]}")
    sections.append("")

    # Current narratives (for update context)
    narratives = load_json(V4_DIR / "narratives.json") or {}
    narrs = narratives.get("narratives", [])
    sections.append("# CURRENT TRANSFORMATION NARRATIVES\n")
    for n in narrs:
        tns = n.get("tns", {})
        outputs = n.get("outputs", {})
        total_models = sum(len(outputs.get(b, [])) for b in ["what_works", "whats_needed", "what_dies"])
        sections.append(f"  #{tns.get('rank', '?'):2}  {n['narrative_id']:>8}  "
                        f"TNS {tns.get('composite', 0):5.1f} [{tns.get('category', ''):12}]  "
                        f"{n['name'][:45]}  ({total_models} models)")
        # Show year-by-year summary
        yby = n.get("year_by_year", {})
        if yby:
            phases = [f"{yr}: {d.get('phase', '?')}" for yr, d in sorted(yby.items())]
            sections.append(f"    Timeline: {' → '.join(phases)}")
    sections.append("")

    # Instructions
    sections.append("# v4 INSTRUCTIONS")
    sections.append("Based on the collision updates and signal evidence, produce narrative updates:")
    sections.append("")
    sections.append("1. For each narrative with new evidence (see Narrative Evidence Matches):")
    sections.append("   - Update year-by-year timeline if signals shift timing")
    sections.append("   - Update geographic variation if regional signals detected")
    sections.append("   - Reclassify models between what_works/whats_needed/what_dies if warranted")
    sections.append("   - Update confidence and falsification criteria status")
    sections.append("")
    sections.append("2. For new collision hypotheses with 3+ signals:")
    sections.append("   - Assess whether they merit a new narrative or belong in an existing one")
    sections.append("   - If new: construct full Transformation Narrative with year-by-year")
    sections.append("")
    sections.append("3. For cascade transmissions:")
    sections.append("   - Update cascade_dependencies in affected narratives")
    sections.append("   - Note any new narrative-to-narrative links")
    sections.append("")
    sections.append("4. Identify model gaps:")
    sections.append("   - Which narratives lack what_works models?")
    sections.append("   - Which narratives lack whats_needed infrastructure models?")
    sections.append("   - Construct new model cards ONLY for critical gaps")
    sections.append("")
    sections.append("Return a JSON object:")
    sections.append("```json")
    sections.append("""{
  "narrative_updates": [
    {
      "narrative_id": "TN-NNN",
      "update_type": "evidence_strengthened | timeline_shifted | geographic_update | model_reclassification",
      "changes": "description of what changed",
      "year_by_year_updates": {"2027": {"phase": "...", "description": "...", "indicators": [...]}},
      "geographic_updates": {"region": {"velocity": "...", "timeline_shift": N}},
      "model_changes": {"added_what_works": [], "added_whats_needed": [], "added_what_dies": []},
      "confidence_update": {"direction": "H/M/L", "timing": "H/M/L", "magnitude": "H/M/L"},
      "falsification_status": "description of any falsification criteria triggered"
    }
  ],
  "new_narratives": [
    {
      "suggested_id": "TN-NEW-NNN",
      "name": "...",
      "collision_ids": ["FC-NNN"],
      "summary": "...",
      "year_by_year": {...},
      "outputs": {"what_works": [], "whats_needed": [], "what_dies": []}
    }
  ],
  "cascade_updates": [
    {"from_narrative": "TN-NNN", "to_narrative": "TN-NNN", "mechanism": "...", "strength": "..."}
  ],
  "new_model_cards": [
    {"model_name": "...", "narrative_id": "TN-NNN", "narrative_role": "what_works|whats_needed|what_dies", "one_line": "..."}
  ],
  "model_gaps_identified": ["narrative TN-NNN lacks what_works models for ..."]
}""")
    sections.append("```")
    sections.append("Return ONLY the JSON object. No preamble.")

    return "\n".join(sections)


def format_for_master_v4(graded_signals, collision_updates, narrative_updates,
                          context_summaries, v4_state):
    """Build Master user message for v4 economy map synthesis."""
    sections = []

    sections.append("# v4 CYCLE RESULTS\n")

    # Signal summary
    sections.append("## Signal Summary")
    stats = collision_updates.get("stats", {})
    sections.append(f"  Total signals: {stats.get('total_signals', len(graded_signals))}")
    sections.append(f"  Collision signals (2+ forces): {stats.get('collision_signals', 0)}")
    sections.append(f"  Cascade transmissions: {stats.get('cascade_detected', 0)}")
    sections.append(f"  Single-force: {stats.get('single_force', 0)}")
    sections.append("")

    # Top signals
    sections.append("## Top Signals (score >= 7)")
    top = sorted([s for s in graded_signals if s.get("relevance_score", 0) >= 7],
                 key=lambda s: s.get("relevance_score", 0), reverse=True)
    for s in top[:15]:
        sections.append(f"  [{s.get('relevance_score', 0)}] {s.get('headline', '?')[:80]}")
    sections.append("")

    # Collision updates
    sections.append("## Collision Updates")
    for s in collision_updates.get("strengthened", [])[:10]:
        sections.append(f"  STRENGTHENED: {s['collision_id']} — {s['signal_count']} signals, "
                        f"{s['strength']} — {s['collision_name'][:50]}")
    for n in collision_updates.get("new_hypotheses", [])[:5]:
        sections.append(f"  NEW HYPOTHESIS: {n['pair_key']} — {n['signal_count']} signals")
    sections.append("")

    # Narrative updates from Agent B
    if narrative_updates:
        sections.append("## Agent B: Narrative Updates")
        nu = narrative_updates.get("narrative_updates", [])
        sections.append(f"  {len(nu)} narratives updated")
        for u in nu[:10]:
            sections.append(f"    {u.get('narrative_id', '?')}: {u.get('update_type', '?')} — "
                            f"{u.get('changes', '')[:80]}")

        nn = narrative_updates.get("new_narratives", [])
        if nn:
            sections.append(f"  {len(nn)} new narratives proposed")
            for n in nn:
                sections.append(f"    {n.get('suggested_id', '?')}: {n.get('name', '?')}")

        cu = narrative_updates.get("cascade_updates", [])
        if cu:
            sections.append(f"  {len(cu)} cascade links updated")

        mg = narrative_updates.get("model_gaps_identified", [])
        if mg:
            sections.append(f"  Model gaps: {len(mg)}")
            for g in mg[:5]:
                sections.append(f"    - {g[:100]}")
        sections.append("")

    # Current narrative rankings
    narratives = load_json(V4_DIR / "narratives.json") or {}
    narrs = narratives.get("narratives", [])
    sections.append("## Current Narrative Rankings (pre-update)")
    for n in narrs[:10]:
        tns = n.get("tns", {})
        sections.append(f"  #{tns.get('rank', '?'):2}  TNS {tns.get('composite', 0):5.1f}  "
                        f"[{tns.get('category', ''):12}]  {n['name'][:45]}")
    sections.append("")

    # Previous cycle context
    cycles = context_summaries.get("cycles", [])
    if cycles:
        sections.append("## Previous Cycle Context")
        for c in cycles[-3:]:
            summary = c.get("summary") or ""
            sections.append(f"Cycle {c['cycle']}: {summary[:1500]}")
        sections.append("")

    # v4 Master instructions
    sections.append("# v4 MASTER SYNTHESIS INSTRUCTIONS")
    sections.append("Produce the Economy Map Update following your v4 output format:")
    sections.append("1. NARRATIVE RANKINGS: Assess which narratives strengthened/weakened")
    sections.append("2. COLLISION VELOCITY REPORT: Which collisions are accelerating?")
    sections.append("3. CASCADE GRAPH UPDATE: New narrative-to-narrative transmissions?")
    sections.append("4. GEOGRAPHIC OVERLAY: Regional variation in collision manifestation")
    sections.append("5. MODEL EVIDENCE HIGHLIGHTS: Key model additions/reclassifications")
    sections.append("6. EMERGENT ECONOMY: New categories from collision interactions")
    sections.append("7. CONFIDENCE & DIRECTIVE: What to scan next cycle")
    sections.append("")
    sections.append("Return a JSON object:")
    sections.append("```json")
    sections.append("""{
  "economy_map_synthesis": "2-4 paragraph narrative of the economy map state",
  "narrative_ranking_changes": [
    {"narrative_id": "TN-NNN", "direction": "strengthened|weakened|stable", "reason": "..."}
  ],
  "collision_velocity_report": [
    {"collision_id": "FC-NNN", "velocity_change": "accelerating|steady|decelerating", "reason": "..."}
  ],
  "cascade_graph_updates": [
    {"from": "TN-NNN", "to": "TN-NNN", "status": "new|strengthened|weakened", "mechanism": "..."}
  ],
  "geographic_highlights": [
    {"region": "...", "key_development": "..."}
  ],
  "emergent_economy_signals": ["..."],
  "scanning_gaps": ["..."],
  "next_cycle_directive": {
    "priority_collisions": ["FC-NNN — what to validate"],
    "priority_narratives": ["TN-NNN — what needs deepening"],
    "scan_focus": ["what Agent A should prioritize"],
    "deprioritize": ["what to reduce focus on"]
  },
  "cycle_summary": "1-paragraph summary for context accumulation"
}""")
    sections.append("```")
    sections.append("Return ONLY the JSON object. No preamble.")

    return "\n".join(sections)


# ---------------------------------------------------------------------------
# v4 Phases
# ---------------------------------------------------------------------------

def phase_agent_a_v4(raw, context_summaries, kill_index, v4_state,
                      analytics_result=None, model="sonnet", verbose=False):
    """Phase 2: Agent A — collision evidence scanning (v4)."""
    print("\n" + "=" * 60)
    print("PHASE 2: AGENT A — v4 collision evidence scanning")
    print("=" * 60)

    system_prompt = load_agent_prompt("agent_a_trends_scanner.md")
    user_message = format_for_agent_a_v4(
        raw, context_summaries, kill_index, v4_state,
        analytics_result=analytics_result,
    )

    print(f"  Sending {len(user_message):,} chars to Agent A...")
    response = llm_call(system_prompt, user_message, model=model, max_tokens=16000)

    if verbose:
        print(f"\n--- Agent A raw response ({len(response)} chars) ---")
        print(response[:2000])
        print("---")

    try:
        signals = parse_json_response(response)
        if isinstance(signals, dict) and "signals" in signals:
            signals = signals["signals"]
        if not isinstance(signals, list):
            signals = [signals]

        # Count signal types
        types = {}
        for s in signals:
            st = s.get("signal_type", "unknown")
            types[st] = types.get(st, 0) + 1

        print(f"  Agent A produced {len(signals)} signals")
        print(f"  Types: {types}")
        return signals
    except Exception as e:
        print(f"  ERROR parsing Agent A response: {e}")
        return []


def phase_agent_c_v4(signals, v4_state, kill_index, model="sonnet", verbose=False):
    """Phase 3: Agent C — collision clustering + grading (v4)."""
    print("\n" + "=" * 60)
    print("PHASE 3: AGENT C — v4 collision clustering & grading")
    print("=" * 60)

    system_prompt = load_agent_prompt("agent_c_sync.md")
    user_message = format_for_agent_c_v4(signals, v4_state, kill_index)

    print(f"  Sending {len(user_message):,} chars to Agent C...")
    response = llm_call(system_prompt, user_message, model=model, max_tokens=16000)

    if verbose:
        print(f"\n--- Agent C raw response ({len(response)} chars) ---")
        print(response[:2000])
        print("---")

    try:
        result = parse_json_response(response)
        graded = result.get("graded_signals", signals)
        collision_groups = result.get("collision_groups", [])
        fv_updates = result.get("force_velocity_updates", {})
        cascade_tx = result.get("cascade_transmissions", [])
        new_hyp = result.get("new_collision_hypotheses", [])

        print(f"  Graded {len(graded)} signals")
        print(f"  {len(collision_groups)} collision groups identified")
        print(f"  {len(fv_updates)} force velocity updates")
        print(f"  {len(cascade_tx)} cascade transmissions")
        print(f"  {len(new_hyp)} new collision hypotheses")

        return {
            "graded_signals": graded,
            "collision_groups": collision_groups,
            "force_velocity_updates": fv_updates,
            "cascade_transmissions": cascade_tx,
            "new_collision_hypotheses": new_hyp,
            "next_cycle_suggestions": result.get("next_cycle_suggestions", []),
        }
    except Exception as e:
        print(f"  ERROR parsing Agent C response: {e}")
        for s in signals:
            s.setdefault("relevance_score", 5.0)
        return {
            "graded_signals": signals,
            "collision_groups": [],
            "force_velocity_updates": {},
            "cascade_transmissions": [],
            "new_collision_hypotheses": [],
            "next_cycle_suggestions": [],
        }


def phase_collision_detector(graded_signals, verbose=False):
    """Phase 3.5: Algorithmic collision detection (v4 NEW)."""
    print("\n" + "=" * 60)
    print("PHASE 3.5: COLLISION DETECTOR — algorithmic matching")
    print("=" * 60)

    from v4_collision_detector import detect_collisions, apply_collision_updates, print_report

    updates = detect_collisions(graded_signals)

    if verbose:
        print_report(updates)
    else:
        stats = updates["stats"]
        print(f"  Processed {stats['total_signals']} signals")
        print(f"  Collision signals: {stats['collision_signals']}")
        print(f"  Strengthened: {len(updates['strengthened'])} existing collisions")
        print(f"  New hypotheses: {len(updates['new_hypotheses'])}")
        print(f"  Cascade signals: {len(updates['cascade_signals'])}")
        print(f"  Narrative matches: {len(updates['narrative_matches'])}")

    # Apply collision updates (update last_evidence_cycle)
    result = apply_collision_updates(updates)
    print(f"  Applied: {result['updated_count']} collision updates, "
          f"{result['stale_count']} stale warnings")

    return updates


def phase_agent_b_v4(collision_updates, graded_signals, v4_state,
                      model="sonnet", verbose=False):
    """Phase 4: Agent B — narrative construction/update (v4)."""
    print("\n" + "=" * 60)
    print("PHASE 4: AGENT B — v4 narrative construction & update")
    print("=" * 60)

    # Skip if no meaningful collision updates
    total_evidence = (len(collision_updates.get("strengthened", []))
                      + len(collision_updates.get("new_hypotheses", []))
                      + len(collision_updates.get("cascade_signals", [])))
    if total_evidence == 0:
        print("  No collision updates to process. Skipping narrative update.")
        return {}

    system_prompt = load_agent_prompt("agent_b_practitioner.md")
    user_message = format_for_agent_b_v4(collision_updates, graded_signals, v4_state)

    print(f"  Sending {len(user_message):,} chars to Agent B...")
    response = llm_call(system_prompt, user_message, model=model, max_tokens=16000)

    if verbose:
        print(f"\n--- Agent B raw response ({len(response)} chars) ---")
        print(response[:2000])
        print("---")

    try:
        result = parse_json_response(response)
        nu = result.get("narrative_updates", [])
        nn = result.get("new_narratives", [])
        cu = result.get("cascade_updates", [])
        nm = result.get("new_model_cards", [])
        mg = result.get("model_gaps_identified", [])

        print(f"  Narrative updates: {len(nu)}")
        print(f"  New narratives proposed: {len(nn)}")
        print(f"  Cascade links: {len(cu)}")
        print(f"  New model cards: {len(nm)}")
        print(f"  Model gaps: {len(mg)}")

        return result
    except Exception as e:
        print(f"  ERROR parsing Agent B response: {e}")
        return {}


def phase_master_v4(graded_signals, collision_updates, narrative_updates,
                     context_summaries, v4_state, model="sonnet", verbose=False):
    """Phase 5: Master — economy map synthesis (v4)."""
    print("\n" + "=" * 60)
    print("PHASE 5: MASTER — v4 economy map synthesis")
    print("=" * 60)

    system_prompt = load_agent_prompt("master.md")
    user_message = format_for_master_v4(
        graded_signals, collision_updates, narrative_updates,
        context_summaries, v4_state,
    )

    print(f"  Sending {len(user_message):,} chars to Master...")
    response = llm_call(system_prompt, user_message, model=model, max_tokens=12000)

    if verbose:
        print(f"\n--- Master raw response ({len(response)} chars) ---")
        print(response[:2000])
        print("---")

    try:
        synthesis = parse_json_response(response)
        nrc = synthesis.get("narrative_ranking_changes", [])
        cvr = synthesis.get("collision_velocity_report", [])
        cgu = synthesis.get("cascade_graph_updates", [])
        gh = synthesis.get("geographic_highlights", [])
        ees = synthesis.get("emergent_economy_signals", [])

        print(f"  Narrative ranking changes: {len(nrc)}")
        print(f"  Collision velocity updates: {len(cvr)}")
        print(f"  Cascade graph updates: {len(cgu)}")
        print(f"  Geographic highlights: {len(gh)}")
        print(f"  Emergent signals: {len(ees)}")

        return synthesis
    except Exception as e:
        print(f"  ERROR parsing Master response: {e}")
        return {"economy_map_synthesis": response[:3000], "cycle_summary": response[:1000]}


def phase_compile_v4(cycle_id, v4_state, master_synthesis, verbose=False):
    """Phase 6: Run v4 scoring + UI compilation scripts."""
    print("\n" + "=" * 60)
    print("PHASE 6: COMPILE — v4 narrative scoring & UI generation")
    print("=" * 60)

    # Run narrative scoring
    print("  Running v4_narrative_scoring.py...")
    result = subprocess.run(
        [sys.executable, str(SCRIPTS_DIR / "v4_narrative_scoring.py")],
        capture_output=True, text=True, timeout=60,
    )
    if result.returncode == 0:
        # Extract summary line
        lines = result.stdout.strip().split("\n")
        for line in lines:
            if "Composite stats" in line or "Categories" in line:
                print(f"    {line.strip()}")
    else:
        print(f"    ERROR: {result.stderr[:200]}")

    # Run UI compilation
    print("  Running v4_compile_ui.py...")
    result = subprocess.run(
        [sys.executable, str(SCRIPTS_DIR / "v4_compile_ui.py")],
        capture_output=True, text=True, timeout=60,
    )
    if result.returncode == 0:
        lines = result.stdout.strip().split("\n")
        for line in lines:
            if "Written:" in line or "Top 5" in line or "#" in line:
                print(f"    {line.strip()}")
    else:
        print(f"    ERROR: {result.stderr[:200]}")

    # Update v4 state
    v4_state["last_updated"] = datetime.now(timezone.utc).isoformat()
    v4_state["last_cycle_synthesis"] = (
        master_synthesis.get("cycle_summary", "")[:500]
    )
    v4_state["next_cycle_directive"] = master_synthesis.get("next_cycle_directive", {})

    # Update entity counts
    narr_data = load_json(V4_DIR / "narratives.json") or {}
    models_data = load_json(V4_DIR / "models.json") or {}
    coll_data = load_json(V4_DIR / "collisions.json") or {}
    casc_data = load_json(V4_DIR / "cascades.json") or {}
    geo_data = load_json(V4_DIR / "geographies.json") or {}

    v4_state["entity_counts"] = {
        "narratives": len(narr_data.get("narratives", [])),
        "collisions": len(coll_data.get("collisions", [])),
        "models": len(models_data.get("models", [])),
        "models_linked": models_data.get("linked_count", 0),
        "models_unlinked": models_data.get("unlinked_count", 0),
        "cascades": len(casc_data.get("cascades", [])),
        "geographies": len(geo_data.get("geographies", [])),
    }

    save_v4_state(v4_state)

    print(f"\n  Cycle {cycle_id} compilation complete.")
    print(f"  Entity counts: {v4_state['entity_counts']}")


# ---------------------------------------------------------------------------
# Main cycle runner
# ---------------------------------------------------------------------------

def run_v4_cycle(model="sonnet", scan_only=False, analytics_only=False,
                  skip_narratives=False, verbose=False, use_api=False):
    """Run a full v4 research cycle."""
    global _use_api
    _use_api = use_api

    t0 = time.time()

    print("\n" + "#" * 60)
    print("#  v4 ECONOMY MAP ENGINE — NARRATIVE-FIRST CYCLE")
    print(f"#  LLM Mode: {'API' if use_api else 'CLI (subscription)'}")
    print(f"#  Model: {MODELS.get(model, model)}")
    print("#" * 60)

    # Load state
    v4_state = load_v4_state()
    cycle_id = bump_cycle(v4_state)
    print(f"\nCycle {cycle_id} starting...")

    context_summaries = load_context_summaries()
    kill_index = load_kill_index()

    # Phase 1: SCAN (reuse v3 infrastructure)
    raw = {}
    analytics_result = {}
    if _HAS_V3_RUNNER:
        raw = phase_scan(verbose=verbose)
        today = datetime.now(timezone.utc).strftime("%Y-%m-%d")
        save_json(DATA_DIR / "raw" / f"{today}.json", raw)

        if scan_only:
            print("\n  --scan-only: stopping after data pull.")
            save_v4_state(v4_state)
            return

        # Phase 1.5: ANALYTICS
        analytics_result = phase_analytics(raw, verbose=verbose)
        save_json(DATA_DIR / "analytics" / f"{today}.json", analytics_result)

        if analytics_only:
            print("\n  --analytics-only: stopping after analytics.")
            save_v4_state(v4_state)
            return
    else:
        if scan_only or analytics_only:
            print("\n  ERROR: run_cycle.py not available for scan/analytics phases.")
            return
        print("\n  WARNING: Skipping scan/analytics (run_cycle.py not available)")
        print("  Proceeding with LLM phases using existing data...")

    # Phase 2: AGENT A (v4 collision-aware scanning)
    signals = phase_agent_a_v4(
        raw, context_summaries, kill_index, v4_state,
        analytics_result=analytics_result, model=model, verbose=verbose,
    )
    if not signals:
        print("\n  ERROR: Agent A produced no signals. Aborting cycle.")
        save_v4_state(v4_state)
        return

    # Phase 3: AGENT C (v4 collision clustering)
    agent_c_result = phase_agent_c_v4(
        signals, v4_state, kill_index, model=model, verbose=verbose,
    )
    graded_signals = agent_c_result.get("graded_signals", signals)

    # Apply force velocity updates from Agent C
    fv_updates = agent_c_result.get("force_velocity_updates", {})
    if fv_updates:
        for fid, update in fv_updates.items():
            if fid in v4_state.get("force_velocities", {}):
                v4_state["force_velocities"][fid]["velocity"] = update.get(
                    "velocity", v4_state["force_velocities"][fid].get("velocity", "steady")
                )
                v4_state["force_velocities"][fid]["confidence"] = update.get(
                    "confidence", v4_state["force_velocities"][fid].get("confidence", "medium")
                )
                v4_state["force_velocities"][fid]["last_update_cycle"] = cycle_id
        print(f"  Applied {len(fv_updates)} force velocity updates to state")

    # Phase 3.5: COLLISION DETECTOR (algorithmic)
    collision_updates = phase_collision_detector(graded_signals, verbose=verbose)

    # Phase 4: AGENT B (v4 narrative update)
    narrative_updates = {}
    if not skip_narratives:
        narrative_updates = phase_agent_b_v4(
            collision_updates, graded_signals, v4_state,
            model=model, verbose=verbose,
        )
    else:
        print("\n  --skip-narratives: skipping Agent B narrative update.")

    # Phase 5: MASTER (v4 economy map synthesis)
    master_synthesis = phase_master_v4(
        graded_signals, collision_updates, narrative_updates,
        context_summaries, v4_state, model=model, verbose=verbose,
    )

    # Save context summary
    cycle_summary = master_synthesis.get("cycle_summary",
                                          master_synthesis.get("economy_map_synthesis", "No summary"))
    if isinstance(cycle_summary, str):
        save_context_summary(cycle_id, cycle_summary)

    # Phase 6: COMPILE (v4 scoring + UI)
    phase_compile_v4(cycle_id, v4_state, master_synthesis, verbose=verbose)

    # Save signals for this cycle
    today = datetime.now(timezone.utc).strftime("%Y-%m-%d")
    save_json(DATA_DIR / "signals" / f"v4_{today}.json", {
        "cycle": cycle_id,
        "date": today,
        "signal_count": len(graded_signals),
        "collision_updates": {
            "strengthened": len(collision_updates.get("strengthened", [])),
            "new_hypotheses": len(collision_updates.get("new_hypotheses", [])),
            "cascade_signals": len(collision_updates.get("cascade_signals", [])),
        },
        "signals": graded_signals,
    })

    elapsed = time.time() - t0
    print("\n" + "#" * 60)
    print(f"#  v4 CYCLE {cycle_id} COMPLETE — {elapsed:.1f}s")
    print(f"#  Signals: {len(graded_signals)}")
    print(f"#  Collisions strengthened: {len(collision_updates.get('strengthened', []))}")
    print(f"#  New hypotheses: {len(collision_updates.get('new_hypotheses', []))}")
    print(f"#  Narrative updates: {len(narrative_updates.get('narrative_updates', []))}")
    if _use_api:
        print(f"#  LLM tokens: {_total_input_tokens:,} in / {_total_output_tokens:,} out")
    print("#" * 60)


# ---------------------------------------------------------------------------
# CLI
# ---------------------------------------------------------------------------

def main():
    parser = argparse.ArgumentParser(
        description="v4 Economy Map Engine — Narrative-First Cycle Runner"
    )
    parser.add_argument("--model", default="sonnet",
                        choices=["sonnet", "opus", "haiku"],
                        help="Claude model (default: sonnet)")
    parser.add_argument("--scan-only", action="store_true",
                        help="Only pull data, skip LLM phases")
    parser.add_argument("--analytics-only", action="store_true",
                        help="Run scan + analytics, skip LLM phases")
    parser.add_argument("--skip-narratives", action="store_true",
                        help="Skip Agent B narrative update (faster cycles)")
    parser.add_argument("--use-api", action="store_true",
                        help="Use Anthropic API instead of Claude Code CLI")
    parser.add_argument("--verbose", action="store_true",
                        help="Print raw LLM responses")
    args = parser.parse_args()

    try:
        run_v4_cycle(
            model=args.model,
            scan_only=args.scan_only,
            analytics_only=args.analytics_only,
            skip_narratives=args.skip_narratives,
            use_api=args.use_api,
            verbose=args.verbose,
        )
    except RuntimeError as e:
        print(f"\n  SETUP ERROR: {e}")
        sys.exit(1)
    except Exception as e:
        print(f"\n  FATAL ERROR: {e}")
        traceback.print_exc()
        sys.exit(1)


if __name__ == "__main__":
    main()
