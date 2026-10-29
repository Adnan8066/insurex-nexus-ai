import io
import shutil
import tempfile
from datetime import timedelta
from decimal import Decimal

from django.contrib.auth import get_user_model
from django.core.files.uploadedfile import SimpleUploadedFile
from django.test import override_settings
from django.utils import timezone
from rest_framework import status
from rest_framework.test import APITestCase

from apps.claims.models import Claim, ClaimNote, ClaimStatus, ClaimStatusHistory
from apps.investigations.models import Investigation
from apps.policies.models import Policy, PolicyStatus
from apps.vehicles.models import Vehicle

TEMP_MEDIA = tempfile.mkdtemp(prefix='claims-tests-media-')


def make_customer_records(username, vin):
    User = get_user_model()
    customer = User.objects.create_user(username=username, email=f'{username}@example.com', password='x', role='customer')
    today = timezone.localdate()
    policy = Policy.objects.create(
        policy_number=f'POL-{username[:10].upper()}', customer=customer, type='auto_comprehensive',
        status=PolicyStatus.ACTIVE, start_date=today - timedelta(days=100), end_date=today + timedelta(days=265),
        premium=Decimal('1000'), deductible=Decimal('100'),
    )
    vehicle = Vehicle.objects.create(
        customer=customer, policy=policy, make='Make', model='Model', year=2020,
        vin=vin, color='Blue', license_plate=f'KA{username[:4]}', license_state='KA',
    )
    policy.vehicle = vehicle
    policy.save(update_fields=['vehicle'])
    return customer, policy, vehicle


@override_settings(ALLOWED_HOSTS=['testserver'], SECURE_SSL_REDIRECT=False, MEDIA_ROOT=TEMP_MEDIA)
class ClaimTestBase(APITestCase):
    @classmethod
    def tearDownClass(cls):
        super().tearDownClass()
        shutil.rmtree(TEMP_MEDIA, ignore_errors=True)

    @classmethod
    def setUpTestData(cls):
        User = get_user_model()
        cls.admin = User.objects.create_user(username='adm', email='adm@example.com', password='x', role='admin')
        cls.employee = User.objects.create_user(username='emp', email='emp@example.com', password='x', role='employee')
        cls.investigator = User.objects.create_user(username='inv', email='inv@example.com', password='x', role='investigator')
        cls.customer, cls.policy, cls.vehicle = make_customer_records('custone', 'VINTEST0000000011')
        cls.customer2, cls.policy2, cls.vehicle2 = make_customer_records('custtwo', 'VINTEST0000000012')

    def make_claim(self, status_value=ClaimStatus.SUBMITTED, fraud=0, **extra):
        return Claim.objects.create(
            claim_number=f'CLM-T{Claim.objects.count() + 1:05d}', customer=self.customer, policy=self.policy,
            vehicle=self.vehicle, incident_date=timezone.localdate() - timedelta(days=2), incident_type='collision',
            incident_severity='minor', location='Somewhere', claim_amount=Decimal('1000'),
            status=status_value, fraud_risk_score=Decimal(fraud), **extra,
        )

    def as_user(self, user):
        self.client.force_authenticate(user)
        return self.client

    def set_status(self, claim, new_status, user=None):
        return self.as_user(user or self.employee).patch(
            f'/api/v1/claims/{claim.pk}/update-status/', {'status': new_status}, format='json',
        )


