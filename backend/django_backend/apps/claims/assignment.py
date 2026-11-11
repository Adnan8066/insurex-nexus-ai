import json
import logging
import os
from pathlib import Path

from django.contrib.auth import get_user_model
from django.db import transaction
from django.db.models import Count
from django.utils import timezone

from apps.assessments.models import EmployeeSkill, RoutingAgentProfile
from .models import Claim, ClaimAssignmentConfig, ClaimAssignmentEvent, ClaimStatus

logger = logging.getLogger(__name__)
User = get_user_model()
OPEN_STATUSES = [ClaimStatus.SUBMITTED, ClaimStatus.UNDER_REVIEW, ClaimStatus.AI_ASSESSMENT, ClaimStatus.INVESTIGATION]
CATEGORY_ALIASES = {
    'collision': {'collision', 'accident', 'vehicle collision'}, 'comprehensive': {'comprehensive', 'other damage', 'property damage'},
    'theft': {'theft', 'vehicle theft'}, 'vandalism': {'vandalism'}, 'fire': {'fire'},
    'water_damage': {'water damage', 'flood'}, 'hail': {'hail', 'weather damage'}, 'animal': {'animal', 'animal strike'},
    'glass': {'glass', 'windshield'}, 'other': {'general', 'other'},
}


def _ppo_gate():
    configured = os.environ.get('CLAIM_ROUTING_MODEL_PATH')
    model = Path(configured or Path(__file__).resolve().parents[3] / 'rl' / 'models' / 'claim_routing_ppo.zip').expanduser().resolve()
    try:
        report = json.loads(model.with_suffix('.evaluation.json').read_text(encoding='utf-8'))
        gate = report.get('evaluation_gate', {})
        metadata = report.get('routing_features', {})
        report_path = model.with_suffix('.evaluation.json')
        version = str(report.get('model_version') or model.stem)
        passed = (model.is_file() and report_path.stat().st_mtime >= model.stat().st_mtime
                  and version == model.stem and bool(gate.get('passed'))
                  and metadata.get('profile_version') == 2 and metadata.get('experience_feature') is True)
        return passed, version
    except (OSError, ValueError, AttributeError, TypeError):
        return False, ''


def _shift_is_open(profile, now):
    local = timezone.localtime(now)
    day = local.strftime('%a').lower()
    if profile.working_days and day not in profile.working_days:
        return False
    start, end = profile.shift_start_time, profile.shift_end_time
    return not start or not end or start <= local.time() <= end


def _matching_expertise(claim, profile, skills):
    labels = CATEGORY_ALIASES.get(claim.incident_type, {claim.incident_type.replace('_', ' ')})
    labels |= {claim.incident_type.replace('_', ' ')}
    rank = {'beginner': 1, 'intermediate': 2, 'advanced': 3, 'expert': 4}
    normalized_labels = {label.casefold() for label in labels}
    matches = []
    for value in [profile.primary_specialization, profile.secondary_specialization]:
        if value and (value.strip().casefold() in normalized_labels or any(label in value.strip().casefold() for label in normalized_labels)):
            matches.append((value, 4, 'specialization'))
    for skill in skills:
        if (skill.name.strip().casefold() in normalized_labels or any(label in skill.name.strip().casefold() for label in normalized_labels)) and rank.get(skill.level, 0) >= 2:
            matches.append((skill.name, rank.get(skill.level, 0), 'skill'))
    return max(matches, key=lambda item: item[1], default=None)


def _candidate_snapshot(claim, now, lock=False):
    employees = User.objects.filter(role='employee', is_active=True).order_by('pk')
    if lock:
        employees = employees.select_for_update()
    candidates = []
    for employee in employees:
        profile = RoutingAgentProfile.objects.select_for_update().filter(user_id=employee.pk).first() if lock else RoutingAgentProfile.objects.filter(user_id=employee.pk).first()
        if not profile or profile.is_demo:
            continue
        load = Claim.objects.filter(assigned_adjuster_id=employee.pk, status__in=OPEN_STATUSES).count()
        expertise = _matching_expertise(claim, profile, list(EmployeeSkill.objects.filter(profile=profile)))
        reasons = []
        if not profile.is_available or profile.availability_status != RoutingAgentProfile.Availability.AVAILABLE:
            reasons.append('employee unavailable')
        if profile.leave_status or profile.availability_status == RoutingAgentProfile.Availability.ON_LEAVE:
            reasons.append('employee on leave')
        if not _shift_is_open(profile, now):
            reasons.append('outside working shift')
        if load >= profile.max_claim_capacity:
            reasons.append('at maximum claim capacity')
        if not expertise:
            reasons.append(f'no authorized expertise for {claim.incident_type}')
        completed = Claim.objects.filter(assigned_adjuster_id=employee.pk, status=ClaimStatus.CLOSED, closed_at__isnull=False)
        completed_count = completed.count()
        avg_days = None
        if completed_count:
            from django.db.models import Avg, F, ExpressionWrapper, DurationField
            avg = completed.annotate(duration=ExpressionWrapper(F('closed_at') - F('submitted_at'), output_field=DurationField())).aggregate(value=Avg('duration'))['value']
            avg_days = round(avg.total_seconds() / 86400, 2) if avg else None
        performance = completed_count / max(Claim.objects.filter(assigned_adjuster_id=employee.pk).count(), 1)
        candidates.append({
            'user': employee, 'profile': profile, 'load': load, 'expertise': expertise,
            'eligible': not reasons, 'ineligibility_reasons': reasons, 'avg_processing_days': avg_days,
            'completion_performance': round(performance, 3),
            'capacity_utilization': load / max(profile.max_claim_capacity, 1),
        })
    return candidates


