from django.contrib.auth import get_user_model
from django.core.files.uploadedfile import SimpleUploadedFile
from django.test import override_settings
from rest_framework.test import APITestCase

from apps.claims.tests import TEMP_MEDIA, make_customer_records


@override_settings(ALLOWED_HOSTS=['testserver'], SECURE_SSL_REDIRECT=False, MEDIA_ROOT=TEMP_MEDIA)
class PolicyApiTests(APITestCase):
    @classmethod
    def setUpTestData(cls):
        User = get_user_model()
        cls.admin = User.objects.create_user(username='padm', email='padm@example.com', password='x', role='admin')
        cls.employee = User.objects.create_user(username='pemp', email='pemp@example.com', password='x', role='employee')
        cls.customer, cls.policy, cls.vehicle = make_customer_records('pcust', 'VINTEST0000000031')

    def test_malformed_parameters_return_400(self):
        self.client.force_authenticate(self.employee)
        self.assertEqual(self.client.get('/api/v1/policies/expiring/?days=abc').status_code, 400)
        self.assertEqual(self.client.post('/api/v1/policies/bind-quote/', {'application_id': 'abc'}, format='json').status_code, 400)
        self.assertEqual(self.client.get('/api/v1/policies/form-options/?customer=abc').status_code, 400)
        self.assertEqual(self.client.post(f'/api/v1/policies/{self.policy.pk}/endorsements/abc/approve/').status_code, 400)

    def test_documents_get_and_admin_post_share_route(self):
        url = f'/api/v1/policies/{self.policy.pk}/documents/'

        def payload():
            return {'file': SimpleUploadedFile('p.pdf', b'%PDF-1.4 p', content_type='application/pdf'),
                    'document_type': 'policy', 'original_name': 'p.pdf'}

        self.client.force_authenticate(self.customer)
        self.assertEqual(self.client.post(url, payload(), format='multipart').status_code, 403)
        self.client.force_authenticate(self.admin)
        response = self.client.post(url, payload(), format='multipart')
        self.assertEqual(response.status_code, 201, response.content)
        self.client.force_authenticate(self.customer)
        listed = self.client.get(url)
        self.assertEqual(listed.status_code, 200)
        self.assertEqual(len(listed.json()), 1)

    def test_endorsements_get_and_post_share_route(self):
        url = f'/api/v1/policies/{self.policy.pk}/endorsements/'
        self.client.force_authenticate(self.employee)
        self.assertEqual(self.client.get(url).status_code, 200)
        created = self.client.post(url, {'change_type': 'deductible', 'deductible': '200'}, format='json')
        self.assertEqual(created.status_code, 201, created.content)
        self.assertEqual(len(self.client.get(url).json()), 1)
        self.client.force_authenticate(self.customer)
        self.assertEqual(self.client.get(url).status_code, 403)

    def test_negative_premium_or_deductible_rejected(self):
        self.client.force_authenticate(self.admin)
        for field, value in (('premium', '-1'), ('deductible', '-1')):
            response = self.client.patch(f'/api/v1/policies/{self.policy.pk}/', {field: value}, format='json')
            self.assertEqual(response.status_code, 400)