class ClaimWorkflowTests(ClaimTestBase):
    def test_customer_cannot_change_status_via_status_action(self):
        claim = self.make_claim()
        for new_status in ('approved', 'closed'):
            response = self.as_user(self.customer).patch(
                f'/api/v1/claims/{claim.pk}/status/', {'status': new_status}, format='json',
            )
            self.assertEqual(response.status_code, status.HTTP_403_FORBIDDEN)
        claim.refresh_from_db()
        self.assertEqual(claim.status, ClaimStatus.SUBMITTED)

    def test_cannot_approve_while_submitted_or_in_investigation(self):
        for current in (ClaimStatus.SUBMITTED, ClaimStatus.INVESTIGATION):
            claim = self.make_claim(current)
            response = self.set_status(claim, 'approved')
            self.assertEqual(response.status_code, status.HTTP_409_CONFLICT, response.content)
            self.assertIn('cannot be approved', response.json()['detail'])
            claim.refresh_from_db()
            self.assertEqual(claim.status, current)

    def test_approval_from_under_review_records_history(self):
        claim = self.make_claim(ClaimStatus.UNDER_REVIEW, fraud=10)
        response = self.as_user(self.employee).patch(
            f'/api/v1/claims/{claim.pk}/update-status/', {'status': 'approved', 'reason': 'Docs verified'}, format='json',
        )
        self.assertEqual(response.status_code, status.HTTP_200_OK, response.content)
        history = ClaimStatusHistory.objects.get(claim=claim, to_status='approved')
        self.assertEqual(history.from_status, 'under_review')
        self.assertEqual(history.changed_by, self.employee)
        self.assertEqual(history.reason, 'Docs verified')
        self.assertIsNotNone(history.changed_at)

    def test_high_risk_claim_requires_completed_investigation(self):
        claim = self.make_claim(ClaimStatus.UNDER_REVIEW, fraud=80)
        response = self.set_status(claim, 'approved')
        self.assertEqual(response.status_code, status.HTTP_409_CONFLICT)
        self.assertIn('high fraud risk', response.json()['detail'])
        Investigation.objects.create(
            claim=claim, investigator=self.investigator, case_number='INV-T1', status='in_progress',
        )
        self.assertEqual(self.set_status(claim, 'approved').status_code, status.HTTP_409_CONFLICT)
        Investigation.objects.filter(claim=claim).update(status='completed')
        self.assertEqual(self.set_status(claim, 'approved').status_code, status.HTTP_200_OK)

    def test_generic_patch_cannot_change_status_or_model_outputs(self):
        claim = self.make_claim(fraud=80)
        response = self.as_user(self.employee).patch(f'/api/v1/claims/{claim.pk}/', {'status': 'approved'}, format='json')
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
        response = self.as_user(self.employee).patch(f'/api/v1/claims/{claim.pk}/', {'fraud_risk_score': '1'}, format='json')
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
        claim.refresh_from_db()
        self.assertEqual(claim.status, ClaimStatus.SUBMITTED)
        self.assertEqual(claim.fraud_risk_score, Decimal('80'))

    def test_investigator_cannot_patch_or_delete_claims(self):
        claim = self.make_claim(assigned_investigator=self.investigator)
        client = self.as_user(self.investigator)
        self.assertEqual(client.patch(f'/api/v1/claims/{claim.pk}/', {'location': 'x'}, format='json').status_code, 403)
        self.assertEqual(client.delete(f'/api/v1/claims/{claim.pk}/').status_code, 403)
        self.assertTrue(Claim.objects.filter(pk=claim.pk).exists())

    def test_customer_can_only_edit_or_delete_submitted_claims(self):
        approved = self.make_claim(ClaimStatus.APPROVED)
        client = self.as_user(self.customer)
        self.assertEqual(client.patch(f'/api/v1/claims/{approved.pk}/', {'claim_amount': '99999'}, format='json').status_code, 403)
        self.assertEqual(client.delete(f'/api/v1/claims/{approved.pk}/').status_code, 403)
        submitted = self.make_claim()
        self.assertEqual(client.delete(f'/api/v1/claims/{submitted.pk}/').status_code, 204)
        # Admins keep the ability to remove decided claims.
        self.assertEqual(self.as_user(self.admin).delete(f'/api/v1/claims/{approved.pk}/').status_code, 204)


