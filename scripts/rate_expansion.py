#!/usr/bin/env python3
"""
Rate 123 precycle-8 expansion models through 5-axis rating system.
Reads precycle8_expansion_2026-02-10.json, outputs v3-3_rated_expansion_2026-02-11.json
"""

import json
import math

# Load input
with open("/Users/mv/Documents/research/data/verified/precycle8_expansion_2026-02-10.json") as f:
    data = json.load(f)

# Force mapping: v2 force name -> F1-F6 codes
FORCE_MAP = {
    "baumol_cure": ["F1", "F2"],
    "silver_tsunami": ["F2"],
    "robotics_ai": ["F1"],
    "ai_inference_collapse": ["F1"],
    "jevons_expansion": ["F1"],
    "coasean_shrinkage": ["F1", "F4"],
    "regulatory_fragmentation": ["F3", "F5"],
    "pe_minsky_vulnerability": ["F4"],
    "sba_504": ["F4"],
}

# Sector phase context
SECTOR_PHASE = {
    "52": "acceleration",      # Financial
    "54": "early_disruption",  # Professional
    "31": "early_disruption", "32": "early_disruption", "33": "early_disruption",  # Manufacturing
    "62": "early_disruption",  # Healthcare
    "56": "acceleration",      # Admin
    "23": "pre_disruption",    # Construction
    "42": "pre_disruption",    # Wholesale
}

# Fear friction by sector prefix
FEAR_FRICTION = {
    "52": 1, "31": 1, "32": 1, "33": 1,
    "56": 2, "54": 3, "62": 3, "81": 2,
    "53": 2, "72": 1, "48": 2, "49": 2,
    "42": 1, "44": 1, "45": 1,
    "61": 3, "71": 2, "51": 2,
    "23": 2, "22": 2, "21": 2,
    "81": 2, "92": 3, "11": 1,
    "55": 2, "91": 3, "92": 3,
}

# Geographic baseline by model characteristics
def get_geo_scores(naics_codes, forces_v3, architecture):
    """Return average geographic grade across 8 regions."""
    primary_naics = naics_codes[0] if naics_codes else "000000"
    prefix2 = primary_naics[:2]

    # Base scores: US, EU, China, Japan, India, LATAM, SEA, MENA
    scores = [7.5, 5.5, 4.0, 6.0, 5.0, 4.5, 4.0, 3.5]

    # US-focused service businesses
    if architecture in ["acquire_and_modernize", "rollup_consolidation"]:
        scores[0] = 8.5  # US strong for physical acquisition
        scores[1] = 5.0  # EU moderate
        scores[2] = 3.0  # China weak for acquisition model
        scores[3] = 6.5  # Japan has aging businesses too
        scores[4] = 4.0
        scores[5] = 4.0
        scores[6] = 3.5
        scores[7] = 3.0

    # Manufacturing/physical
    if prefix2 in ["31", "32", "33", "23", "48", "49"]:
        scores[3] += 1.5  # Japan manufacturing
        scores[1] += 0.5  # EU manufacturing
        scores[4] += 0.5  # India manufacturing growth

    # Healthcare
    if prefix2 in ["62", "63"]:
        scores[3] += 1.5  # Japan aging population
        scores[2] -= 1.0  # China healthcare different system
        scores[1] += 0.5  # EU universal healthcare

    # Financial/compliance
    if prefix2 in ["52", "53"]:
        scores[1] += 1.5  # EU regulatory heavy
        scores[3] += 0.5

    # Elder care / silver tsunami
    if "F2" in forces_v3:
        scores[3] += 1.0  # Japan aging
        scores[1] += 0.5  # EU aging

    # Regulatory moat models
    if architecture == "regulatory_moat_builder":
        scores[0] = 8.0
        scores[1] = 6.5  # EU loves regulation
        scores[2] = 3.0
        scores[3] = 5.5

    # Platform/data models are more globally portable
    if architecture in ["platform_infrastructure", "data_compounding"]:
        scores[1] += 0.5
        scores[4] += 0.5
        scores[6] += 0.5

    # Energy sector
    if prefix2 in ["22", "21"]:
        scores[7] += 1.5  # MENA energy
        scores[4] += 1.0  # India energy growth

    # Clamp all scores to 1-10
    scores = [max(1.0, min(10.0, s)) for s in scores]

    avg = sum(scores) / len(scores)
    variance = sum((s - avg) ** 2 for s in scores) / len(scores)

    return round(avg, 1), round(variance, 1)


