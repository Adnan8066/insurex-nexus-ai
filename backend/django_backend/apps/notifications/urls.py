from django.urls import path, include
from rest_framework.routers import DefaultRouter
from .views import NotificationViewSet, NotificationPreferenceViewSet

router = DefaultRouter()
router.register(r'', NotificationViewSet, basename='notification')

urlpatterns = [
    path(
        'preferences/',
        NotificationPreferenceViewSet.as_view({'get': 'list', 'put': 'update', 'patch': 'update'}),
        name='notification-preferences',
    ),
    path('', include(router.urls)),
]