class ClaimInputValidationTests(ClaimTestBase):
    def claim_payload(self, **overrides):
        payload = {
            'policy': self.policy.pk, 'vehicle': self.vehicle.pk,
            'incident_date': str(timezone.localdate() - timedelta(days=1)), 'incident_type': 'collision',
            'incident_severity': 'minor', 'location': 'Main St', 'claim_amount': '5000',
        }
        payload.update(overrides)
        return payload

    def test_rejects_future_incident_and_non_positive_amount(self):
        client = self.as_user(self.customer)
        future = client.post('/api/v1/claims/', self.claim_payload(incident_date=str(timezone.localdate() + timedelta(days=3))), format='json')
        self.assertEqual(future.status_code, 400)
        self.assertIn('incident_date', future.json()['error']['details'])
        for amount in ('0', '-5'):
            response = client.post('/api/v1/claims/', self.claim_payload(claim_amount=amount), format='json')
            self.assertEqual(response.status_code, 400)
            self.assertIn('claim_amount', response.json()['error']['details'])
        before_term = str(self.policy.start_date - timedelta(days=5))
        self.assertEqual(client.post('/api/v1/claims/', self.claim_payload(incident_date=before_term), format='json').status_code, 400)
        self.assertEqual(client.post('/api/v1/claims/', self.claim_payload(), format='json').status_code, 201)

    def test_malformed_ids_return_400_not_500(self):
        claim = self.make_claim()
        client = self.as_user(self.employee)
        self.assertEqual(client.post(f'/api/v1/claims/{claim.pk}/assign-adjuster/', {'adjuster_id': 'abc'}, format='json').status_code, 400)
        self.assertEqual(client.post(f'/api/v1/claims/{claim.pk}/assign-investigator/', {'investigator_id': 'abc'}, format='json').status_code, 400)
        self.assertEqual(client.post('/api/v1/ai/detect-fraud/', {'claim_id': 'abc'}, format='json').status_code, 400)

    def test_assigned_to_me_and_my_claims_are_paginated(self):
        self.make_claim(assigned_adjuster=self.employee)
        response = self.as_user(self.employee).get('/api/v1/claims/assigned-to-me/')
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.json()['count'], 1)
        response = self.as_user(self.customer).get('/api/v1/claims/my-claims/')
        self.assertEqual(response.status_code, 200)
        self.assertIn('results', response.json())


class ClaimLeakTests(ClaimTestBase):
    def test_customer_does_not_see_internal_notes(self):
        claim = self.make_claim()
        ClaimNote.objects.create(claim=claim, author=self.employee, content='SIU suspicion', is_internal=True)
        ClaimNote.objects.create(claim=claim, author=self.employee, content='We received your photos', is_internal=False)
        client = self.as_user(self.customer)
        detail = client.get(f'/api/v1/claims/{claim.pk}/').json()
        self.assertEqual([note['content'] for note in detail['notes']], ['We received your photos'])
        listed = client.get(f'/api/v1/claims/{claim.pk}/notes/')
        self.assertEqual(listed.status_code, 200)
        self.assertEqual([note['content'] for note in listed.json()], ['We received your photos'])
        created = client.post(f'/api/v1/claims/{claim.pk}/notes/', {'content': 'hi', 'is_internal': True}, format='json')
        self.assertEqual(created.status_code, 201)
        self.assertFalse(created.json()['is_internal'])
        staff_notes = self.as_user(self.employee).get(f'/api/v1/claims/{claim.pk}/notes/').json()
        self.assertEqual(len(staff_notes), 3)

    def test_vehicle_claims_hide_fraud_fields_from_customer(self):
        self.make_claim(fraud=88)
        rows = self.as_user(self.customer).get(f'/api/v1/vehicles/{self.vehicle.pk}/claims/').json()
        self.assertEqual(len(rows), 1)
        for field in ('fraud_risk_score', 'ai_assessment', 'total_loss_probability'):
            self.assertNotIn(field, rows[0])

    def test_customer_cannot_trigger_ai_assessment(self):
        claim = self.make_claim()
        response = self.as_user(self.customer).post(f'/api/v1/claims/{claim.pk}/assessment/', {}, format='json')
        self.assertEqual(response.status_code, 403)

    def test_other_customer_gets_404(self):
        claim = self.make_claim()
        client = self.as_user(self.customer2)
        self.assertEqual(client.get(f'/api/v1/claims/{claim.pk}/').status_code, 404)
        self.assertEqual(client.get(f'/api/v1/claims/{claim.claim_number}/').status_code, 404)
        self.assertEqual(client.get(f'/api/v1/claims/{claim.pk}/documents/').status_code, 404)


