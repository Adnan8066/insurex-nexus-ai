from django.db import models
from django.conf import settings
from django.utils import timezone
from django.utils.translation import gettext_lazy as _

class AssessmentType(models.TextChoices):
    REPAIR_COST = 'repair_cost', _('Repair Cost Prediction')
    FRAUD_RISK = 'fraud_risk', _('Fraud Risk Assessment')
    TOTAL_LOSS = 'total_loss', _('Total Loss Prediction')
    COMPREHENSIVE = 'comprehensive', _('Comprehensive Assessment')

class AssessmentStatus(models.TextChoices):
    PENDING = 'pending', _('Pending')
    IN_PROGRESS = 'in_progress', _('In Progress')
    COMPLETED = 'completed', _('Completed')
    FAILED = 'failed', _('Failed')
    REQUIRES_REVIEW = 'requires_review', _('Requires Review')

class ClaimAssessment(models.Model):
    claim = models.OneToOneField(
        'claims.Claim',
        on_delete=models.CASCADE,
        related_name='assessment'
    )
    assessment_type = models.CharField(
        _('assessment type'),
        max_length=20,
        choices=AssessmentType.choices,
        default=AssessmentType.COMPREHENSIVE
    )
    status = models.CharField(
        _('status'),
        max_length=20,
        choices=AssessmentStatus.choices,
        default=AssessmentStatus.PENDING
    )
    model_version = models.CharField(_('model version'), max_length=50, blank=True)
    
    # Repair Cost Prediction
    predicted_repair_cost = models.DecimalField(
        _('predicted repair cost'),
        max_digits=12,
        decimal_places=2,
        blank=True,
        null=True
    )
    cost_breakdown = models.JSONField(_('cost breakdown'), default=dict, blank=True)
    repair_time_estimate_days = models.PositiveIntegerField(_('repair time estimate (days)'), blank=True, null=True)
    comparable_claims_count = models.PositiveIntegerField(_('comparable claims count'), default=0)
    
    # Fraud Risk Assessment
    fraud_risk_score = models.DecimalField(
        _('fraud risk score'),
        max_digits=5,
        decimal_places=2,
        blank=True,
        null=True
    )
    risk_level = models.CharField(
        _('risk level'),
        max_length=20,
        choices=[('low', _('Low')), ('medium', _('Medium')), ('high', _('High'))],
        blank=True
    )
    risk_factors = models.JSONField(_('risk factors'), default=list, blank=True)
    behavioral_indicators = models.JSONField(_('behavioral indicators'), default=list, blank=True)
    network_analysis = models.JSONField(_('network analysis'), default=dict, blank=True)
    
    # Total Loss Prediction
    total_loss_probability = models.DecimalField(
        _('total loss probability'),
        max_digits=5,
        decimal_places=2,
        blank=True,
        null=True
    )
    
    # Overall
    claim_priority = models.CharField(
        _('claim priority'),
        max_length=20,
        choices=[('low', _('Low')), ('medium', _('Medium')), ('high', _('High')), ('critical', _('Critical'))],
        blank=True
    )
    ai_recommendation = models.TextField(_('AI recommendation'), blank=True)
    confidence = models.DecimalField(_('confidence'), max_digits=5, decimal_places=2, blank=True, null=True)
    contributing_factors = models.JSONField(_('contributing factors'), default=list, blank=True)
    
    assessed_at = models.DateTimeField(_('assessed at'), blank=True, null=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    reviewed_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='reviewed_assessments'
    )
    reviewed_at = models.DateTimeField(_('reviewed at'), blank=True, null=True)
    
    class Meta:
        db_table = 'claim_assessments'
        verbose_name = _('claim assessment')
        verbose_name_plural = _('claim assessments')
        indexes = [
            models.Index(fields=['claim']),
            models.Index(fields=['status']),
            models.Index(fields=['assessed_at']),
        ]
    
    def __str__(self):
        return f"Assessment for {self.claim} ({self.get_status_display()})"

