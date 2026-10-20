from django.test import TestCase
from django.urls import reverse
from rest_framework import status
from rest_framework.test import APIClient


class CoreAPITests(TestCase):
    def test_health_endpoint_returns_ok(self):
        response = APIClient().get(reverse('health'))

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(response.json(), {'status': 'ok'})

    def test_core_api_collections_require_authentication(self):
        client = APIClient()
        endpoints = [
            '/api/v1/customers/',
            '/api/v1/policies/',
            '/api/v1/vehicles/',
            '/api/v1/claims/',
            '/api/v1/assessments/assessments/',
            '/api/v1/investigations/',
            '/api/v1/settlements/',
            '/api/v1/notifications/',
            '/api/v1/analytics/metrics/',
        ]

        for endpoint in endpoints:
            with self.subTest(endpoint=endpoint):
                response = client.get(endpoint)
                self.assertEqual(response.status_code, status.HTTP_401_UNAUTHORIZED)
