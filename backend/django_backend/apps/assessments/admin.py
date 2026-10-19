from django.contrib import admin

from .models import RoutingAgentProfile, RoutingRecommendationReview


@admin.register(RoutingAgentProfile)
class RoutingAgentProfileAdmin(admin.ModelAdmin):
    list_display = ('user', 'skill_tier', 'is_available', 'is_demo', 'updated_at')
    list_filter = ('skill_tier', 'is_available', 'is_demo', 'user__role')
    search_fields = ('user__email', 'user__first_name', 'user__last_name')
    readonly_fields = ('is_demo',)
    def get_queryset(self, request):
        return super().get_queryset(request).select_related('user')

    def formfield_for_foreignkey(self, db_field, request, **kwargs):
        if db_field.name == 'user':
            kwargs['queryset'] = db_field.remote_field.model.objects.filter(
                role__in=['employee', 'investigator'], is_active=True
            )
        return super().formfield_for_foreignkey(db_field, request, **kwargs)


@admin.register(RoutingRecommendationReview)
class RoutingRecommendationReviewAdmin(admin.ModelAdmin):
    list_display = ('recommendation_id', 'claim', 'reviewer', 'decision', 'created_at')
    list_filter = ('decision', 'created_at')
    search_fields = ('recommendation_id', 'reviewer__email')
    readonly_fields = (
        'recommendation_id', 'claim', 'reviewer', 'decision', 'notes', 'claim_data',
        'agent_status', 'recommendation', 'created_at',
    )

    def has_add_permission(self, request):
        return False

    def has_change_permission(self, request, obj=None):
        return False
