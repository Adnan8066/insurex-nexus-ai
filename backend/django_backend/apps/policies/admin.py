from django.contrib import admin

from .models import PolicyApplication, PolicyEndorsement


@admin.register(PolicyApplication)
class PolicyApplicationAdmin(admin.ModelAdmin):
    list_display = ('id', 'customer', 'policy_type', 'quoted_premium', 'risk_score', 'status', 'created_at')
    list_filter = ('status', 'policy_type', 'created_at')
    search_fields = ('customer__email', 'customer__first_name', 'customer__last_name')
    readonly_fields = tuple(field.name for field in PolicyApplication._meta.fields)

    def has_add_permission(self, request):
        return False

    def has_change_permission(self, request, obj=None):
        return False


@admin.register(PolicyEndorsement)
class PolicyEndorsementAdmin(admin.ModelAdmin):
    list_display = ('id', 'policy', 'change_type', 'premium_delta', 'status', 'created_by', 'reviewed_by')
    list_filter = ('status', 'change_type', 'created_at')
    search_fields = ('policy__policy_number', 'created_by__email')
    readonly_fields = tuple(field.name for field in PolicyEndorsement._meta.fields)

    def has_add_permission(self, request):
        return False

    def has_change_permission(self, request, obj=None):
        return False
