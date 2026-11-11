from datetime import timedelta
from decimal import Decimal

from django.contrib.auth import get_user_model
from django.test import TestCase, override_settings
from django.utils import timezone
from rest_framework.test import APIClient

from apps.assessments.assignment import available_employees
from apps.assessments.models import EmployeeSkill, RoutingAgentProfile
from apps.claims.models import Claim, ClaimStatus
from apps.policies.models import Policy, PolicyStatus
from apps.vehicles.models import Vehicle


@override_settings(ALLOWED_HOSTS=['testserver'], SECURE_SSL_REDIRECT=False)
class WorkforceProfileTests(TestCase):
    def setUp(self):
        User = get_user_model()
        self.admin = User.objects.create_user(username='wf-admin', email='wf-admin@example.com', password='x', role='admin')
        self.employee = User.objects.create_user(username='wf-employee', email='wf-employee@example.com', password='x', role='employee', first_name='Asha')
        self.other_employee = User.objects.create_user(username='wf-other', email='wf-other@example.com', password='x', role='employee')
        self.customer = User.objects.create_user(username='wf-customer', email='wf-customer@example.com', password='x', role='customer')
        self.policy = Policy.objects.create(
            policy_number='WF-POL-1', customer=self.customer, type='auto_comprehensive', status=PolicyStatus.ACTIVE,
            start_date=timezone.localdate() - timedelta(days=1), end_date=timezone.localdate() + timedelta(days=365),
            premium=Decimal('1000'), deductible=Decimal('100'),
        )
        self.vehicle = Vehicle.objects.create(
            customer=self.customer, policy=self.policy, make='Make', model='Model', year=2022,
            vin='WFVIN000000000001', color='Blue', license_plate='WF1001', license_state='KA',
        )
        self.policy.vehicle = self.vehicle
        self.policy.save(update_fields=['vehicle'])
        self.client = APIClient()

    def as_user(self, user):
        self.client.force_authenticate(user)
        return self.client

    def make_claim(self, employee, claim_number='WF-CLM-1'):
        return Claim.objects.create(
            claim_number=claim_number, customer=self.customer, policy=self.policy, vehicle=self.vehicle,
            incident_date=timezone.localdate(), incident_type='collision', incident_severity='minor',
            location='Somewhere', claim_amount=Decimal('1000'), assigned_adjuster=employee,
        )

    def test_employee_can_view_own_profile_and_no_history_metrics_are_empty(self):
        response = self.as_user(self.employee).get(f'/api/v1/workforce/employees/{self.employee.pk}/')
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.data['employee_id'], str(self.employee.pk))
        self.assertIsNone(response.data['average_processing_time_days'])
        self.assertIsNone(response.data['on_time_completion_rate'])
        self.assertIsNone(response.data['reassignment_count'])

    def test_employee_cannot_read_another_employee_profile(self):
        response = self.as_user(self.employee).get(f'/api/v1/workforce/employees/{self.other_employee.pk}/')
        self.assertEqual(response.status_code, 403)

    def test_admin_updates_profile_and_skills(self):
        response = self.as_user(self.admin).patch(
            f'/api/v1/workforce/employees/{self.employee.pk}/',
            {'designation': 'Claims Adjuster', 'max_claim_capacity': 4, 'years_of_experience': 7,
             'availability_status': 'busy', 'skills': [{'name': 'Vehicle Damage Assessment', 'level': 'expert'}]},
            format='json',
        )
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.data['capacity_utilization'], 0)
        self.assertEqual(response.data['skills'][0]['level'], 'expert')
        self.assertEqual(EmployeeSkill.objects.filter(profile__user=self.employee).count(), 1)

    def test_employee_can_update_own_skills_but_not_capacity(self):
        url = f'/api/v1/workforce/employees/{self.employee.pk}/'
        skill_response = self.as_user(self.employee).patch(url, {'skills': [{'name': 'Fraud Review', 'level': 'advanced'}]}, format='json')
        self.assertEqual(skill_response.status_code, 200)
        capacity_response = self.client.patch(url, {'max_claim_capacity': 1}, format='json')
        self.assertEqual(capacity_response.status_code, 403)

    def test_utilization_and_capacity_filter_use_assigned_open_claims(self):
        profile = RoutingAgentProfile.objects.create(user=self.employee, max_claim_capacity=1)
        self.make_claim(self.employee)
        response = self.as_user(self.admin).get(f'/api/v1/workforce/employees/{self.employee.pk}/')
        self.assertEqual(response.data['active_claims'], 1)
        self.assertEqual(response.data['capacity_utilization'], 100)
        self.assertFalse(response.data['assignment_eligible'])
        self.assertNotIn(self.employee, available_employees())
        self.assertIn(self.other_employee, available_employees())
        profile.availability_status = RoutingAgentProfile.Availability.ON_LEAVE
        profile.is_available = False
        profile.save()
        self.assertNotIn(self.employee, available_employees())

    def test_processing_time_uses_closed_claim_timestamps(self):
        claim = self.make_claim(self.employee)
        completed_at = timezone.now()
        claim.status = ClaimStatus.CLOSED
        claim.submitted_at = completed_at - timedelta(days=4)
        claim.closed_at = completed_at
        claim.save(update_fields=['status', 'submitted_at', 'closed_at'])

        response = self.as_user(self.admin).get(f'/api/v1/workforce/employees/{self.employee.pk}/')

        self.assertEqual(response.data['successfully_completed_claims'], 1)
        self.assertEqual(response.data['average_processing_time_days'], 4)

    def test_employee_with_configured_nonworking_day_is_not_eligible(self):
        profile = RoutingAgentProfile.objects.create(user=self.employee)
        weekdays = ['mon', 'tue', 'wed', 'thu', 'fri', 'sat', 'sun']
        profile.working_days = [weekdays[(timezone.localtime().weekday() + 1) % 7]]
        profile.save(update_fields=['working_days'])

        response = self.as_user(self.admin).get(f'/api/v1/workforce/employees/{self.employee.pk}/')

        self.assertFalse(response.data['assignment_eligible'])
        self.assertNotIn(self.employee, available_employees())

    def test_admin_only_employee_listing(self):
        self.assertEqual(self.as_user(self.employee).get('/api/v1/workforce/employees/').status_code, 403)
        response = self.as_user(self.admin).get('/api/v1/workforce/employees/')
        self.assertEqual(response.status_code, 200)
        self.assertEqual(len(response.data), 2)
