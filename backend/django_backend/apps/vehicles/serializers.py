import re

from django.utils import timezone
from rest_framework import serializers
from common.uploads import validate_upload
from django.contrib.auth import get_user_model
from apps.accounts.models import Role
from .models import Vehicle, VehicleDocument, VehicleHistory
from apps.policies.models import Policy

User = get_user_model()


VIN_PATTERN = re.compile(r'^[A-HJ-NPR-Z0-9]{17}$')


class VehicleValueValidationMixin:
    """Range checks shared by vehicle create/update (no DB constraints needed)."""

    def validate_year(self, value):
        if value is not None and not 1900 <= value <= timezone.localdate().year + 1:
            raise serializers.ValidationError('Enter a valid model year.')
        return value

    def validate_purchase_price(self, value):
        if value is not None and value < 0:
            raise serializers.ValidationError('Purchase price cannot be negative.')
        return value

    def validate_current_mileage(self, value):
        if value is not None and value < 0:
            raise serializers.ValidationError('Mileage cannot be negative.')
        return value


class VehicleDocumentSerializer(serializers.ModelSerializer):
    class Meta:
        model = VehicleDocument
        fields = ['id', 'document_type', 'file', 'original_name', 'uploaded_at', 'uploaded_by']
        read_only_fields = ['id', 'uploaded_at', 'uploaded_by']

    def validate_file(self, value):
        return validate_upload(value)

class VehicleHistorySerializer(serializers.ModelSerializer):
    class Meta:
        model = VehicleHistory
        fields = ['id', 'event_type', 'description', 'date', 'mileage', 'cost', 'performed_by', 'created_at']
        read_only_fields = ['id', 'created_at']

class VehicleSerializer(serializers.ModelSerializer):
    customer_email = serializers.EmailField(source='customer.email', read_only=True)
    customer_name = serializers.CharField(source='customer.get_full_name', read_only=True)
    policy_number = serializers.CharField(source='policy.policy_number', read_only=True)
    documents = VehicleDocumentSerializer(many=True, read_only=True)
    history = VehicleHistorySerializer(many=True, read_only=True)
    
    class Meta:
        model = Vehicle
        fields = [
            'id', 'customer', 'customer_email', 'customer_name', 'policy', 'policy_number',
            'make', 'model', 'year', 'vin', 'color', 'license_plate', 'license_state',
            'registration_expiry', 'purchase_date', 'purchase_price', 'current_mileage',
            'fuel_type', 'transmission', 'status', 'engine_size', 'body_style', 'features',
            'created_at', 'updated_at', 'documents', 'history'
        ]
        read_only_fields = ['id', 'created_at', 'updated_at']

class VehicleCreateSerializer(VehicleValueValidationMixin, serializers.ModelSerializer):
    customer = serializers.PrimaryKeyRelatedField(
        required=False, allow_null=True,
        queryset=User.objects.filter(role=Role.CUSTOMER, is_active=True),
    )
    license_state = serializers.CharField(required=False, default='IL')

    class Meta:
        model = Vehicle
        fields = [
            'customer', 'policy', 'make', 'model', 'year', 'vin', 'color',
            'license_plate', 'license_state', 'registration_expiry',
            'purchase_date', 'purchase_price', 'current_mileage', 'fuel_type',
            'transmission', 'status', 'engine_size', 'body_style', 'features'
        ]

    def validate_vin(self, value):
        value = (value or '').strip().upper()
        if not VIN_PATTERN.match(value):
            raise serializers.ValidationError('VIN must be 17 characters (letters and digits, excluding I, O and Q).')
        return value

    def validate(self, attrs):
        request_user = self.context['request'].user
        customer = attrs.get('customer') or request_user
        policy = attrs.get('policy')
        if request_user.role in [Role.EMPLOYEE, Role.ADMIN] and not attrs.get('customer'):
            raise serializers.ValidationError({'customer': 'Choose the customer who owns this vehicle.'})
        if request_user.role == Role.CUSTOMER and customer.pk != request_user.pk:
            raise serializers.ValidationError({'customer': 'You can only register a vehicle for your own account.'})
        if policy and policy.customer_id != customer.pk:
            raise serializers.ValidationError({'policy': 'The selected policy does not belong to this customer.'})
        if policy and policy.vehicle_id:
            raise serializers.ValidationError({'policy': 'The selected policy is already linked to another vehicle.'})
        return attrs

class VehicleUpdateSerializer(VehicleValueValidationMixin, serializers.ModelSerializer):
    class Meta:
        model = Vehicle
        fields = [
            'policy', 'make', 'model', 'year', 'color', 'license_plate',
            'license_state', 'registration_expiry', 'purchase_date', 'purchase_price',
            'current_mileage', 'fuel_type', 'transmission', 'status',
            'engine_size', 'body_style', 'features'
        ]

    def validate(self, attrs):
        policy = attrs.get('policy')
        if policy and policy.customer_id != self.instance.customer_id:
            raise serializers.ValidationError({'policy': 'The selected policy does not belong to this vehicle customer.'})
        if policy and policy.vehicle_id and policy.vehicle_id != self.instance.pk:
            raise serializers.ValidationError({'policy': 'The selected policy is already linked to another vehicle.'})
        return attrs
