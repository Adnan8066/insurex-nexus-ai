from rest_framework import serializers
from .models import Policy, PolicyCoverage, PolicyDocument, PremiumHistory

class PolicyCoverageSerializer(serializers.ModelSerializer):
    class Meta:
        model = PolicyCoverage
        fields = [
            'liability', 'collision', 'comprehensive', 'uninsured_motorist',
            'medical_payments', 'personal_injury_protection', 'roadside_assistance',
            'rental_reimbursement', 'glass_coverage', 'dwelling', 'personal_property',
            'additional_living_expenses', 'created_at', 'updated_at'
        ]
        read_only_fields = ['created_at', 'updated_at']

class PolicyDocumentSerializer(serializers.ModelSerializer):
    class Meta:
        model = PolicyDocument
        fields = ['id', 'document_type', 'file', 'original_name', 'uploaded_at', 'uploaded_by']
        read_only_fields = ['id', 'uploaded_at', 'uploaded_by']

class PremiumHistorySerializer(serializers.ModelSerializer):
    class Meta:
        model = PremiumHistory
        fields = [
            'id', 'amount', 'due_date', 'paid_date', 'status',
            'payment_method', 'transaction_id', 'created_at'
        ]
        read_only_fields = ['id', 'created_at']

class PolicySerializer(serializers.ModelSerializer):
    customer_email = serializers.EmailField(source='customer.email', read_only=True)
    customer_name = serializers.CharField(source='customer.get_full_name', read_only=True)
    agent_name = serializers.CharField(source='agent.get_full_name', read_only=True)
    vehicle_info = serializers.SerializerMethodField()
    coverage_details = PolicyCoverageSerializer(read_only=True)
    documents = PolicyDocumentSerializer(many=True, read_only=True)
    premium_history = PremiumHistorySerializer(many=True, read_only=True)
    is_active = serializers.BooleanField(read_only=True)
    days_remaining = serializers.IntegerField(read_only=True)
    
    class Meta:
        model = Policy
        fields = [
            'id', 'policy_number', 'customer', 'customer_email', 'customer_name',
            'agent', 'agent_name', 'type', 'status', 'start_date', 'end_date',
            'premium', 'deductible', 'payment_frequency', 'auto_renew',
            'coverage', 'vehicle', 'vehicle_info', 'property_address',
            'property_type', 'property_year_built', 'property_square_footage',
            'created_at', 'updated_at', 'coverage_details', 'documents',
            'premium_history', 'is_active', 'days_remaining'
        ]
        read_only_fields = ['id', 'policy_number', 'created_at', 'updated_at']
    
    def get_vehicle_info(self, obj):
        if obj.vehicle:
            return {
                'id': obj.vehicle.id,
                'make': obj.vehicle.make,
                'model': obj.vehicle.model,
                'year': obj.vehicle.year,
                'license_plate': obj.vehicle.license_plate
            }
        return None

class PolicyCreateSerializer(serializers.ModelSerializer):
    class Meta:
        model = Policy
        fields = [
            'customer', 'agent', 'type', 'status', 'start_date', 'end_date',
            'premium', 'deductible', 'payment_frequency', 'auto_renew',
            'coverage', 'vehicle', 'property_address', 'property_type',
            'property_year_built', 'property_square_footage'
        ]

class PolicyUpdateSerializer(serializers.ModelSerializer):
    class Meta:
        model = Policy
        fields = [
            'agent', 'status', 'start_date', 'end_date', 'premium', 'deductible',
            'payment_frequency', 'auto_renew', 'coverage', 'vehicle',
            'property_address', 'property_type', 'property_year_built',
            'property_square_footage'
        ]