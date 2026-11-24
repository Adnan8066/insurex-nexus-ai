from django.db import models
from django.conf import settings
from django.utils.translation import gettext_lazy as _

class InvestigationStatus(models.TextChoices):
    OPEN = 'open', _('Open')
    IN_PROGRESS = 'in_progress', _('In Progress')
    PENDING_REVIEW = 'pending_review', _('Pending Review')
    COMPLETED = 'completed', _('Completed')
    CLOSED = 'closed', _('Closed')
    ON_HOLD = 'on_hold', _('On Hold')

class InvestigationPriority(models.TextChoices):
    LOW = 'low', _('Low')
    MEDIUM = 'medium', _('Medium')
    HIGH = 'high', _('High')
    CRITICAL = 'critical', _('Critical')

class EvidenceType(models.TextChoices):
    DOCUMENT = 'document', _('Document')
    PHOTO = 'photo', _('Photo')
    VIDEO = 'video', _('Video')
    AUDIO = 'audio', _('Audio')
    STATEMENT = 'statement', _('Statement')
    SURVEILLANCE = 'surveillance', _('Surveillance')
    DIGITAL = 'digital', _('Digital Forensics')
    FINANCIAL = 'financial', _('Financial Record')
    MEDICAL = 'medical', _('Medical Record')
    OTHER = 'other', _('Other')

class InvestigationOutcome(models.TextChoices):
    # Set only by the investigator when the case is completed. A triage flag is never an outcome.
    PENDING = 'pending', _('Pending')
    CLEARED = 'cleared', _('Cleared (claim is genuine)')
    CONFIRMED_FRAUD = 'confirmed_fraud', _('Confirmed fraud')
    INCONCLUSIVE = 'inconclusive', _('Inconclusive')

# Matches the claim-level fraud_outcome values used by claims.Claim.
OUTCOME_TO_CLAIM_FRAUD_OUTCOME = {
    InvestigationOutcome.CONFIRMED_FRAUD: 'fraud',
    InvestigationOutcome.CLEARED: 'genuine',
    InvestigationOutcome.INCONCLUSIVE: 'unclear',
}

class VehicleCheckCode(models.TextChoices):
    VIN_MATCHES = 'vin_matches', _('VIN on the claim matches the vehicle and its chassis plate')
    PLATE_MATCHES = 'plate_matches', _('Number plate matches the registration record')
    OWNER_MATCHES = 'owner_matches', _('Registered owner matches the policyholder')
    ODOMETER_CONSISTENT = 'odometer_consistent', _("Odometer reading fits the vehicle's age and service history")
    DAMAGE_MATCHES_INCIDENT = 'damage_matches_incident', _('Visible damage matches the reported incident')
    NO_PRIOR_DAMAGE = 'no_prior_damage', _('No unrepaired earlier damage found')
    VEHICLE_INSPECTED = 'vehicle_inspected', _('Vehicle physically inspected, with date and location recorded')
    PHOTOS_TAKEN = 'photos_taken', _('Vehicle photographed and photos attached as evidence')
    AMOUNT_WITHIN_VALUE = 'amount_within_value', _("Claimed amount is within the vehicle's value")
    ESTIMATE_REASONABLE = 'estimate_reasonable', _('Repair estimate checked against a garage or market rate')

class VehicleCheckResult(models.TextChoices):
    PASS = 'pass', _('Pass')
    FAIL = 'fail', _('Fail')
    NOT_APPLICABLE = 'na', _('Not applicable')

class Investigation(models.Model):
    claim = models.OneToOneField(
        'claims.Claim',
        on_delete=models.CASCADE,
        related_name='investigation'
    )
    investigator = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='investigations'
    )
    status = models.CharField(
        _('status'),
        max_length=20,
        choices=InvestigationStatus.choices,
        default=InvestigationStatus.OPEN
    )
    priority = models.CharField(
        _('priority'),
        max_length=20,
        choices=InvestigationPriority.choices,
        default=InvestigationPriority.MEDIUM
    )
    fraud_alert = models.ForeignKey(
        'investigations.FraudAlert',
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='investigations'
    )
    case_number = models.CharField(_('case number'), max_length=20, unique=True)
    summary = models.TextField(_('summary'), blank=True)
    findings = models.TextField(_('findings'), blank=True)
    conclusion = models.TextField(_('conclusion'), blank=True)
    recommendation = models.TextField(_('recommendation'), blank=True)
    investigation_outcome = models.CharField(
        _('investigation outcome'), max_length=20,
        choices=InvestigationOutcome.choices, default=InvestigationOutcome.PENDING,
    )
    outcome_notes = models.TextField(_('outcome notes'), blank=True, max_length=1000)
    outcome_reviewed_at = models.DateTimeField(_('outcome recorded at'), blank=True, null=True)
    opened_at = models.DateTimeField(auto_now_add=True)
    started_at = models.DateTimeField(_('started at'), blank=True, null=True)
    completed_at = models.DateTimeField(_('completed at'), blank=True, null=True)
    closed_at = models.DateTimeField(_('closed at'), blank=True, null=True)
    estimated_completion = models.DateField(_('estimated completion'), blank=True, null=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    
    class Meta:
        db_table = 'investigations'
        verbose_name = _('investigation')
        verbose_name_plural = _('investigations')
        indexes = [
            models.Index(fields=['claim']),
            models.Index(fields=['investigator']),
            models.Index(fields=['status']),
            models.Index(fields=['case_number']),
        ]
        ordering = ['-opened_at']
    
    def __str__(self):
        return f"Investigation {self.case_number} - {self.claim}"

class InvestigationEvidence(models.Model):
    investigation = models.ForeignKey(Investigation, on_delete=models.CASCADE, related_name='evidence')
    evidence_type = models.CharField(_('evidence type'), max_length=20, choices=EvidenceType.choices)
    title = models.CharField(_('title'), max_length=200)
    description = models.TextField(_('description'), blank=True)
    file = models.FileField(_('file'), upload_to='investigation_evidence/', blank=True, null=True)
    source = models.CharField(_('source'), max_length=200, blank=True)
    collected_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True,
        related_name='collected_evidence'
    )
    collected_at = models.DateTimeField(auto_now_add=True)
    is_key_evidence = models.BooleanField(_('key evidence'), default=False)
    verified = models.BooleanField(_('verified'), default=False)
    verified_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='verified_evidence'
    )
    verified_at = models.DateTimeField(_('verified at'), blank=True, null=True)
    metadata = models.JSONField(_('metadata'), default=dict, blank=True)
    
    class Meta:
        db_table = 'investigation_evidence'
        verbose_name = _('investigation evidence')
        verbose_name_plural = _('investigation evidence')
        ordering = ['-collected_at']
    
    def __str__(self):
        return f"{self.investigation} - {self.title}"

