from django.urls import path, include
from rest_framework.routers import DefaultRouter
from .views import ClaimAssessmentViewSet, AgentOutputViewSet, DecisionFlowViewSet, ModelPerformanceViewSet

router = DefaultRouter()
router.register(r'assessments', ClaimAssessmentViewSet, basename='claim-assessment')
router.register(r'agent-outputs', AgentOutputViewSet, basename='agent-output')
router.register(r'decision-flows', DecisionFlowViewSet, basename='decision-flow')
router.register(r'model-performance', ModelPerformanceViewSet, basename='model-performance')

urlpatterns = [
    path('', include(router.urls)),
]