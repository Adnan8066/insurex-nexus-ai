"""Employee availability and hand-off of customer policy requests."""

from django.contrib.auth import get_user_model
from django.db.models import Count, F, Q
from django.core.exceptions import ObjectDoesNotExist
from django.utils import timezone

from apps.accounts.models import Role
from apps.notifications.services import create_in_app_notification

OPEN_CLAIM_STATUSES = ['submitted', 'under_review', 'ai_assessment']


def available_employees():
    """Return active employees within capacity and, when configured, on shift."""
    employees = (
        get_user_model().objects.filter(role=Role.EMPLOYEE, is_active=True)
        .select_related('routing_profile')
        .annotate(active_assigned_claim_count=Count(
            'assigned_claims', filter=Q(assigned_claims__status__in=OPEN_CLAIM_STATUSES + ['investigation'])
        ))
        .exclude(routing_profile__is_demo=True)
        .exclude(routing_profile__is_available=False)
        .exclude(routing_profile__availability_status__in=['busy', 'on_leave', 'off_duty', 'temporarily_unavailable'])
        .filter(
            Q(routing_profile__isnull=True, active_assigned_claim_count__lt=10)
            | Q(active_assigned_claim_count__lt=F('routing_profile__max_claim_capacity'))
        )
        .order_by('id')
    )
    now = timezone.localtime()
    weekday = now.strftime('%a').lower()
    eligible = []
    for employee in employees:
        try:
            profile = employee.routing_profile
        except ObjectDoesNotExist:
            profile = None
        if profile is not None:
            if profile.working_days and weekday not in profile.working_days:
                continue
            if profile.shift_start_time and profile.shift_end_time:
                if not profile.shift_start_time <= now.time() <= profile.shift_end_time:
                    continue
        eligible.append(employee)
    return eligible


def _display_name(user):
    return user.get_full_name() or user.email


def _notify_admins_unassigned(title, message, link, related_object_type, related_object_id):
    for admin in get_user_model().objects.filter(role=Role.ADMIN, is_active=True):
        create_in_app_notification(
            admin, 'system', title, message, link=link, priority='high',
            related_object_type=related_object_type, related_object_id=related_object_id,
        )


def notify_claim_assignee(claim, employee):
    create_in_app_notification(
        employee, 'claim', 'New claim assigned to you',
        f'Claim {claim.claim_number} was assigned to you for review.',
        link=f'/claims/{claim.id}', related_object_type='claim', related_object_id=claim.id,
    )


def assign_policy_request(application):
    """Give a customer's policy request to the employee with the fewest open requests."""
    from apps.policies.models import PolicyApplication

    employees = list(available_employees())
    if not employees:
        _notify_admins_unassigned(
            'Policy request waiting: no employee available',
            f'{_display_name(application.customer)} requested a policy, but no employee is available to review it. '
            'Create an employee; waiting requests are handed over automatically.',
            '/policies/requests', 'policy_application', application.pk,
        )
        return None
    open_counts = {
        employee.id: PolicyApplication.objects.filter(
            assigned_to=employee, status=PolicyApplication.Status.QUOTED,
        ).count()
        for employee in employees
    }
    employee = min(employees, key=lambda item: (open_counts[item.id], item.id))
    application.assigned_to = employee
    application.save(update_fields=['assigned_to', 'updated_at'])
    customer = _display_name(application.customer)
    create_in_app_notification(
        employee, 'policy', 'New policy request assigned to you',
        f'{customer} requested a policy (quoted premium {application.quoted_premium}).',
        link='/policies/requests', related_object_type='policy_application', related_object_id=application.pk,
    )
    return employee


def assign_waiting_work():
    """Hand unassigned customer policy requests to eligible employees."""
    from django.db.models import F
    from apps.policies.models import PolicyApplication

    if not available_employees():
        return 0, 0
    waiting_requests = PolicyApplication.objects.filter(
        status=PolicyApplication.Status.QUOTED, assigned_to__isnull=True, created_by_id=F('customer_id'),
    ).order_by('created_at')
    requests_assigned = sum(1 for application in waiting_requests if assign_policy_request(application))
    return requests_assigned, 0
