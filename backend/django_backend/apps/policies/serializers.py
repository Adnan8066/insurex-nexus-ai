from decimal import Decimal

from rest_framework import serializers
from drf_spectacular.types import OpenApiTypes
from drf_spectacular.utils import extend_schema_field
from django.contrib.auth import get_user_model
from django.utils.dateparse import parse_date
from apps.accounts.models import Role
from common.uploads import validate_upload
from apps.vehicles.models import Vehicle
from .models import Policy, PolicyApplication, PolicyEndorsement, PolicyCoverage, PolicyDocument, PremiumHistory

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

    def validate_file(self, value):
        return validate_upload(value)

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


class PolicyAmountValidationMixin:
    def validate_premium(self, value):
        if value is not None and value <= 0:
            raise serializers.ValidationError('Premium must be greater than zero.')
        return value

    def validate_deductible(self, value):
        if value is not None and value < 0:
            raise serializers.ValidationError('Deductible cannot be negative.')
        return value


class PolicyCreateSerializer(PolicyAmountValidationMixin, serializers.ModelSerializer):
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

class PolicyUpdateSerializer(PolicyAmountValidationMixin, serializers.ModelSerializer):
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


class PolicyQuoteSerializer(serializers.ModelSerializer):
    """Collect the minimum underwriting intake needed for a versioned quote."""
    customer = serializers.PrimaryKeyRelatedField(queryset=User.objects.filter(role=Role.CUSTOMER, is_active=True))
    class Meta:
        model = PolicyApplication
        fields = [
            'customer', 'policy_type', 'applicant_details', 'asset_details', 'risk_factors',
            'asset_value', 'coverage_limit', 'deductible', 'risk_score', 'policy_terms',
        ]

    def validate(self, attrs):
        request_user = self.context['request'].user
        customer = attrs['customer']
        if request_user.role == Role.CUSTOMER and customer.pk != request_user.pk:
            raise serializers.ValidationError({'customer': 'You can only request a quote for your own account.'})
        if attrs['asset_value'] <= 0 or attrs['coverage_limit'] <= 0:
            raise serializers.ValidationError('Asset value and coverage limit must be positive.')
        if attrs['deductible'] < 0:
            raise serializers.ValidationError({'deductible': 'Deductible cannot be negative.'})
        if not Decimal('0') <= attrs['risk_score'] <= Decimal('100'):
            raise serializers.ValidationError({'risk_score': 'Risk score must be between 0 and 100.'})
        if attrs['deductible'] >= attrs['coverage_limit']:
            raise serializers.ValidationError({'deductible': 'Deductible must be below the coverage limit.'})
        terms = attrs['policy_terms']
        if not isinstance(terms, dict) or not terms.get('start_date') or not terms.get('end_date'):
            raise serializers.ValidationError({'policy_terms': 'start_date and end_date are required.'})
        start_date = parse_date(str(terms['start_date']))
        end_date = parse_date(str(terms['end_date']))
        if not start_date or not end_date or end_date < start_date:
            raise serializers.ValidationError({'policy_terms': 'Provide valid dates with end_date on or after start_date.'})
        terms['start_date'] = start_date.isoformat()
        terms['end_date'] = end_date.isoformat()
        if terms.get('agent') and not User.objects.filter(
            pk=terms['agent'], role__in=[Role.EMPLOYEE, Role.ADMIN], is_active=True
        ).exists():
            raise serializers.ValidationError({'policy_terms': 'Assigned agent must be an active employee or admin.'})
        if terms.get('payment_frequency', 'annual') not in {'monthly', 'quarterly', 'semi_annual', 'annual'}:
            raise serializers.ValidationError({'policy_terms': 'Unsupported payment frequency.'})
        vehicle_id = terms.get('vehicle')
        if vehicle_id:
            vehicle = Vehicle.objects.filter(pk=vehicle_id, customer=customer).first()
            if vehicle is None:
                raise serializers.ValidationError({'policy_terms': 'Vehicle must belong to the selected customer.'})
            if vehicle.policy_id:
                raise serializers.ValidationError({'policy_terms': 'Vehicle is already insured by a policy.'})
            terms['vehicle'] = vehicle.pk
        if attrs['policy_type'].startswith('auto_') and not vehicle_id:
            raise serializers.ValidationError({'policy_terms': 'Choose a vehicle for an auto policy.'})
        return attrs


