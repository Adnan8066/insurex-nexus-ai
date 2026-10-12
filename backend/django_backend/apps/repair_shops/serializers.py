from rest_framework import serializers
from .models import RepairShop, RepairJob, RepairEstimate, RepairShopDocument

class RepairShopDocumentSerializer(serializers.ModelSerializer):
    uploaded_by_name = serializers.CharField(source='uploaded_by.get_full_name', read_only=True)
    
    class Meta:
        model = RepairShopDocument
        fields = [
            'id', 'document_type', 'file', 'original_name', 'expiry_date',
            'uploaded_at', 'uploaded_by', 'uploaded_by_name'
        ]
        read_only_fields = ['id', 'uploaded_at', 'uploaded_by']

class RepairEstimateSerializer(serializers.ModelSerializer):
    reviewed_by_name = serializers.CharField(source='reviewed_by.get_full_name', read_only=True)
    approved_by_name = serializers.CharField(source='approved_by.get_full_name', read_only=True)
    
    class Meta:
        model = RepairEstimate
        fields = [
            'id', 'estimate_number', 'status', 'parts_total', 'labor_total',
            'paint_total', 'other_total', 'subtotal', 'tax', 'total',
            'parts', 'labor_items', 'submitted_at', 'reviewed_at', 'reviewed_by',
            'reviewed_by_name', 'approved_at', 'approved_by', 'approved_by_name',
            'created_at', 'updated_at'
        ]
        read_only_fields = ['id', 'estimate_number', 'subtotal', 'total', 'created_at', 'updated_at']

class RepairJobSerializer(serializers.ModelSerializer):
    claim_number = serializers.CharField(source='claim.claim_number', read_only=True)
    repair_shop_name = serializers.CharField(source='repair_shop.name', read_only=True)
    estimates = RepairEstimateSerializer(many=True, read_only=True)
    
    class Meta:
        model = RepairJob
        fields = [
            'id', 'job_number', 'claim', 'claim_number', 'repair_shop', 'repair_shop_name',
            'status', 'priority', 'repair_stage', 'estimated_cost', 'actual_cost',
            'assigned_bay', 'started_at', 'estimated_completion', 'actual_completion',
            'parts', 'labor_hours', 'quality_score', 'customer_satisfaction', 'notes',
            'created_at', 'updated_at', 'estimates'
        ]
        read_only_fields = ['id', 'job_number', 'created_at', 'updated_at']

class RepairJobCreateSerializer(serializers.ModelSerializer):
    class Meta:
        model = RepairJob
        fields = [
            'claim', 'repair_shop', 'priority', 'repair_stage', 'estimated_cost',
            'assigned_bay', 'estimated_completion', 'parts', 'notes'
        ]

class RepairJobUpdateSerializer(serializers.ModelSerializer):
    class Meta:
        model = RepairJob
        fields = [
            'repair_shop', 'status', 'priority', 'repair_stage', 'estimated_cost',
            'actual_cost', 'assigned_bay', 'started_at', 'estimated_completion',
            'actual_completion', 'parts', 'labor_hours', 'quality_score',
            'customer_satisfaction', 'notes'
        ]

class RepairShopSerializer(serializers.ModelSerializer):
    documents = RepairShopDocumentSerializer(many=True, read_only=True)
    active_jobs_count = serializers.SerializerMethodField()
    approved_by_name = serializers.CharField(source='approved_by.get_full_name', read_only=True)
    
    class Meta:
        model = RepairShop
        fields = [
            'id', 'name', 'email', 'phone', 'address', 'city', 'state', 'zip_code',
            'license_number', 'status', 'rating', 'specialties', 'certifications',
            'capacity', 'current_jobs', 'average_turnaround_days', 'oem_certifications',
            'operating_hours', 'contact_person', 'notes', 'created_at', 'updated_at',
            'approved_by', 'approved_by_name', 'approved_at', 'documents', 'active_jobs_count'
        ]
        read_only_fields = ['id', 'created_at', 'updated_at', 'approved_by', 'approved_at']
    
    def get_active_jobs_count(self, obj):
        return obj.jobs.exclude(status__in=['completed', 'delivered', 'cancelled']).count()

class RepairShopCreateSerializer(serializers.ModelSerializer):
    class Meta:
        model = RepairShop
        fields = [
            'name', 'email', 'phone', 'address', 'city', 'state', 'zip_code',
            'license_number', 'specialties', 'certifications', 'capacity',
            'oem_certifications', 'operating_hours', 'contact_person', 'notes'
        ]

class RepairShopUpdateSerializer(serializers.ModelSerializer):
    class Meta:
        model = RepairShop
        fields = [
            'name', 'email', 'phone', 'address', 'city', 'state', 'zip_code',
            'status', 'rating', 'specialties', 'certifications', 'capacity',
            'oem_certifications', 'operating_hours', 'contact_person', 'notes'
        ]