"""Read-only REST endpoint for synthetic RL routing advice."""

from functools import lru_cache
from importlib.util import find_spec
import json
import os
from pathlib import Path
import sys
from uuid import uuid4

from django.db import IntegrityError
from django.core import signing
from drf_spectacular.utils import extend_schema
from rest_framework import serializers, status
from rest_framework.decorators import api_view, permission_classes
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response

from common.permissions import IsStaffMember
from .models import RoutingAgentProfile, RoutingRecommendationReview


def _model_artifact_path():
    configured_path = os.environ.get('CLAIM_ROUTING_MODEL_PATH')
    return Path(
        configured_path or Path(__file__).resolve().parents[3] / 'rl' / 'models' / 'claim_routing_ppo.zip'
    ).expanduser().resolve()


def _evaluation_gate_passed(model_path):
    report_path = model_path.with_suffix('.evaluation.json')
    if not report_path.is_file():
        return False
    try:
        evaluation = json.loads(report_path.read_text(encoding='utf-8'))
        return bool(evaluation.get('evaluation_gate', {}).get('passed'))
    except (OSError, json.JSONDecodeError, AttributeError):
        return False


def auto_assign_new_claim(claim):
    """Assign a new claim only when routing is enabled and the PPO is qualified.

    This is deliberately fail-closed: missing staff profiles, model artifacts,
    dependencies, or a passing evaluation leave the claim unassigned.
    """
    if os.environ.get('CLAIM_ROUTING_AUTO_ASSIGN_ENABLED', 'false').lower() != 'true':
        return False

    model_path = _model_artifact_path()
    if not _evaluation_gate_passed(model_path):
        return False

    from apps.accounts.models import Role
    from apps.claims.models import Claim, ClaimTimeline

    profiles = list(RoutingAgentProfile.objects.select_related('user').filter(
        user__role=Role.EMPLOYEE,
        user__is_active=True,
        is_available=True,
        is_demo=False,
    ))
    agent_status = [_agent_status(profile) for profile in profiles]
    # The model accepts 3-5 candidates. Avoid inventing/fabricating roster data.
    if not 3 <= len(agent_status) <= 5:
        return False

    values = {
        'incident_severity': claim.incident_severity,
        'number_of_vehicles': claim.number_of_vehicles,
        'injuries': claim.injuries,
        'property_damage': claim.property_damage,
        'witnesses': claim.witnesses,
        'police_report': claim.police_report,
        'complexity_score': claim.complexity_score,
    }
    result = _load_recommendation_engine().get_routing_recommendations(
        _claim_routing_features(values), agent_status,
    )
    if result.get('status') != 'recommendation_available':
        return False

    selected = next((
        profile for profile in profiles
        if str(profile.user_id) == str(result.get('recommended_agent_id'))
    ), None)
    option = next((
        item for item in result.get('ranked_options', [])
        if str(item.get('agent_id')) == str(result.get('recommended_agent_id'))
    ), None)
    if selected is None or not option or not option.get('skill_match'):
        return False

    from django.db import transaction
    with transaction.atomic():
        # Conditional update prevents a concurrent/manual assignment being overwritten.
        updated = Claim.objects.filter(
            pk=claim.pk, assigned_adjuster__isnull=True,
            status__in=['submitted', 'under_review', 'ai_assessment'],
        ).update(assigned_adjuster=selected.user)
        if not updated:
            return False
        ClaimTimeline.objects.create(
            claim=claim,
            status=claim.status,
            title='Automatically Assigned to Adjuster',
            description=(
                f'Claim was routed to {selected.user.get_full_name() or selected.user.email} '
                f'by the qualified RL model ({result.get("model_version", "unknown")}).'
            ),
            is_system=True,
        )
    claim.assigned_adjuster = selected.user
    return True


class ActiveAgentStatusSerializer(serializers.Serializer):
    id = serializers.JSONField()
    queue_length = serializers.FloatField(min_value=0)
    workload = serializers.FloatField(min_value=0)
    skill_tier = serializers.IntegerField(min_value=1, max_value=5)
    available = serializers.BooleanField(required=False, default=True)


