from django.urls import path, include
from rest_framework.routers import DefaultRouter
from .views import InvestigationViewSet, FraudAlertViewSet

router = DefaultRouter()
router.register(r'', InvestigationViewSet, basename='investigation')
router.register(r'fraud-alerts', FraudAlertViewSet, basename='fraud-alert')

urlpatterns = [
    path('', include(router.urls)),
]