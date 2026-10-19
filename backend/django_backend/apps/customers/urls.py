from django.urls import path, include
from rest_framework.routers import DefaultRouter
from .views import CallbackRequestViewSet, CustomerViewSet

router = DefaultRouter()
router.register(r'callback-requests', CallbackRequestViewSet, basename='callback-request')
router.register(r'', CustomerViewSet, basename='customer')

urlpatterns = [
    path('', include(router.urls)),
]
