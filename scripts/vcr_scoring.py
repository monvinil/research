#!/usr/bin/env python3
"""
VC ROI Assessment (VCR) — Third Independent Ranking Dimension

Adds a third independent ranking ("VC ROI Rank") alongside:
  - Transformation Certainty (5-axis composite)
  - Opportunity/CLA (4-axis composite)

The VCR measures: "At $10M seed valuation, what is the fundamental
ROI multiple achievable in 3-5 years, derived from market size,
capture mechanics, unit economics, revenue velocity, and moat trajectory?"

5 VCR Axes:
  MKT — Market Magnitude (25%): Realistic capturable market in $
  CAP — Capture Feasibility (25%): Can a seed startup grab share?
  ECO — Unit Economics (20%): Margin and capital efficiency profile
  VEL — Revenue Velocity (15%): Speed from $0 to $5M ARR
  MOA — Moat Trajectory (15%): Defensibility arc over 5 years

VCR Composite = (MKT*25 + CAP*25 + ECO*20 + VEL*15 + MOA*15) / 10

VCR Categories:
  FUND_RETURNER:  VCR >= 75 — potential to return entire fund from one bet
  STRONG_MULTIPLE: VCR >= 60 — 10-30x seed multiple, strong Series A
  VIABLE_RETURN:  VCR >= 45 — 5-10x seed multiple, good business
  MARGINAL:       VCR >= 30 — 2-5x, better bootstrapped or PE-backed
  VC_POOR:        VCR < 30  — below VC return threshold

Triple Ranking Principle:
  Transformation, Opportunity, and VC ROI sit side by side.
  They are NEVER merged into a single number.
  Each carries independent analytical weight.

Input:  data/verified/v3-10_normalized_2026-02-12.json
Output: data/verified/v3-10_normalized_2026-02-12.json (updated in place)
        data/ui/models.json (updated with VCR fields)
        data/ui/dashboard.json (updated with VCR sections)
"""

import json
import re
import statistics
from collections import Counter
from pathlib import Path

BASE = Path("/Users/mv/Documents/research/data/verified")
UI_DIR = Path("/Users/mv/Documents/research/data/ui")

NORMALIZED_FILE = BASE / "v3-12_normalized_2026-02-12.json"
UI_MODELS = UI_DIR / "models.json"
UI_DASHBOARD = UI_DIR / "dashboard.json"

VCR_WEIGHTS = {"MKT": 25, "CAP": 25, "ECO": 20, "VEL": 15, "MOA": 15}
SEED_VALUATION_M = 10  # $10M seed

# ──────────────────────────────────────────────────────────────────────
# Sector TAM Lookup (real market sizes in $M, by NAICS prefix)
# Sourced from IBISWorld, Grand View Research, Statista, BLS QCEW
# ──────────────────────────────────────────────────────────────────────

SECTOR_TAM_M = {
    # 4-digit matches take priority over 2-digit
    # Accommodation & Food Services (72)
    "7211": 220000,  # Hotels & motels $220B
    "7221": 350000,  # Full-service restaurants $350B
    "7222": 380000,  # Limited-service restaurants $380B
    "7223": 65000,   # Special food services (catering) $65B
    "7224": 28000,   # Drinking places $28B
    "72": 900000,    # Total accommodation & food $900B+

    # Transportation & Warehousing (48-49)
    "4841": 350000,  # General freight trucking $350B
    "4842": 80000,   # Specialized freight trucking $80B
    "4811": 280000,  # Scheduled air transport $280B
    "4821": 80000,   # Rail transportation $80B
    "4831": 50000,   # Deep sea/coastal transport $50B
    "4851": 45000,   # Urban transit $45B
    "4881": 80000,   # Support activities for air $80B
    "4885": 30000,   # Freight arrangement (brokers) $30B
    "4911": 90000,   # Postal service $90B
    "4921": 120000,  # Couriers & express delivery $120B
    "4931": 60000,   # Warehousing & storage $60B
    "48": 800000,    # Total transportation $800B
    "49": 300000,    # Total warehousing/postal/courier $300B

    # Construction (23)
    "2361": 500000,  # Residential building $500B
    "2362": 350000,  # Nonresidential building $350B
    "2371": 120000,  # Utility system construction $120B
    "2372": 100000,  # Land subdivision $100B
    "2373": 150000,  # Highway/street/bridge $150B
    "2381": 120000,  # Foundation/structure contractors $120B
    "2382": 250000,  # Building equipment contractors $250B (HVAC/electrical/plumbing)
    "2383": 80000,   # Building finishing contractors $80B
    "2389": 60000,   # Other specialty trades $60B
    "23": 2000000,   # Total construction $2T

    # Admin/Support/Waste (56)
    "5613": 200000,  # Employment services (staffing) $200B
    "5614": 60000,   # Business support services $60B
    "5615": 50000,   # Travel arrangement $50B
    "5616": 90000,   # Investigation & security services $90B
    "5617": 120000,  # Services to buildings (janitorial/landscape) $120B
    "5621": 80000,   # Waste collection $80B
    "5622": 20000,   # Waste treatment $20B
    "5629": 15000,   # Remediation services $15B
    "56": 650000,    # Total admin/support $650B

    # Previously covered sectors — add specific sub-sector TAMs
    "5221": 800000,  # Banking $800B revenue
    "5231": 300000,  # Securities/commodity brokerage $300B
    "5241": 1300000, # Insurance carriers $1.3T
    "5411": 120000,  # Legal services $120B
    "5412": 250000,  # Accounting services $250B
    "5415": 550000,  # Computer systems design $550B
    "5413": 65000,   # Architectural/engineering $65B
    "5416": 120000,  # Management consulting $120B
    "52": 2500000,   # Total finance/insurance $2.5T
    "54": 1200000,   # Total professional services $1.2T

    "6211": 350000,  # Offices of physicians $350B
    "6214": 60000,   # Outpatient care centers $60B
    "6221": 1100000, # General medical hospitals $1.1T
    "6231": 180000,  # Nursing care facilities $180B
    "6241": 50000,   # Individual/family services $50B
    "62": 2600000,   # Total healthcare $2.6T

    "4451": 800000,  # Grocery stores $800B
    "4461": 60000,   # Health/personal care stores $60B
    "4471": 600000,  # Gas stations $600B
    "4481": 280000,  # Clothing stores $280B
    "4411": 250000,  # Auto dealers $250B
    "44": 3500000,   # Total retail $3.5T
    "45": 800000,    # Total general merchandise/misc $800B

    "3111": 200000,  # Animal food manufacturing $200B
    "3114": 60000,   # Fruit/vegetable preserving $60B
    "3241": 250000,  # Petroleum & coal products $250B
    "3254": 300000,  # Pharmaceutical manufacturing $300B
    "3341": 100000,  # Computer & peripheral equipment $100B
    "3344": 120000,  # Semiconductor manufacturing $120B
    "3364": 300000,  # Aerospace product mfg $300B
    "31": 900000,    # Total food/beverage/textile mfg $900B
    "32": 800000,    # Total wood/paper/chemical/plastic mfg $800B
    "33": 1200000,   # Total metals/machinery/electronics mfg $1.2T

    "22": 500000,    # Utilities $500B
    "51": 1500000,   # Information sector $1.5T
    "53": 500000,    # Real estate $500B
    "55": 200000,    # Management of companies $200B
    "61": 180000,    # Educational services $180B
    "71": 200000,    # Arts/entertainment $200B
    "81": 350000,    # Other services $350B
    "92": 400000,    # Public administration $400B (est. addressable tech spend)
    "11": 150000,    # Agriculture $150B
    "21": 200000,    # Mining $200B
}

