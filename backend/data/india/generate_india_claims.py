"""Generate a synthetic Indian private-car motor claims dataset for every model in the project.

    python generate_india_claims.py [--rows 20000] [--seed 7] [--out-dir .]

One population of claims is simulated once, then written out in the layout each trainer reads:

    india_claims_master.csv       every simulated field, including the hidden truth (fraud scheme)
    india_insurance_claims.csv    insurance_claims.csv layout  -> fraud_risk, repair_cost, total_loss
    india_fraud_oracle.csv        fraud_oracle.csv layout      -> fraud_oracle_fraud
    india_vehicle_fraud.csv       vehicle_fraud feature layout -> vehicle_fraud

THIS IS SYNTHETIC DATA. It is built from public Indian rules (IRDAI IDV depreciation, third-party
premiums, compulsory deductibles) and documented motor-fraud patterns, but the costs and fraud
behaviour are assumptions written in this file, not observed settlements. A model trained on it
learns these assumptions. Use it to develop, test and demo the pipeline, and replace it with real
settled claims (with investigator outcomes) before trusting the scores. See README.md.
"""
import argparse
from datetime import date, timedelta
from pathlib import Path

import numpy as np
import pandas as pd

# ------------------------------------------------------------------ reference data

# make, model, body style, fuel options, ex-showroom price (INR, approx. 2024 base-mid variant), cc
CATALOG = [
    ("Maruti Suzuki", "Alto K10", "hatchback", ["gasoline"], 420_000, 998, 7),
    ("Maruti Suzuki", "WagonR", "hatchback", ["gasoline"], 560_000, 998, 7),
    ("Maruti Suzuki", "Swift", "hatchback", ["gasoline"], 680_000, 1197, 9),
    ("Maruti Suzuki", "Baleno", "hatchback", ["gasoline"], 740_000, 1197, 7),
    ("Maruti Suzuki", "Dzire", "sedan", ["gasoline"], 720_000, 1197, 7),
    ("Maruti Suzuki", "Ertiga", "muv", ["gasoline"], 980_000, 1462, 5),
    ("Maruti Suzuki", "Brezza", "suv", ["gasoline"], 1_000_000, 1462, 6),
    ("Maruti Suzuki", "Grand Vitara", "suv", ["gasoline", "hybrid"], 1_300_000, 1462, 3),
    ("Hyundai", "Grand i10 Nios", "hatchback", ["gasoline"], 640_000, 1197, 4),
    ("Hyundai", "i20", "hatchback", ["gasoline"], 800_000, 1197, 4),
    ("Hyundai", "Venue", "suv", ["gasoline", "diesel"], 950_000, 1197, 4),
    ("Hyundai", "Verna", "sedan", ["gasoline"], 1_250_000, 1497, 3),
    ("Hyundai", "Creta", "suv", ["gasoline", "diesel"], 1_350_000, 1497, 6),
    ("Tata", "Tiago", "hatchback", ["gasoline", "electric"], 600_000, 1199, 4),
    ("Tata", "Punch", "suv", ["gasoline", "electric"], 700_000, 1199, 5),
    ("Tata", "Altroz", "hatchback", ["gasoline", "diesel"], 780_000, 1199, 3),
    ("Tata", "Nexon", "suv", ["gasoline", "diesel", "electric"], 1_000_000, 1199, 6),
    ("Tata", "Harrier", "suv", ["diesel"], 1_800_000, 1956, 2),
    ("Mahindra", "Bolero", "suv", ["diesel"], 1_000_000, 1493, 3),
    ("Mahindra", "XUV 3XO", "suv", ["gasoline", "diesel"], 1_000_000, 1197, 2),
    ("Mahindra", "Thar", "suv", ["gasoline", "diesel"], 1_400_000, 2184, 3),
    ("Mahindra", "Scorpio-N", "suv", ["diesel"], 1_700_000, 2184, 3),
    ("Mahindra", "XUV700", "suv", ["gasoline", "diesel"], 1_900_000, 2198, 3),
    ("Kia", "Sonet", "suv", ["gasoline", "diesel"], 950_000, 1197, 3),
    ("Kia", "Seltos", "suv", ["gasoline", "diesel"], 1_350_000, 1497, 3),
    ("Kia", "Carens", "muv", ["gasoline", "diesel"], 1_250_000, 1497, 2),
    ("Toyota", "Glanza", "hatchback", ["gasoline"], 780_000, 1197, 2),
    ("Toyota", "Urban Cruiser Hyryder", "suv", ["gasoline", "hybrid"], 1_400_000, 1462, 2),
    ("Toyota", "Innova Crysta", "muv", ["diesel"], 2_300_000, 2393, 2),
    ("Toyota", "Fortuner", "suv", ["diesel"], 3_800_000, 2755, 1),
    ("Honda", "Amaze", "sedan", ["gasoline"], 800_000, 1199, 3),
    ("Honda", "City", "sedan", ["gasoline", "hybrid"], 1_350_000, 1498, 3),
    ("MG", "Comet EV", "hatchback", ["electric"], 750_000, 0, 1),
    ("MG", "Hector", "suv", ["gasoline", "diesel"], 1_800_000, 1451, 2),
    ("MG", "ZS EV", "suv", ["electric"], 2_000_000, 0, 1),
    ("Renault", "Kwid", "hatchback", ["gasoline"], 500_000, 999, 3),
    ("Renault", "Kiger", "suv", ["gasoline"], 750_000, 999, 2),
    ("Skoda", "Slavia", "sedan", ["gasoline"], 1_300_000, 999, 2),
    ("Volkswagen", "Virtus", "sedan", ["gasoline"], 1_350_000, 999, 2),
    ("BMW", "3 Series", "sedan", ["gasoline", "diesel"], 5_000_000, 1998, 1),
    ("Mercedes-Benz", "C-Class", "sedan", ["gasoline", "diesel"], 6_000_000, 1999, 1),
]
LUXURY_MAKES = {"BMW", "Mercedes-Benz"}

