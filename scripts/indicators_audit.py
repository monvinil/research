#!/usr/bin/env python3
"""
Comprehensive Scoring Health Audit for the 608-model dataset.
Analyzes axis distributions, within/cross-system correlations,
confidence & evidence quality, Polanyi coverage, catalyst scenarios,
and category distributions.

Usage: python3 scripts/indicators_audit.py
"""

import json
import sys
from collections import Counter, defaultdict
from itertools import combinations

import numpy as np
from scipy import stats

# ---------------------------------------------------------------------------
# Load data
# ---------------------------------------------------------------------------

DATA_PATH = "/Users/mv/Documents/research/data/verified/v3-12_normalized_2026-02-12.json"

with open(DATA_PATH) as f:
    raw = json.load(f)

models = raw["models"]
N = len(models)
print(f"{'='*80}")
print(f"  SCORING HEALTH AUDIT -- {N} models")
print(f"  Data: {DATA_PATH}")
print(f"{'='*80}\n")

# ---------------------------------------------------------------------------
# Extract arrays for each axis
# ---------------------------------------------------------------------------

T_AXES = ["SN", "FA", "EC", "TG", "CE"]
CLA_AXES = ["MO", "MA", "VD", "DV"]
VCR_AXES = ["MKT", "CAP", "ECO", "VEL", "MOA"]

def safe_get(d, keys):
    """Navigate nested dict safely."""
    for k in keys:
        if d is None or not isinstance(d, dict):
            return None
        d = d.get(k)
    return d

# Build arrays
t_data = {}
for ax in T_AXES:
    t_data[ax] = np.array([m["scores"][ax] for m in models if m.get("scores") and ax in m["scores"]])

cla_data = {}
for ax in CLA_AXES:
    vals = []
    for m in models:
        v = safe_get(m, ["cla", "scores", ax])
        if v is not None:
            vals.append(v)
    cla_data[ax] = np.array(vals)

vcr_data = {}
for ax in VCR_AXES:
    vals = []
    for m in models:
        v = safe_get(m, ["vcr", "scores", ax])
        if v is not None:
            vals.append(v)
    vcr_data[ax] = np.array(vals)

# Composites
t_comp = np.array([m["composite"] for m in models if m.get("composite") is not None])
cla_comp = np.array([safe_get(m, ["cla", "composite"]) for m in models if safe_get(m, ["cla", "composite"]) is not None])
vcr_comp = np.array([safe_get(m, ["vcr", "composite"]) for m in models if safe_get(m, ["vcr", "composite"]) is not None])

# ---------------------------------------------------------------------------
# SECTION 1: Axis Distributions
# ---------------------------------------------------------------------------

print(f"{'='*80}")
print("  SECTION 1: AXIS DISTRIBUTIONS")
print(f"{'='*80}\n")

def print_axis_stats(name, arr):
    n = len(arr)
    if n == 0:
        print(f"  {name:>8s}: NO DATA\n")
        return
    mn = np.mean(arr)
    md = np.median(arr)
    sd = np.std(arr, ddof=1) if n > 1 else 0.0
    lo = np.min(arr)
    hi = np.max(arr)
    floor_pct = 100.0 * np.sum(arr <= 2) / n
    ceiling_pct = 100.0 * np.sum(arr >= 9) / n
    center_pct = 100.0 * np.sum(arr == 5.0) / n
    print(f"  {name:>8s}  n={n:>4d}  mean={mn:5.2f}  med={md:5.2f}  std={sd:5.2f}  "
          f"min={lo:4.1f}  max={hi:5.1f}  "
          f"floor(<=2)={floor_pct:5.1f}%  ceil(>=9)={ceiling_pct:5.1f}%  center(=5)={center_pct:5.1f}%")

print("  --- Transformation axes ---")
for ax in T_AXES:
    print_axis_stats(ax, t_data[ax])
print_axis_stats("T_comp", t_comp)

