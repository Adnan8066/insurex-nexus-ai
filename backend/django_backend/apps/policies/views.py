from rest_framework import viewsets, status, filters
from rest_framework.decorators import action
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response
from rest_framework import permissions
from django_filters.rest_framework import DjangoFilterBackend
from django.db.models import Q
from django.shortcuts import get_object_or_404
from django.contrib.auth import get_user_model

from .models import Policy, PolicyCoverage, PolicyDocument, PremiumHistory, PolicyStatus
from apps.accounts.models import Role
from apps.vehicles.models import Vehicle
from apps.repair_shops.models import RepairShop
from .serializers import (
    PolicySerializer, PolicyCreateSerializer, PolicyUpdateSerializer,
    PolicyCoverageSerializer, PolicyDocumentSerializer, PremiumHistorySerializer
)
from common.permissions import IsEmployee, IsAdmin

User = get_user_model()


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
    
    lookup_value_regex = r'[^/]+'

    def get_object(self):
        queryset = self.filter_queryset(self.get_queryset())
        pk = self.kwargs.get(self.lookup_field)
        if str(pk).isdigit():
            return get_object_or_404(queryset, pk=pk)
        return get_object_or_404(queryset, policy_number=pk)

    def get_queryset(self):
        user = self.request.user
        if user.role in [Role.ADMIN, Role.EMPLOYEE]:
            return self.queryset
        if user.role == Role.INVESTIGATOR:
            return self.queryset.filter(claims__assigned_investigator=user).distinct()
        if user.role == Role.REPAIR:
            return self.queryset.filter(vehicle__claims__assigned_repair_shop__email__iexact=user.email).distinct()
        if user.role == Role.CUSTOMER:
            return self.queryset.filter(customer=user)
        return self.queryset.none()
    
    def get_permissions(self):
        if self.action == 'create':
            return [IsAuthenticated(), IsAdmin()]
        if self.action == 'form_options':
            return [IsAuthenticated(), IsEmployee()]
        if self.action in ['update', 'partial_update', 'destroy', 'upload_document', 'update_coverage', 'add_premium_payment']:
            return [IsAuthenticated(), IsAdmin()]
        return [IsAuthenticated()]

    def create(self, request, *args, **kwargs):
        serializer = self.get_serializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        self.perform_create(serializer)
        headers = self.get_success_headers(serializer.instance)
        full = PolicySerializer(serializer.instance, context={'request': request}).data
        return Response(full, status=status.HTTP_201_CREATED, headers=headers)

    def perform_create(self, serializer):
        user = self.request.user
        import uuid
        policy_number = f'POL-{uuid.uuid4().hex[:8].upper()}'
        customer = serializer.validated_data.get('customer') or user
        policy = serializer.save(policy_number=policy_number, customer=customer)
        if policy.vehicle_id:
            Vehicle.objects.filter(pk=policy.vehicle_id).update(policy=policy)
        from apps.notifications.services import create_in_app_notification
        create_in_app_notification(
            policy.customer, 'policy', 'Policy created',
            f'Policy {policy.policy_number} was added to your account.',
            link=f'/policies/{policy.policy_number}', related_object_type='policy', related_object_id=policy.policy_number,
        )

    def perform_update(self, serializer):
        policy = self.get_object()
        previous_vehicle_id = policy.vehicle_id
        previous_customer_id = policy.customer_id
        previous_status = policy.status
        updated = serializer.save()
        if previous_vehicle_id and previous_vehicle_id != updated.vehicle_id:
            Vehicle.objects.filter(pk=previous_vehicle_id, policy=updated).update(policy=None)
        if updated.vehicle_id:
            vehicle_update = {'policy': updated}
            if previous_vehicle_id == updated.vehicle_id and previous_customer_id != updated.customer_id:
                vehicle_update['customer_id'] = updated.customer_id
            Vehicle.objects.filter(pk=updated.vehicle_id).update(**vehicle_update)
        from apps.claims.models import Claim
        Claim.objects.filter(policy=updated).exclude(customer=updated.customer).update(customer=updated.customer)
        if previous_status != PolicyStatus.ACTIVE and updated.status == PolicyStatus.ACTIVE:
            from apps.notifications.services import create_in_app_notification
            create_in_app_notification(
                updated.customer,
                'policy',
                'Policy approved and active',
                f'Your policy {updated.policy_number} has been approved and is now active.',
                link=f'/policies/{updated.policy_number}',
                related_object_type='policy',
                related_object_id=updated.policy_number,
                priority='high',
            )

    @action(detail=False, methods=['get'], url_path='form-options', permission_classes=[permissions.IsAuthenticated, IsEmployee])
    def form_options(self, request):
        customer_id = request.query_params.get('customer')
        policy_id = request.query_params.get('policy')
        customers = User.objects.filter(role=Role.CUSTOMER, is_active=True).order_by('last_name', 'first_name', 'email')
        agents = User.objects.filter(role__in=[Role.EMPLOYEE, Role.ADMIN], is_active=True).order_by('last_name', 'first_name', 'email')
        investigators = User.objects.filter(role=Role.INVESTIGATOR, is_active=True).order_by('last_name', 'first_name', 'email')
        vehicles = Vehicle.objects.none()
        policies = Policy.objects.none()
        if customer_id:
            if not customers.filter(pk=customer_id).exists():
                return Response({'detail': 'Select an active customer account.'}, status=status.HTTP_400_BAD_REQUEST)
            current_vehicle_id = None
            if policy_id:
                current_vehicle_id = Policy.objects.filter(pk=policy_id).values_list('vehicle_id', flat=True).first()
            vehicle_scope = Q(customer_id=customer_id)
            if current_vehicle_id:
                vehicle_scope |= Q(pk=current_vehicle_id)
            vehicles = Vehicle.objects.filter(vehicle_scope).filter(
                Q(policy__isnull=True) | Q(policy_id=policy_id) if policy_id else Q(policy__isnull=True)
            ).order_by('year', 'make', 'model')
            available_policies = Q(vehicle__isnull=True)
            if policy_id:
                available_policies |= Q(pk=policy_id)
            policies = Policy.objects.filter(customer_id=customer_id).filter(available_policies).order_by('-created_at')
        shops = RepairShop.objects.filter(status='approved').order_by('name')

        def account_option(user):
            return {
                'id': user.pk,
                'name': user.get_full_name().strip() or user.email,
                'email': user.email,
                'role': user.role,
            }

        return Response({
            'customers': [account_option(user) for user in customers],
            'agents': [account_option(user) for user in agents],
            'investigators': [account_option(user) for user in investigators],
            'vehicles': [{
                'id': vehicle.pk,
                'label': f'{vehicle.year} {vehicle.make} {vehicle.model} ({vehicle.license_plate})',
                'policy': vehicle.policy_id,
            } for vehicle in vehicles],
            'policies': [{
                'id': policy.pk,
                'label': f'{policy.policy_number} — {policy.get_type_display()} ({policy.status})',
            } for policy in policies],
            'repair_shops': [{
                'id': shop.pk,
                'name': shop.name,
                'email': shop.email,
            } for shop in shops],
        })
    
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
            status=PolicyStatus.ACTIVE,
            end_date__lte=upcoming_date,
            end_date__gte=timezone.now().date()
        )
        serializer = self.get_serializer(policies, many=True)
        return Response(serializer.data)
