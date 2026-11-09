from datetime import timedelta
from decimal import Decimal

from django.contrib.auth import get_user_model
from django.test import override_settings
from django.urls import reverse
from django.utils import timezone
from rest_framework import status
from rest_framework.test import APITestCase

from apps.claims.models import Claim, ClaimNote, ClaimStatus
from apps.policies.models import Policy, PolicyStatus, PolicyType
from apps.vehicles.models import Vehicle

User = get_user_model()


def delete_url(user):
    return reverse('auth-delete-user', kwargs={'user_id': user.pk})


@override_settings(ALLOWED_HOSTS=['testserver'], SECURE_SSL_REDIRECT=False)
class AccountRemovalPermissionTests(APITestCase):
    def setUp(self):
        self.admin = User.objects.create_user(username='adm', email='adm@example.com', password='x', role='admin')
        self.other_admin = User.objects.create_user(username='adm2', email='adm2@example.com', password='x', role='admin')
        self.employee = User.objects.create_user(username='emp', email='emp@example.com', password='x', role='employee')
        self.customer = User.objects.create_user(username='cus', email='cus@example.com', password='x', role='customer')

    def test_admin_can_delete_customer_without_history(self):
        self.client.force_authenticate(self.admin)
        response = self.client.delete(delete_url(self.customer))
        self.assertEqual(response.status_code, status.HTTP_200_OK, response.content)
        self.assertEqual(response.json()['data']['action'], 'deleted')
        self.assertFalse(User.objects.filter(pk=self.customer.pk).exists())

    def test_admin_can_delete_employee_and_investigator_without_history(self):
        investigator = User.objects.create_user(username='inv', email='inv@example.com', password='x', role='investigator')
        self.client.force_authenticate(self.admin)
        for target in (self.employee, investigator):
            response = self.client.delete(delete_url(target))
            self.assertEqual(response.status_code, status.HTTP_200_OK, response.content)
            self.assertFalse(User.objects.filter(pk=target.pk).exists())

    def test_non_admin_gets_403(self):
        for actor in (self.employee, self.customer):
            self.client.force_authenticate(actor)
            victim = User.objects.create_user(username=f'v-{actor.pk}', email=f'v{actor.pk}@example.com', password='x')
            response = self.client.delete(delete_url(victim))
            self.assertEqual(response.status_code, status.HTTP_403_FORBIDDEN)
            self.assertTrue(User.objects.filter(pk=victim.pk).exists())

    def test_anonymous_cannot_delete(self):
        response = self.client.delete(delete_url(self.customer))
        self.assertIn(response.status_code, (status.HTTP_401_UNAUTHORIZED, status.HTTP_403_FORBIDDEN))
        self.assertTrue(User.objects.filter(pk=self.customer.pk).exists())

    def test_admin_cannot_delete_self(self):
        self.client.force_authenticate(self.admin)
        response = self.client.delete(delete_url(self.admin))
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
        self.admin.refresh_from_db()
        self.assertTrue(self.admin.is_active)

    def test_admin_cannot_delete_another_admin(self):
        self.client.force_authenticate(self.admin)
        response = self.client.delete(delete_url(self.other_admin))
        self.assertEqual(response.status_code, status.HTTP_403_FORBIDDEN)
        self.other_admin.refresh_from_db()
        self.assertTrue(self.other_admin.is_active)

    def test_unknown_account_returns_404(self):
        self.client.force_authenticate(self.admin)
        response = self.client.delete(reverse('auth-delete-user', kwargs={'user_id': 999999}))
        self.assertEqual(response.status_code, status.HTTP_404_NOT_FOUND)


