"""Plain-language explanations of a claim's AI scores.

Staff see three numbers on every claim (repair cost, fraud score, write-off chance).
This module turns the signals behind them into short sentences a claims handler or
manager can read without knowing the models, for example:

    Fraud score 72 of 100 (high risk), mainly because the policy started 10 days
    before the incident, the claim was reported 9 days late and 1 photo was
    already used on another claim.

Nothing here changes a score; it only describes the inputs that produced it.
"""
import re

from common.risk import fraud_risk_band

MAX_FRAUD_REASONS = 3

# Model features that describe the same thing as a red flag. When the red flag is
# present its sentence is used, so the summary never says the same thing twice.
_SAME_AS_RED_FLAG = {
    'reporting_delay_days': {'late_report'},
    'days_policy_to_incident': {'new_policy'},
    'claim_to_repair_ratio': {'amount_over_estimate'},
    'claim_to_vehicle_price_ratio': {'amount_over_vehicle_price'},
    'past_claims_count': {'frequent_claims', 'repeat_vehicle'},
    'police_report': {'theft_without_police_report', 'injury_without_police_report'},
    'police_report_available': {'theft_without_police_report', 'injury_without_police_report'},
}

_SEVERITY_WORDS = {
    'minor': 'minor', 'moderate': 'moderate', 'major': 'major', 'total_loss': 'total-loss',
    'Trivial Damage': 'minor', 'Minor Damage': 'moderate', 'Major Damage': 'major', 'Total Loss': 'total-loss',
}


_SEGMENT_WORDS = {'hatchback/sedan': 'a hatchback or sedan', 'suv/muv': 'an SUV or MUV'}


def _number(value):
    try:
        return float(value)
    except (TypeError, ValueError):
        return None


def _count(value, one, many):
    n = int(_number(value) or 0)
    return f"{n} {one if n == 1 else many}"


def rupees(value):
    """Indian digit grouping: 1234567 -> ₹12,34,567."""
    amount = int(round(float(value)))
    sign, digits = ('-', str(-amount)) if amount < 0 else ('', str(amount))
    if len(digits) > 3:
        head, tail = digits[:-3], digits[-3:]
        groups = []
        while len(head) > 2:
            groups.insert(0, head[-2:])
            head = head[:-2]
        if head:
            groups.insert(0, head)
        digits = ','.join(groups + [tail])
    return f"{sign}₹{digits}"


def _model_reason_phrase(feature, value):
    """A model input that raised the fraud score, as a clause ('the car is 9 years old')."""
    n = _number(value)
    phrases = {
        'days_policy_to_incident': lambda: f"the policy started only {_count(n, 'day', 'days')} before the incident",
        'reporting_delay_days': lambda: f"the claim was reported {_count(n, 'day', 'days')} after the incident",
        'claim_to_repair_ratio': lambda: f"the amount claimed is {n:.1f} times the expected repair cost",
        'claim_to_vehicle_price_ratio': lambda: f"the amount claimed is {n:.0%} of the car's price",
        'claim_amount_inr': lambda: f"the amount claimed is high ({rupees(n)})",
        'total_claim_amount': lambda: f"the amount claimed is high ({rupees(n)})",
        'vehicle_age_years': lambda: f"the car is {_count(n, 'year', 'years')} old",
        'auto_year': lambda: f"the car was made in {int(n)}",
        'past_claims_count': lambda: f"the customer has {_count(n, 'earlier claim', 'earlier claims')}",
        'photos_reused_from_other_claims': lambda: f"{_count(n, 'photo was', 'photos were')} already used on another claim",
        'photos_taken_before_incident': lambda: f"{_count(n, 'photo was', 'photos were')} taken before the incident date",
        'photo_days_before_incident': lambda: f"a photo is {_count(n, 'day', 'days')} older than the incident",
        'photos_edited': lambda: f"{_count(n, 'photo was', 'photos were')} edited in an app",
        'photos_without_camera_date': lambda: f"{_count(n, 'photo has', 'photos have')} no camera date",
        'photos_small': lambda: f"{_count(n, 'photo is', 'photos are')} very low resolution",
        'photo_count': lambda: "no photos were submitted" if not n else f"only {_count(n, 'photo was', 'photos were')} submitted",
        'number_of_vehicles': lambda: f"{_count(n, 'vehicle was', 'vehicles were')} involved",
        'number_of_vehicles_involved': lambda: f"{_count(n, 'vehicle was', 'vehicles were')} involved",
        'bodily_injuries': lambda: f"{_count(n, 'injury was', 'injuries were')} reported",
    }
    flags = {
        'incident_at_night': ("the incident happened at night", None),
        'injuries': ("injuries were reported", None),
        'witnesses': ("there were witnesses", "there were no witnesses"),
        'police_report': ("a police report was filed", "no police report was filed"),
        'police_report_available': ("a police report was filed", "no police report was filed"),
        'property_damage': ("other property was damaged", None),
    }
    # A small ratio can still match past fraud cases, but "3% of the car's price" reads like
    # reassurance, so it is described without the number.
    if feature == 'claim_to_repair_ratio' and n is not None and n < 1.2:
        return "the amount claimed compared with the expected repair cost matches past fraud cases"
    if feature == 'claim_to_vehicle_price_ratio' and n is not None and n < 0.5:
        return "the amount claimed compared with the car's price matches past fraud cases"
    if feature in flags:
        yes, no = flags[feature]
        truthy = str(value).strip().upper() in {'1', '1.0', 'TRUE', 'YES', 'Y'}
        return yes if truthy else no
    if feature in phrases and n is not None:
        return phrases[feature]()
    labels = {
        'incident_type': 'the type of incident', 'incident_severity': 'the damage reported',
        'vehicle_make': 'the car make', 'auto_make': 'the car make', 'auto_model': 'the car model',
        'body_style': 'the body style', 'fuel_type': 'the fuel type', 'district': 'the location',
        'policy_deductable': 'the deductible', 'policy_annual_premium': 'the premium', 'age': 'the policyholder age',
    }
    label = labels.get(feature, feature.replace('_', ' '))
    shown = _SEVERITY_WORDS.get(value, value)
    return f"{label} ({shown}) matches past fraud cases"


