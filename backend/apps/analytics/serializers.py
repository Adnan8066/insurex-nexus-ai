from rest_framework import serializers
from .models import DashboardMetric, AnalyticsSnapshot, Report, ReportExecution

class DashboardMetricSerializer(serializers.ModelSerializer):
    class Meta:
        model = DashboardMetric
        fields = [
            'id', 'name', 'display_name', 'metric_type', 'description',
            'query', 'is_active', 'refresh_interval_minutes', 'last_calculated',
            'last_value', 'created_at', 'updated_at'
        ]
        read_only_fields = ['id', 'last_calculated', 'last_value', 'created_at', 'updated_at']

class AnalyticsSnapshotSerializer(serializers.ModelSerializer):
    class Meta:
        model = AnalyticsSnapshot
        fields = [
            'id', 'period_type', 'period_start', 'period_end', 'metrics', 'filters', 'created_at'
        ]
        read_only_fields = ['id', 'created_at']

class ReportSerializer(serializers.ModelSerializer):
    created_by_name = serializers.CharField(source='created_by.get_full_name', read_only=True)
    
    class Meta:
        model = Report
        fields = [
            'id', 'name', 'report_type', 'description', 'query', 'parameters',
            'schedule', 'last_run', 'next_run', 'is_active', 'created_by',
            'created_by_name', 'created_at', 'updated_at'
        ]
        read_only_fields = ['id', 'last_run', 'next_run', 'created_at', 'updated_at']

class ReportCreateSerializer(serializers.ModelSerializer):
    class Meta:
        model = Report
        fields = [
            'name', 'report_type', 'description', 'query', 'parameters', 'schedule'
        ]

class ReportExecutionSerializer(serializers.ModelSerializer):
    report_name = serializers.CharField(source='report.name', read_only=True)
    executed_by_name = serializers.CharField(source='executed_by.get_full_name', read_only=True)
    
    class Meta:
        model = ReportExecution
        fields = [
            'id', 'report', 'report_name', 'status', 'parameters', 'result',
            'file_path', 'error_message', 'started_at', 'completed_at',
            'executed_by', 'executed_by_name'
        ]
        read_only_fields = ['id', 'started_at', 'completed_at', 'executed_by']