from rest_framework import viewsets, status, filters
from rest_framework.decorators import action
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response
from django_filters.rest_framework import DjangoFilterBackend
from django.utils import timezone

from .models import ClaimAssessment, AgentOutput, DecisionFlow, ModelPerformance
from .serializers import (
    ClaimAssessmentSerializer, ClaimAssessmentCreateSerializer,
    AgentOutputSerializer, DecisionFlowSerializer, ModelPerformanceSerializer
)
from common.permissions import IsStaffMember


class ClaimAssessmentViewSet(viewsets.ModelViewSet):
    queryset = ClaimAssessment.objects.select_related('claim', 'claim__customer', 'reviewed_by').all()
    serializer_class = ClaimAssessmentSerializer
    permission_classes = [IsAuthenticated, IsStaffMember]
    filter_backends = [DjangoFilterBackend, filters.SearchFilter, filters.OrderingFilter]
    filterset_fields = ['assessment_type', 'status', 'risk_level', 'claim_priority']
    search_fields = ['claim__claim_number', 'claim__customer__email', 'claim__customer__first_name', 'claim__customer__last_name']
    ordering_fields = ['created_at', 'assessed_at', 'fraud_risk_score', 'total_loss_probability']
    ordering = ['-created_at']
    
    def get_serializer_class(self):
        if self.action == 'create':
            return ClaimAssessmentCreateSerializer
        return ClaimAssessmentSerializer
    
    @action(detail=True, methods=['post'], url_path='review')
    def review(self, request, pk=None):
        assessment = self.get_object()
        assessment.status = ClaimAssessment.AssessmentStatus.COMPLETED
        assessment.reviewed_by = request.user
        assessment.reviewed_at = timezone.now()
        assessment.save(update_fields=['status', 'reviewed_by', 'reviewed_at'])
        
        serializer = self.get_serializer(assessment)
        return Response(serializer.data)
    
    @action(detail=True, methods=['post'], url_path='request-review')
    def request_review(self, request, pk=None):
        assessment = self.get_object()
        assessment.status = ClaimAssessment.AssessmentStatus.REQUIRES_REVIEW
        assessment.save(update_fields=['status'])
        
        serializer = self.get_serializer(assessment)
        return Response(serializer.data)


class AgentOutputViewSet(viewsets.ReadOnlyModelViewSet):
    queryset = AgentOutput.objects.select_related('claim').all()
    serializer_class = AgentOutputSerializer
    permission_classes = [IsAuthenticated, IsStaffMember]
    filter_backends = [DjangoFilterBackend, filters.SearchFilter, filters.OrderingFilter]
    filterset_fields = ['agent_type', 'status']
    search_fields = ['claim__claim_number']
    ordering_fields = ['created_at', 'completed_at']
    ordering = ['-created_at']


class DecisionFlowViewSet(viewsets.ReadOnlyModelViewSet):
    queryset = DecisionFlow.objects.select_related('claim').all()
    serializer_class = DecisionFlowSerializer
    permission_classes = [IsAuthenticated, IsStaffMember]
    filter_backends = [DjangoFilterBackend, filters.SearchFilter, filters.OrderingFilter]
    search_fields = ['claim__claim_number']
    ordering_fields = ['created_at', 'decided_at']
    ordering = ['-created_at']


class ModelPerformanceViewSet(viewsets.ReadOnlyModelViewSet):
    queryset = ModelPerformance.objects.all()
    serializer_class = ModelPerformanceSerializer
    permission_classes = [IsAuthenticated, IsStaffMember]
    filter_backends = [DjangoFilterBackend, filters.SearchFilter, filters.OrderingFilter]
    filterset_fields = ['model_type', 'is_active']
    ordering_fields = ['trained_at', 'accuracy', 'f1_score', 'auc']
    ordering = ['-trained_at']
    
    @action(detail=False, methods=['get'], url_path='active')
    def active_models(self, request):
        models = self.get_queryset().filter(is_active=True)
        serializer = self.get_serializer(models, many=True)
        return Response(serializer.data)