class RoutingRecommendationRequestSerializer(serializers.Serializer):
    claim_data = serializers.DictField(child=serializers.FloatField(min_value=0, max_value=1))
    claim_id = serializers.IntegerField(required=False, allow_null=True, min_value=1)
    active_agents_status = ActiveAgentStatusSerializer(many=True, min_length=3, max_length=5)

    def validate(self, attrs):
        claim_id = attrs.get('claim_id')
        if claim_id is None:
            return attrs
        from apps.claims.models import Claim

        claim = Claim.objects.filter(
            pk=claim_id,
            assigned_adjuster__isnull=True,
            status__in=['submitted', 'under_review', 'ai_assessment'],
        ).first()
        if claim is None:
            raise serializers.ValidationError({'claim_id': 'Choose an unassigned open claim from the routing claim list.'})
        values = {
            'incident_severity': claim.incident_severity,
            'number_of_vehicles': claim.number_of_vehicles,
            'injuries': claim.injuries,
            'property_damage': claim.property_damage,
            'witnesses': claim.witnesses,
            'police_report': claim.police_report,
        }
        if _claim_routing_features(values) != attrs['claim_data']:
            raise serializers.ValidationError({'claim_data': 'Claim features do not match the selected claim.'})
        return attrs


class RoutingRecommendationResponseSerializer(serializers.Serializer):
    advisory_only = serializers.BooleanField()
    automated_assignment = serializers.BooleanField()
    requires_human_review = serializers.BooleanField()
    status = serializers.CharField()
    recommended_agent_id = serializers.JSONField(allow_null=True)
    predicted_wait_time = serializers.FloatField(allow_null=True)
    workload_impact_summary = serializers.CharField()
    ranked_alternatives = serializers.ListField(child=serializers.DictField())
    ranked_options = serializers.ListField(child=serializers.DictField())
    recommendation_id = serializers.UUIDField()
    review_token = serializers.CharField()
    claim_id = serializers.IntegerField(allow_null=True)


class RoutingReviewRequestSerializer(serializers.Serializer):
    recommendation_id = serializers.UUIDField()
    claim_id = serializers.IntegerField(required=False, allow_null=True, min_value=1)
    decision = serializers.ChoiceField(choices=RoutingRecommendationReview.Decision.choices)
    notes = serializers.CharField(required=False, allow_blank=True, max_length=2000)
    claim_data = serializers.DictField(child=serializers.FloatField(min_value=0, max_value=1))
    active_agents_status = ActiveAgentStatusSerializer(many=True, min_length=3, max_length=5)
    recommendation = serializers.DictField()
    review_token = serializers.CharField()

    def validate_recommendation(self, value):
        if (
            value.get('advisory_only') is not True
            or value.get('automated_assignment') is not False
            or value.get('requires_human_review') is not True
        ):
            raise serializers.ValidationError('Only advisory, non-automated recommendations can be reviewed here.')
        return value

    def validate_recommendation_id(self, value):
        if RoutingRecommendationReview.objects.filter(recommendation_id=value).exists():
            raise serializers.ValidationError('This recommendation has already been reviewed.')
        return value

    def validate(self, attrs):
        try:
            signed = signing.loads(
                attrs['review_token'], salt='claim-routing-review', max_age=24 * 60 * 60
            )
        except signing.SignatureExpired as exc:
            raise serializers.ValidationError({'review_token': 'This review link expired; request a fresh recommendation.'}) from exc
        except signing.BadSignature as exc:
            raise serializers.ValidationError({'review_token': 'The review token is invalid.'}) from exc

        recommendation = dict(attrs['recommendation'])
        recommendation.pop('review_token', None)
        actual = {
            'recommendation_id': str(attrs['recommendation_id']),
            'claim_id': attrs.get('claim_id'),
            'claim_data': attrs['claim_data'],
            'active_agents_status': attrs['active_agents_status'],
            'recommendation': recommendation,
        }
        if signed != actual:
            raise serializers.ValidationError('Review feedback must match the recommendation returned by this service.')
        claim_id = attrs.get('claim_id')
        if claim_id is not None:
            from apps.claims.models import Claim
            if not Claim.objects.filter(pk=claim_id).exists():
                raise serializers.ValidationError({'claim_id': 'The claim no longer exists, so this feedback cannot be linked.'})
        return attrs