# Buyer-type classification by architecture
# Determines independent CAP and VEL scoring
BUYER_TYPE = {
    "vertical_saas": "smb_mid",
    "saas": "mid_enterprise",
    "platform_saas": "mid_enterprise",
    "horizontal_saas": "mid_enterprise",
    "data_compounding": "mid_enterprise",
    "platform": "multi",
    "platform_infrastructure": "enterprise",
    "infrastructure_platform": "enterprise",
    "network_platform": "multi",
    "marketplace_network": "multi",
    "marketplace_platform": "multi",
    "marketplace": "multi",
    "marketplace_optimizer": "smb_mid",
    "platform_marketplace": "multi",
    "fear_economy_capture": "enterprise",
    "regulatory_moat_builder": "enterprise",
    "service_platform": "smb_mid",
    "advisory_platform": "smb_mid",
    "advisory": "mid_enterprise",
    "academy_platform": "consumer_smb",
    "product": "multi",
    "product_platform": "smb_mid",
    "physical_product_platform": "smb_mid",
    "hardware_plus_saas": "mid_enterprise",
    "full_service_replacement": "smb_mid",
    "managed_service": "mid_enterprise",
    "hybrid_service": "smb_mid",
    "acquire_and_modernize": "smb_mid",
    "rollup_consolidation": "smb_mid",
    "roll_up_modernize": "smb_mid",
    "rollup": "smb_mid",
    "automation": "enterprise",
    "physical_production_ai": "enterprise",
    "project_developer": "enterprise",
    "project_development": "enterprise",
    "distress_operator": "smb_mid",
    "arbitrage_window": "multi",
    "geographic_arbitrage": "smb_mid",
    "service": "smb_mid",
    "micro_firm_os": "consumer_smb",
    "ai_copilot": "consumer_smb",
    "workflow_automation": "smb_mid",
    "compliance_automation": "mid_enterprise",
    "predictive_analytics": "mid_enterprise",
    "embedded_fintech": "multi",
    "insurtech": "mid_enterprise",
    "regtech": "enterprise",
    "supply_chain_optimization": "enterprise",
    "robotics_automation": "enterprise",
    "autonomous_systems": "enterprise",
    "iot_platform": "mid_enterprise",
    "digital_twin": "enterprise",
    "cybersecurity": "mid_enterprise",
    "edtech": "consumer_smb",
    "healthtech": "mid_enterprise",
    "proptech": "smb_mid",
    "climate_tech": "enterprise",
    "agritech": "smb_mid",
    "logistics_optimization": "mid_enterprise",
    "content_automation": "consumer_smb",
    "creator_economy": "consumer_smb",
    "decision_intelligence": "enterprise",
    "simulation_modeling": "enterprise",
}

# Buyer type → independent CAP base modifier and VEL modifier
BUYER_CAP_BASE = {
    "consumer_smb": 8,    # Direct acquisition, PLG, self-serve
    "smb_mid": 7,         # Mixed channels, moderate sales effort
    "multi": 6,           # Multiple buyer types, complex GTM
    "mid_enterprise": 5,  # Longer sales cycles, need champions
    "enterprise": 4,      # Long procurement, committees, POCs
    "government": 2,      # Procurement bureaucracy, 12-24 month cycles
}

BUYER_VEL_BASE = {
    "consumer_smb": 8,    # <6 months to meaningful revenue
    "smb_mid": 7,         # 3-9 months
    "multi": 6,           # 6-12 months average
    "mid_enterprise": 5,  # 6-18 months
    "enterprise": 4,      # 12-24 months
    "government": 2,      # 18-36 months
}

# NAICS-level fragmentation scores (1-10, 10=most fragmented)
# Based on Census establishment counts and HHI concentration
SECTOR_FRAGMENTATION = {
    "72": 10,   # 1M+ restaurants, extreme fragmentation
    "23": 10,   # 750K+ construction firms, extreme
    "81": 9,    # Other services, very fragmented
    "44": 8,    # Retail, fragmented but consolidating
    "45": 8,
    "56": 8,    # Admin/support, many small operators
    "53": 8,    # Real estate, fragmented
    "54": 7,    # Professional services, moderately fragmented
    "62": 6,    # Healthcare, mixed (hospitals consolidated, practices fragmented)
    "48": 6,    # Transportation, mixed
    "61": 6,    # Education, mixed
    "42": 7,    # Wholesale, many distributors
    "31": 5,    # Manufacturing, moderately concentrated
    "32": 5,
    "33": 5,
    "51": 4,    # Information, concentrated
    "52": 4,    # Finance, concentrated
    "22": 3,    # Utilities, very concentrated
    "55": 3,    # Management holding companies
    "21": 4,    # Mining, moderately concentrated
    "92": 2,    # Government, by definition concentrated buyer
    "11": 7,    # Agriculture, fragmented
    "71": 7,    # Arts/entertainment, fragmented
    "49": 5,    # Warehousing/postal
}


# ──────────────────────────────────────────────────────────────────────
# VCR Framework Definition
# ──────────────────────────────────────────────────────────────────────

VCR_SYSTEM = {
    "name": "VC ROI Assessment",
    "version": "2.1",
    "seed_valuation_M": SEED_VALUATION_M,
    "axes": {
        "MKT": {
            "name": "Market Magnitude",
            "weight": 0.25,
            "description": "Realistic capturable market in 3-5 years. Not hand-waving TAM but plausible revenue ceiling for a single company.",
            "scale": {
                "1-2": "Niche market, <$100M realistic addressable",
                "3-4": "$100M-500M addressable, modest VC outcome",
                "5-6": "$500M-2B addressable, single-fund returner potential",
                "7-8": "$2B-10B addressable, multiple paths to $500M+ revenue",
                "9-10": "$10B+ addressable, platform-scale outcome (log-scale, top quartile only)"
            }
        },
        "CAP": {
            "name": "Capture Feasibility",
            "weight": 0.25,
            "description": "Can a seed-funded startup realistically capture meaningful share in 3-5 years? Measures actual capture mechanics, not hype.",
            "scale": {
                "1-2": "Incumbents own distribution, 24+ month sales cycles, regulatory blocks",
                "3-4": "Government/enterprise procurement, 12-24 month cycles, capital-intensive",
                "5-6": "Mixed channels, some accessible, 6-12 month sales cycles",
                "7-8": "Direct acquisition viable, PLG possible, 3-6 month cycles",
                "9-10": "Greenfield with pull demand, viral/PLG, customers actively seeking"
            }
        },
        "ECO": {
            "name": "Unit Economics",
            "weight": 0.20,
            "description": "Steady-state margin and capital efficiency. Architecture-driven — maps business model to known margin profile.",
            "scale": {
                "1-2": "Hardware-dependent, <25% gross margins, massive capex",
                "3-4": "Service-heavy, 30-45% gross margins, linear scaling",
                "5-6": "Mixed model, 45-60% gross margins, some recurring revenue",
                "7-8": "Software/SaaS, 65-80% gross margins, strong unit economics",
                "9-10": "Pure software/data, 80%+ margins, near-zero marginal cost"
            }
        },
        "VEL": {
            "name": "Revenue Velocity",
            "weight": 0.15,
            "description": "Speed from $0 to $5M ARR. Determines whether 3-5 year window produces markable outcome.",
            "scale": {
                "1-2": "36+ months to first material revenue, deep-tech R&D",
                "3-4": "18-36 months, long enterprise sales or regulatory approvals",
                "5-6": "12-18 months, standard B2B SaaS sales cycle",
                "7-8": "6-12 months, PLG or SMB self-serve",
                "9-10": "<6 months, viral/PLG with instant activation, pull demand"
            }
        },
        "MOA": {
            "name": "Moat Trajectory",
            "weight": 0.15,
            "description": "Once you have traction, does the business get harder or easier to compete with? Measures 5-year defensibility arc.",
            "scale": {
                "1-2": "Commodity forever, anyone can replicate, no switching costs",
                "3-4": "Moderate switching costs, relationship moat only",
                "5-6": "Meaningful switching costs + some data effects, but displaceable",
                "7-8": "Strong compounding moat — data flywheel, regulatory capture, multi-product lock-in",
                "9-10": "Winner-take-most dynamics, data moat grows exponentially"
            }
        },
    },
    "composite_formula": "(MKT*25 + CAP*25 + ECO*20 + VEL*15 + MOA*15) / 10",
    "categories": {
        "FUND_RETURNER": "VCR >= 75",
        "STRONG_MULTIPLE": "VCR >= 60",
        "VIABLE_RETURN": "VCR >= 45",
        "MARGINAL": "VCR >= 30",
        "VC_POOR": "VCR < 30"
    }
}