def map_forces(v2_forces):
    """Map v2 force names to F1-F6 codes, deduplicated."""
    f_codes = set()
    for force in v2_forces:
        if force in FORCE_MAP:
            for code in FORCE_MAP[force]:
                f_codes.add(code)
    return sorted(f_codes)


def get_sector_name(naics_codes):
    """Get human-readable sector name from NAICS."""
    NAICS_NAMES = {
        "811111": "Auto Repair", "811198": "Auto Repair Other",
        "561730": "Landscaping", "425120": "Wholesale Brokers",
        "423450": "Medical Equipment Dist", "423830": "Industrial Machinery Dist",
        "531311": "Property Management", "531312": "Property Mgmt Nonresidential",
        "531320": "Real Estate Appraisal", "523940": "Investment Advisory",
        "523910": "Misc Financial Intermediation", "523999": "Misc Financial Activities",
        "812112": "Beauty Salons", "812111": "Barber Shops",
        "811310": "Commercial Equipment Repair", "811210": "Electronic Equipment Repair",
        "512110": "Motion Picture Production", "541820": "Public Relations",
        "541613": "Marketing Consulting", "541810": "Advertising Agencies",
        "711410": "Agents/Managers for Artists", "711510": "Independent Artists",
        "488510": "Freight Arrangement", "484220": "Local Specialized Freight",
        "493110": "Warehousing", "424210": "Drugs/Sundries Wholesale",
        "423610": "Electrical Apparatus Dist", "424690": "Chemical Wholesale",
        "441110": "New Car Dealers", "814110": "Private Households",
        "622110": "Hospitals", "621511": "Medical Laboratories",
        "611430": "Professional Training", "611710": "Educational Support",
        "813910": "Business Associations", "531130": "Self-Storage",
        "424720": "Petroleum Wholesale", "221122": "Electric Power Distribution",
        "221210": "Natural Gas Distribution", "486210": "Pipeline Transportation",
        "445110": "Grocery Stores", "513120": "Periodical Publishers",
        "513199": "Other Publishers", "237310": "Highway Construction",
        "237130": "Power Line Construction", "721110": "Hotels",
        "488410": "Motor Vehicle Towing", "492210": "Local Couriers",
        "238991": "Specialty Trade Construction", "238990": "Other Specialty Contractors",
        "517111": "Wired Telecom", "517810": "Telecom Resellers",
        "324110": "Petroleum Refineries", "449210": "Furniture Stores",
        "334413": "Semiconductor Manufacturing", "325412": "Pharmaceutical Mfg",
        "237990": "Other Heavy Construction", "531120": "Commercial Leasing",
        "334111": "Computer Manufacturing", "711211": "Sports Teams",
        "481111": "Scheduled Air Transport", "481211": "Charter Air Transport",
        "813211": "Grantmaking Foundations", "624120": "Elder Care Services",
        "811121": "Auto Body Repair", "541620": "Environmental Consulting",
        "541940": "Veterinary Services", "541714": "R&D Physical Sciences",
        "541715": "R&D Social Sciences",
        # Dimension 2
        "522110": "Commercial Banking", "524210": "Insurance Agencies",
        "541330": "Engineering Services", "423510": "Metal Dist",
        "541110": "Law Firms", "424490": "Other Grocery Wholesale",
        "424410": "General Line Grocery Wholesale",
        "423430": "Computer Equipment Wholesale", "213112": "Oilfield Services",
        "531210": "Real Estate Agents", "611310": "Universities",
        "423120": "Auto Parts Wholesale", "441310": "Auto Parts Stores",
        "339112": "Surgical Instruments Mfg", "423310": "Lumber Wholesale",
        "444180": "Building Materials", "541512": "Computer Systems Design",
        "561311": "Employment Placement", "561320": "Temp Help Services",
        "921110": "Executive Offices", "921120": "Legislative Bodies",
        # Dimension 3
        "513110": "Newspaper Publishers", "561510": "Travel Agencies",
        "512199": "Other Motion Picture", "541511": "Custom Programming",
        "541519": "Other Computer Services", "541611": "Admin Consulting",
        "541618": "Other Management Consulting", "238220": "Plumbing/HVAC",
        "561720": "Janitorial Services", "561710": "Pest Control",
        "484230": "Specialized Freight Long-Distance",
        "541211": "Offices of CPAs",
        "561110": "Office Admin Services",
        # Dimension 4
        "541213": "Tax Preparation", "541310": "Architecture",
        "541370": "Surveying", "236220": "Commercial Construction",
        "541350": "Building Inspection", "621340": "Physical Therapy",
        "456110": "Pharmacies", "522310": "Mortgage Companies",
        "561312": "Executive Recruiting",
        "621210": "Dental Offices",
        "111998": "Misc Crop Farming", "111419": "Other Food Crops",
    }
    if naics_codes:
        code = naics_codes[0]
        return NAICS_NAMES.get(code, f"NAICS {code}")
    return "Unknown"


