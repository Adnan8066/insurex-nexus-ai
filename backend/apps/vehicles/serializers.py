from rest_framework import serializers
from .models import Vehicle, VehicleDocument, VehicleHistory

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
    class Meta:
        model = Vehicle
        fields = [
            'customer', 'policy', 'make', 'model', 'year', 'vin', 'color',
            'license_plate', 'license_state', 'registration_expiry',
            'purchase_date', 'purchase_price', 'current_mileage', 'fuel_type',
            'transmission', 'status', 'engine_size', 'body_style', 'features'
        ]

class VehicleUpdateSerializer(serializers.ModelSerializer):
    class Meta:
        model = Vehicle
        fields = [
            'policy', 'make', 'model', 'year', 'color', 'license_plate',
            'license_state', 'registration_expiry', 'purchase_date', 'purchase_price',
            'current_mileage', 'fuel_type', 'transmission', 'status',
            'engine_size', 'body_style', 'features'
        ]