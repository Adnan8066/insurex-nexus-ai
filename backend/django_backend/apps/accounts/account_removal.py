"""Rules for removing managed accounts from the admin "Managed Accounts" page.

Many models point at the user with ``on_delete=CASCADE`` (Vehicle, Policy,
Claim, PolicyApplication, ClaimNote, InvestigationNote, ...) and deleting a
policy or vehicle cascades further into claims, assessments, investigations and
fraud alerts. Others use ``SET_NULL`` (Claim.assigned_adjuster, status history
``changed_by``, Investigation.investigator, ...), which would silently erase
who did what. So a hard delete is only allowed when Django's delete collector
shows that nothing but the account's own personal/ephemeral rows would be
touched. Otherwise the account is deactivated: the user can no longer sign in,
and every business and audit record stays intact.
"""
from collections import Counter, defaultdict

from django.apps import apps
from django.db import router
from django.db.models import ProtectedError, QuerySet, RestrictedError
from django.db.models.deletion import Collector

from .models import Role, User

MANAGED_ROLES = [Role.CUSTOMER, Role.INVESTIGATOR, Role.EMPLOYEE]

# Rows that belong only to the account itself and may go with it.
DISPOSABLE_MODELS = {
    'accounts.User',
    'accounts.UserProfile',
    'customers.Customer',
    'notifications.Notification',
    'notifications.NotificationPreference',
    'token_blacklist.OutstandingToken',
    'token_blacklist.BlacklistedToken',
    'assessments.RoutingAgentProfile',
}


def _pks(objs):
    if isinstance(objs, QuerySet):
        return set(objs.values_list('pk', flat=True))
    return {obj.pk for obj in objs}


def account_history_records(user):
    """Return {model label: count} of records a hard delete would remove or orphan."""
    collector = Collector(using=router.db_for_write(User))
    try:
        collector.collect([user])
    except (ProtectedError, RestrictedError) as exc:
        counts = Counter(obj._meta.label for obj in exc.args[1])
        return dict(counts)

    # A row can be both deleted and nulled (e.g. a vehicle cascaded from the user
    # and SET_NULL from a policy), so collect distinct pks per model.
    touched = defaultdict(set)
    for model, instances in collector.data.items():
        touched[model._meta.label] |= _pks(instances)
    for qs in collector.fast_deletes:
        touched[qs.model._meta.label] |= _pks(qs)
    for (field, _value), objs_list in collector.field_updates.items():
        for objs in objs_list:
            touched[field.model._meta.label] |= _pks(objs)
    return {label: len(pks) for label, pks in touched.items() if pks and label not in DISPOSABLE_MODELS}


def describe_history(history):
    """'2 claims, 1 policy' style summary for messages."""
    parts = []
    for label, n in sorted(history.items(), key=lambda item: -item[1]):
        meta = apps.get_model(label)._meta
        noun = meta.verbose_name if n == 1 else meta.verbose_name_plural
        parts.append(f'{n} {noun}')
    return ', '.join(parts) if parts else 'existing records'


def deactivate_account(user):
    """Block sign-in while keeping the account and its history."""
    user.is_active = False
    user.save(update_fields=['is_active'])
    try:
        from rest_framework_simplejwt.token_blacklist.models import BlacklistedToken, OutstandingToken
    except Exception:  # blacklist app not installed
        return
    for token in OutstandingToken.objects.filter(user=user):
        BlacklistedToken.objects.get_or_create(token=token)