@override_settings(ALLOWED_HOSTS=['testserver'], SECURE_SSL_REDIRECT=False, MEDIA_ROOT=TEMP_MEDIA)
class CustomerPolicyRequestTests(APITestCase):
    @classmethod
    def setUpTestData(cls):
        from apps.vehicles.models import Vehicle
        User = get_user_model()
        cls.employee = User.objects.create_user(username='remp', email='remp@example.com', password='x', role='employee')
        cls.customer = User.objects.create_user(username='rcust', email='rcust@example.com', password='x', role='customer')
        cls.other = User.objects.create_user(username='rother', email='rother@example.com', password='x', role='customer')
        cls.vehicle = Vehicle.objects.create(
            customer=cls.customer, make='Hyundai', model='Creta', year=2026, vin='VINTEST0000000041',
            color='White', license_plate='KL41Z6262', license_state='KL',
        )

    def request_payload(self, **overrides):
        payload = {
            'customer': self.customer.pk, 'policy_type': 'auto_comprehensive',
            'applicant_details': {}, 'asset_details': {'vehicle_id': self.vehicle.pk},
            'risk_factors': {}, 'asset_value': '1000000', 'coverage_limit': '1000000',
            'deductible': '1000', 'risk_score': '0',
            'policy_terms': {'start_date': '2026-11-01', 'end_date': '2027-10-31', 'vehicle': self.vehicle.pk,
                             'payment_frequency': 'annual', 'agent': self.employee.pk},
        }
        payload.update(overrides)
        return payload

    def submit_request(self):
        self.client.force_authenticate(self.customer)
        return self.client.post('/api/v1/policies/quote/', self.request_payload(), format='json')

    def test_customer_request_uses_default_risk_and_notifies_staff(self):
        from apps.notifications.models import Notification
        response = self.submit_request()
        self.assertEqual(response.status_code, 201, response.content)
        body = response.json()
        self.assertEqual(body['risk_score'], '25.00')
        self.assertTrue(body['requested_by_customer'])
        self.assertNotIn('agent', body['policy_terms'])
        self.assertIn('Creta', body['vehicle_label'])
        self.assertEqual(body['assigned_to'], self.employee.pk)
        self.assertTrue(Notification.objects.filter(recipient=self.employee, title='New policy request assigned to you').exists())

    def test_duplicate_request_for_same_vehicle_is_rejected(self):
        self.assertEqual(self.submit_request().status_code, 201)
        self.assertEqual(self.submit_request().status_code, 409)

    def test_customers_only_see_their_own_requests(self):
        self.submit_request()
        self.client.force_authenticate(self.other)
        self.assertEqual(self.client.get('/api/v1/policies/applications/').json()['count'], 0)
        self.client.force_authenticate(self.employee)
        self.assertEqual(self.client.get('/api/v1/policies/applications/?status=quoted').json()['count'], 1)

    def test_staff_issue_request_and_customer_cannot(self):
        application_id = self.submit_request().json()['id']
        self.assertEqual(self.client.post('/api/v1/policies/bind-quote/', {'application_id': application_id}, format='json').status_code, 403)
        self.client.force_authenticate(self.employee)
        issued = self.client.post('/api/v1/policies/bind-quote/', {'application_id': application_id}, format='json')
        self.assertEqual(issued.status_code, 201, issued.content)
        self.vehicle.refresh_from_db()
        self.assertEqual(self.vehicle.policy.policy_number, issued.json()['policy_number'])
        application = self.client.get(f'/api/v1/policies/applications/{application_id}/').json()
        self.assertEqual(application['status'], 'bound')
        self.assertEqual(application['bound_policy_number'], issued.json()['policy_number'])

    def test_staff_decline_with_note_notifies_customer(self):
        from apps.notifications.models import Notification
        application_id = self.submit_request().json()['id']
        url = f'/api/v1/policies/applications/{application_id}/decline/'
        self.assertEqual(self.client.post(url, {'note': 'x'}, format='json').status_code, 403)
        self.client.force_authenticate(self.employee)
        declined = self.client.post(url, {'note': 'Vehicle inspection needed'}, format='json')
        self.assertEqual(declined.status_code, 200, declined.content)
        self.assertEqual(declined.json()['status'], 'declined')
        self.assertEqual(self.client.post(url, {}, format='json').status_code, 409)
        self.assertTrue(Notification.objects.filter(recipient=self.customer, title='Policy request declined').exists())
        # A declined request no longer blocks a fresh one for the same vehicle.
        self.assertEqual(self.submit_request().status_code, 201)


