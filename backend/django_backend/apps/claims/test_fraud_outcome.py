import csv
import tempfile
from datetime import date, timedelta
from decimal import Decimal
from io import StringIO
from pathlib import Path

from django.core.management import call_command
from django.core.management.base import CommandError
from django.test import TestCase
from django.utils import timezone
from rest_framework.test import APIClient

from apps.accounts.models import Role, User
from apps.claims.models import Claim
from apps.claims.tests import make_customer_records


class FraudOutcomeTests(TestCase):
    def setUp(self):
        self.customer, self.policy, self.vehicle = make_customer_records('outcomecust', 'VINOUTCOME0000001')
        self.employee = User.objects.create_user(
            username='outcomeemp', email='outcomeemp@insure.com', password='x', role=Role.EMPLOYEE,
        )
        self.investigator = User.objects.create_user(
            username='outcomeinv', email='outcomeinv@insure.com', password='x', role=Role.INVESTIGATOR,
        )
        self.claim = self.make_claim('CLM-OUT00001')
        self.client = APIClient()

    def make_claim(self, number, days_ago=5, **extra):
        values = {'incident_type': 'collision', 'incident_severity': 'minor', 'claim_amount': Decimal('25000'), **extra}
        return Claim.objects.create(
            claim_number=number, customer=self.customer, policy=self.policy, vehicle=self.vehicle,
            incident_date=timezone.localdate() - timedelta(days=days_ago), location='Ernakulam', **values,
        )

    def record(self, claim, payload, user=None):
        self.client.force_authenticate(user or self.employee)
        return self.client.post(f'/api/v1/claims/{claim.pk}/fraud-outcome/', payload, format='json')

    def test_staff_can_record_fraud_outcome(self):
        response = self.record(self.claim, {'outcome': 'fraud', 'note': 'Photos reused', 'outcome_date': '2026-11-01'})
        self.assertEqual(response.status_code, 200, response.content)
        self.claim.refresh_from_db()
        self.assertEqual(self.claim.fraud_outcome, 'fraud')
        self.assertEqual(self.claim.fraud_outcome_date, date(2026, 11, 1))
        self.assertEqual(self.claim.fraud_outcome_note, 'Photos reused')

    def test_investigator_can_record_outcome_on_assigned_claim(self):
        self.claim.assigned_investigator = self.investigator
        self.claim.save(update_fields=['assigned_investigator'])
        self.assertEqual(self.record(self.claim, {'outcome': 'genuine'}, self.investigator).status_code, 200)

    def test_investigator_cannot_record_outcome_on_unassigned_claim(self):
        self.assertEqual(self.record(self.claim, {'outcome': 'genuine'}, self.investigator).status_code, 404)

    def test_invalid_outcome_is_rejected(self):
        self.assertEqual(self.record(self.claim, {'outcome': 'maybe'}).status_code, 400)
        self.claim.refresh_from_db()
        self.assertEqual(self.claim.fraud_outcome, '')

    def test_bad_date_and_long_note_are_rejected(self):
        self.assertEqual(self.record(self.claim, {'outcome': 'fraud', 'outcome_date': '01/11/2026'}).status_code, 400)
        self.assertEqual(self.record(self.claim, {'outcome': 'fraud', 'note': 'x' * 501}).status_code, 400)

    def test_customer_cannot_record_outcome(self):
        self.client.force_authenticate(self.customer)
        response = self.client.post(f'/api/v1/claims/{self.claim.pk}/fraud-outcome/', {'outcome': 'fraud'}, format='json')
        self.assertEqual(response.status_code, 403)

    def test_export_writes_only_labelled_claims(self):
        self.record(self.claim, {'outcome': 'fraud', 'outcome_date': '2026-11-01'})
        self.make_claim('CLM-OUT00002', days_ago=9)  # no outcome yet, must be left out
        with tempfile.TemporaryDirectory() as folder:
            path = Path(folder) / 'claims.csv'
            out = StringIO()
            call_command('export_claim_outcomes', str(path), stdout=out)
            rows = list(csv.DictReader(path.open(encoding='utf-8')))
        self.assertEqual(len(rows), 1)
        self.assertEqual(rows[0]['claim_id'], 'CLM-OUT00001')
        self.assertEqual(rows[0]['outcome'], 'fraud')
        self.assertEqual(rows[0]['district'], 'Ernakulam')
        self.assertEqual(rows[0]['police_report'], 'N')
        self.assertNotIn('customer', ' '.join(rows[0].keys()))

    def test_export_fails_when_nothing_is_labelled(self):
        with tempfile.TemporaryDirectory() as folder:
            with self.assertRaises(CommandError):
                call_command('export_claim_outcomes', str(Path(folder) / 'empty.csv'), stdout=StringIO())
