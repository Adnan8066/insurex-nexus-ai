from datetime import date, datetime
from decimal import Decimal

from django.db.models.signals import pre_save, post_save
from django.dispatch import receiver

from .context import get_current_actor
from .models import AuditEvent


# Deliberately exclude credentials, bank details, documents, and free-text notes.
TRACKED_FIELDS = {
    'policies.policy': {
        'policy_number', 'type', 'status', 'start_date', 'end_date', 'premium',
        'deductible', 'payment_frequency', 'auto_renew', 'coverage', 'vehicle_id',
        'agent_id',
    },
    'claims.claim': {
        'claim_number', 'status', 'priority', 'claim_amount', 'estimated_repair_cost',
        'assigned_adjuster_id', 'assigned_investigator_id', 'assignment_status',
        'fraud_outcome',
    },
    'investigations.investigation': {
        'case_number', 'status', 'priority', 'investigator_id', 'fraud_alert_id',
        'estimated_completion',
    },
    'settlements.settlement': {
        'settlement_number', 'estimated_amount', 'deductible', 'depreciation_amount',
        'asset_age_years', 'zero_depreciation_applied', 'approved_amount', 'status',
        'payment_status', 'payment_method', 'approved_by_id', 'approved_at',
        'paid_by_id', 'paid_at',
    },
}


def json_value(value):
    if isinstance(value, (datetime, date)):
        return value.isoformat()
    if isinstance(value, Decimal):
        return str(value)
    return value


@receiver(pre_save)
def capture_before(sender, instance, raw=False, **kwargs):
    label = sender._meta.label_lower
    if raw or label not in TRACKED_FIELDS or not instance.pk:
        instance._audit_before = None
        return
    try:
        old = sender._base_manager.get(pk=instance.pk)
    except sender.DoesNotExist:
        instance._audit_before = None
        return
    fields = TRACKED_FIELDS[label]
    instance._audit_before = {
        field: json_value(getattr(old, field))
        for field in fields
    }


@receiver(post_save)
def record_change(sender, instance, created, raw=False, **kwargs):
    label = sender._meta.label_lower
    if raw or label not in TRACKED_FIELDS:
        return
    fields = TRACKED_FIELDS[label]
    if created:
        changes = {
            field: {'old': None, 'new': json_value(getattr(instance, field))}
            for field in fields
        }
    else:
        before = getattr(instance, '_audit_before', None)
        if before is None:
            return
        changes = {}
        for field in fields:
            new_value = json_value(getattr(instance, field))
            if before[field] != new_value:
                changes[field] = {'old': before[field], 'new': new_value}
        if not changes:
            return

    AuditEvent.objects.create(
        entity_type=label,
        entity_id=str(instance.pk),
        entity_label=str(instance)[:120],
        action='created' if created else 'updated',
        actor=get_current_actor(),
        changes=changes,
    )
