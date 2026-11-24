"""Background jobs for policy lifecycle: expiry and renewal reminders.

Both tasks are idempotent. Running them twice does not expire a policy twice or send
the same reminder twice.
"""
import logging
from datetime import timedelta

from django.db.utils import OperationalError
from django.utils import timezone

from apps.notifications.models import Notification, NotificationType
from apps.notifications.services import create_in_app_notification
from common.tasks import shared_task

from .models import Policy, PolicyStatus

logger = logging.getLogger(__name__)

# Days before the end date on which a customer gets a renewal reminder.
REMINDER_WINDOWS_DAYS = (30, 15, 7)

RETRY_OPTIONS = {'autoretry_for': (OperationalError,), 'retry_backoff': True, 'max_retries': 3}


@shared_task(**RETRY_OPTIONS)
def check_policy_expirations(today=None):
    """Mark active policies whose end date has passed as expired. Returns how many changed."""
    today = today or timezone.localdate()
    # Filtering on status means a second run finds nothing to change.
    expired = Policy.objects.filter(status=PolicyStatus.ACTIVE, end_date__lt=today)
    changed = expired.update(status=PolicyStatus.EXPIRED)
    logger.info('Expired %s policies ending before %s', changed, today)
    return changed


@shared_task(**RETRY_OPTIONS)
def send_renewal_reminders(today=None):
    """Send each customer one reminder per window for a policy that is about to end."""
    today = today or timezone.localdate()
    sent = 0
    for days in REMINDER_WINDOWS_DAYS:
        due_on = today + timedelta(days=days)
        for policy in Policy.objects.filter(status=PolicyStatus.ACTIVE, end_date=due_on).select_related('customer'):
            title = f'Policy renewal due in {days} days'
            # The title includes the window, so each window is sent once per policy.
            already_sent = Notification.objects.filter(
                recipient=policy.customer,
                notification_type=NotificationType.REMINDER,
                related_object_type='policy',
                related_object_id=str(policy.pk),
                title=title,
            ).exists()
            if already_sent:
                continue
            create_in_app_notification(
                policy.customer, NotificationType.REMINDER, title,
                f'Policy {policy.policy_number} ends on {policy.end_date:%d %b %Y}. Contact us to renew.',
                link=f'/policies/{policy.pk}', related_object_type='policy', related_object_id=policy.pk,
            )
            sent += 1
    logger.info('Sent %s renewal reminders for %s', sent, today)
    return sent
