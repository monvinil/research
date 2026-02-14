#!/usr/bin/env python3
"""
v5.5 "Agriculture Deep Dive Expansion"

Adds 31 new business models across 8 uncovered agriculture sub-sectors
and 5 missing high-performing architectures. Brings TN-017 Agriculture
from 19 models to 50 — healthy coverage for a MAJOR narrative.

Sub-sectors covered:
  1113 Fruit & Tree Nut (170K workers, 3 models)
  1122 Hog & Pig (45K workers, 2 models)
  1123 Poultry & Egg (65K workers, 2 models)
  1125 Aquaculture (8K workers, 2 models)
  113  Forestry & Logging (55K workers, 3 models)
  114  Fishing/Hunting (28K workers, 1 model)
  115  Ag Support Services (830K workers, 5 models)
  1152 Animal Production Support (95K workers, 2 models)
  + 11 cross-sector models filling architecture gaps

Missing architectures filled:
  open_core_ecosystem (3 models)
  ai_copilot (4 models)
  outcome_based (3 models)
  coordination_protocol (1 model)
  hardware_ai (1 model)
  fear_economy_capture (1 model)

Evidence base: data/verified/v3-13_agriculture_deep_dive_2026-02-12.json
"""

import json
import math
import statistics
from collections import Counter
from copy import deepcopy
from datetime import datetime
from pathlib import Path

BASE = Path("/Users/mv/Documents/research")
V4_DIR = BASE / "data" / "v4"
V5_DIR = BASE / "data" / "v5"

MODELS_FILE = V4_DIR / "models.json"
NARRATIVES_FILE = V4_DIR / "narratives.json"
STATE_FILE = V5_DIR / "state.json"

T_WEIGHTS = {"SN": 25, "FA": 25, "EC": 20, "TG": 15, "CE": 15}
CLA_WEIGHTS = {"MO": 30, "MA": 25, "VD": 20, "DV": 25}
VCR_WEIGHTS = {"MKT": 25, "CAP": 25, "ECO": 20, "VEL": 15, "MOA": 15}

NAICS_NAMES = {
    "1113": "Fruit and Tree Nut Farming",
    "1122": "Hog and Pig Farming",
    "1123": "Poultry and Egg Production",
    "1125": "Aquaculture",
    "113": "Forestry and Logging",
    "114": "Fishing, Hunting and Trapping",
    "115": "Support Activities for Agriculture and Forestry",
    "1151": "Support Activities for Crop Production",
    "1152": "Support Activities for Animal Production",
    "1111": "Oilseed and Grain Farming",
    "1112": "Vegetable and Melon Farming",
    "1114": "Greenhouse, Nursery, and Floriculture Production",
    "1119": "Other Crop Farming",
    "1121": "Cattle Ranching and Farming",
    "11": "Agriculture, Forestry, Fishing and Hunting",
}


def compute_t(s):
    return sum(s[a] * T_WEIGHTS[a] for a in T_WEIGHTS) / 10.0

def compute_cla(s):
    return sum(s[a] * CLA_WEIGHTS[a] for a in CLA_WEIGHTS) / 10.0

def compute_vcr(s):
    return sum(s[a] * VCR_WEIGHTS[a] for a in VCR_WEIGHTS) / 10.0

def t_cat(c):
    if c >= 80: return "DEFINING"
    if c >= 65: return "MAJOR"
    if c >= 50: return "MODERATE"
    if c >= 35: return "EMERGING"
    return "SPECULATIVE"

def cla_cat(c):
    if c >= 75: return "WIDE_OPEN"
    if c >= 60: return "ACCESSIBLE"
    if c >= 45: return "CONTESTED"
    if c >= 30: return "FORTIFIED"
    return "LOCKED"

def vcr_cat(c):
    if c >= 75: return "FUND_RETURNER"
    if c >= 60: return "STRONG_MULTIPLE"
    if c >= 45: return "VIABLE_RETURN"
    if c >= 30: return "MARGINAL"
    return "VC_POOR"

def geo_mean(t, o, v):
    return (t * o * v) ** (1.0 / 3.0)


# ══════════════════════════════════════════════════════════════════════
# 31 NEW AGRICULTURE MODELS
# ══════════════════════════════════════════════════════════════════════