# ──────────────────────────────────────────────────────────────────────
# Architecture → Base Score Mappings
# ──────────────────────────────────────────────────────────────────────

ARCH_ECO = {
    "data_compounding": 10,
    "vertical_saas": 9,
    "saas": 8,
    "platform_saas": 8,
    "platform": 7,
    "platform_infrastructure": 7,
    "infrastructure_platform": 7,
    "network_platform": 7,
    "regulatory_moat_builder": 7,
    "fear_economy_capture": 7,
    "marketplace_network": 6,
    "marketplace_platform": 6,
    "marketplace": 6,
    "marketplace_optimizer": 6,
    "platform_marketplace": 6,
    "service_platform": 6,
    "advisory_platform": 6,
    "academy_platform": 6,
    "platform_service": 6,
    "product_platform": 6,
    "product": 6,
    "arbitrage_window": 6,
    "hardware_plus_saas": 6,
    "full_service_replacement": 5,
    "acquire_and_modernize": 5,
    "managed_service": 5,
    "advisory": 5,
    "hybrid_service": 5,
    "distress_operator": 5,
    "geographic_arbitrage": 5,
    "physical_product_platform": 5,
    "project_developer": 4,
    "project_development": 4,
    "rollup_consolidation": 4,
    "roll_up_modernize": 4,
    "rollup": 4,
    "physical_production_ai": 4,
    "automation": 4,
    "service": 4,
}

ARCH_VEL = {
    "vertical_saas": 7,
    "saas": 7,
    "platform_saas": 7,
    "fear_economy_capture": 7,
    "arbitrage_window": 7,
    "data_compounding": 6,
    "regulatory_moat_builder": 6,
    "service_platform": 6,
    "advisory_platform": 6,
    "advisory": 6,
    "managed_service": 6,
    "product": 6,
    "product_platform": 6,
    "geographic_arbitrage": 6,
    "platform": 5,
    "platform_infrastructure": 5,
    "infrastructure_platform": 5,
    "network_platform": 5,
    "marketplace_network": 5,
    "marketplace_platform": 5,
    "marketplace": 5,
    "marketplace_optimizer": 5,
    "platform_marketplace": 5,
    "platform_service": 5,
    "academy_platform": 5,
    "full_service_replacement": 5,
    "hybrid_service": 5,
    "hardware_plus_saas": 5,
    "physical_product_platform": 5,
    "distress_operator": 5,
    "acquire_and_modernize": 4,
    "rollup_consolidation": 4,
    "roll_up_modernize": 4,
    "rollup": 4,
    "project_developer": 4,
    "project_development": 4,
    "physical_production_ai": 4,
    "automation": 4,
    "service": 4,
}

ARCH_MOA = {
    "data_compounding": 9,
    "platform": 8,
    "platform_infrastructure": 8,
    "infrastructure_platform": 8,
    "network_platform": 8,
    "regulatory_moat_builder": 8,
    "marketplace_network": 7,
    "marketplace_platform": 7,
    "marketplace": 7,
    "marketplace_optimizer": 7,
    "platform_marketplace": 7,
    "vertical_saas": 7,
    "fear_economy_capture": 7,
    "platform_saas": 7,
    "product_platform": 7,
    "physical_product_platform": 7,
    "saas": 6,
    "service_platform": 6,
    "platform_service": 6,
    "academy_platform": 6,
    "advisory_platform": 6,
    "hardware_plus_saas": 6,
    "acquire_and_modernize": 5,
    "rollup_consolidation": 5,
    "roll_up_modernize": 5,
    "rollup": 5,
    "full_service_replacement": 5,
    "physical_production_ai": 5,
    "automation": 5,
    "distress_operator": 5,
    "product": 5,
    "hybrid_service": 5,
    "managed_service": 4,
    "project_developer": 4,
    "project_development": 4,
    "geographic_arbitrage": 4,
    "advisory": 3,
    "service": 3,
    "arbitrage_window": 3,
}

# Architecture -> base MKT (can be overridden by TAM parsing)
ARCH_MKT = {
    "platform": 8,
    "platform_infrastructure": 7,
    "infrastructure_platform": 7,
    "marketplace_network": 7,
    "marketplace_platform": 7,
    "marketplace": 7,
    "marketplace_optimizer": 7,
    "platform_marketplace": 7,
    "network_platform": 7,
    "data_compounding": 6,
    "vertical_saas": 6,
    "saas": 6,
    "platform_saas": 6,
    "full_service_replacement": 6,
    "regulatory_moat_builder": 5,
    "fear_economy_capture": 5,
    "acquire_and_modernize": 5,
    "rollup_consolidation": 5,
    "roll_up_modernize": 5,
    "rollup": 5,
    "service_platform": 5,
    "platform_service": 5,
    "product_platform": 5,
    "physical_product_platform": 5,
    "product": 5,
    "hardware_plus_saas": 5,
    "automation": 5,
    "physical_production_ai": 5,
    "advisory_platform": 4,
    "academy_platform": 4,
    "advisory": 4,
    "managed_service": 4,
    "hybrid_service": 4,
    "service": 4,
    "project_developer": 4,
    "project_development": 4,
    "distress_operator": 4,
    "arbitrage_window": 4,
    "geographic_arbitrage": 4,
}

# Architecture -> base CAP
ARCH_CAP = {
    "vertical_saas": 8,
    "saas": 8,
    "platform_saas": 7,
    "fear_economy_capture": 7,
    "arbitrage_window": 7,
    "data_compounding": 7,
    "service_platform": 7,
    "advisory_platform": 7,
    "advisory": 7,
    "academy_platform": 6,
    "product": 6,
    "product_platform": 6,
    "managed_service": 6,
    "hybrid_service": 6,
    "service": 6,
    "regulatory_moat_builder": 6,
    "full_service_replacement": 6,
    "geographic_arbitrage": 6,
    "marketplace_network": 5,
    "marketplace_platform": 5,
    "marketplace": 5,
    "marketplace_optimizer": 5,
    "platform_marketplace": 5,
    "platform": 5,
    "platform_infrastructure": 5,
    "infrastructure_platform": 5,
    "network_platform": 5,
    "platform_service": 5,
    "physical_product_platform": 5,
    "hardware_plus_saas": 5,
    "distress_operator": 5,
    "acquire_and_modernize": 4,
    "rollup_consolidation": 4,
    "roll_up_modernize": 4,
    "rollup": 4,
    "automation": 4,
    "physical_production_ai": 4,
    "project_developer": 4,
    "project_development": 4,
}