class RoutingClaimSerializer(serializers.Serializer):
    id = serializers.IntegerField()
    claim_number = serializers.CharField()
    claim_data = serializers.DictField(child=serializers.FloatField(min_value=0, max_value=1))


class RoutingAgentRosterSerializer(serializers.Serializer):
    id = serializers.IntegerField()
    name = serializers.CharField()
    role = serializers.CharField()
    queue_length = serializers.IntegerField()
    workload = serializers.FloatField()
    skill_tier = serializers.IntegerField()
    available = serializers.BooleanField()
    is_demo = serializers.BooleanField()


@extend_schema(
    responses={200: dict},
    tags=['AI & Routing Advisory'],
    description='Reports whether RL inference dependencies and the configured model artifact are available.',
)
@api_view(['GET'])
@permission_classes([IsAuthenticated, IsStaffMember])
def routing_model_status(request):
    configured_path = os.environ.get('CLAIM_ROUTING_MODEL_PATH')
    model_path = _model_artifact_path()
    dependencies = {
        'gymnasium': find_spec('gymnasium') is not None,
        'stable_baselines3': find_spec('stable_baselines3') is not None,
        'torch': find_spec('torch') is not None,
    }
    artifact_present = model_path.is_file()
    report_path = model_path.with_suffix('.evaluation.json')
    evaluation_report_present = report_path.is_file()
    evaluation_gate_passed = _evaluation_gate_passed(model_path)
    dataset_pretraining = None
    if evaluation_report_present:
        try:
            report = json.loads(report_path.read_text(encoding='utf-8'))
            dataset_pretraining = report.get('dataset_pretraining')
        except (OSError, json.JSONDecodeError, AttributeError):
            dataset_pretraining = None
    return Response({
        'ready': artifact_present and all(dependencies.values()),
        'qualified_for_advisory_pilot': artifact_present and evaluation_gate_passed,
        'evaluation_report_present': evaluation_report_present,
        'evaluation_gate_passed': evaluation_gate_passed,
        'evaluation_gate_enforced': os.environ.get('CLAIM_ROUTING_ENFORCE_EVALUATION_GATE', 'false').lower() == 'true',
        'artifact_present': artifact_present,
        'artifact_name': model_path.name,
        'artifact_size_bytes': model_path.stat().st_size if artifact_present else None,
        'artifact_path_configured': bool(configured_path),
        'dataset_pretraining': dataset_pretraining,
        'dependencies': dependencies,
        'advisory_only': True,
        'automated_assignment': False,
        'detail': None if artifact_present else 'Supply the trained PPO archive and set CLAIM_ROUTING_MODEL_PATH.',
    })

def _claim_routing_features(claim):
    """Create documented normalized simulator features from existing claim fields."""
    severity = {
        'minor': 0.15,
        'moderate': 0.4,
        'major': 0.7,
        'total_loss': 1.0,
    }.get(claim['incident_severity'], 0.5)
    complexity = float(claim.get('complexity_score') or min(
        1.0,
        0.2
        + min(max(int(claim['number_of_vehicles']) - 1, 0), 3) * 0.12
        + bool(claim['injuries']) * 0.2
        + bool(claim['property_damage']) * 0.12
        + bool(claim['witnesses']) * 0.08
        + bool(claim['police_report']) * 0.08,
    ))
    difficulty = min(
        1.0,
        severity * 0.65
        + bool(claim['injuries']) * 0.15
        + bool(claim['property_damage']) * 0.08
        + bool(claim['witnesses']) * 0.06
        + bool(claim['police_report']) * 0.06,
    )
    return {
        'complexity_score': round(float(complexity), 3),
        'severity_score': severity,
        'processing_difficulty': round(float(difficulty), 3),
    }


