from django.urls import path, include
from rest_framework.routers import DefaultRouter
from .views import InvestigationViewSet, FraudAlertViewSet

router = DefaultRouter()
router.register(r'fraud-alerts', FraudAlertViewSet, basename='fraud-alert')
router.register(r'', InvestigationViewSet, basename='investigation')

urlpatterns = [
    path('', include(router.urls)),
]