print("\n  --- CLA (Opportunity) axes ---")
for ax in CLA_AXES:
    print_axis_stats(ax, cla_data[ax])
print_axis_stats("CLA_comp", cla_comp)

print("\n  --- VCR (VC ROI) axes ---")
for ax in VCR_AXES:
    print_axis_stats(ax, vcr_data[ax])
print_axis_stats("VCR_comp", vcr_comp)

# ---------------------------------------------------------------------------
# Helper: paired correlation on models that have both values
# ---------------------------------------------------------------------------

def paired_corr(models_list, get1, get2):
    """Build paired arrays from models where both values exist, return r, p, n."""
    xs, ys = [], []
    for m in models_list:
        v1 = get1(m)
        v2 = get2(m)
        if v1 is not None and v2 is not None:
            xs.append(v1)
            ys.append(v2)
    if len(xs) < 3:
        return None, None, len(xs)
    r, p = stats.pearsonr(xs, ys)
    return r, p, len(xs)

# ---------------------------------------------------------------------------
# SECTION 2: Within-System Correlations
# ---------------------------------------------------------------------------

print(f"\n{'='*80}")
print("  SECTION 2: WITHIN-SYSTEM CORRELATIONS")
print(f"{'='*80}\n")

def print_corr_table(axis_names, getter_fn, label):
    """Print correlation matrix for a scoring system."""
    print(f"  --- {label} ---")
    pairs = list(combinations(axis_names, 2))
    warnings = []
    for a1, a2 in pairs:
        r, p, n = paired_corr(models,
                              lambda m, _a=a1: getter_fn(m, _a),
                              lambda m, _a=a2: getter_fn(m, _a))
        if r is not None:
            flag = " *** HIGH CORRELATION WARNING ***" if abs(r) > 0.40 else ""
            print(f"    {a1:>4s} -- {a2:<4s}  r={r:+6.3f}  p={p:.4f}  n={n:>4d}{flag}")
            if abs(r) > 0.40:
                warnings.append((a1, a2, r))
        else:
            print(f"    {a1:>4s} -- {a2:<4s}  insufficient data (n={n})")
    if warnings:
        print(f"\n    >> {len(warnings)} pair(s) exceed |r|>0.40 threshold")
    else:
        print(f"\n    >> All pairs below |r|>0.40 threshold -- good independence")
    print()

def t_getter(m, ax):
    s = m.get("scores")
    if s and ax in s:
        return s[ax]
    return None

def cla_getter(m, ax):
    return safe_get(m, ["cla", "scores", ax])

def vcr_getter(m, ax):
    return safe_get(m, ["vcr", "scores", ax])

print_corr_table(T_AXES, t_getter, "Transformation (T) axis pairs")
print_corr_table(CLA_AXES, cla_getter, "CLA (Opportunity) axis pairs")
print_corr_table(VCR_AXES, vcr_getter, "VCR (VC ROI) axis pairs")

# ---------------------------------------------------------------------------
# SECTION 3: Cross-System Correlations
# ---------------------------------------------------------------------------

print(f"{'='*80}")
print("  SECTION 3: CROSS-SYSTEM CORRELATIONS")
print(f"{'='*80}\n")

# Composite vs Composite
print("  --- Composite vs Composite ---")

r, p, n = paired_corr(models,
                       lambda m: m.get("composite"),
                       lambda m: safe_get(m, ["cla", "composite"]))
if r is not None:
    flag = " *** HIGH CORRELATION WARNING ***" if abs(r) > 0.40 else ""
    print(f"    {'T_comp':>10s} -- {'CLA_comp':<10s}  r={r:+6.3f}  p={p:.2e}  n={n:>4d}{flag}")

r, p, n = paired_corr(models,
                       lambda m: m.get("composite"),
                       lambda m: safe_get(m, ["vcr", "composite"]))
