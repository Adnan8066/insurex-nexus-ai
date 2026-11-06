from rest_framework import viewsets, status, filters
from rest_framework.decorators import action
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response
from rest_framework import permissions
from django_filters.rest_framework import DjangoFilterBackend
from django.db.models import Q
from django.db import transaction
from django.utils import timezone
from django.utils.dateparse import parse_date
from django.http import HttpResponse
from datetime import timedelta
from django.shortcuts import get_object_or_404
from django.contrib.auth import get_user_model
from django.conf import settings
from decimal import Decimal

from .models import (Policy, PolicyApplication, PolicyEndorsement, PolicyCoverage,
                     PolicyDocument, PremiumHistory, PolicyStatus)
from apps.accounts.models import Role
from apps.vehicles.models import Vehicle
from .serializers import (
    PolicySerializer, PolicyCreateSerializer, PolicyUpdateSerializer,
    PolicyCoverageSerializer, PolicyDocumentSerializer, PremiumHistorySerializer,
    PolicyQuoteSerializer, PolicyApplicationSerializer,
    PolicyEndorsementSerializer, PolicyEndorsementCreateSerializer,
)
from common.permissions import IsEmployee, IsAdmin
from common.params import Conflict, parse_int
from rest_framework.exceptions import PermissionDenied

User = get_user_model()


def _json_safe(value):
    from decimal import Decimal
    if isinstance(value, Decimal):
        return str(value)
    if isinstance(value, dict):
        return {key: _json_safe(item) for key, item in value.items()}
    if isinstance(value, (list, tuple)):
        return [_json_safe(item) for item in value]
    return value


# Customer-requested changes reuse the endorsement queue: staff approve or reject them.
SERVICE_CHANGE_TYPES = {'renewal', 'cancellation', 'vehicle_change'}
VEHICLE_EDITABLE_FIELDS = {'color', 'license_plate', 'current_mileage'}


def _apply_service_request(policy, endorsement):
    """Apply an approved renewal, cancellation or vehicle change to the policy."""
    if endorsement.change_type == 'renewal' and policy.end_date:
        policy.end_date = policy.end_date + timedelta(days=365)
    elif endorsement.change_type == 'cancellation':
        policy.status = 'cancelled'
    elif endorsement.change_type == 'vehicle_change' and policy.vehicle_id:
        vehicle = policy.vehicle
        for field, value in (endorsement.proposed_changes.get('vehicle') or {}).items():
            if field in VEHICLE_EDITABLE_FIELDS:
                setattr(vehicle, field, value)
        vehicle.save()


def _policy_document_html(policy):
    """A printable HTML policy summary the customer can save or print."""
    from django.utils.html import escape
    vehicle = policy.vehicle
    plan_name = (policy.coverage or {}).get('policy_plan', {}).get('name') or policy.type
    rows = [
        ('Policy number', policy.policy_number),
        ('Policy type', plan_name),
        ('Status', policy.status),
        ('Start date', policy.start_date),
        ('End date', policy.end_date),
        ('Annual premium (INR)', policy.premium),
        ('Deductible (INR)', policy.deductible),
        ('Payment frequency', policy.payment_frequency),
        ('Auto-renew', 'Yes' if policy.auto_renew else 'No'),
        ('Customer', policy.customer.get_full_name() or policy.customer.email),
        ('Vehicle', f'{vehicle.year} {vehicle.make} {vehicle.model}' if vehicle else 'Not linked'),
        ('Licence plate', vehicle.license_plate if vehicle else '-'),
        ('Chassis number', vehicle.vin if vehicle else '-'),
    ]
    body = ''.join(f'<tr><th>{escape(label)}</th><td>{escape(value)}</td></tr>' for label, value in rows)
    return (
        '<!doctype html><html><head><meta charset="utf-8">'
        f'<title>{escape(policy.policy_number)}</title>'
        '<style>body{font-family:Arial,sans-serif;margin:40px;color:#111}h1{font-size:22px}'
        'table{border-collapse:collapse;width:100%}th,td{border:1px solid #ccc;padding:8px;text-align:left}'
        'th{width:220px;background:#f3f4f6}.note{color:#555;font-size:12px;margin-top:24px}</style>'
        '</head><body><h1>InsureX Nexus AI - Policy document</h1>'
        f'<table>{body}</table>'
        '<p class="note">Demonstration document. Plan terms and premiums are sample values, '
        'not an insurer policy wording.</p></body></html>'
    )


