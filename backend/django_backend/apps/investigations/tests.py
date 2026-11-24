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
        # A completed case cannot be restarted.
        self.assertEqual(self.client.post(f'{base}/start/').status_code, 400)

    def test_complete_requires_start_and_findings(self):
        self.client.force_authenticate(self.investigator)
        base = f'/api/v1/investigations/{self.investigation.pk}'
        not_started = self.client.post(f'{base}/complete/', {'findings': 'x'}, format='json')
        self.assertEqual(not_started.status_code, 400)
        self.client.post(f'{base}/start/')
        no_findings = self.client.post(f'{base}/complete/', {'findings': '   '}, format='json')
        self.assertEqual(no_findings.status_code, 400)
        self.assertIn('findings', no_findings.json())
        self.investigation.refresh_from_db()
        self.assertEqual(self.investigation.status, 'in_progress')

    def test_notes_and_evidence_support_get_and_post(self):
        self.client.force_authenticate(self.investigator)
        base = f'/api/v1/investigations/{self.investigation.pk}'
        self.assertEqual(self.client.post(f'{base}/notes/', {'content': 'Interviewed driver'}, format='json').status_code, 201)
        self.assertEqual(len(self.client.get(f'{base}/notes/').json()), 1)
        self.assertEqual(self.client.post(f'{base}/evidence/', {'evidence_type': 'document', 'title': 'Statement'}, format='json').status_code, 201)
        self.assertEqual(len(self.client.get(f'{base}/evidence/').json()), 1)

    def test_vehicle_checks_recorded_by_assigned_investigator_and_visible_to_staff(self):
        base = f'/api/v1/investigations/{self.investigation.pk}/vehicle-checks/'
        self.client.force_authenticate(self.investigator)
        checks = [
            {'check_code': 'vin_matches', 'result': 'pass'},
            {'check_code': 'damage_matches_incident', 'result': 'fail', 'note': 'Rear damage, claim says front'},
        ]
        saved = self.client.post(base, {'checks': checks}, format='json')
        self.assertEqual(saved.status_code, 200, saved.content)
        self.assertEqual(saved.json()['completed'], 2)
        self.assertEqual(saved.json()['total'], 10)

        # Re-saving updates the same row rather than adding a duplicate.
        self.client.post(base, {'checks': [{'check_code': 'vin_matches', 'result': 'fail'}]}, format='json')
        self.assertEqual(self.investigation.vehicle_checks.filter(check_code='vin_matches').count(), 1)

        # Employees and admins can read the results but not change them.
        self.client.force_authenticate(self.employee)
        viewed = self.client.get(base)
        self.assertEqual(viewed.status_code, 200)
        by_code = {row['check_code']: row for row in viewed.json()['checks']}
        self.assertEqual(by_code['damage_matches_incident']['result'], 'fail')
        self.assertEqual(by_code['damage_matches_incident']['checked_by_name'], self.investigator.get_full_name())
        self.assertIsNone(by_code['photos_taken']['result'])
        self.assertEqual(self.client.post(base, {'checks': checks}, format='json').status_code, 403)

    def test_vehicle_checks_reject_unknown_codes_and_closed_cases(self):
        base = f'/api/v1/investigations/{self.investigation.pk}/vehicle-checks/'
        self.client.force_authenticate(self.investigator)
        bad = self.client.post(base, {'checks': [{'check_code': 'not_a_check', 'result': 'pass'}]}, format='json')
        self.assertEqual(bad.status_code, 400)
        self.investigation.status = 'completed'
        self.investigation.save(update_fields=['status'])
        closed = self.client.post(base, {'checks': [{'check_code': 'vin_matches', 'result': 'pass'}]}, format='json')
        self.assertEqual(closed.status_code, 400)

    def test_completion_records_outcome_and_updates_claim_fraud_outcome(self):
        self.client.force_authenticate(self.investigator)
        base = f'/api/v1/investigations/{self.investigation.pk}'
        self.client.post(f'{base}/start/')
        bad = self.client.post(f'{base}/complete/', {'findings': 'x', 'investigation_outcome': 'maybe'}, format='json')
        self.assertEqual(bad.status_code, 400)
        self.investigation.refresh_from_db()
        self.assertEqual(self.investigation.status, 'in_progress')  # rejected outcome saves nothing

        done = self.client.post(f'{base}/complete/', {
            'findings': 'Damage does not match the incident', 'investigation_outcome': 'confirmed_fraud',
            'outcome_notes': 'Rear damage predates the claim',
        }, format='json')
        self.assertEqual(done.status_code, 200, done.content)
        body = done.json()
        self.assertEqual(body['investigation_outcome'], 'confirmed_fraud')
        self.assertIsNotNone(body['outcome_reviewed_at'])
        self.assertIn('triage_priority_score', body)
        self.assertTrue(body['heuristic_version'])
        self.assigned_claim.refresh_from_db()
        self.assertEqual(self.assigned_claim.fraud_outcome, 'fraud')
        self.assertEqual(self.assigned_claim.fraud_outcome_note, 'Rear damage predates the claim')

    def test_completion_without_outcome_leaves_it_pending(self):
        self.client.force_authenticate(self.investigator)
        base = f'/api/v1/investigations/{self.investigation.pk}'
        self.client.post(f'{base}/start/')
        done = self.client.post(f'{base}/complete/', {'findings': 'Checked'}, format='json')
        self.assertEqual(done.status_code, 200, done.content)
        self.assertEqual(done.json()['investigation_outcome'], 'pending')
        self.assigned_claim.refresh_from_db()
        self.assertEqual(self.assigned_claim.fraud_outcome, '')

    def test_assessment_review_and_investigator_scope(self):
        self.client.force_authenticate(self.employee)
        review = self.client.post(f'/api/v1/assessments/assessments/{self.other_assessment.pk}/review/')
        self.assertEqual(review.status_code, 200, review.content)
        self.client.force_authenticate(self.investigator)
        listed = self.client.get('/api/v1/assessments/assessments/').json()
        self.assertEqual([row['claim'] for row in listed['results']], [self.assigned_claim.pk])
        self.assertEqual(self.client.post('/api/v1/ai/detect-fraud/', {'claim_id': self.other_claim.pk}, format='json').status_code, 404)