if r is not None:
    flag = " *** HIGH CORRELATION WARNING ***" if abs(r) > 0.40 else ""
    print(f"    {'T_comp':>10s} -- {'VCR_comp':<10s}  r={r:+6.3f}  p={p:.2e}  n={n:>4d}{flag}")

r, p, n = paired_corr(models,
                       lambda m: safe_get(m, ["cla", "composite"]),
                       lambda m: safe_get(m, ["vcr", "composite"]))
if r is not None:
    flag = " *** HIGH CORRELATION WARNING ***" if abs(r) > 0.40 else ""
    print(f"    {'CLA_comp':>10s} -- {'VCR_comp':<10s}  r={r:+6.3f}  p={p:.2e}  n={n:>4d}{flag}")

# All cross-axis pairs
print("\n  --- Cross-axis correlations (top 10 by |r|) ---")

cross_pairs = []

# T vs CLA
for ta in T_AXES:
    for ca in CLA_AXES:
        r, p, n = paired_corr(models,
                              lambda m, _a=ta: t_getter(m, _a),
                              lambda m, _a=ca: cla_getter(m, _a))
        if r is not None:
            cross_pairs.append((f"T:{ta}", f"CLA:{ca}", r, p, n))

# T vs VCR
for ta in T_AXES:
    for va in VCR_AXES:
        r, p, n = paired_corr(models,
                              lambda m, _a=ta: t_getter(m, _a),
                              lambda m, _a=va: vcr_getter(m, _a))
        if r is not None:
            cross_pairs.append((f"T:{ta}", f"VCR:{va}", r, p, n))

# CLA vs VCR
for ca in CLA_AXES:
    for va in VCR_AXES:
        r, p, n = paired_corr(models,
                              lambda m, _a=ca: cla_getter(m, _a),
                              lambda m, _a=va: vcr_getter(m, _a))
        if r is not None:
            cross_pairs.append((f"CLA:{ca}", f"VCR:{va}", r, p, n))

# Sort by |r| descending
cross_pairs.sort(key=lambda x: abs(x[2]), reverse=True)

for i, (n1, n2, r, p, n) in enumerate(cross_pairs[:10]):
    flag = " *** HIGH ***" if abs(r) > 0.40 else ""
    print(f"    {i+1:>2d}. {n1:>10s} -- {n2:<10s}  r={r:+6.3f}  p={p:.2e}  n={n:>4d}{flag}")

total_cross = len(cross_pairs)
high_cross = sum(1 for x in cross_pairs if abs(x[2]) > 0.40)
print(f"\n    >> {high_cross}/{total_cross} cross-axis pairs exceed |r|>0.40")

# ---------------------------------------------------------------------------
# SECTION 4: Confidence & Evidence Quality
# ---------------------------------------------------------------------------

print(f"\n{'='*80}")
print("  SECTION 4: CONFIDENCE & EVIDENCE QUALITY")
print(f"{'='*80}\n")

# Confidence tier distribution
tier_counts = Counter(m.get("confidence_tier", "MISSING") for m in models)
print("  --- Confidence Tier Distribution ---")
for tier in ["HIGH", "MODERATE", "LOW", "MISSING"]:
    ct = tier_counts.get(tier, 0)
    pct = 100.0 * ct / N
    bar = "#" * int(pct / 2)
    print(f"    {tier:>10s}: {ct:>4d} ({pct:5.1f}%)  {bar}")

# Evidence quality
eq_vals = []
eq_by_tier = defaultdict(list)
eq_zero_models = []

for m in models:
    eq = m.get("evidence_quality")
    tier = m.get("confidence_tier", "MISSING")
    if eq is not None:
        eq_vals.append(eq)
        eq_by_tier[tier].append(eq)
        if eq == 0:
            eq_zero_models.append((m["id"], m["name"]))