def rate_model(model, dimension):
    """Apply 5-axis rating to a single model."""
    v2_score = model["score"]
    v2_axes = model.get("axis_scores", {})
    forces = model.get("forces", [])
    arch = model.get("architecture", "")
    naics = model.get("naics_codes", [])
    one_liner = model.get("one_liner", "")
    key_data = model.get("key_data", {})

    forces_v3 = map_forces(forces)
    num_forces = len(forces_v3)
    primary_naics = naics[0] if naics else "000000"
    prefix2 = primary_naics[:2]

    # ============================================================
    # AXIS 1: Structural Necessity (SN) [0-10]
    # Must this business exist given structural forces?
    # ============================================================
    sn = 5.0  # baseline

    # High employment sectors = structurally important
    emp = key_data.get("employment", 0)
    if emp > 1000000: sn += 1.5
    elif emp > 500000: sn += 1.0
    elif emp > 200000: sn += 0.5

    # High Baumol score = structural cost pressure demanding resolution
    baumol = key_data.get("baumol_score", 0)
    if baumol > 2.0: sn += 1.5
    elif baumol > 1.5: sn += 1.0
    elif baumol > 0.5: sn += 0.5

    # Fragmentation = structural need for consolidation/modernization
    frag = key_data.get("fragmentation_proxy", 0)
    estabs = key_data.get("establishments", 0)
    if estabs > 100000 or "MOST fragmented" in one_liner or "MOST FRAGMENTED" in one_liner:
        sn += 1.0
    elif estabs > 50000 or "fragmented" in one_liner.lower():
        sn += 0.5

    # Silver tsunami = structural workforce gap
    if "silver_tsunami" in forces:
        sn += 0.5

    # Baumol cure forces = structural cost problem
    if "baumol_cure" in forces:
        sn += 0.5

    # Declining employment = structural change happening
    emp_growth = key_data.get("emp_growth", 0)
    if emp_growth < -0.01:
        sn += 0.5

    # Architecture adjustments
    if arch == "acquire_and_modernize":
        sn += 0.5  # Physical necessity - someone MUST run these businesses
    elif arch == "regulatory_moat_builder":
        sn += 0.5  # Regulatory compliance is structurally required
    elif arch == "platform_infrastructure":
        sn -= 0.5  # Platforms are nice-to-have, not must-exist
    elif arch == "marketplace_network":
        sn -= 0.5

    # Competitive density penalties
    comp = key_data.get("competitive_density", "")
    if "SATURATED" in str(comp):
        sn -= 1.5
    elif "HIGH" in str(comp):
        sn -= 0.5
    elif "LOW" in str(comp):
        sn += 0.5

    # Dimension-specific adjustments
    if dimension == 3:  # External sources - dead business revivals need extra scrutiny
        if "DEAD BUSINESS" in one_liner or "FAILURE STUDY" in one_liner:
            sn -= 0.5  # Not structurally necessary just because something died
        if "BIZBUYSELL" in one_liner:
            sn += 0.5  # Active market = structural demand

    if dimension == 4:  # AI beneficiaries
        sn += 0.3  # These businesses already exist and must exist; AI just makes them better

    # Use v2 force score as anchor (scale 0-100 -> contribution)
    v2_force = v2_axes.get("force", 70)
    sn += (v2_force - 70) * 0.03

    sn = max(3.0, min(9.5, sn))

    # ============================================================
    # AXIS 2: Force Alignment (FA) [0-10]
    # How many F1-F6 forces drive it?
    # ============================================================
    # Base: 2 forces = 5.0, each additional force adds ~1.5, each fewer subtracts ~1.5
    fa = 3.0 + num_forces * 1.5

    # Force quality matters
    if "F1" in forces_v3 and "F2" in forces_v3:
        fa += 0.5  # Tech + demographics = powerful combo
    if "F3" in forces_v3:
        fa += 0.3  # Geopolitical forces are strong right now (ACCELERATING)
    if "F4" in forces_v3:
        fa += 0.2  # Capital shifting

    # Penalize single-force models
    if num_forces <= 1:
        fa -= 1.0

    # Use v2 convergence as modifier
    v2_conv = v2_axes.get("convergence", 65)
    fa += (v2_conv - 65) * 0.02

    fa = max(3.0, min(9.5, fa))

    # ============================================================
    # AXIS 3: Geographic Grade (GG) [0-10]
    # Average viability across 8 regions
    # ============================================================
    gg_avg, gg_variance = get_geo_scores(naics, forces_v3, arch)
    gg = gg_avg

    # ============================================================
    # AXIS 4: Timing Grade (TG) [0-10]
    # Entry window + Perez crash resilience
    # ============================================================
    tg = 5.5  # baseline

    # Perez crash resilience: Late Installation phase
    # Revenue-generating, physical, cash flow positive = crash resilient
    if arch in ["acquire_and_modernize", "rollup_consolidation"]:
        tg += 1.5  # Physical, revenue-generating from day 1
    elif arch == "full_service_replacement":
        tg += 0.5  # Can be revenue-generating quickly
    elif arch in ["data_compounding", "platform_infrastructure"]:
        tg -= 0.5  # Needs scale before crash-proof
    elif arch == "marketplace_network":
        tg -= 1.0  # Needs liquidity, vulnerable in downturn
    elif arch == "arbitrage_window":
        tg += 1.0  # Distressed assets cheaper in crash

    # Sector timing
    phase = SECTOR_PHASE.get(prefix2, "")
    if phase == "acceleration":
        tg += 0.5  # Market already moving
    elif phase == "early_disruption":
        tg += 0.3  # Good window
    elif phase == "pre_disruption":
        tg += 0.8  # Best entry window - before disruption hits

    # Infrastructure spending tailwind
    if "IIJA" in one_liner or "Infrastructure" in one_liner or "CHIPS" in one_liner or "IRA" in one_liner:
        tg += 0.5

    # Silver tsunami timing
    if "silver_tsunami" in forces:
        tg += 0.5  # Happening NOW

    # Declining sectors = timing urgency
    if emp_growth < -0.01 or "DECLINING" in one_liner or "declining" in one_liner:
        tg += 0.3  # Distressed pricing available now

    # Warning signals for timing
    if "WARNING" in one_liner:
        tg -= 0.5
    if "SATURATED" in str(comp):
        tg -= 1.0

    # Fear friction adjustment
    ff = FEAR_FRICTION.get(prefix2, 2)
    if ff >= 4:
        tg -= 0.5  # High fear = slow adoption
    elif ff <= 1:
        tg += 0.3  # Low fear = fast adoption

    # v2 timing as anchor
    v2_timing = v2_axes.get("timing", 70)
    tg += (v2_timing - 72) * 0.03

    tg = max(3.5, min(9.5, tg))

    # ============================================================
    # AXIS 5: Capital Efficiency (CE) [0-10]
    # Revenue-per-dollar, survives 18mo funding freeze
    # ============================================================
    ce = 5.5  # baseline

    # Architecture determines capital efficiency
    if arch == "acquire_and_modernize":
        ce += 1.0  # Revenue from day 1, SBA 504 eligible
    elif arch == "full_service_replacement":
        ce += 1.0  # Low capex, can bootstrap
    elif arch == "platform_infrastructure":
        ce += 0.5  # SaaS margins but needs GTM spend
    elif arch == "data_compounding":
        ce -= 0.5  # Needs data before value
    elif arch == "rollup_consolidation":
        ce -= 0.5  # Capital intensive for acquisitions
    elif arch == "marketplace_network":
        ce -= 1.0  # Needs liquidity on both sides
    elif arch == "arbitrage_window":
        ce += 0.5  # Cheap acquisitions
    elif arch == "regulatory_moat_builder":
        ce += 0.5  # Compliance = recurring revenue

    # Low avg pay = lower labor cost base
    avg_pay = key_data.get("avg_pay", 0)
    if avg_pay > 0:
        if avg_pay < 50000:
            ce += 0.5  # Low labor cost
        elif avg_pay > 150000:
            ce -= 0.5  # High labor cost to displace means high value but also high expectations

    # SBA 504 eligibility
    if "SBA 504" in one_liner or "SBA" in one_liner:
        ce += 0.5

    # Coasean shrinkage = capital efficient by nature
    if "coasean_shrinkage" in forces:
        ce += 0.5

    # Jevons expansion = revenue multiplier
    if "jevons_expansion" in forces:
        ce += 0.3

    # Concentrated markets harder to enter
    if "CONCENTRATED" in str(comp):
        ce -= 0.5

    # v2 capital as anchor
    v2_cap = v2_axes.get("capital", 72)
    ce += (v2_cap - 72) * 0.03

    ce = max(3.5, min(9.5, ce))

    # ============================================================
    # COMPOSITE SCORE
    # ============================================================
    composite = (sn * 25 + fa * 25 + gg * 20 + tg * 15 + ce * 15) / 10
    composite = round(composite, 1)

    # Round all scores
    sn = round(sn, 1)
    fa = round(fa, 1)
    gg = round(gg, 1)
    tg = round(tg, 1)
    ce = round(ce, 1)

    # ============================================================
    # CATEGORY ASSIGNMENT
    # ============================================================
    # Calculate fear_friction_gap for FEAR_ECONOMY
    fear_gap = FEAR_FRICTION.get(prefix2, 2)

    category = "PARKED"

    if sn >= 8.0 and fa >= 8.0:
        category = "STRUCTURAL_WINNER"
    elif fa >= 7.0:
        category = "FORCE_RIDER"
    elif gg_variance > 4.0:
        category = "GEOGRAPHIC_PLAY"
    elif tg >= 8.0 and sn >= 6.0:
        category = "TIMING_ARBITRAGE"
    elif ce >= 8.0 and sn >= 6.0:
        category = "CAPITAL_MOAT"
    elif fear_gap > 3:
        category = "FEAR_ECONOMY"
    elif primary_naics[:4] in ["5415", "5419", "6241"] or "No NAICS" in one_liner:
        # Check for emerging category
        if sn >= 5.0:
            category = "EMERGING_CATEGORY"

    # Override: CONDITIONAL if composite >= 60 but didn't fit above
    if category == "PARKED" and composite >= 60:
        category = "CONDITIONAL"

    # Override: PARKED if composite < 60 regardless
    if composite < 60:
        category = "PARKED"

    # ============================================================
    # KEY V3 CONTEXT
    # ============================================================
    context_parts = []

    if num_forces >= 4:
        context_parts.append(f"{num_forces}-force convergence ({'+'.join(forces_v3)})")
    elif num_forces >= 3:
        context_parts.append(f"Strong {num_forces}-force alignment ({'+'.join(forces_v3)})")

    if arch == "acquire_and_modernize":
        context_parts.append("Physical acquisition = Perez-crash resilient")
    elif arch == "rollup_consolidation":
        context_parts.append("Rollup = capital intensive but crash-resilient at scale")
    elif arch == "data_compounding":
        context_parts.append("Data moat builds over time; vulnerable pre-scale")
    elif arch == "regulatory_moat_builder":
        context_parts.append("Regulatory complexity = permanent moat")

    if "SATURATED" in str(comp):
        context_parts.append("WARNING: Saturated competitive density")
    elif "HIGH" in str(comp):
        context_parts.append("Elevated competitive density")
    elif "LOW" in str(comp):
        context_parts.append("Low competitive density = open field")

    if baumol > 1.5:
        context_parts.append(f"Baumol {baumol:.1f}x = high stored energy")

    if gg_variance > 4.0:
        context_parts.append(f"Geographic variance {gg_variance:.1f} = regional play")

    phase = SECTOR_PHASE.get(prefix2, "")
    if phase:
        context_parts.append(f"Sector phase: {phase}")

    if tg >= 8.0:
        context_parts.append("Strong timing window")

    if not context_parts:
        context_parts.append(f"Expansion model, {num_forces} forces, {arch} architecture")

    key_context = ". ".join(context_parts)

    return {
        "id": model["id"],
        "name": model["name"],
        "v2_score": v2_score,
        "sector_naics": primary_naics[:4] if len(primary_naics) >= 4 else primary_naics,
        "sector_name": get_sector_name(naics),
        "architecture": arch,
        "forces_v3": forces_v3,
        "scores": {"SN": sn, "FA": fa, "GG": gg, "TG": tg, "CE": ce},
        "composite": composite,
        "category": category,
        "one_liner": one_liner,
        "key_v3_context": key_context
    }