def png_bytes():
    from PIL import Image
    buffer = io.BytesIO()
    Image.new('RGB', (4, 4), 'red').save(buffer, format='PNG')
    return buffer.getvalue()


class ClaimUploadTests(ClaimTestBase):
    def upload(self, name, content, content_type):
        claim = self.make_claim()
        return self.as_user(self.customer).post(
            f'/api/v1/claims/{claim.pk}/documents/',
            {'file': SimpleUploadedFile(name, content, content_type=content_type), 'document_type': 'photos', 'original_name': name},
            format='multipart',
        )

    def test_rejects_disallowed_type_and_mismatched_content(self):
        response = self.upload('evil.html', b'<script>alert(1)</script>', 'text/html')
        self.assertEqual(response.status_code, 400)
        body = response.json()
        # Standard envelope with a readable top-level `detail` string.
        self.assertTrue(body['detail'].startswith('file: Unsupported file type'))
        self.assertIn('file', body['error']['details'])
        self.assertEqual(self.upload('x.exe', b'MZ\x90\x00', 'application/octet-stream').status_code, 400)
        self.assertEqual(self.upload('fake.jpg', b'<script>alert(1)</script>', 'image/jpeg').status_code, 400)

    @override_settings(MAX_UPLOAD_BYTES=10)
    def test_rejects_oversized_file(self):
        from common import uploads
        original = uploads.MAX_UPLOAD_BYTES
        uploads.MAX_UPLOAD_BYTES = 10
        try:
            self.assertEqual(self.upload('a.pdf', b'%PDF-1.4 ' + b'x' * 100, 'application/pdf').status_code, 400)
        finally:
            uploads.MAX_UPLOAD_BYTES = original

    def test_accepts_valid_image_with_random_stored_name(self):
        response = self.upload('my photo.png', png_bytes(), 'image/png')
        self.assertEqual(response.status_code, 201, response.content)
        self.assertEqual(response.json()['original_name'], 'my photo.png')
        self.assertNotIn('my', response.json()['file'].rsplit('/', 1)[-1])
        self.assertEqual(self.upload('doc.pdf', b'%PDF-1.4 test', 'application/pdf').status_code, 201)


class RequestIdTests(ClaimTestBase):
    def test_error_responses_carry_request_id(self):
        self.client.force_authenticate(None)
        response = self.client.get('/api/v1/claims/', HTTP_X_REQUEST_ID='trace-123')
        self.assertEqual(response.status_code, 401)
        self.assertEqual(response['X-Request-ID'], 'trace-123')
        self.assertEqual(response.json()['error']['request_id'], 'trace-123')
        generated = self.client.get('/api/v1/claims/', HTTP_X_REQUEST_ID='bad id with spaces')
        self.assertNotEqual(generated['X-Request-ID'], 'bad id with spaces')


def _fake_models(fraud, total_loss=10.0):
    from unittest import mock
    return (
        mock.patch('apps.assessments.ai_views.predict_repair_cost_ml', return_value={
            'cost': 4200.0, 'breakdown': {}, 'time_estimate': None, 'comparable_count': None}),
        mock.patch('apps.assessments.ai_views.detect_fraud_ml', return_value={
            'score': fraud, 'level': 'high', 'factors': ['test factor'], 'behavioral': [], 'network': {}}),
        mock.patch('apps.assessments.ai_views.predict_total_loss_ml', return_value={'probability': total_loss}),
    )


