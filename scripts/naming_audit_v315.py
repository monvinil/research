#!/usr/bin/env python3
"""
v3-15 AI Naming Audit: Reduce AI-in-name from ~59% to <30%.

Logic:
  1. If "AI" is the PRODUCT identity (copilot, governance, safety, ethics) → KEEP
  2. If "AI" is just a tool-modifier prefix (AI-Native, AI-Powered, AI-Enhanced) → RENAME
  3. If architecture is inherently AI (all of them are) → "AI" adds no info → RENAME

Rename patterns:
  "AI-Native X"     → "Autonomous X"
  "AI-Powered X"    → "Intelligent X"
  "AI-Enhanced X"   → "Smart X"
  "AI-Driven X"     → "Algorithmic X"
  "AI X" (generic)  → varies by context

Audit trail written to data/cache/v315_naming_audit.json
"""

import json
import re
import sys
from pathlib import Path

BASE = Path("/Users/mv/Documents/research/data/verified")
NORMALIZED_FILE = BASE / "v3-12_normalized_2026-02-12.json"
CACHE_DIR = Path("/Users/mv/Documents/research/data/cache")
AUDIT_FILE = CACHE_DIR / "v315_naming_audit.json"


# Patterns where "AI" IS the product (keep as-is)
KEEP_PATTERNS = [
    "AI Copilot",
    "AI Agent",
    "AI Governance",
    "AI Ethics",
    "AI Safety",
    "AI Red Team",
    "Generative AI",
    "AI Infrastructure",
    "AI Training",
    "AI Literacy",
    "AI Trust",
    "AI Audit",
    "AI Risk",
    "AI Bias",
    "AI Explainability",
    "AI Transparency",
    "AI Fairness",
    "Anti-AI",
    "AI-Free",
    "AI Anxiety",
    "AI Displacement",
]


def should_keep_ai(name):
    """Check if 'AI' is the product identity and should be kept."""
    name_lower = name.lower()
    for pattern in KEEP_PATTERNS:
        if pattern.lower() in name_lower:
            return True
    return False


def rename_model(name):
    """Apply rename rules. Returns (new_name, rule_applied) or (name, None) if no rename."""
    if should_keep_ai(name):
        return name, None

    # Check if name even contains AI
    if "AI" not in name and "ai" not in name.split("-")[0]:
        return name, None

    # Pattern 1: "AI-Native X" → "Autonomous X"
    m = re.match(r"^AI-Native\s+(.+)$", name)
    if m:
        return f"Autonomous {m.group(1)}", "AI-Native→Autonomous"

    # Pattern 2: "AI-Powered X" → "Intelligent X"
    m = re.match(r"^AI-Powered\s+(.+)$", name)
    if m:
        return f"Intelligent {m.group(1)}", "AI-Powered→Intelligent"

    # Pattern 3: "AI-Enhanced X" → "Smart X"
    m = re.match(r"^AI-Enhanced\s+(.+)$", name)
    if m:
        return f"Smart {m.group(1)}", "AI-Enhanced→Smart"

    # Pattern 4: "AI-Driven X" → "Algorithmic X"
    m = re.match(r"^AI-Driven\s+(.+)$", name)
    if m:
        return f"Algorithmic {m.group(1)}", "AI-Driven→Algorithmic"

    # Pattern 5: "AI-Optimized X" → "Optimized X"
    m = re.match(r"^AI-Optimized\s+(.+)$", name)
    if m:
        return f"Optimized {m.group(1)}", "AI-Optimized→Optimized"

    # Pattern 6: "AI-Enabled X" → "Automated X"
    m = re.match(r"^AI-Enabled\s+(.+)$", name)
    if m:
        return f"Automated {m.group(1)}", "AI-Enabled→Automated"

    # Pattern 7: "AI-Integrated X" → "Integrated X"
    m = re.match(r"^AI-Integrated\s+(.+)$", name)
    if m:
        return f"Integrated {m.group(1)}", "AI-Integrated→Integrated"

    # Pattern 8: "AI X" (generic prefix) — context-dependent
    m = re.match(r"^AI\s+(.+)$", name)
    if m:
        rest = m.group(1)
        # If rest starts with a verb-like word, drop "AI" entirely
        verb_starts = ["Predictive", "Automated", "Smart", "Digital", "Autonomous",
                       "Real-Time", "Dynamic", "Personalized", "Adaptive"]
        for v in verb_starts:
            if rest.startswith(v):
                return rest, "AI prefix dropped (redundant with adjective)"

        # If rest is a noun phrase describing the product, rename based on architecture meaning
        return f"Automated {rest}", "AI→Automated"

    # Pattern 9: Contains "AI" mid-name (e.g., "Precision AI Farming")
    # More conservative — only rename if "AI" is clearly a filler word
    if " AI " in name:
        new_name = name.replace(" AI ", " ", 1)
        return new_name, "removed mid-name AI"

    return name, None


