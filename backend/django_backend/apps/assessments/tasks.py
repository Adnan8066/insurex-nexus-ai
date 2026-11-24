"""Background claim scoring.

FNOL should not wait for the models, so new claims are scored on the Celery worker.
If the broker is unavailable, the claim is scored in the request instead, so a
queue outage never blocks a claim from being saved.
"""
import logging

from django.db.utils import OperationalError

from common.tasks import CELERY_INSTALLED, shared_task

from .models import AssessmentStatus, ClaimAssessment

logger = logging.getLogger(__name__)


@shared_task(autoretry_for=(OperationalError,), retry_backoff=True, max_retries=3)
def score_claim_async(claim_id):
    """Score one claim, unless it already has a completed score since it was submitted.

    Returns the new assessment id, or None if the claim was skipped or not found.
    """
    from apps.claims.models import Claim
    from .ai_views import run_claim_assessment

    claim = Claim.objects.filter(pk=claim_id).first()
    if claim is None:
        return None
    already_scored = ClaimAssessment.objects.filter(
        claim=claim, status=AssessmentStatus.COMPLETED, assessed_at__gte=claim.submitted_at,
    ).exists()
    if already_scored:
        logger.info('Claim %s already scored since submission; skipping', claim.claim_number)
        return None
    assessment = run_claim_assessment(claim)
    return getattr(assessment, 'pk', None)


def enqueue_claim_scoring(claim_id):
    """Queue scoring on the worker. If the queue cannot be reached, score inline."""
    if not CELERY_INSTALLED:
        # No queue in this environment: run here. Errors propagate to the caller as usual.
        score_claim_async(claim_id)
        return 'inline'
    try:
        score_claim_async.delay(claim_id)
        return 'queued'
    except Exception:
        # Only the send to the broker is retried inline; a failure inside scoring is not.
        logger.warning('Task queue unavailable; scoring claim %s inline', claim_id, exc_info=True)
        score_claim_async(claim_id)
        return 'inline'
