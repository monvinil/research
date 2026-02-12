# Model Granularity Framework — The Third Dimension

**Version:** 1.0
**Introduced:** v3-10 cycle
**Status:** Standardized methodology

---

## The Problem

The engine's two independent rankings — Transformation (5-axis) and Opportunity (CLA 4-axis) — are nearly orthogonal (r=0.088), meaning they capture genuinely independent information. But both rankings operate at whatever granularity level the model happened to be defined at. This creates a systematic bias:

**Coarse models in concentrated sectors get FORTIFIED CLA scores that mask accessible sub-positions.**

Example: Retail Media Networks (T#1, OPP=31.0, FORTIFIED) is defined at sector level, where Amazon's 77% share dominates the CLA. But the value chain has 5+ layers — some of which (mid-market enabling tech, measurement/attribution, retail data clean rooms) have no dominant player and are independently viable businesses.

The model definition granularity is the **third dimension** of the engine:

| Dimension | Question | System | Status |
|-----------|----------|--------|--------|
| 1. Transformation Certainty | "Will this happen?" | 5-axis (SN/FA/EC/TG/CE) | Tuned |
| 2. Opportunity Accessibility | "Can an entrant play this?" | CLA 4-axis (MO/MA/VD/DV) | Tuned |
| 3. Model Granularity | "At what level are we asking?" | This framework | **Standardizing** |

Without a standardized granularity approach, the engine systematically:
- Overstates barriers in fortress markets (averaging locked and open layers)
- Understates barriers in fragmented markets (averaging competitive and greenfield layers)
- Misallocates analytical resources toward sector-level views when layer-level views would be more actionable

---

## Core Principle: The Independently Viable Business Test

A model is at the **right granularity** when it represents a unit that could exist as an independent business — with its own revenue model, customer base, and competitive dynamics — but cannot be meaningfully subdivided further without losing coherent transformation signal.

**Too coarse:** "Retail Media Networks" — averages Amazon's data fortress with the open measurement/attribution layer
**Right level:** "Retail Media Measurement & Attribution Platform" — independent business, distinct competitive landscape
**Too fine:** "Retail Media Click Attribution Algorithm" — not a business, just a feature

---

## When to Decompose: Trigger Criteria

A model is a **decomposition candidate** when it meets ALL THREE conditions:

### Condition 1: Opportunity Suppression Signal
The model is classified **FORTIFIED** (OPP 30-44.9) or **LOCKED** (OPP < 30).

*Rationale:* CONTESTED models (45-59.9) already have viable entry paths priced in. ACCESSIBLE and WIDE_OPEN models don't need decomposition — the opportunity is already visible at the current granularity.

### Condition 2: Value Chain Signal
The model's CLA **VD (Value Chain Depth) score >= 4**.

*Rationale:* VD measures "how many independent defensible positions exist in the value chain." A VD of 4+ means the CLA already tells us multiple layers exist. If VD < 4, the market is both fortified AND shallow — decomposition won't reveal hidden accessible positions because there aren't enough independent layers.

### Condition 3: Analytical Significance
At least ONE of:
- **Transformation Rank <= 50** (high-certainty transformation being obscured)
- **Sector employment >= 1M workers** (scale makes granularity matter for economy mapping)
- **Actionable score mismatch**: T-composite >= 75 but OPP-composite <= 45 (strong transformation signal being wasted by coarse opportunity scoring)

*Rationale:* Not every FORTIFIED model warrants the analytical cost of decomposition. Focus on models where the granularity error has the highest impact on the engine's output quality.

### Trigger Formula

```
DECOMPOSE = (OPP_category IN [FORTIFIED, LOCKED])
            AND (VD >= 4)
            AND (T_rank <= 50 OR sector_employment >= 1M OR (T_composite >= 75 AND OPP_composite <= 45))
```

### Current Inventory Scan (v3-9, 435 models)

Applying the trigger to the 26 FORTIFIED models:

| T# | Model | T-Comp | OPP | VD | Trigger? | Reason |
|----|-------|--------|-----|----|----------|--------|
| 1 | Retail Media Network Platform | 86.5 | 31.0 | 5 | **YES** | T#1, VD=5, mismatch 86.5 vs 31.0 |
| 2 | Warehouse Fulfillment Robotics | 84.0 | 41.0 | 6 | **YES** | T#2, VD=6, mismatch 84.0 vs 41.0 |
| 9 | Autonomous Drone Swarm Command | 82.0 | 39.0 | 5 | **YES** | T#9, VD=5, mismatch 82.0 vs 39.0 |
| 11 | Defense Intelligence Fusion | 81.25 | 32.0 | 4 | **YES** | T#11, VD=4, mismatch 81.25 vs 32.0 |
| 26 | Nuclear Plant AI Ops | 79.0 | 44.5 | 5 | **YES** | T#26, VD=5, mismatch 79.0 vs 44.5 |
| 29 | Classified AI Deployment (IL5/6) | 78.5 | 36.5 | 5 | **YES** | T#29, VD=5, mismatch 78.5 vs 36.5 |
| 37 | Defense Predictive Maintenance | 78.0 | 44.5 | 5 | **YES** | T#37, VD=5, mismatch 78.0 vs 44.5 |
| 42 | Defense Logistics AI | 77.5 | 39.0 | 5 | **YES** | T#42, VD=5, mismatch 77.5 vs 39.0 |
| 44 | Satellite ISR AI Analytics | 77.0 | 44.5 | 5 | **YES** | T#44, VD=5, mismatch 77.0 vs 44.5 |
| 63 | Solar+Storage for DC Campuses | 75.0 | 44.5 | — | NO | Heuristic VD, likely < 4 (project development) |
| 72+ | Lower T-rank FORTIFIED models | <75 | various | — | **Check VD** | Need case-by-case VD check |

**Expected decomposition targets: 9-15 models** (pending VD verification for heuristic-scored models).

---

## How to Decompose: Value Chain Layer Analysis

### Step 1: Map the Full Value Chain Stack

For each decomposition candidate, identify all distinct layers in the value chain. A **layer** is a position in the stack where a business could operate independently.

**Template:**

```
PARENT MODEL: [name] (T#X, OPP=Y, FORTIFIED)

VALUE CHAIN STACK:
  Layer 1: [name] — [what it does] — [who controls it]
  Layer 2: [name] — [what it does] — [who controls it]
  ...
  Layer N: [name] — [what it does] — [who controls it]
```

**Example — Retail Media Networks:**

```
PARENT: Retail Media Network Platform (T#1, OPP=31.0, FORTIFIED)

VALUE CHAIN STACK:
  L1: First-Party Data Ownership    — retailer purchase data  — LOCKED to retailers (Amazon 77%)
  L2: Ad Serving & Targeting        — real-time ad placement  — Amazon DSP, Criteo, PromoteIQ
  L3: Measurement & Attribution     — cross-channel ROAS      — fragmented, no dominant player
  L4: Enabling Tech (mid-market)    — tools for non-Amazon    — Kevel, CitrusAd, Topsort, Moloco
  L5: Retail Data Clean Rooms       — privacy-safe matching   — nascent, Habu/LiveRamp early
  L6: Agency/Managed Service        — brand RMN strategy      — fragmented, consultancy model
```

### Step 2: Independently Viable Business Test (per layer)

For each layer, assess:

| Test | Question | Threshold |
|------|----------|-----------|
| Revenue independence | Can this layer generate revenue without owning other layers? | YES/NO (hard gate) |
| Customer independence | Does this layer have its own buyer (not the same buyer as parent)? | YES/NO (soft signal) |
| Competitive independence | Does this layer have different competitors than the parent model? | YES/NO (hard gate) |
| Scale sufficiency | Is the addressable market for this layer alone >= $100M? | YES/NO (soft signal) |

A layer becomes a **sub-model** only if it passes BOTH hard gates (revenue independence + competitive independence).

### Step 3: Score Sub-Models

Each sub-model gets:

#### Transformation Score (Partially Inherited)
- **FA** (Force Alignment): **Inherit from parent.** The same macro forces drive sub-models — the forces don't change at the layer level.
- **EC** (External Context): **Inherit from parent.** Geographic dynamics apply to the full value chain.
- **SN** (Structural Necessity): **Re-score independently.** A measurement layer may be less structurally necessary than the core data layer.
- **TG** (Timing Grade): **Re-score independently.** Entry windows differ by layer — an enabling tech layer may be open now while the data layer is permanently locked.
- **CE** (Capital Efficiency): **Re-score independently.** A SaaS enabling tool has very different capital needs than building a data asset.

**Sub-model T-composite** = (SN_new*25 + FA_parent*25 + EC_parent*20 + TG_new*15 + CE_new*15) / 10

#### Opportunity Score (Fully Independent)
- **All four CLA axes (MO, MA, VD, DV)** scored fresh for the sub-model.
- The sub-model's VD is now about the depth within its own layer (sub-layer depth), not the parent's full value chain.
- The sub-model's MO reflects the competitive landscape at THIS layer, not the overall sector.

#### Categorization
Sub-models are independently categorized: a sub-model of a FORTIFIED parent can be WIDE_OPEN, ACCESSIBLE, CONTESTED, or even FORTIFIED itself (if that layer is also concentrated).

### Step 4: Link to Parent

Each sub-model carries:

```json
{
  "id": "MC-V38-44-003-L3",
  "parent_id": "MC-V38-44-003",
  "parent_name": "Retail Media Network Platform",
  "layer": 3,
  "layer_name": "Measurement & Attribution",
  "granularity_type": "value_chain_layer",
  "inherited_scores": {
    "FA": 9.0,
    "EC": 8.0
  },
  "independent_scores": {
    "SN": 7.0,
    "TG": 8.0,
    "CE": 7.5
  }
}
```

**ID Convention:** Parent ID + `-L[N]` where N is the layer number.

---

## What NOT to Decompose

### Anti-Patterns

1. **Decomposing ACCESSIBLE/WIDE_OPEN models** — These are already visible. Decomposition would create model bloat without analytical value.

2. **Decomposing below the business boundary** — Features, algorithms, and product components are not models. If the "sub-model" can't exist as a standalone company, it's too fine.

3. **Decomposing for completeness** — Not every layer needs a sub-model. If a layer fails the Independently Viable Business Test, skip it. The parent model already acknowledges it exists through the VD score.

4. **Decomposing PARKED models** — Low transformation certainty + FORTIFIED = neither happening nor accessible. No analytical value in decomposition.

5. **Infinite regression** — Sub-models are NOT decomposed further. One level of decomposition is the standard. If a sub-model is itself FORTIFIED with high VD, flag it for review in the next cycle rather than cascading.

---

## How Decomposition Affects Rankings

### Parent Model
- **Preserved in both rankings.** The parent model keeps its Transformation Rank and Opportunity Rank. It represents the sector-level view that the economy map needs.
- **Annotated:** `"decomposed": true, "sub_model_count": N, "sub_model_opp_range": [min, max]`
- The parent's CLA rationale gets appended: "Sector-level assessment. Sub-models [IDs] capture layer-specific opportunity. See sub-models for entry-point analysis."

### Sub-Models
- **Added to the inventory** with their own ranks on both dimensions.
- **Tagged with source_batch**: `"decomposition_v3-10"` (or appropriate cycle)
- **Ranked independently** — a sub-model can outrank its parent on opportunity.

### Inventory Growth
Decomposing 10 parent models at an average of 4 sub-models each = ~40 new models. Expected inventory after v3-10: 435 + ~40 = ~475 models.

---

## Reverse Direction: Coarse Underestimation Check

The same granularity bias works in reverse: **fragmented markets where the model is defined at the layer level may mask that the full stack is actually FORTIFIED.**

Example: An "AI Bookkeeping SaaS" model might score ACCESSIBLE, but the full competitive landscape for "AI-Native Financial Back Office" (including payments, tax, payroll, compliance) could reveal platform dynamics that concentrate toward a few winners.

### When to Check for Aggregation
- Model is ACCESSIBLE or WIDE_OPEN
- Architecture is `vertical_saas` or `platform` or `marketplace`
- Multiple models in the same NAICS sector exist with similar CLA profiles

When detected, **don't merge** (that would lose resolution). Instead, create a **synthesis note** on the parent sector transformation that flags the aggregation risk: "5 ACCESSIBLE models in NAICS 5412 may consolidate into a CONTESTED platform play."

---

## Integration with Engine Pipeline

### Where Granularity Analysis Runs

```
Signal Scan (Agent A) → Deep Dives (Agent B) → Granularity Analysis → CLA Scoring → Rankings → Economy Map
                                                        ↑
                                                  NEW STEP (v3-10+)
```

Granularity analysis runs AFTER deep dives (which provide value chain intelligence) and BEFORE CLA scoring (which needs to score sub-models).

### Script Integration

The granularity analysis produces a file:
```
data/verified/v3-XX_decomposition_YYYY-MM-DD.json
```

Structure:
```json
{
  "cycle": "v3-10",
  "decomposition_targets": [
    {
      "parent_id": "MC-V38-44-003",
      "parent_name": "Retail Media Network Platform",
      "trigger": {
        "opp_category": "FORTIFIED",
        "opp_composite": 31.0,
        "vd_score": 5,
        "t_rank": 1,
        "significance": "T_rank <= 50 AND T_composite >= 75 AND OPP_composite <= 45"
      },
      "value_chain_stack": [...],
      "sub_models": [
        {
          "id": "MC-V38-44-003-L3",
          "layer": 3,
          "layer_name": "Measurement & Attribution",
          "passes_ivb_test": true,
          "scores": {...},
          "cla": {...}
        }
      ]
    }
  ],
  "summary": {
    "targets_analyzed": 12,
    "sub_models_created": 42,
    "sub_model_opp_distribution": {...}
  }
}
```

The merge script (`merge_v39.py` successor) then integrates sub-models into the normalized inventory alongside regular model cards.

### CLA Scoring Updates

`cla_scoring.py` needs to:
1. Recognize sub-models by the `-L[N]` suffix in their ID
2. Score sub-models with fully independent CLA (no heuristic fallback — sub-models always get manual/analytical CLA)
3. Skip sector adjustments for sub-models (they already have layer-specific scoring)
4. Include sub-models in ranking but annotate them as decomposition products

---

## Success Criteria for Granularity Standardization

1. **Trigger criteria produce 9-15 decomposition candidates** from the current 26 FORTIFIED models (not too aggressive, not too conservative)
2. **Independently Viable Business Test eliminates spurious layers** — not every value chain position becomes a model
3. **At least one parent model's sub-models span >= 3 CLA categories** (demonstrating that decomposition reveals genuine heterogeneity, not just noise)
4. **No infinite regression** — sub-models are leaf nodes, never decomposed further
5. **Parent models preserved** — the economy map still works at sector level
6. **Framework is mechanistic enough** to be applied by Agent B without ad hoc judgment calls per model

---

## Appendix: Defense Sector Special Case

7 of the 26 FORTIFIED models are Defense (NAICS 33/34). Defense FORTIFICATION is driven by procurement barriers (clearances, ITAR, classification levels) that apply uniformly across value chain layers. Decomposition of defense models should test whether ANY layer avoids procurement barriers:

- **Software layer** (unclassified tooling) — may escape classification requirements
- **Allied nation markets** — AUKUS/NATO create parallel markets with lower barriers
- **Commercial dual-use** — some defense tech has civilian applications with different CLA

If all layers are equally FORTIFIED (procurement barriers are universal), the decomposition is documented but no sub-models are created. This is a valid outcome — it confirms that the parent CLA is accurate at every granularity level.
