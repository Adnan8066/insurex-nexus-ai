from django.test import SimpleTestCase

from apps.assessments import fraud_rules


class TriageHeuristicConfigTests(SimpleTestCase):
    def test_config_is_versioned_and_labelled_as_triage(self):
        self.assertEqual(fraud_rules.TRIAGE_HEURISTIC_VERSION, 'v1')
        self.assertEqual(fraud_rules.TRIAGE_HEURISTIC_LABEL, 'Triage Priority Score (Heuristic v1)')

    def test_weights_come_from_the_versioned_file(self):
        self.assertEqual(fraud_rules.RED_FLAG_POINTS['repeat_vehicle'], 25)
        self.assertEqual(fraud_rules.RED_FLAG_POINTS['late_report'], 10)
        self.assertEqual(len(fraud_rules.RED_FLAG_POINTS), 10)
        self.assertEqual(fraud_rules.ALERT_MIN_RED_FLAGS, 2)
        self.assertEqual(fraud_rules.MAX_COMBINED_SCORE, 99.0)
