from datetime import date
from types import SimpleNamespace

from django.test import SimpleTestCase

from .explain import explain_assessment, explain_fraud, explain_repair_cost, explain_total_loss, rupees


def _claim(**overrides):
    values = dict(claim_amount=150000, incident_severity='major', incident_date=date(2026, 3, 1),
                  vehicle=SimpleNamespace(year=2018))
    values.update(overrides)
    return SimpleNamespace(**values)


class RupeesTests(SimpleTestCase):
    def test_indian_digit_grouping(self):
        self.assertEqual(rupees(950), '₹950')
        self.assertEqual(rupees(54500), '₹54,500')
        self.assertEqual(rupees(760000), '₹7,60,000')
        self.assertEqual(rupees(12345678), '₹1,23,45,678')


class FraudExplanationTests(SimpleTestCase):
    def test_red_flags_and_model_reasons_ranked_without_repeats(self):
        result = explain_fraud({
            'score': 72,
            'red_flags': [{'code': 'late_report', 'message': 'Reported 9 days after the incident', 'points': 10}],
            'explanations': [
                {'feature': 'reporting_delay_days', 'value': 9, 'points': 12.0},
                {'feature': 'photos_reused_from_other_claims', 'value': 1, 'points': 30.0},
                {'feature': 'days_policy_to_incident', 'value': 10, 'points': 15.0},
            ],
        })
        self.assertEqual(
            result['summary'],
            'Fraud score 72 of 100 (high risk), mainly because 1 photo was already used on another claim, '
            'the policy started only 10 days before the incident and the claim was reported 9 days after the incident.',
        )
        # The model's late-report reason repeats the red flag, so it is dropped.
        self.assertEqual(len(result['reasons']), 3)
        self.assertEqual(result['reasons'][0]['source'], 'photos')

    def test_low_score_without_reasons(self):
        result = explain_fraud({'score': 8, 'red_flags': [], 'explanations': []})
        self.assertEqual(result['summary'], 'Fraud score 8 of 100 (low risk): nothing in this claim stands out from genuine claims.')

    def test_low_score_with_small_reasons_does_not_sound_suspicious(self):
        result = explain_fraud({'score': 14, 'explanations': [{'feature': 'past_claims_count', 'value': 1, 'points': 3}]})
        self.assertEqual(result['summary'], 'Fraud score 14 of 100 (low risk). Nothing serious stands out '
                                            '(minor points: the customer has 1 earlier claim).')

    def test_medium_score_without_reasons(self):
        self.assertIn('no single detail stands out', explain_fraud({'score': 45})['summary'])


class RepairAndTotalLossTests(SimpleTestCase):
    def test_repair_estimate_breakdown_and_inflated_claim(self):
        result = explain_repair_cost(_claim(claim_amount=172300), {
            'cost': 54500, 'time_estimate': 7,
            'breakdown': {'labour': 12000, 'parts': 42500, 'severity': 'major',
                          'segment': 'hatchback/sedan', 'ex_showroom_price': 760000},
        })
        self.assertEqual(result['summary'], 'Estimated repair ₹54,500 = garage labour ₹12,000 + parts ₹42,500, '
                                            'for major damage to a hatchback or sedan that costs ₹7,60,000 new.')
        self.assertIn('3.2 times this estimate', result['details'][-1])

    def test_constructive_total_loss(self):
        result = explain_repair_cost(_claim(), {
            'cost': 342000, 'breakdown': {'constructive_total_loss': True, 'insured_declared_value': 342000},
        })
        self.assertIn('treated as a write-off', result['summary'])

    def test_model_estimate_without_breakdown(self):
        result = explain_repair_cost(_claim(claim_amount=60000), {'cost': 65863.92, 'breakdown': {}})
        self.assertEqual(result['summary'], 'Estimated repair ₹65,864, predicted by the AI model from similar past claims.')
        self.assertIn('in line with this estimate', result['details'][0])

    def test_total_loss(self):
        result = explain_total_loss(_claim(), 35, {'breakdown': {}})
        self.assertEqual(result['summary'], '35% chance the car is a write-off (possibly a write-off).')
        self.assertEqual(result['details'], ['The customer reported major damage.', 'The car is 8 years old.'])

    def test_full_explanation_has_one_summary_per_score(self):
        result = explain_assessment(_claim(), {'cost': 50000, 'breakdown': {}}, {'score': 10}, {'probability': 5})
        self.assertEqual(set(result), {'summary', 'fraud', 'repair_cost', 'total_loss'})
        self.assertTrue(result['summary'].startswith('Fraud score 10 of 100'))
