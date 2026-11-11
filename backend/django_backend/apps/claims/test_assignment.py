from datetime import date, time, timedelta
from decimal import Decimal
from types import SimpleNamespace
from unittest.mock import patch

from django.contrib.auth import get_user_model
from django.test import TestCase, override_settings
from django.utils import timezone

from apps.assessments.models import EmployeeSkill, RoutingAgentProfile
from apps.claims.assignment import auto_assign_claim, override_assignment
from apps.claims.models import Claim, ClaimAssignmentConfig, ClaimAssignmentEvent, ClaimStatus
from apps.policies.models import Policy
from apps.vehicles.models import Vehicle

User = get_user_model()


class AutomaticClaimAssignmentTests(TestCase):
    def setUp(self):
        self.customer = User.objects.create_user(email='customer@example.test', username='customer', password='x', role='customer')
        self.policy = Policy.objects.create(
            policy_number='POL-ASSIGN-1', customer=self.customer, type='auto_comprehensive', status='active',
            start_date=date.today() - timedelta(days=10), end_date=date.today() + timedelta(days=365),
            premium=Decimal('1000'), deductible=Decimal('100'),
        )
        self.vehicle = Vehicle.objects.create(customer=self.customer, policy=self.policy, make='Test', model='Car', year=2024,
            vin='ASSIGNTEST0001', color='Blue', license_plate='ABC123', license_state='CA')
        self.claim = Claim.objects.create(
            claim_number='CLM-ASSIGN-1', customer=self.customer, policy=self.policy, vehicle=self.vehicle,
            incident_date=date.today(), incident_type='collision', incident_severity='moderate', location='Test',
            claim_amount=Decimal('1000'), status=ClaimStatus.SUBMITTED, complexity_score=Decimal('.5'),
        )

    def employee(self, email='adjuster@example.test', **profile_fields):
        user = User.objects.create_user(email=email, username=email, password='x', role='employee', is_active=True)
        profile = RoutingAgentProfile.objects.create(user=user, primary_specialization='collision', **profile_fields)
        EmployeeSkill.objects.create(profile=profile, name='collision', level='advanced')
        return user, profile

    def test_eligible_employee_gets_auto_assigned_and_audited(self):
        employee, _ = self.employee()
        assigned = auto_assign_claim(self.claim.pk)
        self.assertEqual(assigned.assigned_adjuster_id, employee.pk)
        self.assertEqual(assigned.assignment_status, 'assigned')
        self.assertEqual(ClaimAssignmentEvent.objects.filter(claim=self.claim, event_type='assigned').count(), 1)

    def test_capacity_leave_shift_and_expertise_exclude_employee(self):
        employee, profile = self.employee(max_claim_capacity=1)
        Claim.objects.create(claim_number='CLM-FULL', customer=self.customer, policy=self.policy, vehicle=self.vehicle,
            incident_date=date.today(), incident_type='collision', incident_severity='minor', location='x', claim_amount=Decimal('2'),
            status=ClaimStatus.SUBMITTED, assigned_adjuster=employee)
        self.assertIsNone(auto_assign_claim(self.claim.pk).assigned_adjuster_id)
        profile.max_claim_capacity = 3
        profile.availability_status = 'on_leave'
        profile.save()
        self.assertIsNone(auto_assign_claim(self.claim.pk).assigned_adjuster_id)
        profile.availability_status = 'available'
        profile.shift_start_time, profile.shift_end_time = time(0, 0), time(0, 1)
        profile.save()
        self.assertIsNone(auto_assign_claim(self.claim.pk).assigned_adjuster_id)
        profile.shift_start_time = profile.shift_end_time = None
        profile.primary_specialization = 'theft'
        profile.skills.all().delete()
        profile.save()
        self.assertIsNone(auto_assign_claim(self.claim.pk).assigned_adjuster_id)

    def test_no_eligible_employee_stays_pending_and_is_idempotent(self):
        claim = auto_assign_claim(self.claim.pk)
        self.assertIsNone(claim.assigned_adjuster_id)
        self.assertEqual(claim.assignment_status, 'pending')
        self.assertEqual(ClaimAssignmentEvent.objects.filter(claim=claim, event_type='pending').count(), 1)

    def test_disabled_setting_preserves_manual_workflow(self):
        ClaimAssignmentConfig.objects.create(pk=1, enabled=False)
        self.employee()
        self.assertIsNone(auto_assign_claim(self.claim.pk).assigned_adjuster_id)
        self.assertFalse(ClaimAssignmentEvent.objects.filter(claim=self.claim, event_type='assigned').exists())

    def test_duplicate_auto_retry_does_not_duplicate_history(self):
        self.employee()
        auto_assign_claim(self.claim.pk)
        auto_assign_claim(self.claim.pk)
        self.assertEqual(ClaimAssignmentEvent.objects.filter(claim=self.claim, event_type='assigned').count(), 1)

    def test_admin_override_requires_active_employee_and_records_reason(self):
        employee, _ = self.employee()
        admin = User.objects.create_user(email='admin@example.test', username='admin', password='x', role='admin')
        override_assignment(self.claim.pk, employee.pk, admin, 'Balance workload for urgent repair.')
        event = ClaimAssignmentEvent.objects.get(claim=self.claim, event_type='assigned')
        self.assertEqual(event.actor_id, admin.pk)
        self.assertEqual(event.strategy, 'manual')
        self.assertIn('urgent', event.reason)

    def test_unqualified_ppo_cannot_override_baseline_strategy(self):
        self.employee()
        with override_settings():
            assigned = auto_assign_claim(self.claim.pk)
        self.assertEqual(assigned.assigned_adjuster_id, RoutingAgentProfile.objects.get().user_id)
        event = ClaimAssignmentEvent.objects.get(claim=self.claim)
        self.assertNotEqual(event.strategy, 'ppo')

    def test_qualified_ppo_can_route_after_gate_passes(self):
        employee, _ = self.employee()
        class Engine:
            model_version = 'validated-routing-v2'
            @classmethod
            def load(cls):
                return cls()
            def get_routing_recommendations(self, claim_data, agents):
                return {'recommended_agent_id': str(employee.pk)}
        import sys
        fake_module = SimpleNamespace(ClaimRecommendationEngine=Engine)
        with patch('apps.claims.assignment._ppo_gate', return_value=(True, 'validated-routing-v2')):
            with patch.dict(sys.modules, {'rl.recommendation': fake_module}):
                assigned = auto_assign_claim(self.claim.pk)
        self.assertEqual(assigned.assigned_adjuster_id, employee.pk)
        self.assertEqual(ClaimAssignmentEvent.objects.get(claim=self.claim).strategy, 'ppo')
        self.assertEqual(ClaimAssignmentEvent.objects.get(claim=self.claim).model_version, 'validated-routing-v2')

    def test_sequential_claims_do_not_exceed_capacity(self):
        employee, _ = self.employee(max_claim_capacity=1)
        auto_assign_claim(self.claim.pk)
        second_claim = Claim.objects.create(claim_number='CLM-ASSIGN-2', customer=self.customer, policy=self.policy,
            vehicle=self.vehicle, incident_date=date.today(), incident_type='collision', incident_severity='minor',
            location='Test', claim_amount=Decimal('500'), status=ClaimStatus.SUBMITTED)
        self.assertIsNone(auto_assign_claim(second_claim.pk).assigned_adjuster_id)
        self.assertEqual(Claim.objects.filter(assigned_adjuster=employee, status=ClaimStatus.SUBMITTED).count(), 1)

