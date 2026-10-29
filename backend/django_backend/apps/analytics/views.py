from rest_framework import viewsets, status, filters, serializers
from rest_framework.decorators import action, api_view, permission_classes
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response
from drf_spectacular.types import OpenApiTypes
from drf_spectacular.utils import extend_schema
from django_filters.rest_framework import DjangoFilterBackend
from django.db.models import Count, Sum, Avg, Q
from django.db.models.functions import TruncDate, TruncMonth
from django.utils import timezone
from datetime import date, timedelta
import json

from .models import DashboardMetric, AnalyticsSnapshot, Report, ReportExecution
from .serializers import (
    DashboardMetricSerializer, AnalyticsSnapshotSerializer,
    ReportSerializer, ReportCreateSerializer, ReportExecutionSerializer
)
from common.permissions import IsStaffMember
from common.params import parse_int
from common.risk import FRAUD_HIGH_THRESHOLD, FRAUD_MODERATE_THRESHOLD, FRAUD_RISK_BANDS
from apps.claims.models import Claim, ClaimStatus
from apps.policies.models import Policy
from apps.investigations.models import FraudAlert


class ClaimTrendResponseSerializer(serializers.Serializer):
    date = serializers.DateField()
    count = serializers.IntegerField()
    total_amount = serializers.DecimalField(max_digits=12, decimal_places=2, allow_null=True)


class DashboardMetricViewSet(viewsets.ModelViewSet):
    queryset = DashboardMetric.objects.all()
    serializer_class = DashboardMetricSerializer
    permission_classes = [IsAuthenticated, IsStaffMember]
    filter_backends = [DjangoFilterBackend, filters.SearchFilter, filters.OrderingFilter]
    filterset_fields = ['metric_type', 'is_active']
    search_fields = ['name', 'display_name']
    ordering_fields = ['name', 'last_calculated']
    ordering = ['name']
    
    @action(detail=True, methods=['post'], url_path='calculate')
    def calculate(self, request, pk=None):
        metric = self.get_object()
        return Response({
            'status': 'calculated',
            'metric': metric.name,
            'value': metric.last_value,
        })


class AnalyticsSnapshotViewSet(viewsets.ReadOnlyModelViewSet):
    queryset = AnalyticsSnapshot.objects.all()
    serializer_class = AnalyticsSnapshotSerializer
    permission_classes = [IsAuthenticated, IsStaffMember]
    filter_backends = [DjangoFilterBackend, filters.OrderingFilter]
    filterset_fields = ['period_type']
    ordering_fields = ['period_start']
    ordering = ['-period_start']
    
    @action(detail=False, methods=['get'], url_path='latest')
    def latest(self, request):
        period_type = request.query_params.get('period_type', 'daily')
        snapshots = self.get_queryset().filter(period_type=period_type).first()
        if snapshots:
            serializer = self.get_serializer(snapshots)
            return Response(serializer.data)
        return Response({'detail': 'No snapshot found'}, status=status.HTTP_404_NOT_FOUND)


class ReportViewSet(viewsets.ModelViewSet):
    queryset = Report.objects.select_related('created_by').prefetch_related('executions').all()
    serializer_class = ReportSerializer
    permission_classes = [IsAuthenticated, IsStaffMember]
    filter_backends = [DjangoFilterBackend, filters.SearchFilter, filters.OrderingFilter]
    filterset_fields = ['report_type', 'is_active']
    search_fields = ['name', 'description']
    ordering_fields = ['created_at', 'last_run', 'next_run']
    ordering = ['-created_at']
    
    def get_serializer_class(self):
        if self.action == 'create':
            return ReportCreateSerializer
        return ReportSerializer
    
    @action(detail=True, methods=['post'], url_path='run')
    def run_report(self, request, pk=None):
        report = self.get_object()
        execution = ReportExecution.objects.create(
            report=report,
            status='running',
            parameters=request.data.get('parameters', {}),
            executed_by=request.user
        )
        
        try:
            result = execute_report(report, request.data.get('parameters', {}))
            execution.status = 'completed'
            execution.result = result
            execution.completed_at = timezone.now()
            report.last_run = timezone.now()
            report.save(update_fields=['last_run'])
        except Exception as e:
            execution.status = 'failed'
            execution.error_message = str(e)
            execution.completed_at = timezone.now()
        
        execution.save()
        serializer = ReportExecutionSerializer(execution)
        return Response(serializer.data)
    
    @action(detail=True, methods=['get'], url_path='executions')
    def executions(self, request, pk=None):
        report = self.get_object()
        executions = report.executions.all()
        serializer = ReportExecutionSerializer(executions, many=True)
        return Response(serializer.data)


