from rest_framework.decorators import api_view, permission_classes
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response
from rest_framework import status
from django.shortcuts import get_object_or_404
from django.utils import timezone
from drf_spectacular.types import OpenApiTypes
from drf_spectacular.utils import extend_schema

from apps.claims.models import Claim
from .models import ClaimAssessment, AgentOutput, DecisionFlow, AssessmentType, AssessmentStatus
from .serializers import ClaimAssessmentSerializer, DecisionFlowSerializer
from ml_service import (
    detect_fraud_ml,
    predict_repair_cost_ml,
    predict_total_loss_ml,
    MLModelUnavailable,
)
from common.permissions import IsStaffMember


@extend_schema(request=OpenApiTypes.OBJECT, responses=ClaimAssessmentSerializer)
@api_view(['POST'])
@permission_classes([IsAuthenticated, IsStaffMember])
def assess_claim(request):
    claim_id = request.data.get('claim_id')
    if not claim_id:
        return Response({'error': 'claim_id is required'}, status=status.HTTP_400_BAD_REQUEST)
    
    claim = get_object_or_404(Claim, id=claim_id)
    
    assessment, created = ClaimAssessment.objects.get_or_create(
        claim=claim,
        defaults={'assessment_type': AssessmentType.COMPREHENSIVE}
    )
    
    assessment.status = AssessmentStatus.IN_PROGRESS
    assessment.save()
    
    try:
        predicted_cost = predict_repair_cost_internal(claim)
        fraud_score = detect_fraud_internal(claim)
        total_loss_prob = predict_total_loss_internal(claim)
        
        assessment.predicted_repair_cost = predicted_cost['cost']
        assessment.cost_breakdown = predicted_cost['breakdown']
        assessment.repair_time_estimate_days = predicted_cost['time_estimate']
        assessment.comparable_claims_count = predicted_cost['comparable_count']
        
        assessment.fraud_risk_score = fraud_score['score']
        assessment.risk_level = fraud_score['level']
        assessment.risk_factors = fraud_score['factors']
        assessment.behavioral_indicators = fraud_score['behavioral']
        assessment.network_analysis = fraud_score['network']
        
        assessment.total_loss_probability = total_loss_prob['probability']
        
        if fraud_score['score'] > 70:
            assessment.claim_priority = 'critical'
        elif fraud_score['score'] > 40 or total_loss_prob['probability'] > 50:
            assessment.claim_priority = 'high'
        elif fraud_score['score'] > 20 or total_loss_prob['probability'] > 25:
            assessment.claim_priority = 'medium'
        else:
            assessment.claim_priority = 'low'
        
        assessment.ai_recommendation = generate_recommendation(assessment)
        assessment.confidence = calculate_confidence(assessment)
        assessment.assessed_at = timezone.now()
        assessment.status = AssessmentStatus.COMPLETED
        assessment.save()
        
        serializer = ClaimAssessmentSerializer(assessment)
        return Response(serializer.data)
        
    except Exception as e:
        assessment.status = AssessmentStatus.FAILED
        assessment.save()
        if isinstance(e, MLModelUnavailable):
            return Response({'error': str(e)}, status=status.HTTP_503_SERVICE_UNAVAILABLE)
        return Response({'error': str(e)}, status=status.HTTP_500_INTERNAL_SERVER_ERROR)


def predict_repair_cost_internal(claim):
    return predict_repair_cost_ml(claim_model_input(claim))


def detect_fraud_internal(claim):
    return detect_fraud_ml(claim_model_input(claim))


def predict_total_loss_internal(claim):
    return predict_total_loss_ml(claim_model_input(claim))


def claim_model_input(claim):
    """Return dataset-shaped input for model inference on a claim record."""
    assessment_data = claim.ai_assessment or {}
    source_data = assessment_data.get('source_data')
    if source_data:
        result = dict(source_data)
        result['_source_dataset'] = assessment_data.get('source_dataset')
        return result

    incident_types = {
        'collision': 'Single Vehicle Collision' if claim.number_of_vehicles == 1 else 'Multi-vehicle Collision',
        'theft': 'Vehicle Theft',
        'comprehensive': 'Parked Car',
    }
    severities = {
        'minor': 'Minor Damage',
        'moderate': 'Minor Damage',
        'major': 'Major Damage',
        'total_loss': 'Total Loss',
    }
    vehicle = claim.vehicle
    policy = claim.policy
    customer_age = None
    try:
        birth_date = claim.customer.customer_profile.date_of_birth
        if birth_date:
            customer_age = max(0, claim.incident_date.year - birth_date.year)
    except AttributeError:
        pass

    return {
        '_source_dataset': 'insurance_claims',
        'age': customer_age,
        'policy_deductable': float(policy.deductible or 0),
        'policy_annual_premium': float(policy.premium or 0),
        'incident_type': incident_types.get(claim.incident_type, 'Other'),
        'incident_severity': severities.get(claim.incident_severity, 'Minor Damage'),
        'number_of_vehicles_involved': claim.number_of_vehicles,
        'property_damage': 'YES' if claim.property_damage else 'NO',
        'bodily_injuries': int(bool(claim.injuries)),
        'witnesses': int(bool(claim.witnesses)),
        'police_report_available': 'YES' if claim.police_report else 'NO',
        'auto_make': vehicle.make,
        'auto_model': vehicle.model,
        'auto_year': vehicle.year,
        'claim_amount': float(claim.claim_amount or 0),
    }


