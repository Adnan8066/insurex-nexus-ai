from rest_framework import viewsets, status, filters
from rest_framework.decorators import action
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response
from django_filters.rest_framework import DjangoFilterBackend
from django.db.models import Q

from .models import Policy, PolicyCoverage, PolicyDocument, PremiumHistory
from .serializers import (
    PolicySerializer, PolicyCreateSerializer, PolicyUpdateSerializer,
    PolicyCoverageSerializer, PolicyDocumentSerializer, PremiumHistorySerializer
)
from common.permissions import IsOwnerOrAdmin, IsStaffMember


class PolicyViewSet(viewsets.ModelViewSet):
    queryset = Policy.objects.select_related('customer', 'agent', 'vehicle').prefetch_related(
        'coverage_details', 'documents', 'premium_history'
    )
    serializer_class = PolicySerializer
    permission_classes = [IsAuthenticated]
    filter_backends = [DjangoFilterBackend, filters.SearchFilter, filters.OrderingFilter]
    filterset_fields = ['type', 'status', 'payment_frequency']
    search_fields = ['policy_number', 'customer__email', 'customer__first_name', 'customer__last_name']
    ordering_fields = ['created_at', 'start_date', 'end_date', 'premium']
    ordering = ['-created_at']
    
    def get_serializer_class(self):
        if self.action == 'create':
            return PolicyCreateSerializer
        elif self.action in ['update', 'partial_update']:
            return PolicyUpdateSerializer
        return PolicySerializer
    
    def get_queryset(self):
        user = self.request.user
        if user.is_staff_member:
            return self.queryset
        return self.queryset.filter(customer=user)
    
    def get_permissions(self):
        if self.action in ['create']:
            return [IsAuthenticated(), IsStaffMember()]
        elif self.action in ['update', 'partial_update', 'destroy']:
            return [IsAuthenticated(), IsOwnerOrAdmin()]
        return [IsAuthenticated()]
    
    def perform_create(self, serializer):
        import uuid
        policy_number = f"POL-{uuid.uuid4().hex[:8].upper()}"
        serializer.save(policy_number=policy_number)
    
    @action(detail=True, methods=['post'], url_path='documents')
    def upload_document(self, request, pk=None):
        policy = self.get_object()
        serializer = PolicyDocumentSerializer(data=request.data)
        if serializer.is_valid():
            serializer.save(policy=policy, uploaded_by=request.user)
            return Response(serializer.data, status=status.HTTP_201_CREATED)
        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)
    
    @action(detail=True, methods=['get'], url_path='documents')
    def list_documents(self, request, pk=None):
        policy = self.get_object()
        documents = policy.documents.all()
        serializer = PolicyDocumentSerializer(documents, many=True)
        return Response(serializer.data)
    
    @action(detail=True, methods=['get'], url_path='premium-history')
    def premium_history(self, request, pk=None):
        policy = self.get_object()
        history = policy.premium_history.all()
        serializer = PremiumHistorySerializer(history, many=True)
        return Response(serializer.data)
    
    @action(detail=True, methods=['post'], url_path='premium-history')
    def add_premium_payment(self, request, pk=None):
        policy = self.get_object()
        serializer = PremiumHistorySerializer(data=request.data)
        if serializer.is_valid():
            serializer.save(policy=policy)
            return Response(serializer.data, status=status.HTTP_201_CREATED)
        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)
    
    @action(detail=True, methods=['get'], url_path='coverage')
    def coverage(self, request, pk=None):
        policy = self.get_object()
        try:
            coverage = policy.coverage_details
            serializer = PolicyCoverageSerializer(coverage)
            return Response(serializer.data)
        except PolicyCoverage.DoesNotExist:
            return Response({'detail': 'Coverage details not found'}, status=status.HTTP_404_NOT_FOUND)
    
    @action(detail=True, methods=['put', 'patch'], url_path='coverage')
    def update_coverage(self, request, pk=None):
        policy = self.get_object()
        coverage, created = PolicyCoverage.objects.get_or_create(policy=policy)
        serializer = PolicyCoverageSerializer(coverage, data=request.data, partial=True)
        if serializer.is_valid():
            serializer.save()
            return Response(serializer.data)
        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)
    
    @action(detail=False, methods=['get'], url_path='expiring')
    def expiring_soon(self, request):
        from django.utils import timezone
        from datetime import timedelta
        
        days = int(request.query_params.get('days', 30))
        upcoming_date = timezone.now().date() + timedelta(days=days)
        
        policies = self.get_queryset().filter(
            status=Policy.PolicyStatus.ACTIVE,
            end_date__lte=upcoming_date,
            end_date__gte=timezone.now().date()
        )
        serializer = self.get_serializer(policies, many=True)
        return Response(serializer.data)