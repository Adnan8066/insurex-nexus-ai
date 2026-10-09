from django.db import models
from django.conf import settings
from django.utils import timezone
from django.utils.translation import gettext_lazy as _

class PolicyType(models.TextChoices):
    AUTO_COMPREHENSIVE = 'auto_comprehensive', _('Comprehensive Auto')
    AUTO_COLLISION = 'auto_collision', _('Collision Auto')
    AUTO_LIABILITY = 'auto_liability', _('Liability Auto')
    HOMEOWNERS = 'homeowners', _('Homeowners')
    RENTERS = 'renters', _('Renters')
    UMBRELLA = 'umbrella', _('Umbrella')

class PolicyStatus(models.TextChoices):
    ACTIVE = 'active', _('Active')
    EXPIRED = 'expired', _('Expired')
    CANCELLED = 'cancelled', _('Cancelled')
    PENDING = 'pending', _('Pending')
    SUSPENDED = 'suspended', _('Suspended')

class PaymentFrequency(models.TextChoices):
    MONTHLY = 'monthly', _('Monthly')
    QUARTERLY = 'quarterly', _('Quarterly')
    SEMI_ANNUAL = 'semi_annual', _('Semi-Annual')
    ANNUAL = 'annual', _('Annual')

class Policy(models.Model):
    policy_number = models.CharField(_('policy number'), max_length=20, unique=True)
    customer = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name='policies'
    )
    agent = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='managed_policies'
    )
    type = models.CharField(_('type'), max_length=30, choices=PolicyType.choices)
    status = models.CharField(_('status'), max_length=20, choices=PolicyStatus.choices, default=PolicyStatus.PENDING)
    start_date = models.DateField(_('start date'))
    end_date = models.DateField(_('end date'))
    premium = models.DecimalField(_('premium'), max_digits=10, decimal_places=2)
    deductible = models.DecimalField(_('deductible'), max_digits=10, decimal_places=2)
    payment_frequency = models.CharField(
        _('payment frequency'),
        max_length=20,
        choices=PaymentFrequency.choices,
        default=PaymentFrequency.ANNUAL
    )
    auto_renew = models.BooleanField(_('auto renew'), default=True)
    coverage = models.JSONField(_('coverage'), default=dict)
    vehicle = models.ForeignKey(
        'vehicles.Vehicle',
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='policies'
    )
    property_address = models.TextField(_('property address'), blank=True)
    property_type = models.CharField(_('property type'), max_length=50, blank=True)
    property_year_built = models.IntegerField(_('year built'), blank=True, null=True)
    property_square_footage = models.IntegerField(_('square footage'), blank=True, null=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    
    class Meta:
        db_table = 'policies'
        verbose_name = _('policy')
        verbose_name_plural = _('policies')
        indexes = [
            models.Index(fields=['policy_number']),
            models.Index(fields=['customer']),
            models.Index(fields=['status']),
            models.Index(fields=['start_date', 'end_date']),
        ]
    
    def __str__(self):
        return f"{self.policy_number} - {self.get_type_display()}"
    
    @property
    def is_active(self):
        today = timezone.now().date()
        return self.status == PolicyStatus.ACTIVE and self.start_date <= today <= self.end_date
    
    @property
    def days_remaining(self):
        if self.end_date:
            delta = self.end_date - timezone.now().date()
            return max(0, delta.days)
        return 0

class PolicyCoverage(models.Model):
    policy = models.OneToOneField(Policy, on_delete=models.CASCADE, related_name='coverage_details')
    liability = models.DecimalField(_('liability'), max_digits=12, decimal_places=2, default=0)
    collision = models.DecimalField(_('collision'), max_digits=12, decimal_places=2, default=0)
    comprehensive = models.DecimalField(_('comprehensive'), max_digits=12, decimal_places=2, default=0)
    uninsured_motorist = models.DecimalField(_('uninsured motorist'), max_digits=12, decimal_places=2, default=0)
    medical_payments = models.DecimalField(_('medical payments'), max_digits=12, decimal_places=2, default=0)
    personal_injury_protection = models.DecimalField(_('PIP'), max_digits=12, decimal_places=2, default=0)
    roadside_assistance = models.BooleanField(_('roadside assistance'), default=False)
    rental_reimbursement = models.BooleanField(_('rental reimbursement'), default=False)
    glass_coverage = models.BooleanField(_('glass coverage'), default=False)
    dwelling = models.DecimalField(_('dwelling'), max_digits=12, decimal_places=2, default=0)
    personal_property = models.DecimalField(_('personal property'), max_digits=12, decimal_places=2, default=0)
    additional_living_expenses = models.DecimalField(_('additional living expenses'), max_digits=12, decimal_places=2, default=0)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    
    class Meta:
        db_table = 'policy_coverages'
        verbose_name = _('policy coverage')
        verbose_name_plural = _('policy coverages')

class PolicyDocument(models.Model):
    DOCUMENT_TYPES = [
        ('policy', _('Policy Document')),
        ('declaration', _('Declaration Page')),
        ('endorsement', _('Endorsement')),
        ('binder', _('Binder')),
        ('other', _('Other')),
    ]
    
    policy = models.ForeignKey(Policy, on_delete=models.CASCADE, related_name='documents')
    document_type = models.CharField(_('document type'), max_length=20, choices=DOCUMENT_TYPES)
    file = models.FileField(_('file'), upload_to='policy_documents/')
    original_name = models.CharField(_('original name'), max_length=255)
    uploaded_at = models.DateTimeField(auto_now_add=True)
    uploaded_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True,
        related_name='uploaded_policy_documents'
    )
    
    class Meta:
        db_table = 'policy_documents'
        verbose_name = _('policy document')
        verbose_name_plural = _('policy documents')
    
    def __str__(self):
        return f"{self.policy} - {self.get_document_type_display()}"

class PremiumHistory(models.Model):
    policy = models.ForeignKey(Policy, on_delete=models.CASCADE, related_name='premium_history')
    amount = models.DecimalField(_('amount'), max_digits=10, decimal_places=2)
    due_date = models.DateField(_('due date'))
    paid_date = models.DateField(_('paid date'), blank=True, null=True)
    status = models.CharField(_('status'), max_length=20, choices=[
        ('pending', _('Pending')),
        ('paid', _('Paid')),
        ('overdue', _('Overdue')),
        ('cancelled', _('Cancelled')),
    ], default='pending')
    payment_method = models.CharField(_('payment method'), max_length=50, blank=True)
    transaction_id = models.CharField(_('transaction ID'), max_length=100, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)
    
    class Meta:
        db_table = 'premium_history'
        verbose_name = _('premium history')
        verbose_name_plural = _('premium histories')
        ordering = ['-due_date']
    
    def __str__(self):
        return f"{self.policy} - {self.amount} ({self.status})"