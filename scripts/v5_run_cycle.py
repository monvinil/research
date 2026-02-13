#!/usr/bin/env python3
"""v5.0 Research Cycle Runner — Constraint Propagation Engine.

Extends v4.1 pipeline with tension detection, requirement-directed scanning,
bounded score propagation, and self-fulfillment monitoring.

v5 Pipeline:
  Phase 0:    TENSION DETECTION (v5_tension_detector) → tensions.json
  Phase 0.5:  REQUIREMENT GENERATION (v5_requirement_generator) → requirements.json
  Phase 1:    SCAN — pull live data (unchanged)
  Phase 1.5:  ANALYTICS (unchanged)
  Phase 2:    AGENT A — directed by requirements.json, not generic scan
  Phase 3:    AGENT C — collision clustering + signal grading
  Phase 3.5:  COLLISION DETECTOR (unchanged)
  Phase 4:    PROPAGATION PASS (v5_propagator) → bounded score adjustments
  Phase 4.5:  TENSION RE-CHECK — did propagation resolve/create tensions?
  Phase 5:    AGENT B — model cards informed by tension context
  Phase 6:    MASTER — synthesis includes tension resolution report
  Phase 7:    COMPILE — v4_compile_ui + tension data

Usage:
    python scripts/v5_run_cycle.py                   # full v5 cycle
    python scripts/v5_run_cycle.py --demo             # tension/propagation only (no LLM)
    python scripts/v5_run_cycle.py --tensions-only    # just detect tensions
    python scripts/v5_run_cycle.py --propagate-only   # detect + propagate (no LLM)
    python scripts/v5_run_cycle.py --model opus       # use opus for agents
    python scripts/v5_run_cycle.py --dry-run          # propagation in dry-run mode
"""

import argparse
import json
import subprocess
import sys
import time
from datetime import datetime, timezone
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parent.parent
SCRIPTS_DIR = PROJECT_ROOT / "scripts"
V4_DIR = PROJECT_ROOT / "data" / "v4"
V5_DIR = PROJECT_ROOT / "data" / "v5"

sys.path.insert(0, str(SCRIPTS_DIR))

# Import v4 cycle runner functions
from v4_run_cycle import (
    load_v4_state, save_v4_state, bump_cycle, load_context_summaries,
    load_kill_index, save_context_summary, load_json, save_json,
    phase_agent_c_v4, phase_collision_detector, phase_agent_b_v4,
    phase_master_v4, phase_compile_v4, phase_agent_a_v4,
    llm_call, load_agent_prompt, parse_json_response,
    MODELS, DATA_DIR,
)

# Import v5 scripts
from v5_tension_detector import run as run_tension_detector
from v5_requirement_generator import run as run_requirement_generator
from v5_propagator import run as run_propagator

# Check for v3 runner
try:
    from run_cycle import phase_scan, phase_analytics
    _HAS_V3_RUNNER = True
except ImportError:
    _HAS_V3_RUNNER = False


# ---------------------------------------------------------------------------
# v5 Phase 0: Tension Detection
# ---------------------------------------------------------------------------

def phase_0_tension_detection():
    """Run tension detector on current v4 data."""
    print("\n" + "=" * 60)
    print("PHASE 0: TENSION DETECTION")
    print("=" * 60)

    result = run_tension_detector()

    n_tensions = result["summary"]["total_tensions"]
    by_type = result["summary"]["by_type"]
    sf_status = result["summary"]["self_fulfillment_status"]

    print(f"\n  Summary: {n_tensions} tensions detected")
    print(f"  By type: {by_type}")
    print(f"  Self-fulfillment: {sf_status}")

    return result


# ---------------------------------------------------------------------------
# v5 Phase 0.5: Requirement Generation
# ---------------------------------------------------------------------------

