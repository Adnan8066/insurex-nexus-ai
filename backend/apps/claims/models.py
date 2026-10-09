from django.db import models
from django.conf import settings
from django.utils import timezone
from django.utils.translation import gettext_lazy as _

class IncidentType(models.TextChoices):
    COLLISION = 'collision', _('Collision')
    COMPREHENSIVE = 'comprehensive', _('Comprehensive')
    THEFT = 'theft', _('Theft')
    VANDALISM = 'vandalism', _('Vandalism')
    FIRE = 'fire', _('Fire')
    WATER_DAMAGE = 'water_damage', _('Water Damage')
    HAIL = 'hail', _('Hail')
    ANIMAL = 'animal', _('Animal Strike')
    GLASS = 'glass', _('Glass Breakage')
    OTHER = 'other', _('Other')

class IncidentSeverity(models.TextChoices):
    MINOR = 'minor', _('Minor')
    MODERATE = 'moderate', _('Moderate')
    MAJOR = 'major', _('Major')
    TOTAL_LOSS = 'total_loss', _('Total Loss')

class ClaimStatus(models.TextChoices):
    SUBMITTED = 'submitted', _('Submitted')
    UNDER_REVIEW = 'under_review', _('Under Review')
    AI_ASSESSMENT = 'ai_assessment', _('AI Assessment')
    INVESTIGATION = 'investigation', _('Investigation')
    APPROVED = 'approved', _('Approved')
    REJECTED = 'rejected', _('Rejected')
    REPAIR_SETTLEMENT = 'repair_settlement', _('Repair/Settlement')
    CLOSED = 'closed', _('Closed')

class ClaimPriority(models.TextChoices):
    LOW = 'low', _('Low')
    MEDIUM = 'medium', _('Medium')
    HIGH = 'high', _('High')
    CRITICAL = 'critical', _('Critical')

class Claim(models.Model):
    claim_number = models.CharField(_('claim number'), max_length=20, unique=True)
    customer = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name='claims'
    )
    policy = models.ForeignKey(
        'policies.Policy',
        on_delete=models.CASCADE,
        related_name='claims'
    )
    vehicle = models.ForeignKey(
        'vehicles.Vehicle',
        on_delete=models.CASCADE,
        related_name='claims'
    )
    incident_date = models.DateField(_('incident date'))
    incident_time = models.TimeField(_('incident time'), blank=True, null=True)
    incident_type = models.CharField(_('incident type'), max_length=20, choices=IncidentType.choices)
    incident_severity = models.CharField(_('incident severity'), max_length=20, choices=IncidentSeverity.choices)
    location = models.TextField(_('location'))
    latitude = models.DecimalField(_('latitude'), max_digits=9, decimal_places=6, blank=True, null=True)
    longitude = models.DecimalField(_('longitude'), max_digits=9, decimal_places=6, blank=True, null=True)
    number_of_vehicles = models.PositiveIntegerField(_('number of vehicles'), default=1)
    injuries = models.BooleanField(_('injuries'), default=False)
    injury_details = models.TextField(_('injury details'), blank=True)
    property_damage = models.BooleanField(_('property damage'), default=False)
    property_damage_details = models.TextField(_('property damage details'), blank=True)
    witnesses = models.BooleanField(_('witnesses'), default=False)
    witness_details = models.TextField(_('witness details'), blank=True)
    police_report = models.BooleanField(_('police report'), default=False)
    police_report_number = models.CharField(_('police report number'), max_length=50, blank=True)
    claim_amount = models.DecimalField(_('claim amount'), max_digits=12, decimal_places=2)
    description = models.TextField(_('description'), blank=True)
    status = models.CharField(_('status'), max_length=20, choices=ClaimStatus.choices, default=ClaimStatus.SUBMITTED)
    priority = models.CharField(_('priority'), max_length=20, choices=ClaimPriority.choices, default=ClaimPriority.MEDIUM)
    assigned_adjuster = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='assigned_claims'
    )
    assigned_investigator = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='investigated_claims'
    )
    assigned_repair_shop = models.ForeignKey(
        'repair_shops.RepairShop',
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='assigned_claims'
    )
    ai_assessment = models.JSONField(_('AI assessment'), default=dict, blank=True)
    fraud_risk_score = models.DecimalField(_('fraud risk score'), max_digits=5, decimal_places=2, default=0)
    total_loss_probability = models.DecimalField(_('total loss probability'), max_digits=5, decimal_places=2, default=0)
    submitted_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    closed_at = models.DateTimeField(_('closed at'), blank=True, null=True)
    
    class Meta:
        db_table = 'claims'
        verbose_name = _('claim')
        verbose_name_plural = _('claims')
        indexes = [
            models.Index(fields=['claim_number']),
            models.Index(fields=['customer']),
            models.Index(fields=['policy']),
            models.Index(fields=['vehicle']),
            models.Index(fields=['status']),
            models.Index(fields=['incident_date']),
            models.Index(fields=['assigned_adjuster']),
            models.Index(fields=['assigned_investigator']),
        ]
        ordering = ['-submitted_at']
    
    def __str__(self):
        return f"{self.claim_number} - {self.customer.get_full_name() or self.customer.email}"