def _check_can_review(user, application):
    """Employees act on requests assigned to them (or not yet assigned); admins may step in on any."""
    if user.role == Role.EMPLOYEE and application.assigned_to_id not in (None, user.id):
        raise PermissionDenied('This request is assigned to another employee.')


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
        if user.role == Role.CUSTOMER:
            return self.queryset.filter(customer=user)
        return self.queryset.none()
    
    def get_permissions(self):
        if self.action == 'quote':
            return [IsAuthenticated()]
        if self.action in ['bind_quote', 'approve_endorsement', 'reject_endorsement']:
            return [IsAuthenticated(), IsEmployee()]
        if self.action == 'endorsements':
            return [IsAuthenticated(), IsEmployee()]
        if self.action == 'create':
            return [IsAuthenticated(), IsEmployee()]
        if self.action == 'form_options':
            return [IsAuthenticated(), IsEmployee()]
        if self.action in ['update', 'partial_update', 'destroy', 'update_coverage', 'add_premium_payment']:
            return [IsAuthenticated(), IsAdmin()]
        if self.action == 'documents' and self.request.method == 'POST':
            return [IsAuthenticated(), IsAdmin()]
        return [IsAuthenticated()]

    @action(detail=False, methods=['post'], url_path='quote')
    def quote(self, request):
        """Collect underwriting details and persist an estimate-only quote."""
        serializer = PolicyQuoteSerializer(data=request.data, context={'request': request})
        serializer.is_valid(raise_exception=True)
        data = serializer.validated_data
        is_customer_request = request.user.role == Role.CUSTOMER
        if is_customer_request:
            # Underwriting inputs are not self-declared: apply the default score and
            # leave agent assignment to the staff member who reviews the request.
            data['risk_score'] = Decimal(str(settings.POLICY_DEFAULT_RISK_SCORE))
            data['risk_factors'] = {'source': 'customer request; default risk score pending staff review'}
            data['policy_terms'].pop('agent', None)
            vehicle_id = data['policy_terms'].get('vehicle')
            if vehicle_id and PolicyApplication.objects.filter(
                customer=request.user, status=PolicyApplication.Status.QUOTED, policy_terms__vehicle=vehicle_id,
            ).exists():
                raise Conflict('A policy request for this vehicle is already waiting for review.')
        from .services.rating import calculate_premium
        try:
            quote = calculate_premium(
                coverage_limit=data['coverage_limit'],
                deductible=data['deductible'],
                risk_score=data['risk_score'],
            )
        except ValueError as exc:
            return Response({'detail': str(exc)}, status=status.HTTP_400_BAD_REQUEST)
        application = PolicyApplication.objects.create(
            **data,
            created_by=request.user,
            quoted_premium=quote.premium,
            rating_breakdown=quote.as_dict(),
        )
        if is_customer_request:
            from apps.assessments.assignment import assign_policy_request
            assign_policy_request(application)
        return Response(PolicyApplicationSerializer(application).data, status=status.HTTP_201_CREATED)

    @action(detail=False, methods=['post'], url_path='bind-quote')
    def bind_quote(self, request):
        """Explicit staff approval binds a quoted application into an active policy."""
        application_id = parse_int(request.data.get('application_id'), 'application_id')
        with transaction.atomic():
            # Lock the quote so two reviewers cannot issue it twice.
            application = get_object_or_404(PolicyApplication.objects.select_for_update(), pk=application_id)
            if application.status != PolicyApplication.Status.QUOTED:
                return Response({'detail': 'Only an unbound quote can be issued.'}, status=status.HTTP_409_CONFLICT)
            _check_can_review(request.user, application)
            terms = application.policy_terms
            if terms.get('vehicle'):
                vehicle = get_object_or_404(Vehicle.objects.select_for_update(), pk=terms['vehicle'])
                if vehicle.customer_id != application.customer_id or vehicle.policy_id:
                    return Response({'detail': 'The quoted vehicle is no longer available for this customer.'}, status=status.HTTP_409_CONFLICT)
            policy = Policy.objects.create(
                policy_number=f'POL-{__import__("uuid").uuid4().hex[:8].upper()}',
                customer=application.customer,
                agent_id=terms.get('agent'),
                type=application.policy_type,
                status=PolicyStatus.ACTIVE,
                # policy_terms stores ISO strings; convert so the returned policy
                # (is_active, days_remaining) compares real dates.
                start_date=parse_date(terms['start_date']),
                end_date=parse_date(terms['end_date']),
                premium=application.quoted_premium,
                deductible=application.deductible,
                payment_frequency=terms.get('payment_frequency', 'annual'),
                auto_renew=bool(terms.get('auto_renew', False)),
                coverage=terms.get('coverage') or {},
                vehicle_id=terms.get('vehicle'),
                property_address=terms.get('property_address', ''),
                property_type=terms.get('property_type', ''),
                property_year_built=terms.get('property_year_built'),
                property_square_footage=terms.get('property_square_footage'),
            )
            if policy.vehicle_id:
                Vehicle.objects.filter(pk=policy.vehicle_id).update(policy=policy)
            divisor = {'monthly': 12, 'quarterly': 4, 'semi_annual': 2}.get(policy.payment_frequency, 1)
            PremiumHistory.objects.create(
                policy=policy,
                amount=(policy.premium / divisor).quantize(__import__('decimal').Decimal('0.01')),
                due_date=policy.start_date,
            )
            application.status = PolicyApplication.Status.BOUND
            application.bound_policy = policy
            application.reviewed_by = request.user
            application.reviewed_at = timezone.now()
            application.save(update_fields=['status', 'bound_policy', 'reviewed_by', 'reviewed_at', 'updated_at'])
        from apps.notifications.services import create_in_app_notification
        create_in_app_notification(
            policy.customer,
            'policy',
            'Policy issued',
            f'Policy {policy.policy_number} has been issued and is active.',
            link=f'/policies/{policy.policy_number}',
            related_object_type='policy',
            related_object_id=policy.policy_number,
        )
        return Response(PolicySerializer(policy, context={'request': request}).data, status=status.HTTP_201_CREATED)

    # GET and POST share one action: two @actions with the same url_path collide
    # in the router and GET answered 405.
    @action(detail=True, methods=['get', 'post'], url_path='endorsements')
    def endorsements(self, request, pk=None):
        policy = self.get_object()
        if request.method == 'GET':
            return Response(PolicyEndorsementSerializer(policy.endorsements.all(), many=True).data)
        serializer = PolicyEndorsementCreateSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        changes = dict(serializer.validated_data)
        premium_delta = changes.get('premium_delta', 0)
        if policy.premium + premium_delta <= 0:
            return Response({'detail': 'Endorsed premium must remain above zero.'}, status=status.HTTP_400_BAD_REQUEST)
        before = {'premium': str(policy.premium), 'deductible': str(policy.deductible), 'coverage': policy.coverage or {}}
        after = {
            'premium': str(policy.premium + premium_delta),
            'deductible': str(changes.get('deductible', policy.deductible)),
            'coverage': changes.get('coverage', policy.coverage or {}),
        }
        endorsement = PolicyEndorsement.objects.create(
            policy=policy, change_type=changes.pop('change_type'),
            proposed_changes=_json_safe(changes),
            premium_delta=premium_delta, before_snapshot=before, after_snapshot=after,
            created_by=request.user,
        )
        return Response(PolicyEndorsementSerializer(endorsement).data, status=status.HTTP_201_CREATED)

    @action(detail=True, methods=['post'], url_path='endorsements/(?P<endorsement_id>[^/.]+)/approve')
    def approve_endorsement(self, request, pk=None, endorsement_id=None):
        policy = self.get_object()
        with transaction.atomic():
            policy = Policy.objects.select_for_update().get(pk=policy.pk)
            endorsement = get_object_or_404(policy.endorsements.select_for_update(), pk=parse_int(endorsement_id, 'endorsement_id'))
            if endorsement.status != PolicyEndorsement.Status.PENDING:
                return Response({'detail': 'This endorsement is no longer pending.'}, status=status.HTTP_409_CONFLICT)
            changes = endorsement.proposed_changes
            if endorsement.change_type in SERVICE_CHANGE_TYPES:
                _apply_service_request(policy, endorsement)
            coverage = dict(policy.coverage or {})
            coverage.update(changes.get('coverage', {}))
            if changes.get('assets_add'):
                coverage['scheduled_assets'] = [*coverage.get('scheduled_assets', []), *changes['assets_add']]
            policy.coverage = coverage
            policy.deductible = changes.get('deductible', policy.deductible)
            policy.premium = policy.premium + endorsement.premium_delta
            policy.save(update_fields=['coverage', 'deductible', 'premium', 'end_date', 'status', 'updated_at'])
            endorsement.status = PolicyEndorsement.Status.APPROVED
            endorsement.reviewed_by = request.user
            endorsement.reviewed_at = timezone.now()
            endorsement.after_snapshot = {'premium': str(policy.premium), 'deductible': str(policy.deductible), 'coverage': policy.coverage}
            endorsement.save(update_fields=['status', 'reviewed_by', 'reviewed_at', 'after_snapshot'])
            if endorsement.premium_delta:
                PremiumHistory.objects.create(
                    policy=policy,
                    amount=endorsement.premium_delta,
                    due_date=timezone.localdate(),
                    status='pending',
                )
        return Response(PolicyEndorsementSerializer(endorsement).data)

    @action(detail=True, methods=['post'], url_path='endorsements/(?P<endorsement_id>[^/.]+)/reject')
    def reject_endorsement(self, request, pk=None, endorsement_id=None):
        endorsement = get_object_or_404(self.get_object().endorsements.all(), pk=parse_int(endorsement_id, 'endorsement_id'))
        if endorsement.status != PolicyEndorsement.Status.PENDING:
            return Response({'detail': 'This endorsement is no longer pending.'}, status=status.HTTP_409_CONFLICT)
        endorsement.status = PolicyEndorsement.Status.REJECTED
        endorsement.reviewed_by = request.user
        endorsement.reviewed_at = timezone.now()
        endorsement.save(update_fields=['status', 'reviewed_by', 'reviewed_at'])
        return Response(PolicyEndorsementSerializer(endorsement).data)

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
        customer_id = parse_int(customer_id, 'customer') if customer_id else None
        policy_id = parse_int(policy_id, 'policy') if policy_id else None
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
                'year': vehicle.year,
                'make': vehicle.make,
                'model': vehicle.model,
                'purchase_price': str(vehicle.purchase_price) if vehicle.purchase_price is not None else None,
            } for vehicle in vehicles],
            'policies': [{
                'id': policy.pk,
                'label': f'{policy.policy_number} — {policy.get_type_display()} ({policy.status})',
            } for policy in policies],
        })
    
    # GET (any user who can see the policy) and POST (admin only, see
    # get_permissions) share one action; two @actions with the same url_path
    # collide in the router and POST answered 405.
    @action(detail=True, methods=['get', 'post'], url_path='documents')
    def documents(self, request, pk=None):
        policy = self.get_object()
        if request.method == 'POST':
            serializer = PolicyDocumentSerializer(data=request.data)
            if serializer.is_valid():
                serializer.save(policy=policy, uploaded_by=request.user)
                return Response(serializer.data, status=status.HTTP_201_CREATED)
            return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)
        serializer = PolicyDocumentSerializer(policy.documents.all(), many=True)
        return Response(serializer.data)
    
    @action(detail=False, methods=['get'], url_path='plans')
    def plans(self, request):
        """Demo plan catalogue for viewing and comparing policy tiers."""
        from .plans import DEMO_NOTICE, PLAN_CATALOGUE
        return Response({'notice': DEMO_NOTICE, 'plans': PLAN_CATALOGUE})

    @action(detail=True, methods=['get', 'post'], url_path='service-requests')
    def service_requests(self, request, pk=None):
        """Customer requests for renewal, cancellation or vehicle changes; staff approve them."""
        policy = self.get_object()
        pending_queue = policy.endorsements.filter(change_type__in=SERVICE_CHANGE_TYPES)
        if request.method == 'GET':
            return Response(PolicyEndorsementSerializer(pending_queue, many=True).data)
        if request.user.role != Role.CUSTOMER:
            return Response({'detail': 'Only customers can submit service requests.'}, status=status.HTTP_403_FORBIDDEN)

        change_type = request.data.get('change_type')
        reason = str(request.data.get('reason', '')).strip()
        if change_type not in SERVICE_CHANGE_TYPES:
            return Response({'detail': 'Choose renewal, cancellation or vehicle_change.'}, status=status.HTTP_400_BAD_REQUEST)
        if not reason or len(reason) > 500:
            return Response({'detail': 'Give a reason of up to 500 characters.'}, status=status.HTTP_400_BAD_REQUEST)
        if pending_queue.filter(change_type=change_type, status=PolicyEndorsement.Status.PENDING).exists():
            return Response({'detail': 'A request of this type is already waiting for review.'}, status=status.HTTP_409_CONFLICT)
        if change_type == 'cancellation' and policy.status != 'active':
            return Response({'detail': 'Only an active policy can be cancelled.'}, status=status.HTTP_400_BAD_REQUEST)
        if change_type == 'renewal' and policy.status not in ('active', 'expired'):
            return Response({'detail': 'Only an active or expired policy can be renewed.'}, status=status.HTTP_400_BAD_REQUEST)

        proposed = {'reason': reason}
        if change_type == 'vehicle_change':
            requested = request.data.get('vehicle') or {}
            if not isinstance(requested, dict):
                return Response({'detail': 'Vehicle changes must be an object.'}, status=status.HTTP_400_BAD_REQUEST)
            allowed = {key: value for key, value in requested.items()
                       if key in VEHICLE_EDITABLE_FIELDS and value not in (None, '')}
            if not allowed:
                return Response({'detail': 'Choose at least one vehicle detail: colour, licence plate or mileage.'},
                                status=status.HTTP_400_BAD_REQUEST)
            if 'current_mileage' in allowed:
                try:
                    allowed['current_mileage'] = int(allowed['current_mileage'])
                except (TypeError, ValueError):
                    return Response({'detail': 'Mileage must be a whole number.'}, status=status.HTTP_400_BAD_REQUEST)
                if allowed['current_mileage'] < 0:
                    return Response({'detail': 'Mileage cannot be negative.'}, status=status.HTTP_400_BAD_REQUEST)
            proposed['vehicle'] = _json_safe(allowed)

        endorsement = PolicyEndorsement.objects.create(
            policy=policy,
            change_type=change_type,
            proposed_changes=_json_safe(proposed),
            premium_delta=Decimal('0'),
            before_snapshot={'status': policy.status, 'end_date': str(policy.end_date), 'premium': str(policy.premium)},
            after_snapshot={},
            created_by=request.user,
        )
        return Response(PolicyEndorsementSerializer(endorsement).data, status=status.HTTP_201_CREATED)

    @action(detail=True, methods=['get'], url_path='policy-document')
    def policy_document(self, request, pk=None):
        """Download a printable policy summary (HTML)."""
        policy = self.get_object()
        response = HttpResponse(_policy_document_html(policy), content_type='text/html; charset=utf-8')
        response['Content-Disposition'] = f'attachment; filename="{policy.policy_number}.html"'
        return response

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
        
        days = parse_int(request.query_params.get('days'), 'days', minimum=0, maximum=3650, default=30)
        upcoming_date = timezone.now().date() + timedelta(days=days)
        
        policies = self.get_queryset().filter(
            status=PolicyStatus.ACTIVE,
            end_date__lte=upcoming_date,
            end_date__gte=timezone.now().date()
        )
        serializer = self.get_serializer(policies, many=True)
        return Response(serializer.data)


