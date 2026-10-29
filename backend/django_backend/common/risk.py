"""Shared fraud-risk banding so dashboards and fraud alerts use the same thresholds."""

FRAUD_MODERATE_THRESHOLD = 30
FRAUD_HIGH_THRESHOLD = 65

FRAUD_RISK_BANDS = [
    ('low', f'Low Risk (<{FRAUD_MODERATE_THRESHOLD}%)'),
    ('medium', f'Moderate Risk ({FRAUD_MODERATE_THRESHOLD}-{FRAUD_HIGH_THRESHOLD}%)'),
    ('high', f'High Risk (>{FRAUD_HIGH_THRESHOLD}%)'),
]


def fraud_risk_band(score):
    """Return 'low', 'medium', or 'high' for a 0-100 fraud risk score."""
    score = float(score or 0)
    if score > FRAUD_HIGH_THRESHOLD:
        return 'high'
    if score >= FRAUD_MODERATE_THRESHOLD:
        return 'medium'
    return 'low'