def main():
    apply_mode = "--apply" in sys.argv

    print("=" * 70)
    print("v3-15 AI NAMING AUDIT")
    print("=" * 70)
    print(f"Mode: {'APPLY (writing changes)' if apply_mode else 'ANALYZE (read-only)'}")
    print()

    with open(NORMALIZED_FILE) as f:
        data = json.load(f)
    models = data["models"]

    # Count AI-in-name before
    ai_before = sum(1 for m in models if "AI" in m["name"] or "ai" in m["name"].split("-")[0])
    print(f"Models with AI in name: {ai_before}/{len(models)} ({ai_before/len(models)*100:.1f}%)")

    # Process renames
    renames = []
    kept = []
    unchanged = []

    for m in models:
        new_name, rule = rename_model(m["name"])
        if rule:
            renames.append({
                "id": m["id"],
                "old_name": m["name"],
                "new_name": new_name,
                "rule": rule,
            })
        elif should_keep_ai(m["name"]):
            kept.append({"id": m["id"], "name": m["name"]})
        else:
            unchanged.append(m["id"])

    # Count AI-in-name after renames
    name_map = {r["id"]: r["new_name"] for r in renames}
    ai_after = 0
    for m in models:
        final_name = name_map.get(m["id"], m["name"])
        if "AI" in final_name or "ai" in final_name.split("-")[0]:
            ai_after += 1

    print(f"Renames: {len(renames)}")
    print(f"Kept (AI is product): {len(kept)}")
    print(f"No AI in name: {len(unchanged)}")
    print(f"AI-in-name after: {ai_after}/{len(models)} ({ai_after/len(models)*100:.1f}%)")

    # Rule distribution
    from collections import Counter
    rule_dist = Counter(r["rule"] for r in renames)
    print(f"\nRename rules applied:")
    for rule, count in rule_dist.most_common():
        print(f"  {rule:<40s} {count:>4d}")

    # Show sample renames
    print(f"\nSample renames (first 20):")
    for r in renames[:20]:
        print(f"  {r['old_name']:<55s} → {r['new_name']}")

    # Show kept models
    print(f"\nKept (AI is product identity, {len(kept)}):")
    for k in kept[:10]:
        print(f"  {k['name']}")
    if len(kept) > 10:
        print(f"  ... and {len(kept) - 10} more")

    if apply_mode:
        print(f"\n{'='*70}")
        print("APPLYING RENAMES")
        print(f"{'='*70}")

        for m in models:
            if m["id"] in name_map:
                m["name"] = name_map[m["id"]]

        # Write normalized file
        with open(NORMALIZED_FILE, "w") as f:
            json.dump(data, f, indent=2, ensure_ascii=False)
        print(f"Written: {NORMALIZED_FILE}")

        # Write audit trail
        CACHE_DIR.mkdir(parents=True, exist_ok=True)
        audit = {
            "date": "2026-02-12",
            "total_models": len(models),
            "ai_before": ai_before,
            "ai_after": ai_after,
            "renames": renames,
            "kept": kept,
        }
        with open(AUDIT_FILE, "w") as f:
            json.dump(audit, f, indent=2, ensure_ascii=False)
        print(f"Audit trail: {AUDIT_FILE}")

        # Final verification
        final_ai = sum(1 for m in models if "AI" in m["name"] or "ai" in m["name"].split("-")[0])
        print(f"\nFinal AI-in-name: {final_ai}/{len(models)} ({final_ai/len(models)*100:.1f}%)")
    else:
        print(f"\nRun with --apply to write changes.")


if __name__ == "__main__":
    main()