@override_settings(ALLOWED_HOSTS=['testserver'], SECURE_SSL_REDIRECT=False, MEDIA_ROOT=TEMP_MEDIA)
class PolicyRequestAssignmentTests(APITestCase):
    @classmethod
    def setUpTestData(cls):
        from apps.vehicles.models import Vehicle
        User = get_user_model()
        cls.admin = User.objects.create_user(username='aadm', email='aadm@example.com', password='x', role='admin')
        cls.busy = User.objects.create_user(username='abusy', email='abusy@example.com', password='x', role='employee')
        cls.free = User.objects.create_user(username='afree', email='afree@example.com', password='x', role='employee')
        cls.customer = User.objects.create_user(username='acust', email='acust@example.com', password='x', role='customer')
        cls.vehicles = [
            Vehicle.objects.create(customer=cls.customer, make='Make', model=f'M{index}', year=2024,
                                   vin=f'VINTEST00000005{index}{index}', color='Red', license_plate=f'KL0{index}', license_state='KL')
            for index in range(3)
        ]

    def request_policy(self, vehicle):
        self.client.force_authenticate(self.customer)
        return self.client.post('/api/v1/policies/quote/', {
            'customer': self.customer.pk, 'policy_type': 'auto_comprehensive', 'applicant_details': {},
            'asset_details': {}, 'risk_factors': {}, 'asset_value': '500000', 'coverage_limit': '500000',
            'deductible': '1000', 'risk_score': '0',
            'policy_terms': {'start_date': '2026-11-01', 'end_date': '2027-10-31', 'vehicle': vehicle.pk},
        }, format='json').json()

    def test_requests_are_spread_to_least_busy_employee_not_admin(self):
        from apps.notifications.models import Notification
        first = self.request_policy(self.vehicles[0])
        second = self.request_policy(self.vehicles[1])
        self.assertEqual({first['assigned_to'], second['assigned_to']}, {self.busy.pk, self.free.pk})
        self.assertFalse(Notification.objects.filter(recipient=self.admin).exists())

    def test_employee_only_sees_and_acts_on_own_requests_admin_can_oversee(self):
        application = self.request_policy(self.vehicles[0])
        owner = self.busy if application['assigned_to'] == self.busy.pk else self.free
        other = self.free if owner == self.busy else self.busy
        self.client.force_authenticate(other)
        self.assertEqual(self.client.get('/api/v1/policies/applications/').json()['count'], 0)
        bind = {'application_id': application['id']}
        self.assertEqual(self.client.post('/api/v1/policies/bind-quote/', bind, format='json').status_code, 403)
        self.client.force_authenticate(self.admin)
        self.assertEqual(self.client.get('/api/v1/policies/applications/').json()['count'], 1)
        self.client.force_authenticate(owner)
        self.assertEqual(self.client.post('/api/v1/policies/bind-quote/', bind, format='json').status_code, 201)


@override_settings(ALLOWED_HOSTS=['testserver'], SECURE_SSL_REDIRECT=False, MEDIA_ROOT=TEMP_MEDIA)
class NoEmployeeAvailableTests(APITestCase):
    @classmethod
    def setUpTestData(cls):
        from apps.vehicles.models import Vehicle
        User = get_user_model()
        cls.admin = User.objects.create_user(username='nadm', email='nadm@example.com', password='x', role='admin')
        cls.customer = User.objects.create_user(username='ncust', email='ncust@example.com', password='x', role='customer')
        cls.vehicle = Vehicle.objects.create(customer=cls.customer, make='Make', model='Solo', year=2024,
                                             vin='VINTEST0000000061', color='Red', license_plate='KL61', license_state='KL')

    def test_admin_is_alerted_and_new_employee_receives_waiting_request(self):
        from apps.notifications.models import Notification
        self.client.force_authenticate(self.customer)
        application = self.client.post('/api/v1/policies/quote/', {
            'customer': self.customer.pk, 'policy_type': 'auto_comprehensive', 'applicant_details': {},
            'asset_details': {}, 'risk_factors': {}, 'asset_value': '500000', 'coverage_limit': '500000',
            'deductible': '1000', 'risk_score': '0',
            'policy_terms': {'start_date': '2026-11-01', 'end_date': '2027-10-31', 'vehicle': self.vehicle.pk},
        }, format='json').json()
        self.assertIsNone(application['assigned_to'])
        self.assertTrue(Notification.objects.filter(
            recipient=self.admin, title='Policy request waiting: no employee available').exists())

        self.client.force_authenticate(self.admin)
        created = self.client.post('/api/v1/auth/users/', {
            'first_name': 'New', 'last_name': 'Hire', 'email': 'hire@example.com', 'role': 'employee',
            'password': 'Str0ng-pass-123', 'password_confirm': 'Str0ng-pass-123',
        }, format='json')
        self.assertEqual(created.status_code, 201, created.content)
        hire = get_user_model().objects.get(email='hire@example.com')
        detail = self.client.get(f"/api/v1/policies/applications/{application['id']}/").json()
        self.assertEqual(detail['assigned_to'], hire.pk)
        self.assertTrue(Notification.objects.filter(recipient=hire, title='New policy request assigned to you').exists())