# Revenue multiples at exit by architecture (low, high)
ARCH_MULTIPLES = {
    "data_compounding": (12, 25),
    "platform": (10, 20),
    "platform_infrastructure": (10, 18),
    "infrastructure_platform": (10, 18),
    "network_platform": (10, 18),
    "vertical_saas": (8, 15),
    "saas": (8, 12),
    "platform_saas": (8, 15),
    "marketplace_network": (5, 12),
    "marketplace_platform": (5, 12),
    "marketplace": (5, 10),
    "marketplace_optimizer": (5, 10),
    "platform_marketplace": (6, 12),
    "regulatory_moat_builder": (6, 12),
    "fear_economy_capture": (8, 15),
    "product_platform": (6, 12),
    "physical_product_platform": (5, 10),
    "hardware_plus_saas": (6, 10),
    "service_platform": (5, 10),
    "platform_service": (5, 10),
    "advisory_platform": (4, 8),
    "academy_platform": (4, 8),
    "product": (5, 10),
    "full_service_replacement": (3, 6),
    "acquire_and_modernize": (4, 8),
    "rollup_consolidation": (3, 5),
    "roll_up_modernize": (3, 5),
    "rollup": (3, 5),
    "automation": (5, 8),
    "physical_production_ai": (4, 7),
    "project_developer": (3, 5),
    "project_development": (3, 5),
    "distress_operator": (3, 6),
    "arbitrage_window": (3, 7),
    "geographic_arbitrage": (3, 6),
    "advisory": (3, 6),
    "managed_service": (3, 6),
    "service": (3, 5),
    "hybrid_service": (3, 6),
}


# ──────────────────────────────────────────────────────────────────────
# NAICS Sector Adjustments (2-digit prefix)
# ──────────────────────────────────────────────────────────────────────

# (mkt_adj, cap_adj, eco_adj, vel_adj, moa_adj)
# MKT adjustments reduced — log-scale scoring already differentiates by sector TAM.
# Non-MKT adjustments unchanged.
SECTOR_ADJ = {
    "11": (0, -1, 0, -1, 0),    # Agriculture: slow, resistant
    "21": (-0.5, -1, 0, -2, 0), # Mining: small, slow procurement
    "22": (0, -1, 0, -1, 1),    # Utilities: slow adoption, strong moats (TAM already in lookup)
    "23": (0.5, 0, 0, 0, 0),    # Construction: under-digitized bonus
    "31": (0, 0, -1, 0, 0),     # Manufacturing food: lower margins
    "32": (0, 0, -1, 0, 0),     # Manufacturing chem: moderate
    "33": (0.5, 0, -1, 0, 1),   # Manufacturing advanced: hardware-ish, strong moats
    "42": (0, 1, 0, 0, 0),      # Wholesale: fragmented
    "44": (0.5, 1, 0, 1, 0),    # Retail: faster cycles
    "45": (0.5, 1, 0, 1, 0),    # Retail: faster cycles
    "48": (0, 0, -1, -1, 0),    # Transportation: capital heavy
    "51": (0.5, 0, 1, 0, 1),    # Information: tech-native, data moats
    "52": (0, -1, 0, -1, 1),    # Finance: regulated, strong moats
    "53": (0, 1, 0, 0, -1),     # Real estate: fragmented, weak moats
    "54": (0.5, 1, 0, 0, 0),    # Professional services: fragmented
    "55": (0, -1, 0, -1, 0),    # Management: slow, enterprise
    "56": (0, 1, -1, 1, -1),    # Admin services: fragmented, commodity
    "61": (0, 0, 0, 0, 0),      # Education: moderate
    "62": (0.5, -1, 0, -1, 1),  # Healthcare: regulated
    "72": (0.5, 1, -1, 1, -1),  # Accommodation/food: fragmented, thin margins
    "81": (0, 1, -1, 0, -1),    # Other services: fragmented, commodity
}

# Defense-specific penalty (procurement barriers)
DEFENSE_PENALTY = {"CAP": -3, "VEL": -2}


# ──────────────────────────────────────────────────────────────────────
# Manual VCR Overrides (~35 models with deep analysis)
# Format: (MKT, CAP, ECO, VEL, MOA, rationale)
# ──────────────────────────────────────────────────────────────────────

MANUAL_VCR = {
    # Retail Media cluster
    "MC-V38-44-003": (10, 2, 7, 5, 9, "Retail media $69B+ but Amazon controls 77%. Massive market, near-impossible capture at seed stage."),
    "MC-V38-44-003-L3": (7, 8, 9, 8, 7, "Measurement/attribution for 50+ retail networks. $2-3.5B TAM, fragmented, SaaS margins. Fast sales."),
    "MC-V38-44-003-L4": (6, 8, 9, 8, 7, "Mid-market enabling tech (Kevel, Topsort). $1-2B TAM, clear buyers, vertical SaaS."),
    "MC-V38-44-003-L5": (6, 7, 8, 7, 8, "Retail data clean rooms. $2B→$10B by 2033. Privacy regulation tailwind. Platform moat."),

    # Warehouse Robotics cluster
    "MC-V38-44-002": (9, 3, 4, 4, 7, "Warehouse robotics $181B by 2031 but requires massive capex. Hardware margins. Not seed-fundable at core."),
    "MC-V38-44-002-L3": (7, 7, 8, 6, 8, "Warehouse orchestration software. Multi-vendor robot coordination. Pure SaaS, data moat."),
    "MC-V38-44-002-L6": (6, 7, 9, 7, 8, "Robot fleet maintenance SaaS. $8.7B market. Predictive maintenance + fleet mgmt. High margins, recurring."),

    # Defense cluster (procurement penalty)
    "V3-DEF-001": (7, 2, 5, 2, 7, "Autonomous drone swarms. Massive defense TAM but procurement barriers kill seed-stage capture."),
    "V3-DEF-002-L3": (6, 7, 8, 7, 7, "OSINT platform — dual-use defense + commercial. Enterprise SaaS, no clearance required."),
    "MC-DEF-011": (6, 6, 9, 7, 8, "CMMC compliance SaaS. 220K DIB companies, regulatory cliff 2026. High urgency, high margins."),
    "MC-DEF-012-L4": (6, 7, 9, 8, 8, "Cloud compliance automation. FedRAMP/CMMC/NIST from 18mo→90 days. SaaS, regulatory moat."),
    "V3-DEF-003": (7, 3, 7, 3, 7, "Defense cybersecurity. Big TAM but procurement kills velocity and capture."),

    # Utilities cluster
    "MC-UTL-001": (7, 5, 7, 5, 7, "Grid optimization. Big market but utility sales cycles are 18-24 months."),
    "MC-UTL-004-L5": (5, 7, 9, 7, 7, "DC energy management software. Smaller TAM but SaaS margins, data center buyers."),

    # Micro-Firm cluster (emergent)
    "V3-EMRG-001": (8, 8, 8, 8, 8, "Micro-Firm AI OS. 7.5M US micro-firms. Platform play. AI agent reliability crossed threshold. Pull demand."),
    "MC-V39-MICRO-004": (7, 8, 9, 8, 6, "AI accountant for micro-firms. 7.5M TAM, $150-400/mo SaaS. Fast adoption but weak moat (commoditizable)."),
    "MC-V39-MICRO-005": (6, 8, 8, 8, 6, "AI sales/lead gen for solopreneurs. Fast adoption, SaaS, but low switching costs."),
    "MC-V39-MICRO-003": (6, 8, 8, 8, 7, "AI legal/compliance for micro-firms. Regulatory complexity creates some moat."),

    # Information sector
    "MC-INFO-001": (7, 6, 8, 6, 7, "AI-native data center ops. $30B+ market. SaaS but enterprise sales cycle."),
    "MC-INFO-002": (8, 8, 9, 8, 7, "AI code quality/security audit. 82% devs use AI tools. Growing WITH AI adoption. Pull demand."),

    # AI Governance / Fear Economy
    "V3-FEAR-001": (7, 7, 7, 6, 8, "AI governance platform. Enterprise compliance, growing regulatory push, but immature buying process."),
    "V3-FEAR-002": (5, 8, 6, 7, 4, "AI job transition coaching. Big addressable but thin margins, weak moat."),

    # Healthcare
    "MC-V37-62-003": (8, 5, 6, 4, 7, "Healthcare revenue cycle AI. Massive TAM (140K providers) but slow buyer, complex implementation."),
    "MC-V37-62-001": (7, 4, 7, 4, 7, "AI clinical decision support. Big but FDA pathway + hospital procurement = very slow."),

    # Financial Services
    "MC-V37-523-002": (5, 6, 8, 7, 8, "Securities compliance automation. 4K broker-dealers. SEC regulatory tailwind. SaaS with regulatory moat."),
    "MC-V37-523-001": (6, 5, 7, 5, 7, "Algorithmic market making AI. Good margins but requires significant capital reserves."),

    # Manufacturing
    "MC-V39-MFG-001": (8, 5, 5, 4, 6, "Manufacturing quality AI. Big market but factory sales cycles are 12-24 months."),
    "MC-V39-MFG-011": (6, 5, 8, 6, 8, "Defense manufacturing compliance SaaS. 220K suppliers. CMMC+ITAR+AS9100."),
    "MC-V39-MFG-006": (6, 7, 5, 5, 6, "CNC shop acquire & modernize. Good unit economics post-acquisition but rollup execution risk."),

    # Education
    "MC-V37-61-001": (6, 7, 7, 7, 6, "AI tutoring platform. Large addressable (K-12 + higher ed). PLG possible. Moderate moat."),

    # IT Services
    "MC-V37-5415-001": (8, 6, 6, 5, 5, "AI-native consulting. Massive market (TCS, Accenture replacement) but service model limits margins."),
    "MC-V37-5415-003": (5, 7, 9, 7, 7, "AI DevOps automation SaaS. Clear buyer (engineering teams). High margins."),

    # Real Estate
    "MC-V37-53-001": (7, 7, 5, 5, 5, "AI property management platform. 488K establishments. Fragmented. But service-heavy execution."),
}