# city, state code, state name, city tier (labour rates and traffic differ by tier)
CITIES = [
    ("Mumbai", "MH", "Maharashtra", 1), ("Delhi", "DL", "Delhi", 1), ("Bengaluru", "KA", "Karnataka", 1),
    ("Chennai", "TN", "Tamil Nadu", 1), ("Hyderabad", "TG", "Telangana", 1), ("Kolkata", "WB", "West Bengal", 1),
    ("Pune", "MH", "Maharashtra", 1), ("Ahmedabad", "GJ", "Gujarat", 1), ("Gurugram", "HR", "Haryana", 1),
    ("Noida", "UP", "Uttar Pradesh", 1), ("Jaipur", "RJ", "Rajasthan", 2), ("Lucknow", "UP", "Uttar Pradesh", 2),
    ("Indore", "MP", "Madhya Pradesh", 2), ("Surat", "GJ", "Gujarat", 2), ("Nagpur", "MH", "Maharashtra", 2),
    ("Kochi", "KL", "Kerala", 2), ("Chandigarh", "CH", "Chandigarh", 2), ("Coimbatore", "TN", "Tamil Nadu", 2),
    ("Bhopal", "MP", "Madhya Pradesh", 2), ("Patna", "BR", "Bihar", 2), ("Vadodara", "GJ", "Gujarat", 2),
    ("Ludhiana", "PB", "Punjab", 2), ("Visakhapatnam", "AP", "Andhra Pradesh", 2), ("Bhubaneswar", "OD", "Odisha", 2),
    ("Nashik", "MH", "Maharashtra", 3), ("Mysuru", "KA", "Karnataka", 3), ("Meerut", "UP", "Uttar Pradesh", 3),
    ("Agra", "UP", "Uttar Pradesh", 3), ("Guwahati", "AS", "Assam", 3), ("Dehradun", "UK", "Uttarakhand", 3),
    ("Madurai", "TN", "Tamil Nadu", 3), ("Raipur", "CG", "Chhattisgarh", 3), ("Ranchi", "JH", "Jharkhand", 3),
    ("Thiruvananthapuram", "KL", "Kerala", 3), ("Udaipur", "RJ", "Rajasthan", 3),
]
CITY_WEIGHTS = np.array([5 if tier == 1 else 2.5 if tier == 2 else 1.2 for *_, tier in CITIES], dtype=float)
LABOUR_MULT = {1: 1.15, 2: 1.0, 3: 0.88}
MONSOON_STATES = {"MH", "KL", "TN", "AS", "WB", "KA", "GJ", "OD", "BR", "UK"}

# IRDAI IDV depreciation (vehicle age in months up to and including -> rate); past 5 years the
# IDV is negotiated, approximated as +5 points a year to 80%. Same rule as repair_estimate.py.
IRDAI_DEPRECIATION = [(6, 0.05), (12, 0.15), (24, 0.20), (36, 0.30), (48, 0.40), (60, 0.50)]

# Third-party premium by engine size (IRDAI, effective 2019, still in force) and the compulsory
# own-damage deductible (INR 1,000 up to 1500 cc, INR 2,000 above).
def tp_premium(cc):
    return 2094 if cc <= 1000 else 3416 if cc <= 1500 else 7897


NCB_LADDER = [0, 20, 25, 35, 45, 50]

