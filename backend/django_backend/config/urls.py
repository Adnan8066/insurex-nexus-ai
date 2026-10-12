from django.contrib import admin
from django.urls import path, include
from django.conf import settings
from django.conf.urls.static import static
from django.views.generic import RedirectView
from drf_spectacular.views import SpectacularAPIView, SpectacularSwaggerView, SpectacularRedocView

urlpatterns = [
    path('', RedirectView.as_view(url='/api/v1/schema/swagger-ui/', permanent=False), name='home'),
    path('admin/', admin.site.urls),
    
    # API Schema
    path('api/v1/schema/', SpectacularAPIView.as_view(), name='schema'),
    path('api/v1/schema/swagger-ui/', SpectacularSwaggerView.as_view(url_name='schema'), name='swagger-ui'),
    path('api/v1/schema/redoc/', SpectacularRedocView.as_view(url_name='schema'), name='redoc'),
    
    # API v1 Endpoints
    path('api/v1/auth/', include('apps.accounts.urls')),
    path('api/v1/customers/', include('apps.customers.urls')),
    path('api/v1/policies/', include('apps.policies.urls')),
    path('api/v1/vehicles/', include('apps.vehicles.urls')),
    path('api/v1/claims/', include('apps.claims.urls')),
    path('api/v1/assessments/', include('apps.assessments.urls')),
    path('api/v1/investigations/', include('apps.investigations.urls')),
    path('api/v1/repair-shops/', include('apps.repair_shops.urls')),
    path('api/v1/settlements/', include('apps.settlements.urls')),
    path('api/v1/notifications/', include('apps.notifications.urls')),
    path('api/v1/analytics/', include('apps.analytics.urls')),
    path('api/v1/ai/', include('apps.assessments.ai_urls')),
]

if settings.DEBUG:
    urlpatterns += static(settings.MEDIA_URL, document_root=settings.MEDIA_ROOT)
    urlpatterns += static(settings.STATIC_URL, document_root=settings.STATIC_ROOT)