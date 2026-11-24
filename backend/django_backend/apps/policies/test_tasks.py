from datetime import timedelta
from decimal import Decimal

from django.contrib.auth import get_user_model
from django.test import TestCase
from django.utils import timezone

from apps.notifications.models import Notification
from apps.policies.models import Policy, PolicyStatus, PolicyType
from apps.policies.tasks import check_policy_expirations, send_renewal_reminders


class PolicyBackgroundJobTests(TestCase):
    @classmethod
    def setUpTestData(cls):
        cls.customer = get_user_model().objects.create_user(
            username='task-cust', email='task-cust@example.com', password='x', role='customer',
        )
        cls.today = timezone.localdate()

    def make_policy(self, number, end_date, status=PolicyStatus.ACTIVE):
        return Policy.objects.create(
            policy_number=number, customer=self.customer, type=PolicyType.choices[0][0], status=status,
            start_date=end_date - timedelta(days=365), end_date=end_date,
            premium=Decimal('1000'), deductible=Decimal('100'),
        )

    def test_expiry_marks_past_policies_and_is_idempotent(self):
        ended = self.make_policy('POL-END-1', self.today - timedelta(days=1))
        running = self.make_policy('POL-RUN-1', self.today + timedelta(days=100))

        self.assertEqual(check_policy_expirations(today=self.today), 1)
        ended.refresh_from_db()
        running.refresh_from_db()
        self.assertEqual(ended.status, PolicyStatus.EXPIRED)
        self.assertEqual(running.status, PolicyStatus.ACTIVE)

        # A second run changes nothing.
        self.assertEqual(check_policy_expirations(today=self.today), 0)

    def test_renewal_reminder_sent_once_per_window(self):
        self.make_policy('POL-REM-30', self.today + timedelta(days=30))
        self.assertEqual(send_renewal_reminders(today=self.today), 1)

        reminders = Notification.objects.filter(recipient=self.customer, notification_type='reminder')
        self.assertEqual(reminders.count(), 1)
        self.assertEqual(reminders.first().title, 'Policy renewal due in 30 days')

        # Running again on the same day does not send a duplicate.
        self.assertEqual(send_renewal_reminders(today=self.today), 0)
        self.assertEqual(reminders.count(), 1)

    def test_no_reminder_for_policies_outside_the_windows(self):
        self.make_policy('POL-FAR-1', self.today + timedelta(days=45))
        self.assertEqual(send_renewal_reminders(today=self.today), 0)
