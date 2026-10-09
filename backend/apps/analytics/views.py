from rest_framework import viewsets, status, filters
from rest_framework.decorators import action, api_view, permission_classes
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response
from django_filters.rest_framework import DjangoFilterBackend
from django.db.models import Count, Sum, Avg, Q
from django.utils import timezone
from datetime import timedelta
import json

from .models import DashboardMetric, AnalyticsSnapshot, Report, ReportExecution
from .serializers import (
    DashboardMetricSerializer, AnalyticsSnapshotSerializer,
    ReportSerializer, ReportCreateSerializer, ReportExecutionSerializer
)
from common.permissions import IsStaffMember
from apps.claims.models import Claim
from apps.policies.models import Policy
from apps.settlements.models import Settlement
from apps.investigations.models import FraudAlert


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
        try:
            exec(metric.query, {'models': __import__('django.db.models', fromlist=['models'])})
            return Response({'status': 'calculated', 'metric': metric.name})
        except Exception as e:
            return Response({'error': str(e)}, status=status.HTTP_500_INTERNAL_SERVER_ERROR)


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


@api_view(['GET'])
@permission_classes([IsAuthenticated, IsStaffMember])
def dashboard_summary(request):
    from apps.claims.models import Claim
    from apps.policies.models import Policy
    from apps.settlements.models import Settlement
    from apps.investigations.models import FraudAlert
    from apps.customers.models import Customer
    from apps.vehicles.models import Vehicle
    from apps.repair_shops.models import RepairShop, RepairJob
    
    now = timezone.now()
    thirty_days_ago = now - timedelta(days=30)
    
    summary = {
        'claims': {
            'total': Claim.objects.count(),
            'new_this_month': Claim.objects.filter(submitted_at__gte=thirty_days_ago).count(),
            'by_status': dict(Claim.objects.values('status').annotate(count=Count('id')).values_list('status', 'count')),
            'total_amount': Claim.objects.aggregate(Sum('claim_amount'))['claim_amount__sum'] or 0,
        },
        'policies': {
            'total': Policy.objects.count(),
            'active': Policy.objects.filter(status=Policy.PolicyStatus.ACTIVE).count(),
            'expiring_soon': Policy.objects.filter(
                status=Policy.PolicyStatus.ACTIVE,
                end_date__lte=now.date() + timedelta(days=30),
                end_date__gte=now.date()
            ).count(),
        },
        'settlements': {
            'total': Settlement.objects.count(),
            'pending_approval': Settlement.objects.filter(status=Settlement.SettlementStatus.UNDER_REVIEW).count(),
            'pending_payment': Settlement.objects.filter(payment_status=Settlement.PaymentStatus.PROCESSING).count(),
            'total_paid': Settlement.objects.filter(payment_status=Settlement.PaymentStatus.COMPLETED).aggregate(Sum('approved_amount'))['approved_amount__sum'] or 0,
        },
        'fraud': {
            'total_alerts': FraudAlert.objects.count(),
            'high_risk': FraudAlert.objects.filter(risk_level='high').count(),
            'under_investigation': FraudAlert.objects.filter(status='investigation').count(),
        },
        'customers': {
            'total': Customer.objects.count(),
            'new_this_month': Customer.objects.filter(created_at__gte=thirty_days_ago).count(),
        },
        'vehicles': {
            'total': Vehicle.objects.count(),
            'active': Vehicle.objects.filter(status=Vehicle.VehicleStatus.ACTIVE).count(),
        },
        'repair_shops': {
            'total': RepairShop.objects.count(),
            'approved': RepairShop.objects.filter(status=RepairShop.RepairShopStatus.APPROVED).count(),
            'active_jobs': RepairJob.objects.exclude(status__in=['completed', 'delivered', 'cancelled']).count(),
        },
    }
    
    return Response(summary)


@api_view(['GET'])
@permission_classes([IsAuthenticated, IsStaffMember])
def claims_trend(request):
    days = int(request.query_params.get('days', 30))
    end_date = timezone.now().date()
    start_date = end_date - timedelta(days=days)
    
    from apps.claims.models import Claim
    from django.db.models.functions import TruncDate
    
    daily_claims = Claim.objects.filter(
        submitted_at__date__gte=start_date,
        submitted_at__date__lte=end_date
    ).annotate(
        date=TruncDate('submitted_at')
    ).values('date').annotate(
        count=Count('id'),
        total_amount=Sum('claim_amount')
    ).order_by('date')
    
    return Response(list(daily_claims))


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
    from apps.settlements.models import Settlement
    from apps.claims.models import Claim
    from apps.policies.models import Policy, PremiumHistory
    from django.db.models import Sum
    
    return {
        'total_claims_amount': Claim.objects.aggregate(Sum('claim_amount'))['claim_amount__sum'] or 0,
        'total_paid': Settlement.objects.filter(payment_status='completed').aggregate(Sum('approved_amount'))['approved_amount__sum'] or 0,
        'pending_payments': Settlement.objects.filter(payment_status__in=['pending', 'processing']).aggregate(Sum('approved_amount'))['approved_amount__sum'] or 0,
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
    from apps.settlements.models import Settlement
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
        'settlement_approval_rate': Settlement.objects.filter(
            created_at__gte=thirty_days_ago
        ).filter(status='approved').count() / max(Settlement.objects.filter(created_at__gte=thirty_days_ago).count(), 1) * 100,
    }