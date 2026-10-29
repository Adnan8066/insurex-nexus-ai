from django.utils import timezone
from rest_framework import serializers
from common.uploads import validate_upload
from drf_spectacular.types import OpenApiTypes
from drf_spectacular.utils import extend_schema_field
from .models import Claim, ClaimDocument, ClaimStatusHistory, ClaimTimeline, ClaimNote, ClaimStatus, ClaimPriority

class ClaimDocumentSerializer(serializers.ModelSerializer):
    uploaded_by_name = serializers.CharField(source='uploaded_by.get_full_name', read_only=True)
    verified_by_name = serializers.CharField(source='verified_by.get_full_name', read_only=True)
    
    class Meta:
        model = ClaimDocument
        fields = [
            'id', 'document_type', 'file', 'original_name', 'description',
            'uploaded_at', 'uploaded_by', 'uploaded_by_name', 'verified',
            'verified_by', 'verified_by_name', 'verified_at'
        ]
        read_only_fields = ['id', 'uploaded_at', 'uploaded_by', 'verified', 'verified_by', 'verified_at']

    def validate_file(self, value):
        return validate_upload(value)

class ClaimStatusHistorySerializer(serializers.ModelSerializer):
    changed_by_name = serializers.CharField(source='changed_by.get_full_name', read_only=True)
    
    class Meta:
        model = ClaimStatusHistory
        fields = ['id', 'from_status', 'to_status', 'reason', 'changed_by', 'changed_by_name', 'changed_at', 'metadata']
        read_only_fields = ['id', 'changed_at', 'changed_by']

class ClaimTimelineSerializer(serializers.ModelSerializer):
    user_name = serializers.CharField(source='user.get_full_name', read_only=True)
    
    class Meta:
        model = ClaimTimeline
        fields = ['id', 'status', 'title', 'description', 'user', 'user_name', 'timestamp', 'is_system', 'metadata']
        read_only_fields = ['id', 'timestamp', 'user']

class ClaimNoteSerializer(serializers.ModelSerializer):
    author_name = serializers.CharField(source='author.get_full_name', read_only=True)
    
    class Meta:
        model = ClaimNote
        fields = ['id', 'content', 'is_internal', 'author', 'author_name', 'created_at', 'updated_at']
        read_only_fields = ['id', 'author', 'created_at', 'updated_at']

class ClaimSerializer(serializers.ModelSerializer):
    customer_email = serializers.EmailField(source='customer.email', read_only=True)
    customer_name = serializers.CharField(source='customer.get_full_name', read_only=True)
    policy_number = serializers.CharField(source='policy.policy_number', read_only=True)
    vehicle_info = serializers.SerializerMethodField()
    assigned_adjuster_name = serializers.CharField(source='assigned_adjuster.get_full_name', read_only=True)
    assigned_investigator_name = serializers.CharField(source='assigned_investigator.get_full_name', read_only=True)
    documents = ClaimDocumentSerializer(many=True, read_only=True)
    status_history = ClaimStatusHistorySerializer(many=True, read_only=True)
    timeline = ClaimTimelineSerializer(many=True, read_only=True)
    notes = ClaimNoteSerializer(many=True, read_only=True)
    
    class Meta:
        model = Claim
        fields = [
            'id', 'claim_number', 'customer', 'customer_email', 'customer_name',
            'policy', 'policy_number', 'vehicle', 'vehicle_info',
            'incident_date', 'incident_time', 'incident_type', 'incident_severity',
            'location', 'latitude', 'longitude', 'number_of_vehicles',
            'injuries', 'injury_details', 'property_damage', 'property_damage_details',
            'witnesses', 'witness_details', 'police_report', 'police_report_number',
            'claim_amount', 'description', 'status', 'priority',
            'estimated_repair_cost', 'complexity_score',
            'assigned_adjuster', 'assigned_adjuster_name',
            'assigned_investigator', 'assigned_investigator_name',
            'ai_assessment', 'fraud_risk_score', 'total_loss_probability',
            'submitted_at', 'updated_at', 'closed_at',
            'documents', 'status_history', 'timeline', 'notes'
        ]
        read_only_fields = ['id', 'claim_number', 'submitted_at', 'updated_at', 'closed_at', 'complexity_score']

    def to_representation(self, instance):
        data = super().to_representation(instance)
        request = self.context.get('request')
        if request is None or request.user.role == 'customer':
            # Model outputs and internal staff notes are never shown to customers
            # (or when the caller did not supply a request context).
            data.pop('ai_assessment', None)
            data.pop('fraud_risk_score', None)
            data.pop('total_loss_probability', None)
            data['notes'] = [note for note in data.get('notes', []) if not note.get('is_internal')]
        return data
    
    @extend_schema_field(OpenApiTypes.OBJECT)
    def get_vehicle_info(self, obj):
        if obj.vehicle:
            return {
                'id': obj.vehicle.id,
                'make': obj.vehicle.make,
                'model': obj.vehicle.model,
                'year': obj.vehicle.year,
                'license_plate': obj.vehicle.license_plate,
                'vin': obj.vehicle.vin
            }
        return None

