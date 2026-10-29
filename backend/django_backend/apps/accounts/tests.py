import io

from django.contrib.auth import get_user_model
from django.test import TestCase, override_settings
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


from django.core.cache import cache  # noqa: E402


@override_settings(ALLOWED_HOSTS=['testserver'], SECURE_SSL_REDIRECT=False)
class AuthHardeningTests(APITestCase):
    def setUp(self):
        cache.clear()  # throttle history lives in the default cache

    def tearDown(self):
        cache.clear()

    def test_repeated_failed_logins_are_throttled(self):
        get_user_model().objects.create_user(username='victim', email='victim@example.com', password='RightPass!2026')
        codes = [
            self.client.post('/api/v1/auth/login/', {'email': 'victim@example.com', 'password': 'wrong'}, format='json').status_code
            for _ in range(12)
        ]
        self.assertEqual(codes[:10], [401] * 10)
        self.assertEqual(codes[-1], status.HTTP_429_TOO_MANY_REQUESTS)

    def test_registration_with_same_email_local_part_does_not_collide(self):
        for email in ('john@a-example.com', 'john@b-example.com'):
            response = self.client.post(
                reverse('auth-register'),
                {'email': email, 'password': 'NewStrongPass!920', 'password_confirm': 'NewStrongPass!920'},
                format='json',
            )
            self.assertEqual(response.status_code, status.HTTP_201_CREATED, response.content)
        usernames = set(get_user_model().objects.filter(email__startswith='john@').values_list('username', flat=True))
        self.assertEqual(len(usernames), 2)

    def test_support_contacts_exclude_demo_and_inactive_accounts(self):
        from apps.assessments.models import RoutingAgentProfile
        User = get_user_model()
        real = User.objects.create_user(username='realemp', email='real@example.com', password='x', role='employee')
        demo = User.objects.create_user(username='demo-routing-x', email='demo-routing-x@example.invalid', password='x', role='employee')
        RoutingAgentProfile.objects.create(user=demo, skill_tier=3, is_demo=True)
        User.objects.create_user(username='gone', email='gone@example.com', password='x', role='employee', is_active=False)
        self.client.force_authenticate(real)
        emails = {c['email'] for c in self.client.get('/api/v1/auth/support-contacts/').json()['data']['contacts']}
        self.assertEqual(emails, {'real@example.com'})

    def test_logout_blacklists_refresh_token(self):
        get_user_model().objects.create_user(username='u1', email='u1@example.com', password='RightPass!2026')
        login = self.client.post('/api/v1/auth/login/', {'email': 'u1@example.com', 'password': 'RightPass!2026'}, format='json')
        tokens = login.json()['data']
        self.client.credentials(HTTP_AUTHORIZATION='Bearer ' + tokens['access'])
        logout = self.client.post('/api/v1/auth/logout/', {'refresh': tokens['refresh']}, format='json')
        self.assertEqual(logout.status_code, 200)
        self.client.credentials()
        refreshed = self.client.post('/api/v1/auth/token/refresh/', {'refresh': tokens['refresh']}, format='json')
        self.assertEqual(refreshed.status_code, 401)


class EnsureAdminCommandTests(TestCase):
    def test_creates_app_admin_once_from_environment(self):
        from unittest import mock
        from django.core.management import call_command
        env = {'DJANGO_SUPERUSER_EMAIL': 'Boss@Example.com', 'DJANGO_SUPERUSER_PASSWORD': 'S3cure-pass!'}
        with mock.patch.dict('os.environ', env):
            call_command('ensure_admin', stdout=io.StringIO())
            call_command('ensure_admin', stdout=io.StringIO())
        admins = get_user_model().objects.filter(email='boss@example.com')
        self.assertEqual(admins.count(), 1)
        admin = admins.get()
        self.assertEqual(admin.role, 'admin')
        self.assertTrue(admin.is_superuser)
        self.assertTrue(admin.check_password('S3cure-pass!'))
