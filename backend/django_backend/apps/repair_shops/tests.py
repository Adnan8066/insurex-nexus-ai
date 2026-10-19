from django.test import TestCase
from django.urls import reverse
from drf_spectacular.generators import SchemaGenerator
from rest_framework import status
from rest_framework.test import APIClient


class RepairJobSchemaTests(TestCase):
    def test_repair_job_endpoints_are_in_the_generated_api_schema(self):
        schema = SchemaGenerator().get_schema(request=None, public=True)

        self.assertIn('/api/v1/repair-shops/jobs/', schema['paths'])
        self.assertIn('/api/v1/repair-shops/jobs/{id}/', schema['paths'])

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
            '/api/v1/repair-shops/shops/',
            '/api/v1/repair-shops/jobs/',
            '/api/v1/settlements/',
            '/api/v1/notifications/',
            '/api/v1/analytics/metrics/',
        ]

        for endpoint in endpoints:
            with self.subTest(endpoint=endpoint):
                response = client.get(endpoint)
                self.assertEqual(response.status_code, status.HTTP_401_UNAUTHORIZED)
