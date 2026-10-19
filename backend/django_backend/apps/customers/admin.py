from django.contrib import admin

from .models import CallbackRequest


@admin.register(CallbackRequest)
class CallbackRequestAdmin(admin.ModelAdmin):
    list_display = ('name', 'phone', 'vehicle_type', 'status', 'created_at')
    list_filter = ('status', 'vehicle_type', 'created_at')
    search_fields = ('name', 'phone')
    readonly_fields = ('name', 'phone', 'vehicle_type', 'consent', 'created_at')
    list_editable = ('status',)
