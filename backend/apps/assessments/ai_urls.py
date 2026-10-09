from django.urls import path
from . import ai_views

urlpatterns = [
    path('assess-claim/', ai_views.assess_claim, name='assess-claim'),
    path('predict-repair-cost/', ai_views.predict_repair_cost, name='predict-repair-cost'),
    path('detect-fraud/', ai_views.detect_fraud, name='detect-fraud'),
    path('predict-total-loss/', ai_views.predict_total_loss, name='predict-total-loss'),
    path('run-agent/<str:agent_type>/', ai_views.run_agent, name='run-agent'),
    path('decision-flow/<int:claim_id>/', ai_views.get_decision_flow, name='decision-flow'),
]