class ClaimAutoAssessmentTests(ClaimTestBase):
    claim_payload = ClaimInputValidationTests.claim_payload

    def submit(self):
        response = self.as_user(self.customer).post('/api/v1/claims/', self.claim_payload(), format='json')
        self.assertEqual(response.status_code, 201, response.content)
        return Claim.objects.get(claim_number=response.json()['claim_number'])

    def test_new_claim_is_scored_and_high_risk_raises_fraud_alert(self):
        from apps.investigations.models import FraudAlert
        cost, fraud, total_loss = _fake_models(fraud=80.0, total_loss=60.0)
        with cost, fraud, total_loss:
            claim = self.submit()
        self.assertEqual(claim.fraud_risk_score, Decimal('80.00'))
        self.assertEqual(claim.total_loss_probability, Decimal('60.00'))
        self.assertEqual(claim.ai_assessment['fraud_risk']['factors'], ['test factor'])
        alert = FraudAlert.objects.get(claim=claim)
        self.assertEqual((alert.risk_level, alert.status), ('high', 'new'))

    def test_low_risk_claim_gets_no_fraud_alert(self):
        from apps.investigations.models import FraudAlert
        cost, fraud, total_loss = _fake_models(fraud=12.0)
        with cost, fraud, total_loss:
            claim = self.submit()
        self.assertEqual(claim.fraud_risk_score, Decimal('12.00'))
        self.assertFalse(FraudAlert.objects.filter(claim=claim).exists())

    def test_model_outage_does_not_block_submission(self):
        from unittest import mock
        from ml_service import MLModelUnavailable
        with mock.patch('apps.assessments.ai_views.predict_repair_cost_ml', side_effect=MLModelUnavailable('down')):
            claim = self.submit()
        self.assertEqual(claim.fraud_risk_score, Decimal('0'))

    def test_rescoring_keeps_imported_source_row_and_alert_workflow(self):
        from apps.assessments.ai_views import run_claim_assessment
        from apps.investigations.models import FraudAlert
        claim = self.make_claim(ai_assessment={'source_dataset': 'insurance_claims', 'source_data': {'age': 40}})
        FraudAlert.objects.create(claim=claim, risk_score=0, risk_level='low', ai_recommendation='x',
                                  status='investigation', assigned_investigator=self.investigator)
        cost, fraud, total_loss = _fake_models(fraud=70.0)
        with cost, fraud, total_loss:
            run_claim_assessment(claim)
        claim.refresh_from_db()
        self.assertEqual(claim.ai_assessment['source_data'], {'age': 40})
        alert = FraudAlert.objects.get(claim=claim)
        self.assertEqual((alert.risk_level, alert.status, alert.assigned_investigator), ('high', 'investigation', self.investigator))


class ClaimAutoAssignmentTests(ClaimTestBase):
    claim_payload = ClaimInputValidationTests.claim_payload

    def test_new_claim_goes_to_least_busy_employee_and_notifies_them(self):
        from apps.notifications.models import Notification
        User = get_user_model()
        idle = User.objects.create_user(username='idle', email='idle@example.com', password='x', role='employee')
        self.make_claim(assigned_adjuster=self.employee)
        response = self.as_user(self.customer).post('/api/v1/claims/', self.claim_payload(), format='json')
        self.assertEqual(response.status_code, 201, response.content)
        claim = Claim.objects.get(claim_number=response.json()['claim_number'])
        self.assertEqual(claim.assigned_adjuster, idle)
        self.assertTrue(claim.timeline.filter(title='Automatically Assigned to Adjuster').exists())
        self.assertTrue(Notification.objects.filter(recipient=idle, title='New claim assigned to you').exists())

    @override_settings(CLAIM_AUTO_ASSIGN_LEAST_BUSY=False)
    def test_least_busy_assignment_can_be_switched_off(self):
        response = self.as_user(self.customer).post('/api/v1/claims/', self.claim_payload(), format='json')
        self.assertIsNone(Claim.objects.get(claim_number=response.json()['claim_number']).assigned_adjuster)
