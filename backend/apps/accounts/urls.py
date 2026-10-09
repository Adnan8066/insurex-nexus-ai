from django.urls import path, include
from rest_framework.routers import DefaultRouter
from .views import AuthViewSet, CustomTokenRefreshView

router = DefaultRouter()
router.register(r'', AuthViewSet, basename='auth')

urlpatterns = [
    path('', include(router.urls)),
    path('token/refresh/', CustomTokenRefreshView.as_view(), name='token_refresh'),
]