def phase_05_requirement_generation():
    """Convert tensions into external data requirements."""
    print("\n" + "=" * 60)
    print("PHASE 0.5: REQUIREMENT GENERATION")
    print("=" * 60)

    result = run_requirement_generator()

    n_reqs = result["summary"]["total_requirements"]
    by_priority = result["summary"]["by_priority"]

    print(f"\n  Summary: {n_reqs} requirements generated")
    print(f"  By priority: {by_priority}")

    return result


# ---------------------------------------------------------------------------
# v5 Phase 2: Agent A — Requirement-Directed Scanning
# ---------------------------------------------------------------------------

def phase_agent_a_v5(raw, context_summaries, kill_index, v4_state,
                      requirements, analytics_result=None, model="sonnet",
                      verbose=False):
    """Phase 2: Agent A — scanning directed by requirements.json."""
    print("\n" + "=" * 60)
    print("PHASE 2: AGENT A — v5 requirement-directed scanning")
    print("=" * 60)

    # Build enhanced user message with requirements
    from v4_run_cycle import format_for_agent_a_v4
    base_message = format_for_agent_a_v4(
        raw, context_summaries, kill_index, v4_state,
        analytics_result=analytics_result,
    )

    # Prepend requirements section
    req_section = ["# v5 SCAN REQUIREMENTS — TENSION-DIRECTED\n"]
    req_section.append("The following questions need SPECIFIC evidence to validate or falsify.")
    req_section.append("Prioritize finding data that addresses these requirements over generic scanning.\n")

    reqs = requirements.get("requirements", [])
    high = [r for r in reqs if r["priority"] == "high"]
    medium = [r for r in reqs if r["priority"] == "medium"]

    if high:
        req_section.append("## HIGH PRIORITY (must address)")
        for r in high:
            req_section.append(f"  [{r['requirement_id']}] {r['question']}")
            for vd in r.get("validation_data", [])[:2]:
                req_section.append(f"    → Look for: {vd}")
            req_section.append(f"    Validate if: {r['threshold_validate']}")
            req_section.append(f"    Falsify if: {r['threshold_falsify']}")
            req_section.append("")

    if medium:
        req_section.append("## MEDIUM PRIORITY (address if evidence found)")
        for r in medium[:5]:
            req_section.append(f"  [{r['requirement_id']}] {r['question']}")
        req_section.append("")

    enhanced_message = "\n".join(req_section) + "\n\n" + base_message

    # Replace the generic scan directive with requirement-directed one
    enhanced_message = enhanced_message.replace(
        "# v4 SCAN DIRECTIVE\nScan for COLLISION EVIDENCE",
        "# v5 SCAN DIRECTIVE\nScan for evidence that VALIDATES or FALSIFIES the requirements above. Also scan for COLLISION EVIDENCE",
    )

    system_prompt = load_agent_prompt("agent_a_trends_scanner.md")

    print(f"  Sending {len(enhanced_message):,} chars to Agent A (requirement-directed)...")
    print(f"  Requirements: {len(high)} high, {len(medium)} medium priority")
    response = llm_call(system_prompt, enhanced_message, model=model, max_tokens=16000)

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

        # Tag signals with requirement matches
        req_matched = 0
        for s in signals:
            req_refs = s.get("requirement_refs", [])
            if req_refs:
                req_matched += 1

        print(f"  Agent A produced {len(signals)} signals")
        print(f"  Requirement-matched signals: {req_matched}/{len(signals)}")
        return signals
    except Exception as e:
        print(f"  ERROR parsing Agent A response: {e}")
        return []


# ---------------------------------------------------------------------------
# v5 Phase 4: Propagation Pass
# ---------------------------------------------------------------------------

def phase_4_propagation(dry_run=False):
    """Phase 4: Run bounded score propagation."""
    print("\n" + "=" * 60)
    print(f"PHASE 4: PROPAGATION {'(DRY RUN)' if dry_run else ''}")
    print("=" * 60)

    result = run_propagator(dry_run=dry_run)

    print(f"\n  Summary:")
    print(f"    Models changed: {result['summary']['models_changed']}")
    print(f"    Narratives changed: {result['summary']['narratives_changed']}")
    print(f"    Converged: {result['summary']['converged']}")

    return result


