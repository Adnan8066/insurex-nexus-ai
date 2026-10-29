from datetime import timedelta
from decimal import Decimal

from django.contrib.auth import get_user_model
from django.test import override_settings
from django.utils import timezone
from rest_framework.test import APITestCase

from apps.assessments.models import ClaimAssessment
from apps.claims.models import Claim
from apps.claims.tests import TEMP_MEDIA, make_customer_records
from apps.investigations.models import Investigation


@override_settings(ALLOWED_HOSTS=['testserver'], SECURE_SSL_REDIRECT=False, MEDIA_ROOT=TEMP_MEDIA)
class InvestigationApiTests(APITestCase):
    @classmethod
    def setUpTestData(cls):
        User = get_user_model()
        cls.employee = User.objects.create_user(username='iemp', email='iemp@example.com', password='x', role='employee')
        cls.investigator = User.objects.create_user(username='iinv', email='iinv@example.com', password='x', role='investigator')
        cls.customer, cls.policy, cls.vehicle = make_customer_records('icust', 'VINTEST0000000041')

        def claim(number, investigator=None):
            return Claim.objects.create(
                claim_number=number, customer=cls.customer, policy=cls.policy, vehicle=cls.vehicle,
                incident_date=timezone.localdate() - timedelta(days=1), incident_type='collision',
                incident_severity='minor', location='x', claim_amount=Decimal('10'), assigned_investigator=investigator,
            )

        cls.assigned_claim = claim('CLM-I1', cls.investigator)
        cls.other_claim = claim('CLM-I2')
        cls.investigation = Investigation.objects.create(
            claim=cls.assigned_claim, investigator=cls.investigator, case_number='INV-I1',
        )
        ClaimAssessment.objects.create(claim=cls.assigned_claim)
        cls.other_assessment = ClaimAssessment.objects.create(claim=cls.other_claim)

    def test_start_and_complete_investigation(self):
        self.client.force_authenticate(self.investigator)
        base = f'/api/v1/investigations/{self.investigation.pk}'
        self.assertEqual(self.client.post(f'{base}/start/').status_code, 200)
        completed = self.client.post(f'{base}/complete/', {'findings': 'Consistent story'}, format='json')
        self.assertEqual(completed.status_code, 200, completed.content)
        self.assertEqual(completed.json()['status'], 'completed')

    def test_notes_and_evidence_support_get_and_post(self):
        self.client.force_authenticate(self.investigator)
        base = f'/api/v1/investigations/{self.investigation.pk}'
        self.assertEqual(self.client.post(f'{base}/notes/', {'content': 'Interviewed driver'}, format='json').status_code, 201)
        self.assertEqual(len(self.client.get(f'{base}/notes/').json()), 1)
        self.assertEqual(self.client.post(f'{base}/evidence/', {'evidence_type': 'document', 'title': 'Statement'}, format='json').status_code, 201)
        self.assertEqual(len(self.client.get(f'{base}/evidence/').json()), 1)

    def test_assessment_review_and_investigator_scope(self):
        self.client.force_authenticate(self.employee)
        review = self.client.post(f'/api/v1/assessments/assessments/{self.other_assessment.pk}/review/')
        self.assertEqual(review.status_code, 200, review.content)
        self.client.force_authenticate(self.investigator)
        listed = self.client.get('/api/v1/assessments/assessments/').json()
        self.assertEqual([row['claim'] for row in listed['results']], [self.assigned_claim.pk])
        self.assertEqual(self.client.post('/api/v1/ai/detect-fraud/', {'claim_id': self.other_claim.pk}, format='json').status_code, 404)
