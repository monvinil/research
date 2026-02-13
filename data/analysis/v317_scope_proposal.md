# v3-17 Scope Proposal: Three Clusters

Consolidated from: Experiment 2 (reverse loop), Experiment 1 (value capture inversions), and independent engine audit.

---

## Cluster A: Engine Calibration (from Experiment 2)

Findings from applying the 5 T-axes to 35 countries and comparing to ground truth (HDI, Happiness, Legatum). These are empirically-grounded scoring adjustments.

| # | Item | Source Finding | What Changes | Impact |
|---|------|---------------|-------------|--------|
| A1 | **Test axis weight sensitivity** | E2-F1, E2-F9 | Run 608 models with FA=30%/SN=20% vs current FA=25%/SN=25%. Compare ranking shifts, identify models that move >10 ranks | Validates whether FA's demonstrated predictive superiority should increase its weight |
| A2 | **Add "market quality" modifier to VCR MKT** | E2-F1, E2-F5 | Add buyer sophistication/wealth signal to MKT. QCEW avg_pay/sector already available. High-wage sectors (Baumol >1.3) = premium buyers | Addresses "no already good axis" — wealthy stable markets score better |
| A3 | **Explore absorption capacity concept** | E2-F2, E2-F7 | Research which 608 models have high SN + low institutional capacity to adopt. Flag as "pressure trap" vs genuine opportunity | Addresses "crisis ≠ opportunity" — pressure without capacity is a trap |
| A4 | **Split EC sub-components** | E2-F8 | EC currently conflates institutional quality (Norway=good) with external pressure (China sanctions=transformative). Document whether splitting affects model scores | Addresses EC doing double duty |
| A5 | **Document welfare gap** | E2-F5 | Add explicit stated limitation to engine docs: "predicts transformation, not human outcomes" | Low effort, high clarity |

**Estimated effort**: A1 is a script run (low). A2 is a VCR modifier (medium). A3 is research/flagging (medium). A4 is analysis-only (low). A5 is documentation (trivial).

---

## Cluster B: Value Capture Expansion (from Experiment 1)

Findings from analyzing 10 non-conventional value capture mechanisms. These are architecture and scoring expansions.

| # | Item | Source Inversion | What Changes | Impact |
|---|------|-----------------|-------------|--------|
| B1 | **Add `open_core_ecosystem` architecture** | E1-Inv1 | New architecture type with distinct MOA (ecosystem lock-in=8), CAP (free adoption=9), ECO (enterprise layer margins=7). Score differently from platform_infrastructure | 0/15 architectures capture the Red Hat/HashiCorp/HuggingFace model. Affects models that COULD use open-source strategy |
| B2 | **Add `steady_state_eco` field** | E1-Inv2, E1-Inv7 | Parallel ECO score: current margins vs maturity margins. For data_compounding and outcome-based models, current ECO is misleading | 55+ data_compounding models penalized ~12-15 VCR points by snapshot ECO |
| B3 | **Add `outcome_based` architecture** | E1-Inv7 | Revenue from measurable outcomes, not product pricing. CAP=9 (zero acquisition friction), ECO=variable, MOA=7 (alignment moat) | 129 full_service_replacement models don't distinguish pricing strategy |
| B4 | **Add self-funding feasibility flag** | E1-Inv6 | Binary + score: "Can this business reach $2M+ revenue at 80%+ margins without external capital?" Parallel to VCR, not replacing it | Surfaces anti-scale micro-firm path invisible to VC lens |
| B5 | **Reframe FEAR_ECONOMY as trust accumulation** | E1-Inv8 | Review 29 FEAR_ECONOMY (primary) models: are they selling fear reduction or accumulating trust? Trust moat ≠ relationship moat — upgrade MOA where trust compounds | MOA=3-4 → MOA=7-8 for genuine trust-compounders |
| B6 | **Add `coordination_protocol` architecture** | E1-Inv3 | Thin-margin infrastructure for permissionless activity. Distinct from platform: no proprietary lock-in, thin capture, massive volume. MOA=6, ECO=4, CAP=7 | Distinguishes protocol from platform — different capture mechanics |

**Estimated effort**: B1, B3, B6 are architecture additions (medium each — modify vcr_scoring.py, re-run). B2 is a data field (medium — requires per-model judgment). B4 is a flag (low). B5 is a re-scoring audit (medium).

---

## Cluster C: Data Quality & Infrastructure (from Engine Audit)

Practical issues found independent of philosophical experiments.