# ---------------------------------------------------------------------------
# v5 Phase 4.5: Tension Re-Check
# ---------------------------------------------------------------------------

def phase_45_tension_recheck(pre_tensions):
    """Phase 4.5: Re-detect tensions after propagation and compare."""
    print("\n" + "=" * 60)
    print("PHASE 4.5: TENSION RE-CHECK")
    print("=" * 60)

    post_result = run_tension_detector()
    post_tensions = post_result["tensions"]

    pre_count = pre_tensions["summary"]["total_tensions"]
    post_count = post_result["summary"]["total_tensions"]

    # Compare tension counts by type
    pre_by_type = pre_tensions["summary"]["by_type"]
    post_by_type = post_result["summary"]["by_type"]

    print(f"\n  Pre-propagation:  {pre_count} tensions")
    print(f"  Post-propagation: {post_count} tensions")

    all_types = set(list(pre_by_type.keys()) + list(post_by_type.keys()))
    resolved = 0
    new_tensions = 0
    for tt in sorted(all_types):
        pre_n = pre_by_type.get(tt, 0)
        post_n = post_by_type.get(tt, 0)
        delta = post_n - pre_n
        if delta != 0:
            marker = "+" if delta > 0 else ""
            print(f"    {tt}: {pre_n} → {post_n} ({marker}{delta})")
            if delta < 0:
                resolved += abs(delta)
            else:
                new_tensions += delta

    print(f"\n  Resolved: {resolved} tensions")
    print(f"  New: {new_tensions} tensions")
    print(f"  Net change: {post_count - pre_count:+d}")

    # Compare self-fulfillment
    pre_sf = pre_tensions["self_fulfillment_metrics"]
    post_sf = post_result["self_fulfillment_metrics"]
    for key in ["tns_vs_model_t", "tns_vs_model_o", "model_t_vs_model_o"]:
        pre_r = pre_sf["correlations"][key]["r"]
        post_r = post_sf["correlations"][key]["r"]
        if abs(post_r - pre_r) > 0.01:
            print(f"  Self-fulfillment {key}: r={pre_r:.4f} → {post_r:.4f}")

    # Save post-propagation tensions
    save_json(V5_DIR / "tensions_post_propagation.json", post_result)

    return {
        "pre_count": pre_count,
        "post_count": post_count,
        "resolved": resolved,
        "new": new_tensions,
        "post_tensions": post_result,
    }


# ---------------------------------------------------------------------------
# v5 Phase 5: Agent B — Tension-Informed Model Cards
# ---------------------------------------------------------------------------

def phase_agent_b_v5(collision_updates, graded_signals, v4_state, tensions,
                      model="sonnet", verbose=False):
    """Phase 5: Agent B with tension context."""
    print("\n" + "=" * 60)
    print("PHASE 5: AGENT B — v5 tension-informed model cards")
    print("=" * 60)

    # Fall back to standard Agent B but inject tension context
    from v4_run_cycle import format_for_agent_b_v4
    base_message = format_for_agent_b_v4(collision_updates, graded_signals, v4_state)

    # Inject tension context
    tension_section = ["\n# v5 TENSION CONTEXT\n"]
    tension_section.append("The following tensions have been detected in the current model inventory.")
    tension_section.append("When updating model cards, address these tensions where relevant:\n")

    # Add top tensions by type
    by_type = {}
    for t in tensions.get("tensions", []):
        tt = t["tension_type"]
        by_type.setdefault(tt, []).append(t)

    for tt, tt_tensions in by_type.items():
        tension_section.append(f"## {tt.replace('_', ' ').title()} ({len(tt_tensions)} tensions)")
        for t in tt_tensions[:3]:
            tension_section.append(f"  - {t.get('question', t.get('tension_id', '?'))[:120]}")
        tension_section.append("")

    enhanced_message = base_message + "\n".join(tension_section)

    system_prompt = load_agent_prompt("agent_b_practitioner.md")

    # Check if there's anything to process
    total_evidence = (len(collision_updates.get("strengthened", []))
                      + len(collision_updates.get("new_hypotheses", []))
                      + len(collision_updates.get("cascade_signals", [])))
    if total_evidence == 0:
        print("  No collision updates to process. Skipping.")
        return {}

    print(f"  Sending {len(enhanced_message):,} chars to Agent B (tension-informed)...")
    response = llm_call(system_prompt, enhanced_message, model=model, max_tokens=16000)

    if verbose:
        print(f"\n--- Agent B raw response ({len(response)} chars) ---")
        print(response[:2000])
        print("---")

    try:
        result = parse_json_response(response)
        print(f"  Narrative updates: {len(result.get('narrative_updates', []))}")
        print(f"  New model cards: {len(result.get('new_model_cards', []))}")
        return result
    except Exception as e:
        print(f"  ERROR parsing Agent B response: {e}")
        return {}


