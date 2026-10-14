from rest_framework import serializers
from django.contrib.auth import get_user_model
from apps.accounts.models import Role
from .models import Vehicle, VehicleDocument, VehicleHistory

User = get_user_model()

class VehicleDocumentSerializer(serializers.ModelSerializer):
    class Meta:
        model = VehicleDocument
        fields = ['id', 'document_type', 'file', 'original_name', 'uploaded_at', 'uploaded_by']
        read_only_fields = ['id', 'uploaded_at', 'uploaded_by']

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

class VehicleCreateSerializer(serializers.ModelSerializer):
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

class VehicleUpdateSerializer(serializers.ModelSerializer):
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