def _agent_status(profile):
    """Derive queue and workload estimates from active assigned claims."""
    from apps.claims.models import Claim

    user = profile.user
    claims = Claim.objects.filter(
        status__in=['submitted', 'under_review', 'ai_assessment', 'investigation']
    )
    if user.role == 'investigator':
        claims = claims.filter(assigned_investigator_id=user.id, status='investigation')
    else:
        claims = claims.filter(assigned_adjuster_id=user.id)
    rows = list(claims.values(
        'incident_severity', 'number_of_vehicles', 'injuries', 'property_damage', 'witnesses', 'police_report', 'complexity_score'
    ))
    try:
        backend_root = str(Path(__file__).resolve().parents[3])
        if backend_root not in sys.path:
            sys.path.insert(0, backend_root)
        from rl.environment import estimate_claim_workload
        workload = sum(
            estimate_claim_workload(
                _claim_routing_features(row)['complexity_score'],
                _claim_routing_features(row)['processing_difficulty'],
            )
            for row in rows
        )
    except ImportError:
        # Match the simulator's documented workload formula while keeping this
        # read-only roster endpoint available when optional RL packages are absent.
        workload = sum(
            1 + 4 * _claim_routing_features(row)['complexity_score']
            + 5 * _claim_routing_features(row)['processing_difficulty']
            for row in rows
        )
    return {
        'id': user.id,
        'name': user.get_full_name() or user.email,
        'role': user.role,
        'queue_length': len(rows),
        'workload': round(float(workload), 2),
        'skill_tier': profile.skill_tier,
        'available': profile.is_available,
        'is_demo': profile.is_demo,
    }


@lru_cache(maxsize=1)
def _load_recommendation_engine():
    # Keep Torch/SB3 imports out of Django startup; load the policy only when
    # an authorized user requests an advisory recommendation.
    backend_root = str(Path(__file__).resolve().parents[3])
    if backend_root not in sys.path:
        sys.path.insert(0, backend_root)
    from rl.recommendation import ClaimRecommendationEngine

    return ClaimRecommendationEngine.load()


@extend_schema(
    request=RoutingRecommendationRequestSerializer,
    responses={200: RoutingRecommendationResponseSerializer},
    tags=["AI & Routing Advisory"],
    description=(
        "Returns synthetic-policy ranking advice for human review. This endpoint "
        "does not create or update claims, assignments, or database records."
    ),
)
@api_view(["POST"])
@permission_classes([IsAuthenticated, IsStaffMember])
def routing_recommendation(request):
    """Score caller-supplied claim/agent data without persisting any changes."""
    request_serializer = RoutingRecommendationRequestSerializer(data=request.data)
    request_serializer.is_valid(raise_exception=True)
    payload = request_serializer.validated_data
    gate_enforced = os.environ.get('CLAIM_ROUTING_ENFORCE_EVALUATION_GATE', 'false').lower() == 'true'
    if gate_enforced and not _evaluation_gate_passed(_model_artifact_path()):
        return Response(
            {'detail': 'The PPO candidate has not passed the held-out evaluation gate against the least-workload heuristic. Production recommendations are disabled until a qualified artifact and evaluation report are deployed.'},
            status=status.HTTP_503_SERVICE_UNAVAILABLE,
        )
    try:
        engine = _load_recommendation_engine()
        result = engine.get_routing_recommendations(
            claim_data=payload["claim_data"],
            active_agents_status=payload["active_agents_status"],
        )
        result['recommendation_id'] = str(uuid4())
        result['claim_id'] = payload.get('claim_id')
        result['review_token'] = signing.dumps(
            {
                'recommendation_id': result['recommendation_id'],
                'claim_id': payload.get('claim_id'),
                'claim_data': payload['claim_data'],
                'active_agents_status': payload['active_agents_status'],
                'recommendation': result,
            },
            salt='claim-routing-review',
        )
    except ImportError as exc:
        return Response(
            {"detail": "RL inference dependencies are not installed."},
            status=status.HTTP_503_SERVICE_UNAVAILABLE,
        )
    except FileNotFoundError as exc:
        return Response(
            {"detail": str(exc)}, status=status.HTTP_503_SERVICE_UNAVAILABLE
        )
    except RuntimeError as exc:
        return Response({"detail": str(exc)}, status=status.HTTP_503_SERVICE_UNAVAILABLE)
    except ValueError as exc:
        return Response({"detail": str(exc)}, status=status.HTTP_400_BAD_REQUEST)
    return Response(result, status=status.HTTP_200_OK)