# ---------------------------------------------------------------------------
# v5 Phase 6: Master — Tension Resolution Report
# ---------------------------------------------------------------------------

def phase_master_v5(graded_signals, collision_updates, narrative_updates,
                     context_summaries, v4_state, tension_recheck,
                     model="sonnet", verbose=False):
    """Phase 6: Master with tension resolution report."""
    print("\n" + "=" * 60)
    print("PHASE 6: MASTER — v5 synthesis with tension resolution")
    print("=" * 60)

    from v4_run_cycle import format_for_master_v4
    base_message = format_for_master_v4(
        graded_signals, collision_updates, narrative_updates,
        context_summaries, v4_state,
    )

    # Inject tension resolution
    tension_section = ["\n# v5 TENSION RESOLUTION REPORT\n"]
    tension_section.append(f"Pre-propagation tensions: {tension_recheck['pre_count']}")
    tension_section.append(f"Post-propagation tensions: {tension_recheck['post_count']}")
    tension_section.append(f"Resolved: {tension_recheck['resolved']}")
    tension_section.append(f"New: {tension_recheck['new']}")
    tension_section.append("")
    tension_section.append("Include tension resolution status in your synthesis.")
    tension_section.append("Report which tensions were resolved, which persist, which are new.")

    enhanced_message = base_message + "\n".join(tension_section)
    system_prompt = load_agent_prompt("master.md")

    print(f"  Sending {len(enhanced_message):,} chars to Master (tension-aware)...")
    response = llm_call(system_prompt, enhanced_message, model=model, max_tokens=12000)

    if verbose:
        print(f"\n--- Master raw response ({len(response)} chars) ---")
        print(response[:2000])
        print("---")

    try:
        synthesis = parse_json_response(response)
        return synthesis
    except Exception as e:
        print(f"  ERROR parsing Master response: {e}")
        return {"economy_map_synthesis": response[:3000], "cycle_summary": response[:1000]}


# ---------------------------------------------------------------------------
# Main cycle runner
# ---------------------------------------------------------------------------