# ──────────────────────────────────────────────────────────────────────
# TAM Extraction from Text
# ──────────────────────────────────────────────────────────────────────

def parse_tam_from_text(text):
    """Extract market size from one_liner and deep_dive_evidence."""
    if not text:
        return None

    amounts_m = []
    # Match "$X.XB", "$X.XM", "$X.XT", "$X.X billion", etc.
    for match in re.finditer(r'\$(\d+(?:\.\d+)?)\s*([BMT](?:illion|rillion)?)\b', text, re.IGNORECASE):
        val = float(match.group(1))
        unit = match.group(2)[0].upper()
        if unit == 'T':
            amounts_m.append(val * 1_000_000)
        elif unit == 'B':
            amounts_m.append(val * 1_000)
        elif unit == 'M':
            amounts_m.append(val)

    growth = None
    gm = re.search(r'(\d+(?:\.\d+)?)\s*%\s*(?:CAGR|annual|growth|annually)', text, re.IGNORECASE)
    if gm:
        growth = float(gm.group(1))

    if amounts_m:
        return {
            "tam_low_M": min(amounts_m),
            "tam_high_M": max(amounts_m),
            "growth_pct": growth,
        }
    return None


def tam_to_mkt_score(tam_m, growth_pct=None):
    """Convert TAM in $M to MKT score (1-10) using log-scale.

    Log-scale provides much better differentiation across the 4-order-of-magnitude
    range of realistic addressable TAMs ($30M to $100B+). The old step-function
    gave 56% of models a score of 10 — zero discriminating power.

    Anchors: $30M → 1, $100M → 3, $500M → 5, $2B → 7, $10B → 9, $50B+ → 10
    """
    import math
    if tam_m <= 0:
        return 1

    log_tam = math.log10(tam_m)

    # Map log10(TAM_M) to 1-10 score
    # log10(30) = 1.48 → 1, log10(100000) = 5.0 → 10
    # Linear: score = (log_tam - 1.48) / (5.0 - 1.48) * 9 + 1
    LOG_MIN = 1.48   # $30M
    LOG_MAX = 5.0    # $100B
    base = (log_tam - LOG_MIN) / (LOG_MAX - LOG_MIN) * 9 + 1

    # Growth modifier (smaller impact with log scale)
    if growth_pct and growth_pct > 30:
        base += 0.5
    elif growth_pct and growth_pct > 20:
        base += 0.3

    return round(min(10, max(1, base)), 1)


# ──────────────────────────────────────────────────────────────────────
# Heuristic VCR Scoring
# ──────────────────────────────────────────────────────────────────────

def clamp(v, lo=1, hi=10):
    return max(lo, min(hi, round(v, 1)))


def lookup_sector_tam(naics_full):
    """Look up TAM from SECTOR_TAM_M using longest NAICS prefix match."""
    # Try 4-digit, then 3-digit, then 2-digit
    for length in (4, 3, 2):
        prefix = naics_full[:length]
        if prefix in SECTOR_TAM_M:
            return SECTOR_TAM_M[prefix]
    return None