class PolicyApplicationSerializer(serializers.ModelSerializer):
    customer_name = serializers.SerializerMethodField()
    customer_email = serializers.EmailField(source='customer.email', read_only=True)
    vehicle_label = serializers.SerializerMethodField()
    requested_by_customer = serializers.SerializerMethodField()
    bound_policy_number = serializers.CharField(source='bound_policy.policy_number', read_only=True, default=None)
    reviewed_by_name = serializers.SerializerMethodField()
    assigned_to_name = serializers.SerializerMethodField()

    class Meta:
        model = PolicyApplication
        fields = [
            'id', 'customer', 'customer_name', 'customer_email', 'policy_type', 'applicant_details',
            'asset_details', 'risk_factors', 'asset_value', 'coverage_limit', 'deductible', 'risk_score',
            'quoted_premium', 'rating_breakdown', 'policy_terms', 'vehicle_label', 'status',
            'requested_by_customer', 'assigned_to', 'assigned_to_name', 'bound_policy', 'bound_policy_number', 'reviewed_by_name',
            'reviewed_at', 'review_note', 'created_at',
        ]
        read_only_fields = fields

    @extend_schema_field(OpenApiTypes.STR)
    def get_customer_name(self, obj):
        return obj.customer.get_full_name() or obj.customer.email

    @extend_schema_field(OpenApiTypes.STR)
    def get_vehicle_label(self, obj):
        vehicle_id = (obj.policy_terms or {}).get('vehicle')
        vehicle = Vehicle.objects.filter(pk=vehicle_id).first() if vehicle_id else None
        if vehicle is None:
            return ''
        return f'{vehicle.year} {vehicle.make} {vehicle.model} ({vehicle.license_plate})'.strip()

    @extend_schema_field(OpenApiTypes.BOOL)
    def get_requested_by_customer(self, obj):
        return obj.created_by_id == obj.customer_id

    @extend_schema_field(OpenApiTypes.STR)
    def get_assigned_to_name(self, obj):
        if not obj.assigned_to:
            return ''
        return obj.assigned_to.get_full_name() or obj.assigned_to.email

    @extend_schema_field(OpenApiTypes.STR)
    def get_reviewed_by_name(self, obj):
        if not obj.reviewed_by:
            return ''
        return obj.reviewed_by.get_full_name() or obj.reviewed_by.email


class PolicyEndorsementSerializer(serializers.ModelSerializer):
    class Meta:
        model = PolicyEndorsement
        fields = [
            'id', 'policy', 'change_type', 'proposed_changes', 'premium_delta', 'before_snapshot',
            'after_snapshot', 'status', 'created_by', 'reviewed_by', 'created_at', 'reviewed_at',
        ]
        read_only_fields = fields


class PolicyEndorsementCreateSerializer(serializers.Serializer):
    change_type = serializers.CharField(max_length=40)
    coverage = serializers.DictField(required=False)
    deductible = serializers.DecimalField(max_digits=10, decimal_places=2, min_value=0, required=False)
    premium_delta = serializers.DecimalField(max_digits=12, decimal_places=2, required=False, default=0)
    assets_add = serializers.ListField(child=serializers.DictField(), required=False)

    def validate(self, attrs):
        if not any(key in attrs for key in ('coverage', 'deductible', 'assets_add')):
            raise serializers.ValidationError('Provide coverage, deductible, or assets_add changes.')
        for asset in attrs.get('assets_add', []):
            if not asset.get('description') or Decimal(str(asset.get('value', 0))) <= 0:
                raise serializers.ValidationError({'assets_add': 'Each asset needs a description and positive value.'})
        return attrs
