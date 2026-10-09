from rest_framework import viewsets, status, filters
from rest_framework.decorators import action
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response
from django_filters.rest_framework import DjangoFilterBackend
from django.utils import timezone

from .models import Investigation, InvestigationEvidence, InvestigationNote, FraudAlert
from .serializers import (
    InvestigationSerializer, InvestigationCreateSerializer, InvestigationUpdateSerializer,
    InvestigationEvidenceSerializer, InvestigationNoteSerializer,
    FraudAlertSerializer, FraudAlertUpdateSerializer
)
from common.permissions import IsStaffMember, IsInvestigator


class InvestigationViewSet(viewsets.ModelViewSet):
    queryset = Investigation.objects.select_related(
        'claim', 'claim__customer', 'investigator', 'fraud_alert'
    ).prefetch_related('evidence', 'notes')
    serializer_class = InvestigationSerializer
    permission_classes = [IsAuthenticated, IsInvestigator]
    filter_backends = [DjangoFilterBackend, filters.SearchFilter, filters.OrderingFilter]
    filterset_fields = ['status', 'priority']
    search_fields = ['case_number', 'claim__claim_number', 'claim__customer__email']
    ordering_fields = ['opened_at', 'started_at', 'completed_at']
    ordering = ['-opened_at']
    
    def get_serializer_class(self):
        if self.action == 'create':
            return InvestigationCreateSerializer
        elif self.action in ['update', 'partial_update']:
            return InvestigationUpdateSerializer
        return InvestigationSerializer
    
    def get_queryset(self):
        user = self.request.user
        if user.is_staff_member:
            return self.queryset
        return self.queryset.filter(investigator=user)
    
    def perform_create(self, serializer):
        import uuid
        case_number = f"INV-{uuid.uuid4().hex[:8].upper()}"
        serializer.save(case_number=case_number, opened_at=timezone.now())
    
    @action(detail=True, methods=['post'], url_path='evidence')
    def add_evidence(self, request, pk=None):
        investigation = self.get_object()
        serializer = InvestigationEvidenceSerializer(data=request.data)
        if serializer.is_valid():
            serializer.save(investigation=investigation, collected_by=request.user)
            return Response(serializer.data, status=status.HTTP_201_CREATED)
        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)
    
    @action(detail=True, methods=['get'], url_path='evidence')
    def list_evidence(self, request, pk=None):
        investigation = self.get_object()
        evidence = investigation.evidence.all()
        serializer = InvestigationEvidenceSerializer(evidence, many=True)
        return Response(serializer.data)
    
    @action(detail=True, methods=['post'], url_path='notes')
    def add_note(self, request, pk=None):
        investigation = self.get_object()
        serializer = InvestigationNoteSerializer(data=request.data)
        if serializer.is_valid():
            serializer.save(investigation=investigation, author=request.user)
            return Response(serializer.data, status=status.HTTP_201_CREATED)
        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)
    
    @action(detail=True, methods=['get'], url_path='notes')
    def list_notes(self, request, pk=None):
        investigation = self.get_object()
        notes = investigation.notes.all()
        serializer = InvestigationNoteSerializer(notes, many=True)
        return Response(serializer.data)
    
    @action(detail=True, methods=['post'], url_path='start')
    def start_investigation(self, request, pk=None):
        investigation = self.get_object()
        investigation.status = Investigation.InvestigationStatus.IN_PROGRESS
        investigation.started_at = timezone.now()
        investigation.save(update_fields=['status', 'started_at'])
        serializer = self.get_serializer(investigation)
        return Response(serializer.data)
    
    @action(detail=True, methods=['post'], url_path='complete')
    def complete_investigation(self, request, pk=None):
        investigation = self.get_object()
        investigation.status = Investigation.InvestigationStatus.COMPLETED
        investigation.completed_at = timezone.now()
        investigation.findings = request.data.get('findings', investigation.findings)
        investigation.conclusion = request.data.get('conclusion', investigation.conclusion)
        investigation.recommendation = request.data.get('recommendation', investigation.recommendation)
        investigation.save(update_fields=['status', 'completed_at', 'findings', 'conclusion', 'recommendation'])
        serializer = self.get_serializer(investigation)
        return Response(serializer.data)


class FraudAlertViewSet(viewsets.ModelViewSet):
    queryset = FraudAlert.objects.select_related('claim', 'claim__customer', 'assigned_investigator', 'reviewed_by').all()
    serializer_class = FraudAlertSerializer
    permission_classes = [IsAuthenticated, IsStaffMember]
    filter_backends = [DjangoFilterBackend, filters.SearchFilter, filters.OrderingFilter]
    filterset_fields = ['risk_level', 'status']
    search_fields = ['claim__claim_number', 'claim__customer__email']
    ordering_fields = ['created_at', 'risk_score']
    ordering = ['-created_at']
    
    def get_serializer_class(self):
        if self.action in ['update', 'partial_update']:
            return FraudAlertUpdateSerializer
        return FraudAlertSerializer
    
    @action(detail=True, methods=['post'], url_path='review')
    def review(self, request, pk=None):
        alert = self.get_object()
        alert.status = 'reviewed'
        alert.reviewed_by = request.user
        alert.reviewed_at = timezone.now()
        alert.investigator_notes = request.data.get('investigator_notes', alert.investigator_notes)
        alert.save(update_fields=['status', 'reviewed_by', 'reviewed_at', 'investigator_notes'])
        
        serializer = self.get_serializer(alert)
        return Response(serializer.data)
    
    @action(detail=True, methods=['post'], url_path='escalate')
    def escalate(self, request, pk=None):
        alert = self.get_object()
        alert.status = 'escalated'
        alert.assigned_investigator = request.user
        alert.save(update_fields=['status', 'assigned_investigator'])
        
        serializer = self.get_serializer(alert)
        return Response(serializer.data)
    
    @action(detail=True, methods=['post'], url_path='dismiss')
    def dismiss(self, request, pk=None):
        alert = self.get_object()
        alert.status = 'dismissed'
        alert.investigator_notes = request.data.get('investigator_notes', alert.investigator_notes)
        alert.reviewed_by = request.user
        alert.reviewed_at = timezone.now()
        alert.save(update_fields=['status', 'investigator_notes', 'reviewed_by', 'reviewed_at'])
        
        serializer = self.get_serializer(alert)
        return Response(serializer.data)
    
    @action(detail=False, methods=['get'], url_path='high-risk')
    def high_risk(self, request):
        alerts = self.get_queryset().filter(risk_level='high', status__in=['new', 'investigation'])
        serializer = self.get_serializer(alerts, many=True)
        return Response(serializer.data)