class ReportExecutionViewSet(viewsets.ReadOnlyModelViewSet):
    queryset = ReportExecution.objects.select_related('report', 'executed_by').all()
    serializer_class = ReportExecutionSerializer
    permission_classes = [IsAuthenticated, IsStaffMember]
    filter_backends = [DjangoFilterBackend, filters.OrderingFilter]
    filterset_fields = ['status', 'report']
    ordering_fields = ['started_at']
    ordering = ['-started_at']


TIMEFRAME_LABELS = {
    'week': 'Last 7 days',
    'month': 'Last 30 days',
    'quarter': 'Current quarter',
    'ytd': 'Year to date',
    'year': 'Last year',
}
TOTAL_LOSS_THRESHOLD = 50


def resolve_timeframe(timeframe, today=None):
    """Return (start_date, end_date) for a dashboard timeframe, or (None, None) for all time."""
    today = today or timezone.localdate()
    if timeframe == 'week':
        return today - timedelta(days=6), today
    if timeframe == 'month':
        return today - timedelta(days=29), today
    if timeframe == 'quarter':
        return date(today.year, 3 * ((today.month - 1) // 3) + 1, 1), today
    if timeframe == 'ytd':
        return date(today.year, 1, 1), today
    if timeframe == 'year':
        return date(today.year - 1, 1, 1), date(today.year - 1, 12, 31)
    return None, None


def _period(request):
    timeframe = request.query_params.get('timeframe')
    start, end = resolve_timeframe(timeframe)
    return {
        'timeframe': timeframe if start else 'all',
        'label': TIMEFRAME_LABELS.get(timeframe, 'All time'),
        'start': start,
        'end': end,
    }


def _scoped_claims(request, period):
    user = request.user
    claims = Claim.objects.all() if user.is_staff_member else Claim.objects.filter(customer=user)
    if period['start']:
        claims = claims.filter(submitted_at__date__range=(period['start'], period['end']))
    return claims


def _scoped_alerts(request, period):
    user = request.user
    alerts = FraudAlert.objects.all() if user.is_staff_member else FraudAlert.objects.filter(claim__customer=user)
    if period['start']:
        alerts = alerts.filter(created_at__date__range=(period['start'], period['end']))
    return alerts


def _fraud_band_counts(claims):
    return claims.aggregate(
        low=Count('id', filter=Q(fraud_risk_score__lt=FRAUD_MODERATE_THRESHOLD)),
        medium=Count('id', filter=Q(
            fraud_risk_score__gte=FRAUD_MODERATE_THRESHOLD,
            fraud_risk_score__lte=FRAUD_HIGH_THRESHOLD,
        )),
        high=Count('id', filter=Q(fraud_risk_score__gt=FRAUD_HIGH_THRESHOLD)),
    )


def _period_payload(period):
    return {
        'timeframe': period['timeframe'],
        'label': period['label'],
        'start': period['start'],
        'end': period['end'],
    }


@extend_schema(responses=OpenApiTypes.OBJECT)
@api_view(['GET'])
@permission_classes([IsAuthenticated])
def dashboard_summary(request):
    """Dashboard totals. Pass ?timeframe=week|month|quarter|ytd|year to limit claims to that period."""
    from apps.policies.models import Policy, PolicyStatus
    from apps.customers.models import Customer
    from apps.vehicles.models import Vehicle, VehicleStatus

    period = _period(request)
    today = timezone.localdate()
    thirty_days_ago = timezone.now() - timedelta(days=30)
    user = request.user
    claims_qs = _scoped_claims(request, period)
    alerts_qs = _scoped_alerts(request, period)
    policies_qs = Policy.objects.all() if user.is_staff_member else Policy.objects.filter(customer=user)
    active_policies = policies_qs.filter(status=PolicyStatus.ACTIVE)
    if period['start']:
        # Policies started in the period, and policies whose coverage overlapped it.
        new_policies = policies_qs.filter(start_date__range=(period['start'], period['end']))
        active_policies = active_policies.filter(start_date__lte=period['end'], end_date__gte=period['start'])
    else:
        new_policies = policies_qs

    status_counts = dict(claims_qs.values('status').annotate(count=Count('id')).values_list('status', 'count'))
    total_claims = claims_qs.count()
    amounts = claims_qs.aggregate(total=Sum('claim_amount'), avg=Avg('claim_amount'))
    total_loss_cases = claims_qs.filter(total_loss_probability__gte=TOTAL_LOSS_THRESHOLD).count()
    bands = _fraud_band_counts(claims_qs)

    summary = {
        'period': _period_payload(period),
        'claims': {
            'total': total_claims,
            'new_this_month': claims_qs.filter(submitted_at__gte=thirty_days_ago).count(),
            'by_status': status_counts,
            # Every lifecycle status in pipeline order, including statuses with no claims.
            'status_distribution': [
                {'status': value, 'label': str(label), 'count': status_counts.get(value, 0)}
                for value, label in ClaimStatus.choices
            ],
            'by_incident_type': dict(claims_qs.values('incident_type').annotate(count=Count('id')).values_list('incident_type', 'count')),
            'total_amount': amounts['total'] or 0,
            'avg_claim_amount': amounts['avg'] or 0,
            'total_loss_cases': total_loss_cases,
            'repairable_cases': total_claims - total_loss_cases,
            'total_loss_threshold': TOTAL_LOSS_THRESHOLD,
        },
        'policies': {
            'total': new_policies.count(),
            'active': active_policies.count(),
            'expiring_soon': policies_qs.filter(
                status=PolicyStatus.ACTIVE,
                end_date__lte=today + timedelta(days=30),
                end_date__gte=today
            ).count(),
        },
        'fraud': {
            # Model-scored claims above the high-risk band.
            'high_risk_claims': bands['high'],
            'flag_rate': round(bands['high'] / total_claims * 100, 1) if total_claims else 0,
            # Fraud alerts are opened when a claim is referred to an investigator (SIU),
            # which can happen for any score, so they are reported separately.
            'siu_referrals': alerts_qs.count(),
            'total_alerts': alerts_qs.count(),
            'high_risk': alerts_qs.filter(risk_level='high').count(),
            'under_investigation': alerts_qs.filter(status='investigation').count(),
        },
        'customers': {
            'total': Customer.objects.count(),
            'new_this_month': Customer.objects.filter(created_at__gte=thirty_days_ago).count(),
        },
        'vehicles': {
            'total': Vehicle.objects.count(),
            'active': Vehicle.objects.filter(status=VehicleStatus.ACTIVE).count(),
        },
    }

    if not user.is_staff_member:
        # Fraud scoring/SIU referrals are investigator-only information, and
        # portfolio-wide customer/vehicle totals are not the customer's data.
        summary.pop('fraud')
        summary.pop('customers')
        own_vehicles = Vehicle.objects.filter(customer=user)
        summary['vehicles'] = {
            'total': own_vehicles.count(),
            'active': own_vehicles.filter(status=VehicleStatus.ACTIVE).count(),
        }
        summary['claims'].pop('total_loss_cases')
        summary['claims'].pop('repairable_cases')
        summary['claims'].pop('total_loss_threshold')

    return Response(summary)


@extend_schema(responses=OpenApiTypes.OBJECT)
@api_view(['GET'])
@permission_classes([IsAuthenticated, IsStaffMember])
def fraud_risk(request):
    """Claims in the period grouped by fraud risk score band (<30, 30-65, >65)."""
    period = _period(request)
    claims = _scoped_claims(request, period)
    bands = _fraud_band_counts(claims)
    return Response({
        'period': _period_payload(period),
        'total': claims.count(),
        'by_level': bands,
        'bands': [
            {'level': level, 'label': label, 'count': bands[level]}
            for level, label in FRAUD_RISK_BANDS
        ],
        'high_risk': bands['high'],
        'thresholds': {'moderate': FRAUD_MODERATE_THRESHOLD, 'high': FRAUD_HIGH_THRESHOLD},
    })


@extend_schema(responses=OpenApiTypes.OBJECT)
@api_view(['GET'])
@permission_classes([IsAuthenticated])
def overview(request):
    return dashboard_summary(request)


@extend_schema(request=OpenApiTypes.OBJECT, responses=OpenApiTypes.OBJECT)
@api_view(['POST'])
@permission_classes([IsAuthenticated])
def export_report(request):
    return Response({'detail': 'Export is not configured in this environment.'}, status=status.HTTP_501_NOT_IMPLEMENTED)


def _month_starts(start, end):
    current = start.replace(day=1)
    while current <= end:
        yield current
        current = date(current.year + current.month // 12, current.month % 12 + 1, 1)


@extend_schema(responses={200: ClaimTrendResponseSerializer(many=True)})
@api_view(['GET'])
@permission_classes([IsAuthenticated])
def claims_trend(request):
    """Claim intake and amount per bucket, with empty buckets filled with zeros.

    Use ?timeframe=week|month|quarter|ytd|year, or ?days=N for the trailing N days.
    ?granularity=day|month controls bucketing; month buckets are dated on the 1st.
    """
    period = _period(request)
    if period['start']:
        start_date, end_date = period['start'], period['end']
    else:
        end_date = timezone.localdate()
        days = parse_int(request.query_params.get('days'), 'days', minimum=1, maximum=3660, default=30)
        start_date = end_date - timedelta(days=days)
    granularity = 'month' if request.query_params.get('granularity') == 'month' else 'day'

    user = request.user
    claims = Claim.objects.all() if user.is_staff_member else Claim.objects.filter(customer=user)
    claims = claims.filter(submitted_at__date__range=(start_date, end_date))

    if granularity == 'month':
        rows = claims.annotate(bucket=TruncMonth('submitted_at'))
        buckets = list(_month_starts(start_date, end_date))
    else:
        rows = claims.annotate(bucket=TruncDate('submitted_at'))
        buckets = [start_date + timedelta(days=i) for i in range((end_date - start_date).days + 1)]

    totals = {}
    for row in rows.values('bucket').annotate(count=Count('id'), total_amount=Sum('claim_amount')):
        bucket = row['bucket']
        bucket = bucket.date() if hasattr(bucket, 'date') else bucket
        totals[bucket] = row

    return Response([
        {
            'date': bucket,
            'count': totals.get(bucket, {}).get('count', 0),
            'total_amount': totals.get(bucket, {}).get('total_amount') or 0,
        }
        for bucket in buckets
    ])


def execute_report(report, parameters):
    if report.report_type == 'claims_summary':
        return generate_claims_summary(parameters)
    elif report.report_type == 'financial_summary':
        return generate_financial_summary(parameters)
    elif report.report_type == 'fraud_analysis':
        return generate_fraud_analysis(parameters)
    elif report.report_type == 'performance':
        return generate_performance_report(parameters)
    return {}


def generate_claims_summary(parameters):
    from apps.claims.models import Claim
    from django.db.models import Count, Sum, Avg
    from django.db.models.functions import TruncMonth
    
    queryset = Claim.objects.all()
    if parameters.get('start_date'):
        queryset = queryset.filter(submitted_at__gte=parameters['start_date'])
    if parameters.get('end_date'):
        queryset = queryset.filter(submitted_at__lte=parameters['end_date'])
    
    return {
        'total_claims': queryset.count(),
        'by_status': list(queryset.values('status').annotate(count=Count('id'))),
        'by_type': list(queryset.values('incident_type').annotate(count=Count('id'))),
        'monthly_trend': list(
            queryset.annotate(month=TruncMonth('submitted_at'))
            .values('month').annotate(count=Count('id')).order_by('month')
        ),
        'avg_claim_amount': queryset.aggregate(Avg('claim_amount'))['claim_amount__avg'] or 0,
    }


def generate_financial_summary(parameters):
    from apps.claims.models import Claim
    from apps.policies.models import Policy, PremiumHistory
    from django.db.models import Sum
    
    return {
        'total_claims_amount': Claim.objects.aggregate(Sum('claim_amount'))['claim_amount__sum'] or 0,
        'premium_collected': PremiumHistory.objects.filter(status='paid').aggregate(Sum('amount'))['amount__sum'] or 0,
    }


def generate_fraud_analysis(parameters):
    from apps.investigations.models import FraudAlert
    from apps.claims.models import Claim
    from django.db.models import Count, Avg
    
    return {
        'total_fraud_alerts': FraudAlert.objects.count(),
        'by_risk_level': list(FraudAlert.objects.values('risk_level').annotate(count=Count('id'))),
        'by_status': list(FraudAlert.objects.values('status').annotate(count=Count('id'))),
        'avg_risk_score': FraudAlert.objects.aggregate(Avg('risk_score'))['risk_score__avg'] or 0,
        'high_risk_claims': list(
            FraudAlert.objects.filter(risk_level='high')
            .select_related('claim').values('claim__claim_number', 'risk_score', 'status')[:10]
        ),
    }


def generate_performance_report(parameters):
    from apps.claims.models import Claim
    from apps.investigations.models import Investigation
    from django.db.models import Count, Avg
    from django.utils import timezone
    from datetime import timedelta
    
    thirty_days_ago = timezone.now() - timedelta(days=30)
    
    return {
        'claim_processing_time_avg': Claim.objects.filter(
            status__in=['approved', 'closed', 'rejected'],
            updated_at__gte=thirty_days_ago
        ).aggregate(Avg('updated_at'))['updated_at__avg'],
        'investigation_completion_rate': Investigation.objects.filter(
            opened_at__gte=thirty_days_ago
        ).filter(status='completed').count() / max(Investigation.objects.filter(opened_at__gte=thirty_days_ago).count(), 1) * 100,
    }
