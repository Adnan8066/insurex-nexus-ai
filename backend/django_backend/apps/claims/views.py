from rest_framework import viewsets, status, filters
from rest_framework.decorators import action
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response
import logging
from django_filters.rest_framework import DjangoFilterBackend
from django.db import transaction
from django.db.models import Q
from rest_framework.exceptions import PermissionDenied
from django.utils import timezone
from django.conf import settings
from apps.accounts.models import Role

from django.shortcuts import get_object_or_404
from .models import Claim, ClaimDocument, ClaimStatusHistory, ClaimTimeline, ClaimNote, ClaimStatus
from .serializers import (
    ClaimSerializer, ClaimCreateSerializer, ClaimUpdateSerializer,
    ClaimStatusUpdateSerializer, ClaimDocumentSerializer,
    ClaimStatusHistorySerializer, ClaimTimelineSerializer, ClaimNoteSerializer
)
from common.permissions import IsEmployee, CanIssuePolicy, IsStaffMember
from common.params import parse_int
from .workflow import TransitionError, check_transition

logger = logging.getLogger(__name__)


class ClaimViewSet(viewsets.ModelViewSet):
    queryset = Claim.objects.select_related(
        'customer', 'policy', 'vehicle', 'assigned_adjuster',
        'assigned_investigator'
    ).prefetch_related('documents', 'status_history', 'timeline', 'notes')
    serializer_class = ClaimSerializer
    permission_classes = [IsAuthenticated]
    filter_backends = [DjangoFilterBackend, filters.SearchFilter, filters.OrderingFilter]
    filterset_fields = ['status', 'priority', 'incident_type', 'incident_severity']
    search_fields = ['claim_number', 'customer__email', 'customer__first_name', 'customer__last_name', 'policy__policy_number']
    ordering_fields = ['submitted_at', 'incident_date', 'claim_amount', 'status', 'priority']
    ordering = ['-submitted_at']
    
    def get_serializer_class(self):
        if self.action == 'create':
            return ClaimCreateSerializer
        elif self.action in ['update', 'partial_update']:
            return ClaimUpdateSerializer
        return ClaimSerializer
    
    lookup_value_regex = r'[^/]+'

    def get_object(self):
        queryset = self.filter_queryset(self.get_queryset())
        pk = self.kwargs.get(self.lookup_field)
        if str(pk).isdigit():
            return get_object_or_404(queryset, pk=pk)
        return get_object_or_404(queryset, claim_number=pk)

    def get_queryset(self):
        user = self.request.user
        if user.role in [Role.ADMIN, Role.EMPLOYEE]:
            return self.queryset
        if user.role == Role.INVESTIGATOR:
            return self.queryset.filter(assigned_investigator=user)
        if user.role == Role.CUSTOMER:
            return self.queryset.filter(customer=user)
        return self.queryset.none()
    
    def get_permissions(self):
        if self.action in ['create']:
            return [IsAuthenticated(), CanIssuePolicy()]
        elif self.action in ['update', 'partial_update', 'destroy']:
            # Customers (own claims, enforced by get_queryset), employees and admins.
            # Investigators work claims through the investigations API.
            return [IsAuthenticated(), CanIssuePolicy()]
        elif self.action in ['update_status', 'assign_adjuster', 'assign_investigator']:
            return [IsAuthenticated(), IsEmployee()]
        elif self.action == 'submit_assessment':
            return [IsAuthenticated(), IsStaffMember()]
        return [IsAuthenticated()]

    def perform_update(self, serializer):
        user = self.request.user
        if user.role == Role.CUSTOMER and serializer.instance.status != ClaimStatus.SUBMITTED:
            raise PermissionDenied('Claims can only be edited by the customer while they are still submitted.')
        serializer.save()

    def perform_destroy(self, instance):
        user = self.request.user
        if user.role != Role.ADMIN and instance.status != ClaimStatus.SUBMITTED:
            raise PermissionDenied(
                'Only submitted claims can be deleted. Claims that are under review or decided are kept for the audit trail.'
            )
        instance.delete()

    def create(self, request, *args, **kwargs):
        serializer = self.get_serializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        self.perform_create(serializer)
        headers = self.get_success_headers(serializer.instance)
        full = ClaimSerializer(serializer.instance, context={'request': request}).data
        return Response(full, status=status.HTTP_201_CREATED, headers=headers)
    
    def perform_create(self, serializer):
        import uuid
        claim_number = f"CLM-{uuid.uuid4().hex[:8].upper()}"
        user = self.request.user
        customer = serializer.validated_data['policy'].customer if user.is_staff_member else user
        submitted = serializer.validated_data
        complexity = min(
            1.0,
            0.2
            + min(max(int(submitted.get('number_of_vehicles', 1)) - 1, 0), 3) * 0.12
            + bool(submitted.get('injuries')) * 0.2
            + bool(submitted.get('property_damage')) * 0.12
            + bool(submitted.get('witnesses')) * 0.08
            + bool(submitted.get('police_report')) * 0.08,
        )
        claim = serializer.save(
            customer=customer,
            claim_number=claim_number,
            estimated_repair_cost=submitted.get('estimated_repair_cost') or submitted['claim_amount'],
            complexity_score=complexity,
        )
        
        ClaimStatusHistory.objects.create(
            claim=claim,
            from_status='',
            to_status=claim.status,
            reason='Claim submitted',
            changed_by=self.request.user
        )
        ClaimTimeline.objects.create(
            claim=claim,
            status=claim.status,
            title='Claim Submitted',
            description='New claim has been submitted',
            user=self.request.user,
            is_system=True
        )
        from apps.notifications.services import create_in_app_notification
        create_in_app_notification(
            claim.customer, 'claim', 'Claim submitted',
            f'Claim {claim.claim_number} was submitted successfully.',
            link=f'/claims/{claim.id}', related_object_type='claim', related_object_id=claim.id,
        )
        # Score every new claim so staff see fraud and total-loss risk without
        # running the assessment by hand. A model outage must not block FNOL.
        try:
            from apps.assessments.ai_views import run_claim_assessment
            run_claim_assessment(claim)
        except Exception:
            logger.exception('Automatic AI assessment failed for claim %s', claim.claim_number)
        # The RL router assigns only when enabled and its evaluation gate has
        # passed; otherwise the least-busy employee takes the claim.
        try:
            from apps.assessments.rl_views import auto_assign_new_claim
            from apps.assessments.assignment import assign_claim_to_least_busy
            if not auto_assign_new_claim(claim) and settings.CLAIM_AUTO_ASSIGN_LEAST_BUSY:
                assign_claim_to_least_busy(claim)
        except Exception:
            # A routing/model outage must never roll back a customer's claim.
            logger.exception('Automatic routing failed for claim %s', claim.claim_number)
    
    @action(detail=True, methods=['get', 'post'], url_path='documents')
    def documents(self, request, pk=None):
        claim = self.get_object()
        if request.method == 'POST':
            serializer = ClaimDocumentSerializer(data=request.data, context={'request': request})
            # raise_exception gives the standard error envelope the upload UI reads.
            serializer.is_valid(raise_exception=True)
            serializer.save(claim=claim, uploaded_by=request.user)
            return Response(serializer.data, status=status.HTTP_201_CREATED)

        documents = claim.documents.all()
        serializer = ClaimDocumentSerializer(documents, many=True, context={'request': request})
        return Response(serializer.data)
    
    @action(detail=True, methods=['post', 'patch'], url_path='update-status')
    def update_status(self, request, pk=None):
        claim = self.get_object()
        serializer = ClaimStatusUpdateSerializer(data=request.data)
        if serializer.is_valid():
            old_status = claim.status
            new_status = serializer.validated_data['status']
            reason = serializer.validated_data.get('reason', '')
            try:
                check_transition(claim, new_status, request.user)
            except TransitionError as exc:
                return Response({'detail': exc.message}, status=exc.status_code)
            
            with transaction.atomic():
                claim.status = new_status
                if new_status == ClaimStatus.CLOSED:
                    claim.closed_at = timezone.now()
                claim.save()
                
                ClaimStatusHistory.objects.create(
                    claim=claim,
                    from_status=old_status,
                    to_status=new_status,
                    reason=reason,
                    changed_by=request.user
                )
                
                ClaimTimeline.objects.create(
                    claim=claim,
                    status=new_status,
                    title=f'Status changed to {claim.get_status_display()}',
                    description=reason or f'Status updated from {old_status} to {new_status}',
                    user=request.user,
                    is_system=False
                )

            if claim.customer_id != request.user.id:
                from apps.notifications.services import create_in_app_notification
                create_in_app_notification(
                    claim.customer, 'claim', 'Claim status updated',
                    f'Claim {claim.claim_number} is now {claim.get_status_display()}.',
                    link=f'/claims/{claim.id}', related_object_type='claim', related_object_id=claim.id,
                )

            serializer = self.get_serializer(claim)
            return Response(serializer.data)
        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)
    
    @action(detail=True, methods=['post'], url_path='assign-adjuster')
    def assign_adjuster(self, request, pk=None):
        claim = self.get_object()
        adjuster_id = request.data.get('adjuster_id')
        if not adjuster_id:
            return Response({'error': 'adjuster_id is required'}, status=status.HTTP_400_BAD_REQUEST)
        adjuster_id = parse_int(adjuster_id, 'adjuster_id')
        
        from django.contrib.auth import get_user_model
        User = get_user_model()
        try:
            adjuster = User.objects.get(id=adjuster_id, role__in=['employee', 'admin'])
        except User.DoesNotExist:
            return Response({'error': 'Invalid adjuster'}, status=status.HTTP_400_BAD_REQUEST)
        
        claim.assigned_adjuster = adjuster
        claim.save(update_fields=['assigned_adjuster'])
        
        ClaimTimeline.objects.create(
            claim=claim,
            status=claim.status,
            title='Adjuster Assigned',
            description=f'Claim assigned to {adjuster.get_full_name() or adjuster.email}',
            user=request.user
        )
        
        serializer = self.get_serializer(claim)
        return Response(serializer.data)
    
    @action(detail=True, methods=['post'], url_path='assign-investigator')
    def assign_investigator(self, request, pk=None):
        claim = self.get_object()
        investigator_id = request.data.get('investigator_id')
        if not investigator_id:
            return Response({'error': 'investigator_id is required'}, status=status.HTTP_400_BAD_REQUEST)
        investigator_id = parse_int(investigator_id, 'investigator_id')
        
        from django.contrib.auth import get_user_model
        User = get_user_model()
        try:
            investigator = User.objects.get(id=investigator_id, role__in=['investigator', 'admin'])
        except User.DoesNotExist:
            return Response({'error': 'Invalid investigator'}, status=status.HTTP_400_BAD_REQUEST)
        
        claim.assigned_investigator = investigator
        fields_to_update = ['assigned_investigator']
        old_status = claim.status
        if claim.status != ClaimStatus.INVESTIGATION:
            claim.status = ClaimStatus.INVESTIGATION
            fields_to_update.append('status')
        claim.save(update_fields=fields_to_update)

        from apps.investigations.models import FraudAlert, Investigation
        from common.risk import fraud_risk_band
        import uuid

        score = claim.fraud_risk_score or 0
        risk_level = fraud_risk_band(score)
        assessment = claim.ai_assessment if isinstance(claim.ai_assessment, dict) else {}
        fraud_risk = assessment.get('fraud_risk') if isinstance(assessment.get('fraud_risk'), dict) else {}
        alert, _ = FraudAlert.objects.update_or_create(
            claim=claim,
            defaults={
                'risk_score': score,
                'risk_level': risk_level,
                'risk_factors': fraud_risk.get('factors', []),
                'ai_recommendation': 'Claim assigned to an investigator for review.',
                'assigned_investigator': investigator,
                'status': 'investigation',
            },
        )
        investigation, created = Investigation.objects.get_or_create(
            claim=claim,
            defaults={
                'investigator': investigator,
                'fraud_alert': alert,
                'case_number': f'INV-{uuid.uuid4().hex[:8].upper()}',
                'priority': claim.priority,
                'summary': f'Investigation opened for claim {claim.claim_number}.',
            },
        )
        if not created:
            investigation.investigator = investigator
            investigation.fraud_alert = alert
            investigation.priority = claim.priority
            investigation.save(update_fields=['investigator', 'fraud_alert', 'priority', 'updated_at'])

        if old_status != claim.status:
            ClaimStatusHistory.objects.create(
                claim=claim, from_status=old_status, to_status=claim.status,
                reason='Investigator assigned', changed_by=request.user,
            )
        
        ClaimTimeline.objects.create(
            claim=claim,
            status=claim.status,
            title='Investigator Assigned',
            description=f'Claim assigned to investigator {investigator.get_full_name() or investigator.email}',
            user=request.user
        )
        
        serializer = self.get_serializer(claim)
        return Response(serializer.data)
    
    # GET and POST share one action: two @actions with the same url_path collide
    # in the router and one of the methods answered 405.
    @action(detail=True, methods=['get', 'post'], url_path='notes')
    def notes(self, request, pk=None):
        claim = self.get_object()
        is_customer = request.user.role == Role.CUSTOMER
        if request.method == 'POST':
            serializer = ClaimNoteSerializer(data=request.data)
            if serializer.is_valid():
                extra = {'is_internal': False} if is_customer else {}
                serializer.save(claim=claim, author=request.user, **extra)
                return Response(serializer.data, status=status.HTTP_201_CREATED)
            return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)
        notes = claim.notes.all()
        if is_customer:
            notes = notes.filter(is_internal=False)
        serializer = ClaimNoteSerializer(notes, many=True)
        return Response(serializer.data)
    
    @action(detail=True, methods=['get', 'patch'], url_path='status')
    def claim_status(self, request, pk=None):
        if request.method.lower() == 'patch':
            # Calling update_status directly skips its permission classes, so the
            # employee/admin check must be repeated here.
            if not IsEmployee().has_permission(request, self):
                raise PermissionDenied('Only insurance employees or administrators can change a claim status.')
            return self.update_status(request, pk=pk)
        claim = self.get_object()
        return Response({'status': claim.status})

    @action(detail=True, methods=['get'], url_path='timeline')
    def list_timeline(self, request, pk=None):
        claim = self.get_object()
        serializer = ClaimTimelineSerializer(claim.timeline.all(), many=True)
        return Response(serializer.data)

    @action(detail=True, methods=['post'], url_path='assessment')
    def submit_assessment(self, request, pk=None):
        from apps.assessments.ai_views import run_claim_assessment
        from ml_service import MLModelUnavailable
        from apps.assessments.serializers import ClaimAssessmentSerializer

        claim = self.get_object()
        try:
            assessment = run_claim_assessment(claim)
        except MLModelUnavailable as exc:
            return Response({'error': str(exc)}, status=status.HTTP_503_SERVICE_UNAVAILABLE)
        return Response(ClaimAssessmentSerializer(assessment).data)

    @action(detail=False, methods=['get'], url_path='my-claims')
    def my_claims(self, request):
        claims = self.get_queryset().filter(customer=request.user)
        page = self.paginate_queryset(claims)
        serializer = self.get_serializer(page, many=True)
        return self.get_paginated_response(serializer.data)
    
    @action(detail=False, methods=['get'], url_path='assigned-to-me')
    def assigned_to_me(self, request):
        claims = self.get_queryset().filter(
            Q(assigned_adjuster=request.user)
            | Q(assigned_investigator=request.user)
        ).distinct()
        page = self.paginate_queryset(claims)
        serializer = self.get_serializer(page, many=True)
        return self.get_paginated_response(serializer.data)
