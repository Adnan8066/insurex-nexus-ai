"""Automatic hand-off of new work to employees.

Claims are routed by the RL model only once it passes its evaluation gate
(``rl_views.auto_assign_new_claim``). Until then, and for policy requests, work
goes to the least-busy available employee: the same least-workload rule the RL
model is benchmarked against. Admins are not part of the rotation.
"""

from django.contrib.auth import get_user_model
from django.db import transaction

from apps.accounts.models import Role
from apps.notifications.services import create_in_app_notification

OPEN_CLAIM_STATUSES = ['submitted', 'under_review', 'ai_assessment']
# Simulator's wait-time units (rl/environment.py): queue length and work units.
QUEUE_WAIT_UNIT = 1.5
SERVICE_CAPACITY_PER_STEP = 4.0


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


def least_busy_claim_handler():
    """Employee with the shortest estimated wait for a new claim, or None."""
    from .rl_views import open_claim_load

    best, best_key = None, None
    for employee in available_employees():
        queue_length, workload = open_claim_load(employee)
        key = (queue_length * QUEUE_WAIT_UNIT + workload / SERVICE_CAPACITY_PER_STEP, queue_length, employee.id)
        if best_key is None or key < best_key:
            best, best_key = employee, key
    return best


def assign_claim_to_least_busy(claim):
    """Assign an unassigned open claim to the least-busy employee. Returns the employee or None."""
    from apps.claims.models import Claim, ClaimTimeline

    employee = least_busy_claim_handler()
    if employee is None:
        return None
    with transaction.atomic():
        # Conditional update so a manual or RL assignment made meanwhile is kept.
        updated = Claim.objects.filter(
            pk=claim.pk, assigned_adjuster__isnull=True, status__in=OPEN_CLAIM_STATUSES,
        ).update(assigned_adjuster=employee)
        if not updated:
            return None
        ClaimTimeline.objects.create(
            claim=claim,
            status=claim.status,
            title='Automatically Assigned to Adjuster',
            description=f'Claim was assigned to {_display_name(employee)}, the employee with the lightest current workload.',
            is_system=True,
        )
    claim.assigned_adjuster = employee
    notify_claim_assignee(claim, employee)
    return employee


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
