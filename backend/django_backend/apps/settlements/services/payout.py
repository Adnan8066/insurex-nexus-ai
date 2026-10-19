"""Auditable payout calculations using policy-configured depreciation terms."""

from dataclasses import dataclass
from decimal import Decimal, ROUND_HALF_UP

from django.conf import settings
from django.utils import timezone


@dataclass(frozen=True)
class PayoutCalculation:
    gross_repair_cost: Decimal
    deductible: Decimal
    depreciation: Decimal
    asset_age_years: int
    zero_depreciation_applied: bool
    payout: Decimal

    def as_dict(self):
        return {
            "gross_repair_cost": str(self.gross_repair_cost),
            "deductible": str(self.deductible),
            "depreciation": str(self.depreciation),
            "asset_age_years": self.asset_age_years,
            "zero_depreciation_applied": self.zero_depreciation_applied,
            "payout": str(self.payout),
        }


def calculate_claim_payout(*, repair_cost, deductible, asset_age_years,
                           zero_depreciation=False, annual_depreciation_rate=None,
                           max_depreciation_rate=None) -> PayoutCalculation:
    """Return max(0, repair cost − deductible − age depreciation).

    Rates default to Django settings and are illustrative until replaced with
    approved, product-specific policy terms.
    """
    cost = Decimal(str(repair_cost))
    excess = Decimal(str(deductible))
    age = int(asset_age_years)
    if cost < 0 or excess < 0 or age < 0:
        raise ValueError("Repair cost, deductible, and asset age must be non-negative.")
    annual_rate = Decimal(str(
        annual_depreciation_rate if annual_depreciation_rate is not None
        else getattr(settings, "CLAIM_ANNUAL_DEPRECIATION_RATE", "0.05")
    ))
    maximum_rate = Decimal(str(
        max_depreciation_rate if max_depreciation_rate is not None
        else getattr(settings, "CLAIM_MAX_DEPRECIATION_RATE", "0.80")
    ))
    if not Decimal("0") <= annual_rate <= Decimal("1") or not Decimal("0") <= maximum_rate <= Decimal("1"):
        raise ValueError("Depreciation rates must be between 0 and 1.")
    depreciation_rate = min(annual_rate * age, maximum_rate)
    depreciation = Decimal("0") if zero_depreciation else cost * depreciation_rate
    cents = Decimal("0.01")
    depreciation = depreciation.quantize(cents, rounding=ROUND_HALF_UP)
    payout = max(Decimal("0"), cost - excess - depreciation).quantize(cents, rounding=ROUND_HALF_UP)
    return PayoutCalculation(
        gross_repair_cost=cost.quantize(cents, rounding=ROUND_HALF_UP),
        deductible=excess.quantize(cents, rounding=ROUND_HALF_UP),
        depreciation=depreciation,
        asset_age_years=age,
        zero_depreciation_applied=bool(zero_depreciation),
        payout=payout,
    )


def calculate_payout_for_claim(claim, repair_cost):
    """Apply the claim's linked policy deductible, asset year, and add-on terms."""
    coverage = claim.policy.coverage if isinstance(claim.policy.coverage, dict) else {}
    add_ons = coverage.get('addons', [])
    plan_add_ons = coverage.get('policy_plan', {}).get('addons', [])
    if not isinstance(plan_add_ons, list):
        plan_add_ons = []
    if not isinstance(add_ons, list):
        add_on_names = []
    else:
        add_on_names = add_ons
    zero_depreciation = bool(
        coverage.get('zero_depreciation')
        or (isinstance(add_ons, dict) and add_ons.get('zero_depreciation'))
        or any(
            'zero depreciation' in str(item).lower().replace('-', ' ')
            for item in [*plan_add_ons, *add_on_names]
        )
    )
    current_year = timezone.now().year
    asset_age = max(0, current_year - (claim.vehicle.year or current_year))
    return calculate_claim_payout(
        repair_cost=repair_cost,
        deductible=claim.policy.deductible,
        asset_age_years=asset_age,
        zero_depreciation=zero_depreciation,
    )
