from datetime import date, timedelta
from decimal import Decimal

from django.test import TestCase
from rest_framework.test import APIClient

from apps.accounts.models import Role, User
from apps.policies.models import Policy, PolicyEndorsement
from apps.vehicles.models import Vehicle


class ServiceRequestTests(TestCase):
    def setUp(self):
        self.customer = User.objects.create_user(
            username='svccust', email='svccust@demo.com', password='x', role=Role.CUSTOMER,
            first_name='Service', last_name='Customer', phone='9812034567',
        )
        self.other_customer = User.objects.create_user(
            username='othercust', email='othercust@demo.com', password='x', role=Role.CUSTOMER,
        )
        self.employee = User.objects.create_user(
            username='svcemp', email='svcemp@insure.com', password='x', role=Role.EMPLOYEE,
        )
        self.admin = User.objects.create_user(
            username='svcadmin', email='svcadmin@insure.com', password='x', role=Role.ADMIN,
        )
        self.vehicle = Vehicle.objects.create(
            customer=self.customer, make='Tata', model='Punch', year=2025, vin='MAT3SVC00000001AA',
            color='Silver', license_plate='KL 07 S 2637', license_state='KL', current_mileage=2995,
        )
        today = date.today()
        self.policy = Policy.objects.create(
            policy_number='POL-SVC-0001', customer=self.customer, vehicle=self.vehicle, type='auto_comprehensive',
            status='active', start_date=today - timedelta(days=100), end_date=today + timedelta(days=265),
            premium=Decimal('12000.00'), deductible=Decimal('1000.00'), payment_frequency='annual', coverage={},
        )
        self.client = APIClient()

    def url(self, suffix=''):
        return f'/api/v1/policies/{self.policy.pk}/{suffix}'

    def submit(self, change_type, **extra):
        self.client.force_authenticate(self.customer)
        return self.client.post(self.url('service-requests/'), {'change_type': change_type, 'reason': 'Test reason', **extra}, format='json')

    def approve(self, endorsement_id):
        self.client.force_authenticate(self.employee)
        return self.client.post(self.url(f'endorsements/{endorsement_id}/approve/'), format='json')

    def test_renewal_is_pending_then_extends_end_date_when_approved(self):
        original_end = self.policy.end_date
        response = self.submit('renewal')
        self.assertEqual(response.status_code, 201, response.content)
        endorsement_id = response.json()['id']
        self.policy.refresh_from_db()
        self.assertEqual(self.policy.end_date, original_end)  # still unchanged while pending

        self.assertEqual(self.approve(endorsement_id).status_code, 200)
        self.policy.refresh_from_db()
        self.assertEqual(self.policy.end_date, original_end + timedelta(days=365))

    def test_cancellation_cancels_the_policy_after_approval(self):
        endorsement_id = self.submit('cancellation').json()['id']
        self.assertEqual(self.approve(endorsement_id).status_code, 200)
        self.policy.refresh_from_db()
        self.assertEqual(self.policy.status, 'cancelled')

    def test_vehicle_change_updates_only_editable_fields(self):
        response = self.submit('vehicle_change', vehicle={'color': 'Red', 'current_mileage': 4000, 'make': 'Hacked'})
        self.assertEqual(response.status_code, 201, response.content)
        self.assertEqual(self.approve(response.json()['id']).status_code, 200)
        self.vehicle.refresh_from_db()
        self.assertEqual((self.vehicle.color, self.vehicle.current_mileage, self.vehicle.make), ('Red', 4000, 'Tata'))

    def test_vehicle_change_needs_a_valid_field(self):
        self.assertEqual(self.submit('vehicle_change', vehicle={'make': 'Nope'}).status_code, 400)
        self.assertEqual(self.submit('vehicle_change', vehicle={'current_mileage': -5}).status_code, 400)

    def test_duplicate_pending_request_is_rejected(self):
        self.assertEqual(self.submit('renewal').status_code, 201)
        self.assertEqual(self.submit('renewal').status_code, 409)

    def test_unknown_change_type_and_missing_reason_are_rejected(self):
        self.assertEqual(self.submit('upgrade').status_code, 400)
        self.client.force_authenticate(self.customer)
        response = self.client.post(self.url('service-requests/'), {'change_type': 'renewal', 'reason': ' '}, format='json')
        self.assertEqual(response.status_code, 400)

    def test_staff_cannot_submit_service_requests(self):
        self.client.force_authenticate(self.employee)
        response = self.client.post(self.url('service-requests/'), {'change_type': 'renewal', 'reason': 'x'}, format='json')
        self.assertEqual(response.status_code, 403)

    def test_other_customers_cannot_see_the_policy(self):
        self.client.force_authenticate(self.other_customer)
        self.assertEqual(self.client.get(self.url('service-requests/')).status_code, 404)
        self.assertEqual(self.client.get(self.url('policy-document/')).status_code, 404)

    def test_customer_sees_their_own_requests(self):
        self.submit('renewal')
        self.client.force_authenticate(self.customer)
        response = self.client.get(self.url('service-requests/'))
        self.assertEqual(response.status_code, 200)
        self.assertEqual([item['change_type'] for item in response.json()], ['renewal'])
        self.assertEqual(PolicyEndorsement.objects.filter(policy=self.policy).count(), 1)

    def test_plan_catalogue_lists_demo_plans(self):
        self.client.force_authenticate(self.customer)
        data = self.client.get('/api/v1/policies/plans/').json()
        self.assertEqual(len(data['plans']), 3)
        self.assertIn('not insurer quotes', data['notice'])

    def test_policy_document_is_an_html_attachment_with_escaped_values(self):
        self.customer.first_name = '<b>Test</b>'
        self.customer.save()
        self.client.force_authenticate(self.customer)
        response = self.client.get(self.url('policy-document/'))
        self.assertEqual(response.status_code, 200)
        self.assertIn('text/html', response['Content-Type'])
        self.assertIn('attachment; filename="POL-SVC-0001.html"', response['Content-Disposition'])
        body = response.content.decode()
        self.assertIn('POL-SVC-0001', body)
        self.assertNotIn('<b>Test</b>', body)
        self.assertIn('&lt;b&gt;Test&lt;/b&gt;', body)
