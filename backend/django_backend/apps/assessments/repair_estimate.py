"""Repair-cost estimate for Indian app claims, calibrated to real Indian part and labour prices.

    estimate = body-shop labour for the severity and segment
             + parts share for the severity x ex-showroom (purchase) price

Parts are bought new, so the bill scales with the car's new price, not its depreciated value.
The IDV (insured declared value) is used only to cap the bill: a repair costing more than 75%
of the IDV is settled as a constructive total loss at the IDV, as Indian insurers do.

    IDV = ex-showroom price x (1 - IRDAI depreciation for the vehicle's age)

Calibration (backend/data/india/reference/, collected Nov 2026):
- Parts shares are medians of authorised-dealer part prices with 18% GST, divided by the
  model's ex-showroom price, across 11 models (ZigWheels / CarDekho listings, mostly the
  previous generation of each model):
    minor     small parts and clips only; the job is mostly a repaint
    moderate  1.2%  median of a two-part job (bumper + headlight, door + mirror, rear bumper + tail light)
    major     4.0%  front-end set (bumper + bonnet + headlight) is a 2.0% median; doubled for hidden
                    damage (radiator, condenser, airbags, suspension), which is an assumption
    glass     0.7%  front windshield
- Labour is the middle of the per-panel denting + painting ranges from workshop price guides
  (hatchback/sedan vs SUV/MUV), and the windshield fitting charge with GST.

Depreciation follows the IRDAI motor tariff schedule used to set IDV. The tariff gives no rate
past five years, where IDV is agreed between insurer and insured; 5 more points a year, up to
80%, is an assumption. Replace these figures with settled Indian claims once the app has enough.
"""
from datetime import date

# (vehicle age in months up to and including, depreciation) — IRDAI IDV schedule.
IRDAI_DEPRECIATION = [(6, 0.05), (12, 0.15), (24, 0.20), (36, 0.30), (48, 0.40), (60, 0.50)]
OLD_VEHICLE_EXTRA_PER_YEAR = 0.05
MAX_DEPRECIATION = 0.80

SMALL, LARGE = 'hatchback/sedan', 'suv/muv'
LARGE_BODY_STYLES = ('suv', 'muv', 'mpv', 'crossover', 'pickup', 'van')
# Cars with no body style recorded are treated as SUV/MUV from this ex-showroom price.
LARGE_PRICE_FROM = 1_000_000

# Severity -> (labour in INR by segment, parts as a share of ex-showroom price).
REPAIR_RATES = {
    'minor': ({SMALL: 4_500, LARGE: 6_000}, 0.002),
    'moderate': ({SMALL: 5_000, LARGE: 6_500}, 0.012),
    'major': ({SMALL: 12_000, LARGE: 17_500}, 0.040),
}
# Glass breakage: a windshield, whatever severity was picked.
GLASS_RATE = ({SMALL: 2_360, LARGE: 2_360}, 0.007)
CONSTRUCTIVE_TOTAL_LOSS_SHARE = 0.75
# Working days in the garage per severity (assumption), for the repair-time figure.
REPAIR_DAYS = {'minor': 3, 'moderate': 7, 'major': 21, 'total_loss': None}


class RepairEstimateUnavailable(ValueError):
    """The claim lacks what the estimate needs (vehicle purchase price or year)."""


def vehicle_age_months(vehicle, on_date):
    start = vehicle.purchase_date or (date(vehicle.year, 1, 1) if vehicle.year else None)
    if start is None:
        return None
    return max(0, (on_date.year - start.year) * 12 + on_date.month - start.month)


def depreciation_for_age(months):
    for limit, rate in IRDAI_DEPRECIATION:
        if months <= limit:
            return rate
    extra_years = (months - 60 + 11) // 12
    return min(MAX_DEPRECIATION, 0.50 + extra_years * OLD_VEHICLE_EXTRA_PER_YEAR)


def insured_declared_value(vehicle, on_date):
    if not vehicle or not vehicle.purchase_price:
        raise RepairEstimateUnavailable('The vehicle has no purchase price, so its insured value cannot be worked out.')
    months = vehicle_age_months(vehicle, on_date)
    if months is None:
        raise RepairEstimateUnavailable('The vehicle has no purchase date or year, so its insured value cannot be worked out.')
    depreciation = depreciation_for_age(months)
    return float(vehicle.purchase_price) * (1 - depreciation), depreciation, months


def vehicle_segment(vehicle):
    body = (vehicle.body_style or '').strip().lower()
    if body:
        return LARGE if any(style in body for style in LARGE_BODY_STYLES) else SMALL
    return LARGE if float(vehicle.purchase_price) >= LARGE_PRICE_FROM else SMALL


def estimate_repair_cost(claim):
    """Return the same shape as the model result: cost, breakdown, time_estimate, comparable_count."""
    on_date = claim.incident_date or date.today()
    vehicle = claim.vehicle
    idv, depreciation, months = insured_declared_value(vehicle, on_date)
    price = float(vehicle.purchase_price)
    severity = claim.incident_severity or 'moderate'
    segment = vehicle_segment(vehicle)
    glass = claim.incident_type == 'glass'

    if severity == 'total_loss':
        labour = parts = 0.0
        cost = idv
    else:
        labour_by_segment, parts_share = GLASS_RATE if glass else REPAIR_RATES.get(severity, REPAIR_RATES['moderate'])
        labour = float(labour_by_segment[segment])
        parts = price * parts_share
        cost = labour + parts
    total_loss = severity == 'total_loss' or cost > CONSTRUCTIVE_TOTAL_LOSS_SHARE * idv
    if total_loss:
        cost = idv
    return {
        'cost': round(cost, -2),
        'breakdown': {
            'method': 'Labour + parts share of ex-showroom price (calibrated to Indian part prices, Nov 2026)',
            'ex_showroom_price': round(price, 2),
            'segment': segment,
            'severity': severity,
            'labour': round(labour, -2),
            'parts': round(parts, -2),
            'vehicle_age_months': months,
            'idv_depreciation': depreciation,
            'insured_declared_value': round(idv, 2),
            'constructive_total_loss': total_loss,
        },
        'time_estimate': None if total_loss else (1 if glass else REPAIR_DAYS.get(severity)),
        'comparable_count': None,
    }
