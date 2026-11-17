from rest_framework import serializers

from .models import AuditEvent


class AuditEventSerializer(serializers.ModelSerializer):
    actor_email = serializers.EmailField(source='actor.email', read_only=True, default=None)

    class Meta:
        model = AuditEvent
        fields = ['id', 'entity_type', 'entity_id', 'entity_label', 'action', 'actor', 'actor_email', 'changes', 'timestamp']
        read_only_fields = fields
