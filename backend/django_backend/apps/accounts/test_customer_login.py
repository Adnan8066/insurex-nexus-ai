import re
from datetime import timedelta

from django.core import mail
from django.core.cache import cache
from django.test import TestCase, override_settings
from django.utils import timezone
from rest_framework.test import APIClient

from apps.accounts.models import CustomerLoginCode, Role, User


@override_settings(EMAIL_BACKEND='django.core.mail.backends.locmem.EmailBackend')
class CustomerCodeLoginTests(TestCase):
    REQUEST_URL = '/api/v1/auth/customer-login/request-code/'
    VERIFY_URL = '/api/v1/auth/customer-login/verify-code/'

    def setUp(self):
        cache.clear()
        self.customer = User.objects.create_user(
            username='codeuser', email='codeuser@example.com', password='unused-by-this-flow',
            role=Role.CUSTOMER, first_name='Test', last_name='Customer', phone='(555) 555-0101',
        )
        self.staff = User.objects.create_user(
            username='staffmember', email='staff@example.com', password='x', role=Role.EMPLOYEE,
        )
        self.client = APIClient()

    def request_code(self, email):
        return self.client.post(self.REQUEST_URL, {'email': email}, format='json')

    def verify(self, email, code):
        return self.client.post(self.VERIFY_URL, {'email': email, 'code': code}, format='json')

    def last_emailed_code(self):
        return re.search(r'\b(\d{6})\b', mail.outbox[-1].body).group(1)

    def test_requested_code_signs_the_customer_in(self):
        response = self.request_code('codeuser@example.com')
        self.assertEqual(response.status_code, 200, response.content)
        self.assertEqual(len(mail.outbox), 1)
        self.assertEqual(mail.outbox[0].to, ['codeuser@example.com'])

        response = self.verify('codeuser@example.com', self.last_emailed_code())
        self.assertEqual(response.status_code, 200, response.content)
        data = response.json()['data']
        self.assertTrue(data['access'])
        self.assertTrue(data['refresh'])
        self.assertEqual(data['user']['email'], 'codeuser@example.com')

    def test_only_a_hash_of_the_code_is_stored(self):
        self.request_code('codeuser@example.com')
        code = self.last_emailed_code()
        stored = CustomerLoginCode.objects.get(user=self.customer)
        self.assertNotIn(code, stored.code_hash)

    def test_email_is_case_insensitive(self):
        self.request_code('CodeUser@Example.com')
        self.assertEqual(self.verify('CODEUSER@example.com', self.last_emailed_code()).status_code, 200)

    def test_unknown_email_gets_the_same_response_and_no_email(self):
        known = self.request_code('codeuser@example.com')
        unknown = self.request_code('nobody@example.com')
        self.assertEqual(unknown.status_code, 200)
        self.assertEqual(unknown.json(), known.json())
        self.assertEqual(len(mail.outbox), 1)

    def test_staff_and_inactive_customers_get_no_code(self):
        self.request_code('staff@example.com')
        self.customer.is_active = False
        self.customer.save()
        self.request_code('codeuser@example.com')
        self.assertEqual(len(mail.outbox), 0)

    def test_wrong_code_is_rejected(self):
        self.request_code('codeuser@example.com')
        code = self.last_emailed_code()
        wrong = '000000' if code != '000000' else '111111'
        response = self.verify('codeuser@example.com', wrong)
        self.assertEqual(response.status_code, 401)
        self.assertNotIn('access', response.json())

    def test_code_works_only_once(self):
        self.request_code('codeuser@example.com')
        code = self.last_emailed_code()
        self.assertEqual(self.verify('codeuser@example.com', code).status_code, 200)
        self.assertEqual(self.verify('codeuser@example.com', code).status_code, 401)

    def test_expired_code_is_rejected(self):
        self.request_code('codeuser@example.com')
        code = self.last_emailed_code()
        CustomerLoginCode.objects.filter(user=self.customer).update(expires_at=timezone.now() - timedelta(seconds=1))
        self.assertEqual(self.verify('codeuser@example.com', code).status_code, 401)

    def test_new_request_cancels_the_earlier_code(self):
        self.request_code('codeuser@example.com')
        first = self.last_emailed_code()
        self.request_code('codeuser@example.com')
        second = self.last_emailed_code()
        if first != second:
            self.assertEqual(self.verify('codeuser@example.com', first).status_code, 401)
        self.assertEqual(self.verify('codeuser@example.com', second).status_code, 200)

    @override_settings(CUSTOMER_LOGIN_CODE_MAX_ATTEMPTS=3)
    def test_too_many_wrong_guesses_lock_the_code(self):
        self.request_code('codeuser@example.com')
        code = self.last_emailed_code()
        wrong = '000000' if code != '000000' else '111111'
        for _ in range(3):
            self.assertEqual(self.verify('codeuser@example.com', wrong).status_code, 401)
        # Even the right code no longer works; the customer must request a new one.
        self.assertEqual(self.verify('codeuser@example.com', code).status_code, 401)

    def test_code_cannot_sign_in_a_different_customer(self):
        User.objects.create_user(
            username='other', email='other@example.com', password='x', role=Role.CUSTOMER,
        )
        self.request_code('codeuser@example.com')
        self.assertEqual(self.verify('other@example.com', self.last_emailed_code()).status_code, 401)

    def test_old_plate_and_mobile_endpoint_is_gone(self):
        response = self.client.post(
            '/api/v1/auth/customer-login/',
            {'email': 'codeuser@example.com', 'license_plate': 'X', 'mobile_number': '5555550101'},
            format='json',
        )
        self.assertIn(response.status_code, (404, 405))