def _notify_admins(claim, reason):
    from apps.assessments.assignment import _notify_admins_unassigned
    _notify_admins_unassigned('Claim waiting for employee assignment', f'Claim {claim.claim_number}: {reason}', f'/claims/{claim.pk}', 'claim', claim.pk)


def _record(claim, event_type, employee=None, actor=None, strategy='expertise_least_workload', version='', reason='', snapshot=None):
    return ClaimAssignmentEvent.objects.create(claim=claim, event_type=event_type, employee=employee, actor=actor,
        strategy=strategy, model_version=version, reason=reason, eligibility_snapshot=snapshot or {})


@transaction.atomic
def auto_assign_claim(claim_id):
    claim = Claim.objects.select_for_update().get(pk=claim_id)
    if claim.assigned_adjuster_id:
        return claim
    config, _ = ClaimAssignmentConfig.objects.get_or_create(pk=1)
    if not config.enabled:
        claim.assignment_status = 'pending'
        claim.save(update_fields=['assignment_status'])
        return claim
    now = timezone.now()
    candidates = _candidate_snapshot(claim, now, lock=True)
    eligible = [item for item in candidates if item['eligible']]
    if not eligible:
        reason = 'No active employee is currently eligible for this claim.'
        snapshot = {'candidates': [{k: v for k, v in item.items() if k not in {'user', 'profile', 'expertise'}} | {'employee_id': item['user'].pk, 'ineligibility_reasons': item['ineligibility_reasons']} for item in candidates]}
        claim.assignment_status = 'pending'
        claim.assignment_updated_at = now
        claim.save(update_fields=['assignment_status', 'assignment_updated_at'])
        _record(claim, 'pending', reason=reason, snapshot=snapshot)
        try:
            _notify_admins(claim, reason)
        except Exception:
            logger.exception('Could not notify administrators about pending claim %s', claim.pk)
        return claim
    ppo_qualified, version = _ppo_gate()
    use_ppo = config.prefer_qualified_ppo and ppo_qualified
    strategy = 'expertise_least_workload'
    ppo_selected = None
    if use_ppo:
        try:
            import sys
            backend_root = str(Path(__file__).resolve().parents[3])
            if backend_root not in sys.path:
                sys.path.insert(0, backend_root)
            from rl.recommendation import ClaimRecommendationEngine
            engine = ClaimRecommendationEngine.load()
            severity = {'minor': .2, 'moderate': .45, 'major': .75, 'total_loss': 1.0}.get(claim.incident_severity, .5)
            difficulty = min(1.0, max(float(claim.complexity_score or 0), severity * .7))
            live = eligible[:10]
            recommendations = engine.get_routing_recommendations(
                {'complexity_score': float(claim.complexity_score or 0), 'severity_score': severity, 'processing_difficulty': difficulty},
                [{'id': str(item['user'].pk), 'queue_length': item['load'],
                  'workload': min(10.0, item['load'] / max(item['profile'].max_claim_capacity, 1) * 10),
                  'skill_tier': item['profile'].skill_tier,
                  'years_of_experience': item['profile'].years_of_experience,
                  'max_claim_capacity': item['profile'].max_claim_capacity,
                  'available': True, 'current_shift_status': 'on_shift'} for item in live],
            )
            preferred_id = recommendations.get('recommended_agent_id')
            ppo_selected = next((item for item in live if str(item['user'].pk) == str(preferred_id)), None)
            if ppo_selected:
                strategy = 'ppo'
                version = engine.model_version
        except Exception:
            logger.exception('Qualified PPO inference failed; using workload baseline for claim %s', claim.pk)
    selected = ppo_selected or min(eligible, key=lambda item: (
        -item['expertise'][1], item['capacity_utilization'], -item['profile'].years_of_experience,
        -(item['completion_performance']), item['avg_processing_days'] if item['avg_processing_days'] is not None else float('inf'), item['user'].pk,
    ))
    previous = claim.assigned_adjuster_id
    claim.assigned_adjuster = selected['user']
    claim.assignment_status = 'assigned'
    claim.assignment_updated_at = now
    claim.save(update_fields=['assigned_adjuster', 'assignment_status', 'assignment_updated_at', 'updated_at'])
    reason = f"Matched {selected['expertise'][0]} expertise; {selected['load']}/{selected['profile'].max_claim_capacity} active claims, {selected['profile'].years_of_experience} years experience."
    snapshot = {'employee_id': selected['user'].pk, 'active_workload': selected['load'], 'max_capacity': selected['profile'].max_claim_capacity,
        'capacity_utilization': selected['capacity_utilization'], 'specialization': selected['expertise'][0], 'expertise_source': selected['expertise'][2],
        'expertise_level': selected['expertise'][1], 'years_of_experience': selected['profile'].years_of_experience,
        'average_processing_days': selected['avg_processing_days'], 'completion_performance': selected['completion_performance'], 'eligible': True,
        'within_shift': True, 'strategy': strategy, 'ppo_qualified': ppo_qualified}
    _record(claim, 'assigned' if not previous else 'reassigned', selected['user'], strategy=strategy, version=version if use_ppo else '', reason=reason, snapshot=snapshot)
    from apps.assessments.assignment import notify_claim_assignee
    transaction.on_commit(lambda: notify_claim_assignee(claim, selected['user']))
    return claim


