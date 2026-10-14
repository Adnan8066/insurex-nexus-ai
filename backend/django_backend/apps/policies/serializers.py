from rest_framework import serializers
from drf_spectacular.types import OpenApiTypes
from drf_spectacular.utils import extend_schema_field
from django.contrib.auth import get_user_model
from apps.accounts.models import Role
from apps.vehicles.models import Vehicle
from .models import Policy, PolicyCoverage, PolicyDocument, PremiumHistory

User = get_user_model()

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
    
    @extend_schema_field(OpenApiTypes.OBJECT)
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
    customer = serializers.PrimaryKeyRelatedField(
        required=False, allow_null=True,
        queryset=User.objects.filter(role=Role.CUSTOMER, is_active=True),
    )
    agent = serializers.PrimaryKeyRelatedField(
        required=False, allow_null=True,
        queryset=User.objects.filter(role__in=[Role.EMPLOYEE, Role.ADMIN], is_active=True),
    )
    vehicle = serializers.PrimaryKeyRelatedField(
        required=False, allow_null=True, queryset=Vehicle.objects.all(),
    )

    class Meta:
        model = Policy
        fields = [
            'customer', 'agent', 'type', 'status', 'start_date', 'end_date',
            'premium', 'deductible', 'payment_frequency', 'auto_renew',
            'coverage', 'vehicle', 'property_address', 'property_type',
            'property_year_built', 'property_square_footage'
        ]

    def validate(self, attrs):
        request_user = self.context['request'].user
        customer = attrs.get('customer') or request_user
        vehicle = attrs.get('vehicle')
        if request_user.role in [Role.EMPLOYEE, Role.ADMIN] and not attrs.get('customer'):
            raise serializers.ValidationError({'customer': 'Choose the customer who owns this policy.'})
        if request_user.role == Role.CUSTOMER and customer.pk != request_user.pk:
            raise serializers.ValidationError({'customer': 'You can only create a policy for your own account.'})
        if vehicle and vehicle.customer_id != customer.pk:
            raise serializers.ValidationError({'vehicle': 'The selected vehicle does not belong to this customer.'})
        if vehicle and vehicle.policy_id:
            raise serializers.ValidationError({'vehicle': 'The selected vehicle is already linked to another policy.'})
        if attrs.get('type', '').startswith('auto_') and not vehicle:
            raise serializers.ValidationError({'vehicle': 'Choose a customer-owned vehicle for an auto policy.'})
        if attrs.get('start_date') and attrs.get('end_date') and attrs['end_date'] < attrs['start_date']:
            raise serializers.ValidationError({'end_date': 'End date must be on or after the start date.'})
        return attrs

class PolicyUpdateSerializer(serializers.ModelSerializer):
    customer = serializers.PrimaryKeyRelatedField(
        required=False,
        queryset=User.objects.filter(role=Role.CUSTOMER, is_active=True),
    )
    agent = serializers.PrimaryKeyRelatedField(
        required=False, allow_null=True,
        queryset=User.objects.filter(role__in=[Role.EMPLOYEE, Role.ADMIN], is_active=True),
    )

    class Meta:
        model = Policy
        fields = [
            'customer', 'agent', 'status', 'start_date', 'end_date', 'premium', 'deductible',
            'payment_frequency', 'auto_renew', 'coverage', 'vehicle',
            'property_address', 'property_type', 'property_year_built',
            'property_square_footage'
        ]

    def validate(self, attrs):
        customer = attrs.get('customer', self.instance.customer)
        vehicle = attrs.get('vehicle')
        if vehicle is None and 'vehicle' not in attrs:
            vehicle = self.instance.vehicle
        is_current_linked_vehicle = bool(
            vehicle
            and vehicle.pk == self.instance.vehicle_id
            and vehicle.customer_id == self.instance.customer_id
        )
        if vehicle and vehicle.customer_id != customer.pk and not is_current_linked_vehicle:
            raise serializers.ValidationError({'vehicle': 'The selected vehicle does not belong to this policy customer.'})
        if vehicle and vehicle.policy_id and vehicle.policy_id != self.instance.pk:
            raise serializers.ValidationError({'vehicle': 'The selected vehicle is already linked to another policy.'})
        policy_type = attrs.get('type', self.instance.type)
        if policy_type.startswith('auto_') and not vehicle:
            raise serializers.ValidationError({'vehicle': 'Choose a customer-owned vehicle for an auto policy.'})
        start_date = attrs.get('start_date', self.instance.start_date)
        end_date = attrs.get('end_date', self.instance.end_date)
        if end_date < start_date:
            raise serializers.ValidationError({'end_date': 'End date must be on or after the start date.'})
        return attrs