class PolicyApplicationViewSet(viewsets.ReadOnlyModelViewSet):
    """Quotes waiting for a decision. Customers see their own requests; staff see all."""
    serializer_class = PolicyApplicationSerializer
    permission_classes = [IsAuthenticated]
    filter_backends = [DjangoFilterBackend, filters.OrderingFilter]
    filterset_fields = ['status']
    ordering = ['-created_at']

    def get_queryset(self):
        queryset = PolicyApplication.objects.select_related('customer', 'assigned_to', 'reviewed_by', 'bound_policy')
        user = self.request.user
        if user.role == Role.ADMIN:
            return queryset
        if user.role == Role.EMPLOYEE:
            return queryset.filter(Q(assigned_to=user) | Q(assigned_to__isnull=True))
        if user.role == Role.CUSTOMER:
            return queryset.filter(customer=user)
        return queryset.none()

    @action(detail=True, methods=['post'], url_path='decline', permission_classes=[IsAuthenticated, IsEmployee])
    def decline(self, request, pk=None):
        with transaction.atomic():
            application = get_object_or_404(self.get_queryset().select_for_update(of=('self',)), pk=pk)
            if application.status != PolicyApplication.Status.QUOTED:
                raise Conflict('Only a quote waiting for review can be declined.')
            _check_can_review(request.user, application)
            application.status = PolicyApplication.Status.DECLINED
            application.reviewed_by = request.user
            application.reviewed_at = timezone.now()
            application.review_note = str(request.data.get('note', '')).strip()[:2000]
            application.save(update_fields=['status', 'reviewed_by', 'reviewed_at', 'review_note', 'updated_at'])
        from apps.notifications.services import create_in_app_notification
        reason = f' Reason: {application.review_note}' if application.review_note else ''
        create_in_app_notification(
            application.customer, 'policy', 'Policy request declined',
            f'Your policy request could not be approved.{reason}',
            link='/vehicles', related_object_type='policy_application', related_object_id=application.pk,
        )
        return Response(self.get_serializer(application).data)
