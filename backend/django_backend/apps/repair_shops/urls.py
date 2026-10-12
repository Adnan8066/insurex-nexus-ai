from django.urls import path, include
from rest_framework.routers import DefaultRouter
from .views import RepairShopViewSet, RepairJobViewSet

router = DefaultRouter()
router.register(r'shops', RepairShopViewSet, basename='repair-shop')
router.register(r'jobs', RepairJobViewSet, basename='repair-job')

urlpatterns = [
    path('', include(router.urls)),
]