# Red flag messages (fraud_rules.py) as clauses; {n} is the first number in the message.
_RED_FLAG_CLAUSES = {
    'new_policy': 'the incident happened only {n} days after the policy started',
    'policy_ending': 'the incident happened {n} days before the policy ends',
    'late_report': 'the claim was reported {n} days after the incident',
    'frequent_claims': 'the customer made {n} other claims in the past 12 months',
    'repeat_vehicle': 'the same car had {n} other {claims} within 6 months',
    'amount_over_estimate': 'the amount claimed is {n} times the repair estimate',
    'amount_over_vehicle_price': "the amount claimed is more than the car's purchase price",
    'theft_without_police_report': 'a theft was reported without a police report',
    'injury_without_police_report': 'injuries were reported without a police report',
    'recent_policy_change': 'the policy was changed {n} days before the incident',
}


def _red_flag_clause(flag):
    message = flag.get('message', '')
    template = _RED_FLAG_CLAUSES.get(flag.get('code'))
    number = re.search(r'\d+(?:\.\d+)?', message)
    if template and ('{n}' not in template or number):
        n = number.group() if number else ''
        return template.format(n=n, claims='claim' if n == '1' else 'claims')
    return message[:1].lower() + message[1:]


def _join(clauses):
    if len(clauses) <= 1:
        return ''.join(clauses)
    return f"{', '.join(clauses[:-1])} and {clauses[-1]}"


def fraud_reasons(fraud_score):
    """Reasons that raised the fraud score, largest first, red flags before model reasons."""
    flags = fraud_score.get('red_flags') or []
    flag_codes = {flag.get('code') for flag in flags}
    reasons = [
        {'text': flag['message'], 'clause': _red_flag_clause(flag),
         'points': float(flag.get('points') or 0), 'source': 'claim history'}
        for flag in flags
    ]
    for item in fraud_score.get('explanations') or []:
        feature = item.get('feature', '')
        if _SAME_AS_RED_FLAG.get(feature, set()) & flag_codes:
            continue
        clause = _model_reason_phrase(feature, item.get('value'))
        if not clause:
            continue
        source = 'photos' if feature.startswith('photo') else 'AI model'
        reasons.append({'text': clause[0].upper() + clause[1:], 'clause': clause,
                        'points': float(item.get('points') or 0), 'source': source})
    reasons.sort(key=lambda reason: reason['points'], reverse=True)
    return reasons


