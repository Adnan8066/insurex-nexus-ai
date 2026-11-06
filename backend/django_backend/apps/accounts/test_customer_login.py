from datetime import date

from django.core.cache import cache
from django.test import TestCase
from rest_framework.test import APIClient

from apps.accounts.models import Role, User
from apps.vehicles.models import Vehicle


class CustomerLoginTests(TestCase):
    URL = '/api/v1/auth/customer-login/'

    def setUp(self):
        cache.clear()
        self.customer = User.objects.create_user(
            username='plateuser', email='plateuser@demo.com', password='unused-by-this-flow',
            role=Role.CUSTOMER, first_name='Test', last_name='Customer', phone='+91 98120-34567',
        )
        self.vehicle = Vehicle.objects.create(
            customer=self.customer, make='Mahindra', model='Thar', year=2022, vin='MA1PLATE00000001X',
            color='Blue', license_plate='KL 01 Z 7315', license_state='KL',
            purchase_date=date(2025, 10, 19),
        )
        self.staff = User.objects.create_user(
            username='staffmember', email='staff@insure.com', password='x',
            role=Role.EMPLOYEE, phone='9812034567',
        )
        self.client = APIClient()

    def post(self, email, plate, mobile):
        return self.client.post(
            self.URL, {'email': email, 'license_plate': plate, 'mobile_number': mobile}, format='json',
        )

    def test_correct_email_plate_and_mobile_returns_tokens(self):
        response = self.post('plateuser@demo.com', 'KL 01 Z 7315', '+91 98120-34567')
        self.assertEqual(response.status_code, 200, response.content)
        data = response.json()['data']
        self.assertTrue(data['access'])
        self.assertTrue(data['refresh'])
        self.assertEqual(data['user']['email'], 'plateuser@demo.com')

    def test_email_is_case_insensitive_and_plate_matches_loosely(self):
        self.assertEqual(self.post('PlateUser@Demo.com', 'kl01z7315', '9812034567').status_code, 200)

    def test_wrong_email_is_rejected(self):
        response = self.post('someone@demo.com', 'KL 01 Z 7315', '+91 98120-34567')
        self.assertEqual(response.status_code, 401)
        self.assertNotIn('access', response.json())

    def test_wrong_mobile_is_rejected(self):
        self.assertEqual(self.post('plateuser@demo.com', 'KL 01 Z 7315', '9000000000').status_code, 401)

    def test_wrong_plate_is_rejected(self):
        self.assertEqual(self.post('plateuser@demo.com', 'KL 99 Z 0000', '+91 98120-34567').status_code, 401)

    def test_staff_account_cannot_use_customer_login(self):
        self.staff.phone = '9000011111'
        self.staff.save()
        self.assertEqual(self.post('staff@insure.com', 'KL 01 Z 7315', '9000011111').status_code, 401)

    def test_inactive_customer_is_rejected(self):
        self.customer.is_active = False
        self.customer.save()
        self.assertEqual(self.post('plateuser@demo.com', 'KL 01 Z 7315', '+91 98120-34567').status_code, 401)
