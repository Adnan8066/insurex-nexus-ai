from rest_framework import viewsets, status, filters
from rest_framework.decorators import action
from rest_framework.permissions import AllowAny, IsAuthenticated
from rest_framework.response import Response
from django_filters.rest_framework import DjangoFilterBackend
from django.db.models import Q
from apps.accounts.models import Role

from .models import CallbackRequest, Customer, CustomerDocument
from .serializers import (
    CustomerSerializer, CustomerCreateSerializer,
    CustomerUpdateSerializer, CustomerDocumentSerializer, CallbackRequestSerializer
)
from common.permissions import IsOwnerOrAdmin, IsStaffMember
from common.params import Conflict


class CallbackRequestViewSet(viewsets.ModelViewSet):
    queryset = CallbackRequest.objects.all()
    serializer_class = CallbackRequestSerializer
    http_method_names = ['get', 'post', 'patch', 'head', 'options']

    throttle_scope = 'public_form'

    def get_throttles(self):
        # Only the anonymous public form is rate limited.
        if self.action == 'create':
            from rest_framework.throttling import ScopedRateThrottle
            return [ScopedRateThrottle()]
        return []

    def get_permissions(self):
        if self.action == 'create':
            return [AllowAny()]
        return [IsAuthenticated(), IsStaffMember()]

    def get_queryset(self):
        return CallbackRequest.objects.all() if self.request.user.is_authenticated else CallbackRequest.objects.none()


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
        if user.role in [Role.ADMIN, Role.EMPLOYEE]:
            return self.queryset
        if user.role == Role.INVESTIGATOR:
            return self.queryset.filter(user__claims__assigned_investigator=user).distinct()
        if user.role == Role.CUSTOMER:
            return self.queryset.filter(user=user)
        return self.queryset.none()
    
    def get_permissions(self):
        if self.action in ['create']:
            return [IsAuthenticated()]
        elif self.action in ['update', 'partial_update', 'destroy']:
            return [IsAuthenticated(), IsOwnerOrAdmin()]
        return [IsAuthenticated()]
    
    def perform_create(self, serializer):
        import uuid
        if Customer.objects.filter(user=self.request.user).exists():
            raise Conflict('A customer profile already exists for this account.')
        customer_number = f"CUST-{uuid.uuid4().hex[:8].upper()}"
        serializer.save(customer_number=customer_number)

    # GET and POST share one action; separate @actions with the same url_path
    # collide in the router and POST answered 405.
    @action(detail=True, methods=['get', 'post'], url_path='documents')
    def documents(self, request, pk=None):
        customer = self.get_object()
        if request.method == 'POST':
            serializer = CustomerDocumentSerializer(data=request.data)
            if serializer.is_valid():
                serializer.save(customer=customer, uploaded_by=request.user)
                return Response(serializer.data, status=status.HTTP_201_CREATED)
            return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)
        serializer = CustomerDocumentSerializer(customer.documents.all(), many=True)
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
