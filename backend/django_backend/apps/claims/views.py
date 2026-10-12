from rest_framework import viewsets, status, filters
from rest_framework.decorators import action
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response
from django_filters.rest_framework import DjangoFilterBackend
from django.db import transaction
from django.utils import timezone

from .models import Claim, ClaimDocument, ClaimStatusHistory, ClaimTimeline, ClaimNote
from .serializers import (
    ClaimSerializer, ClaimCreateSerializer, ClaimUpdateSerializer,
    ClaimStatusUpdateSerializer, ClaimDocumentSerializer,
    ClaimStatusHistorySerializer, ClaimTimelineSerializer, ClaimNoteSerializer
)
from common.permissions import IsOwnerOrAdmin, IsStaffMember, CanAccessClaim


class ClaimViewSet(viewsets.ModelViewSet):
    queryset = Claim.objects.select_related(
        'customer', 'policy', 'vehicle', 'assigned_adjuster',
        'assigned_investigator', 'assigned_repair_shop'
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
    
    def get_queryset(self):
        user = self.request.user
        if user.is_staff_member:
            return self.queryset
        return self.queryset.filter(customer=user)
    
    def get_permissions(self):
        if self.action in ['create']:
            return [IsAuthenticated()]
        elif self.action in ['update', 'partial_update', 'destroy']:
            return [IsAuthenticated(), IsOwnerOrAdmin()]
        elif self.action in ['update_status', 'assign_adjuster', 'assign_investigator', 'assign_repair_shop']:
            return [IsAuthenticated(), IsStaffMember()]
        return [IsAuthenticated()]
    
    def perform_create(self, serializer):
        import uuid
        claim_number = f"CLM-{uuid.uuid4().hex[:8].upper()}"
        claim = serializer.save(customer=self.request.user, claim_number=claim_number)
        
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
    
    @action(detail=True, methods=['post'], url_path='update-status')
    def update_status(self, request, pk=None):
        claim = self.get_object()
        serializer = ClaimStatusUpdateSerializer(data=request.data)
        if serializer.is_valid():
            old_status = claim.status
            new_status = serializer.validated_data['status']
            reason = serializer.validated_data.get('reason', '')
            
            with transaction.atomic():
                claim.status = new_status
                if new_status == Claim.ClaimStatus.CLOSED:
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
        claim.save(update_fields=['assigned_investigator'])
        
        ClaimTimeline.objects.create(
            claim=claim,
            status=claim.status,
            title='Investigator Assigned',
            description=f'Claim assigned to investigator {investigator.get_full_name() or investigator.email}',
            user=request.user
        )
        
        serializer = self.get_serializer(claim)
        return Response(serializer.data)
    
    @action(detail=True, methods=['post'], url_path='assign-repair-shop')
    def assign_repair_shop(self, request, pk=None):
        claim = self.get_object()
        repair_shop_id = request.data.get('repair_shop_id')
        if not repair_shop_id:
            return Response({'error': 'repair_shop_id is required'}, status=status.HTTP_400_BAD_REQUEST)
        
        from apps.repair_shops.models import RepairShop
        try:
            repair_shop = RepairShop.objects.get(id=repair_shop_id, status='active')
        except RepairShop.DoesNotExist:
            return Response({'error': 'Invalid repair shop'}, status=status.HTTP_400_BAD_REQUEST)
        
        claim.assigned_repair_shop = repair_shop
        claim.save(update_fields=['assigned_repair_shop'])
        
        ClaimTimeline.objects.create(
            claim=claim,
            status=claim.status,
            title='Repair Shop Assigned',
            description=f'Claim assigned to repair shop {repair_shop.name}',
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
    
    @action(detail=False, methods=['get'], url_path='my-claims')
    def my_claims(self, request):
        claims = self.get_queryset().filter(customer=request.user)
        serializer = self.get_serializer(claims, many=True)
        return Response(serializer.data)
    
    @action(detail=False, methods=['get'], url_path='assigned-to-me')
    def assigned_to_me(self, request):
        claims = self.get_queryset().filter(
            assigned_adjuster=request.user
        ) | self.get_queryset().filter(assigned_investigator=request.user)
        serializer = self.get_serializer(claims, many=True)
        return Response(serializer.data)