class AgentOutput(models.Model):
    AGENT_TYPES = [
        ('claim_agent', _('Claim Agent')),
        ('policy_agent', _('Policy Agent')),
        ('fraud_agent', _('Fraud Agent')),
        ('damage_agent', _('Damage Agent')),
        ('settlement_agent', _('Settlement Agent')),
        ('decision_agent', _('Decision Agent')),
    ]
    
    claim = models.ForeignKey('claims.Claim', on_delete=models.CASCADE, related_name='agent_outputs')
    agent_type = models.CharField(_('agent type'), max_length=20, choices=AGENT_TYPES)
    status = models.CharField(_('status'), max_length=20, choices=[
        ('pending', _('Pending')),
        ('running', _('Running')),
        ('completed', _('Completed')),
        ('failed', _('Failed')),
    ], default='pending')
    input_data = models.JSONField(_('input data'), default=dict)
    output_data = models.JSONField(_('output data'), default=dict)
    confidence = models.DecimalField(_('confidence'), max_digits=5, decimal_places=2, blank=True, null=True)
    processing_time_seconds = models.DecimalField(
        _('processing time (seconds)'),
        max_digits=6,
        decimal_places=2,
        blank=True,
        null=True
    )
    error_message = models.TextField(_('error message'), blank=True)
    created_at = models.DateTimeField(auto_now_add=True)
    completed_at = models.DateTimeField(_('completed at'), blank=True, null=True)
    
    class Meta:
        db_table = 'agent_outputs'
        verbose_name = _('agent output')
        verbose_name_plural = _('agent outputs')
        unique_together = ['claim', 'agent_type']
    
    def __str__(self):
        return f"{self.get_agent_type_display()} for {self.claim}"

class DecisionFlow(models.Model):
    claim = models.OneToOneField('claims.Claim', on_delete=models.CASCADE, related_name='decision_flow')
    agents = models.JSONField(_('agents'), default=list)
    rl_recommendation = models.JSONField(_('RL recommendation'), default=dict)
    final_decision = models.JSONField(_('final decision'), default=dict)
    model_version = models.CharField(_('model version'), max_length=50, blank=True)
    decided_at = models.DateTimeField(_('decided at'), blank=True, null=True)
    decided_by = models.CharField(_('decided by'), max_length=100, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    
    class Meta:
        db_table = 'decision_flows'
        verbose_name = _('decision flow')
        verbose_name_plural = _('decision flows')
    
    def __str__(self):
        return f"Decision Flow for {self.claim}"

class ModelPerformance(models.Model):
    MODEL_TYPES = [
        ('claim_assessment', _('Claim Assessment')),
        ('fraud_detection', _('Fraud Detection')),
        ('total_loss_prediction', _('Total Loss Prediction')),
        ('repair_cost_prediction', _('Repair Cost Prediction')),
        ('rl_optimizer', _('RL Optimizer')),
    ]
    
    model_type = models.CharField(_('model type'), max_length=30, choices=MODEL_TYPES)
    version = models.CharField(_('version'), max_length=50)
    accuracy = models.DecimalField(_('accuracy'), max_digits=5, decimal_places=2, blank=True, null=True)
    precision = models.DecimalField(_('precision'), max_digits=5, decimal_places=2, blank=True, null=True)
    recall = models.DecimalField(_('recall'), max_digits=5, decimal_places=2, blank=True, null=True)
    f1_score = models.DecimalField(_('F1 score'), max_digits=5, decimal_places=2, blank=True, null=True)
    mae = models.DecimalField(_('MAE'), max_digits=10, decimal_places=2, blank=True, null=True)
    rmse = models.DecimalField(_('RMSE'), max_digits=10, decimal_places=2, blank=True, null=True)
    r2_score = models.DecimalField(_('R² score'), max_digits=5, decimal_places=4, blank=True, null=True)
    auc = models.DecimalField(_('AUC'), max_digits=5, decimal_places=4, blank=True, null=True)
    training_samples = models.PositiveIntegerField(_('training samples'), default=0)
    validation_samples = models.PositiveIntegerField(_('validation samples'), default=0)
    test_samples = models.PositiveIntegerField(_('test samples'), default=0)
    training_duration_seconds = models.PositiveIntegerField(_('training duration (seconds)'), default=0)
    hyperparameters = models.JSONField(_('hyperparameters'), default=dict)
    metrics = models.JSONField(_('metrics'), default=dict)
    artifact_path = models.CharField(_('artifact path'), max_length=500, blank=True)
    is_active = models.BooleanField(_('is active'), default=False)
    trained_at = models.DateTimeField(_('trained at'))
    registered_at = models.DateTimeField(auto_now_add=True)
    
    class Meta:
        db_table = 'model_performances'
        verbose_name = _('model performance')
        verbose_name_plural = _('model performances')
        unique_together = ['model_type', 'version']
        ordering = ['-trained_at']
    
    def __str__(self):
        return f"{self.get_model_type_display()} v{self.version}"