from datetime import timedelta
from decimal import Decimal
from unittest import mock

import pandas as pd
from django.test import TestCase
from django.utils import timezone

from apps.assessments.ai_views import claim_model_input
from apps.assessments.fraud_rules import connected_claims, red_flags
from apps.claims.models import Claim
from apps.claims.tests import make_customer_records


class RedFlagTests(TestCase):
    @classmethod
    def setUpTestData(cls):
        cls.customer, cls.policy, cls.vehicle = make_customer_records('flagged', 'VINFLAG0000000001')

    def make_claim(self, days_ago=2, **extra):
        values = {
            'incident_type': 'collision', 'incident_severity': 'minor', 'claim_amount': Decimal('1000'),
            **extra,
        }
        return Claim.objects.create(
            claim_number=f'CLM-F{Claim.objects.count() + 1:05d}', customer=self.customer, policy=self.policy,
            vehicle=self.vehicle, incident_date=timezone.localdate() - timedelta(days=days_ago),
            location='Somewhere', **values,
        )

    def codes(self, claim):
        return {flag['code'] for flag in red_flags(claim)}

    def test_ordinary_claim_raises_no_flags(self):
        self.assertEqual(self.codes(self.make_claim()), set())

    def test_new_policy_late_report_and_missing_police_report(self):
        self.policy.start_date = timezone.localdate() - timedelta(days=50)
        self.policy.save(update_fields=['start_date'])
        claim = self.make_claim(days_ago=40, incident_type='theft', police_report=False)
        self.assertEqual(self.codes(claim), {'new_policy', 'late_report', 'theft_without_police_report'})

    def test_amount_well_above_estimate(self):
        claim = self.make_claim(claim_amount=Decimal('3000'), estimated_repair_cost=Decimal('1000'))
        self.assertIn('amount_over_estimate', self.codes(claim))

    def test_repeat_claims_on_customer_and_vehicle(self):
        self.make_claim(days_ago=60)
        self.make_claim(days_ago=30)
        claim = self.make_claim()
        self.assertTrue({'frequent_claims', 'repeat_vehicle'} <= self.codes(claim))
        self.assertEqual(connected_claims(claim)['connected_claims'], 2)


class ModelInputTests(TestCase):
    def test_amounts_are_converted_to_dataset_currency_and_severity_kept_apart(self):
        customer, policy, vehicle = make_customer_records('rupees', 'VINRUPEE000000001')
        claim = Claim.objects.create(
            claim_number='CLM-R00001', customer=customer, policy=policy, vehicle=vehicle,
            incident_date=timezone.localdate(), incident_type='collision', incident_severity='minor',
            location='Somewhere', claim_amount=Decimal('83000'),
        )
        with mock.patch('apps.assessments.ai_views.CURRENCY_PER_DATASET_UNIT', 83.0):
            row = claim_model_input(claim)
        self.assertAlmostEqual(row['total_claim_amount'], 1000.0)
        self.assertAlmostEqual(row['policy_annual_premium'], 1000 / 83)
        self.assertEqual(row['incident_severity'], 'Trivial Damage')


class ScoreReasonTests(TestCase):
    def test_only_values_that_raise_the_score_are_reasons(self):
        from ml_service import _score_reasons

        class FakeModel:
            classes_ = [0, 1]

            def predict_proba(self, frame):
                risk = 0.2 + (0.5 if frame.at[0, 'incident_severity'] == 'Major Damage' else 0)
                return [[1 - risk, risk]]

        frame = pd.DataFrame([{'incident_severity': 'Major Damage', 'witnesses': 3}])
        reasons = _score_reasons(
            FakeModel(), frame, 70.0, {'incident_severity': 'Minor Damage', 'witnesses': 1.0},
        )
        self.assertEqual([reason['feature'] for reason in reasons], ['incident_severity'])
        self.assertEqual(reasons[0]['points'], 50.0)
