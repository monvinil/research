# VCR Axis Correlation Analysis (v3-17 Audit)

## Findings

### Within-VCR Correlations

- **CAP↔VEL: r=0.767 (VERY HIGH)** — "Capture Feasibility" and "Revenue Velocity" are measuring nearly the same thing. Both are influenced by market fragmentation, buyer type, and go-to-market difficulty.
- **ECO↔MOA: r=0.721 (HIGH)** — "Unit Economics" and "Moat Trajectory" correlate because SaaS models score high on both (good margins + data flywheel moat) while hardware models score low on both.
- **CAP↔ECO**: Check — likely moderate correlation driven by architecture type (SaaS vs. hardware vs. services).
- **MKT↔CAP**: Check — market size and capture feasibility may correlate if larger markets also tend to be more fragmented.
- Other VCR pairs: lower correlations expected for MKT↔MOA, MKT↔VEL.

### Cross-System Leakage

- **CLA:MO ↔ VCR:CAP: r=0.624** — "Market Openness" and "Capture Feasibility" overlap because both measure how fragmented/accessible the market is. This means the CLA and VCR systems are not fully independent for these axes.

### Within-T Correlations

- **FA↔TG: r=0.543** — "Force Alignment" and "Timing" correlate because models with strong multi-force convergence tend to have good timing (the forces are converging NOW). This is somewhat expected but worth monitoring.

## Impact Assessment

- The VCR system effectively has **~3 independent information dimensions** rather than 5.
- VCR composite still provides useful differentiation (stdev, spread) even with correlated axes.
- Cross-system composites remain independent: **T↔CLA r=0.040**, **T↔VCR r=-0.059** (excellent).
- The composite-level independence means the Triple Ranking system is sound even if within-VCR axes are correlated.

## Recommendations (for future cycles, NOT v3-17)

1. **Monitor, don't change**: VCR axis correlations are structural — both CAP and VEL genuinely depend on market fragmentation and buyer type. Forcing decorrelation would make axes artificial.
2. **Consider merging CAP+VEL**: In a future cycle, test a 4-axis VCR: MKT (30%), CAP+VEL merged as "Go-to-Market Feasibility" (30%), ECO (20%), MOA (20%). This would make the information loss explicit.
3. **Address MO↔CAP cross-leak**: Both axes could benefit from clearer conceptual separation. MO measures incumbent ABSENCE, CAP measures startup ABILITY. The overlap is in fragmentation — both score fragmented markets higher. Consider making CAP more about the STARTUP'S execution requirements rather than market structure.
4. **FA↔TG is acceptable**: Some correlation between "forces are aligned" and "timing is right" is conceptually expected. No action needed unless r exceeds 0.65.

## Decision: No Scoring Changes in v3-17

Weight sensitivity test showed rankings are volatile (54.6% of models move >=15 ranks with a 5-point weight shift). The current system works at the composite level. Changing axis definitions mid-cycle would create more noise than signal. This is documented for the next major refactor cycle.