class ClaimCreateSerializer(serializers.ModelSerializer):
    class Meta:
        model = Claim
        fields = [
            'policy', 'vehicle', 'incident_date', 'incident_time',
            'incident_type', 'incident_severity', 'location', 'latitude', 'longitude',
            'number_of_vehicles', 'injuries', 'injury_details', 'property_damage',
            'property_damage_details', 'witnesses', 'witness_details', 'police_report',
            'police_report_number', 'claim_amount', 'estimated_repair_cost', 'description'
        ]
    
    def validate(self, attrs):
        policy = attrs.get('policy')
        vehicle = attrs.get('vehicle')
        request_user = self.context['request'].user
        customer = policy.customer if policy else request_user
        
        if request_user.role == 'customer' and policy.customer_id != request_user.id:
            raise serializers.ValidationError('Policy does not belong to the current user.')

        if vehicle.customer_id != customer.id or policy.customer_id != vehicle.customer_id:
            raise serializers.ValidationError('The selected vehicle and policy must belong to the same customer.')
        
        if vehicle.policy_id and vehicle.policy_id != policy.id:
            raise serializers.ValidationError('Vehicle is not covered by the selected policy.')

        if policy.vehicle_id and policy.vehicle_id != vehicle.id:
            raise serializers.ValidationError('The selected vehicle does not match the vehicle linked to this policy.')

        incident_date = attrs.get('incident_date')
        if incident_date and policy.start_date and policy.end_date and not (
            policy.start_date <= incident_date <= policy.end_date
        ):
            raise serializers.ValidationError({
                'incident_date': f'The incident date must fall within the policy term ({policy.start_date} to {policy.end_date}).'
            })
        return attrs

    def validate_incident_date(self, value):
        if value > timezone.localdate():
            raise serializers.ValidationError('The incident date cannot be in the future.')
        return value

    def validate_claim_amount(self, value):
        if value is None or value <= 0:
            raise serializers.ValidationError('Claim amount must be greater than zero.')
        return value

    def validate_estimated_repair_cost(self, value):
        if value is not None and value < 0:
            raise serializers.ValidationError('Estimated repair cost cannot be negative.')
        return value

class ClaimUpdateSerializer(serializers.ModelSerializer):
    class Meta:
        model = Claim
        fields = [
            'incident_type', 'incident_severity', 'location', 'latitude', 'longitude',
            'number_of_vehicles', 'injuries', 'injury_details', 'property_damage',
            'property_damage_details', 'witnesses', 'witness_details', 'police_report',
            'police_report_number', 'claim_amount', 'description',
            'estimated_repair_cost',
            'status', 'priority', 'assigned_adjuster', 'assigned_investigator',
            'ai_assessment', 'fraud_risk_score', 'total_loss_probability'
        ]

    MODEL_OUTPUT_FIELDS = {'ai_assessment', 'fraud_risk_score', 'total_loss_probability'}

    def validate(self, attrs):
        request = self.context.get('request')
        submitted = set(getattr(self, 'initial_data', {}).keys())
        if 'status' in submitted:
            # Status changes must go through the update-status endpoint, which
            # enforces the workflow rules and records ClaimStatusHistory.
            raise serializers.ValidationError({
                'status': 'Use the update-status endpoint to change a claim status.'
            })
        if request and request.user.role == 'customer':
            protected_fields = {
                'priority', 'assigned_adjuster', 'assigned_investigator',
            } | self.MODEL_OUTPUT_FIELDS
            attempted = protected_fields.intersection(submitted)
            if attempted:
                raise serializers.ValidationError({
                    field: 'Only staff can update this field.' for field in sorted(attempted)
                })
        elif request and request.user.role != 'admin':
            # AI outputs drive the investigation rule; only admins may override them.
            attempted = self.MODEL_OUTPUT_FIELDS.intersection(submitted)
            if attempted:
                raise serializers.ValidationError({
                    field: 'AI model outputs can only be overridden by an administrator.' for field in sorted(attempted)
                })
        return attrs

    def validate_claim_amount(self, value):
        if value is None or value <= 0:
            raise serializers.ValidationError('Claim amount must be greater than zero.')
        return value

    def validate_estimated_repair_cost(self, value):
        if value is not None and value < 0:
            raise serializers.ValidationError('Estimated repair cost cannot be negative.')
        return value

class ClaimStatusUpdateSerializer(serializers.Serializer):
    status = serializers.ChoiceField(choices=ClaimStatus.choices)
    reason = serializers.CharField(required=False, allow_blank=True)
