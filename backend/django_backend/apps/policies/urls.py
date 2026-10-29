from django.urls import path, include
from rest_framework.routers import DefaultRouter
from .views import PolicyApplicationViewSet, PolicyViewSet

router = DefaultRouter()
# Registered first: the policy detail route would otherwise treat "applications" as a policy number.
router.register(r'applications', PolicyApplicationViewSet, basename='policy-application')
router.register(r'', PolicyViewSet, basename='policy')

urlpatterns = [
    path('', include(router.urls)),
]
