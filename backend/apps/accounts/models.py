from django.contrib.auth.models import AbstractUser
from django.db import models
from django.utils import timezone
from django.utils.translation import gettext_lazy as _

class Role(models.TextChoices):
    CUSTOMER = 'customer', _('Customer')
    EMPLOYEE = 'employee', _('Insurance Employee')
    INVESTIGATOR = 'investigator', _('Investigator')
    REPAIR = 'repair', _('Repair Shop')
    ADMIN = 'admin', _('Administrator')

class User(AbstractUser):
    email = models.EmailField(_('email address'), unique=True)
    role = models.CharField(
        _('role'),
        max_length=20,
        choices=Role.choices,
        default=Role.CUSTOMER
    )
    phone = models.CharField(_('phone number'), max_length=20, blank=True)
    address = models.TextField(_('address'), blank=True)
    department = models.CharField(_('department'), max_length=100, blank=True)
    avatar = models.ImageField(_('avatar'), upload_to='avatars/', blank=True, null=True)
    date_joined = models.DateTimeField(_('date joined'), default=timezone.now)
    is_verified = models.BooleanField(_('verified'), default=False)
    last_login_ip = models.GenericIPAddressField(_('last login IP'), blank=True, null=True)
    password_reset_token = models.CharField(_('password reset token'), max_length=64, blank=True, null=True)
    password_reset_token_created = models.DateTimeField(_('password reset token created'), blank=True, null=True)
    
    USERNAME_FIELD = 'email'
    REQUIRED_FIELDS = ['username']
    
    class Meta:
        db_table = 'users'
        verbose_name = _('user')
        verbose_name_plural = _('users')
        indexes = [
            models.Index(fields=['email']),
            models.Index(fields=['role']),
        ]
    
    def __str__(self):
        return f"{self.email} ({self.get_role_display()})"
    
    @property
    def is_customer(self):
        return self.role == Role.CUSTOMER
    
    @property
    def is_employee(self):
        return self.role == Role.EMPLOYEE
    
    @property
    def is_investigator(self):
        return self.role == Role.INVESTIGATOR
    
    @property
    def is_repair(self):
        return self.role == Role.REPAIR
    
    @property
    def is_admin(self):
        return self.role == Role.ADMIN
    
    @property
    def is_staff_member(self):
        return self.role in [Role.EMPLOYEE, Role.INVESTIGATOR, Role.ADMIN]

class UserProfile(models.Model):
    user = models.OneToOneField(User, on_delete=models.CASCADE, related_name='profile')
    bio = models.TextField(_('bio'), blank=True)
    date_of_birth = models.DateField(_('date of birth'), blank=True, null=True)
    emergency_contact_name = models.CharField(_('emergency contact name'), max_length=100, blank=True)
    emergency_contact_phone = models.CharField(_('emergency contact phone'), max_length=20, blank=True)
    preferred_language = models.CharField(_('preferred language'), max_length=10, default='en')
    timezone = models.CharField(_('timezone'), max_length=50, default='UTC')
    notification_email = models.BooleanField(_('email notifications'), default=True)
    notification_sms = models.BooleanField(_('SMS notifications'), default=False)
    notification_push = models.BooleanField(_('push notifications'), default=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    
    class Meta:
        db_table = 'user_profiles'
        verbose_name = _('user profile')
        verbose_name_plural = _('user profiles')
    
    def __str__(self):
        return f"Profile: {self.user.email}"