@transaction.atomic
def override_assignment(claim_id, employee_id, actor, reason):
    claim = Claim.objects.select_for_update().get(pk=claim_id)
    employee = User.objects.filter(pk=employee_id, role='employee', is_active=True).first()
    if employee is None:
        raise ValueError('Select an active employee account.')
    before = claim.assigned_adjuster_id
    candidates = _candidate_snapshot(claim, timezone.now())
    candidate = next((item for item in candidates if item['user'].pk == employee.pk), None)
    snapshot = {'employee_id': employee.pk, 'eligible': bool(candidate and candidate['eligible']), 'override': True,
                'ineligibility_reasons': candidate['ineligibility_reasons'] if candidate else ['no routing profile']}
    claim.assigned_adjuster = employee
    claim.assignment_status = 'assigned'
    claim.assignment_updated_at = timezone.now()
    claim.save(update_fields=['assigned_adjuster', 'assignment_status', 'assignment_updated_at', 'updated_at'])
    _record(claim, 'reassigned' if before else 'assigned', employee, actor, 'manual', reason=reason, snapshot=snapshot)
    from apps.claims.models import ClaimTimeline
    ClaimTimeline.objects.create(claim=claim, status=claim.status, title='Adjuster assignment overridden', description=reason, user=actor, metadata=snapshot)
    from apps.assessments.assignment import notify_claim_assignee
    transaction.on_commit(lambda: notify_claim_assignee(claim, employee))
    return claim


@transaction.atomic
def unassign_claim(claim_id, actor, reason):
    claim = Claim.objects.select_for_update().get(pk=claim_id)
    previous = claim.assigned_adjuster_id
    claim.assigned_adjuster = None
    claim.assignment_status = 'pending'
    claim.assignment_updated_at = timezone.now()
    claim.save(update_fields=['assigned_adjuster', 'assignment_status', 'assignment_updated_at', 'updated_at'])
    _record(claim, 'unassigned', actor=actor, strategy='manual', reason=reason, snapshot={'previous_employee_id': previous, 'override': True})
    from apps.claims.models import ClaimTimeline
    ClaimTimeline.objects.create(claim=claim, status=claim.status, title='Adjuster assignment removed', description=reason, user=actor)
    transaction.on_commit(retry_pending_assignments_safely)
    return claim


def retry_pending_assignments():
    config = ClaimAssignmentConfig.objects.filter(pk=1).first()
    if not config or not config.enabled:
        return {'attempted': 0, 'assigned': 0}
    ids = list(Claim.objects.filter(assigned_adjuster__isnull=True, assignment_status='pending', status__in=OPEN_STATUSES).order_by('submitted_at').values_list('pk', flat=True)[:250])
    assigned = 0
    for claim_id in ids:
        try:
            if auto_assign_claim(claim_id).assigned_adjuster_id:
                assigned += 1
        except Exception:
            logger.exception('Pending assignment retry failed for claim %s', claim_id)
    return {'attempted': len(ids), 'assigned': assigned}


def retry_pending_assignments_safely():
    try:
        return retry_pending_assignments()
    except Exception:
        logger.exception('Retrying pending claim assignments failed')
        return {'attempted': 0, 'assigned': 0}
