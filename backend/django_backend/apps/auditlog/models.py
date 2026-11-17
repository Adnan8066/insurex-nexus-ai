from django.conf import settings
from django.db import models


class AuditEvent(models.Model):
    """Append-only record of operational changes to core insurance records."""

    entity_type = models.CharField(max_length=40, db_index=True)
    entity_id = models.CharField(max_length=64, db_index=True)
    entity_label = models.CharField(max_length=120, blank=True)
    action = models.CharField(max_length=12, choices=[('created', 'Created'), ('updated', 'Updated')])
    actor = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='audit_events',
    )
    changes = models.JSONField(default=dict)
    timestamp = models.DateTimeField(auto_now_add=True, db_index=True)

    class Meta:
        ordering = ['-timestamp', '-id']
        indexes = [models.Index(fields=['entity_type', 'entity_id', '-timestamp'])]

    def __str__(self):
        return f'{self.entity_type} {self.entity_id}: {self.action}'