@override_settings(ALLOWED_HOSTS=['testserver'], SECURE_SSL_REDIRECT=False)
class AccountRemovalHistoryTests(APITestCase):
    def setUp(self):
        self.admin = User.objects.create_user(username='adm', email='adm@example.com', password='x', role='admin')
        self.customer = User.objects.create_user(username='cus', email='cus@example.com', password='x', role='customer')
        self.employee = User.objects.create_user(username='emp', email='emp@example.com', password='x', role='employee')
        today = timezone.localdate()
        self.policy = Policy.objects.create(
            policy_number='POL-DEL-1', customer=self.customer, type=PolicyType.choices[0][0],
            status=PolicyStatus.ACTIVE, start_date=today - timedelta(days=10), end_date=today + timedelta(days=355),
            premium=Decimal('1000'), deductible=Decimal('100'),
        )
        self.vehicle = Vehicle.objects.create(
            customer=self.customer, policy=self.policy, make='Maruti', model='Swift', year=2020,
            vin='VINDEL00000000001', color='White', license_plate='KL01AB1234', license_state='KL',
        )
        self.claim = Claim.objects.create(
            claim_number='CLM-DEL-1', customer=self.customer, policy=self.policy, vehicle=self.vehicle,
            incident_date=today, incident_type='collision', incident_severity='minor',
            location='Kochi', claim_amount=Decimal('5000'), status=ClaimStatus.SUBMITTED,
            assigned_adjuster=self.employee,
        )
        self.client.force_authenticate(self.admin)

    def test_customer_with_policies_and_claims_is_deactivated_not_deleted(self):
        response = self.client.delete(delete_url(self.customer))
        self.assertEqual(response.status_code, status.HTTP_200_OK, response.content)
        body = response.json()
        self.assertEqual(body['data']['action'], 'deactivated')
        self.assertIn('claims.Claim', body['data']['related_records'])
        self.assertIn('policies.Policy', body['data']['related_records'])
        self.assertEqual(body['data']['related_records']['vehicles.Vehicle'], 1)
        self.assertIn('deactivated', body['message'])

        self.customer.refresh_from_db()
        self.assertFalse(self.customer.is_active)
        self.assertTrue(Policy.objects.filter(pk=self.policy.pk).exists())
        self.assertTrue(Vehicle.objects.filter(pk=self.vehicle.pk).exists())
        self.assertTrue(Claim.objects.filter(pk=self.claim.pk).exists())

    def test_customer_with_only_a_vehicle_is_kept(self):
        loner = User.objects.create_user(username='lone', email='lone@example.com', password='x', role='customer')
        Vehicle.objects.create(
            customer=loner, make='Tata', model='Nexon', year=2022, vin='VINDEL00000000002',
            color='Blue', license_plate='KL07CD5678', license_state='KL',
        )
        response = self.client.delete(delete_url(loner))
        self.assertEqual(response.json()['data']['action'], 'deactivated')
        self.assertEqual(Vehicle.objects.filter(customer=loner).count(), 1)

    def test_employee_assigned_to_a_claim_is_deactivated_and_attribution_kept(self):
        response = self.client.delete(delete_url(self.employee))
        self.assertEqual(response.status_code, status.HTTP_200_OK, response.content)
        self.assertEqual(response.json()['data']['action'], 'deactivated')
        self.claim.refresh_from_db()
        self.assertEqual(self.claim.assigned_adjuster_id, self.employee.pk)

    def test_staff_note_author_is_not_deleted(self):
        investigator = User.objects.create_user(username='inv', email='inv@example.com', password='x', role='investigator')
        note = ClaimNote.objects.create(claim=self.claim, author=investigator, content='Checked the garage invoice.')
        response = self.client.delete(delete_url(investigator))
        self.assertEqual(response.json()['data']['action'], 'deactivated')
        self.assertTrue(ClaimNote.objects.filter(pk=note.pk).exists())

    def test_deactivated_account_with_history_returns_conflict_on_repeat(self):
        self.client.delete(delete_url(self.customer))
        response = self.client.delete(delete_url(self.customer))
        self.assertEqual(response.status_code, status.HTTP_409_CONFLICT)
        self.assertIn('already deactivated', response.json()['error']['message'])
        self.assertTrue(User.objects.filter(pk=self.customer.pk).exists())

    def test_deactivated_customer_cannot_sign_in(self):
        self.customer.set_password('StrongPass!2026')
        self.customer.save()
        self.client.delete(delete_url(self.customer))
        self.client.force_authenticate(None)
        response = self.client.post(
            '/api/v1/auth/login/', {'email': 'cus@example.com', 'password': 'StrongPass!2026'}, format='json',
        )
        self.assertNotEqual(response.status_code, status.HTTP_200_OK)
