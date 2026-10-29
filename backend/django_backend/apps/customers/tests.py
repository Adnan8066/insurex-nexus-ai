from django.contrib.auth import get_user_model
from django.core.cache import cache
from django.test import override_settings
from rest_framework.test import APITestCase


@override_settings(ALLOWED_HOSTS=['testserver'], SECURE_SSL_REDIRECT=False)
class CustomerApiTests(APITestCase):
    def setUp(self):
        cache.clear()
        self.customer = get_user_model().objects.create_user(
            username='ccust', email='ccust@example.com', password='x', role='customer',
        )

    def test_customer_cannot_set_underwriting_fields(self):
        self.client.force_authenticate(self.customer)
        response = self.client.post('/api/v1/customers/', {'license_number': 'DL1', 'risk_rating': 'low', 'credit_score': 850}, format='json')
        self.assertEqual(response.status_code, 400)
        self.assertIn('risk_rating', response.json()['error']['details'])

    def test_duplicate_customer_profile_returns_409_not_500(self):
        self.client.force_authenticate(self.customer)
        self.assertEqual(self.client.post('/api/v1/customers/', {'license_number': 'DL1'}, format='json').status_code, 201)
        self.assertEqual(self.client.post('/api/v1/customers/', {'license_number': 'DL2'}, format='json').status_code, 409)

    def test_public_callback_form_is_throttled(self):
        payload = {'name': 'A', 'phone': '9876543210', 'vehicle_type': 'car', 'consent': True}
        codes = [self.client.post('/api/v1/customers/callback-requests/', payload, format='json').status_code for _ in range(21)]
        self.assertEqual(codes[0], 201)
        self.assertEqual(codes[-1], 429)