| # | Item | Finding | What Changes | Impact |
|---|------|---------|-------------|--------|
| C1 | **Backfill Polanyi data for 70 models** | 88.5% → target 95%+ | Re-run Polanyi enrichment connector on 70 missing models (clustered in old MC-31, MC-52, MC-54, MC-56, MC-62 IDs) | SN data-driven scoring (v3-16) falls back to heuristic for these 70 |
| C2 | **Audit 15 EQ=0 legacy models** | 15 models with evidence_quality=0 | Decide: update with current evidence, or mark as deprecated. All are v2-era (2+ years old) | Bottom of evidence quality — dragging confidence distribution |
| C3 | **Define EQ grading criteria** | 262 models (43%) stuck at EQ=2 | Document explicit thresholds: EQ=2 (initial entry), EQ=4 (secondary validation), EQ=6 (deep dive), EQ=8 (multi-source), EQ=10 (published). Create automated upgrade logic | 43% of models at default EQ — unclear if accurate or just ungraded |
| C4 | **Re-rank research priorities** | Top 10 priorities are all LOW confidence | Rebuild research_priorities in dashboard by (confidence_tier, evidence_quality, composite) instead of just composite. Filter to MODERATE+ | Research queue is backwards — lowest quality models first |
| C5 | **Update stale script references** | CLA script references v3-8, VCR references v3-12 | Parameterize file paths across merge scripts. Single config for normalized file path | Prevents stale reference bugs in future cycles |
| C6 | **Merge v3-13 deep dives** | 5 deep dive files (ag, arts, gov, mining, wholesale) staged but not merged | Run merge into normalized file — adds ~60 models. Would bring total to ~668 | Content created but not integrated |

**Estimated effort**: C1 is a connector re-run (medium). C2 is a review (low). C3 is documentation + script (medium). C4 is a script change (low). C5 is a refactor (low). C6 is a merge (medium — needs scoring for new models).

---

## Priority Ranking Across All Clusters

### Must-Do (High confidence these improve the engine)

| Priority | Item | Cluster | Effort | Rationale |
|----------|------|---------|--------|-----------|
| 1 | A1: Weight sensitivity test | Calibration | Low | Only way to validate axis weights empirically. FA=30%/SN=20% hypothesis is testable NOW |
| 2 | C1: Backfill Polanyi (70 models) | Data Quality | Medium | SN data-driven scoring is the v3-16 headline feature — 11.5% of models still on heuristic fallback |
| 3 | B2: Add steady_state_eco | Value Capture | Medium | ECO snapshot penalizes 55+ data_compounding models. Biggest VCR scoring distortion identified |
| 4 | C4: Re-rank research priorities | Data Quality | Low | Research queue is backwards. Quick fix, high visibility |
| 5 | A5: Document welfare gap | Calibration | Trivial | One paragraph in framework docs. Important intellectual honesty |

### Should-Do (Strong evidence, moderate effort)

| Priority | Item | Cluster | Effort | Rationale |
|----------|------|---------|--------|-----------|
| 6 | B1: open_core_ecosystem architecture | Value Capture | Medium | 0/15 architectures cover this; real precedent companies worth $34B+ |
| 7 | A2: Market quality modifier | Calibration | Medium | QCEW data already available. Addresses largest Exp 2 bias (stable markets penalized) |
| 8 | C2+C3: EQ audit + grading criteria | Data Quality | Medium | 277 models (45%) at EQ ≤ 2. Evidence quality is under-specified |
| 9 | B5: FEAR_ECONOMY → trust reframe | Value Capture | Medium | 29 models potentially mispriced on MOA |
| 10 | B4: Self-funding feasibility flag | Value Capture | Low | Binary flag, low effort, surfaces important pattern |

### Could-Do (Interesting but lower confidence)

| Priority | Item | Cluster | Effort | Rationale |
|----------|------|---------|--------|-----------|
| 11 | B3: outcome_based architecture | Value Capture | Medium | Real pattern but hard to identify which models use it |
| 12 | A3: Absorption capacity | Calibration | Medium | Conceptually important but hard to operationalize |
| 13 | B6: coordination_protocol architecture | Value Capture | Medium | Emerging pattern, early-stage |
| 14 | A4: EC split | Calibration | Low | Analysis only — may not change scores materially |
| 15 | C6: Merge v3-13 deep dives | Data Quality | Medium | Adds ~60 models but requires full scoring pipeline |
| 16 | C5: Script path refactor | Data Quality | Low | Housekeeping |