NEW_MODELS = [
    # ── NAICS 1113: Fruit & Tree Nut Farming (170K workers) ──
    {
        "id": "MC-V55-1113-001",
        "name": "Orchard Harvest Robotics Platform",
        "one_liner": "Autonomous apple/citrus picking robots with computer vision "
                     "for ripeness detection — targeting the $12B US fruit harvest "
                     "where 65% of costs are manual labor and H-2A shortages "
                     "leave 10-20% of crops unpicked annually",
        "architecture": "robotics_automation",
        "sector_naics": "1113",
        "scores": {"SN": 8.0, "FA": 7.0, "EC": 6.0, "TG": 6.0, "CE": 5.5},
        "cla": {
            "scores": {"MO": 7, "MA": 7, "VD": 5, "DV": 7},
            "rationale": "Nascent market — Abundant Robotics (failed), FFRobotics, "
                "Tevel (Israeli drone picker). No dominant player. Hardware moat "
                "is moderate. Fruit variety-specific picking heads needed. "
                "Apple/citrus first, then stone fruit. H-2A labor crisis ($16.56/hr "
                "average adverse effect wage) creates pull demand."
        },
        "vcr": {
            "scores": {"MKT": 6.5, "CAP": 4.5, "ECO": 5.0, "VEL": 4.0, "MOA": 6.0},
            "rationale": "TAM $2-4B (fruit harvest labor replacement). Hardware-heavy "
                "= lower margins (40-55%). Long sales cycle (growers buy pre-season). "
                "Capital intensive ($200K+ per unit). Strong moat from orchard-specific "
                "training data. Payback 2-3 seasons per unit."
        },
        "forces_v3": ["F1_technology", "F2_demographics"],
        "primary_category": "STRUCTURAL_WINNER",
    },
    {
        "id": "MC-V55-1113-002",
        "name": "Tree Crop Health & Yield Prediction Platform",
        "one_liner": "Satellite + drone multispectral imaging platform that detects "
                     "citrus greening, fire blight, and nutrient deficiencies in "
                     "orchards/vineyards — predicting yield 60-90 days pre-harvest "
                     "with 85%+ accuracy for crop insurance and forward contracts",
        "architecture": "data_compounding",
        "sector_naics": "1113",
        "scores": {"SN": 7.5, "FA": 7.0, "EC": 6.5, "TG": 7.0, "CE": 7.0},
        "cla": {
            "scores": {"MO": 7, "MA": 7, "VD": 6, "DV": 7},
            "rationale": "Aerobotics (South Africa, $27M raised), Agworld, Semios "
                "compete but no dominant tree-crop specialist at US scale. Data "
                "compounding moat: 5+ years of spectral-to-yield correlation per "
                "orchard block. Crop insurance integration creates recurring revenue. "
                "Citrus greening detection alone saves $2,000-5,000/acre in "
                "replanting costs."
        },
        "vcr": {
            "scores": {"MKT": 6.0, "CAP": 7.0, "ECO": 7.0, "VEL": 6.5, "MOA": 7.0},
            "rationale": "TAM $1-2B (tree crop monitoring + crop insurance analytics). "
                "Software margins 75%+. 6-month sales cycle (winter decisions). "
                "Strong data moat from multi-year spectral-yield correlations. "
                "Revenue per farm: $5-15/acre on 500K+ bearing acres."
        },
        "forces_v3": ["F1_technology", "F6_energy"],
        "primary_category": "FORCE_RIDER",
    },
    {
        "id": "MC-V55-1113-003",
        "name": "Specialty Crop Packing & Cold Chain SaaS",
        "one_liner": "Vertical SaaS for fruit/vegetable packing houses and cold "
                     "storage — AI-powered grading, inventory optimization, and "
                     "FSMA 204 traceability compliance for the 4,800 US produce "
                     "packing operations",
        "architecture": "vertical_saas",
        "sector_naics": "1113",
        "scores": {"SN": 7.0, "FA": 6.5, "EC": 7.0, "TG": 7.5, "CE": 7.0},
        "cla": {
            "scores": {"MO": 8, "MA": 8, "VD": 6, "DV": 7},
            "rationale": "Highly fragmented: 4,800 packing houses, mostly using "
                "paper/spreadsheet grading. FSMA 204 compliance deadline creates "
                "regulatory urgency. No dominant SaaS player. Compac/TOMRA do "
                "hardware sorting but not full workflow SaaS. Strong regulatory "
                "pull from traceability requirements."
        },
        "vcr": {
            "scores": {"MKT": 5.5, "CAP": 7.5, "ECO": 7.5, "VEL": 7.5, "MOA": 6.5},
            "rationale": "TAM $500M-1B (packing house SaaS + cold chain). SaaS "
                "margins 80%+. Regulatory urgency compresses sales cycle to 3-6 "
                "months. $10-30K ACV per packing operation. FSMA 204 compliance "
                "= mandatory spend, not discretionary."
        },
        "forces_v3": ["F1_technology", "F3_geopolitics"],
        "primary_category": "TIMING_ARBITRAGE",
    },

    # ── NAICS 1122: Hog & Pig Farming (45K workers) ──
    {
        "id": "MC-V55-1122-001",
        "name": "Swine Production AI Copilot",
        "one_liner": "AI assistant for swine farm managers integrating feed "
                     "conversion, growth modeling, disease early-warning, and "
                     "market timing — copiloting decisions for the 60K US hog "
                     "operations producing 130M+ pigs annually",
        "architecture": "ai_copilot",
        "sector_naics": "1122",
        "scores": {"SN": 7.0, "FA": 6.5, "EC": 6.5, "TG": 6.5, "CE": 6.5},
        "cla": {
            "scores": {"MO": 5, "MA": 5, "VD": 5, "DV": 6},
            "rationale": "Extreme consolidation: top 20 producers control 50%+ "
                "of production. Smithfield (1.1M sows) and Tyson build proprietary "
                "tools. But 40K+ smaller operations (100-5,000 sows) need AI "
                "tools they can't build internally. Contract grower model means "
                "integrators may mandate tools. MO limited by consolidation."
        },
        "vcr": {
            "scores": {"MKT": 5.0, "CAP": 6.0, "ECO": 6.0, "VEL": 6.0, "MOA": 5.5},
            "rationale": "TAM $300-600M (swine management software). Feed is 65% "
                "of cost — 1% optimization = $3-5/pig × 130M pigs. B2B sales to "
                "mid-size integrators. 6-month adoption. Moderate margins (70%). "
                "Data moat from production outcome correlation."
        },
        "forces_v3": ["F1_technology", "F2_demographics"],
        "primary_category": "CONDITIONAL",
    },
    {
        "id": "MC-V55-1122-002",
        "name": "Swine Waste & Environmental Compliance Platform",
        "one_liner": "Compliance automation for hog farm nutrient management "
                     "plans, waste lagoon monitoring, and EPA methane reporting — "
                     "addressing tightening environmental regulations for the "
                     "65,000+ US confined swine operations",
        "architecture": "compliance_automation",
        "sector_naics": "1122",
        "scores": {"SN": 7.5, "FA": 7.0, "EC": 6.0, "TG": 7.0, "CE": 6.0},
        "cla": {
            "scores": {"MO": 7, "MA": 7, "VD": 5, "DV": 7},
            "rationale": "No dominant compliance platform for swine waste. State-by- "
                "state regulations create fragmented compliance burden. IoT sensors "
                "for lagoon levels + AI for nutrient management plans. EPA methane "
                "rule (2024) creates new reporting requirements. NC, IA, MN have "
                "strictest swine waste regulations."
        },
        "vcr": {
            "scores": {"MKT": 4.5, "CAP": 7.0, "ECO": 6.5, "VEL": 6.5, "MOA": 7.0},
            "rationale": "TAM $200-400M (swine environmental compliance). Regulatory "
                "moat once certified. SaaS margins 75%+. Compliance = non-discretionary "
                "spend. $5-15K ACV per operation. Regulatory complexity creates "
                "switching costs."
        },
        "forces_v3": ["F1_technology", "F6_energy"],
        "primary_category": "FORCE_RIDER",
    },

    # ── NAICS 1123: Poultry & Egg Production (65K workers) ──
    {
        "id": "MC-V55-1123-001",
        "name": "Poultry House Automation & Performance SaaS",
        "one_liner": "Vertical SaaS integrating ventilation control, feed/water "
                     "monitoring, mortality detection, and flock performance "
                     "analytics for 25,000+ US contract poultry growers — "
                     "turning houses from manual to autonomous",
        "architecture": "vertical_saas",
        "sector_naics": "1123",
        "scores": {"SN": 7.5, "FA": 7.0, "EC": 7.0, "TG": 7.0, "CE": 7.0},
        "cla": {
            "scores": {"MO": 6, "MA": 6, "VD": 6, "DV": 7},
            "rationale": "Integrators (Tyson, Pilgrim's Pride, Perdue) mandate "
                "performance standards but don't provide management software to "
                "contract growers. Cumberland, Chore-Time sell hardware controls "
                "but not AI analytics. 25K+ contract growers are underserved. "
                "Cage-free transition (Prop 12) creating retrofit urgency."
        },
        "vcr": {
            "scores": {"MKT": 5.5, "CAP": 7.0, "ECO": 7.0, "VEL": 7.0, "MOA": 6.5},
            "rationale": "TAM $400-800M (poultry house management). SaaS margins "
                "80%+. Contract grower settlement data integration creates stickiness. "
                "$3-8K ACV per house, 4-8 houses per grower = $12-64K ACV. "
                "Integrator partnerships for distribution."
        },
        "forces_v3": ["F1_technology", "F2_demographics"],
        "primary_category": "FORCE_RIDER",
    },
    {
        "id": "MC-V55-1123-002",
        "name": "Contract Grower Performance & Settlement Platform",
        "one_liner": "Outcome-based platform that transparently tracks poultry "
                     "contract grower performance vs. settlement payments — "
                     "bridging the information asymmetry between 25K growers and "
                     "4 dominant integrators",
        "architecture": "outcome_based",
        "sector_naics": "1123",
        "scores": {"SN": 6.5, "FA": 7.5, "EC": 6.0, "TG": 6.0, "CE": 6.0},
        "cla": {
            "scores": {"MO": 7, "MA": 8, "VD": 5, "DV": 7},
            "rationale": "No independent performance analytics for contract growers. "
                "Integrators control the data. 25K growers with minimal negotiating "
                "power need independent benchmarking. Outcome-based model: growers "
                "pay % of settlement improvement. USDA Packers & Stockyards division "
                "increasingly scrutinizing contract fairness."
        },
        "vcr": {
            "scores": {"MKT": 4.0, "CAP": 6.5, "ECO": 6.0, "VEL": 5.5, "MOA": 7.0},
            "rationale": "TAM $150-300M (contract grower analytics + advocacy). "
                "Outcome-based revenue model: 5-10% of settlement improvement. "
                "Average grower settles $150-250K/year, 5% improvement = $7.5-12.5K "
                "value. Software margins high but adoption requires trust-building."
        },
        "forces_v3": ["F1_technology", "F5_psychology"],
        "primary_category": "FEAR_ECONOMY",
    },

    # ── NAICS 1125: Aquaculture (8K workers, growing) ──
    {
        "id": "MC-V55-1125-001",
        "name": "Aquaculture Feed & Health Monitoring System",
        "one_liner": "Underwater camera + sensor platform for fish feeding "
                     "optimization, sea lice detection, and biomass estimation — "
                     "targeting the $280B global aquaculture industry where feed "
                     "is 50-70% of production cost",
        "architecture": "physical_production_ai",
        "sector_naics": "1125",
        "scores": {"SN": 7.5, "FA": 6.5, "EC": 6.5, "TG": 6.5, "CE": 6.0},
        "cla": {
            "scores": {"MO": 7, "MA": 7, "VD": 6, "DV": 7},
            "rationale": "Observe Technologies ($12M raised), Aquabyte (acquired by "
                "InnovaSea), XpertSea ($25M raised) compete but market is early. "
                "Feed optimization alone saves 10-15% ($0.15-0.25/kg fish). "
                "Norwegian salmon producers (Mowi, SalMar) are early adopters. "
                "US RAS facilities growing rapidly."
        },
        "vcr": {
            "scores": {"MKT": 7.0, "CAP": 5.5, "ECO": 6.0, "VEL": 5.5, "MOA": 7.0},
            "rationale": "TAM $3-6B (global aquaculture monitoring + feed optimization). "
                "Hardware+software margins 50-60%. Long sales cycle (6-12 months). "
                "Strong data moat from species-specific feeding patterns. "
                "$50-200K per facility. Global market favors multi-geography approach."
        },
        "forces_v3": ["F1_technology", "F6_energy"],
        "primary_category": "FORCE_RIDER",
    },
    {
        "id": "MC-V55-1125-002",
        "name": "Recirculating Aquaculture Systems (RAS) Control Platform",
        "one_liner": "Vertical SaaS for indoor fish farm operations — water "
                     "quality management, biofilter optimization, and production "
                     "planning for the emerging $2B+ RAS facility market bringing "
                     "fish farming inland and urban",
        "architecture": "vertical_saas",
        "sector_naics": "1125",
        "scores": {"SN": 7.0, "FA": 6.0, "EC": 6.0, "TG": 6.0, "CE": 5.5},
        "cla": {
            "scores": {"MO": 8, "MA": 8, "VD": 6, "DV": 7},
            "rationale": "RAS is emerging category — no dominant software platform. "
                "AquaMaof, Innovasea sell hardware+consulting but not SaaS. "
                "250+ RAS facilities under construction globally. Water chemistry "
                "management is complex (pH, ammonia, nitrite, dissolved O2). "
                "AI can optimize biofilter performance and predict system failures."
        },
        "vcr": {
            "scores": {"MKT": 5.0, "CAP": 6.5, "ECO": 6.0, "VEL": 5.0, "MOA": 7.0},
            "rationale": "TAM $500M-1B (RAS operations software). SaaS margins 75%+. "
                "Long sales cycle (facility design phase). $20-50K ACV per facility. "
                "Strong moat from species-specific water chemistry models. "
                "Small current market but growing rapidly as ocean farming faces limits."
        },
        "forces_v3": ["F1_technology", "F6_energy"],
        "primary_category": "EMERGING_CATEGORY",
    },

    # ── NAICS 113: Forestry & Logging (55K workers) ──
    {
        "id": "MC-V55-113-001",
        "name": "Forest Carbon Inventory & Credit Verification Platform",
        "one_liner": "Satellite LiDAR + AI platform for forest carbon stock "
                     "measurement, additionality verification, and credit "
                     "issuance — replacing $5,000-50,000 manual forest inventories "
                     "with $500-2,000 remote sensing assessments at 95% accuracy",
        "architecture": "data_compounding",
        "sector_naics": "113",
        "scores": {"SN": 8.0, "FA": 7.5, "EC": 6.5, "TG": 7.0, "CE": 7.0},
        "cla": {
            "scores": {"MO": 7, "MA": 7, "VD": 7, "DV": 8},
            "rationale": "Pachama ($79M raised), NCX, Sylvera compete but market "
                "is early and growing rapidly. Voluntary forest carbon market: "
                "$1-3B and growing. Integrity concerns (Verra controversy 2023) "
                "create demand for satellite-verified credits. Data moat from "
                "multi-year forest growth models. Multi-layer: measurement, "
                "verification, credit issuance, trading."
        },
        "vcr": {
            "scores": {"MKT": 7.0, "CAP": 7.0, "ECO": 7.5, "VEL": 6.0, "MOA": 7.5},
            "rationale": "TAM $5-15B (forest carbon verification + trading). Software "
                "margins 80%+. Project sales 6-12 months. Strong data moat from "
                "forest growth models calibrated over years. $5-30/acre/year "
                "verification revenue on 1B+ acres of managed US timberland."
        },
        "forces_v3": ["F1_technology", "F6_energy", "F3_geopolitics"],
        "primary_category": "STRUCTURAL_WINNER",
    },
    {
        "id": "MC-V55-113-002",
        "name": "Autonomous Timber Harvesting System",
        "one_liner": "GPS-guided autonomous feller-buncher and forwarder system "
                     "with AI-driven selective harvesting — reducing logging "
                     "crew size from 4-6 to 1-2 operators while improving yield "
                     "recovery 15-20% through optimal tree selection",
        "architecture": "robotics_automation",
        "sector_naics": "113",
        "scores": {"SN": 7.0, "FA": 6.5, "EC": 5.5, "TG": 5.5, "CE": 5.0},
        "cla": {
            "scores": {"MO": 6, "MA": 6, "VD": 4, "DV": 6},
            "rationale": "Logging equipment dominated by Deere, Caterpillar, Komatsu, "
                "Ponsse. Autonomy retrofits possible but OEM integration required. "
                "Selective harvesting AI is the software wedge. Terrain complexity "
                "(slopes, debris) makes full autonomy harder than field crops. "
                "Labor shortage acute — average logger age 52, highest fatality "
                "rate of any US occupation."
        },
        "vcr": {
            "scores": {"MKT": 4.5, "CAP": 4.0, "ECO": 4.5, "VEL": 3.5, "MOA": 5.5},
            "rationale": "TAM $1-2B (logging automation). Hardware-heavy = low margins "
                "(35-45%). 12-month+ sales cycle. Capital intensive ($500K+ per unit). "
                "Moderate moat from terrain-specific models. Small US market limits "
                "scale. Nordic countries (Ponsse, Komatsu Forest) are further ahead."
        },
        "forces_v3": ["F1_technology", "F2_demographics"],
        "primary_category": "CONDITIONAL",
    },
    {
        "id": "MC-V55-113-003",
        "name": "Wildfire Risk Assessment & Forest Management Service",
        "one_liner": "AI-powered wildfire risk modeling, fuel load assessment, and "
                     "prescribed burn planning service for the 350M acres of US "
                     "national forests and 10M+ private timberland owners facing "
                     "escalating fire risk",
        "architecture": "service_platform",
        "sector_naics": "113",
        "scores": {"SN": 8.0, "FA": 7.0, "EC": 6.0, "TG": 7.0, "CE": 6.5},
        "cla": {
            "scores": {"MO": 7, "MA": 7, "VD": 6, "DV": 8},
            "rationale": "USFS spends $4B+/year on fire suppression but only $500M "
                "on prevention. Private landowner market is fragmented and underserved. "
                "Insurance companies increasingly requiring fire risk assessments. "
                "Satellite + weather + fuel load AI models outperform manual assessments. "
                "No dominant private-sector wildfire analytics platform."
        },
        "vcr": {
            "scores": {"MKT": 6.0, "CAP": 6.5, "ECO": 6.5, "VEL": 5.5, "MOA": 7.0},
            "rationale": "TAM $2-4B (wildfire risk assessment + forest management). "
                "Service margins 60-70%. Government sales are slow (12-18 months) "
                "but insurance channel is faster. Strong data moat from historical "
                "fire-fuel correlations. Climate change makes this structurally "
                "necessary — demand only grows."
        },
        "forces_v3": ["F1_technology", "F6_energy", "F5_psychology"],
        "primary_category": "STRUCTURAL_WINNER",
    },

    # ── NAICS 114: Fishing/Hunting/Trapping (28K workers) ──
    {
        "id": "MC-V55-114-001",
        "name": "AI Fisheries Stock Assessment & Bycatch Reduction",
        "one_liner": "Computer vision + acoustic monitoring platform for commercial "
                     "fishing fleets — real-time species identification, bycatch "
                     "avoidance, and catch documentation for regulatory compliance "
                     "across $5.6B US commercial fishing",
        "architecture": "data_compounding",
        "sector_naics": "114",
        "scores": {"SN": 7.0, "FA": 6.5, "EC": 5.5, "TG": 6.0, "CE": 5.5},
        "cla": {
            "scores": {"MO": 7, "MA": 7, "VD": 5, "DV": 7},
            "rationale": "NOAA mandates electronic monitoring on many fleets but "
                "no dominant AI analytics platform. EM (electronic monitoring) "
                "hardware is commoditizing. AI species ID + bycatch prediction "
                "is the value layer. Fishing quota management creates regulatory "
                "pull. Small total market but high per-vessel value."
        },
        "vcr": {
            "scores": {"MKT": 3.5, "CAP": 6.0, "ECO": 6.0, "VEL": 5.0, "MOA": 7.0},
            "rationale": "TAM $300-600M (fisheries monitoring + analytics). Software "
                "margins 70%+. Regulatory sales cycle (NOAA partnership needed). "
                "$10-30K/vessel/year. Strong data moat from species/location "
                "correlations. Small US market limits VC scale."
        },
        "forces_v3": ["F1_technology", "F3_geopolitics"],
        "primary_category": "CONDITIONAL",
    },

    # ── NAICS 115: Support Activities for Agriculture (830K workers!) ──
    {
        "id": "MC-V55-115-001",
        "name": "Open-Source Farm Data Operating System",
        "one_liner": "Open-core farm data platform — a Linux for agriculture — "
                     "that aggregates equipment data (ISO 11783/ISOBUS), field "
                     "records, and agronomic decisions into a farmer-owned data "
                     "layer with open APIs, breaking vendor lock-in from Deere/"
                     "CNH/AGCO proprietary ecosystems",
        "architecture": "open_core_ecosystem",
        "sector_naics": "115",
        "scores": {"SN": 8.5, "FA": 8.0, "EC": 7.0, "TG": 7.0, "CE": 7.0},
        "cla": {
            "scores": {"MO": 8, "MA": 9, "VD": 8, "DV": 9},
            "rationale": "RIGHT-TO-REPAIR meets OPEN DATA. No open-source farm data "
                "OS exists despite clear demand (72% of farmers concerned about "
                "data ownership). OpenAg Data Alliance died; AgGateway is standards "
                "body not software. Deep value chain: data ingestion, field records, "
                "APIs, analytics, sharing. Open-source wedge + enterprise features "
                "monetization. 7 states passed right-to-repair for ag equipment."
        },
        "vcr": {
            "scores": {"MKT": 7.5, "CAP": 7.5, "ECO": 7.0, "VEL": 7.0, "MOA": 8.0},
            "rationale": "TAM $5-10B (farm data management + integrations). Open-core "
                "PLG, developer adoption in 3-6 months. 80%+ margins on enterprise "
                "features. Data sovereignty moat — farmers WANT to own their data. "
                "Network effects from ecosystem of third-party apps. "
                "Analogous to Linux/Red Hat for farming."
        },
        "forces_v3": ["F1_technology", "F5_psychology"],
        "primary_category": "STRUCTURAL_WINNER",
    },
    {
        "id": "MC-V55-115-002",
        "name": "Agronomist AI Copilot for Crop Consulting",
        "one_liner": "AI copilot for the 14,000 US certified crop advisors — "
                     "generating field-specific recommendations from soil tests, "
                     "satellite imagery, and historical yield data, increasing "
                     "consultant productivity 3-5x while improving recommendation "
                     "accuracy",
        "architecture": "ai_copilot",
        "sector_naics": "115",
        "scores": {"SN": 8.0, "FA": 7.5, "EC": 7.5, "TG": 8.0, "CE": 7.5},
        "cla": {
            "scores": {"MO": 8, "MA": 8, "VD": 6, "DV": 8},
            "rationale": "14K certified crop advisors (CCAs) each manage 20-50 "
                "farms. AI copilot doesn't replace advisors — it augments them "
                "(Jevons: more recommendations per advisor = more acres served). "
                "No AI CCA copilot exists at scale. Agworld, Ag Leader have "
                "record-keeping but not AI recommendations. Trust channel: "
                "farmer trusts their CCA, CCA trusts the AI tool."
        },
        "vcr": {
            "scores": {"MKT": 6.0, "CAP": 8.0, "ECO": 8.0, "VEL": 8.0, "MOA": 6.5},
            "rationale": "TAM $1-2B (crop consulting software + AI). Pure software "
                "85%+ margins. Fast adoption via CCA channel (3-6 months). "
                "$2-5K/CCA/year or $0.50-1.50/acre. PLG through free trial "
                "with CCA network. Moderate moat — AI model quality differentiates."
        },
        "forces_v3": ["F1_technology", "F2_demographics"],
        "primary_category": "FORCE_RIDER",
    },
    {
        "id": "MC-V55-115-003",
        "name": "Precision Ag Service Provider Platform",
        "one_liner": "Platform infrastructure for precision ag service companies — "
                     "job scheduling, variable-rate application logging, fleet GPS "
                     "tracking, and farmer reporting for the 5,000+ custom "
                     "applicators and precision ag dealers serving 200M+ acres",
        "architecture": "platform_infrastructure",
        "sector_naics": "115",
        "scores": {"SN": 7.5, "FA": 7.0, "EC": 7.0, "TG": 7.5, "CE": 7.5},
        "cla": {
            "scores": {"MO": 8, "MA": 7, "VD": 6, "DV": 7},
            "rationale": "Custom applicators are highly fragmented (5K+ operators). "
                "Most use paper or basic GPS. No dominant SaaS for precision ag "
                "service businesses. Granular/Bushel acquired by Corteva but "
                "focused on farmer-side not service provider-side. Regulatory "
                "record-keeping for pesticide application creates compliance pull."
        },
        "vcr": {
            "scores": {"MKT": 5.0, "CAP": 7.5, "ECO": 7.5, "VEL": 7.5, "MOA": 6.5},
            "rationale": "TAM $500M-1B (ag service provider software). SaaS margins "
                "80%+. 3-6 month sales cycle. $5-15K ACV per operator. Strong "
                "retention from operational dependency. Network effects if farmers "
                "and applicators share data through platform."
        },
        "forces_v3": ["F1_technology", "F2_demographics"],
        "primary_category": "FORCE_RIDER",
    },
    {
        "id": "MC-V55-115-004",
        "name": "Custom Harvesting & Ag Services Marketplace",
        "one_liner": "Two-sided marketplace connecting farmers needing harvest, "
                     "spraying, or tillage services with equipment operators — "
                     "the Uber for combines, targeting $15B+ in custom farming "
                     "services where 40% of US crops are custom-harvested",
        "architecture": "marketplace_network",
        "sector_naics": "115",
        "scores": {"SN": 7.0, "FA": 6.5, "EC": 6.5, "TG": 6.5, "CE": 6.0},
        "cla": {
            "scores": {"MO": 8, "MA": 8, "VD": 5, "DV": 7},
            "rationale": "Currently word-of-mouth and local relationships. No "
                "dominant platform. Harvest timing is critical (1-2 week windows). "
                "Custom combiners run north-to-south following harvest. "
                "Marketplace eliminates geographic information asymmetry. "
                "Equipment utilization is low (combines used 30-60 days/year)."
        },
        "vcr": {
            "scores": {"MKT": 6.0, "CAP": 6.0, "ECO": 5.5, "VEL": 5.5, "MOA": 6.0},
            "rationale": "TAM $2-3B (custom harvesting marketplace + adjacent services). "
                "Platform margins 15-25% (marketplace take rate 5-10%). Seasonal "
                "demand concentration. Network effects from farmer/operator matching "
                "but requires geographic density. Chicken-and-egg supply challenge."
        },
        "forces_v3": ["F1_technology", "F2_demographics"],
        "primary_category": "TIMING_ARBITRAGE",
    },
    {
        "id": "MC-V55-115-005",
        "name": "AI Soil Testing & Lab Analytics Service",
        "one_liner": "AI-powered soil testing service combining rapid in-field "
                     "spectroscopy with lab analysis — cutting turnaround from "
                     "2-3 weeks to 48 hours and cost from $25-50/sample to $8-15, "
                     "enabling 10x denser sampling grids for precision application",
        "architecture": "service_platform",
        "sector_naics": "115",
        "scores": {"SN": 7.5, "FA": 7.0, "EC": 7.0, "TG": 7.5, "CE": 7.5},
        "cla": {
            "scores": {"MO": 7, "MA": 7, "VD": 5, "DV": 7},
            "rationale": "Traditional soil testing labs are slow and expensive. "
                "NIR spectroscopy + AI can predict macronutrients (N, P, K) in "
                "minutes. AgriNIR, Veris Technologies, TerrAvion compete in pieces. "
                "No end-to-end rapid soil testing + prescription service. "
                "2.5x grid density = 2.5x revenue per field."
        },
        "vcr": {
            "scores": {"MKT": 5.5, "CAP": 7.0, "ECO": 7.0, "VEL": 7.5, "MOA": 6.0},
            "rationale": "TAM $1-2B (soil testing + analytics). Service margins 60-70% "
                "(lab costs + field ops). Fast revenue: per-sample pricing. Seasonal "
                "concentration (fall/spring sampling windows). Moderate moat from "
                "calibration library (spectral→nutrient models)."
        },
        "forces_v3": ["F1_technology", "F6_energy"],
        "primary_category": "FORCE_RIDER",
    },

    # ── NAICS 1152: Support for Animal Production (95K workers) ──
    {
        "id": "MC-V55-1152-001",
        "name": "Veterinary AI Diagnostic Copilot",
        "one_liner": "AI copilot for large-animal veterinarians — image-based "
                     "lameness scoring, ultrasound interpretation, and treatment "
                     "protocol recommendations for the 15,000 US food-animal vets "
                     "facing a 15% workforce shortage",
        "architecture": "ai_copilot",
        "sector_naics": "1152",
        "scores": {"SN": 7.5, "FA": 7.5, "EC": 6.5, "TG": 7.0, "CE": 6.5},
        "cla": {
            "scores": {"MO": 8, "MA": 8, "VD": 6, "DV": 8},
            "rationale": "Food-animal vet shortage is acute: 15% unfilled positions, "
                "worsening as new grads prefer companion animal practice. AI copilot "
                "extends each vet's capacity (Jevons). No large-animal AI diagnostic "
                "tool exists at scale. USDA accreditation requirements for disease "
                "surveillance create regulatory channel. Trust via vet schools."
        },
        "vcr": {
            "scores": {"MKT": 5.0, "CAP": 7.0, "ECO": 7.0, "VEL": 6.5, "MOA": 7.0},
            "rationale": "TAM $500M-1B (vet diagnostic software + decision support). "
                "Software margins 80%+. 6-month adoption through vet school channel. "
                "$5-15K/vet/year. Data moat from case outcome correlations. "
                "Small market but defensible niche."
        },
        "forces_v3": ["F1_technology", "F2_demographics"],
        "primary_category": "FORCE_RIDER",
    },
    {
        "id": "MC-V55-1152-002",
        "name": "Livestock Genetics & Breeding Management Platform",
        "one_liner": "Vertical SaaS for livestock breeding operations — genomic "
                     "selection, mating planning, EPD (expected progeny difference) "
                     "management, and pedigree tracking for beef cattle, dairy, "
                     "and swine genetics companies",
        "architecture": "vertical_saas",
        "sector_naics": "1152",
        "scores": {"SN": 7.0, "FA": 6.5, "EC": 6.5, "TG": 6.5, "CE": 6.5},
        "cla": {
            "scores": {"MO": 7, "MA": 6, "VD": 6, "DV": 6},
            "rationale": "Neogen ($600M+ revenue) dominates genomic testing but not "
                "breeding management software. DHIA (dairy herd improvement) is "
                "cooperative-owned legacy system. Beef breed registries (Angus, "
                "Hereford) each have proprietary databases. Platform that unifies "
                "across breeds/species fills a real gap."
        },
        "vcr": {
            "scores": {"MKT": 4.5, "CAP": 6.5, "ECO": 6.5, "VEL": 5.5, "MOA": 6.5},
            "rationale": "TAM $300-600M (livestock genetics software). SaaS margins "
                "75%+. 6-12 month sales cycle (seedstock operations). $5-20K ACV "
                "per operation. Data moat from genomic-performance correlations. "
                "Small but sticky niche."
        },
        "forces_v3": ["F1_technology", "F2_demographics"],
        "primary_category": "CONDITIONAL",
    },

    # ── Cross-sector: Missing architectures ──
    {
        "id": "MC-V55-1111-001",
        "name": "Open-Source Crop Modeling & Decision Framework",
        "one_liner": "Open-core crop growth simulation platform — integrating "
                     "DSSAT, APSIM, and WOFOST crop models into a modern API "
                     "with ML-enhanced calibration, enabling precision ag companies "
                     "and researchers to build on a shared modeling layer",
        "architecture": "open_core_ecosystem",
        "sector_naics": "1111",
        "scores": {"SN": 7.5, "FA": 7.0, "EC": 6.5, "TG": 6.5, "CE": 7.0},
        "cla": {
            "scores": {"MO": 8, "MA": 8, "VD": 7, "DV": 8},
            "rationale": "DSSAT, APSIM are open-source academic crop models but "
                "unusable by commercial developers (FORTRAN, no APIs, poor docs). "
                "Modern API wrapper with ML calibration fills massive gap. "
                "Developer ecosystem builds on platform. No commercial equivalent. "
                "Crop modeling is foundation of all precision ag — whoever owns "
                "the modeling layer captures ecosystem value."
        },
        "vcr": {
            "scores": {"MKT": 6.0, "CAP": 7.5, "ECO": 7.5, "VEL": 6.0, "MOA": 8.0},
            "rationale": "TAM $2-4B (crop modeling infrastructure for precision ag). "
                "Open-core with enterprise licensing. 80%+ margins. Developer adoption "
                "in 3-6 months. Very strong ecosystem moat once third-party apps "
                "build on the platform. Analogous to Hugging Face for agriculture."
        },
        "forces_v3": ["F1_technology"],
        "primary_category": "STRUCTURAL_WINNER",
    },
    {
        "id": "MC-V55-1111-002",
        "name": "Per-Bushel Yield Guarantee Platform",
        "one_liner": "Outcome-based precision ag platform that guarantees yield "
                     "improvement or farmers don't pay — aligning agronomic "
                     "recommendations with economic outcomes, pricing per bushel "
                     "of yield improvement rather than per acre subscription",
        "architecture": "outcome_based",
        "sector_naics": "1111",
        "scores": {"SN": 7.5, "FA": 8.0, "EC": 6.5, "TG": 6.5, "CE": 6.0},
        "cla": {
            "scores": {"MO": 7, "MA": 8, "VD": 5, "DV": 8},
            "rationale": "NO precision ag company offers outcome guarantees. Current "
                "model: farmers pay subscription regardless of results. Outcome-based "
                "pricing breaks the trust barrier (72% farmer data distrust). "
                "Requires enough yield-data correlation to underwrite the guarantee. "
                "Revenue per acre higher if recommendations work, zero if they don't."
        },
        "vcr": {
            "scores": {"MKT": 6.5, "CAP": 6.0, "ECO": 5.5, "VEL": 5.5, "MOA": 7.5},
            "rationale": "TAM $3-6B (precision ag with outcome pricing). Variable "
                "margins (depends on recommendation accuracy). 3-6 month pilot "
                "then annual contracts. Very strong moat: outcome data creates "
                "proprietary risk models. Revenue = % of yield improvement × "
                "commodity price × acres. Must manage downside risk."
        },
        "forces_v3": ["F1_technology", "F5_psychology"],
        "primary_category": "FEAR_ECONOMY",
    },
    {
        "id": "MC-V55-11-001",
        "name": "Farm Data Interoperability Standard Platform",
        "one_liner": "Coordination protocol for agricultural data exchange — "
                     "implementing AgGateway ADAPT and ISO 11783 standards as a "
                     "cloud API that enables equipment data to flow between Deere, "
                     "CNH, AGCO, and independent software without vendor lock-in",
        "architecture": "coordination_protocol",
        "sector_naics": "11",
        "scores": {"SN": 8.0, "FA": 7.5, "EC": 6.0, "TG": 6.0, "CE": 6.0},
        "cla": {
            "scores": {"MO": 7, "MA": 9, "VD": 7, "DV": 8},
            "rationale": "AgGateway ADAPT framework exists as specification but no "
                "company has built the commercial implementation layer. Equipment "
                "OEMs have proprietary data silos. EU right-to-data regulation "
                "(Data Act 2025) mandates equipment data portability. Coordination "
                "protocol = standard-setting moat once adopted. Neutral third-party "
                "position is key (cannot be owned by an OEM)."
        },
        "vcr": {
            "scores": {"MKT": 6.0, "CAP": 6.5, "ECO": 6.0, "VEL": 5.0, "MOA": 8.0},
            "rationale": "TAM $2-3B (ag data integration + middleware). API-based "
                "revenue model. 75%+ margins. Slow standards adoption (12-24 months "
                "for OEM partnerships). Very strong protocol moat once adopted — "
                "switching costs are enormous. Network effects from ecosystem."
        },
        "forces_v3": ["F1_technology", "F3_geopolitics"],
        "primary_category": "STRUCTURAL_WINNER",
    },
    {
        "id": "MC-V55-11-002",
        "name": "Smart Soil Sensor Network & Analytics",
        "one_liner": "Low-cost ($50-100/unit) wireless soil moisture, temperature, "
                     "and nutrient sensors with edge AI — deploying 10-50 sensors "
                     "per field for continuous monitoring vs. the current standard "
                     "of 1-2 soil tests per year",
        "architecture": "hardware_ai",
        "sector_naics": "11",
        "scores": {"SN": 7.5, "FA": 7.0, "EC": 7.0, "TG": 7.0, "CE": 6.5},
        "cla": {
            "scores": {"MO": 7, "MA": 6, "VD": 5, "DV": 7},
            "rationale": "Arable ($40M raised), CropX ($55M raised), Teralytic "
                "compete. No dominant winner yet. Hardware commoditizing — value "
                "is in the analytics layer. Sensor cost must reach $50-100 (currently "
                "$200-500) for mass adoption. Irrigation management is beachhead "
                "use case. Continuous data >> annual soil tests."
        },
        "vcr": {
            "scores": {"MKT": 6.0, "CAP": 5.5, "ECO": 5.5, "VEL": 6.0, "MOA": 6.0},
            "rationale": "TAM $2-4B (soil sensors + analytics). Hardware+software "
                "margins 50-60%. Sensor replacement revenue every 3-5 years. "
                "Moderate data moat from field-specific calibrations. "
                "$500-2,500/field/year. Mass market requires sub-$100 sensor price."
        },
        "forces_v3": ["F1_technology", "F6_energy"],
        "primary_category": "FORCE_RIDER",
    },
    {
        "id": "MC-V55-1121-001",
        "name": "Cattle Feedlot Acquisition & AI Modernization",
        "one_liner": "Acquire underperforming 1,000-5,000 head feedlots from "
                     "retiring operators, deploy AI feed optimization, health "
                     "monitoring, and automated pen management — targeting the "
                     "2,100 large US feedlots where average operator age is 58+",
        "architecture": "acquire_and_modernize",
        "sector_naics": "1121",
        "scores": {"SN": 7.5, "FA": 6.5, "EC": 6.5, "TG": 7.0, "CE": 5.5},
        "cla": {
            "scores": {"MO": 7, "MA": 7, "VD": 4, "DV": 6},
            "rationale": "Feedlot ownership is fragmenting as operators retire. "
                "Top 50 feedlots are corporate-owned but 1,500+ mid-size feedlots "
                "(1K-5K head) are family-owned with aging operators. PE firms "
                "(Cactus Feeders model) are already rolling up but without AI "
                "modernization focus. Physical asset + AI operations creates "
                "defensible position. SBA/USDA loan programs assist acquisitions."
        },
        "vcr": {
            "scores": {"MKT": 5.5, "CAP": 5.0, "ECO": 4.5, "VEL": 5.0, "MOA": 5.5},
            "rationale": "TAM $3-5B (mid-size feedlot M&A market). Asset-heavy = lower "
                "returns (15-25% IRR target). 6-12 month acquisition cycle. "
                "Moderate moat from operational data. $2-5M per acquisition. "
                "Cyclical revenue (cattle cycle). Perez crash risk: commodity exposure."
        },
        "forces_v3": ["F1_technology", "F2_demographics", "F4_capital"],
        "primary_category": "TIMING_ARBITRAGE",
    },
    {
        "id": "MC-V55-1114-001",
        "name": "Open-Source Vertical Farm Control System",
        "one_liner": "Open-core environment control platform for indoor farms — "
                     "lighting, HVAC, irrigation, and nutrient dosing automation "
                     "with AI-optimized growth recipes, providing the operating "
                     "system for 2,500+ US vertical farming facilities",
        "architecture": "open_core_ecosystem",
        "sector_naics": "1114",
        "scores": {"SN": 7.0, "FA": 6.5, "EC": 6.0, "TG": 6.0, "CE": 5.5},
        "cla": {
            "scores": {"MO": 8, "MA": 8, "VD": 7, "DV": 7},
            "rationale": "Vertical farming had high-profile failures (AppHarvest "
                "bankrupt, AeroFarms bankrupt) but surviving operators need "
                "affordable control software. Priva, Autogrow, and Growlink "
                "sell hardware+software bundles. Open-source control layer "
                "reduces switching costs and enables farmer customization. "
                "CEA market growing despite failures — leafy greens economics work."
        },
        "vcr": {
            "scores": {"MKT": 4.5, "CAP": 6.5, "ECO": 5.5, "VEL": 5.5, "MOA": 7.0},
            "rationale": "TAM $500M-1B (CEA control software). Open-core margins "
                "80%+ on enterprise features. 3-6 month adoption. Community-driven "
                "growth recipe sharing creates network effects. Small current market "
                "but growing as CEA economics improve."
        },
        "forces_v3": ["F1_technology", "F6_energy"],
        "primary_category": "EMERGING_CATEGORY",
    },
    {
        "id": "MC-V55-1112-001",
        "name": "Vegetable Production AI Copilot",
        "one_liner": "AI copilot for vegetable and specialty crop growers — pest "
                     "identification from phone photos, irrigation scheduling, "
                     "harvest timing, and market price optimization for the "
                     "115K workers across 30,000+ vegetable operations",
        "architecture": "ai_copilot",
        "sector_naics": "1112",
        "scores": {"SN": 7.5, "FA": 7.0, "EC": 7.0, "TG": 7.5, "CE": 7.0},
        "cla": {
            "scores": {"MO": 8, "MA": 8, "VD": 6, "DV": 7},
            "rationale": "Specialty crops are underserved by precision ag — most "
                "tools optimized for corn/soy. Vegetables have 100+ crop types "
                "with different pest complexes. Phone-based image identification "
                "is accessible (no hardware needed). Plantix (20M+ downloads, "
                "India focus) proves concept but no US-focused veggie copilot. "
                "Highly fragmented market — no incumbent dominance."
        },
        "vcr": {
            "scores": {"MKT": 5.5, "CAP": 7.5, "ECO": 7.5, "VEL": 7.5, "MOA": 5.5},
            "rationale": "TAM $1-2B (specialty crop decision support). Pure software "
                "85%+ margins. Freemium → premium PLG model. Fast adoption via "
                "mobile. $500-3,000/grower/year. Moderate moat — crop-specific "
                "training data differentiates but AI advances commoditize."
        },
        "forces_v3": ["F1_technology", "F2_demographics"],
        "primary_category": "FORCE_RIDER",
    },
    {
        "id": "MC-V55-1111-003",
        "name": "Farm Data Privacy & Sovereignty Platform",
        "one_liner": "Privacy-first farm data vault — encrypted storage, granular "
                     "sharing permissions, and audit trails for field-level "
                     "agronomic data, addressing the 72% of farmers concerned "
                     "about who accesses their data, especially after the Monsanto/"
                     "Climate Corp data controversies",
        "architecture": "fear_economy_capture",
        "sector_naics": "1111",
        "scores": {"SN": 7.0, "FA": 8.5, "EC": 6.0, "TG": 6.5, "CE": 6.5},
        "cla": {
            "scores": {"MO": 8, "MA": 8, "VD": 5, "DV": 8},
            "rationale": "Fear-driven demand: 72% of farmers concerned about data "
                "privacy (Farm Bureau 2023). Monsanto/Climate Corp acquisition "
                "created lasting distrust. No privacy-first farm data platform. "
                "EU Data Act (2025) mandates ag equipment data portability, "
                "creating regulatory tailwind. Farmer cooperatives are natural "
                "distribution channel."
        },
        "vcr": {
            "scores": {"MKT": 5.0, "CAP": 7.0, "ECO": 6.5, "VEL": 6.0, "MOA": 7.0},
            "rationale": "TAM $1-2B (farm data privacy + sovereignty). SaaS margins "
                "80%+. 6-month adoption via cooperative channel. $1-3/acre/year "
                "or $2-5K/farm/year. Fear-driven demand is structural and growing. "
                "Trust moat — once farmers trust a platform, switching is rare."
        },
        "forces_v3": ["F1_technology", "F5_psychology"],
        "primary_category": "FEAR_ECONOMY",
    },
    {
        "id": "MC-V55-1119-001",
        "name": "Specialty Crop Compliance & Licensing SaaS",
        "one_liner": "Vertical SaaS for state-regulated specialty crops (hemp, "
                     "cannabis, hops) — cultivation tracking, THC compliance "
                     "testing, seed-to-sale reporting, and multi-state license "
                     "management for 50,000+ licensed operators navigating "
                     "fragmented state regulations",
        "architecture": "vertical_saas",
        "sector_naics": "1119",
        "scores": {"SN": 7.0, "FA": 7.0, "EC": 7.0, "TG": 6.5, "CE": 7.0},
        "cla": {
            "scores": {"MO": 7, "MA": 6, "VD": 5, "DV": 7},
            "rationale": "Metrc (mandatory track-and-trace in 20+ states) is dominant "
                "but widely hated by operators. Dutchie, Flowhub compete in retail "
                "POS but cultivation compliance is underserved. Hemp/cannabis "
                "regulatory fragmentation (50 different state regimes) creates "
                "compliance complexity = willingness to pay. Federal legalization "
                "would expand TAM dramatically."
        },
        "vcr": {
            "scores": {"MKT": 5.5, "CAP": 7.0, "ECO": 7.0, "VEL": 6.5, "MOA": 6.0},
            "rationale": "TAM $500M-1B (cultivation compliance SaaS). SaaS margins "
                "80%+. Regulatory urgency drives 3-6 month sales. $3-10K ACV per "
                "licensed operation. Moderate moat from state-specific compliance "
                "rules. Federal legalization risk: could simplify compliance, "
                "reducing willingness to pay."
        },
        "forces_v3": ["F1_technology", "F3_geopolitics"],
        "primary_category": "TIMING_ARBITRAGE",
    },
    {
        "id": "MC-V55-1121-002",
        "name": "Cattle Weight Gain Guarantee Platform",
        "one_liner": "Outcome-based feeding platform for cattle feedlots — AI "
                     "optimizes individual-pen rations and guarantees minimum "
                     "average daily gain (ADG) or feedlot doesn't pay, aligning "
                     "feed costs with weight performance on 26M+ head fed annually",
        "architecture": "outcome_based",
        "sector_naics": "1121",
        "scores": {"SN": 7.0, "FA": 7.0, "EC": 6.0, "TG": 6.0, "CE": 5.5},
        "cla": {
            "scores": {"MO": 7, "MA": 7, "VD": 5, "DV": 7},
            "rationale": "No feedlot nutrition company offers outcome guarantees. "
                "Current model: feedlots buy rations from nutritionists, bear "
                "all performance risk. Outcome-based pricing breaks trust barrier. "
                "ADG guarantee requires strong feed-to-gain predictive model. "
                "26M head fed annually × $1.10-$1.40/lb cost of gain × 500-600 lb "
                "gain = massive addressable spend."
        },
        "vcr": {
            "scores": {"MKT": 5.5, "CAP": 5.5, "ECO": 5.0, "VEL": 5.0, "MOA": 7.0},
            "rationale": "TAM $1-2B (outcome-based feeding optimization). Variable "
                "margins (depends on model accuracy). 6-month pilot cycles. "
                "Very strong moat from pen-level feeding outcome data. Must manage "
                "downside risk (guarantee payouts on bad pens). Commodity exposure."
        },
        "forces_v3": ["F1_technology", "F6_energy"],
        "primary_category": "CONDITIONAL",
    },
    {
        "id": "MC-V55-11-003",
        "name": "Agricultural IoT Gateway & Edge Compute Platform",
        "one_liner": "Ruggedized IoT gateway with edge AI for farm environments — "
                     "connecting sensors, cameras, and equipment data streams "
                     "in areas with limited cellular connectivity (60% of US "
                     "farmland lacks reliable broadband)",
        "architecture": "platform_infrastructure",
        "sector_naics": "11",
        "scores": {"SN": 8.0, "FA": 7.0, "EC": 7.0, "TG": 7.0, "CE": 6.5},
        "cla": {
            "scores": {"MO": 6, "MA": 6, "VD": 6, "DV": 7},
            "rationale": "Rural connectivity is THE bottleneck for precision ag. "
                "60% of farmland lacks reliable broadband. USDA ReConnect program "
                "investing $3.4B in rural broadband but deployment is slow. "
                "Edge compute + LoRaWAN/satellite solves the last-mile problem. "
                "John Deere's StarFire network is proprietary. Solinftec (Brazil) "
                "is closest competitor. Hardware + platform play."
        },
        "vcr": {
            "scores": {"MKT": 6.0, "CAP": 5.5, "ECO": 5.5, "VEL": 5.5, "MOA": 6.5},
            "rationale": "TAM $2-4B (ag IoT infrastructure). Hardware + software "
                "margins 45-55%. 6-12 month deployment. $1-5K per gateway + "
                "$500-2K/year SaaS. Infrastructure moat once deployed (switching "
                "costs). Rural connectivity improving but slowly — 5-10 year "
                "window of opportunity."
        },
        "forces_v3": ["F1_technology", "F3_geopolitics"],
        "primary_category": "FORCE_RIDER",
    },
]


