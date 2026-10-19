from django.db import models
from django.conf import settings
from django.utils import timezone
from django.utils.translation import gettext_lazy as _

class Customer(models.Model):
    user = models.OneToOneField(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name='customer_profile'
    )
    customer_number = models.CharField(_('customer number'), max_length=20, unique=True)
    date_of_birth = models.DateField(_('date of birth'), blank=True, null=True)
    license_number = models.CharField(_('license number'), max_length=50, blank=True)
    license_state = models.CharField(_('license state'), max_length=2, blank=True)
    license_expiry = models.DateField(_('license expiry'), blank=True, null=True)
    credit_score = models.IntegerField(_('credit score'), blank=True, null=True)
    risk_rating = models.CharField(_('risk rating'), max_length=20, blank=True)
    notes = models.TextField(_('notes'), blank=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    
    class Meta:
        db_table = 'customers'
        verbose_name = _('customer')
        verbose_name_plural = _('customers')
        indexes = [
            models.Index(fields=['customer_number']),
            models.Index(fields=['user']),
        ]
    
    def __str__(self):
        return f"{self.customer_number} - {self.user.get_full_name() or self.user.email}"

class CustomerDocument(models.Model):
    DOCUMENT_TYPES = [
        ('id', _('ID Document')),
        ('license', _('Driver License')),
        ('insurance', _('Insurance Card')),
        ('registration', _('Registration')),
        ('other', _('Other')),
    ]
    
    customer = models.ForeignKey(Customer, on_delete=models.CASCADE, related_name='documents')
    document_type = models.CharField(_('document type'), max_length=20, choices=DOCUMENT_TYPES)
    file = models.FileField(_('file'), upload_to='customer_documents/')
    original_name = models.CharField(_('original name'), max_length=255)
    uploaded_at = models.DateTimeField(auto_now_add=True)
    uploaded_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True,
        related_name='uploaded_customer_documents'
    )
    
    class Meta:
        db_table = 'customer_documents'
        verbose_name = _('customer document')
        verbose_name_plural = _('customer documents')
    
    def __str__(self):
        return f"{self.customer} - {self.get_document_type_display()}"


class CallbackRequest(models.Model):
    VEHICLE_TYPES = [
        ('car', _('Car')),
        ('two_wheeler', _('Two-wheeler')),
        ('commercial', _('Commercial vehicle')),
        ('other', _('Other')),
    ]
    STATUSES = [
        ('new', _('New')),
        ('contacted', _('Contacted')),
        ('closed', _('Closed')),
    ]

    name = models.CharField(_('name'), max_length=120)
    phone = models.CharField(_('contact number'), max_length=20)
    vehicle_type = models.CharField(_('vehicle type'), max_length=20, choices=VEHICLE_TYPES)
    consent = models.BooleanField(_('consent to be contacted'))
    status = models.CharField(_('status'), max_length=20, choices=STATUSES, default='new')
    created_at = models.DateTimeField(_('requested at'), auto_now_add=True)

    class Meta:
        db_table = 'callback_requests'
        ordering = ['-created_at']
        verbose_name = _('callback request')
        verbose_name_plural = _('callback requests')

    def __str__(self):
        return f"{self.name} - {self.phone} ({self.get_status_display()})"