def explain_fraud(fraud_score):
    score = float(fraud_score.get('score') or 0)
    band = fraud_risk_band(score)
    reasons = fraud_reasons(fraud_score)
    top = [reason['clause'] for reason in reasons[:MAX_FRAUD_REASONS]]
    head = f"Fraud score {score:.0f} of 100 ({band} risk)"
    if top and band == 'low':
        summary = f"{head}. Nothing serious stands out (minor points: {_join(top)})."
    elif top:
        summary = f"{head}, mainly because {_join(top)}."
    elif band == 'low':
        summary = f"{head}: nothing in this claim stands out from genuine claims."
    else:
        summary = f"{head}: the overall pattern resembles past fraud cases, but no single detail stands out."
    return {
        'summary': summary,
        'reasons': [{key: reason[key] for key in ('text', 'points', 'source')} for reason in reasons],
    }


def explain_repair_cost(claim, predicted_cost):
    cost = _number(predicted_cost.get('cost'))
    if cost is None:
        return {'summary': 'No repair cost estimate is available for this claim.', 'details': []}
    breakdown = predicted_cost.get('breakdown') or {}
    details = []
    if breakdown.get('constructive_total_loss'):
        idv = breakdown.get('insured_declared_value')
        summary = (f"Estimated payout {rupees(cost)}: the repair would cost more than 75% of the car's "
                   f"insured value ({rupees(idv)}), so it is treated as a write-off.")
    elif 'labour' in breakdown and 'parts' in breakdown:
        severity = _SEVERITY_WORDS.get(breakdown.get('severity'), breakdown.get('severity') or '')
        car = _SEGMENT_WORDS.get(breakdown.get('segment'), 'a car')
        summary = (f"Estimated repair {rupees(cost)} = garage labour {rupees(breakdown['labour'])} + parts "
                   f"{rupees(breakdown['parts'])}, for {severity} damage to {car} "
                   f"that costs {rupees(breakdown.get('ex_showroom_price', 0))} new.")
        if predicted_cost.get('time_estimate'):
            details.append(f"Typical repair time: {_count(predicted_cost['time_estimate'], 'day', 'days')}.")
    else:
        summary = f"Estimated repair {rupees(cost)}, predicted by the AI model from similar past claims."
    claimed = _number(getattr(claim, 'claim_amount', None))
    if claimed and cost:
        ratio = claimed / cost
        if ratio >= 1.5:
            details.append(f"The customer claimed {rupees(claimed)}, {ratio:.1f} times this estimate. Check the bill.")
        elif ratio <= 0.67:
            details.append(f"The customer claimed {rupees(claimed)}, well below this estimate.")
        else:
            details.append(f"The customer claimed {rupees(claimed)}, in line with this estimate.")
    return {'summary': summary, 'details': details}


def explain_total_loss(claim, probability, predicted_cost):
    p = _number(probability)
    if p is None:
        return {'summary': 'No write-off estimate is available for this claim.', 'details': []}
    outlook = 'likely a write-off' if p > 50 else 'possibly a write-off' if p > 25 else 'likely repairable'
    details = []
    severity = _SEVERITY_WORDS.get(getattr(claim, 'incident_severity', None))
    if severity:
        details.append(f"The customer reported {severity} damage.")
    vehicle = getattr(claim, 'vehicle', None)
    year = getattr(vehicle, 'year', None)
    incident = getattr(claim, 'incident_date', None)
    if year and incident:
        details.append(f"The car is {_count(max(0, incident.year - year), 'year', 'years')} old.")
    if (predicted_cost.get('breakdown') or {}).get('constructive_total_loss'):
        details.append("The estimated repair is above 75% of the car's insured value.")
    return {'summary': f"{p:.0f}% chance the car is a write-off ({outlook}).", 'details': details}


def explain_assessment(claim, predicted_cost, fraud_score, total_loss):
    """The explanation stored on a ClaimAssessment: one summary per score."""
    fraud = explain_fraud(fraud_score)
    cost = explain_repair_cost(claim, predicted_cost)
    loss = explain_total_loss(claim, total_loss.get('probability'), predicted_cost)
    return {
        'summary': ' '.join(part['summary'] for part in (fraud, cost, loss)),
        'fraud': fraud,
        'repair_cost': cost,
        'total_loss': loss,
    }
