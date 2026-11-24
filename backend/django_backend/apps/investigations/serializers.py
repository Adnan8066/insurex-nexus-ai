from rest_framework import serializers
from common.uploads import EVIDENCE_EXTENSIONS, validate_upload
from .models import (
    Investigation, InvestigationEvidence, InvestigationNote, InvestigationVehicleCheck, FraudAlert,
    VehicleCheckResult,
)

class VehicleCheckItemSerializer(serializers.Serializer):
    """One row of the investigator's vehicle checklist, as submitted by the investigator."""
    check_code = serializers.CharField()
    result = serializers.ChoiceField(choices=VehicleCheckResult.choices)
    note = serializers.CharField(required=False, allow_blank=True, max_length=500, default='')

class InvestigationVehicleCheckSerializer(serializers.ModelSerializer):
    check_label = serializers.CharField(source='get_check_code_display', read_only=True)
    checked_by_name = serializers.CharField(source='checked_by.get_full_name', read_only=True)

    class Meta:
        model = InvestigationVehicleCheck
        fields = ['id', 'check_code', 'check_label', 'result', 'note', 'checked_by', 'checked_by_name', 'checked_at']
        read_only_fields = fields

class InvestigationEvidenceSerializer(serializers.ModelSerializer):
    collected_by_name = serializers.CharField(source='collected_by.get_full_name', read_only=True)
    verified_by_name = serializers.CharField(source='verified_by.get_full_name', read_only=True)
    
    class Meta:
        model = InvestigationEvidence
        fields = [
            'id', 'evidence_type', 'title', 'description', 'file', 'source',
            'collected_by', 'collected_by_name', 'collected_at', 'is_key_evidence',
            'verified', 'verified_by', 'verified_by_name', 'verified_at', 'metadata'
        ]
        read_only_fields = ['id', 'collected_at', 'collected_by', 'verified', 'verified_by', 'verified_at']

    def validate_file(self, value):
        return validate_upload(value, EVIDENCE_EXTENSIONS)

class InvestigationNoteSerializer(serializers.ModelSerializer):
    author_name = serializers.CharField(source='author.get_full_name', read_only=True)
    
    class Meta:
        model = InvestigationNote
        fields = [
            'id', 'content', 'is_interview', 'interviewee', 'interview_date',
            'is_confidential', 'author', 'author_name', 'created_at', 'updated_at'
        ]
        read_only_fields = ['id', 'author', 'created_at', 'updated_at']

class InvestigationSerializer(serializers.ModelSerializer):
    claim_number = serializers.CharField(source='claim.claim_number', read_only=True)
    customer_name = serializers.CharField(source='claim.customer.get_full_name', read_only=True)
    investigator_name = serializers.CharField(source='investigator.get_full_name', read_only=True)
    fraud_alert_risk_level = serializers.CharField(source='fraud_alert.risk_level', read_only=True)
    # Triage semantics: a review-priority signal, not a fraud finding.
    triage_priority_score = serializers.SerializerMethodField()
    heuristic_version = serializers.SerializerMethodField()
    evidence = InvestigationEvidenceSerializer(many=True, read_only=True)
    notes = InvestigationNoteSerializer(many=True, read_only=True)

    def get_triage_priority_score(self, obj):
        if obj.fraud_alert_id:
            return obj.fraud_alert.risk_score
        return obj.claim.fraud_risk_score

    def get_heuristic_version(self, obj):
        from apps.assessments.fraud_rules import TRIAGE_HEURISTIC_VERSION
        from apps.assessments.models import ClaimAssessment
        version = (
            ClaimAssessment.objects.filter(claim=obj.claim).exclude(triage_heuristic_version='')
            .order_by('-assessed_at').values_list('triage_heuristic_version', flat=True).first()
        )
        return version or TRIAGE_HEURISTIC_VERSION

    class Meta:
        model = Investigation
        fields = [
            'id', 'claim', 'claim_number', 'customer_name', 'investigator', 'investigator_name',
            'status', 'priority', 'fraud_alert', 'fraud_alert_risk_level', 'case_number',
            'summary', 'findings', 'conclusion', 'recommendation',
            'investigation_outcome', 'outcome_notes', 'outcome_reviewed_at',
            'triage_priority_score', 'heuristic_version',
            'opened_at', 'started_at', 'completed_at', 'closed_at',
            'estimated_completion', 'created_at', 'updated_at',
            'evidence', 'notes'
        ]
        read_only_fields = [
            'id', 'case_number', 'opened_at', 'created_at', 'updated_at',
            'investigation_outcome', 'outcome_notes', 'outcome_reviewed_at',
        ]

class InvestigationCreateSerializer(serializers.ModelSerializer):
    class Meta:
        model = Investigation
        fields = [
            'claim', 'investigator', 'status', 'priority', 'fraud_alert',
            'summary', 'estimated_completion'
        ]

class InvestigationUpdateSerializer(serializers.ModelSerializer):
    class Meta:
        model = Investigation
        fields = [
            'investigator', 'status', 'priority', 'fraud_alert',
            'summary', 'findings', 'conclusion', 'recommendation',
            'started_at', 'completed_at', 'closed_at', 'estimated_completion'
        ]

class FraudAlertSerializer(serializers.ModelSerializer):
    claim_number = serializers.CharField(source='claim.claim_number', read_only=True)
    customer_name = serializers.CharField(source='claim.customer.get_full_name', read_only=True)
    assigned_investigator_name = serializers.CharField(source='assigned_investigator.get_full_name', read_only=True)
    reviewed_by_name = serializers.CharField(source='reviewed_by.get_full_name', read_only=True)
    
    class Meta:
        model = FraudAlert
        fields = [
            'id', 'claim', 'claim_number', 'customer_name', 'risk_score', 'risk_level',
            'risk_factors', 'behavioral_indicators', 'network_analysis',
            'ai_recommendation', 'assigned_investigator', 'assigned_investigator_name',
            'status', 'investigator_notes', 'created_at', 'updated_at',
            'reviewed_at', 'reviewed_by', 'reviewed_by_name'
        ]
        read_only_fields = ['id', 'created_at', 'updated_at', 'reviewed_at', 'reviewed_by']

class FraudAlertUpdateSerializer(serializers.ModelSerializer):
    class Meta:
        model = FraudAlert
        fields = [
            'status', 'investigator_notes', 'assigned_investigator'
        ]