from rest_framework import viewsets, status, filters
from rest_framework.decorators import action
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response
from django_filters.rest_framework import DjangoFilterBackend
from django.db import transaction
from django.utils import timezone
from apps.accounts.models import Role

from .models import (
    Investigation, FraudAlert, InvestigationStatus, InvestigationVehicleCheck,
    VehicleCheckCode, VehicleCheckResult,
)
from .serializers import (
    InvestigationSerializer, InvestigationCreateSerializer, InvestigationUpdateSerializer,
    InvestigationEvidenceSerializer, InvestigationNoteSerializer,
    FraudAlertSerializer, FraudAlertUpdateSerializer,
    InvestigationVehicleCheckSerializer, VehicleCheckItemSerializer,
)
from common.permissions import IsStaffMember
from apps.auditlog.context import AuditActorViewSetMixin

STARTABLE_STATUSES = {InvestigationStatus.OPEN, InvestigationStatus.ON_HOLD, InvestigationStatus.PENDING_REVIEW}
COMPLETABLE_STATUSES = {InvestigationStatus.IN_PROGRESS, InvestigationStatus.PENDING_REVIEW}


class InvestigationViewSet(AuditActorViewSetMixin, viewsets.ModelViewSet):
    queryset = Investigation.objects.select_related(
        'claim', 'claim__customer', 'investigator', 'fraud_alert'
    ).prefetch_related('evidence', 'notes')
    serializer_class = InvestigationSerializer
    permission_classes = [IsAuthenticated, IsStaffMember]
    filter_backends = [DjangoFilterBackend, filters.SearchFilter, filters.OrderingFilter]
    filterset_fields = ['status', 'priority', 'claim']
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
        if user.role in [Role.ADMIN, Role.EMPLOYEE]:
            return self.queryset
        if user.role == Role.INVESTIGATOR:
            return self.queryset.filter(investigator=user)
        return self.queryset.none()
    
    def perform_create(self, serializer):
        import uuid
        case_number = f"INV-{uuid.uuid4().hex[:8].upper()}"
        serializer.save(case_number=case_number, opened_at=timezone.now())
    
    # GET and POST share one action per path: separate @actions with the same
    # url_path collide in the router and GET answered 405.
    @action(detail=True, methods=['get', 'post'], url_path='evidence')
    def evidence(self, request, pk=None):
        investigation = self.get_object()
        if request.method == 'POST':
            serializer = InvestigationEvidenceSerializer(data=request.data)
            if serializer.is_valid():
                serializer.save(investigation=investigation, collected_by=request.user)
                return Response(serializer.data, status=status.HTTP_201_CREATED)
            return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)
        serializer = InvestigationEvidenceSerializer(investigation.evidence.all(), many=True)
        return Response(serializer.data)

    @action(detail=True, methods=['get', 'post'], url_path='notes')
    def notes(self, request, pk=None):
        investigation = self.get_object()
        if request.method == 'POST':
            serializer = InvestigationNoteSerializer(data=request.data)
            if serializer.is_valid():
                serializer.save(investigation=investigation, author=request.user)
                return Response(serializer.data, status=status.HTTP_201_CREATED)
            return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)
        serializer = InvestigationNoteSerializer(investigation.notes.all(), many=True)
        return Response(serializer.data)
    
    # Fixed vehicle checklist. GET is readable by every staff member who can see the case;
    # POST is only for the investigator assigned to it, and only while the case is still open.
    @action(detail=True, methods=['get', 'post'], url_path='vehicle-checks')
    def vehicle_checks(self, request, pk=None):
        investigation = self.get_object()
        if request.method == 'POST':
            if request.user.role != Role.INVESTIGATOR or investigation.investigator_id != request.user.id:
                return Response(
                    {'detail': 'Only the investigator assigned to this case can record vehicle checks.'},
                    status=status.HTTP_403_FORBIDDEN,
                )
            if investigation.status in {InvestigationStatus.COMPLETED, InvestigationStatus.CLOSED}:
                return Response(
                    {'detail': 'This investigation is closed, so its vehicle checks can no longer be changed.'},
                    status=status.HTTP_400_BAD_REQUEST,
                )
            items = request.data.get('checks')
            if not isinstance(items, list):
                return Response({'checks': ['Send a list of checks.']}, status=status.HTTP_400_BAD_REQUEST)
            serializer = VehicleCheckItemSerializer(data=items, many=True)
            if not serializer.is_valid():
                return Response({'checks': serializer.errors}, status=status.HTTP_400_BAD_REQUEST)
            valid_codes = set(VehicleCheckCode.values)
            for item in serializer.validated_data:
                if item['check_code'] not in valid_codes:
                    return Response(
                        {'checks': [f"Unknown check: {item['check_code']}"]}, status=status.HTTP_400_BAD_REQUEST,
                    )
            with transaction.atomic():
                for item in serializer.validated_data:
                    InvestigationVehicleCheck.objects.update_or_create(
                        investigation=investigation,
                        check_code=item['check_code'],
                        defaults={
                            'result': item['result'],
                            'note': item.get('note', ''),
                            'checked_by': request.user,
                        },
                    )
        return Response(self._vehicle_check_payload(investigation))

    @staticmethod
    def _vehicle_check_payload(investigation):
        saved = {row.check_code: row for row in investigation.vehicle_checks.select_related('checked_by')}
        rows = []
        for code, label in VehicleCheckCode.choices:
            row = saved.get(code)
            rows.append({
                'check_code': code,
                'check_label': str(label),
                'result': row.result if row else None,
                'note': row.note if row else '',
                'checked_by_name': row.checked_by.get_full_name() if row and row.checked_by else None,
                'checked_at': row.checked_at if row else None,
            })
        completed = sum(1 for r in rows if r['result'] is not None)
        return {'checks': rows, 'completed': completed, 'total': len(rows)}

    @action(detail=True, methods=['post'], url_path='start')
    def start_investigation(self, request, pk=None):
        investigation = self.get_object()
        if investigation.status not in STARTABLE_STATUSES:
            return Response(
                {'detail': f'An investigation that is {investigation.get_status_display().lower()} cannot be started.'},
                status=status.HTTP_400_BAD_REQUEST,
            )
        investigation.status = InvestigationStatus.IN_PROGRESS
        if not investigation.started_at:
            investigation.started_at = timezone.now()
        investigation.save(update_fields=['status', 'started_at'])
        serializer = self.get_serializer(investigation)
        return Response(serializer.data)

    @action(detail=True, methods=['post'], url_path='complete')
    def complete_investigation(self, request, pk=None):
        investigation = self.get_object()
        if investigation.status not in COMPLETABLE_STATUSES:
            return Response(
                {'detail': 'Start the investigation before completing it.'},
                status=status.HTTP_400_BAD_REQUEST,
            )
        findings = str(request.data.get('findings', investigation.findings) or '').strip()
        if not findings:
            # Completing unblocks approval of a high-risk claim, so it must say what was found.
            return Response(
                {'findings': ['Describe what the investigation found before completing it.']},
                status=status.HTTP_400_BAD_REQUEST,
            )
        investigation.status = InvestigationStatus.COMPLETED
        investigation.completed_at = timezone.now()
        investigation.findings = findings
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

    def get_queryset(self):
        user = self.request.user
        if user.role in [Role.ADMIN, Role.EMPLOYEE]:
            return self.queryset
        if user.role == Role.INVESTIGATOR:
            return self.queryset.filter(assigned_investigator=user)
        return self.queryset.none()
    
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
