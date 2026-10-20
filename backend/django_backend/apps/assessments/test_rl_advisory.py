from unittest.mock import patch

from django.contrib.auth import get_user_model
from django.core import signing
from django.db import connection
from django.test import TestCase, override_settings
from django.test.utils import CaptureQueriesContext
from django.urls import reverse
from drf_spectacular.generators import SchemaGenerator
from rest_framework import status
from rest_framework.test import APIClient

from apps.assessments.models import RoutingAgentProfile, RoutingRecommendationReview


@override_settings(ALLOWED_HOSTS=["testserver", "localhost"], SECURE_SSL_REDIRECT=False)
class RoutingAdvisoryAPITests(TestCase):
    def setUp(self):
        self.endpoint = reverse("route-recommendation")
        self.payload = {
            "claim_data": {
                "complexity_score": 0.7,
                "severity_score": 0.6,
                "processing_difficulty": 0.5,
            },
            "active_agents_status": [
                {"id": f"agent-{i}", "queue_length": i, "workload": i * 3, "skill_tier": i}
                for i in range(1, 4)
            ],
        }

    def test_route_requires_authentication(self):
        response = APIClient().post(self.endpoint, self.payload, format="json")

        self.assertEqual(response.status_code, status.HTTP_401_UNAUTHORIZED)

    def test_routing_advice_is_exposed_in_openapi_schema(self):
        schema = SchemaGenerator().get_schema(request=None, public=True)

        self.assertIn("/api/v1/ai/route-recommendation/", schema["paths"])
        self.assertIn("/api/v1/ai/routing-agents/", schema["paths"])
        self.assertIn("/api/v1/ai/route-recommendation/review/", schema["paths"])
        self.assertIn("/api/v1/ai/routing-model-status/", schema["paths"])

    @override_settings(DEBUG=True)
    def test_authorized_request_returns_advice_without_assignment_writes(self):
        User = get_user_model()
        staff_user = User.objects.create_user(
            username="routing-reviewer",
            email="routing-reviewer@example.com",
            password="StrongTestPassword!123",
            role="employee",
        )
        client = APIClient()
        client.force_authenticate(user=staff_user)
        recommendation = {
            "advisory_only": True,
            "automated_assignment": False,
            "requires_human_review": True,
            "status": "recommendation_available",
            "recommended_agent_id": "agent-1",
            "predicted_wait_time": 3.0,
            "workload_impact_summary": "Review the options.",
            "ranked_alternatives": [],
            "ranked_options": [],
        }

        with CaptureQueriesContext(connection) as queries, patch(
            "apps.assessments.rl_views._load_recommendation_engine"
        ) as load_engine:
            engine = load_engine.return_value
            engine.get_routing_recommendations.return_value = recommendation
            response = client.post(self.endpoint, self.payload, format="json")

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(response.json()['recommended_agent_id'], recommendation['recommended_agent_id'])
        self.assertTrue(response.json()['recommendation_id'])
        self.assertFalse(response.json()['automated_assignment'])
        engine.get_routing_recommendations.assert_called_once()
        writes = [
            query["sql"]
            for query in queries
            if query["sql"].lstrip().upper().startswith(("INSERT", "UPDATE", "DELETE"))
        ]
        self.assertEqual(writes, [])

    def test_production_refuses_unqualified_policy(self):
        User = get_user_model()
        client = APIClient()
        client.force_authenticate(user=User.objects.create_user(
            username='production-reviewer', email='production@example.com', password='TestPassword!123', role='employee'
        ))
        with patch.dict('os.environ', {'CLAIM_ROUTING_ENFORCE_EVALUATION_GATE': 'true'}), patch(
            'apps.assessments.rl_views._evaluation_gate_passed', return_value=False
        ), patch(
            'apps.assessments.rl_views._load_recommendation_engine'
        ) as load_engine:
            response = client.post(self.endpoint, self.payload, format='json')

        self.assertEqual(response.status_code, status.HTTP_503_SERVICE_UNAVAILABLE)
        load_engine.assert_not_called()

    def test_roster_uses_configured_profiles(self):
        User = get_user_model()
        client = APIClient()
        client.force_authenticate(user=User.objects.create_user(
            username='roster-reviewer', email='roster@example.com', password='TestPassword!123', role='employee'
        ))
        for index in range(3):
            user = User.objects.create_user(
                username=f'routing-agent-{index}',
                email=f'routing-agent-{index}@example.com',
                password='TestPassword!123',
                role='employee',
                first_name=f'Agent {index}',
            )
            RoutingAgentProfile.objects.create(
                user=user, skill_tier=index + 2, is_available=index != 2, is_demo=index == 1
            )

        response = client.get('/api/v1/ai/routing-agents/')

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(len(response.json()['agents']), 3)
        self.assertEqual(response.json()['agents'][0]['queue_length'], 0)
        self.assertTrue(response.json()['agents'][1]['is_demo'])
        self.assertIn('Synthetic estimate', response.json()['wait_basis'])

    def test_human_review_records_feedback_without_claim_assignment(self):
        User = get_user_model()
        reviewer = User.objects.create_user(
            username='feedback-reviewer', email='feedback@example.com', password='TestPassword!123', role='employee'
        )
        client = APIClient()
        client.force_authenticate(user=reviewer)
        payload = {
            'recommendation_id': 'd7940f5f-6ef3-4139-9642-75ef5e5919aa',
            'decision': 'accepted',
            'notes': 'Useful workload comparison.',
            **self.payload,
            'recommendation': {
                'advisory_only': True,
                'automated_assignment': False,
                'requires_human_review': True,
                'recommended_agent_id': 'agent-1',
                'ranked_options': [],
            },
        }
        normalized_claim = {key: float(value) for key, value in self.payload['claim_data'].items()}
        normalized_agents = [
            {
                **agent,
                'queue_length': float(agent['queue_length']),
                'workload': float(agent['workload']),
                'available': True,
            }
            for agent in self.payload['active_agents_status']
        ]
        payload['review_token'] = signing.dumps(
            {
                'recommendation_id': payload['recommendation_id'],
                'claim_id': None,
                'claim_data': normalized_claim,
                'active_agents_status': normalized_agents,
                'recommendation': payload['recommendation'],
            },
            salt='claim-routing-review',
        )

        with CaptureQueriesContext(connection) as queries:
            response = client.post('/api/v1/ai/route-recommendation/review/', payload, format='json')

        self.assertEqual(response.status_code, status.HTTP_201_CREATED)
        self.assertFalse(response.json()['assignment_changed'])
        self.assertTrue(RoutingRecommendationReview.objects.filter(reviewer=reviewer, decision='accepted').exists())
        writes = [q['sql'] for q in queries if q['sql'].lstrip().upper().startswith(('INSERT', 'UPDATE', 'DELETE'))]
        self.assertEqual(sum('routing_recommendation_reviews' in sql for sql in writes), 1)
        self.assertFalse(any('claims' in sql for sql in writes))
