from rest_framework import viewsets, status, filters
from rest_framework.decorators import action
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response
from django_filters.rest_framework import DjangoFilterBackend
from django.utils import timezone

from .models import RepairShop, RepairJob, RepairEstimate, RepairShopDocument
from .serializers import (
    RepairShopSerializer, RepairShopCreateSerializer, RepairShopUpdateSerializer,
    RepairJobSerializer, RepairJobCreateSerializer, RepairJobUpdateSerializer,
    RepairEstimateSerializer, RepairShopDocumentSerializer
)
from common.permissions import IsStaffMember, IsRepairShop


class RepairShopViewSet(viewsets.ModelViewSet):
    queryset = RepairShop.objects.prefetch_related('documents', 'jobs').all()
    serializer_class = RepairShopSerializer
    permission_classes = [IsAuthenticated, IsStaffMember]
    filter_backends = [DjangoFilterBackend, filters.SearchFilter, filters.OrderingFilter]
    filterset_fields = ['status', 'city', 'state']
    search_fields = ['name', 'license_number', 'email', 'city']
    ordering_fields = ['created_at', 'name', 'rating']
    ordering = ['-created_at']
    
    def get_serializer_class(self):
        if self.action == 'create':
            return RepairShopCreateSerializer
        elif self.action in ['update', 'partial_update']:
            return RepairShopUpdateSerializer
        return RepairShopSerializer
    
    @action(detail=True, methods=['post'], url_path='documents')
    def upload_document(self, request, pk=None):
        shop = self.get_object()
        serializer = RepairShopDocumentSerializer(data=request.data)
        if serializer.is_valid():
            serializer.save(repair_shop=shop, uploaded_by=request.user)
            return Response(serializer.data, status=status.HTTP_201_CREATED)
        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)
    
    @action(detail=True, methods=['get'], url_path='documents')
    def list_documents(self, request, pk=None):
        shop = self.get_object()
        documents = shop.documents.all()
        serializer = RepairShopDocumentSerializer(documents, many=True)
        return Response(serializer.data)
    
    @action(detail=True, methods=['post'], url_path='approve')
    def approve(self, request, pk=None):
        shop = self.get_object()
        shop.status = RepairShop.RepairShopStatus.APPROVED
        shop.approved_by = request.user
        shop.approved_at = timezone.now()
        shop.save(update_fields=['status', 'approved_by', 'approved_at'])
        serializer = self.get_serializer(shop)
        return Response(serializer.data)
    
    @action(detail=True, methods=['post'], url_path='suspend')
    def suspend(self, request, pk=None):
        shop = self.get_object()
        shop.status = RepairShop.RepairShopStatus.SUSPENDED
        shop.save(update_fields=['status'])
        serializer = self.get_serializer(shop)
        return Response(serializer.data)
    
    @action(detail=False, methods=['get'], url_path='nearby')
    def nearby(self, request):
        city = request.query_params.get('city')
        state = request.query_params.get('state')
        
        if not city or not state:
            return Response(
                {'error': 'city and state query parameters are required'},
                status=status.HTTP_400_BAD_REQUEST
            )
        
        shops = self.get_queryset().filter(
            city__iexact=city, state__iexact=state,
            status=RepairShop.RepairShopStatus.APPROVED
        )
        serializer = self.get_serializer(shops, many=True)
        return Response(serializer.data)


class RepairJobViewSet(viewsets.ModelViewSet):
    queryset = RepairJob.objects.select_related('claim', 'repair_shop').prefetch_related('estimates').all()
    serializer_class = RepairJobSerializer
    permission_classes = [IsAuthenticated]
    filter_backends = [DjangoFilterBackend, filters.SearchFilter, filters.OrderingFilter]
    filterset_fields = ['status', 'priority', 'repair_shop']
    search_fields = ['job_number', 'claim__claim_number']
    ordering_fields = ['created_at', 'estimated_completion', 'started_at']
    ordering = ['-created_at']
    
    def get_serializer_class(self):
        if self.action == 'create':
            return RepairJobCreateSerializer
        elif self.action in ['update', 'partial_update']:
            return RepairJobUpdateSerializer
        return RepairJobSerializer
    
    def get_queryset(self):
        user = self.request.user
        if user.is_staff_member:
            return self.queryset
        if user.role == 'repair':
            return self.queryset.filter(repair_shop__contact_person=user.email)
        return self.queryset.filter(claim__customer=user)
    
    def get_permissions(self):
        if self.action in ['create']:
            return [IsAuthenticated(), IsStaffMember()]
        elif self.action in ['update', 'partial_update', 'destroy']:
            return [IsAuthenticated(), IsStaffMember()]
        return [IsAuthenticated()]
    
    def perform_create(self, serializer):
        import uuid
        job_number = f"JOB-{uuid.uuid4().hex[:8].upper()}"
        serializer.save(job_number=job_number)
    
    @action(detail=True, methods=['post'], url_path='estimates')
    def add_estimate(self, request, pk=None):
        job = self.get_object()
        serializer = RepairEstimateSerializer(data=request.data)
        if serializer.is_valid():
            import uuid
            estimate_number = f"EST-{uuid.uuid4().hex[:8].upper()}"
            serializer.save(repair_job=job, estimate_number=estimate_number)
            return Response(serializer.data, status=status.HTTP_201_CREATED)
        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)
    
    @action(detail=True, methods=['get'], url_path='estimates')
    def list_estimates(self, request, pk=None):
        job = self.get_object()
        estimates = job.estimates.all()
        serializer = RepairEstimateSerializer(estimates, many=True)
        return Response(serializer.data)
    
    @action(detail=True, methods=['post'], url_path='start')
    def start_job(self, request, pk=None):
        job = self.get_object()
        job.status = RepairJob.JOB_STATUS_CHOICES[2][0]  # in_progress
        job.started_at = timezone.now().date()
        job.repair_shop.current_jobs += 1
        job.repair_shop.save(update_fields=['current_jobs'])
        job.save(update_fields=['status', 'started_at'])
        serializer = self.get_serializer(job)
        return Response(serializer.data)
    
    @action(detail=True, methods=['post'], url_path='complete')
    def complete_job(self, request, pk=None):
        job = self.get_object()
        job.status = RepairJob.JOB_STATUS_CHOICES[5][0]  # completed
        job.actual_completion = timezone.now().date()
        job.actual_cost = request.data.get('actual_cost', job.actual_cost)
        job.quality_score = request.data.get('quality_score', job.quality_score)
        job.repair_shop.current_jobs = max(0, job.repair_shop.current_jobs - 1)
        job.repair_shop.save(update_fields=['current_jobs'])
        job.save(update_fields=['status', 'actual_completion', 'actual_cost', 'quality_score'])
        serializer = self.get_serializer(job)
        return Response(serializer.data)
    
    @action(detail=False, methods=['get'], url_path='my-jobs')
    def my_jobs(self, request):
        if request.user.role == 'repair':
            jobs = self.get_queryset().filter(repair_shop__contact_person=request.user.email)
        else:
            jobs = self.get_queryset().filter(claim__customer=request.user)
        serializer = self.get_serializer(jobs, many=True)
        return Response(serializer.data)