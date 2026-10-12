from rest_framework import viewsets, status, filters
from rest_framework.decorators import action
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response
from django_filters.rest_framework import DjangoFilterBackend
from django.db.models import Q

from .models import Customer, CustomerDocument
from .serializers import (
    CustomerSerializer, CustomerCreateSerializer,
    CustomerUpdateSerializer, CustomerDocumentSerializer
)
from common.permissions import IsOwnerOrAdmin, IsStaffMember


class CustomerViewSet(viewsets.ModelViewSet):
    queryset = Customer.objects.select_related('user').prefetch_related('documents')
    serializer_class = CustomerSerializer
    permission_classes = [IsAuthenticated]
    filter_backends = [DjangoFilterBackend, filters.SearchFilter, filters.OrderingFilter]
    filterset_fields = ['risk_rating']
    search_fields = ['customer_number', 'user__email', 'user__first_name', 'user__last_name', 'license_number']
    ordering_fields = ['created_at', 'customer_number', 'risk_rating']
    ordering = ['-created_at']
    
    def get_serializer_class(self):
        if self.action == 'create':
            return CustomerCreateSerializer
        elif self.action in ['update', 'partial_update']:
            return CustomerUpdateSerializer
        return CustomerSerializer
    
    def get_queryset(self):
        user = self.request.user
        if user.is_staff_member:
            return self.queryset
        return self.queryset.filter(user=user)
    
    def get_permissions(self):
        if self.action in ['create']:
            return [IsAuthenticated()]
        elif self.action in ['update', 'partial_update', 'destroy']:
            return [IsAuthenticated(), IsOwnerOrAdmin()]
        return [IsAuthenticated()]
    
    def perform_create(self, serializer):
        import uuid
        customer_number = f"CUST-{uuid.uuid4().hex[:8].upper()}"
        serializer.save(customer_number=customer_number)
    
    @action(detail=True, methods=['post'], url_path='documents')
    def upload_document(self, request, pk=None):
        customer = self.get_object()
        serializer = CustomerDocumentSerializer(data=request.data)
        if serializer.is_valid():
            serializer.save(customer=customer, uploaded_by=request.user)
            return Response(serializer.data, status=status.HTTP_201_CREATED)
        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)
    
    @action(detail=True, methods=['get'], url_path='documents')
    def list_documents(self, request, pk=None):
        customer = self.get_object()
        documents = customer.documents.all()
        serializer = CustomerDocumentSerializer(documents, many=True)
        return Response(serializer.data)
    
    @action(detail=False, methods=['get'], url_path='me')
    def my_profile(self, request):
        try:
            customer = Customer.objects.get(user=request.user)
            serializer = self.get_serializer(customer)
            return Response(serializer.data)
        except Customer.DoesNotExist:
            return Response(
                {'detail': 'Customer profile not found'},
                status=status.HTTP_404_NOT_FOUND
            )