from django.db import models
from django.conf import settings
from django.utils.translation import gettext_lazy as _

class NotificationType(models.TextChoices):
    CLAIM = 'claim', _('Claim Update')
    POLICY = 'policy', _('Policy Update')
    PAYMENT = 'payment', _('Payment')
    DOCUMENT = 'document', _('Document Required')
    AI_ASSESSMENT = 'ai_assessment', _('AI Assessment')
    FRAUD_ALERT = 'fraud_alert', _('Fraud Alert')
    SETTLEMENT = 'settlement', _('Settlement')
    SYSTEM = 'system', _('System')
    REMINDER = 'reminder', _('Reminder')

class NotificationPriority(models.TextChoices):
    LOW = 'low', _('Low')
    NORMAL = 'normal', _('Normal')
    HIGH = 'high', _('High')
    URGENT = 'urgent', _('Urgent')

class Notification(models.Model):
    recipient = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name='notifications'
    )
    notification_type = models.CharField(
        _('type'),
        max_length=20,
        choices=NotificationType.choices
    )
    priority = models.CharField(
        _('priority'),
        max_length=10,
        choices=NotificationPriority.choices,
        default=NotificationPriority.NORMAL
    )
    title = models.CharField(_('title'), max_length=200)
    message = models.TextField(_('message'))
    link = models.CharField(_('link'), max_length=500, blank=True)
    related_object_type = models.CharField(_('related object type'), max_length=50, blank=True)
    related_object_id = models.CharField(_('related object ID'), max_length=50, blank=True)
    is_read = models.BooleanField(_('read'), default=False)
    read_at = models.DateTimeField(_('read at'), blank=True, null=True)
    sent_at = models.DateTimeField(auto_now_add=True)
    expires_at = models.DateTimeField(_('expires at'), blank=True, null=True)
    metadata = models.JSONField(_('metadata'), default=dict, blank=True)
    
    class Meta:
        db_table = 'notifications'
        verbose_name = _('notification')
        verbose_name_plural = _('notifications')
        indexes = [
            models.Index(fields=['recipient', 'is_read']),
            models.Index(fields=['notification_type']),
            models.Index(fields=['sent_at']),
        ]
        ordering = ['-sent_at']
    
    def __str__(self):
        return f"{self.recipient} - {self.title}"

class NotificationPreference(models.Model):
    user = models.OneToOneField(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name='notification_preferences'
    )
    email_claim_updates = models.BooleanField(_('email claim updates'), default=True)
    email_policy_updates = models.BooleanField(_('email policy updates'), default=True)
    email_payment_updates = models.BooleanField(_('email payment updates'), default=True)
    email_document_requests = models.BooleanField(_('email document requests'), default=True)
    email_ai_assessments = models.BooleanField(_('email AI assessments'), default=True)
    email_fraud_alerts = models.BooleanField(_('email fraud alerts'), default=True)
    email_settlements = models.BooleanField(_('email settlements'), default=True)
    email_marketing = models.BooleanField(_('email marketing'), default=False)
    push_claim_updates = models.BooleanField(_('push claim updates'), default=True)
    push_policy_updates = models.BooleanField(_('push policy updates'), default=True)
    push_payment_updates = models.BooleanField(_('push payment updates'), default=True)
    push_document_requests = models.BooleanField(_('push document requests'), default=True)
    push_ai_assessments = models.BooleanField(_('push AI assessments'), default=True)
    push_fraud_alerts = models.BooleanField(_('push fraud alerts'), default=True)
    push_settlements = models.BooleanField(_('push settlements'), default=True)
    sms_urgent_only = models.BooleanField(_('SMS urgent only'), default=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    
    class Meta:
        db_table = 'notification_preferences'
        verbose_name = _('notification preference')
        verbose_name_plural = _('notification preferences')
    
    def __str__(self):
        return f"Preferences for {self.user}"