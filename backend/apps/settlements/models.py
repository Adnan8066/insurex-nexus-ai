from django.db import models
from django.conf import settings
from django.utils.translation import gettext_lazy as _

class SettlementStatus(models.TextChoices):
    CALCULATED = 'calculated', _('Calculated')
    UNDER_REVIEW = 'under_review', _('Under Review')
    APPROVED = 'approved', _('Approved')
    REJECTED = 'rejected', _('Rejected')
    PAID = 'paid', _('Paid')

class PaymentStatus(models.TextChoices):
    PENDING = 'pending', _('Pending')
    PROCESSING = 'processing', _('Processing')
    COMPLETED = 'completed', _('Completed')
    FAILED = 'failed', _('Failed')
    REFUNDED = 'refunded', _('Refunded')

class PaymentMethod(models.TextChoices):
    BANK_TRANSFER = 'bank_transfer', _('Bank Transfer (ACH)')
    WIRE = 'wire', _('Wire Transfer')
    CHECK = 'check', _('Check')
    DIGITAL_WALLET = 'digital_wallet', _('Digital Wallet')
    CARD = 'card', _('Card')

class Settlement(models.Model):
    settlement_number = models.CharField(_('settlement number'), max_length=20, unique=True)
    claim = models.OneToOneField(
        'claims.Claim',
        on_delete=models.CASCADE,
        related_name='settlement'
    )
    customer = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name='settlements'
    )
    estimated_amount = models.DecimalField(_('estimated amount'), max_digits=12, decimal_places=2)
    deductible = models.DecimalField(_('deductible'), max_digits=12, decimal_places=2)
    approved_amount = models.DecimalField(_('approved amount'), max_digits=12, decimal_places=2)
    status = models.CharField(
        _('status'),
        max_length=20,
        choices=SettlementStatus.choices,
        default=SettlementStatus.CALCULATED
    )
    payment_status = models.CharField(
        _('payment status'),
        max_length=20,
        choices=PaymentStatus.choices,
        default=PaymentStatus.PENDING
    )
    payment_method = models.CharField(
        _('payment method'),
        max_length=20,
        choices=PaymentMethod.choices,
        default=PaymentMethod.BANK_TRANSFER
    )
    payment_reference = models.CharField(_('payment reference'), max_length=100, blank=True)
    bank_account = models.JSONField(_('bank account details'), default=dict, blank=True)
    approved_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='approved_settlements'
    )
    approved_at = models.DateTimeField(_('approved at'), blank=True, null=True)
    paid_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='paid_settlements'
    )
    paid_at = models.DateTimeField(_('paid at'), blank=True, null=True)
    notes = models.TextField(_('notes'), blank=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    
    class Meta:
        db_table = 'settlements'
        verbose_name = _('settlement')
        verbose_name_plural = _('settlements')
        indexes = [
            models.Index(fields=['settlement_number']),
            models.Index(fields=['claim']),
            models.Index(fields=['customer']),
            models.Index(fields=['status']),
            models.Index(fields=['payment_status']),
        ]
        ordering = ['-created_at']
    
    def __str__(self):
        return f"Settlement {self.settlement_number} for {self.claim}"

class SettlementTimeline(models.Model):
    settlement = models.ForeignKey(Settlement, on_delete=models.CASCADE, related_name='timeline')
    status = models.CharField(_('status'), max_length=20, choices=SettlementStatus.choices)
    title = models.CharField(_('title'), max_length=200)
    description = models.TextField(_('description'), blank=True)
    user = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='settlement_timeline_entries'
    )
    timestamp = models.DateTimeField(auto_now_add=True)
    metadata = models.JSONField(_('metadata'), default=dict, blank=True)
    
    class Meta:
        db_table = 'settlement_timelines'
        verbose_name = _('settlement timeline')
        verbose_name_plural = _('settlement timelines')
        ordering = ['timestamp']
    
    def __str__(self):
        return f"{self.settlement} - {self.title}"

class SettlementPayment(models.Model):
    settlement = models.ForeignKey(Settlement, on_delete=models.CASCADE, related_name='payments')
    payment_number = models.CharField(_('payment number'), max_length=20, unique=True)
    amount = models.DecimalField(_('amount'), max_digits=12, decimal_places=2)
    payment_method = models.CharField(_('payment method'), max_length=20, choices=PaymentMethod.choices)
    payment_reference = models.CharField(_('payment reference'), max_length=100, blank=True)
    status = models.CharField(
        _('status'),
        max_length=20,
        choices=PaymentStatus.choices,
        default=PaymentStatus.PENDING
    )
    initiated_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True,
        related_name='initiated_payments'
    )
    processed_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='processed_payments'
    )
    initiated_at = models.DateTimeField(auto_now_add=True)
    processed_at = models.DateTimeField(_('processed at'), blank=True, null=True)
    failure_reason = models.TextField(_('failure reason'), blank=True)
    metadata = models.JSONField(_('metadata'), default=dict, blank=True)
    
    class Meta:
        db_table = 'settlement_payments'
        verbose_name = _('settlement payment')
        verbose_name_plural = _('settlement payments')
        ordering = ['-initiated_at']
    
    def __str__(self):
        return f"Payment {self.payment_number} for {self.settlement}"