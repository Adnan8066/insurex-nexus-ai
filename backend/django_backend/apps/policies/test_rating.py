from datetime import date
from decimal import Decimal

from django.test import SimpleTestCase, override_settings

from apps.policies.services.rating import calculate_premium, tp_premium, zone_for

TODAY = date(2026, 11, 19)


def line_amount(quote, label_start):
    for line in quote.breakdown['lines']:
        if line['label'].startswith(label_start):
            return Decimal(line['amount'])
    raise AssertionError(f'No line starting with {label_start!r}')


class TpPremiumSlabTests(SimpleTestCase):
    def test_third_party_slabs_follow_engine_capacity(self):
        self.assertEqual(tp_premium(999), Decimal('2094.00'))
        self.assertEqual(tp_premium(1000), Decimal('3416.00'))
        self.assertEqual(tp_premium(1500), Decimal('3416.00'))
        self.assertEqual(tp_premium(1501), Decimal('7897.00'))

    def test_engine_capacity_is_required_for_third_party(self):
        with self.assertRaises(ValueError):
            tp_premium(None)


class ZoneTests(SimpleTestCase):
    def test_metro_cities_are_zone_a_others_zone_b(self):
        self.assertEqual(zone_for('Mumbai'), 'A')
        self.assertEqual(zone_for(' chennai '), 'A')
        self.assertEqual(zone_for('Kochi'), 'B')
        self.assertEqual(zone_for(''), 'B')


@override_settings()
class PremiumCalculationTests(SimpleTestCase):
    def test_comprehensive_zone_b_no_claim_years_zero(self):
        # 2026 car, age 0 -> 5% depreciation -> IDV 23,75,000.
        # OD = 2,375,000 x 2.5% = 59,375.00 ; TP 1500cc = 3,416 ; CPA = 350.
        # Subtotal = 63,141.00 ; GST 18% = 11,365.38 ; total = 74,506.38.
        quote = calculate_premium(
            policy_type='auto_comprehensive', ex_showroom_price=Decimal('2500000'), vehicle_year=2026,
            engine_cc=1500, registration_city='Kochi', ncb_years=0, today=TODAY,
        )
        self.assertEqual(quote.breakdown['idv'], '2375000.00')
        self.assertEqual(line_amount(quote, 'Own-damage premium'), Decimal('59375.00'))
        self.assertEqual(line_amount(quote, 'Third-party premium'), Decimal('3416.00'))
        self.assertEqual(line_amount(quote, 'Compulsory personal accident'), Decimal('350.00'))
        self.assertEqual(quote.premium, Decimal('74506.38'))

    def test_ncb_discount_applies_to_own_damage_only(self):
        # NCB 2 years = 25% of OD 59,375.00 = 14,843.75 discount.
        quote = calculate_premium(
            policy_type='auto_comprehensive', ex_showroom_price=Decimal('2500000'), vehicle_year=2026,
            engine_cc=1500, registration_city='Kochi', ncb_years=2, today=TODAY,
        )
        self.assertEqual(line_amount(quote, 'No-claim bonus'), Decimal('-14843.75'))
        self.assertEqual(line_amount(quote, 'Third-party premium'), Decimal('3416.00'))
        self.assertEqual(quote.breakdown['subtotal'], '48297.25')

    def test_total_equals_sum_of_lines(self):
        quote = calculate_premium(
            policy_type='auto_comprehensive', ex_showroom_price=Decimal('2500000'), vehicle_year=2024,
            engine_cc=1200, registration_city='Mumbai', ncb_years=5,
            add_ons=['zero_depreciation', 'roadside_assistance'], today=TODAY,
        )
        lines_total = sum(Decimal(line['amount']) for line in quote.breakdown['lines'])
        self.assertEqual(quote.premium, lines_total)

    def test_third_party_only_has_no_own_damage_or_add_ons(self):
        quote = calculate_premium(
            policy_type='auto_liability', ex_showroom_price=Decimal('2500000'), vehicle_year=2026,
            engine_cc=900, registration_city='Kochi', add_ons=['zero_depreciation'], today=TODAY,
        )
        labels = [line['label'] for line in quote.breakdown['lines']]
        self.assertFalse(any('Own-damage' in label or 'Add-on' in label for label in labels))
        self.assertEqual(quote.breakdown['deductible'], '0')

    def test_standalone_own_damage_has_no_third_party_line(self):
        quote = calculate_premium(
            policy_type='auto_collision', ex_showroom_price=Decimal('2500000'), vehicle_year=2026,
            engine_cc=1500, registration_city='Kochi', today=TODAY,
        )
        labels = [line['label'] for line in quote.breakdown['lines']]
        self.assertFalse(any('Third-party' in label for label in labels))

    def test_invalid_inputs_are_rejected(self):
        base = dict(policy_type='auto_comprehensive', ex_showroom_price=Decimal('2500000'), vehicle_year=2026,
                    engine_cc=1500, registration_city='Kochi', today=TODAY)
        for overrides in ({'ncb_years': 6}, {'ncb_years': -1}, {'add_ons': ['unknown']},
                          {'ex_showroom_price': None}, {'policy_type': 'auto_bike'}):
            with self.subTest(overrides=overrides):
                with self.assertRaises(ValueError):
                    calculate_premium(**{**base, **overrides})
