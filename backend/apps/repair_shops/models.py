from django.db import models
from django.conf import settings
from django.utils.translation import gettext_lazy as _

class RepairShopStatus(models.TextChoices):
    PENDING_REVIEW = 'pending_review', _('Pending Review')
    APPROVED = 'approved', _('Approved')
    SUSPENDED = 'suspended', _('Suspended')
    REJECTED = 'rejected', _('Rejected')
    INACTIVE = 'inactive', _('Inactive')

class RepairShop(models.Model):
    name = models.CharField(_('name'), max_length=200)
    email = models.EmailField(_('email'))
    phone = models.CharField(_('phone'), max_length=20)
    address = models.TextField(_('address'))
    city = models.CharField(_('city'), max_length=100)
    state = models.CharField(_('state'), max_length=2)
    zip_code = models.CharField(_('ZIP code'), max_length=10)
    license_number = models.CharField(_('license number'), max_length=50, unique=True)
    status = models.CharField(
        _('status'),
        max_length=20,
        choices=RepairShopStatus.choices,
        default=RepairShopStatus.PENDING_REVIEW
    )
    rating = models.DecimalField(_('rating'), max_digits=3, decimal_places=1, default=0.0)
    specialties = models.JSONField(_('specialties'), default=list, blank=True)
    certifications = models.JSONField(_('certifications'), default=list, blank=True)
    capacity = models.PositiveIntegerField(_('capacity (bays)'), default=0)
    current_jobs = models.PositiveIntegerField(_('current jobs'), default=0)
    average_turnaround_days = models.PositiveIntegerField(_('average turnaround (days)'), default=0)
    oem_certifications = models.JSONField(_('OEM certifications'), default=list, blank=True)
    operating_hours = models.JSONField(_('operating hours'), default=dict, blank=True)
    contact_person = models.CharField(_('contact person'), max_length=100, blank=True)
    notes = models.TextField(_('notes'), blank=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    approved_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='approved_shops'
    )
    approved_at = models.DateTimeField(_('approved at'), blank=True, null=True)
    
    class Meta:
        db_table = 'repair_shops'
        verbose_name = _('repair shop')
        verbose_name_plural = _('repair shops')
        indexes = [
            models.Index(fields=['license_number']),
            models.Index(fields=['status']),
            models.Index(fields=['city', 'state']),
        ]
    
    def __str__(self):
        return f"{self.name} ({self.license_number})"

