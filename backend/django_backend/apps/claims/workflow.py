"""Claim status workflow rules shared by every endpoint that changes Claim.status."""
from common.risk import FRAUD_HIGH_THRESHOLD

from .models import ClaimStatus

# Only these roles may record a coverage decision on a claim.
DECISION_ROLES = {'employee', 'admin'}
DECISION_STATUSES = {ClaimStatus.APPROVED, ClaimStatus.REJECTED}
# A claim must be reviewed (moved out of these statuses) before it can be approved.
NOT_APPROVABLE_FROM = {ClaimStatus.SUBMITTED, ClaimStatus.INVESTIGATION}
COMPLETED_INVESTIGATION_STATUSES = {'completed', 'closed'}


class TransitionError(Exception):
    def __init__(self, message, status_code=409):
        super().__init__(message)
        self.message = message
        self.status_code = status_code


def is_high_risk(claim):
    return float(claim.fraud_risk_score or 0) > FRAUD_HIGH_THRESHOLD


def has_completed_investigation(claim):
    from apps.investigations.models import Investigation
    return Investigation.objects.filter(
        claim=claim, status__in=COMPLETED_INVESTIGATION_STATUSES,
    ).exists()


def check_transition(claim, new_status, user):
    """Raise TransitionError if ``user`` may not move ``claim`` to ``new_status``."""
    old_status = claim.status
    if new_status in DECISION_STATUSES and getattr(user, 'role', None) not in DECISION_ROLES:
        raise TransitionError('Only insurance employees or administrators can approve or reject claims.', 403)
    if new_status == ClaimStatus.APPROVED and old_status != ClaimStatus.APPROVED:
        if old_status in NOT_APPROVABLE_FROM:
            raise TransitionError(
                f'A claim cannot be approved while its status is "{dict(ClaimStatus.choices).get(old_status, old_status)}". '
                'Move it to Under Review once the review/investigation is finished.'
            )
        if is_high_risk(claim) and not has_completed_investigation(claim):
            raise TransitionError(
                f'This claim has a high fraud risk score (above {FRAUD_HIGH_THRESHOLD}). '
                'It must be assigned to an investigator and the investigation completed before approval.'
            )
