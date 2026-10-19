from rest_framework import serializers
from .models import CallbackRequest, Customer, CustomerDocument


class CallbackRequestSerializer(serializers.ModelSerializer):
    class Meta:
        model = CallbackRequest
        fields = ['id', 'name', 'phone', 'vehicle_type', 'consent', 'status', 'created_at']
        read_only_fields = ['id', 'status', 'created_at']

    def validate_phone(self, value):
        normalized = ''.join(character for character in value if character.isdigit())
        if not 7 <= len(normalized) <= 15:
            raise serializers.ValidationError('Enter a valid contact number.')
        return value.strip()

    def validate_consent(self, value):
        if not value:
            raise serializers.ValidationError('Consent is required so our team can contact you.')
        return value

class CustomerDocumentSerializer(serializers.ModelSerializer):
    class Meta:
        model = CustomerDocument
        fields = ['id', 'document_type', 'file', 'original_name', 'uploaded_at', 'uploaded_by']
        read_only_fields = ['id', 'uploaded_at', 'uploaded_by']

class CustomerSerializer(serializers.ModelSerializer):
    user_email = serializers.EmailField(source='user.email', read_only=True)
    user_full_name = serializers.CharField(source='user.get_full_name', read_only=True)
    documents = CustomerDocumentSerializer(many=True, read_only=True)
    
    class Meta:
        model = Customer
        fields = [
            'id', 'customer_number', 'user', 'user_email', 'user_full_name',
            'date_of_birth', 'license_number', 'license_state', 'license_expiry',
            'credit_score', 'risk_rating', 'notes', 'created_at', 'updated_at',
            'documents'
        ]
        read_only_fields = ['id', 'customer_number', 'created_at', 'updated_at']

class CustomerCreateSerializer(serializers.ModelSerializer):
    user = serializers.HiddenField(default=serializers.CurrentUserDefault())
    
    class Meta:
        model = Customer
        fields = [
            'user', 'date_of_birth', 'license_number', 'license_state',
            'license_expiry', 'credit_score', 'risk_rating', 'notes'
        ]

class CustomerUpdateSerializer(serializers.ModelSerializer):
    class Meta:
        model = Customer
        fields = [
            'date_of_birth', 'license_number', 'license_state', 'license_expiry',
            'credit_score', 'risk_rating', 'notes'
        ]