def generate_recommendation(assessment):
    if assessment.fraud_risk_score and assessment.fraud_risk_score > 70:
        return "High fraud risk detected. Recommend SIU investigation before settlement."
    elif assessment.total_loss_probability and assessment.total_loss_probability > 50:
        return "High probability of total loss. Consider total loss settlement path."
    else:
        return "Standard processing recommended. Proceed with repair assessment."


def calculate_confidence(assessment):
    # The current models do not produce a validated, calibrated claim-level confidence value.
    return None


@extend_schema(request=OpenApiTypes.OBJECT, responses=OpenApiTypes.OBJECT)
@api_view(['POST'])
@permission_classes([IsAuthenticated, IsStaffMember])
def predict_repair_cost(request):
    claim_id = request.data.get('claim_id')
    if not claim_id:
        return Response({'error': 'claim_id is required'}, status=status.HTTP_400_BAD_REQUEST)
    
    claim = get_object_or_404(Claim, id=claim_id)
    try:
        result = predict_repair_cost_internal(claim)
    except MLModelUnavailable as exc:
        return Response({'error': str(exc)}, status=status.HTTP_503_SERVICE_UNAVAILABLE)
    return Response(result)


@extend_schema(request=OpenApiTypes.OBJECT, responses=OpenApiTypes.OBJECT)
@api_view(['POST'])
@permission_classes([IsAuthenticated, IsStaffMember])
def detect_fraud(request):
    claim_id = request.data.get('claim_id')
    if not claim_id:
        return Response({'error': 'claim_id is required'}, status=status.HTTP_400_BAD_REQUEST)
    
    claim = get_object_or_404(Claim, id=claim_id)
    try:
        result = detect_fraud_internal(claim)
    except MLModelUnavailable as exc:
        return Response({'error': str(exc)}, status=status.HTTP_503_SERVICE_UNAVAILABLE)
    return Response(result)


@extend_schema(request=OpenApiTypes.OBJECT, responses=OpenApiTypes.OBJECT)
@api_view(['POST'])
@permission_classes([IsAuthenticated, IsStaffMember])
def predict_total_loss(request):
    claim_id = request.data.get('claim_id')
    if not claim_id:
        return Response({'error': 'claim_id is required'}, status=status.HTTP_400_BAD_REQUEST)
    
    claim = get_object_or_404(Claim, id=claim_id)
    try:
        result = predict_total_loss_internal(claim)
    except MLModelUnavailable as exc:
        return Response({'error': str(exc)}, status=status.HTTP_503_SERVICE_UNAVAILABLE)
    return Response(result)


