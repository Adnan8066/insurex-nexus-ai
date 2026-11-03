"""Automatic hand-off of new work to employees.

Claims are routed only by the qualified RL model (``rl_views.auto_assign_new_claim``);
when it cannot assign one, the claim waits and admins are notified. Policy
requests go to the employee with the fewest open requests. Admins are not part
of the rotation; they are notified when work cannot be handed over, so nothing
waits unseen.
"""

from django.contrib.auth import get_user_model
from django.db import transaction

from apps.accounts.models import Role
from apps.notifications.services import create_in_app_notification

OPEN_CLAIM_STATUSES = ['submitted', 'under_review', 'ai_assessment']


def available_employees():
    """Active employees who can take work; demo routing profiles and staff marked unavailable are skipped."""
    return (
        get_user_model().objects.filter(role=Role.EMPLOYEE, is_active=True)
        .exclude(routing_profile__is_demo=True)
        .exclude(routing_profile__is_available=False)
        .order_by('id')
    )


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
    """Hand unassigned customer policy requests and open claims to available employees.

    Called when an employee joins (and by ``manage.py assign_waiting_claims``),
    so work that arrived while nobody could take it does not stay unassigned.
    Claims are retried through the RL model; admins were already notified when
    each claim first waited, so retries stay quiet.
    """
    from django.db.models import F
    from .rl_views import auto_assign_new_claim
    from apps.claims.models import Claim
    from apps.policies.models import PolicyApplication

    if not available_employees().exists():
        return 0, 0
    waiting_requests = PolicyApplication.objects.filter(
        status=PolicyApplication.Status.QUOTED, assigned_to__isnull=True, created_by_id=F('customer_id'),
    ).order_by('created_at')
    requests_assigned = sum(1 for application in waiting_requests if assign_policy_request(application))
    waiting_claims = Claim.objects.filter(
        assigned_adjuster__isnull=True, status__in=OPEN_CLAIM_STATUSES,
    ).order_by('submitted_at')
    claims_assigned = sum(
        1 for claim in waiting_claims if auto_assign_new_claim(claim, notify_admins=False)
    )
    return requests_assigned, claims_assigned