eq_arr = np.array(eq_vals)
print(f"\n  --- Evidence Quality Distribution (n={len(eq_arr)}) ---")
print(f"    mean={np.mean(eq_arr):.2f}  med={np.median(eq_arr):.1f}  "
      f"std={np.std(eq_arr, ddof=1):.2f}  min={np.min(eq_arr)}  max={np.max(eq_arr)}")

# Histogram
eq_hist = Counter(eq_vals)
print(f"\n    {'EQ':>4s}  {'Count':>6s}  {'%':>6s}  Bar")
for score in range(0, 11):
    ct = eq_hist.get(score, 0)
    pct = 100.0 * ct / len(eq_vals) if eq_vals else 0
    bar = "#" * int(pct)
    print(f"    {score:>4d}  {ct:>6d}  {pct:>5.1f}%  {bar}")

# EQ=0 models
print(f"\n  --- Models with EQ=0 ({len(eq_zero_models)}) ---")
if eq_zero_models:
    for mid, mname in eq_zero_models:
        print(f"    {mid:<30s}  {mname}")
else:
    print("    (none)")

# Mean EQ by tier
print(f"\n  --- Mean Evidence Quality by Confidence Tier ---")
for tier in ["HIGH", "MODERATE", "LOW", "MISSING"]:
    vals = eq_by_tier.get(tier, [])
    if vals:
        print(f"    {tier:>10s}: mean={np.mean(vals):5.2f}  n={len(vals)}")
    else:
        print(f"    {tier:>10s}: no data")

# ---------------------------------------------------------------------------
# SECTION 5: Polanyi Coverage
# ---------------------------------------------------------------------------

print(f"\n{'='*80}")
print("  SECTION 5: POLANYI COVERAGE")
print(f"{'='*80}\n")

with_polanyi = []
without_polanyi = []
for m in models:
    if m.get("polanyi") is not None and isinstance(m["polanyi"], dict):
        with_polanyi.append(m)
    else:
        without_polanyi.append(m)

print(f"  With Polanyi data:    {len(with_polanyi):>4d} ({100*len(with_polanyi)/N:.1f}%)")
print(f"  Without Polanyi data: {len(without_polanyi):>4d} ({100*len(without_polanyi)/N:.1f}%)")

# Automation exposure distribution for those that have it
ae_vals = []
for m in with_polanyi:
    ae = m["polanyi"].get("automation_exposure")
    if ae is not None:
        ae_vals.append(ae)
if ae_vals:
    ae_arr = np.array(ae_vals)
    print(f"\n  Automation Exposure (n={len(ae_arr)}):")
    print(f"    mean={np.mean(ae_arr):.3f}  med={np.median(ae_arr):.3f}  "
          f"std={np.std(ae_arr, ddof=1):.3f}  min={np.min(ae_arr):.3f}  max={np.max(ae_arr):.3f}")

# Sector clusters missing Polanyi
def cluster_key(model_id):
    """Extract sector cluster from model ID (first 2-3 meaningful segments)."""
    parts = model_id.split("-")
    if len(parts) >= 3:
        return "-".join(parts[:3]) if not parts[2].isdigit() else "-".join(parts[:2])
    return "-".join(parts[:2])

missing_clusters = Counter()
for m in without_polanyi:
    ck = cluster_key(m["id"])
    missing_clusters[ck] += 1

print(f"\n  --- Sector Clusters Missing Polanyi ({len(missing_clusters)} clusters, {len(without_polanyi)} models) ---")
for ck, ct in missing_clusters.most_common():
    sample_names = [m["name"] for m in without_polanyi if cluster_key(m["id"]) == ck][:2]
    print(f"    {ck:<25s}  {ct:>3d} models  (e.g., {sample_names[0][:55]})")

# ---------------------------------------------------------------------------
# SECTION 6: Catalyst Summary
# ---------------------------------------------------------------------------

print(f"\n{'='*80}")
print("  SECTION 6: CATALYST SUMMARY")
print(f"{'='*80}\n")