# App incident types (apps.claims.models.IncidentType) with base frequency for private cars.
INCIDENT_TYPES = {
    "collision": 0.52, "comprehensive": 0.07, "theft": 0.04, "vandalism": 0.04, "fire": 0.012,
    "water_damage": 0.05, "hail": 0.005, "animal": 0.05, "glass": 0.11, "other": 0.103,
}
# Severity probabilities per incident type: minor, moderate, major, total_loss (before the
# constructive-total-loss rule, which can still turn an expensive repair into a total loss).
SEVERITY_BY_TYPE = {
    "collision": [0.40, 0.36, 0.20, 0.04], "comprehensive": [0.50, 0.35, 0.13, 0.02],
    "theft": [0.08, 0.10, 0.07, 0.75], "vandalism": [0.55, 0.35, 0.10, 0.00],
    "fire": [0.10, 0.20, 0.35, 0.35], "water_damage": [0.15, 0.40, 0.35, 0.10],
    "hail": [0.45, 0.45, 0.10, 0.00], "animal": [0.45, 0.40, 0.14, 0.01],
    "glass": [0.85, 0.15, 0.00, 0.00], "other": [0.55, 0.32, 0.12, 0.01],
}
SEVERITIES = ["minor", "moderate", "major", "total_loss"]
# Repair bill = body-shop labour + parts share of ex-showroom price (parts are bought new, so the
# new price, not the IDV, drives the bill). Same calibration as apps/assessments/repair_estimate.py,
# from real Indian part prices and labour rates (data/india/reference/, Nov 2026). Medians; actual
# bills vary log-normally around them, parts more than labour (real parts shares for a two-part
# job range from 0.2% to 3% of the price depending on the model).
SMALL, LARGE = "hatchback/sedan", "suv/muv"
REPAIR_RATES = {  # severity -> ({segment: labour INR}, parts share)
    "minor": ({SMALL: 4_500, LARGE: 6_000}, 0.002),
    "moderate": ({SMALL: 5_000, LARGE: 6_500}, 0.012),
    "major": ({SMALL: 12_000, LARGE: 17_500}, 0.040),
}
GLASS_RATE = ({SMALL: 2_360, LARGE: 2_360}, 0.007)
TYPE_COST_MULT = {"hail": 0.9, "water_damage": 1.25, "fire": 1.3, "vandalism": 0.8}


def segment_of(body):
    return LARGE if body in ("suv", "muv") else SMALL


def rate_for(severity, incident_type):
    return GLASS_RATE if incident_type == "glass" else REPAIR_RATES[severity]
CONSTRUCTIVE_TOTAL_LOSS_SHARE = 0.75  # repair above 75% of IDV is settled as a total loss

# Mapping to the insurance_claims.csv vocabulary, matching apps/assessments/ai_views.py so the
# app scores live claims with the same categories it was trained on.
INSURANCE_SEVERITY = {"minor": "Trivial Damage", "moderate": "Minor Damage", "major": "Major Damage",
                      "total_loss": "Total Loss"}