def build_model(template):
    """Build complete model from template."""
    m = deepcopy(template)
    m["sector_name"] = NAICS_NAMES.get(m["sector_naics"], "Agriculture")
    m["composite"] = round(compute_t(m["scores"]), 2)
    m["cla"]["composite"] = round(compute_cla(m["cla"]["scores"]), 2)
    m["cla"]["category"] = cla_cat(m["cla"]["composite"])

    m["vcr"]["composite"] = round(compute_vcr(m["vcr"]["scores"]), 2)
    m["vcr"]["category"] = vcr_cat(m["vcr"]["composite"])

    # ROI estimate
    vs = m["vcr"]["scores"]
    tam_factor = vs["MKT"] * 80
    cap_rate = vs["CAP"] * 0.002
    vel = 1.0 + (vs["VEL"] - 5) * 0.12
    is_saas = "saas" in m.get("architecture", "") or "copilot" in m.get("architecture", "")
    rev_mult = 12.0 if is_saas else 8.0
    y5_rev = tam_factor * cap_rate * vel
    exit_val = y5_rev * rev_mult
    m["vcr"]["roi_estimate"] = {
        "year5_revenue_M": round(y5_rev, 1),
        "revenue_multiple": rev_mult,
        "exit_val_M": round(exit_val, 1),
        "seed_roi_multiple": round(exit_val / 10.0, 1)
    }

    m["category"] = [m["primary_category"]]
    m["new_in_v36"] = False
    m["narrative_ids"] = ["TN-017"]
    m["confidence_tier"] = "HIGH" if m["composite"] >= 70 else "MEDIUM"
    m["evidence_quality"] = "v55_agriculture_deep_dive"
    m["source_batch"] = "v55_agriculture_expansion"
    m["falsification_criteria"] = []
    return m


