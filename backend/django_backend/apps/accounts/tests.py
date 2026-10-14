from django.contrib.auth import get_user_model
from django.test import override_settings
from django.urls import reverse
from rest_framework import status
from rest_framework.test import APITestCase

@override_settings(
    ALLOWED_HOSTS=['testserver', 'localhost', '127.0.0.1'],
    SECURE_SSL_REDIRECT=False,
)
class RegistrationTests(APITestCase):
    def test_public_registration_cannot_assign_a_privileged_role(self):
        response = self.client.post(
            reverse('auth-register'),
            {
                'email': 'new-customer@example.com',
                'password': 'NewStrongPass!920',
                'password_confirm': 'NewStrongPass!920',
                'role': 'admin',
            },
            format='json',
        )

        self.assertEqual(response.status_code, status.HTTP_201_CREATED)
        user = get_user_model().objects.get(email='new-customer@example.com')
        self.assertEqual(user.role, 'customer')

    def test_registration_rejects_mismatched_passwords(self):
        response = self.client.post(
            reverse('auth-register'),
            {
                'email': 'mismatch@example.com',
                'password': 'NewStrongPass!920',
                'password_confirm': 'DifferentStrongPass!920',
            },
            format='json',
        )

        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertFalse(get_user_model().objects.filter(email='mismatch@example.com').exists())