class InvestigationNote(models.Model):
    investigation = models.ForeignKey(Investigation, on_delete=models.CASCADE, related_name='notes')
    author = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name='investigation_notes'
    )
    content = models.TextField(_('content'))
    is_interview = models.BooleanField(_('interview note'), default=False)
    interviewee = models.CharField(_('interviewee'), max_length=200, blank=True)
    interview_date = models.DateTimeField(_('interview date'), blank=True, null=True)
    is_confidential = models.BooleanField(_('confidential'), default=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    
    class Meta:
        db_table = 'investigation_notes'
        verbose_name = _('investigation note')
        verbose_name_plural = _('investigation notes')
        ordering = ['-created_at']
    
    def __str__(self):
        return f"Note on {self.investigation} by {self.author}"

class InvestigationVehicleCheck(models.Model):
    investigation = models.ForeignKey(Investigation, on_delete=models.CASCADE, related_name='vehicle_checks')
    check_code = models.CharField(_('check'), max_length=40, choices=VehicleCheckCode.choices)
    result = models.CharField(_('result'), max_length=10, choices=VehicleCheckResult.choices)
    note = models.TextField(_('note'), blank=True)
    checked_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='vehicle_checks_done'
    )
    checked_at = models.DateTimeField(_('checked at'), auto_now=True)

    class Meta:
        db_table = 'investigation_vehicle_checks'
        verbose_name = _('investigation vehicle check')
        verbose_name_plural = _('investigation vehicle checks')
        constraints = [
            models.UniqueConstraint(fields=['investigation', 'check_code'], name='unique_vehicle_check_per_case'),
        ]

    def __str__(self):
        return f"{self.investigation} - {self.check_code}: {self.result}"

FRAUD_ALERT_STATUS_CHOICES = [
    ('new', _('New')),
    ('investigation', _('Investigation')),
    ('reviewed', _('Reviewed')),
    ('dismissed', _('Dismissed')),
    ('escalated', _('Escalated')),
]


class FraudAlert(models.Model):
    RISK_LEVELS = [
        ('low', _('Low')),
        ('medium', _('Medium')),
        ('high', _('High')),
    ]
    
    claim = models.OneToOneField(
        'claims.Claim',
        on_delete=models.CASCADE,
        related_name='fraud_alert'
    )
    risk_score = models.DecimalField(_('risk score'), max_digits=5, decimal_places=2)
    risk_level = models.CharField(_('risk level'), max_length=10, choices=RISK_LEVELS)
    risk_factors = models.JSONField(_('risk factors'), default=list)
    behavioral_indicators = models.JSONField(_('behavioral indicators'), default=list, blank=True)
    network_analysis = models.JSONField(_('network analysis'), default=dict, blank=True)
    ai_recommendation = models.TextField(_('AI recommendation'))
    assigned_investigator = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='assigned_fraud_alerts'
    )
    status = models.CharField(_('status'), max_length=20, choices=FRAUD_ALERT_STATUS_CHOICES, default='new')
    investigator_notes = models.TextField(_('investigator notes'), blank=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    reviewed_at = models.DateTimeField(_('reviewed at'), blank=True, null=True)
    reviewed_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='reviewed_fraud_alerts'
    )
    
    class Meta:
        db_table = 'fraud_alerts'
        verbose_name = _('fraud alert')
        verbose_name_plural = _('fraud alerts')
        indexes = [
            models.Index(fields=['risk_level']),
            models.Index(fields=['status']),
            models.Index(fields=['assigned_investigator']),
        ]
        ordering = ['-created_at']
    
    def __str__(self):
        return f"Fraud Alert for {self.claim} ({self.risk_level})"
