from decimal import Decimal
from io import StringIO
from unittest import mock

from django.core.management import call_command
from django.core.management.base import CommandError
from django.test import TestCase, override_settings

from apps.accounts.models import Role, User
from apps.assessments.models import ClaimAssessment
from apps.claims.management.commands.load_demo import CLAIMS, DEFAULT_PASSWORD, DEMO_DOMAIN
from apps.claims.models import Claim, ClaimStatusHistory, ClaimTimeline
from apps.claims.tests import make_customer_records
from apps.investigations.models import FraudAlert, Investigation
from apps.policies.models import Policy
from apps.vehicles.models import Vehicle


def fake_assessment(claim):
    """Stand-in for the ML scoring: the real models are slow and may be absent in CI."""
    score = Decimal('90') if claim.incident_type == 'theft' else Decimal('10')
    assessment, _ = ClaimAssessment.objects.update_or_create(
        claim=claim, defaults={'status': 'completed', 'fraud_risk_score': score,
                               'risk_level': 'high' if score > 65 else 'low'},
    )
    Claim.objects.filter(pk=claim.pk).update(fraud_risk_score=score)
    if score > 65:
        FraudAlert.objects.get_or_create(claim=claim, defaults={
            'risk_score': score, 'risk_level': 'high', 'ai_recommendation': 'Investigate.',
        })
    return assessment


def demo_users():
    return User.objects.filter(email__endswith='@' + DEMO_DOMAIN)


@override_settings(DEBUG=True)
@mock.patch('apps.assessments.ai_views.run_claim_assessment', side_effect=fake_assessment)
class LoadDemoTests(TestCase):
    def load(self, *args):
        out = StringIO()
        call_command('load_demo', *args, stdout=out, stderr=StringIO())
        return out.getvalue()

    def counts(self):
        return {
            'users': demo_users().count(),
            'claims': Claim.objects.count(),
            'policies': Policy.objects.count(),
            'vehicles': Vehicle.objects.count(),
            'history': ClaimStatusHistory.objects.count(),
            'timeline': ClaimTimeline.objects.count(),
            'assessments': ClaimAssessment.objects.count(),
            'investigations': Investigation.objects.count(),
        }

    def test_creates_logins_claims_and_assessments(self, _assess):
        output = self.load()
        roles = set(demo_users().filter(is_active=True).values_list('role', flat=True))
        self.assertEqual(roles, {Role.ADMIN, Role.EMPLOYEE, Role.INVESTIGATOR, Role.CUSTOMER})
        for role in ('admin', 'employee', 'investigator', 'customer'):
            user = User.objects.get(email=f'{role}@{DEMO_DOMAIN}')
            self.assertTrue(user.check_password(DEFAULT_PASSWORD))
            self.assertIn(user.email, output)
        self.assertIn(DEFAULT_PASSWORD, output)
        self.assertEqual(demo_users().filter(role=Role.CUSTOMER).count(), 3)
        self.assertEqual(Claim.objects.filter(claim_number__startswith='DEMO-').count(), len(CLAIMS))
        self.assertEqual(ClaimAssessment.objects.count(), len(CLAIMS))
        self.assertEqual(_assess.call_count, len(CLAIMS))

        for claim in Claim.objects.select_related('policy', 'vehicle'):
            self.assertEqual(claim.policy.customer_id, claim.vehicle.customer_id)
            self.assertEqual(claim.vehicle.policy_id, claim.policy_id)
            self.assertTrue(claim.policy.start_date <= claim.incident_date <= claim.policy.end_date)
            self.assertTrue(claim.status_history.exists())
            self.assertRegex(claim.vehicle.vin, r'^[A-HJ-NPR-Z0-9]{17}$')

        theft = Claim.objects.get(incident_type='theft')
        investigator = User.objects.get(email=f'investigator@{DEMO_DOMAIN}')
        self.assertEqual(theft.investigation.investigator, investigator)
        self.assertEqual(theft.fraud_alert.assigned_investigator, investigator)
        late = Claim.objects.get(claim_number='DEMO-CLM-0003')
        self.assertGreater((late.submitted_at.date() - late.incident_date).days, 30)

    def test_second_run_does_not_duplicate(self, _assess):
        self.load()
        first = self.counts()
        self.load()
        self.assertEqual(self.counts(), first)

    def test_reset_recreates_only_demo_data(self, _assess):
        _customer, _policy, _vehicle = make_customer_records('realcust', 'VINREALCUST000001')
        real_user = User.objects.create_user(
            username='realemp', email='realemp@insure.com', password='x', role=Role.EMPLOYEE,
        )
        self.load()
        old_ids = set(Claim.objects.filter(claim_number__startswith='DEMO-').values_list('pk', flat=True))
        first = self.counts()
        self.load('--reset', '--password', 'Another@Pass1')
        self.assertEqual(self.counts(), first)
        new_ids = set(Claim.objects.filter(claim_number__startswith='DEMO-').values_list('pk', flat=True))
        self.assertFalse(old_ids & new_ids)
        self.assertTrue(User.objects.filter(pk=real_user.pk).exists())
        self.assertTrue(Vehicle.objects.filter(vin='VINREALCUST000001').exists())
        self.assertTrue(User.objects.get(email=f'admin@{DEMO_DOMAIN}').check_password('Another@Pass1'))

    def test_model_failure_does_not_stop_the_command(self, assess):
        assess.side_effect = RuntimeError('model missing')
        self.load()
        self.assertEqual(Claim.objects.filter(claim_number__startswith='DEMO-').count(), len(CLAIMS))
        # The most suspicious claim still gets its alert and investigation.
        theft = Claim.objects.get(incident_type='theft')
        self.assertTrue(FraudAlert.objects.filter(claim=theft).exists())
        self.assertTrue(Investigation.objects.filter(claim=theft).exists())


class LoadDemoSafetyTests(TestCase):
    @override_settings(DEBUG=False)
    def test_refuses_when_debug_is_false(self):
        with self.assertRaisesMessage(CommandError, 'DEBUG is False'):
            call_command('load_demo', stdout=StringIO())
        self.assertFalse(demo_users().exists())

    @override_settings(DEBUG=False)
    @mock.patch('apps.assessments.ai_views.run_claim_assessment', side_effect=fake_assessment)
    def test_allow_production_overrides(self, _assess):
        call_command('load_demo', '--allow-production', stdout=StringIO(), stderr=StringIO())
        self.assertEqual(demo_users().count(), 6)