@extend_schema(request=OpenApiTypes.OBJECT, responses=OpenApiTypes.OBJECT)
@api_view(['POST'])
@permission_classes([IsAuthenticated, IsStaffMember])
def run_agent(request, agent_type):
    claim_id = request.data.get('claim_id')
    input_data = request.data.get('input_data', {})
    supported_agents = {
        'claim_agent', 'policy_agent', 'fraud_agent',
        'damage_agent', 'settlement_agent', 'decision_agent',
    }
    
    if not claim_id:
        return Response({'error': 'claim_id is required'}, status=status.HTTP_400_BAD_REQUEST)

    if agent_type not in supported_agents:
        return Response({'error': 'Unknown agent type'}, status=status.HTTP_404_NOT_FOUND)
    
    claim = get_object_or_404(Claim, id=claim_id)

    agent_output, created = AgentOutput.objects.get_or_create(
        claim=claim,
        agent_type=agent_type,
        defaults={'input_data': input_data}
    )
    
    agent_output.status = 'running'
    agent_output.input_data = input_data
    agent_output.save()
    
    try:
        output_data = {}
        if agent_type == 'claim_agent':
            output_data = {
                'status': claim.status,
                'claim_number': claim.claim_number,
                'policy_number': claim.policy.policy_number,
                'summary': 'Claim record and required policy and vehicle links loaded.',
            }
        elif agent_type == 'policy_agent':
            policy = claim.policy
            covered = (
                policy.customer_id == claim.customer_id
                and policy.status == 'active'
                and policy.start_date <= claim.incident_date <= policy.end_date
            )
            vehicle_matches = policy.vehicle_id in (None, claim.vehicle_id)
            output_data = {
                'coverage_valid': covered and vehicle_matches,
                'policy_status': policy.status,
                'incident_within_term': policy.start_date <= claim.incident_date <= policy.end_date,
                'vehicle_matches_policy': vehicle_matches,
                'deductible': float(policy.deductible),
                'review_required': not covered or not vehicle_matches,
            }
        elif agent_type == 'fraud_agent':
            output_data = detect_fraud_internal(claim)
        elif agent_type == 'damage_agent':
            output_data = predict_repair_cost_internal(claim)
        elif agent_type == 'settlement_agent':
            cost = predict_repair_cost_internal(claim)
            deductible = float(claim.policy.deductible or 0)
            estimate = float(cost.get('cost') or claim.claim_amount or 0)
            output_data = {
                'estimated_repair_cost': estimate,
                'deductible': deductible,
                'recommended_amount': max(0, estimate - deductible),
                'requires_adjuster_approval': True,
            }
        elif agent_type == 'decision_agent':
            fraud = detect_fraud_internal(claim)
            cost = predict_repair_cost_internal(claim)
            deductible = float(claim.policy.deductible or 0)
            estimated_cost = float(cost.get('cost') or claim.claim_amount or 0)
            output_data = {
                'decision': 'manual_review',
                'reason': 'AI outputs are review aids; an adjuster must make the coverage and settlement decision.',
                'fraud_risk_score': fraud.get('score'),
                'recommended_amount': max(0, estimated_cost - deductible),
                'automated_approval': False,
            }
        
        agent_output.output_data = output_data
        agent_output.status = 'completed'
        agent_output.confidence = None
        agent_output.processing_time_seconds = None
        agent_output.completed_at = timezone.now()
        agent_output.save()

        decision_flow, _ = DecisionFlow.objects.get_or_create(
            claim=claim,
            defaults={'rl_recommendation': {'available': False, 'reason': 'No reinforcement-learning optimizer is configured.'}},
        )
        decision_flow.agents = list(claim.agent_outputs.order_by('created_at').values(
            'agent_type', 'status', 'input_data', 'output_data', 'confidence',
            'processing_time_seconds', 'error_message', 'created_at', 'completed_at',
        ))
        if agent_type == 'decision_agent':
            decision_flow.final_decision = output_data
            decision_flow.decided_by = 'Rules-based review recommendation'
            decision_flow.decided_at = timezone.now()
        decision_flow.save()
        
        return Response({'status': 'completed', 'agent_type': agent_type, 'output': output_data})
        
    except Exception as e:
        agent_output.status = 'failed'
        agent_output.error_message = str(e)
        agent_output.save()
        if isinstance(e, MLModelUnavailable):
            return Response({'error': str(e)}, status=status.HTTP_503_SERVICE_UNAVAILABLE)
        return Response({'error': str(e)}, status=status.HTTP_500_INTERNAL_SERVER_ERROR)


@extend_schema(responses=DecisionFlowSerializer)
@api_view(['GET'])
@permission_classes([IsAuthenticated, IsStaffMember])
def get_decision_flow(request, claim_id):
    claim = get_object_or_404(Claim, id=claim_id)
    
    decision_flow, created = DecisionFlow.objects.get_or_create(
        claim=claim,
        defaults={
            'agents': ['claim_agent', 'policy_agent', 'fraud_agent', 'damage_agent', 'settlement_agent'],
            'rl_recommendation': {},
            'final_decision': {}
        }
    )
    
    from .serializers import DecisionFlowSerializer
    serializer = DecisionFlowSerializer(decision_flow)
    return Response(serializer.data)


@extend_schema(responses=OpenApiTypes.OBJECT)
@api_view(['GET'])
@permission_classes([IsAuthenticated])
def model_status(request):
    if not request.user.is_staff_member:
        return Response({'detail': 'Staff access is required.'}, status=status.HTTP_403_FORBIDDEN)
    from ml_service import get_model_status
    current = get_model_status()
    report = current.pop('training_report', None)
    return Response({
        'models': current,
        'trained_at': report.get('trained_at') if report else None,
        'datasets': report.get('datasets', {}) if report else {},
        'metrics': report.get('metrics', []) if report else [],
        'data_audit': report.get('data_audit', {}) if report else {},
    })