def heuristic_vcr(model):
    """Compute VCR scores fundamentally from market structure and architecture.

    v2 (fundamental): Minimizes cross-references to existing CLA/Transformation
    scores. Scoring is driven primarily by:
      - Architecture type (business model economics)
      - Sector TAM data (real market sizes)
      - Buyer type analysis (who buys, how fast)
      - Market fragmentation (establishment counts)
      - Keyword signals from evidence text
    """
    arch = model.get("architecture", "")
    naics_full = model.get("sector_naics", "")
    naics = naics_full[:2]
    mid = model.get("id", "")
    scores = model.get("scores", {})
    cla = model.get("cla", {})
    cla_scores = cla.get("scores", {})
    one_liner = model.get("one_liner", "") or ""
    evidence = model.get("deep_dive_evidence", "")
    if isinstance(evidence, dict):
        evidence = json.dumps(evidence)
    elif not isinstance(evidence, str):
        evidence = str(evidence) if evidence else ""
    all_text = one_liner + " " + evidence
    text_lower = all_text.lower()

    # ── MKT: Market Magnitude ──
    # Priority: parsed TAM from text > sector TAM lookup > architecture default
    tam_data = parse_tam_from_text(all_text)
    tam_source = "none"
    if tam_data:
        mkt = tam_to_mkt_score(tam_data["tam_high_M"], tam_data.get("growth_pct"))
        tam_source = f"parsed ${tam_data['tam_high_M']:.0f}M"
    else:
        sector_tam = lookup_sector_tam(naics_full)
        if sector_tam:
            # Scale sector TAM down — a startup addresses a software/AI layer, not total revenue
            # Previous percentages (3%/1.5%/0.5%) were too generous — produced $15B-$75B
            # "addressable" markets that all scored MKT=10, eliminating differentiation.
            # Revised: reflects that a single AI startup competes for a narrow slice
            # 4-digit NAICS: specific sub-sector → 1% of sub-sector revenue
            # 3-digit NAICS: moderate specificity → 0.5%
            # 2-digit NAICS: very broad → 0.15% of total sector revenue
            naics_digits = len(naics_full.rstrip())
            if naics_digits >= 4:
                tam_pct = 0.01
            elif naics_digits >= 3:
                tam_pct = 0.005
            else:
                tam_pct = 0.0015
            realistic_tam = sector_tam * tam_pct
            mkt = tam_to_mkt_score(realistic_tam)
            tam_source = f"sector ${sector_tam:.0f}M→${realistic_tam:.0f}M addressable"
        else:
            mkt = ARCH_MKT.get(arch, 5)
            tam_source = "arch_default"

    # ── CAP: Capture Feasibility ── (FUNDAMENTALIZED)
    # Three independent inputs: architecture, buyer type, fragmentation
    # Minimal cross-reference to CLA (20% down from 60%)

    # Input 1: Architecture base (what kind of product)
    arch_cap = ARCH_CAP.get(arch, 5)

    # Input 2: Buyer type (who buys, how accessible)
    buyer = BUYER_TYPE.get(arch, "mid_enterprise")
    buyer_cap = BUYER_CAP_BASE.get(buyer, 5)

    # Input 3: Market fragmentation (how many potential buyers)
    frag = SECTOR_FRAGMENTATION.get(naics, 5)
    frag_bonus = (frag - 5) * 0.3  # -1.2 to +1.5 based on fragmentation

    # Blend: 40% architecture + 30% buyer type + 10% fragmentation + 20% CLA MO
    mo = cla_scores.get("MO", 5)
    cap = arch_cap * 0.40 + buyer_cap * 0.30 + frag_bonus + mo * 0.20

    # Keyword adjustments for CAP
    if "fragmented" in text_lower or "150k+" in text_lower or "100k+" in text_lower:
        cap += 0.5
    if "monopol" in text_lower or "duopol" in text_lower or "oligopol" in text_lower:
        cap -= 1.0
    if "regulatory cliff" in text_lower or "mandate" in text_lower:
        cap += 0.5  # forced adoption
    if "nascent" in text_lower or "greenfield" in text_lower or "no dominant" in text_lower:
        cap += 0.5
    if "plg" in text_lower or "self-serve" in text_lower or "product-led" in text_lower:
        cap += 0.5
    if "enterprise sales" in text_lower or "rfe" in text_lower or "rfp" in text_lower:
        cap -= 0.5

    # ── ECO: Unit Economics ── (reduced CE dependency)
    eco = ARCH_ECO.get(arch, 5)

    # CE minor adjustment (15% down from 30%)
    ce = scores.get("CE", 5)
    eco = eco * 0.85 + ce * 0.15

    # Keyword adjustments for ECO
    if "saas" in text_lower or "recurring" in text_lower or "subscription" in text_lower:
        eco += 0.3
    if "hardware" in text_lower or "physical" in text_lower or "capex" in text_lower:
        eco -= 0.3
    if "thin margin" in text_lower or "low margin" in text_lower:
        eco -= 0.5

    # ── VEL: Revenue Velocity ── (FUNDAMENTALIZED)
    # Primary: architecture velocity + buyer type velocity
    # Minor TG adjustment (15% down from 40%)

    arch_vel = ARCH_VEL.get(arch, 5)
    buyer_vel = BUYER_VEL_BASE.get(buyer, 5)

    # Blend: 50% architecture + 35% buyer type + 15% TG
    tg = scores.get("TG", 5)
    vel = arch_vel * 0.50 + buyer_vel * 0.35 + tg * 0.15

    # Keyword adjustments for VEL
    if "procurement" in text_lower or "clearance" in text_lower or "certification" in text_lower:
        vel -= 0.5
    if "regulatory cliff" in text_lower or "mandate" in text_lower:
        vel += 0.5  # urgency accelerates
    if "pilot" in text_lower or "poc" in text_lower:
        vel -= 0.3  # implies enterprise evaluation
    if "viral" in text_lower or "word of mouth" in text_lower:
        vel += 0.5

    # ── MOA: Moat Trajectory ── (already mostly independent)
    moa = ARCH_MOA.get(arch, 5)

    # SN bonus — structurally necessary businesses have durable moats
    sn = scores.get("SN", 5)
    if sn >= 8:
        moa += 1

    # CLA MA cross-reference (conditional, small impact)
    ma = cla_scores.get("MA", 5)
    if ma >= 7 and arch in ("data_compounding", "platform", "platform_infrastructure",
                             "vertical_saas", "marketplace_network"):
        moa += 0.5

    # Keyword adjustments for MOA
    if "network effect" in text_lower or "data flywheel" in text_lower:
        moa += 0.5
    if "commodity" in text_lower or "undifferentiated" in text_lower:
        moa -= 1
    if "switching cost" in text_lower or "lock-in" in text_lower:
        moa += 0.5
    if "api integration" in text_lower or "embedded" in text_lower:
        moa += 0.3

    # ── Apply NAICS sector adjustments (refined, smaller impact) ──
    adj = SECTOR_ADJ.get(naics, (0, 0, 0, 0, 0))
    mkt += adj[0]
    cap += adj[1] * 0.5   # Halve sector CAP adjustment since fragmentation already captures this
    eco += adj[2]
    vel += adj[3] * 0.5   # Halve sector VEL adjustment since buyer type already captures this
    moa += adj[4]

    # ── Defense penalty ──
    is_defense = mid.startswith("V3-DEF") or mid.startswith("MC-DEF") or "defense" in one_liner.lower()
    if is_defense:
        cap += DEFENSE_PENALTY["CAP"]
        vel += DEFENSE_PENALTY["VEL"]

    # ── Sub-model bonus ──
    if model.get("parent_id"):
        cap += 0.5

    # ── VCR evidence from deep dive (new in v3-12) ──
    vcr_ev = model.get("vcr_evidence", {})
    if vcr_ev:
        # If deep dive includes explicit VCR evidence, use keyword signals
        ev_text = json.dumps(vcr_ev).lower() if isinstance(vcr_ev, dict) else str(vcr_ev).lower()
        if "high margin" in ev_text or ">70%" in ev_text or ">80%" in ev_text:
            eco += 0.5
        if "fast adoption" in ev_text or "pull demand" in ev_text:
            vel += 0.5
        if "data moat" in ev_text or "network effect" in ev_text:
            moa += 0.5

    # Clamp all scores
    mkt = clamp(mkt)
    cap = clamp(cap)
    eco = clamp(eco)
    vel = clamp(vel)
    moa = clamp(moa)

    rationale = f"Fundamental v2: arch={arch}, buyer={buyer}, frag={SECTOR_FRAGMENTATION.get(naics, '?')}"
    rationale += f", tam_source={tam_source}"
    if is_defense:
        rationale += ", defense penalty"

    return mkt, cap, eco, vel, moa, rationale


# ──────────────────────────────────────────────────────────────────────
# ROI Multiple Estimator
# ──────────────────────────────────────────────────────────────────────

MKT_TO_TAM_M = {
    1: 10, 2: 30, 3: 75, 4: 150, 5: 400,
    6: 800, 7: 2000, 8: 4000, 9: 8000, 10: 20000
}

CAP_TO_SHARE = {
    1: 0.001, 2: 0.002, 3: 0.004, 4: 0.006, 5: 0.01,
    6: 0.015, 7: 0.02, 8: 0.03, 9: 0.04, 10: 0.05
}


def estimate_roi_multiple(model, vcr_scores):
    """Estimate seed ROI multiple from fundamentals."""
    arch = model.get("architecture", "")
    mult_range = ARCH_MULTIPLES.get(arch, (5, 10))

    # Interpolate revenue multiple using MOA
    moa = vcr_scores["MOA"]
    mult = mult_range[0] + (mult_range[1] - mult_range[0]) * (moa - 1) / 9

    # TAM from MKT score
    mkt_rounded = max(1, min(10, round(vcr_scores["MKT"])))
    tam = MKT_TO_TAM_M.get(mkt_rounded, 400)

    # Capture rate from CAP score
    cap_rounded = max(1, min(10, round(vcr_scores["CAP"])))
    share = CAP_TO_SHARE.get(cap_rounded, 0.01)

    # VEL accelerates capture
    vel_mult = 0.7 + (vcr_scores["VEL"] - 1) * 0.1  # 0.7x to 1.6x

    year5_revenue = tam * share * vel_mult
    exit_val = year5_revenue * mult
    roi_multiple = round(exit_val / SEED_VALUATION_M, 1)
    roi_multiple = max(0.1, min(500, roi_multiple))

    return {
        "year5_revenue_M": round(year5_revenue, 1),
        "revenue_multiple": round(mult, 1),
        "exit_val_M": round(exit_val, 0),
        "seed_roi_multiple": roi_multiple,
    }


