from django.urls import path, include
from rest_framework.routers import DefaultRouter
from .views import (
    DashboardMetricViewSet, AnalyticsSnapshotViewSet,
    ReportViewSet, ReportExecutionViewSet,
    dashboard_summary, claims_trend
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
]