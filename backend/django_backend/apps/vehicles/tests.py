from datetime import timedelta
from decimal import Decimal

from django.contrib.auth import get_user_model
from django.core.files.uploadedfile import SimpleUploadedFile
from django.test import override_settings
from django.utils import timezone
from rest_framework.test import APITestCase

from apps.claims.models import Claim
from apps.claims.tests import TEMP_MEDIA, make_customer_records


@override_settings(ALLOWED_HOSTS=['testserver'], SECURE_SSL_REDIRECT=False, MEDIA_ROOT=TEMP_MEDIA)
class VehicleApiTests(APITestCase):
    @classmethod
    def setUpTestData(cls):
        User = get_user_model()
        cls.admin = User.objects.create_user(username='vadm', email='vadm@example.com', password='x', role='admin')
        cls.investigator = User.objects.create_user(username='vinv', email='vinv@example.com', password='x', role='investigator')
        cls.customer, cls.policy, cls.vehicle = make_customer_records('vcust', 'VINTEST0000000021')

    def test_registration_expiring_does_not_500(self):
        self.client.force_authenticate(self.customer)
        self.assertEqual(self.client.get('/api/v1/vehicles/registration-expiring/').status_code, 200)
        self.assertEqual(self.client.get('/api/v1/vehicles/registration-expiring/?days=abc').status_code, 400)

    def test_document_upload_and_list_share_route(self):
        self.client.force_authenticate(self.customer)
        url = f'/api/v1/vehicles/{self.vehicle.pk}/documents/'
        upload = self.client.post(url, {
            'file': SimpleUploadedFile('rc.pdf', b'%PDF-1.4 rc', content_type='application/pdf'),
            'document_type': 'registration', 'original_name': 'rc.pdf',
        }, format='multipart')
        self.assertEqual(upload.status_code, 201, upload.content)
        self.assertEqual(len(self.client.get(url).json()), 1)
        svg = self.client.post(url, {
            'file': SimpleUploadedFile('a.svg', b'<svg onload=alert(1)>', content_type='image/svg+xml'),
            'document_type': 'registration', 'original_name': 'a.svg',
        }, format='multipart')
        self.assertEqual(svg.status_code, 400)

    def test_vin_and_numeric_validation(self):
        self.client.force_authenticate(self.admin)
        base = {'customer': self.customer.pk, 'make': 'M', 'model': 'X', 'year': 2021, 'color': 'red',
                'license_plate': 'KA01', 'license_state': 'KA'}
        post = lambda **extra: self.client.post('/api/v1/vehicles/', {**base, **extra}, format='json')
        self.assertEqual(post(vin='SHORT').status_code, 400)
        self.assertEqual(post(vin='IOQ45678901234567').status_code, 400)
        self.assertEqual(post(vin='VABCD1234567890XY', purchase_price='-1').status_code, 400)
        self.assertEqual(post(vin='VABCD1234567890XY', current_mileage=-5).status_code, 400)
        ok = post(vin='vabcd1234567890xy')
        self.assertEqual(ok.status_code, 201, ok.content)
        self.assertEqual(ok.json()['vin'], 'VABCD1234567890XY')

    def test_vehicle_with_claims_cannot_be_deleted_and_investigator_cannot_edit(self):
        claim = Claim.objects.create(
            claim_number='CLM-V1', customer=self.customer, policy=self.policy, vehicle=self.vehicle,
            incident_date=timezone.localdate() - timedelta(days=1), incident_type='collision',
            incident_severity='minor', location='x', claim_amount=Decimal('10'), assigned_investigator=self.investigator,
        )
        self.client.force_authenticate(self.investigator)
        self.assertEqual(self.client.patch(f'/api/v1/vehicles/{self.vehicle.pk}/', {'color': 'x'}, format='json').status_code, 403)
        self.client.force_authenticate(self.customer)
        self.assertEqual(self.client.delete(f'/api/v1/vehicles/{self.vehicle.pk}/').status_code, 409)
        self.assertTrue(Claim.objects.filter(pk=claim.pk).exists())