@extend_schema(
    responses={200: RoutingAgentRosterSerializer(many=True)},
    tags=['AI & Routing Advisory'],
    description=(
        'Returns staff routing profiles with queue counts and workload estimates '
        'derived from active assigned claims. Wait and workload are simulator estimates.'
    ),
)
@api_view(['GET'])
@permission_classes([IsAuthenticated, IsStaffMember])
def routing_agents(request):
    profiles = RoutingAgentProfile.objects.select_related('user').filter(
        user__role__in=['employee', 'investigator'], user__is_active=True
    )
    agents = [_agent_status(profile) for profile in profiles]
    return Response({
        'agents': agents,
        'queue_basis': 'Count of open claims assigned to this staff member.',
        'workload_basis': 'Estimated from active assigned claim features using synthetic simulator weights; not a measured time value.',
        'wait_basis': 'Synthetic estimate based on queue/workload; not measured operational wait time.',
    })


@extend_schema(
    responses={200: RoutingClaimSerializer(many=True)},
    tags=['AI & Routing Advisory'],
    description=(
        'Lists unassigned open claims with normalized simulator features derived '
        'from claim metadata. Values are advisory feature estimates.'
    ),
)
@api_view(['GET'])
@permission_classes([IsAuthenticated, IsStaffMember])
def routing_claims(request):
    from apps.claims.models import Claim

    claims = Claim.objects.filter(
        assigned_adjuster__isnull=True,
        status__in=['submitted', 'under_review', 'ai_assessment'],
    ).order_by('submitted_at')[:100]
    result = []
    for claim in claims:
        values = {
            'incident_severity': claim.incident_severity,
            'number_of_vehicles': claim.number_of_vehicles,
            'injuries': claim.injuries,
            'property_damage': claim.property_damage,
            'witnesses': claim.witnesses,
            'police_report': claim.police_report,
            'complexity_score': claim.complexity_score,
        }
        result.append({
            'id': claim.id,
            'claim_number': claim.claim_number,
            'claim_data': _claim_routing_features(values),
        })
    return Response(result)


@extend_schema(
    request=RoutingReviewRequestSerializer,
    responses={201: dict},
    tags=['AI & Routing Advisory'],
    description=(
        'Records explicit staff feedback on an advisory result. This does not '
        'assign, update, or otherwise mutate any claim.'
    ),
)
@api_view(['POST'])
@permission_classes([IsAuthenticated, IsStaffMember])
def review_routing_recommendation(request):
    serializer = RoutingReviewRequestSerializer(data=request.data)
    serializer.is_valid(raise_exception=True)
    data = serializer.validated_data
    recommendation_snapshot = dict(data['recommendation'])
    recommendation_snapshot.pop('review_token', None)
    try:
        review = RoutingRecommendationReview.objects.create(
            recommendation_id=data['recommendation_id'],
            claim_id=data.get('claim_id'),
            reviewer=request.user,
            decision=data['decision'],
            notes=data.get('notes', ''),
            claim_data=data['claim_data'],
            agent_status=data['active_agents_status'],
            recommendation=recommendation_snapshot,
        )
    except IntegrityError:
        return Response(
            {'detail': 'This recommendation has already been reviewed.'},
            status=status.HTTP_409_CONFLICT,
        )
    return Response({
        'recommendation_id': str(review.recommendation_id),
        'decision': review.decision,
        'reviewed_at': review.created_at,
        'assignment_changed': False,
    }, status=status.HTTP_201_CREATED)
