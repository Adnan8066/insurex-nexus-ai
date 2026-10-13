from django.urls import path, include
from rest_framework.routers import DefaultRouter
from .views import (
    DashboardMetricViewSet, AnalyticsSnapshotViewSet,
    ReportViewSet, ReportExecutionViewSet,
    dashboard_summary, claims_trend, fraud_risk, overview, export_report
)

router = DefaultRouter()
router.register(r'metrics', DashboardMetricViewSet, basename='dashboard-metric')
router.register(r'snapshots', AnalyticsSnapshotViewSet, basename='analytics-snapshot')
router.register(r'reports', ReportViewSet, basename='report')
router.register(r'executions', ReportExecutionViewSet, basename='report-execution')

urlpatterns = [
    path('', include(router.urls)),
    path('dashboard/', dashboard_summary, name='dashboard-summary'),
    path('claims-trend/', claims_trend, name='claims-trend'),
    path('fraud-risk/', fraud_risk, name='fraud-risk'),
    path('overview/', overview, name='analytics-overview'),
    path('export/', export_report, name='analytics-export'),
]