class ClaimDocument(models.Model):
    DOCUMENT_TYPES = [
        ('police_report', _('Police Report')),
        ('photos', _('Photos')),
        ('medical', _('Medical Records')),
        ('estimate', _('Repair Estimate')),
        ('invoice', _('Invoice')),
        ('receipt', _('Receipt')),
        ('total_loss', _('Total Loss Report')),
        ('settlement', _('Settlement Agreement')),
        ('weather', _('Weather Report')),
        ('correspondence', _('Correspondence')),
        ('other', _('Other')),
    ]
    
    claim = models.ForeignKey(Claim, on_delete=models.CASCADE, related_name='documents')
    document_type = models.CharField(_('document type'), max_length=20, choices=DOCUMENT_TYPES)
    file = models.FileField(_('file'), upload_to='claim_documents/')
    original_name = models.CharField(_('original name'), max_length=255)
    description = models.TextField(_('description'), blank=True)
    uploaded_at = models.DateTimeField(auto_now_add=True)
    uploaded_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True,
        related_name='uploaded_claim_documents'
    )
    verified = models.BooleanField(_('verified'), default=False)
    verified_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='verified_claim_documents'
    )
    verified_at = models.DateTimeField(_('verified at'), blank=True, null=True)
    
    class Meta:
        db_table = 'claim_documents'
        verbose_name = _('claim document')
        verbose_name_plural = _('claim documents')
        ordering = ['-uploaded_at']
    
    def __str__(self):
        return f"{self.claim} - {self.get_document_type_display()}"

class ClaimStatusHistory(models.Model):
    claim = models.ForeignKey(Claim, on_delete=models.CASCADE, related_name='status_history')
    from_status = models.CharField(_('from status'), max_length=20, choices=ClaimStatus.choices, blank=True)
    to_status = models.CharField(_('to status'), max_length=20, choices=ClaimStatus.choices)
    reason = models.TextField(_('reason'), blank=True)
    changed_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True,
        related_name='status_changes'
    )
    changed_at = models.DateTimeField(auto_now_add=True)
    metadata = models.JSONField(_('metadata'), default=dict, blank=True)
    
    class Meta:
        db_table = 'claim_status_histories'
        verbose_name = _('claim status history')
        verbose_name_plural = _('claim status histories')
        ordering = ['-changed_at']
    
    def __str__(self):
        return f"{self.claim} - {self.from_status} → {self.to_status}"

class ClaimTimeline(models.Model):
    claim = models.ForeignKey(Claim, on_delete=models.CASCADE, related_name='timeline')
    status = models.CharField(_('status'), max_length=20, choices=ClaimStatus.choices)
    title = models.CharField(_('title'), max_length=200)
    description = models.TextField(_('description'))
    user = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='timeline_entries'
    )
    timestamp = models.DateTimeField(auto_now_add=True)
    is_system = models.BooleanField(_('system generated'), default=False)
    metadata = models.JSONField(_('metadata'), default=dict, blank=True)
    
    class Meta:
        db_table = 'claim_timelines'
        verbose_name = _('claim timeline')
        verbose_name_plural = _('claim timelines')
        ordering = ['timestamp']
    
    def __str__(self):
        return f"{self.claim} - {self.title}"

class ClaimNote(models.Model):
    claim = models.ForeignKey(Claim, on_delete=models.CASCADE, related_name='notes')
    author = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name='claim_notes'
    )
    content = models.TextField(_('content'))
    is_internal = models.BooleanField(_('internal note'), default=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    
    class Meta:
        db_table = 'claim_notes'
        verbose_name = _('claim note')
        verbose_name_plural = _('claim notes')
        ordering = ['-created_at']
    
    def __str__(self):
        return f"Note on {self.claim} by {self.author}"