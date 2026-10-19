from rest_framework import viewsets, status, filters
from rest_framework.decorators import action
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response
from django_filters.rest_framework import DjangoFilterBackend
from django.db import transaction
from django.utils import timezone
import uuid

from .models import (
    Settlement, SettlementTimeline, SettlementPayment,
    SettlementStatus, PaymentStatus,
)
from .serializers import (
    SettlementSerializer, SettlementCreateSerializer, SettlementUpdateSerializer,
    SettlementApproveSerializer, SettlementPaySerializer,
    SettlementTimelineSerializer, SettlementPaymentSerializer
)
from apps.claims.models import ClaimStatus, ClaimStatusHistory, ClaimTimeline
from common.permissions import IsStaffMember


class SettlementViewSet(viewsets.ModelViewSet):
    queryset = Settlement.objects.select_related(
        'claim', 'customer', 'approved_by', 'paid_by'
    ).prefetch_related('timeline', 'payments').all()
    serializer_class = SettlementSerializer
    permission_classes = [IsAuthenticated]
    filter_backends = [DjangoFilterBackend, filters.SearchFilter, filters.OrderingFilter]
    filterset_fields = ['status', 'payment_status', 'payment_method']
    search_fields = ['settlement_number', 'claim__claim_number', 'customer__email']
    ordering_fields = ['created_at', 'approved_at', 'paid_at']
    ordering = ['-created_at']

    def get_permissions(self):
        if self.action in ['list', 'retrieve', 'my_settlements', 'timeline', 'payments', 'by_claim']:
            return [IsAuthenticated()]
        return [IsAuthenticated(), IsStaffMember()]

    def get_queryset(self):
        queryset = super().get_queryset()
        if self.request.user.is_staff_member:
            return queryset
        return queryset.filter(customer=self.request.user)
    
    def get_serializer_class(self):
        if self.action == 'create':
            return SettlementCreateSerializer
        elif self.action in ['update', 'partial_update']:
            return SettlementUpdateSerializer
        return SettlementSerializer
    
    def perform_create(self, serializer):
        settlement_number = f"SET-{uuid.uuid4().hex[:8].upper()}"
        claim = serializer.validated_data['claim']
        from .services.payout import calculate_payout_for_claim
        payout = calculate_payout_for_claim(claim, serializer.validated_data['estimated_amount'])
        settlement = serializer.save(
            settlement_number=settlement_number,
            customer=claim.customer,
            deductible=payout.deductible,
            approved_amount=payout.payout,
            depreciation_amount=payout.depreciation,
            asset_age_years=payout.asset_age_years,
            zero_depreciation_applied=payout.zero_depreciation_applied,
            payout_calculation=payout.as_dict(),
        )
        
        SettlementTimeline.objects.create(
            settlement=settlement,
            status=settlement.status,
            title='Settlement Calculated',
            description=f'Settlement calculated with estimated amount: ₹{settlement.estimated_amount:,.2f}',
            user=self.request.user,
            metadata={'estimated_amount': str(settlement.estimated_amount)}
        )
        from apps.notifications.services import create_in_app_notification
        create_in_app_notification(
            settlement.customer, 'settlement', 'Settlement prepared',
            f'A settlement record for claim {settlement.claim.claim_number} is ready for review.',
            link=f'/settlements', related_object_type='settlement', related_object_id=settlement.id,
        )
    
    @action(detail=True, methods=['post'], url_path='approve')
    def approve(self, request, pk=None):
        settlement = self.get_object()
        if settlement.status not in [SettlementStatus.CALCULATED, SettlementStatus.UNDER_REVIEW]:
            return Response({'detail': 'Only calculated settlements can be approved.'}, status=status.HTTP_409_CONFLICT)
        serializer = SettlementApproveSerializer(data=request.data)
        if serializer.is_valid():
            with transaction.atomic():
                settlement.approved_amount = serializer.validated_data['approved_amount']
                settlement.status = SettlementStatus.APPROVED
                settlement.approved_by = request.user
                settlement.approved_at = timezone.now()
                settlement.notes = serializer.validated_data.get('notes', settlement.notes)
                settlement.save(update_fields=[
                    'approved_amount', 'status', 'approved_by', 'approved_at', 'notes'
                ])

                SettlementTimeline.objects.create(
                    settlement=settlement,
                    status=settlement.status,
                    title='Settlement Approved',
                    description=f'Settlement approved for amount: ₹{settlement.approved_amount:,.2f}',
                    user=request.user,
                    metadata={'approved_amount': str(settlement.approved_amount)}
                )

                claim = settlement.claim
                if claim.status == ClaimStatus.APPROVED:
                    claim.status = ClaimStatus.REPAIR_SETTLEMENT
                    claim.save(update_fields=['status', 'updated_at'])
                    ClaimStatusHistory.objects.create(
                        claim=claim,
                        from_status=ClaimStatus.APPROVED,
                        to_status=ClaimStatus.REPAIR_SETTLEMENT,
                        reason=f'Settlement {settlement.settlement_number} approved.',
                        changed_by=request.user,
                        metadata={'settlement_id': settlement.id},
                    )
                    ClaimTimeline.objects.create(
                        claim=claim,
                        status=ClaimStatus.REPAIR_SETTLEMENT,
                        title='Settlement Approved',
                        description=f'Settlement {settlement.settlement_number} approved for ₹{settlement.approved_amount:,.2f}.',
                        user=request.user,
                        metadata={'settlement_id': settlement.id},
                    )
            from apps.notifications.services import create_in_app_notification
            create_in_app_notification(
                settlement.customer, 'settlement', 'Settlement approved',
                f'Settlement {settlement.settlement_number} was approved.',
                link='/settlements', related_object_type='settlement', related_object_id=settlement.id,
            )
            
            return Response(self.get_serializer(settlement).data)
        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)
    
    @action(detail=True, methods=['post'], url_path='reject')
    def reject(self, request, pk=None):
        settlement = self.get_object()
        if settlement.status not in [SettlementStatus.CALCULATED, SettlementStatus.UNDER_REVIEW]:
            return Response({'detail': 'Only calculated settlements can be rejected.'}, status=status.HTTP_409_CONFLICT)
        settlement.status = SettlementStatus.REJECTED
        settlement.notes = request.data.get('notes', settlement.notes)
        settlement.save(update_fields=['status', 'notes'])
        
        SettlementTimeline.objects.create(
            settlement=settlement,
            status=settlement.status,
            title='Settlement Rejected',
            description=settlement.notes or 'Settlement rejected',
            user=request.user
        )
        from apps.notifications.services import create_in_app_notification
        create_in_app_notification(
            settlement.customer, 'settlement', 'Settlement declined',
            f'Settlement {settlement.settlement_number} was declined.',
            link='/settlements', related_object_type='settlement', related_object_id=settlement.id,
        )
        
        return Response(self.get_serializer(settlement).data)
    
    @action(detail=True, methods=['post'], url_path='pay')
    def pay(self, request, pk=None):
        settlement = self.get_object()
        
        if settlement.status != SettlementStatus.APPROVED:
            return Response(
                {'error': 'Settlement must be approved before payment'},
                status=status.HTTP_400_BAD_REQUEST
            )

        if settlement.payment_status == PaymentStatus.PROCESSING:
            return Response(
                {'detail': 'A payout is already in progress for this settlement.'},
                status=status.HTTP_409_CONFLICT
            )
        
        serializer = SettlementPaySerializer(data=request.data)
        if serializer.is_valid():
            payment_number = f"PAY-{uuid.uuid4().hex[:8].upper()}"
            
            payment = SettlementPayment.objects.create(
                settlement=settlement,
                payment_number=payment_number,
                amount=settlement.approved_amount,
                payment_method=serializer.validated_data['payment_method'],
                payment_reference=serializer.validated_data.get('payment_reference', ''),
                status=PaymentStatus.PROCESSING,
                initiated_by=request.user
            )
            
            settlement.payment_status = PaymentStatus.PROCESSING
            settlement.payment_method = payment.payment_method
            settlement.payment_reference = payment.payment_reference
            settlement.save(update_fields=['payment_status', 'payment_method', 'payment_reference'])
            
            SettlementTimeline.objects.create(
                settlement=settlement,
                status=settlement.status,
                title='Payment Initiated',
                description=f'Payment of ₹{payment.amount:,.2f} initiated via {payment.payment_method}',
                user=request.user,
                metadata={'payment_number': payment_number}
            )
            from apps.notifications.services import create_in_app_notification
            create_in_app_notification(
                settlement.customer, 'payment', 'Payout initiated',
                f'A payout record for settlement {settlement.settlement_number} was initiated. This does not confirm funds transfer.',
                link='/settlements', related_object_type='settlement', related_object_id=settlement.id,
            )
            
            return Response(SettlementPaymentSerializer(payment).data, status=status.HTTP_201_CREATED)
        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)
    
    @action(detail=True, methods=['post'], url_path='complete-payment')
    def complete_payment(self, request, pk=None):
        settlement = self.get_object()
        if settlement.payment_status != PaymentStatus.PROCESSING:
            return Response({'detail': 'There is no payout in progress for this settlement.'}, status=status.HTTP_409_CONFLICT)
        payment_id = request.data.get('payment_id')
        
        if not payment_id:
            return Response({'error': 'payment_id is required'}, status=status.HTTP_400_BAD_REQUEST)
        
        try:
            payment = settlement.payments.get(id=payment_id)
        except SettlementPayment.DoesNotExist:
            return Response({'error': 'Payment not found'}, status=status.HTTP_404_NOT_FOUND)

        if payment.status != PaymentStatus.PROCESSING:
            return Response({'detail': 'This payment is not awaiting completion.'}, status=status.HTTP_409_CONFLICT)
        
        payment.status = PaymentStatus.COMPLETED
        payment.processed_by = request.user
        payment.processed_at = timezone.now()
        payment.save(update_fields=['status', 'processed_by', 'processed_at'])
        
        settlement.payment_status = PaymentStatus.COMPLETED
        settlement.status = SettlementStatus.PAID
        settlement.paid_by = request.user
        settlement.paid_at = timezone.now()
        settlement.save(update_fields=['payment_status', 'status', 'paid_by', 'paid_at'])
        
        SettlementTimeline.objects.create(
            settlement=settlement,
            status=settlement.status,
            title='Payment Completed',
            description=f'Payment of ₹{payment.amount:,.2f} completed successfully',
            user=request.user,
            metadata={'payment_number': payment.payment_number}
        )
        from apps.notifications.services import create_in_app_notification
        create_in_app_notification(
            settlement.customer, 'payment', 'Payout marked complete',
            f'Payment {payment.payment_number} for settlement {settlement.settlement_number} was marked complete by staff.',
            link='/settlements', related_object_type='settlement', related_object_id=settlement.id,
        )
        
        return Response(self.get_serializer(settlement).data)
    
    @action(detail=True, methods=['get'], url_path='timeline')
    def timeline(self, request, pk=None):
        settlement = self.get_object()
        timeline = settlement.timeline.all()
        serializer = SettlementTimelineSerializer(timeline, many=True)
        return Response(serializer.data)
    
    @action(detail=True, methods=['get'], url_path='payments')
    def payments(self, request, pk=None):
        settlement = self.get_object()
        payments = settlement.payments.all()
        serializer = SettlementPaymentSerializer(payments, many=True)
        return Response(serializer.data)
    
    @action(detail=False, methods=['get'], url_path='my-settlements')
    def my_settlements(self, request):
        if request.user.is_staff_member:
            settlements = self.get_queryset()
            serializer = self.get_serializer(settlements, many=True)
            return Response(serializer.data)
        
        settlements = self.get_queryset().filter(customer=request.user)
        serializer = self.get_serializer(settlements, many=True)
        return Response(serializer.data)

    @action(detail=False, methods=['get'], url_path=r'by-claim/(?P<claim_id>\d+)')
    def by_claim(self, request, claim_id=None):
        settlement = self.get_queryset().filter(claim_id=claim_id).first()
        if settlement is None:
            return Response({'detail': 'No settlement found for this claim.'}, status=status.HTTP_404_NOT_FOUND)
        return Response(self.get_serializer(settlement).data)
