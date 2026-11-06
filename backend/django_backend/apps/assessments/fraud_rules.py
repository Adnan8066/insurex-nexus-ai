"""Rule-based fraud red flags computed from the claim history in the database.

The trained models only see one claim at a time. These checks add the
signals investigators look for across a customer's policy and claim history.
Each flag explains itself; none of them is proof of fraud.
"""
from datetime import timedelta
from decimal import Decimal

from apps.claims.models import Claim
from common.risk import FRAUD_MODERATE_THRESHOLD

NEW_POLICY_DAYS = 30
POLICY_ENDING_DAYS = 15
LATE_REPORT_DAYS = 30
FREQUENT_CLAIMS_WINDOW_DAYS = 365
FREQUENT_CLAIMS_COUNT = 2
REPEAT_VEHICLE_WINDOW_DAYS = 180
RECENT_ENDORSEMENT_DAYS = 30
AMOUNT_OVER_ESTIMATE_RATIO = Decimal('1.5')

# Two independent red flags raise a fraud alert even when the model score is low.
ALERT_MIN_RED_FLAGS = 2

# Score points each red flag adds on top of the model's fraud probability.
# The model only sees one claim, so these carry the history signals it cannot.
# These are hand-picked review-priority weights, not fitted to data.
RED_FLAG_POINTS = {
    'repeat_vehicle': 25,
    'amount_over_vehicle_price': 25,
    'new_policy': 20,
    'frequent_claims': 20,
    'theft_without_police_report': 20,
    'amount_over_estimate': 15,
    'recent_policy_change': 15,
    'policy_ending': 10,
    'late_report': 10,
    'injury_without_police_report': 10,
}
# A rule-boosted score never claims certainty.
MAX_COMBINED_SCORE = 99.0


def _flag(code, message):
    return {'code': code, 'message': message, 'points': RED_FLAG_POINTS.get(code, 0)}


def combined_fraud_score(model_score, flags):
    """Model probability (0-100) plus red-flag points, capped below 100.

    Two or more independent red flags lift the claim to at least the moderate
    band, so a claim the model finds ordinary still gets reviewed.
    """
    score = float(model_score or 0) + sum(flag.get('points', 0) for flag in flags)
    if len(flags) >= ALERT_MIN_RED_FLAGS:
        score = max(score, float(FRAUD_MODERATE_THRESHOLD))
    return round(min(score, MAX_COMBINED_SCORE), 2)


def red_flags(claim):
    """Return the red flags raised by a claim, most specific first."""
    flags = []
    policy = claim.policy
    incident = claim.incident_date

    if policy.start_date and 0 <= (incident - policy.start_date).days <= NEW_POLICY_DAYS:
        days = (incident - policy.start_date).days
        flags.append(_flag('new_policy', f'Incident {days} days after the policy started'))
    if policy.end_date and 0 <= (policy.end_date - incident).days <= POLICY_ENDING_DAYS:
        days = (policy.end_date - incident).days
        flags.append(_flag('policy_ending', f'Incident {days} days before the policy ends'))

    reported = claim.submitted_at.date() if claim.submitted_at else None
    if reported and (reported - incident).days > LATE_REPORT_DAYS:
        flags.append(_flag('late_report', f'Reported {(reported - incident).days} days after the incident'))

    other_claims = Claim.objects.exclude(pk=claim.pk)
    recent_customer_claims = other_claims.filter(
        customer_id=claim.customer_id,
        incident_date__gte=incident - timedelta(days=FREQUENT_CLAIMS_WINDOW_DAYS),
        incident_date__lte=incident,
    ).count()
    if recent_customer_claims >= FREQUENT_CLAIMS_COUNT:
        flags.append(_flag('frequent_claims', f'{recent_customer_claims} other claims by this customer in the past 12 months'))

    if claim.vehicle_id:
        repeat_vehicle_claims = other_claims.filter(
            vehicle_id=claim.vehicle_id,
            incident_date__gte=incident - timedelta(days=REPEAT_VEHICLE_WINDOW_DAYS),
            incident_date__lte=incident + timedelta(days=REPEAT_VEHICLE_WINDOW_DAYS),
        ).count()
        if repeat_vehicle_claims:
            flags.append(_flag('repeat_vehicle', f'{repeat_vehicle_claims} other claim(s) on this vehicle within 6 months'))

    amount = claim.claim_amount or Decimal('0')
    estimate = claim.estimated_repair_cost
    if estimate and amount > estimate * AMOUNT_OVER_ESTIMATE_RATIO:
        flags.append(_flag('amount_over_estimate', f'Claimed amount is {amount / estimate:.1f} times the repair estimate'))
    purchase_price = getattr(claim.vehicle, 'purchase_price', None) if claim.vehicle_id else None
    if purchase_price and amount > purchase_price:
        flags.append(_flag('amount_over_vehicle_price', "Claimed amount is more than the vehicle's purchase price"))

    if claim.incident_type == 'theft' and not claim.police_report:
        flags.append(_flag('theft_without_police_report', 'Theft reported without a police report'))
    if claim.injuries and not claim.police_report:
        flags.append(_flag('injury_without_police_report', 'Injuries reported without a police report'))

    recent_endorsement = policy.endorsements.filter(
        status='approved',
        created_at__date__gte=incident - timedelta(days=RECENT_ENDORSEMENT_DAYS),
        created_at__date__lte=incident,
    ).order_by('-created_at').first()
    if recent_endorsement:
        days = (incident - recent_endorsement.created_at.date()).days
        flags.append(_flag('recent_policy_change', f'Policy was changed {days} days before the incident'))

    return flags


def connected_claims(claim):
    """Other claims that share this claim's vehicle, for the network view."""
    if not claim.vehicle_id:
        return {'connected_claims': 0, 'shared_parties': []}
    numbers = list(
        Claim.objects.exclude(pk=claim.pk)
        .filter(vehicle_id=claim.vehicle_id)
        .order_by('-incident_date')
        .values_list('claim_number', flat=True)[:10]
    )
    return {
        'connected_claims': len(numbers),
        'shared_parties': [{'type': 'vehicle', 'claims': numbers}] if numbers else [],
    }
