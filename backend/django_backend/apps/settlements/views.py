from rest_framework import viewsets, status, filters
from rest_framework.decorators import action
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response
from django_filters.rest_framework import DjangoFilterBackend
from django.utils import timezone
import uuid

from .models import Settlement, SettlementTimeline, SettlementPayment
from .serializers import (
    SettlementSerializer, SettlementCreateSerializer, SettlementUpdateSerializer,
    SettlementApproveSerializer, SettlementPaySerializer,
    SettlementTimelineSerializer, SettlementPaymentSerializer
)
from common.permissions import IsStaffMember


class SettlementViewSet(viewsets.ModelViewSet):
    queryset = Settlement.objects.select_related(
        'claim', 'customer', 'approved_by', 'paid_by'
    ).prefetch_related('timeline', 'payments').all()
    serializer_class = SettlementSerializer
    permission_classes = [IsAuthenticated, IsStaffMember]
    filter_backends = [DjangoFilterBackend, filters.SearchFilter, filters.OrderingFilter]
    filterset_fields = ['status', 'payment_status', 'payment_method']
    search_fields = ['settlement_number', 'claim__claim_number', 'customer__email']
    ordering_fields = ['created_at', 'approved_at', 'paid_at']
    ordering = ['-created_at']
    
    def get_serializer_class(self):
        if self.action == 'create':
            return SettlementCreateSerializer
        elif self.action in ['update', 'partial_update']:
            return SettlementUpdateSerializer
        return SettlementSerializer
    
    def perform_create(self, serializer):
        settlement_number = f"SET-{uuid.uuid4().hex[:8].upper()}"
        settlement = serializer.save(settlement_number=settlement_number)
        
        SettlementTimeline.objects.create(
            settlement=settlement,
            status=settlement.status,
            title='Settlement Calculated',
            description=f'Settlement calculated with estimated amount: ${settlement.estimated_amount}',
            user=self.request.user,
            metadata={'estimated_amount': str(settlement.estimated_amount)}
        )
    
    @action(detail=True, methods=['post'], url_path='approve')
    def approve(self, request, pk=None):
        settlement = self.get_object()
        serializer = SettlementApproveSerializer(data=request.data)
        if serializer.is_valid():
            settlement.approved_amount = serializer.validated_data['approved_amount']
            settlement.status = Settlement.SettlementStatus.APPROVED
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
                description=f'Settlement approved for amount: ${settlement.approved_amount}',
                user=request.user,
                metadata={'approved_amount': str(settlement.approved_amount)}
            )
            
            return Response(self.get_serializer(settlement).data)
        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)
    
    @action(detail=True, methods=['post'], url_path='reject')
    def reject(self, request, pk=None):
        settlement = self.get_object()
        settlement.status = Settlement.SettlementStatus.REJECTED
        settlement.notes = request.data.get('notes', settlement.notes)
        settlement.save(update_fields=['status', 'notes'])
        
        SettlementTimeline.objects.create(
            settlement=settlement,
            status=settlement.status,
            title='Settlement Rejected',
            description=settlement.notes or 'Settlement rejected',
            user=request.user
        )
        
        return Response(self.get_serializer(settlement).data)
    
    @action(detail=True, methods=['post'], url_path='pay')
    def pay(self, request, pk=None):
        settlement = self.get_object()
        
        if settlement.status != Settlement.SettlementStatus.APPROVED:
            return Response(
                {'error': 'Settlement must be approved before payment'},
                status=status.HTTP_400_BAD_REQUEST
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
                status=SettlementPayment.PaymentStatus.PROCESSING,
                initiated_by=request.user
            )
            
            settlement.payment_status = Settlement.PaymentStatus.PROCESSING
            settlement.save(update_fields=['payment_status'])
            
            SettlementTimeline.objects.create(
                settlement=settlement,
                status=settlement.status,
                title='Payment Initiated',
                description=f'Payment of ${payment.amount} initiated via {payment.payment_method}',
                user=request.user,
                metadata={'payment_number': payment_number}
            )
            
            return Response(SettlementPaymentSerializer(payment).data, status=status.HTTP_201_CREATED)
        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)
    
    @action(detail=True, methods=['post'], url_path='complete-payment')
    def complete_payment(self, request, pk=None):
        settlement = self.get_object()
        payment_id = request.data.get('payment_id')
        
        if not payment_id:
            return Response({'error': 'payment_id is required'}, status=status.HTTP_400_BAD_REQUEST)
        
        try:
            payment = settlement.payments.get(id=payment_id)
        except SettlementPayment.DoesNotExist:
            return Response({'error': 'Payment not found'}, status=status.HTTP_404_NOT_FOUND)
        
        payment.status = SettlementPayment.PaymentStatus.COMPLETED
        payment.processed_by = request.user
        payment.processed_at = timezone.now()
        payment.save(update_fields=['status', 'processed_by', 'processed_at'])
        
        settlement.payment_status = Settlement.PaymentStatus.COMPLETED
        settlement.paid_by = request.user
        settlement.paid_at = timezone.now()
        settlement.save(update_fields=['payment_status', 'paid_by', 'paid_at'])
        
        SettlementTimeline.objects.create(
            settlement=settlement,
            status=settlement.status,
            title='Payment Completed',
            description=f'Payment of ${payment.amount} completed successfully',
            user=request.user,
            metadata={'payment_number': payment.payment_number}
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
            return Response({'error': 'Use list endpoint'}, status=status.HTTP_400_BAD_REQUEST)
        
        settlements = self.get_queryset().filter(customer=request.user)
        serializer = self.get_serializer(settlements, many=True)
        return Response(serializer.data)