def depreciation(months):
    for limit, rate in IRDAI_DEPRECIATION:
        if months <= limit:
            return rate
    return min(0.80, 0.50 + ((months - 60 + 11) // 12) * 0.05)


# ------------------------------------------------------------------ simulation

def simulate(rows, seed):
    rng = np.random.default_rng(seed)
    catalog_weights = np.array([entry[-1] for entry in CATALOG], dtype=float)
    catalog_weights /= catalog_weights.sum()
    city_p = CITY_WEIGHTS / CITY_WEIGHTS.sum()
    type_names = list(INCIDENT_TYPES)
    type_p = np.array(list(INCIDENT_TYPES.values()))
    type_p /= type_p.sum()
    garages = [f"GRG{n:04d}" for n in range(1, 401)]
    # A few garages work with organised fraud; most fraud is opportunistic and goes anywhere.
    ring_garages = set(rng.choice(garages, size=12, replace=False))

    start, end = date(2022, 1, 1), date(2025, 12, 31)
    span = (end - start).days
    records = []
    for index in range(rows):
        make, model, body, fuels, price, cc, _ = CATALOG[rng.choice(len(CATALOG), p=catalog_weights)]
        fuel = fuels[rng.integers(len(fuels))]
        if fuel == "electric":
            price = int(price * 1.45) if model not in ("Comet EV", "ZS EV") else price
        price = int(round(price * rng.uniform(0.9, 1.25), -3))  # variant spread
        city, state_code, state, tier = CITIES[rng.choice(len(CITIES), p=city_p)]

        incident = start + timedelta(days=int(rng.integers(span)))
        vehicle_age_years = int(min(15, rng.gamma(2.0, 2.0)))
        reg_year = incident.year - vehicle_age_years
        age_months = vehicle_age_years * 12 + int(rng.integers(0, 12))
        dep = depreciation(age_months)
        idv = round(price * (1 - dep), -2)

        holder_age = int(np.clip(rng.normal(41, 11), 21, 78))
        sex = "Male" if rng.random() < 0.82 else "Female"
        marital = rng.choice(["Married", "Single", "Widow", "Divorced"], p=[0.72, 0.23, 0.03, 0.02])
        months_as_customer = int(rng.integers(1, 240))
        past_claims = int(rng.poisson(0.35 + 0.004 * min(months_as_customer, 120)))
        ncb = NCB_LADDER[min(5, max(0, int(rng.integers(0, 7)) - past_claims * 2))]
        plan = rng.choice(["Comprehensive", "Zero Depreciation", "Standalone OD"], p=[0.5, 0.35, 0.15])
        if plan == "Zero Depreciation" and vehicle_age_years > 5:
            plan = "Comprehensive"  # insurers rarely sell zero-dep past 5 years
        voluntary_deductible = int(rng.choice([0, 0, 0, 2500, 5000, 7500]))
        deductible = (1000 if cc <= 1500 else 2000) + voluntary_deductible
        od_rate = (0.0310 if cc <= 1000 else 0.0328 if cc <= 1500 else 0.0344) * (1.0 if tier == 1 else 0.97)
        od = idv * od_rate * (1 - ncb / 100) * rng.uniform(0.55, 0.9)  # market discount on tariff
        if plan == "Zero Depreciation":
            od *= 1.18
        tp = 0 if plan == "Standalone OD" else tp_premium(cc)
        premium = round((od + tp) * 1.18, 2)  # 18% GST
        policy_start = incident - timedelta(days=int(rng.integers(0, 365)))

        incident_type = type_names[rng.choice(len(type_names), p=type_p)]
        in_monsoon = state_code in MONSOON_STATES and incident.month in (6, 7, 8, 9)
        if incident_type == "water_damage" and not in_monsoon and rng.random() < 0.6:
            incident_type = "collision"  # floods outside the monsoon belt/season are rarer
        severity = SEVERITIES[rng.choice(4, p=SEVERITY_BY_TYPE[incident_type])]
        hour = int(rng.choice(24, p=_hour_profile()))
        vehicles = 1 if incident_type != "collision" else int(rng.choice([1, 2, 3], p=[0.45, 0.47, 0.08]))
        injuries = bool(incident_type == "collision" and rng.random() < {"minor": 0.03, "moderate": 0.1,
                                                                         "major": 0.35, "total_loss": 0.5}[severity])
        property_damage = bool(incident_type == "collision" and rng.random() < 0.25)
        witnesses = int(rng.choice([0, 1, 2, 3], p=[0.5, 0.3, 0.15, 0.05])) if incident_type == "collision" else int(rng.random() < 0.12)
        police_p = {"theft": 0.97, "fire": 0.7, "collision": {"minor": 0.08, "moderate": 0.2, "major": 0.6,
                                                              "total_loss": 0.85}[severity]}.get(incident_type, 0.1)
        police_report = bool(rng.random() < police_p or injuries and rng.random() < 0.8)
        # Most honest claims are reported within a few days, but a real minority come in a week or
        # more later (travel, waiting for a garage quote, festivals, slow paperwork), so lateness
        # alone must not look like proof of fraud.
        late = rng.random()
        if late < 0.80:
            reporting_delay = int(rng.geometric(0.55) - 1)
        elif late < 0.97:
            reporting_delay = int(rng.integers(4, 22))
        else:
            reporting_delay = int(rng.integers(22, 46))
        if incident_type == "water_damage":
            reporting_delay += int(rng.integers(0, 4))  # floods delay intimation for genuine reasons
        garage = garages[rng.integers(len(garages))]

        # Fraud propensity: opportunity and pressure factors, plus a lot of unexplained variation.
        logit = (-3.05 + 0.9 * (policy_start > incident - timedelta(days=45)) + 0.35 * min(past_claims, 3)
                 + 0.5 * (vehicle_age_years >= 8) + 0.4 * (ncb == 0) + 0.45 * (plan == "Zero Depreciation")
                 - 0.004 * months_as_customer + 1.6 * (garage in ring_garages) + rng.normal(0, 0.8))
        is_fraud = rng.random() < 1 / (1 + np.exp(-logit))
        scheme = ""

        # Photo evidence of an honest claim. WhatsApp-forwarded photos lose their camera date,
        # so missing EXIF is common even when nothing is wrong.
        photo_count = 0 if rng.random() < 0.05 else int(np.clip(rng.poisson(5), 1, 15))
        photos = dict(reused=0, before=0, days_before=0, edited=0, no_date=0, small=0)
        if photo_count:
            photos["no_date"] = int(rng.binomial(photo_count, 0.15))
            photos["edited"] = int(rng.binomial(photo_count, 0.01))
            photos["small"] = int(rng.binomial(photo_count, 0.03))
            if rng.random() < 0.02:  # wrong phone clock
                photos["before"], photos["days_before"] = 1, int(rng.integers(1, 3))
            if rng.random() < 0.003:
                photos["reused"] = 1

        if is_fraud:
            scheme = _pick_scheme(rng, incident_type, vehicle_age_years)
            if scheme == "staged_accident":
                incident_type, vehicles = "collision", int(rng.choice([2, 3], p=[0.8, 0.2]))
                severity = SEVERITIES[rng.choice(4, p=[0.1, 0.45, 0.4, 0.05])]
                if rng.random() < 0.6:
                    hour = int(rng.choice([22, 23, 0, 1, 2, 3, 4]))
                injuries = rng.random() < 0.55
                witnesses = int(rng.choice([0, 1, 2], p=[0.25, 0.3, 0.45]))  # friendly witnesses
                police_report = rng.random() < 0.45
            elif scheme == "pre_existing_damage":
                policy_start = incident - timedelta(days=int(rng.integers(1, 30)))
                reporting_delay += int(rng.integers(2, 20))
                if photo_count and rng.random() < 0.45:
                    photos["before"] = max(1, int(rng.binomial(photo_count, 0.4)))
                    photos["days_before"] = int(rng.integers(8, 240))
                police_report = rng.random() < 0.05
            elif scheme == "fake_theft":
                incident_type, severity = "theft", "total_loss"
                police_report = rng.random() < 0.65  # FIR is mandatory; missing or late FIRs stand out
                reporting_delay += int(rng.integers(3, 30))
                if rng.random() < 0.5:
                    hour = int(rng.choice([23, 0, 1, 2, 3, 4]))
                photo_count = 0 if rng.random() < 0.7 else photo_count
            elif scheme == "recycled_photos":
                photo_count = max(photo_count, int(rng.integers(2, 8)))
                photos["reused"] = int(rng.integers(1, photo_count + 1)) if rng.random() < 0.6 else 0
                photos["edited"] = int(rng.binomial(photo_count, 0.3))
                photos["small"] = int(rng.binomial(photo_count, 0.35))
                photos["no_date"] = int(rng.binomial(photo_count, 0.5))
            elif scheme == "arson_or_flood_dump":
                incident_type = "fire" if rng.random() < 0.55 else "water_damage"
                severity = SEVERITIES[rng.choice(4, p=[0, 0.1, 0.35, 0.55])]
                reporting_delay += int(rng.integers(1, 10))
                police_report = rng.random() < 0.5

        # The severity the customer picks on the claim form. People misjudge damage by one level
        # about 15% of the time; theft and total-loss reports are taken as given. The surveyor's
        # outcome (`severity` below) can still turn an expensive repair into a total loss.
        reported_severity = severity
        if incident_type != "theft" and severity != "total_loss" and rng.random() < 0.15:
            level = SEVERITIES.index(severity) + int(rng.choice([-1, 1]))
            reported_severity = SEVERITIES[min(max(level, 0), 2)]

        # True (surveyor-assessed) loss before deductible.
        parts_mult = TYPE_COST_MULT.get(incident_type, 1.0)
        if severity == "total_loss" and incident_type != "theft" and rng.random() < 0.25:
            # Reported as a write-off, but the surveyor finds it repairable: a heavy major repair,
            # which can still cross the 75%-of-IDV line below.
            severity, parts_mult = "major", parts_mult * rng.uniform(3, 8)
        elif severity == "major" and rng.random() < 0.25:
            parts_mult *= rng.uniform(2, 6)  # structural, airbag or engine damage behind the panels
        if severity == "total_loss":
            true_cost = idv
        else:
            labour_by_segment, parts_share = rate_for(severity, incident_type)
            labour = labour_by_segment[segment_of(body)] * LABOUR_MULT[tier] * rng.lognormal(0, 0.25)
            if make in LUXURY_MAKES:
                labour *= 1.35  # premium paint and dealer labour rates
            if fuel == "electric" and severity == "major":
                parts_mult *= 1.3  # battery pack and high-voltage components
            true_cost = labour + price * parts_share * parts_mult * rng.lognormal(0, 0.45)
            if true_cost > CONSTRUCTIVE_TOTAL_LOSS_SHARE * idv:
                severity, true_cost = "total_loss", idv
        true_cost = round(max(true_cost, 1500), -2)

        # What the customer claims.
        claim_ratio = rng.lognormal(0.06, 0.08)  # honest claims round up a little
        if scheme == "inflated_bill":
            claim_ratio = rng.uniform(1.4, 3.2)
        elif scheme in ("staged_accident", "pre_existing_damage"):
            claim_ratio = rng.uniform(1.1, 2.0)
        claimed_vehicle = round(min(true_cost * claim_ratio, idv * 1.05), -2)
        injury_claim = round(rng.uniform(15_000, 250_000), -2) if injuries else 0
        if scheme == "staged_accident" and injuries:
            injury_claim = round(injury_claim * rng.uniform(1.3, 2.5), -2)
        property_claim = round(rng.uniform(5_000, 80_000), -2) if property_damage else 0

        # Estimate the app makes from IDV and the reported severity (apps/assessments/repair_estimate.py).
        if reported_severity == "total_loss":
            app_estimate = idv
        else:
            labour_by_segment, parts_share = rate_for(reported_severity, incident_type)
            app_estimate = min(labour_by_segment[segment_of(body)] + price * parts_share, idv)
        app_estimate = round(app_estimate, -2)

        # Investigators do not catch everything, and occasionally wrongly flag an honest claim.
        if is_fraud:
            label = "fraud" if rng.random() < 0.88 else "genuine"
        else:
            label = "fraud" if rng.random() < 0.01 else "genuine"

        days_policy_to_incident = (incident - policy_start).days
        records.append({
            "claim_id": f"INC{index + 1:06d}",
            "policy_number": f"POL{int(rng.integers(10**8, 10**9))}",
            "policy_start_date": policy_start.isoformat(),
            "incident_date": incident.isoformat(),
            "reported_date": (incident + timedelta(days=reporting_delay)).isoformat(),
            "incident_hour": hour,
            "city": city, "state_code": state_code, "state": state, "city_tier": tier,
            "garage_id": garage,
            "holder_age": holder_age, "holder_sex": sex, "holder_marital_status": marital,
            "months_as_customer": months_as_customer, "past_claims_count": past_claims, "ncb_percent": ncb,
            "policy_plan": plan, "deductible_inr": deductible, "annual_premium_inr": premium,
            "vehicle_make": make, "vehicle_model": model, "body_style": body, "fuel_type": fuel,
            "engine_cc": cc, "registration_year": reg_year, "vehicle_age_years": vehicle_age_years,
            "ex_showroom_price_inr": price, "idv_inr": idv,
            "incident_type": incident_type, "reported_severity": reported_severity,
            "incident_severity": severity, "is_total_loss": int(severity == "total_loss"),
            "number_of_vehicles": vehicles, "injuries": int(injuries), "property_damage": int(property_damage),
            "witnesses": witnesses, "police_report": int(police_report),
            "days_policy_to_incident": days_policy_to_incident, "reporting_delay_days": reporting_delay,
            "photo_count": photo_count,
            "photos_reused_from_other_claims": min(photos["reused"], photo_count),
            "photos_taken_before_incident": min(photos["before"], photo_count),
            "photo_days_before_incident": photos["days_before"] if photo_count else 0,
            "photos_edited": min(photos["edited"], photo_count),
            "photos_without_camera_date": min(photos["no_date"], photo_count),
            "photos_small": min(photos["small"], photo_count),
            "app_repair_estimate_inr": app_estimate,
            "assessed_repair_cost_inr": true_cost,
            "claimed_vehicle_amount_inr": claimed_vehicle,
            "injury_claim_inr": injury_claim, "property_claim_inr": property_claim,
            "total_claim_amount_inr": claimed_vehicle + injury_claim + property_claim,
            "supplementary_estimates": int(rng.poisson(2.2 if scheme == "inflated_bill" else 0.5)),
            "address_changed_recently": int(rng.random() < (0.12 if is_fraud else 0.03)),
            "fraud_outcome": label,
            "is_fraud_truth": int(is_fraud),
            "fraud_scheme": scheme,
        })
    return pd.DataFrame.from_records(records)


_HOURS = None


def _hour_profile():
    global _HOURS
    if _HOURS is None:
        weights = np.array([1, 0.7, 0.6, 0.5, 0.6, 1, 2, 4, 6, 6, 5, 5, 5, 5, 5, 5, 6, 7, 7, 6, 4, 3, 2, 1.5])
        _HOURS = weights / weights.sum()
    return _HOURS


def _pick_scheme(rng, incident_type, vehicle_age_years):
    weights = {"inflated_bill": 0.42, "staged_accident": 0.14, "pre_existing_damage": 0.16,
               "fake_theft": 0.09, "recycled_photos": 0.12, "arson_or_flood_dump": 0.07}
    if vehicle_age_years >= 7:  # dumping an old car for its IDV
        weights["fake_theft"] *= 2
        weights["arson_or_flood_dump"] *= 2
    if incident_type == "glass":
        weights["inflated_bill"] *= 1.5
    names = list(weights)
    p = np.array(list(weights.values()))
    return names[rng.choice(len(names), p=p / p.sum())]


# ------------------------------------------------------------------ export layouts

def insurance_layout(m):
    """insurance_claims.csv columns, in rupees, with the app's category names (ai_views.py)."""
    incident_type = np.select(
        [m.incident_type.eq("collision") & m.number_of_vehicles.eq(1), m.incident_type.eq("collision"),
         m.incident_type.eq("theft"), m.incident_type.eq("comprehensive")],
        ["Single Vehicle Collision", "Multi-vehicle Collision", "Vehicle Theft", "Parked Car"], "Other")
    yes_no = lambda s: np.where(s.astype(bool), "YES", "NO")
    return pd.DataFrame({
        "months_as_customer": m.months_as_customer,
        "age": m.holder_age,
        "policy_number": m.policy_number,
        "policy_bind_date": m.policy_start_date,
        "policy_state": m.state_code,
        "policy_csl": "unlimited TP / IDV OD",
        "policy_deductable": m.deductible_inr,
        "policy_annual_premium": m.annual_premium_inr,
        "umbrella_limit": 0,
        "insured_zip": "",
        "insured_sex": m.holder_sex.str.upper(),
        "incident_date": m.incident_date,
        "incident_type": incident_type,
        "collision_type": np.where(m.incident_type.eq("collision"), "Front/Side/Rear", "?"),
        # What the customer reported; the surveyor's total-loss decision is a separate outcome.
        "incident_severity": m.reported_severity.map(INSURANCE_SEVERITY),
        "total_loss_outcome": np.where(m.is_total_loss.astype(bool), "Y", "N"),
        "authorities_contacted": np.where(m.police_report.astype(bool), "Police", "None"),
        "incident_state": m.state_code,
        "incident_city": m.city,
        "incident_location": m.city,
        "incident_hour_of_the_day": m.incident_hour,
        "number_of_vehicles_involved": m.number_of_vehicles,
        "property_damage": yes_no(m.property_damage),
        "bodily_injuries": m.injuries,
        "witnesses": m.witnesses,
        "police_report_available": yes_no(m.police_report),
        "total_claim_amount": m.total_claim_amount_inr,
        "injury_claim": m.injury_claim_inr,
        "property_claim": m.property_claim_inr,
        # Repair-cost target: what the surveyor assessed, not what the customer asked for.
        "vehicle_claim": m.assessed_repair_cost_inr,
        "auto_make": m.vehicle_make,
        "auto_model": m.vehicle_model,
        "auto_year": m.registration_year,
        "fraud_reported": np.where(m.fraud_outcome.eq("fraud"), "Y", "N"),
    })


def _band(values, edges, labels):
    return pd.cut(values, bins=edges, labels=labels, right=True).astype(str)


def oracle_layout(m):
    """fraud_oracle.csv columns with Indian makes, rupee price bands and Indian policy plans."""
    incident = pd.to_datetime(m.incident_date)
    reported = pd.to_datetime(m.reported_date)
    week = lambda d: ((d.dt.day - 1) // 7 + 1).clip(upper=5)
    days_band = lambda s: _band(s, [-1, 0, 7, 15, 30, 10**6], ["none", "1 to 7", "8 to 15", "15 to 30", "more than 30"])
    return pd.DataFrame({
        "Month": incident.dt.strftime("%b"),
        "WeekOfMonth": week(incident),
        "DayOfWeek": incident.dt.day_name(),
        "Make": m.vehicle_make,
        "AccidentArea": np.where(m.city_tier.lt(3), "Urban", "Rural"),
        "DayOfWeekClaimed": reported.dt.day_name(),
        "MonthClaimed": reported.dt.strftime("%b"),
        "WeekOfMonthClaimed": week(reported),
        "Sex": m.holder_sex,
        "MaritalStatus": m.holder_marital_status,
        "Age": m.holder_age,
        # Who was at fault is settled during the investigation; staged collisions blame the other car.
        "Fault": np.where(m.incident_type.eq("collision") & (m.fraud_scheme.eq("staged_accident") | (m.claim_id.str[-1].astype(int) % 3 == 0)),
                          "Third Party", "Policy Holder"),
        "PolicyType": m.body_style.str.title() + " - " + m.policy_plan,
        "VehicleCategory": m.body_style.str.title(),
        "VehiclePrice": _band(m.ex_showroom_price_inr, [0, 500_000, 800_000, 1_200_000, 2_000_000, 4_000_000, 10**9],
                              ["less than 5 lakh", "5 to 8 lakh", "8 to 12 lakh", "12 to 20 lakh", "20 to 40 lakh", "more than 40 lakh"]),
        "FraudFound_P": m.fraud_outcome.eq("fraud").astype(int),
        "PolicyNumber": np.arange(1, len(m) + 1),
        "RepNumber": (m.garage_id.str[3:].astype(int) % 16) + 1,
        "Deductible": m.deductible_inr,
        "DriverRating": np.clip(4 - m.past_claims_count, 1, 4),
        "Days_Policy_Accident": days_band(m.days_policy_to_incident),
        "Days_Policy_Claim": days_band(m.days_policy_to_incident + m.reporting_delay_days),
        "PastNumberOfClaims": _band(m.past_claims_count, [-1, 0, 1, 4, 10**6], ["none", "1", "2 to 4", "more than 4"]),
        "AgeOfVehicle": _band(m.vehicle_age_years, [-1, 0, 2, 3, 4, 5, 6, 7, 100],
                              ["new", "2 years", "3 years", "4 years", "5 years", "6 years", "7 years", "more than 7"]),
        "AgeOfPolicyHolder": _band(m.holder_age, [0, 25, 30, 35, 40, 50, 65, 200],
                                   ["21 to 25", "26 to 30", "31 to 35", "36 to 40", "41 to 50", "51 to 65", "over 65"]),
        "PoliceReportFiled": np.where(m.police_report.astype(bool), "Yes", "No"),
        "WitnessPresent": np.where(m.witnesses.gt(0), "Yes", "No"),
        "AgentType": np.where(m.claim_id.str[-2:].astype(int) % 20 == 0, "Internal", "External"),
        "NumberOfSuppliments": _band(m.supplementary_estimates, [-1, 0, 2, 5, 10**6], ["none", "1 to 2", "3 to 5", "more than 5"]),
        "AddressChange_Claim": np.where(m.address_changed_recently.astype(bool), "under 6 months", "no change"),
        "NumberOfCars": "1 vehicle",
        "Year": incident.dt.year,
        "BasePolicy": m.policy_plan,
    })


def vehicle_fraud_layout(m):
    """Feature columns of apps/assessments/vehicle_fraud.py plus fraud_outcome."""
    incident_hour = m.incident_hour
    return pd.DataFrame({
        "claim_id": m.claim_id,
        "vehicle_age_years": m.vehicle_age_years,
        "claim_amount_inr": m.total_claim_amount_inr,
        "claim_to_repair_ratio": (m.total_claim_amount_inr / m.app_repair_estimate_inr).round(4),
        "claim_to_vehicle_price_ratio": (m.total_claim_amount_inr / m.ex_showroom_price_inr).round(4),
        "days_policy_to_incident": m.days_policy_to_incident,
        "reporting_delay_days": m.reporting_delay_days,
        "police_report": m.police_report,
        "witnesses": m.witnesses.gt(0).astype(int),
        "injuries": m.injuries,
        "number_of_vehicles": m.number_of_vehicles,
        "past_claims_count": m.past_claims_count,
        "incident_at_night": ((incident_hour >= 22) | (incident_hour < 5)).astype(int),
        "photo_count": m.photo_count,
        "photos_reused_from_other_claims": m.photos_reused_from_other_claims,
        "photos_taken_before_incident": m.photos_taken_before_incident,
        "photo_days_before_incident": m.photo_days_before_incident,
        "photos_edited": m.photos_edited,
        "photos_without_camera_date": m.photos_without_camera_date,
        "photos_small": m.photos_small,
        "vehicle_make": m.vehicle_make,
        "fuel_type": m.fuel_type,
        "body_style": m.body_style,
        "incident_type": m.incident_type,
        "incident_severity": m.reported_severity,
        "district": m.city,
        "fraud_outcome": m.fraud_outcome,
    })


def main():
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    parser.add_argument("--rows", type=int, default=20_000)
    parser.add_argument("--seed", type=int, default=7)
    parser.add_argument("--out-dir", type=Path, default=Path(__file__).resolve().parent)
    args = parser.parse_args()
    args.out_dir.mkdir(parents=True, exist_ok=True)

    master = simulate(args.rows, args.seed)
    outputs = {
        "india_claims_master.csv": master,
        "india_insurance_claims.csv": insurance_layout(master),
        "india_fraud_oracle.csv": oracle_layout(master),
        "india_vehicle_fraud.csv": vehicle_fraud_layout(master),
    }
    for name, frame in outputs.items():
        frame.to_csv(args.out_dir / name, index=False)
        print(f"{name}: {len(frame)} rows, {frame.shape[1]} columns")
    print(f"Fraud label rate: {master.fraud_outcome.eq('fraud').mean():.3f} "
          f"(true fraud {master.is_fraud_truth.mean():.3f})")


if __name__ == "__main__":
    main()