def run_v5_cycle(model="sonnet", demo=False, tensions_only=False,
                  propagate_only=False, dry_run=False, verbose=False,
                  use_api=False):
    """Run a full v5 constraint propagation cycle."""
    import v4_run_cycle
    v4_run_cycle._use_api = use_api

    t0 = time.time()

    print("\n" + "#" * 60)
    print("#  v5.0 CONSTRAINT PROPAGATION ENGINE")
    print(f"#  Mode: {'DEMO' if demo else 'TENSIONS-ONLY' if tensions_only else 'PROPAGATE-ONLY' if propagate_only else 'FULL CYCLE'}")
    if not demo and not tensions_only and not propagate_only:
        print(f"#  LLM Model: {MODELS.get(model, model)}")
    print("#" * 60)

    # Phase 0: Tension Detection
    tensions = phase_0_tension_detection()

    if tensions_only:
        elapsed = time.time() - t0
        print(f"\n  --tensions-only complete. {elapsed:.1f}s")
        return

    # Phase 0.5: Requirement Generation
    requirements = phase_05_requirement_generation()

    if demo or propagate_only:
        # Phase 4: Propagation
        prop_result = phase_4_propagation(dry_run=dry_run)

        # Phase 4.5: Tension Re-Check
        recheck = phase_45_tension_recheck(tensions)

        # Phase 7: Compile UI
        print("\n" + "=" * 60)
        print("PHASE 7: COMPILE UI")
        print("=" * 60)
        result = subprocess.run(
            [sys.executable, str(SCRIPTS_DIR / "v4_compile_ui.py")],
            capture_output=True, text=True, timeout=60,
        )
        if result.returncode == 0:
            for line in result.stdout.strip().split("\n"):
                if "Written:" in line or "Models:" in line:
                    print(f"  {line.strip()}")
        else:
            print(f"  ERROR: {result.stderr[:200]}")

        elapsed = time.time() - t0
        print(f"\n{'#' * 60}")
        print(f"#  v5 {'DEMO' if demo else 'PROPAGATE-ONLY'} COMPLETE — {elapsed:.1f}s")
        print(f"#  Tensions: {tensions['summary']['total_tensions']} → {recheck['post_count']}")
        print(f"#  Requirements: {requirements['summary']['total_requirements']}")
        print(f"#  Models changed: {prop_result['summary']['models_changed']}")
        print(f"#  Converged: {prop_result['summary']['converged']}")
        print(f"{'#' * 60}")
        return

    # --- Full cycle with LLM agents ---

    # Load state
    v4_state = load_v4_state()
    cycle_id = bump_cycle(v4_state)
    v4_state["engine_version"] = "5.0"
    print(f"\nCycle {cycle_id} starting (v5 constraint propagation)...")

    context_summaries = load_context_summaries()
    kill_index = load_kill_index()

    # Phase 1: SCAN
    raw = {}
    analytics_result = {}
    if _HAS_V3_RUNNER:
        raw = phase_scan(verbose=verbose)
        today = datetime.now(timezone.utc).strftime("%Y-%m-%d")
        save_json(DATA_DIR / "raw" / f"{today}.json", raw)

        # Phase 1.5: ANALYTICS
        analytics_result = phase_analytics(raw, verbose=verbose)
        save_json(DATA_DIR / "analytics" / f"{today}.json", analytics_result)
    else:
        print("\n  WARNING: Skipping scan/analytics (run_cycle.py not available)")

    # Phase 2: AGENT A (requirement-directed)
    signals = phase_agent_a_v5(
        raw, context_summaries, kill_index, v4_state,
        requirements, analytics_result=analytics_result,
        model=model, verbose=verbose,
    )
    if not signals:
        print("\n  ERROR: Agent A produced no signals. Aborting cycle.")
        save_v4_state(v4_state)
        return

    # Phase 3: AGENT C
    agent_c_result = phase_agent_c_v4(
        signals, v4_state, kill_index, model=model, verbose=verbose,
    )
    graded_signals = agent_c_result.get("graded_signals", signals)

    # Apply force velocity updates
    fv_updates = agent_c_result.get("force_velocity_updates", {})
    if fv_updates:
        for fid, update in fv_updates.items():
            if fid in v4_state.get("force_velocities", {}):
                v4_state["force_velocities"][fid]["velocity"] = update.get("velocity", "steady")
                v4_state["force_velocities"][fid]["confidence"] = update.get("confidence", "medium")
                v4_state["force_velocities"][fid]["last_update_cycle"] = cycle_id
        print(f"  Applied {len(fv_updates)} force velocity updates")

    # Phase 3.5: COLLISION DETECTOR
    collision_updates = phase_collision_detector(graded_signals, verbose=verbose)

    # Phase 4: PROPAGATION
    prop_result = phase_4_propagation(dry_run=dry_run)

    # Phase 4.5: TENSION RE-CHECK
    recheck = phase_45_tension_recheck(tensions)

    # Phase 5: AGENT B (tension-informed)
    narrative_updates = phase_agent_b_v5(
        collision_updates, graded_signals, v4_state, tensions,
        model=model, verbose=verbose,
    )

    # Phase 6: MASTER (tension-aware synthesis)
    master_synthesis = phase_master_v5(
        graded_signals, collision_updates, narrative_updates,
        context_summaries, v4_state, recheck,
        model=model, verbose=verbose,
    )

    # Save cycle summary
    cycle_summary = master_synthesis.get("cycle_summary",
                                          master_synthesis.get("economy_map_synthesis", "No summary"))
    if isinstance(cycle_summary, str):
        save_context_summary(cycle_id, cycle_summary)

    # Phase 7: COMPILE
    phase_compile_v4(cycle_id, v4_state, master_synthesis, verbose=verbose)

    # Update v5 state
    v5_state = {
        "state_version": 1,
        "engine_version": "5.0",
        "current_cycle": cycle_id,
        "last_updated": datetime.now(timezone.utc).isoformat(),
        "tensions_pre": tensions["summary"]["total_tensions"],
        "tensions_post": recheck["post_count"],
        "tensions_resolved": recheck["resolved"],
        "tensions_new": recheck["new"],
        "requirements_count": requirements["summary"]["total_requirements"],
        "propagation_models_changed": prop_result["summary"]["models_changed"],
        "propagation_converged": prop_result["summary"]["converged"],
    }
    save_json(V5_DIR / "state.json", v5_state)

    # Save signals
    today = datetime.now(timezone.utc).strftime("%Y-%m-%d")
    save_json(DATA_DIR / "signals" / f"v5_{today}.json", {
        "cycle": cycle_id,
        "date": today,
        "signal_count": len(graded_signals),
        "requirement_directed": True,
        "tensions_resolved": recheck["resolved"],
        "signals": graded_signals,
    })

    elapsed = time.time() - t0
    print(f"\n{'#' * 60}")
    print(f"#  v5 CYCLE {cycle_id} COMPLETE — {elapsed:.1f}s")
    print(f"#  Signals: {len(graded_signals)}")
    print(f"#  Tensions: {tensions['summary']['total_tensions']} → {recheck['post_count']} "
          f"(resolved: {recheck['resolved']}, new: {recheck['new']})")
    print(f"#  Requirements: {requirements['summary']['total_requirements']}")
    print(f"#  Propagation: {prop_result['summary']['models_changed']} models changed, "
          f"converged={prop_result['summary']['converged']}")
    print(f"{'#' * 60}")


