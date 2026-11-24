"""Motor premium estimates using the IRDAI-style structure from the product spec.

All rates come from settings.POLICY_RATING_TABLES. Items marked SPEC are from the
product spec; items marked PLACEHOLDER are not and must be replaced with approved
insurer data before these quotes are used for real contracts.

Premium lines (each rounded to paise, then summed):
  TP premium        fixed by engine capacity (cc)                    [SPEC]
  CPA premium       owner-driver personal accident cover             [PLACEHOLDER amount]
  OD premium        IDV x OD rate                                    [rate PLACEHOLDER, range SPEC]
  NCB discount      OD premium x NCB %, OD part only                 [SPEC]
  Add-ons           % of IDV or fixed rupees                         [PLACEHOLDER prices]
  GST               18% of the subtotal                              [SPEC]
"""

from dataclasses import dataclass
from datetime import date
from decimal import Decimal, ROUND_HALF_UP

from django.conf import settings

CENT = Decimal('0.01')

# Deductible per plan (policy_type). Third-party-only has no own-damage cover, so none.
PLAN_DEDUCTIBLE = {'auto_liability': Decimal('0'), 'auto_comprehensive': Decimal('1000'), 'auto_collision': Decimal('1000')}
# Which premium parts each plan includes.
PLAN_INCLUDES = {
    'auto_liability': {'tp': True, 'od': False},
    'auto_comprehensive': {'tp': True, 'od': True},
    # Standalone OD needs a separate third-party policy, so no TP premium here.
    'auto_collision': {'tp': False, 'od': True},
}


@dataclass(frozen=True)
class PremiumQuote:
    premium: Decimal
    breakdown: dict

    def as_dict(self):
        return self.breakdown


def _tables():
    return settings.POLICY_RATING_TABLES


def _money(value):
    return Decimal(str(value)).quantize(CENT, rounding=ROUND_HALF_UP)


def tp_premium(engine_cc):
    """IRDAI-fixed third-party premium by engine capacity (SPEC)."""
    if engine_cc is None or int(engine_cc) <= 0:
        raise ValueError('Engine capacity (cc) is needed to price the third-party premium.')
    cc = int(engine_cc)
    tp = _tables()['tp_premium']
    if cc < 1000:
        return _money(tp['under_1000'])
    if cc <= 1500:
        return _money(tp['from_1000_to_1500'])
    return _money(tp['above_1500'])


def depreciation_rate(age_years):
    """Share of ex-showroom price lost to age (SPEC slabs)."""
    table = _tables()['depreciation']
    if age_years in table:
        return Decimal(str(table[age_years]))
    return Decimal(str(_tables()['depreciation_max']))


def idv_for(ex_showroom_price, vehicle_year, today=None):
    """Insured declared value = ex-showroom price x (1 - depreciation)."""
    today = today or date.today()
    age = max(0, today.year - int(vehicle_year))
    rate = depreciation_rate(age)
    return _money(Decimal(str(ex_showroom_price)) * (Decimal('1') - rate)), age, rate


def ncb_rate(years):
    """No-claim bonus share for consecutive claim-free years (SPEC)."""
    table = _tables()['ncb']
    years = min(int(years), max(table))
    return Decimal(str(table[years]))


def zone_for(registration_city):
    """Zone A for listed metro cities, otherwise Zone B (PLACEHOLDER city list)."""
    city = (registration_city or '').strip().lower()
    return 'A' if city in _tables()['zone_a_cities'] else 'B'


def calculate_premium(*, policy_type, ex_showroom_price, vehicle_year, engine_cc,
                      registration_city='', ncb_years=0, add_ons=(), today=None):
    """Return a PremiumQuote with every line of the 1-year premium."""
    if policy_type not in PLAN_INCLUDES:
        raise ValueError('Unsupported policy type.')
    if ex_showroom_price is None or Decimal(str(ex_showroom_price)) <= 0:
        raise ValueError('The vehicle needs an ex-showroom price before a premium can be calculated.')
    if vehicle_year is None:
        raise ValueError('The vehicle needs a model year before a premium can be calculated.')
    try:
        ncb_years = int(ncb_years or 0)
    except (TypeError, ValueError):
        raise ValueError('No-claim years must be a whole number from 0 to 5.')
    if not 0 <= ncb_years <= 5:
        raise ValueError('No-claim years must be from 0 to 5.')

    tables = _tables()
    includes = PLAN_INCLUDES[policy_type]
    idv, age, dep_rate = idv_for(ex_showroom_price, vehicle_year, today=today)
    lines = []

    if includes['tp']:
        lines.append({'label': 'Third-party premium', 'amount': tp_premium(engine_cc)})
        lines.append({'label': 'Compulsory personal accident cover', 'amount': _money(tables['cpa_premium'])})

    od_info = {}
    if includes['od']:
        zone = zone_for(registration_city)
        od_rate = Decimal(str(tables['od_rate'][zone]))
        od_premium = _money(idv * od_rate)
        ncb_pct = ncb_rate(ncb_years)
        ncb_amount = _money(od_premium * ncb_pct)
        lines.append({'label': f'Own-damage premium (IDV x {od_rate * 100:.1f}%)', 'amount': od_premium})
        lines.append({'label': f'No-claim bonus discount ({ncb_pct * 100:.0f}%, own-damage only)', 'amount': -ncb_amount})
        od_info = {'zone': zone, 'od_rate': str(od_rate), 'ncb_years': ncb_years, 'ncb_percent': str(ncb_pct)}

        addon_table = tables['addons']
        for code in add_ons or []:
            if code not in addon_table:
                raise ValueError(f'Unknown add-on: {code}')
            price = addon_table[code]
            if 'percent' in price:
                amount = _money(idv * Decimal(str(price['percent'])))
            else:
                amount = _money(price['fixed'])
            lines.append({'label': f'Add-on: {code.replace("_", " ")}', 'amount': amount})

    subtotal = sum((line['amount'] for line in lines), Decimal('0.00'))
    gst = _money(subtotal * Decimal(str(tables['gst_rate'])))
    total = subtotal + gst
    lines.append({'label': f'GST ({Decimal(str(tables["gst_rate"])) * 100:.0f}%)', 'amount': gst})

    breakdown = {
        'rating_version': tables['rating_version'],
        'estimate_only': True,
        # Every quote says where its rates come from, so demo figures are never shown as filed tariffs.
        'tariff_source': 'INDICATIVE_DEMO_TARIFF',
        'idv': str(idv),
        'vehicle_age_years': age,
        'depreciation_percent': str(dep_rate * 100),
        'deductible': str(PLAN_DEDUCTIBLE[policy_type]),
        'lines': [{'label': line['label'], 'amount': str(line['amount'])} for line in lines],
        'subtotal': str(subtotal),
        'total': str(total),
        **od_info,
    }
    return PremiumQuote(premium=total, breakdown=breakdown)
