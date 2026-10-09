from django.db import models
from django.conf import settings
from django.utils.translation import gettext_lazy as _

class VehicleStatus(models.TextChoices):
    ACTIVE = 'active', _('Active')
    SOLD = 'sold', _('Sold')
    TOTAL_LOSS = 'total_loss', _('Total Loss')
    SALVAGE = 'salvage', _('Salvage')
    INACTIVE = 'inactive', _('Inactive')

class FuelType(models.TextChoices):
    GASOLINE = 'gasoline', _('Gasoline')
    DIESEL = 'diesel', _('Diesel')
    HYBRID = 'hybrid', _('Hybrid')
    ELECTRIC = 'electric', _('Electric')
    PLUGIN_HYBRID = 'plugin_hybrid', _('Plug-in Hybrid')

class TransmissionType(models.TextChoices):
    AUTOMATIC = 'automatic', _('Automatic')
    MANUAL = 'manual', _('Manual')
    CVT = 'cvt', _('CVT')
    SEMI_AUTOMATIC = 'semi_automatic', _('Semi-Automatic')

class Vehicle(models.Model):
    customer = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name='vehicles'
    )
    policy = models.ForeignKey(
        'policies.Policy',
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='vehicles'
    )
    make = models.CharField(_('make'), max_length=50)
    model = models.CharField(_('model'), max_length=50)
    year = models.IntegerField(_('year'))
    vin = models.CharField(_('VIN'), max_length=17, unique=True)
    color = models.CharField(_('color'), max_length=30)
    license_plate = models.CharField(_('license plate'), max_length=20)
    license_state = models.CharField(_('license state'), max_length=2)
    registration_expiry = models.DateField(_('registration expiry'))
    purchase_date = models.DateField(_('purchase date'), blank=True, null=True)
    purchase_price = models.DecimalField(_('purchase price'), max_digits=10, decimal_places=2, blank=True, null=True)
    current_mileage = models.IntegerField(_('current mileage'), default=0)
    fuel_type = models.CharField(_('fuel type'), max_length=20, choices=FuelType.choices, default=FuelType.GASOLINE)
    transmission = models.CharField(_('transmission'), max_length=20, choices=TransmissionType.choices, default=TransmissionType.AUTOMATIC)
    status = models.CharField(_('status'), max_length=20, choices=VehicleStatus.choices, default=VehicleStatus.ACTIVE)
    engine_size = models.DecimalField(_('engine size (L)'), max_digits=3, decimal_places=1, blank=True, null=True)
    body_style = models.CharField(_('body style'), max_length=30, blank=True)
    features = models.JSONField(_('features'), default=dict, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    
    class Meta:
        db_table = 'vehicles'
        verbose_name = _('vehicle')
        verbose_name_plural = _('vehicles')
        indexes = [
            models.Index(fields=['vin']),
            models.Index(fields=['license_plate', 'license_state']),
            models.Index(fields=['customer']),
            models.Index(fields=['policy']),
        ]
    
    def __str__(self):
        return f"{self.year} {self.make} {self.model} ({self.license_plate})"

class VehicleDocument(models.Model):
    DOCUMENT_TYPES = [
        ('registration', _('Registration')),
        ('inspection', _('Inspection Report')),
        ('title', _('Title')),
        ('bill_of_sale', _('Bill of Sale')),
        ('insurance_card', _('Insurance Card')),
        ('other', _('Other')),
    ]
    
    vehicle = models.ForeignKey(Vehicle, on_delete=models.CASCADE, related_name='documents')
    document_type = models.CharField(_('document type'), max_length=20, choices=DOCUMENT_TYPES)
    file = models.FileField(_('file'), upload_to='vehicle_documents/')
    original_name = models.CharField(_('original name'), max_length=255)
    uploaded_at = models.DateTimeField(auto_now_add=True)
    uploaded_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True,
        related_name='uploaded_vehicle_documents'
    )
    
    class Meta:
        db_table = 'vehicle_documents'
        verbose_name = _('vehicle document')
        verbose_name_plural = _('vehicle documents')
    
    def __str__(self):
        return f"{self.vehicle} - {self.get_document_type_display()}"

class VehicleHistory(models.Model):
    vehicle = models.ForeignKey(Vehicle, on_delete=models.CASCADE, related_name='history')
    event_type = models.CharField(_('event type'), max_length=50)
    description = models.TextField(_('description'))
    date = models.DateField(_('date'))
    mileage = models.IntegerField(_('mileage'), blank=True, null=True)
    cost = models.DecimalField(_('cost'), max_digits=10, decimal_places=2, blank=True, null=True)
    performed_by = models.CharField(_('performed by'), max_length=100, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)
    
    class Meta:
        db_table = 'vehicle_histories'
        verbose_name = _('vehicle history')
        verbose_name_plural = _('vehicle histories')
        ordering = ['-date']
    
    def __str__(self):
        return f"{self.vehicle} - {self.event_type} ({self.date})"