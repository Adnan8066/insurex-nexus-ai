from django.urls import path
from . import ai_views, rl_views

urlpatterns = [
    path('assess-claim/', ai_views.assess_claim, name='assess-claim'),
    path('predict-repair-cost/', ai_views.predict_repair_cost, name='predict-repair-cost'),
    path('detect-fraud/', ai_views.detect_fraud, name='detect-fraud'),
    path('predict-total-loss/', ai_views.predict_total_loss, name='predict-total-loss'),
    path('run-agent/<str:agent_type>/', ai_views.run_agent, name='run-agent'),
    path('decision-flow/<int:claim_id>/', ai_views.get_decision_flow, name='decision-flow'),
    path('model-status/', ai_views.model_status, name='model-status'),
    path('route-recommendation/', rl_views.routing_recommendation, name='route-recommendation'),
    path('routing-agents/', rl_views.routing_agents, name='routing-agents'),
    path('routing-claims/', rl_views.routing_claims, name='routing-claims'),
    path('route-recommendation/review/', rl_views.review_routing_recommendation, name='route-recommendation-review'),
    path('routing-model-status/', rl_views.routing_model_status, name='routing-model-status'),
]
