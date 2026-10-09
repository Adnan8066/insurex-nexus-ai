from rest_framework.decorators import api_view, permission_classes
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response
from rest_framework import status
from django.shortcuts import get_object_or_404

from apps.claims.models import Claim
from .models import ClaimAssessment, AgentOutput, DecisionFlow
from .serializers import ClaimAssessmentSerializer


@api_view(['POST'])
@permission_classes([IsAuthenticated])
def assess_claim(request):
    claim_id = request.data.get('claim_id')
    if not claim_id:
        return Response({'error': 'claim_id is required'}, status=status.HTTP_400_BAD_REQUEST)
    
    claim = get_object_or_404(Claim, id=claim_id)
    
    if not request.user.is_staff_member and claim.customer != request.user:
        return Response({'error': 'Not authorized'}, status=status.HTTP_403_FORBIDDEN)
    
    assessment, created = ClaimAssessment.objects.get_or_create(
        claim=claim,
        defaults={'assessment_type': ClaimAssessment.AssessmentType.COMPREHENSIVE}
    )
    
    assessment.status = ClaimAssessment.AssessmentStatus.IN_PROGRESS
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
        assessment.status = ClaimAssessment.AssessmentStatus.COMPLETED
        assessment.save()
        
        serializer = ClaimAssessmentSerializer(assessment)
        return Response(serializer.data)
        
    except Exception as e:
        assessment.status = ClaimAssessment.AssessmentStatus.FAILED
        assessment.save()
        return Response({'error': str(e)}, status=status.HTTP_500_INTERNAL_SERVER_ERROR)


def predict_repair_cost_internal(claim):
    return {
        'cost': claim.claim_amount * 0.85,
        'breakdown': {
            'labor': claim.claim_amount * 0.4,
            'parts': claim.claim_amount * 0.35,
            'materials': claim.claim_amount * 0.1,
            'overhead': claim.claim_amount * 0.05
        },
        'time_estimate': 5,
        'comparable_count': 12
    }


def detect_fraud_internal(claim):
    return {
        'score': 15.0,
        'level': 'low',
        'factors': ['normal claim pattern', 'consistent documentation'],
        'behavioral': ['prompt reporting', 'cooperative'],
        'network': {'connected_claims': 0, 'shared_parties': []}
    }


def predict_total_loss_internal(claim):
    return {
        'probability': 10.0
    }


def generate_recommendation(assessment):
    if assessment.fraud_risk_score and assessment.fraud_risk_score > 70:
        return "High fraud risk detected. Recommend SIU investigation before settlement."
    elif assessment.total_loss_probability and assessment.total_loss_probability > 50:
        return "High probability of total loss. Consider total loss settlement path."
    else:
        return "Standard processing recommended. Proceed with repair assessment."


def calculate_confidence(assessment):
    return 85.0


from django.utils import timezone


@api_view(['POST'])
@permission_classes([IsAuthenticated])
def predict_repair_cost(request):
    claim_id = request.data.get('claim_id')
    if not claim_id:
        return Response({'error': 'claim_id is required'}, status=status.HTTP_400_BAD_REQUEST)
    
    claim = get_object_or_404(Claim, id=claim_id)
    result = predict_repair_cost_internal(claim)
    return Response(result)


@api_view(['POST'])
@permission_classes([IsAuthenticated])
def detect_fraud(request):
    claim_id = request.data.get('claim_id')
    if not claim_id:
        return Response({'error': 'claim_id is required'}, status=status.HTTP_400_BAD_REQUEST)
    
    claim = get_object_or_404(Claim, id=claim_id)
    result = detect_fraud_internal(claim)
    return Response(result)


@api_view(['POST'])
@permission_classes([IsAuthenticated])
def predict_total_loss(request):
    claim_id = request.data.get('claim_id')
    if not claim_id:
        return Response({'error': 'claim_id is required'}, status=status.HTTP_400_BAD_REQUEST)
    
    claim = get_object_or_404(Claim, id=claim_id)
    result = predict_total_loss_internal(claim)
    return Response(result)


@api_view(['POST'])
@permission_classes([IsAuthenticated])
def run_agent(request, agent_type):
    claim_id = request.data.get('claim_id')
    input_data = request.data.get('input_data', {})
    
    if not claim_id:
        return Response({'error': 'claim_id is required'}, status=status.HTTP_400_BAD_REQUEST)
    
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
            output_data = {'status': 'processed', 'summary': 'Claim validated'}
        elif agent_type == 'policy_agent':
            output_data = {'coverage_valid': True, 'deductible_applies': True}
        elif agent_type == 'fraud_agent':
            output_data = detect_fraud_internal(claim)
        elif agent_type == 'damage_agent':
            output_data = predict_repair_cost_internal(claim)
        elif agent_type == 'settlement_agent':
            output_data = {'recommended_amount': claim.claim_amount * 0.85}
        elif agent_type == 'decision_agent':
            output_data = {'decision': 'approve', 'reason': 'Standard claim'}
        
        agent_output.output_data = output_data
        agent_output.status = 'completed'
        agent_output.confidence = 90.0
        agent_output.processing_time_seconds = 1.5
        agent_output.completed_at = timezone.now()
        agent_output.save()
        
        return Response({'status': 'completed', 'output': output_data})
        
    except Exception as e:
        agent_output.status = 'failed'
        agent_output.error_message = str(e)
        agent_output.save()
        return Response({'error': str(e)}, status=status.HTTP_500_INTERNAL_SERVER_ERROR)


@api_view(['GET'])
@permission_classes([IsAuthenticated])
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