# ──────────────────────────────────────────────────────────────────────
# Composite & Classification
# ──────────────────────────────────────────────────────────────────────

def calc_vcr_composite(mkt, cap, eco, vel, moa):
    return round((mkt * 25 + cap * 25 + eco * 20 + vel * 15 + moa * 15) / 10, 2)


def classify_vcr(vcr):
    if vcr >= 75:
        return "FUND_RETURNER"
    elif vcr >= 60:
        return "STRONG_MULTIPLE"
    elif vcr >= 45:
        return "VIABLE_RETURN"
    elif vcr >= 30:
        return "MARGINAL"
    else:
        return "VC_POOR"


# ──────────────────────────────────────────────────────────────────────
# Score a single model
# ──────────────────────────────────────────────────────────────────────

def score_model(model):
    """Score model VCR: check manual override first, then heuristic."""
    mid = model.get("id", "")

    if mid in MANUAL_VCR:
        mkt, cap, eco, vel, moa, rationale = MANUAL_VCR[mid]
    else:
        mkt, cap, eco, vel, moa, rationale = heuristic_vcr(model)

    vcr_comp = calc_vcr_composite(mkt, cap, eco, vel, moa)
    vcr_cat = classify_vcr(vcr_comp)
    roi = estimate_roi_multiple(model, {"MKT": mkt, "CAP": cap, "ECO": eco, "VEL": vel, "MOA": moa})

    return {
        "scores": {"MKT": mkt, "CAP": cap, "ECO": eco, "VEL": vel, "MOA": moa},
        "composite": vcr_comp,
        "category": vcr_cat,
        "roi_estimate": roi,
        "rationale": rationale,
    }


# ──────────────────────────────────────────────────────────────────────
# Build slim model for UI
# ──────────────────────────────────────────────────────────────────────

def build_slim_model(m):
    """Build UI-facing slim model with triple ranking."""
    cla = m.get("cla", {})
    vcr = m.get("vcr", {})
    roi = vcr.get("roi_estimate", {})

    slim = {
        "rank": m["rank"],
        "opportunity_rank": m.get("opportunity_rank"),
        "vcr_rank": m.get("vcr_rank"),
        "id": m["id"],
        "name": m["name"],
        "composite": m["composite"],
        "opportunity_composite": cla.get("composite"),
        "vcr_composite": vcr.get("composite"),
        "vcr_roi_multiple": roi.get("seed_roi_multiple"),
        "vcr_exit_val_M": roi.get("exit_val_M"),
        "category": m.get("primary_category", m["category"][0] if isinstance(m.get("category"), list) and m["category"] else "PARKED"),
        "opportunity_category": cla.get("category"),
        "vcr_category": vcr.get("category"),
        "categories": m["category"] if isinstance(m.get("category"), list) else [m.get("category", "PARKED")],
        "scores": m["scores"],
        "cla_scores": cla.get("scores"),
        "vcr_scores": vcr.get("scores"),
        "sector_naics": m.get("sector_naics"),
        "architecture": m.get("architecture"),
        "source_batch": m.get("source_batch"),
        "new_in_v36": m.get("new_in_v36", False),
        "one_liner": m.get("one_liner"),
    }

    # Decomposition fields
    if m.get("decomposed"):
        slim["decomposed"] = True
        slim["sub_model_count"] = m.get("sub_model_count")
        slim["sub_model_opp_range"] = m.get("sub_model_opp_range")
    if m.get("parent_id"):
        slim["parent_id"] = m["parent_id"]
        slim["layer"] = m.get("layer")
        slim["layer_name"] = m.get("layer_name")
        slim["granularity_type"] = m.get("granularity_type")

    return slim


# ──────────────────────────────────────────────────────────────────────
# Main
# ──────────────────────────────────────────────────────────────────────