# ============================================================
# PROCESS ALL MODELS
# ============================================================
rated_models = []

# Dimension 1: NAICS decomposition
for m in data["dimension_1_naics_decomposition"]["models"]:
    rated_models.append(rate_model(m, 1))

# Dimension 2: Supply chain adjacencies
for m in data["dimension_2_supply_chain_adjacencies"]["models"]:
    rated_models.append(rate_model(m, 2))

# Dimension 3: External sources
for m in data["dimension_3_external_sources"]["models"]:
    rated_models.append(rate_model(m, 3))

# Dimension 4: AI beneficiaries
for m in data["dimension_4_ai_beneficiaries"]["models"]:
    rated_models.append(rate_model(m, 4))

# ============================================================
# SUMMARY STATS
# ============================================================
categories = {}
for rm in rated_models:
    cat = rm["category"]
    categories[cat] = categories.get(cat, 0) + 1

composites = [rm["composite"] for rm in rated_models]
composites.sort()

# Sort rated models by composite descending
rated_models.sort(key=lambda x: x["composite"], reverse=True)

output = {
    "batch": "precycle8_expansion",
    "rated_at": "2026-02-11",
    "rating_system": "v3-3_5axis",
    "models_rated": len(rated_models),
    "methodology": {
        "axes": {
            "SN": "Structural Necessity (25%): Must this business exist given structural forces?",
            "FA": "Force Alignment (25%): How many F1-F6 forces drive it?",
            "GG": "Geographic Grade (20%): Average viability across 8 regions (US/EU/China/Japan/India/LATAM/SEA/MENA)",
            "TG": "Timing Grade (15%): Entry window + Perez crash resilience",
            "CE": "Capital Efficiency (15%): Revenue-per-dollar, survives 18mo funding freeze"
        },
        "composite_formula": "(SN*25 + FA*25 + GG*20 + TG*15 + CE*15) / 10 → 0-100",
        "force_mapping": {
            "F1_Tech": "ai_inference_collapse, jevons_expansion, robotics_ai, baumol_cure(partial), coasean_shrinkage(partial)",
            "F2_Demographics": "silver_tsunami, baumol_cure(partial)",
            "F3_Geopolitics": "regulatory_fragmentation(partial)",
            "F4_Capital": "pe_minsky_vulnerability, sba_504, coasean_shrinkage(partial)",
            "F5_Psychology": "regulatory_fragmentation(partial)",
            "F6_Energy": "mapped where applicable"
        }
    },
    "summary": {
        "total_models": len(rated_models),
        "composite_range": f"{min(composites):.1f} - {max(composites):.1f}",
        "composite_mean": f"{sum(composites)/len(composites):.1f}",
        "composite_median": f"{composites[len(composites)//2]:.1f}",
        "category_distribution": categories,
        "by_dimension": {
            "dim1_naics": len(data["dimension_1_naics_decomposition"]["models"]),
            "dim2_supply_chain": len(data["dimension_2_supply_chain_adjacencies"]["models"]),
            "dim3_external": len(data["dimension_3_external_sources"]["models"]),
            "dim4_ai_beneficiaries": len(data["dimension_4_ai_beneficiaries"]["models"])
        }
    },
    "rated_models": rated_models
}

# Write output
outpath = "/Users/mv/Documents/research/data/verified/v3-3_rated_expansion_2026-02-11.json"
with open(outpath, "w") as f:
    json.dump(output, f, indent=2)

print(f"Rated {len(rated_models)} models")
print(f"Composite range: {min(composites):.1f} - {max(composites):.1f}")
print(f"Mean: {sum(composites)/len(composites):.1f}, Median: {composites[len(composites)//2]:.1f}")
print(f"\nCategory distribution:")
for cat, count in sorted(categories.items(), key=lambda x: -x[1]):
    print(f"  {cat}: {count}")
print(f"\nTop 10 by composite:")
for rm in rated_models[:10]:
    print(f"  {rm['composite']:5.1f} | {rm['category']:20s} | {rm['id']} — {rm['name']}")
print(f"\nBottom 5 by composite:")
for rm in rated_models[-5:]:
    print(f"  {rm['composite']:5.1f} | {rm['category']:20s} | {rm['id']} — {rm['name']}")
