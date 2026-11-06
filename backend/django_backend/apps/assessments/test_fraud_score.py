from apps.assessments.fraud_rules import ALERT_MIN_RED_FLAGS, MAX_COMBINED_SCORE, RED_FLAG_POINTS, combined_fraud_score
from common.risk import fraud_risk_band
from django.test import SimpleTestCase


def flag(code):
    return {'code': code, 'message': code, 'points': RED_FLAG_POINTS[code]}


class CombinedFraudScoreTests(SimpleTestCase):
    def test_no_flags_keeps_model_score(self):
        self.assertEqual(combined_fraud_score(23.6, []), 23.6)

    def test_flags_add_their_points(self):
        score = combined_fraud_score(23.6, [flag('repeat_vehicle'), flag('new_policy')])
        self.assertEqual(score, 68.6)
        self.assertEqual(fraud_risk_band(score), 'high')

    def test_two_flags_reach_at_least_moderate_even_with_low_model_score(self):
        score = combined_fraud_score(0.0, [flag('late_report'), flag('late_report')])
        self.assertGreaterEqual(score, 30)
        self.assertEqual(fraud_risk_band(score), 'medium')

    def test_single_flag_does_not_lift_low_score_to_moderate(self):
        self.assertEqual(combined_fraud_score(5.0, [flag('late_report')]), 15.0)

    def test_score_never_reaches_certainty(self):
        flags = [flag(code) for code in RED_FLAG_POINTS]
        self.assertEqual(combined_fraud_score(90.0, flags), MAX_COMBINED_SCORE)

    def test_threshold_for_two_flags_is_the_alert_minimum(self):
        self.assertEqual(ALERT_MIN_RED_FLAGS, 2)