catalyst_models = [m for m in models if m.get("catalyst_scenario") is not None]
print(f"  Total models with catalyst scenarios: {len(catalyst_models)}/{N}")

if catalyst_models:
    # By cluster
    cluster_counts = Counter()
    asym_vals = []
    for m in catalyst_models:
        cs = m["catalyst_scenario"]
        cl = cs.get("cluster", cs.get("cluster_name", "unknown"))
        cluster_counts[cl] += 1
        ar = cs.get("asymmetry_ratio")
        if ar is not None:
            asym_vals.append(ar)

    print(f"\n  --- By Cluster ---")
    for cl, ct in cluster_counts.most_common():
        print(f"    {cl:<45s}  {ct:>3d}")

    if asym_vals:
        asym_arr = np.array(asym_vals)
        print(f"\n  --- Asymmetry Ratio Distribution (n={len(asym_arr)}) ---")
        print(f"    mean={np.mean(asym_arr):.3f}  med={np.median(asym_arr):.3f}  "
              f"std={np.std(asym_arr, ddof=1):.3f}  "
              f"min={np.min(asym_arr):.3f}  max={np.max(asym_arr):.3f}")
else:
    print("  No catalyst scenarios found.")

# ---------------------------------------------------------------------------
# SECTION 7: Category Distribution
# ---------------------------------------------------------------------------

print(f"\n{'='*80}")
print("  SECTION 7: CATEGORY DISTRIBUTION")
print(f"{'='*80}\n")

# Primary category = first element of category list
primary_cats = Counter()
cat_tier = defaultdict(lambda: Counter())

for m in models:
    cats = m.get("category", [])
    if isinstance(cats, list) and len(cats) > 0:
        pc = cats[0]
    elif isinstance(cats, str):
        pc = cats
    else:
        pc = "(empty)"
    tier = m.get("confidence_tier", "MISSING")
    primary_cats[pc] += 1
    cat_tier[pc][tier] += 1

print("  --- Primary Category Counts ---")
for cat, ct in primary_cats.most_common():
    pct = 100.0 * ct / N
    print(f"    {cat:<30s}  {ct:>4d} ({pct:5.1f}%)")

# Cross-tab
all_tiers = ["HIGH", "MODERATE", "LOW", "MISSING"]
present_tiers = [t for t in all_tiers if any(cat_tier[c].get(t, 0) > 0 for c in primary_cats)]

print(f"\n  --- Category x Confidence Tier Cross-Tab ---")
header = f"    {'Category':<30s}" + "".join(f"  {t:>10s}" for t in present_tiers) + f"  {'Total':>6s}"
print(header)
print(f"    {'-'*30}" + "".join(f"  {'-'*10}" for _ in present_tiers) + f"  {'-'*6}")

for cat, _ in primary_cats.most_common():
    row = f"    {cat:<30s}"
    total = 0
    for t in present_tiers:
        ct = cat_tier[cat].get(t, 0)
        total += ct
        row += f"  {ct:>10d}"
    row += f"  {total:>6d}"
    print(row)

# Totals row
row = f"    {'TOTAL':<30s}"
for t in present_tiers:
    ct = sum(cat_tier[c].get(t, 0) for c in primary_cats)
    row += f"  {ct:>10d}"
row += f"  {N:>6d}"
print(row)

# ---------------------------------------------------------------------------
# Summary
# ---------------------------------------------------------------------------

print(f"\n{'='*80}")
print("  AUDIT COMPLETE")
print(f"{'='*80}")
print(f"  Models: {N}")
print(f"  T-scored: {len(t_comp)}, CLA-scored: {len(cla_comp)}, VCR-scored: {len(vcr_comp)}")
print(f"  Polanyi: {len(with_polanyi)}, Catalyst: {len(catalyst_models)}")
print(f"  Confidence: {tier_counts.get('HIGH',0)} HIGH / {tier_counts.get('MODERATE',0)} MOD / {tier_counts.get('LOW',0)} LOW")
print()