def main():
    print("=" * 70)
    print("v5.5 Agriculture Deep Dive Expansion")
    print("=" * 70)

    with open(MODELS_FILE) as f:
        models_data = json.load(f)
    models = models_data.get("models", models_data) if isinstance(models_data, dict) else models_data
    print("Loaded {} models".format(len(models)))

    existing_ids = {m["id"] for m in models}
    added = []

    for template in NEW_MODELS:
        if template["id"] not in existing_ids:
            m = build_model(template)
            models.append(m)
            added.append(m)
            gm = geo_mean(m["composite"], m["cla"]["composite"], m["vcr"]["composite"])
            print("  + {} — {} (T={}, CLA={}, VCR={}, GM={:.1f})".format(
                m["id"], m["name"][:55],
                m["composite"], m["cla"]["composite"], m["vcr"]["composite"], gm))

    print("\nAdded {} new models (total: {})".format(len(added), len(models)))

    # Rerank
    models.sort(key=lambda m: -m["composite"])
    for i, m in enumerate(models):
        m["rank"] = i + 1

    models.sort(key=lambda m: -m["cla"]["composite"])
    for i, m in enumerate(models):
        m["opportunity_rank"] = i + 1

    models.sort(key=lambda m: -m["vcr"]["composite"])
    for i, m in enumerate(models):
        m["vcr_rank"] = i + 1

    models.sort(key=lambda m: m["rank"])

    # Stats
    ag_models = [m for m in models if "TN-017" in m.get("narrative_ids", [])]
    print("\nTN-017 Agriculture models: {} (was 19)".format(len(ag_models)))

    ag_t = [m["composite"] for m in ag_models]
    ag_cla = [m["cla"]["composite"] for m in ag_models]
    ag_vcr = [m["vcr"]["composite"] for m in ag_models]
    print("  T mean={:.1f}, CLA mean={:.1f}, VCR mean={:.1f}".format(
        statistics.mean(ag_t), statistics.mean(ag_cla), statistics.mean(ag_vcr)))

    # Top 10 ag by GM
    print("\n  Top 10 Agriculture (by GM):")
    for m in ag_models:
        m["_gm"] = geo_mean(m["composite"], m["cla"]["composite"], m["vcr"]["composite"])
    ag_models.sort(key=lambda m: -m["_gm"])
    for i, m in enumerate(ag_models[:10]):
        print("    #{}: {} — GM={:.1f} (T={}, CLA={}, VCR={})".format(
            i + 1, m["name"][:55], m["_gm"],
            m["composite"], m["cla"]["composite"], m["vcr"]["composite"]))

    # Architecture distribution
    arch_dist = Counter(m.get("architecture", "") for m in ag_models)
    print("\n  Architecture distribution:")
    for arch, count in arch_dist.most_common():
        print("    {}: {}".format(arch, count))

    # Sub-sector distribution
    naics_dist = Counter(str(m.get("sector_naics", "")) for m in ag_models)
    print("\n  Sub-sector distribution:")
    for naics, count in naics_dist.most_common():
        name = NAICS_NAMES.get(naics, naics)
        print("    {} ({}): {}".format(naics, name[:30], count))

    # Clean temp
    for m in ag_models:
        if "_gm" in m:
            del m["_gm"]

    # Update narratives
    with open(NARRATIVES_FILE) as f:
        narr_data = json.load(f)
    narratives = narr_data["narratives"]
    for n in narratives:
        if n["narrative_id"] == "TN-017":
            ww = n["outputs"]["what_works"]
            for m in added:
                if m["id"] not in ww:
                    ww.append(m["id"])
            n["v3_models_rated"] = len(ag_models)
            print("\nUpdated TN-017: {} models in what_works".format(len(ww)))

    # Save
    if isinstance(models_data, dict):
        models_data["models"] = models
        models_data["count"] = len(models)
        models_data["last_updated"] = datetime.now().isoformat()
        models_data["version"] = "v5.5_agriculture_expansion"
    with open(MODELS_FILE, "w") as f:
        json.dump(models_data, f, indent=2)
    with open(NARRATIVES_FILE, "w") as f:
        json.dump(narr_data, f, indent=2)

    # Update state
    with open(STATE_FILE) as f:
        state = json.load(f)
    state["engine_version"] = "5.5"
    state["entity_counts"]["models"] = len(models)
    state["description"] = (
        "v5.5: {} models. Agriculture deep dive expansion: {} new models "
        "across 14 sub-sectors, 13 architecture types. TN-017 Agriculture: "
        "{} models (was 19).".format(len(models), len(added), len(ag_models))
    )
    state["cycles"].append({
        "cycle_id": "v5-5-agriculture",
        "date": datetime.now().strftime("%Y-%m-%d"),
        "models_before": 797,
        "models_after": len(models),
        "new_models": [m["id"] for m in added],
        "key_findings": [],
    })
    with open(STATE_FILE, "w") as f:
        json.dump(state, f, indent=2)

    print("\nSaved {} models, state updated to v5.5".format(len(models)))
    print("=" * 70)


if __name__ == "__main__":
    main()
