from datetime import timedelta
from decimal import Decimal
from unittest.mock import patch

from django.test import TestCase, override_settings
from django.utils import timezone

from apps.assessments.models import AssessmentStatus, ClaimAssessment
from apps.assessments.tasks import enqueue_claim_scoring, score_claim_async
from apps.claims.models import Claim
from apps.claims.tests import TEMP_MEDIA, make_customer_records


@override_settings(MEDIA_ROOT=TEMP_MEDIA)
class ClaimScoringTaskTests(TestCase):
    @classmethod
    def setUpTestData(cls):
        cls.customer, cls.policy, cls.vehicle = make_customer_records('task-score', 'VINTEST0000000071')

    def make_claim(self, number):
        return Claim.objects.create(
            claim_number=number, customer=self.customer, policy=self.policy, vehicle=self.vehicle,
            incident_date=timezone.localdate() - timedelta(days=1), incident_type='collision',
            incident_severity='minor', location='Kochi', claim_amount=Decimal('10'),
        )

    def test_claim_already_scored_since_submission_is_skipped(self):
        claim = self.make_claim('CLM-TASK-1')
        ClaimAssessment.objects.create(
            claim=claim, status=AssessmentStatus.COMPLETED, assessed_at=timezone.now(),
        )
        with patch('apps.assessments.ai_views.run_claim_assessment') as run:
            self.assertIsNone(score_claim_async(claim.pk))
        run.assert_not_called()

    def test_unscored_claim_is_scored_once(self):
        claim = self.make_claim('CLM-TASK-2')
        with patch('apps.assessments.ai_views.run_claim_assessment') as run:
            run.return_value = ClaimAssessment(pk=99)
            self.assertEqual(score_claim_async(claim.pk), 99)
        run.assert_called_once()

    def test_missing_claim_is_ignored(self):
        with patch('apps.assessments.ai_views.run_claim_assessment') as run:
            self.assertIsNone(score_claim_async(999999))
        run.assert_not_called()

    def test_enqueue_runs_inline_when_no_queue_is_installed(self):
        claim = self.make_claim('CLM-TASK-3')
        with patch('apps.assessments.ai_views.run_claim_assessment') as run:
            run.return_value = ClaimAssessment(pk=7)
            with patch('apps.assessments.tasks.CELERY_INSTALLED', False):
                self.assertEqual(enqueue_claim_scoring(claim.pk), 'inline')
        run.assert_called_once()
