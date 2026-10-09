from rest_framework import serializers
from .models import Notification, NotificationPreference

class NotificationSerializer(serializers.ModelSerializer):
    class Meta:
        model = Notification
        fields = [
            'id', 'notification_type', 'priority', 'title', 'message', 'link',
            'related_object_type', 'related_object_id', 'is_read', 'read_at',
            'sent_at', 'expires_at', 'metadata'
        ]
        read_only_fields = ['id', 'sent_at', 'read_at']

class NotificationPreferenceSerializer(serializers.ModelSerializer):
    class Meta:
        model = NotificationPreference
        fields = [
            'email_claim_updates', 'email_policy_updates', 'email_payment_updates',
            'email_document_requests', 'email_ai_assessments', 'email_fraud_alerts',
            'email_settlements', 'email_marketing', 'push_claim_updates',
            'push_policy_updates', 'push_payment_updates', 'push_document_requests',
            'push_ai_assessments', 'push_fraud_alerts', 'push_settlements',
            'sms_urgent_only'
        ]