# ---------------------------------------------------------------------------
# CLI
# ---------------------------------------------------------------------------

def main():
    parser = argparse.ArgumentParser(
        description="v5.0 Constraint Propagation Engine — Cycle Runner"
    )
    parser.add_argument("--model", default="sonnet",
                        choices=["sonnet", "opus", "haiku"],
                        help="Claude model (default: sonnet)")
    parser.add_argument("--demo", action="store_true",
                        help="Run tension/propagation only (no LLM, no scan)")
    parser.add_argument("--tensions-only", action="store_true",
                        help="Only detect tensions, no propagation or agents")
    parser.add_argument("--propagate-only", action="store_true",
                        help="Detect tensions + propagate (no LLM agents)")
    parser.add_argument("--dry-run", action="store_true",
                        help="Propagation in dry-run mode (no data changes)")
    parser.add_argument("--use-api", action="store_true",
                        help="Use Anthropic API instead of Claude Code CLI")
    parser.add_argument("--verbose", action="store_true",
                        help="Print raw LLM responses")
    args = parser.parse_args()

    try:
        run_v5_cycle(
            model=args.model,
            demo=args.demo,
            tensions_only=args.tensions_only,
            propagate_only=args.propagate_only,
            dry_run=args.dry_run,
            use_api=args.use_api,
            verbose=args.verbose,
        )
    except Exception as e:
        print(f"\n  ERROR: {e}")
        import traceback
        traceback.print_exc()
        sys.exit(1)


if __name__ == "__main__":
    main()
