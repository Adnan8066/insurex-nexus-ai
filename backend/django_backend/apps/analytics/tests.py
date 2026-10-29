from datetime import date, timedelta
from decimal import Decimal

from django.contrib.auth import get_user_model
from django.test import SimpleTestCase, override_settings
from django.urls import reverse
from django.utils import timezone
from rest_framework.test import APITestCase

from apps.analytics.views import resolve_timeframe
from apps.claims.models import Claim, ClaimStatus
from apps.policies.models import Policy, PolicyStatus, PolicyType
from apps.vehicles.models import Vehicle
from common.risk import fraud_risk_band


class FraudRiskBandTests(SimpleTestCase):
    def test_band_boundaries(self):
        self.assertEqual(fraud_risk_band(None), 'low')
        self.assertEqual(fraud_risk_band(29.99), 'low')
        self.assertEqual(fraud_risk_band(30), 'medium')
        self.assertEqual(fraud_risk_band(65), 'medium')
        self.assertEqual(fraud_risk_band(65.01), 'high')


class ResolveTimeframeTests(SimpleTestCase):
    def test_ranges(self):
        today = date(2026, 10, 28)
        self.assertEqual(resolve_timeframe('week', today), (date(2026, 10, 22), today))
        self.assertEqual(resolve_timeframe('month', today), (date(2026, 9, 29), today))
        self.assertEqual(resolve_timeframe('quarter', today), (date(2026, 10, 1), today))
        self.assertEqual(resolve_timeframe('ytd', today), (date(2026, 1, 1), today))
        self.assertEqual(resolve_timeframe('year', today), (date(2025, 1, 1), date(2025, 12, 31)))
        self.assertEqual(resolve_timeframe('bogus', today), (None, None))


@override_settings(ALLOWED_HOSTS=['testserver'], SECURE_SSL_REDIRECT=False)
class DashboardAnalyticsTests(APITestCase):
    @classmethod
    def setUpTestData(cls):
        User = get_user_model()
        cls.admin = User.objects.create_user(username='admin', email='admin@example.com', password='x', role='admin')
        cls.customer = User.objects.create_user(username='cust', email='cust@example.com', password='x', role='customer')
        today = timezone.localdate()
        policy = Policy.objects.create(
            policy_number='POL-TEST-1', customer=cls.customer, type=PolicyType.choices[0][0],
            status=PolicyStatus.ACTIVE, start_date=today - timedelta(days=10), end_date=today + timedelta(days=355),
            premium=Decimal('1000'), deductible=Decimal('100'),
        )
        vehicle = Vehicle.objects.create(
            customer=cls.customer, policy=policy, make='Make', model='Model', year=2020,
            vin='VINTEST0000000001', color='Blue', license_plate='AB12', license_state='KA',
        )

        def claim(number, days_ago, status, fraud, total_loss, amount):
            created = Claim.objects.create(
                claim_number=number, customer=cls.customer, policy=policy, vehicle=vehicle,
                incident_date=today, incident_type='collision', incident_severity='minor',
                location='Somewhere', claim_amount=Decimal(amount), status=status,
                fraud_risk_score=Decimal(fraud), total_loss_probability=Decimal(total_loss),
            )
            Claim.objects.filter(pk=created.pk).update(submitted_at=timezone.now() - timedelta(days=days_ago))

        claim('CLM-1', 1, ClaimStatus.SUBMITTED, 10, 0, 1000)
        claim('CLM-2', 3, ClaimStatus.APPROVED, 50, 80, 2000)
        claim('CLM-3', 20, ClaimStatus.APPROVED, 90, 0, 3000)

    def setUp(self):
        self.client.force_authenticate(self.admin)

    def test_summary_respects_timeframe(self):
        week = self.client.get(reverse('dashboard-summary'), {'timeframe': 'week'}).json()
        month = self.client.get(reverse('dashboard-summary'), {'timeframe': 'month'}).json()
        self.assertEqual(week['claims']['total'], 2)
        self.assertEqual(month['claims']['total'], 3)
        self.assertEqual(week['period']['label'], 'Last 7 days')

    def test_summary_lists_every_status_with_counts(self):
        data = self.client.get(reverse('dashboard-summary'), {'timeframe': 'month'}).json()
        counts = {row['status']: row['count'] for row in data['claims']['status_distribution']}
        self.assertEqual(set(counts), set(ClaimStatus.values))
        self.assertEqual(counts['approved'], 2)
        self.assertEqual(counts['submitted'], 1)
        self.assertEqual(counts['closed'], 0)
        self.assertEqual(data['claims']['total_loss_cases'], 1)
        self.assertEqual(data['claims']['repairable_cases'], 2)
        self.assertEqual(data['fraud']['high_risk_claims'], 1)

    def test_fraud_risk_bands(self):
        data = self.client.get(reverse('fraud-risk'), {'timeframe': 'month'}).json()
        self.assertEqual(data['by_level'], {'low': 1, 'medium': 1, 'high': 1})

    def test_claims_trend_is_zero_filled(self):
        data = self.client.get(reverse('claims-trend'), {'timeframe': 'week'}).json()
        self.assertEqual(len(data), 7)
        self.assertEqual(sum(row['count'] for row in data), 2)
        monthly = self.client.get(reverse('claims-trend'), {'timeframe': 'ytd', 'granularity': 'month'}).json()
        self.assertEqual(len(monthly), timezone.localdate().month)
        self.assertTrue(all(row['date'].endswith('-01') for row in monthly))

    def test_customer_sees_only_own_claims(self):
        other = get_user_model().objects.create_user(username='other', email='other@example.com', password='x', role='customer')
        self.client.force_authenticate(other)
        data = self.client.get(reverse('claims-trend'), {'timeframe': 'month'}).json()
        self.assertEqual(sum(row['count'] for row in data), 0)


class CustomerAnalyticsLeakTests(DashboardAnalyticsTests):
    def setUp(self):
        self.client.force_authenticate(self.customer)

    def test_customer_dashboard_omits_fraud_and_portfolio_totals(self):
        data = self.client.get(reverse('dashboard-summary')).json()
        self.assertEqual(data['claims']['total'], 3)
        self.assertNotIn('fraud', data)
        self.assertNotIn('customers', data)
        self.assertNotIn('total_loss_cases', data['claims'])

    def test_customer_cannot_read_fraud_risk_bands(self):
        self.assertEqual(self.client.get(reverse('fraud-risk')).status_code, 403)

    def test_claims_trend_rejects_bad_days(self):
        self.assertEqual(self.client.get(reverse('claims-trend'), {'days': 'abc'}).status_code, 400)
        self.assertEqual(self.client.get(reverse('claims-trend'), {'days': '3000000'}).status_code, 400)

    # Inherited staff-only assertions do not apply to customers.
    test_summary_respects_timeframe = None
    test_summary_lists_every_status_with_counts = None
    test_fraud_risk_bands = None
    test_claims_trend_is_zero_filled = None
    test_customer_sees_only_own_claims = None