class RepairJob(models.Model):
    JOB_STATUS_CHOICES = [
        ('scheduled', _('Scheduled')),
        ('parts_ordered', _('Parts Ordered')),
        ('in_progress', _('In Progress')),
        ('painting', _('Painting & Refinishing')),
        ('quality_inspection', _('Quality Inspection')),
        ('completed', _('Completed')),
        ('delivered', _('Delivered')),
        ('on_hold', _('On Hold')),
        ('cancelled', _('Cancelled')),
    ]
    
    PRIORITY_CHOICES = [
        ('low', _('Low')),
        ('medium', _('Medium')),
        ('high', _('High')),
        ('critical', _('Critical')),
    ]
    
    job_number = models.CharField(_('job number'), max_length=20, unique=True)
    claim = models.OneToOneField(
        'claims.Claim',
        on_delete=models.CASCADE,
        related_name='repair_job'
    )
    repair_shop = models.ForeignKey(
        RepairShop,
        on_delete=models.CASCADE,
        related_name='jobs'
    )
    status = models.CharField(
        _('status'),
        max_length=20,
        choices=JOB_STATUS_CHOICES,
        default='scheduled'
    )
    priority = models.CharField(
        _('priority'),
        max_length=10,
        choices=PRIORITY_CHOICES,
        default='medium'
    )
    repair_stage = models.CharField(_('repair stage'), max_length=100, blank=True)
    estimated_cost = models.DecimalField(_('estimated cost'), max_digits=12, decimal_places=2)
    actual_cost = models.DecimalField(_('actual cost'), max_digits=12, decimal_places=2, blank=True, null=True)
    assigned_bay = models.CharField(_('assigned bay'), max_length=20, blank=True)
    started_at = models.DateField(_('started at'), blank=True, null=True)
    estimated_completion = models.DateField(_('estimated completion'), blank=True, null=True)
    actual_completion = models.DateField(_('actual completion'), blank=True, null=True)
    parts = models.JSONField(_('parts'), default=list, blank=True)
    labor_hours = models.DecimalField(_('labor hours'), max_digits=6, decimal_places=2, blank=True, null=True)
    quality_score = models.DecimalField(_('quality score'), max_digits=3, decimal_places=1, blank=True, null=True)
    customer_satisfaction = models.PositiveIntegerField(_('customer satisfaction (1-5)'), blank=True, null=True)
    notes = models.TextField(_('notes'), blank=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    
    class Meta:
        db_table = 'repair_jobs'
        verbose_name = _('repair job')
        verbose_name_plural = _('repair jobs')
        indexes = [
            models.Index(fields=['job_number']),
            models.Index(fields=['claim']),
            models.Index(fields=['repair_shop']),
            models.Index(fields=['status']),
        ]
    
    def __str__(self):
        return f"Job {self.job_number} - {self.claim}"

class RepairEstimate(models.Model):
    STATUS_CHOICES = [
        ('draft', _('Draft')),
        ('submitted', _('Submitted')),
        ('under_review', _('Under Review')),
        ('approved', _('Approved')),
        ('rejected', _('Rejected')),
        ('revised', _('Revised')),
    ]
    
    repair_job = models.ForeignKey(RepairJob, on_delete=models.CASCADE, related_name='estimates')
    estimate_number = models.CharField(_('estimate number'), max_length=20, unique=True)
    status = models.CharField(_('status'), max_length=20, choices=STATUS_CHOICES, default='draft')
    parts_total = models.DecimalField(_('parts total'), max_digits=12, decimal_places=2, default=0)
    labor_total = models.DecimalField(_('labor total'), max_digits=12, decimal_places=2, default=0)
    paint_total = models.DecimalField(_('paint total'), max_digits=12, decimal_places=2, default=0)
    other_total = models.DecimalField(_('other total'), max_digits=12, decimal_places=2, default=0)
    subtotal = models.DecimalField(_('subtotal'), max_digits=12, decimal_places=2, default=0)
    tax = models.DecimalField(_('tax'), max_digits=12, decimal_places=2, default=0)
    total = models.DecimalField(_('total'), max_digits=12, decimal_places=2, default=0)
    parts = models.JSONField(_('parts detail'), default=list)
    labor_items = models.JSONField(_('labor items'), default=list)
    submitted_at = models.DateTimeField(_('submitted at'), blank=True, null=True)
    reviewed_at = models.DateTimeField(_('reviewed at'), blank=True, null=True)
    reviewed_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='reviewed_estimates'
    )
    approved_at = models.DateTimeField(_('approved at'), blank=True, null=True)
    approved_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='approved_estimates'
    )
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    
    class Meta:
        db_table = 'repair_estimates'
        verbose_name = _('repair estimate')
        verbose_name_plural = _('repair estimates')
        ordering = ['-created_at']
    
    def __str__(self):
        return f"Estimate {self.estimate_number} for {self.repair_job}"

class RepairShopDocument(models.Model):
    DOCUMENT_TYPES = [
        ('license', _('Business License')),
        ('insurance', _('Insurance Certificate')),
        ('certification', _('Certification')),
        ('oem_cert', _('OEM Certification')),
        ('other', _('Other')),
    ]
    
    repair_shop = models.ForeignKey(RepairShop, on_delete=models.CASCADE, related_name='documents')
    document_type = models.CharField(_('document type'), max_length=20, choices=DOCUMENT_TYPES)
    file = models.FileField(_('file'), upload_to='repair_shop_documents/')
    original_name = models.CharField(_('original name'), max_length=255)
    expiry_date = models.DateField(_('expiry date'), blank=True, null=True)
    uploaded_at = models.DateTimeField(auto_now_add=True)
    uploaded_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True,
        related_name='uploaded_shop_documents'
    )
    
    class Meta:
        db_table = 'repair_shop_documents'
        verbose_name = _('repair shop document')
        verbose_name_plural = _('repair shop documents')
    
    def __str__(self):
        return f"{self.repair_shop} - {self.get_document_type_display()}"