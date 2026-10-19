from rest_framework import viewsets, status, filters
from rest_framework.decorators import action
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response
from django_filters.rest_framework import DjangoFilterBackend
from django.db import transaction
from django.utils import timezone
from apps.accounts.models import Role

from django.shortcuts import get_object_or_404
from .models import Claim, ClaimDocument, ClaimStatusHistory, ClaimTimeline, ClaimNote, ClaimStatus
from .serializers import (
    ClaimSerializer, ClaimCreateSerializer, ClaimUpdateSerializer,
    ClaimStatusUpdateSerializer, ClaimDocumentSerializer,
    ClaimStatusHistorySerializer, ClaimTimelineSerializer, ClaimNoteSerializer
)
from common.permissions import IsOwnerOrAdmin, IsEmployee, CanIssuePolicy


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
            return [IsAuthenticated(), IsOwnerOrAdmin()]
        elif self.action in ['update_status', 'assign_adjuster', 'assign_investigator']:
            return [IsAuthenticated(), IsEmployee()]
        return [IsAuthenticated()]

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
    
    @action(detail=True, methods=['post'], url_path='documents')
    def upload_document(self, request, pk=None):
        claim = self.get_object()
        serializer = ClaimDocumentSerializer(data=request.data)
        if serializer.is_valid():
            serializer.save(claim=claim, uploaded_by=request.user)
            return Response(serializer.data, status=status.HTTP_201_CREATED)
        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)
    
    @action(detail=True, methods=['get'], url_path='documents')
    def list_documents(self, request, pk=None):
        claim = self.get_object()
        documents = claim.documents.all()
        serializer = ClaimDocumentSerializer(documents, many=True)
        return Response(serializer.data)
    
    @action(detail=True, methods=['post', 'patch'], url_path='update-status')
    def update_status(self, request, pk=None):
        claim = self.get_object()
        serializer = ClaimStatusUpdateSerializer(data=request.data)
        if serializer.is_valid():
            old_status = claim.status
            new_status = serializer.validated_data['status']
            reason = serializer.validated_data.get('reason', '')
            
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

                # Approval should prepare the settlement record so staff can
                # review it directly from the Settlements dashboard.
                if new_status == ClaimStatus.APPROVED and old_status != ClaimStatus.APPROVED:
                    from decimal import Decimal
                    import uuid
                    from apps.settlements.models import Settlement, SettlementTimeline

                    assessment = claim.ai_assessment if isinstance(claim.ai_assessment, dict) else {}
                    estimate_value = claim.estimated_repair_cost or assessment.get('predicted_repair_cost') or claim.claim_amount
                    if isinstance(estimate_value, dict):
                        estimate_value = estimate_value.get('cost') or claim.claim_amount
                    estimated_amount = Decimal(str(estimate_value))
                    deductible = claim.policy.deductible
                    from apps.settlements.services.payout import calculate_payout_for_claim
                    payout = calculate_payout_for_claim(claim, estimated_amount)
                    Settlement.objects.get_or_create(
                        claim=claim,
                        defaults={
                            'settlement_number': f"SET-{uuid.uuid4().hex[:8].upper()}",
                            'customer': claim.customer,
                            'estimated_amount': estimated_amount,
                            'deductible': deductible,
                            'approved_amount': payout.payout,
                            'depreciation_amount': payout.depreciation,
                            'asset_age_years': payout.asset_age_years,
                            'zero_depreciation_applied': payout.zero_depreciation_applied,
                            'payout_calculation': payout.as_dict(),
                            'notes': 'Estimated payout prepared for staff review; verify coverage and policy terms before approval.',
                        },
                    )
                    settlement = Settlement.objects.get(claim=claim)
                    if not settlement.timeline.exists():
                        SettlementTimeline.objects.create(
                            settlement=settlement,
                            status=settlement.status,
                            title='Settlement Prepared After Claim Approval',
                            description=f'Settlement prepared for approved claim {claim.claim_number}. Review the amount and payment status.',
                            user=request.user,
                            metadata={'estimated_amount': str(settlement.estimated_amount)},
                        )

            if claim.customer_id != request.user.id:
                from apps.notifications.services import create_in_app_notification
                create_in_app_notification(
                    claim.customer, 'claim', 'Claim status updated',
                    f'Claim {claim.claim_number} is now {claim.get_status_display()}.',
                    link=f'/claims/{claim.id}', related_object_type='claim', related_object_id=claim.id,
                )

            if new_status == ClaimStatus.APPROVED and old_status != ClaimStatus.APPROVED:
                from apps.notifications.services import create_in_app_notification
                settlement = getattr(claim, 'settlement', None)
                if settlement:
                    create_in_app_notification(
                        claim.customer, 'settlement', 'Settlement prepared',
                        f'Claim {claim.claim_number} was approved and its settlement is ready for staff review.',
                        link='/settlements', related_object_type='settlement', related_object_id=settlement.id,
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
        import uuid

        score = claim.fraud_risk_score or 0
        risk_level = 'high' if score >= 70 else 'medium' if score >= 35 else 'low'
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
    
    @action(detail=True, methods=['post'], url_path='notes')
    def add_note(self, request, pk=None):
        claim = self.get_object()
        serializer = ClaimNoteSerializer(data=request.data)
        if serializer.is_valid():
            serializer.save(claim=claim, author=request.user)
            return Response(serializer.data, status=status.HTTP_201_CREATED)
        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)
    
    @action(detail=True, methods=['get'], url_path='notes')
    def list_notes(self, request, pk=None):
        claim = self.get_object()
        notes = claim.notes.all()
        serializer = ClaimNoteSerializer(notes, many=True)
        return Response(serializer.data)
    
    @action(detail=True, methods=['get', 'patch'], url_path='status')
    def claim_status(self, request, pk=None):
        if request.method.lower() == 'patch':
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
        from apps.assessments.ai_views import (
            predict_repair_cost_internal, detect_fraud_internal, predict_total_loss_internal,
            generate_recommendation, calculate_confidence,
        )
        from ml_service import MLModelUnavailable
        from apps.assessments.models import ClaimAssessment, AssessmentType, AssessmentStatus
        from apps.assessments.serializers import ClaimAssessmentSerializer

        claim = self.get_object()
        assessment, _created = ClaimAssessment.objects.get_or_create(
            claim=claim,
            defaults={'assessment_type': AssessmentType.COMPREHENSIVE},
        )
        try:
            predicted_cost = predict_repair_cost_internal(claim)
            fraud_score = detect_fraud_internal(claim)
            total_loss_prob = predict_total_loss_internal(claim)
        except MLModelUnavailable as exc:
            return Response({'error': str(exc)}, status=status.HTTP_503_SERVICE_UNAVAILABLE)
        assessment.predicted_repair_cost = predicted_cost['cost']
        assessment.fraud_risk_score = fraud_score['score']
        assessment.total_loss_probability = total_loss_prob['probability']
        assessment.ai_recommendation = generate_recommendation(assessment)
        assessment.confidence = calculate_confidence(assessment)
        assessment.status = AssessmentStatus.COMPLETED
        assessment.save()
        claim.ai_assessment = ClaimAssessmentSerializer(assessment).data
        claim.fraud_risk_score = fraud_score['score']
        claim.total_loss_probability = total_loss_prob['probability']
        claim.save(update_fields=['ai_assessment', 'fraud_risk_score', 'total_loss_probability'])
        return Response(ClaimAssessmentSerializer(assessment).data)

    @action(detail=False, methods=['get'], url_path='my-claims')
    def my_claims(self, request):
        claims = self.get_queryset().filter(customer=request.user)
        serializer = self.get_serializer(claims, many=True)
        return Response(serializer.data)
    
    @action(detail=False, methods=['get'], url_path='assigned-to-me')
    def assigned_to_me(self, request):
        claims = self.get_queryset().filter(
            Q(assigned_adjuster=request.user)
            | Q(assigned_investigator=request.user)
        ).distinct()
        serializer = self.get_serializer(claims, many=True)
        return Response(serializer.data)
