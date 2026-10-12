from rest_framework import viewsets, status, filters
from rest_framework.decorators import action
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response
from django_filters.rest_framework import DjangoFilterBackend

from .models import Vehicle, VehicleDocument, VehicleHistory
from .serializers import (
    VehicleSerializer, VehicleCreateSerializer, VehicleUpdateSerializer,
    VehicleDocumentSerializer, VehicleHistorySerializer
)
from common.permissions import IsOwnerOrAdmin, IsStaffMember


class VehicleViewSet(viewsets.ModelViewSet):
    queryset = Vehicle.objects.select_related('customer', 'policy').prefetch_related('documents', 'history')
    serializer_class = VehicleSerializer
    permission_classes = [IsAuthenticated]
    filter_backends = [DjangoFilterBackend, filters.SearchFilter, filters.OrderingFilter]
    filterset_fields = ['status', 'fuel_type', 'transmission', 'year']
    search_fields = ['vin', 'license_plate', 'make', 'model', 'customer__email', 'customer__first_name', 'customer__last_name']
    ordering_fields = ['created_at', 'year', 'make', 'model', 'current_mileage']
    ordering = ['-created_at']
    
    def get_serializer_class(self):
        if self.action == 'create':
            return VehicleCreateSerializer
        elif self.action in ['update', 'partial_update']:
            return VehicleUpdateSerializer
        return VehicleSerializer
    
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
    
    @action(detail=True, methods=['post'], url_path='documents')
    def upload_document(self, request, pk=None):
        vehicle = self.get_object()
        serializer = VehicleDocumentSerializer(data=request.data)
        if serializer.is_valid():
            serializer.save(vehicle=vehicle, uploaded_by=request.user)
            return Response(serializer.data, status=status.HTTP_201_CREATED)
        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)
    
    @action(detail=True, methods=['get'], url_path='documents')
    def list_documents(self, request, pk=None):
        vehicle = self.get_object()
        documents = vehicle.documents.all()
        serializer = VehicleDocumentSerializer(documents, many=True)
        return Response(serializer.data)
    
    @action(detail=True, methods=['post'], url_path='history')
    def add_history(self, request, pk=None):
        vehicle = self.get_object()
        serializer = VehicleHistorySerializer(data=request.data)
        if serializer.is_valid():
            serializer.save(vehicle=vehicle)
            return Response(serializer.data, status=status.HTTP_201_CREATED)
        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)
    
    @action(detail=True, methods=['get'], url_path='history')
    def list_history(self, request, pk=None):
        vehicle = self.get_object()
        history = vehicle.history.all()
        serializer = VehicleHistorySerializer(history, many=True)
        return Response(serializer.data)
    
    @action(detail=False, methods=['get'], url_path='registration-expiring')
    def registration_expiring(self, request):
        from django.utils import timezone
        from datetime import timedelta
        
        days = int(request.query_params.get('days', 30))
        upcoming_date = timezone.now().date() + timedelta(days=days)
        
        vehicles = self.get_queryset().filter(
            registration_expiry__lte=upcoming_date,
            registration_expiry__gte=timezone.now().date(),
            status=Vehicle.VehicleStatus.ACTIVE
        )
        serializer = self.get_serializer(vehicles, many=True)
        return Response(serializer.data)