def main():
    print("=" * 70)
    print("VCR SCORING: VC ROI Assessment — Third Independent Ranking Dimension")
    print("=" * 70)
    print()

    # Load normalized file
    print("Loading normalized inventory...")
    with open(NORMALIZED_FILE) as f:
        data = json.load(f)
    models = data["models"]
    print(f"  Loaded {len(models)} models")
    print()

    # Score all models
    print("Scoring VCR for all models...")
    manual_count = 0
    heuristic_count = 0

    for model in models:
        vcr = score_model(model)
        model["vcr"] = vcr

        if model["id"] in MANUAL_VCR:
            manual_count += 1
        else:
            heuristic_count += 1

    print(f"  Manual overrides: {manual_count}")
    print(f"  Heuristic scores: {heuristic_count}")
    print()

    # Sort by VCR composite for VCR Rank (descending)
    models_by_vcr = sorted(models, key=lambda m: (-m["vcr"]["composite"], m["id"]))
    for i, m in enumerate(models_by_vcr, 1):
        m["vcr_rank"] = i

    # Re-sort by transformation composite (canonical order) for file
    models.sort(key=lambda m: (-m["composite"], m["id"]))

    # Compute VCR stats
    vcr_composites = [m["vcr"]["composite"] for m in models]
    vcr_stats = {
        "max": max(vcr_composites),
        "min": min(vcr_composites),
        "mean": round(statistics.mean(vcr_composites), 2),
        "median": round(statistics.median(vcr_composites), 2),
    }

    vcr_cat_dist = Counter(m["vcr"]["category"] for m in models)
    vcr_comp_dist = {
        "above_75": sum(1 for c in vcr_composites if c >= 75),
        "60_to_75": sum(1 for c in vcr_composites if 60 <= c < 75),
        "45_to_60": sum(1 for c in vcr_composites if 45 <= c < 60),
        "30_to_45": sum(1 for c in vcr_composites if 30 <= c < 45),
        "below_30": sum(1 for c in vcr_composites if c < 30),
    }

    roi_multiples = [m["vcr"]["roi_estimate"]["seed_roi_multiple"] for m in models]
    roi_stats = {
        "max": max(roi_multiples),
        "min": min(roi_multiples),
        "mean": round(statistics.mean(roi_multiples), 1),
        "median": round(statistics.median(roi_multiples), 1),
        "above_10x": sum(1 for r in roi_multiples if r >= 10),
        "above_20x": sum(1 for r in roi_multiples if r >= 20),
        "above_50x": sum(1 for r in roi_multiples if r >= 50),
    }

    # Add VCR system to rating_system
    data["rating_system"]["vcr_system"] = VCR_SYSTEM

    # Add VCR summary
    data["summary"]["vcr_stats"] = vcr_stats
    data["summary"]["vcr_distribution"] = vcr_comp_dist
    data["summary"]["vcr_category_distribution"] = dict(sorted(vcr_cat_dist.items()))
    data["summary"]["vcr_roi_stats"] = roi_stats

    # Write updated normalized file
    print(f"Writing updated normalized file ({len(models)} models)...")
    with open(NORMALIZED_FILE, "w") as f:
        json.dump(data, f, indent=2, ensure_ascii=False)

    # Write UI models.json
    print("Writing UI models.json...")
    ui_models = [build_slim_model(m) for m in models]
    ui_output = {
        "cycle": data.get("cycle", "v3-11"),
        "date": data.get("date", "2026-02-12"),
        "total": len(models),
        "dual_ranking": True,
        "triple_ranking": True,
        "granularity_layer": True,
        "vcr_system": VCR_SYSTEM,
        "summary": {
            "total_models": len(models),
            "composite_stats": data["summary"].get("composite_stats", {}),
            "primary_category_distribution": data["summary"].get("primary_category_distribution", {}),
            "opportunity_stats": data["summary"].get("opportunity_stats", {}),
            "opportunity_category_distribution": data["summary"].get("opportunity_category_distribution", {}),
            "vcr_stats": vcr_stats,
            "vcr_distribution": vcr_comp_dist,
            "vcr_category_distribution": dict(sorted(vcr_cat_dist.items())),
            "vcr_roi_stats": roi_stats,
        },
        "models": ui_models,
    }
    with open(UI_MODELS, "w") as f:
        json.dump(ui_output, f, indent=2, ensure_ascii=False)

    # Update dashboard.json
    print("Updating dashboard.json...")
    with open(UI_DASHBOARD) as f:
        dashboard = json.load(f)

    dashboard["triple_ranking"] = True
    dashboard["vcr_system"] = VCR_SYSTEM
    dashboard["vcr_stats"] = vcr_stats
    dashboard["vcr_distribution"] = vcr_comp_dist
    dashboard["vcr_category_distribution"] = dict(sorted(vcr_cat_dist.items()))
    dashboard["vcr_roi_stats"] = roi_stats

    # Build top 20 by VCR
    top20_vcr = []
    for m in models_by_vcr[:20]:
        roi = m["vcr"]["roi_estimate"]
        top20_vcr.append({
            "vcr_rank": m["vcr_rank"],
            "transformation_rank": m["rank"],
            "opportunity_rank": m.get("opportunity_rank"),
            "id": m["id"],
            "name": m["name"],
            "composite": m["composite"],
            "opportunity_composite": m.get("cla", {}).get("composite"),
            "vcr_composite": m["vcr"]["composite"],
            "vcr_category": m["vcr"]["category"],
            "seed_roi_multiple": roi["seed_roi_multiple"],
            "exit_val_M": roi["exit_val_M"],
            "architecture": m.get("architecture"),
            "vcr_scores": m["vcr"]["scores"],
        })
    dashboard["top_20_by_vcr_roi"] = top20_vcr

    # Build top 20 "triple actionable" — high on all 3 dimensions
    tri_ranked = sorted(models,
        key=lambda m: -(
            m["composite"] *
            m.get("cla", {}).get("composite", 1) *
            m.get("vcr", {}).get("composite", 1)
        ) ** (1/3))
    top20_tri = []
    for m in tri_ranked[:20]:
        tri_score = round((
            m["composite"] *
            m.get("cla", {}).get("composite", 1) *
            m.get("vcr", {}).get("composite", 1)
        ) ** (1/3), 2)
        top20_tri.append({
            "tri_score": tri_score,
            "transformation_rank": m["rank"],
            "opportunity_rank": m.get("opportunity_rank"),
            "vcr_rank": m.get("vcr_rank"),
            "id": m["id"],
            "name": m["name"],
            "composite": m["composite"],
            "opportunity_composite": m.get("cla", {}).get("composite"),
            "vcr_composite": m.get("vcr", {}).get("composite"),
            "seed_roi_multiple": m.get("vcr", {}).get("roi_estimate", {}).get("seed_roi_multiple"),
        })
    dashboard["top_20_tri_actionable"] = top20_tri

    # Architecture breakdown
    arch_data = {}
    for m in models:
        a = m.get("architecture", "unknown")
        if a not in arch_data:
            arch_data[a] = {"count": 0, "eco_sum": 0, "moa_sum": 0, "roi_sum": 0}
        arch_data[a]["count"] += 1
        arch_data[a]["eco_sum"] += m["vcr"]["scores"]["ECO"]
        arch_data[a]["moa_sum"] += m["vcr"]["scores"]["MOA"]
        arch_data[a]["roi_sum"] += m["vcr"]["roi_estimate"]["seed_roi_multiple"]
    arch_breakdown = []
    for a, d in sorted(arch_data.items(), key=lambda x: -x[1]["roi_sum"]/x[1]["count"]):
        if d["count"] >= 2:  # Only show archs with 2+ models
            arch_breakdown.append({
                "architecture": a,
                "count": d["count"],
                "avg_eco": round(d["eco_sum"] / d["count"], 1),
                "avg_moa": round(d["moa_sum"] / d["count"], 1),
                "avg_roi_multiple": round(d["roi_sum"] / d["count"], 1),
            })
    dashboard["vcr_architecture_breakdown"] = arch_breakdown

    with open(UI_DASHBOARD, "w") as f:
        json.dump(dashboard, f, indent=2, ensure_ascii=False)

    # ── Print Summary ──
    print()
    print("=" * 70)
    print("VCR SCORING COMPLETE — TRIPLE RANKING SYSTEM ACTIVE")
    print("=" * 70)
    print()

    print("  VCR Statistics:")
    print(f"    Max:    {vcr_stats['max']}")
    print(f"    Min:    {vcr_stats['min']}")
    print(f"    Mean:   {vcr_stats['mean']}")
    print(f"    Median: {vcr_stats['median']}")
    print()

    print("  VCR Categories:")
    for cat in ["FUND_RETURNER", "STRONG_MULTIPLE", "VIABLE_RETURN", "MARGINAL", "VC_POOR"]:
        print(f"    {cat:<18s}: {vcr_cat_dist.get(cat, 0)}")
    print()

    print("  ROI Multiple Stats:")
    print(f"    Max:     {roi_stats['max']}x")
    print(f"    Mean:    {roi_stats['mean']}x")
    print(f"    Median:  {roi_stats['median']}x")
    print(f"    Above 10x: {roi_stats['above_10x']}")
    print(f"    Above 20x: {roi_stats['above_20x']}")
    print(f"    Above 50x: {roi_stats['above_50x']}")
    print()

    print("  Top 20 by VC ROI:")
    print(f"  {'VCR#':>4s}  {'T#':>3s}  {'O#':>3s}  {'VCR':>6s}  {'ROI':>7s}  {'Exit$M':>7s}  {'Cat':<18s}  {'Arch':<25s}  Name")
    for m in models_by_vcr[:20]:
        roi = m["vcr"]["roi_estimate"]
        print(f"  {m['vcr_rank']:4d}  {m['rank']:3d}  {m.get('opportunity_rank', 0):3d}  "
              f"{m['vcr']['composite']:6.1f}  {roi['seed_roi_multiple']:6.1f}x  "
              f"${roi['exit_val_M']:6.0f}M  "
              f"{m['vcr']['category']:<18s}  {m.get('architecture', '?'):<25s}  {m['name'][:35]}")
    print()

    print("  Top 20 TRIPLE ACTIONABLE (high on all 3 dimensions):")
    print(f"  {'Tri':>6s}  {'T#':>3s}  {'O#':>3s}  {'V#':>3s}  {'TComp':>6s}  {'OComp':>6s}  {'VCR':>6s}  {'ROI':>6s}  Name")
    for a in top20_tri:
        print(f"  {a['tri_score']:6.2f}  {a['transformation_rank']:3d}  "
              f"{a.get('opportunity_rank', 0):3d}  {a.get('vcr_rank', 0):3d}  "
              f"{a['composite']:6.1f}  {a.get('opportunity_composite', 0):6.1f}  "
              f"{a.get('vcr_composite', 0):6.1f}  "
              f"{a.get('seed_roi_multiple', 0):5.1f}x  {a['name'][:35]}")
    print()

    print("  Architecture ROI Breakdown (2+ models):")
    print(f"  {'Architecture':<28s}  {'Count':>5s}  {'Avg ECO':>7s}  {'Avg MOA':>7s}  {'Avg ROI':>8s}")
    for ab in arch_breakdown[:15]:
        print(f"  {ab['architecture']:<28s}  {ab['count']:5d}  "
              f"{ab['avg_eco']:7.1f}  {ab['avg_moa']:7.1f}  "
              f"{ab['avg_roi_multiple']:7.1f}x")
    print()

    print(f"  Output: {NORMALIZED_FILE}")
    print(f"  UI:     {UI_MODELS}")
    print(f"  Dash:   {UI_DASHBOARD}")


if __name__ == "__main__":
    main()
