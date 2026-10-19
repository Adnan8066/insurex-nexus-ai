"""Configurable, transparent policy premium estimates.

The default factors are demonstration assumptions, not approved insurer rates.
Production deployments must provide an actuarially approved rate table.
"""

from dataclasses import dataclass
from decimal import Decimal, ROUND_HALF_UP

from django.conf import settings


@dataclass(frozen=True)
class PremiumQuote:
    premium: Decimal
    base_premium: Decimal
    risk_loading: Decimal
    deductible_credit: Decimal
    rating_version: str

    def as_dict(self):
        return {
            "premium": str(self.premium),
            "base_premium": str(self.base_premium),
            "risk_loading": str(self.risk_loading),
            "deductible_credit": str(self.deductible_credit),
            "rating_version": self.rating_version,
            "estimate_only": True,
        }


def calculate_premium(*, coverage_limit, deductible, risk_score) -> PremiumQuote:
    """Calculate an annual estimate using explicit settings and a 0–100 score."""
    coverage = Decimal(str(coverage_limit))
    deductible_value = Decimal(str(deductible))
    risk = Decimal(str(risk_score))
    if coverage <= 0 or deductible_value < 0 or not Decimal("0") <= risk <= Decimal("100"):
        raise ValueError("Coverage must be positive, deductible non-negative, and risk_score between 0 and 100.")

    rate = Decimal(str(getattr(settings, "POLICY_BASE_ANNUAL_RATE", "0.025")))
    deductible_credit_rate = Decimal(str(getattr(settings, "POLICY_DEDUCTIBLE_CREDIT_RATE", "0.20")))
    if rate <= 0 or not Decimal("0") <= deductible_credit_rate <= Decimal("1"):
        raise ValueError("Policy rating settings contain invalid values.")

    base = coverage * rate
    risk_loading = base * risk / Decimal("100")
    deductible_ratio = min(deductible_value / coverage, Decimal("1"))
    deductible_credit = (base + risk_loading) * deductible_ratio * deductible_credit_rate
    premium = max(Decimal("0.01"), base + risk_loading - deductible_credit)
    cents = Decimal("0.01")
    return PremiumQuote(
        premium=premium.quantize(cents, rounding=ROUND_HALF_UP),
        base_premium=base.quantize(cents, rounding=ROUND_HALF_UP),
        risk_loading=risk_loading.quantize(cents, rounding=ROUND_HALF_UP),
        deductible_credit=deductible_credit.quantize(cents, rounding=ROUND_HALF_UP),
        rating_version=getattr(settings, "POLICY_RATING_VERSION", "demo-v1"),
    )
