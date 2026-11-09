from datetime import date
from decimal import Decimal
from unittest import mock

from django.test import TestCase

from apps.assessments.ai_views import predict_repair_cost_internal
from apps.assessments.repair_estimate import (
    RepairEstimateUnavailable, depreciation_for_age, estimate_repair_cost,
)
from apps.claims.models import Claim
from apps.claims.tests import make_customer_records


class RepairEstimateTests(TestCase):
    def setUp(self):
        self.customer, self.policy, self.vehicle = make_customer_records('repaircust', 'VINREPAIR00000001')
        self.vehicle.make, self.vehicle.model = 'Maruti Suzuki', 'Brezza'
        self.vehicle.purchase_price = Decimal('1000000')
        self.vehicle.purchase_date = date(2024, 1, 10)
        self.vehicle.save()

    def claim(self, severity='minor', incident_type='collision', **extra):
        return Claim.objects.create(
            claim_number=f'CLM-R{Claim.objects.count():06d}', customer=self.customer, policy=self.policy,
            vehicle=self.vehicle, incident_date=date(2026, 10, 1), incident_type=incident_type,
            incident_severity=severity, location='Kochi', claim_amount=Decimal('30000'), **extra,
        )

    def test_irdai_depreciation_schedule(self):
        self.assertEqual(depreciation_for_age(3), 0.05)
        self.assertEqual(depreciation_for_age(12), 0.15)
        self.assertEqual(depreciation_for_age(30), 0.30)
        self.assertEqual(depreciation_for_age(60), 0.50)
        self.assertEqual(depreciation_for_age(61), 0.55)
        self.assertEqual(depreciation_for_age(400), 0.80)

    def test_minor_dent_is_labour_plus_small_parts(self):
        # No body style and a ₹10 lakh price -> SUV/MUV labour ₹6,000 + 0.2% of price ₹2,000.
        result = estimate_repair_cost(self.claim('minor'))
        self.assertEqual(result['cost'], 8000)
        self.assertEqual(result['breakdown']['segment'], 'suv/muv')
        self.assertEqual(result['breakdown']['insured_declared_value'], 700000)  # 33 months -> 30%
        self.assertFalse(result['breakdown']['constructive_total_loss'])

    def test_body_style_sets_labour_segment(self):
        self.vehicle.body_style = 'Hatchback'
        self.vehicle.save()
        # Hatchback labour ₹4,500 + ₹2,000 parts.
        self.assertEqual(estimate_repair_cost(self.claim('minor'))['cost'], 6500)

    def test_total_loss_pays_idv_and_glass_is_a_windshield(self):
        self.assertEqual(estimate_repair_cost(self.claim('total_loss', 'theft'))['cost'], 700000)
        self.assertTrue(estimate_repair_cost(self.claim('total_loss'))['breakdown']['constructive_total_loss'])
        # Fitting ₹2,360 + 0.7% of price ₹7,000, whatever severity was picked.
        glass = estimate_repair_cost(self.claim('major', 'glass'))
        self.assertEqual((glass['cost'], glass['time_estimate']), (9400, 1))

    def test_repair_above_75_percent_of_idv_is_constructive_total_loss(self):
        self.vehicle.purchase_price = Decimal('100000')
        self.vehicle.purchase_date = date(2005, 1, 1)
        self.vehicle.save()
        # IDV ₹20,000 (80% depreciation); major ₹12,000 + ₹4,000 = ₹16,000 > ₹15,000 -> pay the IDV.
        result = estimate_repair_cost(self.claim('major'))
        self.assertEqual(result['cost'], 20000)
        self.assertTrue(result['breakdown']['constructive_total_loss'])
        self.assertIsNone(result['time_estimate'])

    def test_app_claims_use_estimate_not_dataset_model(self):
        with mock.patch('apps.assessments.ai_views.predict_repair_cost_ml') as model:
            result = predict_repair_cost_internal(self.claim('moderate'))
        model.assert_not_called()
        self.assertEqual(result['cost'], 18500)  # ₹6,500 labour + 1.2% of ₹10 lakh

    def test_falls_back_to_model_without_purchase_price_or_for_imported_rows(self):
        self.vehicle.purchase_price = None
        self.vehicle.save()
        with self.assertRaises(RepairEstimateUnavailable):
            estimate_repair_cost(self.claim())
        fake = {'cost': 1.0, 'breakdown': {}, 'time_estimate': None, 'comparable_count': None}
        with mock.patch('apps.assessments.ai_views.predict_repair_cost_ml', return_value=fake) as model:
            self.assertEqual(predict_repair_cost_internal(self.claim()), fake)
            imported = self.claim(ai_assessment={'source_dataset': 'insurance_claims', 'source_data': {'age': 40}})
            self.assertEqual(predict_repair_cost_internal(imported), fake)
        self.assertEqual(model.call_count, 2)
