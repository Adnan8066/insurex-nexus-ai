from rest_framework import serializers
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
    assigned_repair_shop_name = serializers.CharField(source='assigned_repair_shop.name', read_only=True)
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
            'assigned_adjuster', 'assigned_adjuster_name',
            'assigned_investigator', 'assigned_investigator_name',
            'assigned_repair_shop', 'assigned_repair_shop_name',
            'ai_assessment', 'fraud_risk_score', 'total_loss_probability',
            'submitted_at', 'updated_at', 'closed_at',
            'documents', 'status_history', 'timeline', 'notes'
        ]
        read_only_fields = ['id', 'claim_number', 'submitted_at', 'updated_at', 'closed_at']
    
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
            'police_report_number', 'claim_amount', 'description'
        ]
    
    def validate(self, attrs):
        policy = attrs.get('policy')
        vehicle = attrs.get('vehicle')
        customer = self.context['request'].user
        
        if policy.customer != customer:
            raise serializers.ValidationError('Policy does not belong to the current user.')
        
        if vehicle.customer != customer:
            raise serializers.ValidationError('Vehicle does not belong to the current user.')
        
        if vehicle.policy != policy:
            raise serializers.ValidationError('Vehicle is not covered by the selected policy.')
        
        return attrs

class ClaimUpdateSerializer(serializers.ModelSerializer):
    class Meta:
        model = Claim
        fields = [
            'incident_type', 'incident_severity', 'location', 'latitude', 'longitude',
            'number_of_vehicles', 'injuries', 'injury_details', 'property_damage',
            'property_damage_details', 'witnesses', 'witness_details', 'police_report',
            'police_report_number', 'claim_amount', 'description',
            'status', 'priority', 'assigned_adjuster', 'assigned_investigator',
            'assigned_repair_shop', 'ai_assessment', 'fraud_risk_score', 'total_loss_probability'
        ]

class ClaimStatusUpdateSerializer(serializers.Serializer):
    status = serializers.ChoiceField(choices=ClaimStatus.choices)
    reason = serializers.CharField(required=False, allow_blank=True)