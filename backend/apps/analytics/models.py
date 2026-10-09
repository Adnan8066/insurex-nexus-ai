from django.db import models
from django.conf import settings
from django.utils.translation import gettext_lazy as _

class DashboardMetric(models.Model):
    METRIC_TYPES = [
        ('count', _('Count')),
        ('sum', _('Sum')),
        ('average', _('Average')),
        ('percentage', _('Percentage')),
        ('rate', _('Rate')),
    ]
    
    name = models.CharField(_('name'), max_length=100, unique=True)
    display_name = models.CharField(_('display name'), max_length=200)
    metric_type = models.CharField(_('metric type'), max_length=20, choices=METRIC_TYPES)
    description = models.TextField(_('description'), blank=True)
    query = models.TextField(_('query'), help_text='SQL or ORM query to calculate the metric')
    is_active = models.BooleanField(_('active'), default=True)
    refresh_interval_minutes = models.PositiveIntegerField(_('refresh interval (minutes)'), default=60)
    last_calculated = models.DateTimeField(_('last calculated'), blank=True, null=True)
    last_value = models.JSONField(_('last value'), default=dict, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    
    class Meta:
        db_table = 'dashboard_metrics'
        verbose_name = _('dashboard metric')
        verbose_name_plural = _('dashboard metrics')
    
    def __str__(self):
        return self.display_name

class AnalyticsSnapshot(models.Model):
    PERIOD_TYPES = [
        ('hourly', _('Hourly')),
        ('daily', _('Daily')),
        ('weekly', _('Weekly')),
        ('monthly', _('Monthly')),
        ('quarterly', _('Quarterly')),
        ('yearly', _('Yearly')),
    ]
    
    period_type = models.CharField(_('period type'), max_length=20, choices=PERIOD_TYPES)
    period_start = models.DateTimeField(_('period start'))
    period_end = models.DateTimeField(_('period end'))
    metrics = models.JSONField(_('metrics'), default=dict)
    filters = models.JSONField(_('filters'), default=dict, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)
    
    class Meta:
        db_table = 'analytics_snapshots'
        verbose_name = _('analytics snapshot')
        verbose_name_plural = _('analytics snapshots')
        unique_together = ['period_type', 'period_start', 'filters']
        indexes = [
            models.Index(fields=['period_type', 'period_start']),
        ]
        ordering = ['-period_start']
    
    def __str__(self):
        return f"{self.get_period_type_display()} {self.period_start.date()}"

class Report(models.Model):
    REPORT_TYPES = [
        ('claims_summary', _('Claims Summary')),
        ('financial_summary', _('Financial Summary')),
        ('fraud_analysis', _('Fraud Analysis')),
        ('performance', _('Performance Report')),
        ('custom', _('Custom Report')),
    ]
    
    FORMAT_CHOICES = [
        ('json', _('JSON')),
        ('csv', _('CSV')),
        ('pdf', _('PDF')),
        ('xlsx', _('Excel')),
    ]
    
    name = models.CharField(_('name'), max_length=200)
    report_type = models.CharField(_('report type'), max_length=30, choices=REPORT_TYPES)
    description = models.TextField(_('description'), blank=True)
    query = models.TextField(_('query'), blank=True)
    parameters = models.JSONField(_('parameters'), default=dict, blank=True)
    schedule = models.JSONField(_('schedule'), default=dict, blank=True)
    last_run = models.DateTimeField(_('last run'), blank=True, null=True)
    next_run = models.DateTimeField(_('next run'), blank=True, null=True)
    is_active = models.BooleanField(_('active'), default=True)
    created_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True,
        related_name='created_reports'
    )
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    
    class Meta:
        db_table = 'reports'
        verbose_name = _('report')
        verbose_name_plural = _('reports')
        ordering = ['-created_at']
    
    def __str__(self):
        return self.name

class ReportExecution(models.Model):
    STATUS_CHOICES = [
        ('pending', _('Pending')),
        ('running', _('Running')),
        ('completed', _('Completed')),
        ('failed', _('Failed')),
    ]
    
    report = models.ForeignKey(Report, on_delete=models.CASCADE, related_name='executions')
    status = models.CharField(_('status'), max_length=20, choices=STATUS_CHOICES, default='pending')
    parameters = models.JSONField(_('parameters'), default=dict, blank=True)
    result = models.JSONField(_('result'), default=dict, blank=True)
    file_path = models.CharField(_('file path'), max_length=500, blank=True)
    error_message = models.TextField(_('error message'), blank=True)
    started_at = models.DateTimeField(auto_now_add=True)
    completed_at = models.DateTimeField(_('completed at'), blank=True, null=True)
    executed_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True,
        related_name='executed_reports'
    )
    
    class Meta:
        db_table = 'report_executions'
        verbose_name = _('report execution')
        verbose_name_plural = _('report executions')
        ordering = ['-started_at']
    
    def __str__(self):
        return f"{self.report} - {self.status}"