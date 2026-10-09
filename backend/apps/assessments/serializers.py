from rest_framework import serializers
from .models import ClaimAssessment, AgentOutput, DecisionFlow, ModelPerformance

class ClaimAssessmentSerializer(serializers.ModelSerializer):
    claim_number = serializers.CharField(source='claim.claim_number', read_only=True)
    customer_name = serializers.CharField(source='claim.customer.get_full_name', read_only=True)
    reviewed_by_name = serializers.CharField(source='reviewed_by.get_full_name', read_only=True)
    
    class Meta:
        model = ClaimAssessment
        fields = [
            'id', 'claim', 'claim_number', 'customer_name', 'assessment_type',
            'status', 'model_version', 'predicted_repair_cost', 'cost_breakdown',
            'repair_time_estimate_days', 'comparable_claims_count', 'fraud_risk_score',
            'risk_level', 'risk_factors', 'behavioral_indicators', 'network_analysis',
            'total_loss_probability', 'claim_priority', 'ai_recommendation',
            'confidence', 'contributing_factors', 'assessed_at', 'created_at',
            'updated_at', 'reviewed_by', 'reviewed_by_name', 'reviewed_at'
        ]
        read_only_fields = ['id', 'created_at', 'updated_at', 'assessed_at', 'reviewed_by', 'reviewed_at']

class ClaimAssessmentCreateSerializer(serializers.ModelSerializer):
    class Meta:
        model = ClaimAssessment
        fields = [
            'claim', 'assessment_type', 'model_version',
            'predicted_repair_cost', 'cost_breakdown', 'repair_time_estimate_days',
            'comparable_claims_count', 'fraud_risk_score', 'risk_level',
            'risk_factors', 'behavioral_indicators', 'network_analysis',
            'total_loss_probability', 'claim_priority', 'ai_recommendation',
            'confidence', 'contributing_factors'
        ]

class AgentOutputSerializer(serializers.ModelSerializer):
    claim_number = serializers.CharField(source='claim.claim_number', read_only=True)
    
    class Meta:
        model = AgentOutput
        fields = [
            'id', 'claim', 'claim_number', 'agent_type', 'status',
            'input_data', 'output_data', 'confidence', 'processing_time_seconds',
            'error_message', 'created_at', 'completed_at'
        ]
        read_only_fields = ['id', 'created_at', 'completed_at']

class DecisionFlowSerializer(serializers.ModelSerializer):
    claim_number = serializers.CharField(source='claim.claim_number', read_only=True)
    
    class Meta:
        model = DecisionFlow
        fields = [
            'id', 'claim', 'claim_number', 'agents', 'rl_recommendation',
            'final_decision', 'model_version', 'decided_at', 'decided_by',
            'created_at', 'updated_at'
        ]
        read_only_fields = ['id', 'created_at', 'updated_at', 'decided_at']

class ModelPerformanceSerializer(serializers.ModelSerializer):
    class Meta:
        model = ModelPerformance
        fields = [
            'id', 'model_type', 'version', 'accuracy', 'precision', 'recall',
            'f1_score', 'mae', 'rmse', 'r2_score', 'auc', 'training_samples',
            'validation_samples', 'test_samples', 'training_duration_seconds',
            'hyperparameters', 'metrics', 'artifact_path', 'is_active',
            'trained_at', 'registered_at'
        ]
        read_only_fields = ['id', 'registered_at']