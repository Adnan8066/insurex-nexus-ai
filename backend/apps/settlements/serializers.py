from rest_framework import serializers
from .models import Settlement, SettlementTimeline, SettlementPayment, SettlementStatus, PaymentStatus, PaymentMethod

class SettlementTimelineSerializer(serializers.ModelSerializer):
    user_name = serializers.CharField(source='user.get_full_name', read_only=True)
    
    class Meta:
        model = SettlementTimeline
        fields = ['id', 'status', 'title', 'description', 'user', 'user_name', 'timestamp', 'metadata']
        read_only_fields = ['id', 'timestamp', 'user']

class SettlementPaymentSerializer(serializers.ModelSerializer):
    initiated_by_name = serializers.CharField(source='initiated_by.get_full_name', read_only=True)
    processed_by_name = serializers.CharField(source='processed_by.get_full_name', read_only=True)
    
    class Meta:
        model = SettlementPayment
        fields = [
            'id', 'payment_number', 'amount', 'payment_method', 'payment_reference',
            'status', 'initiated_by', 'initiated_by_name', 'processed_by', 'processed_by_name',
            'initiated_at', 'processed_at', 'failure_reason', 'metadata'
        ]
        read_only_fields = ['id', 'payment_number', 'initiated_at', 'initiated_by']

class SettlementSerializer(serializers.ModelSerializer):
    claim_number = serializers.CharField(source='claim.claim_number', read_only=True)
    customer_name = serializers.CharField(source='customer.get_full_name', read_only=True)
    customer_email = serializers.EmailField(source='customer.email', read_only=True)
    approved_by_name = serializers.CharField(source='approved_by.get_full_name', read_only=True)
    paid_by_name = serializers.CharField(source='paid_by.get_full_name', read_only=True)
    timeline = SettlementTimelineSerializer(many=True, read_only=True)
    payments = SettlementPaymentSerializer(many=True, read_only=True)
    
    class Meta:
        model = Settlement
        fields = [
            'id', 'settlement_number', 'claim', 'claim_number', 'customer',
            'customer_name', 'customer_email', 'estimated_amount', 'deductible',
            'approved_amount', 'status', 'payment_status', 'payment_method',
            'payment_reference', 'bank_account', 'approved_by', 'approved_by_name',
            'approved_at', 'paid_by', 'paid_by_name', 'paid_at', 'notes',
            'created_at', 'updated_at', 'timeline', 'payments'
        ]
        read_only_fields = ['id', 'settlement_number', 'created_at', 'updated_at',
                           'approved_by', 'approved_at', 'paid_by', 'paid_at']

class SettlementCreateSerializer(serializers.ModelSerializer):
    class Meta:
        model = Settlement
        fields = [
            'claim', 'estimated_amount', 'deductible', 'approved_amount',
            'payment_method', 'bank_account', 'notes'
        ]

class SettlementUpdateSerializer(serializers.ModelSerializer):
    class Meta:
        model = Settlement
        fields = [
            'estimated_amount', 'deductible', 'approved_amount', 'status',
            'payment_status', 'payment_method', 'payment_reference',
            'bank_account', 'notes'
        ]

class SettlementApproveSerializer(serializers.Serializer):
    approved_amount = serializers.DecimalField(max_digits=12, decimal_places=2)
    notes = serializers.CharField(required=False, allow_blank=True)

class SettlementPaySerializer(serializers.Serializer):
    payment_method = serializers.ChoiceField(choices=PaymentMethod.choices)
    payment_reference = serializers.CharField(required=False, allow_blank=True)
    notes = serializers.CharField(required=False, allow_blank=True)